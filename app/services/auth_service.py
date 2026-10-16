import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.currency import Currency
from app.models.user import Role, User, UserSession
from app.schemas.user import LoginRequest, TokenPair, UserCreate


class AuthenticationError(Exception):
    pass


class RegistrationError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, data: UserCreate, request: Request) -> tuple[User, TokenPair]:
        if self.db.get(Currency, data.default_currency) is None:
            raise RegistrationError("Unsupported default currency")
        user_role = self.db.scalar(select(Role).where(Role.code == "user"))
        if user_role is None:
            raise RuntimeError("Required user role is missing; apply the database seed migration")

        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            default_currency=data.default_currency,
        )
        self.db.add(user)
        self.db.flush()
        user.roles.append(user_role)
        pair = self._create_session(user, request)
        self.db.commit()
        self.db.refresh(user)
        return user, pair

    def login(self, data: LoginRequest, request: Request) -> tuple[User, TokenPair]:
        user = self.db.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == data.email)
        )
        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if user.status != "active":
            raise AuthenticationError("Account is locked")
        user.last_login_at = datetime.now(timezone.utc)
        pair = self._create_session(user, request)
        self.db.commit()
        return user, pair

    def rotate_refresh_token(self, token: str) -> TokenPair:
        payload = self._decode(token)
        user_id = UUID(str(payload["sub"]))
        session_id = UUID(str(payload["sid"]))
        session = self.db.scalar(
            select(UserSession).where(UserSession.id == session_id).with_for_update()
        )
        now = datetime.now(timezone.utc)
        if (
            session is None
            or session.user_id != user_id
            or session.revoked_at is not None
            or session.expires_at <= now
            or not hmac.compare_digest(session.refresh_token_hash, hash_refresh_token(token))
        ):
            raise AuthenticationError("Invalid or expired refresh token")
        user = self.db.scalar(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        if user is None or user.status != "active":
            raise AuthenticationError("Invalid or expired refresh token")
        refresh = create_refresh_token(user.id, session.id, session.expires_at)
        session.refresh_token_hash = hash_refresh_token(refresh)
        self.db.commit()
        return TokenPair(
            access_token=create_access_token(user.id, [role.code for role in user.roles]),
            refresh_token=refresh,
        )

    def revoke_refresh_token(self, token: str) -> None:
        payload = self._decode(token)
        session = self.db.scalar(
            select(UserSession)
            .where(UserSession.id == UUID(str(payload["sid"])))
            .with_for_update()
        )
        if (
            session is None
            or session.user_id != UUID(str(payload["sub"]))
            or not hmac.compare_digest(session.refresh_token_hash, hash_refresh_token(token))
        ):
            raise AuthenticationError("Invalid refresh token")
        if session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def _create_session(self, user: User, request: Request) -> TokenPair:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        session_id = uuid4()
        refresh = create_refresh_token(user.id, session_id, expires_at)
        client_ip = None
        if request.client and request.client.host:
            try:
                import ipaddress
                ipaddress.ip_address(request.client.host)
                client_ip = request.client.host
            except ValueError:
                client_ip = None
        session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh),
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent", "")[:255] or None,
        )
        self.db.add(session)
        return TokenPair(
            access_token=create_access_token(
                user.id, [role.code for role in user.roles]
            ),
            refresh_token=refresh,
        )

    @staticmethod
    def _decode(token: str) -> dict[str, object]:
        try:
            return decode_token(token, "refresh")
        except InvalidTokenError as exc:
            raise AuthenticationError(str(exc)) from exc