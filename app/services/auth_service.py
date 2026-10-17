import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy.orm import Session

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
from app.models.user import User, UserSession
from app.repositories.currency_repository import CurrencyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.schemas.user import LoginRequest, TokenPair, UserCreate


class AuthenticationError(Exception):
    pass


class RegistrationError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        db: Session | None = None,
        user_repo: UserRepository | None = None,
        session_repo: UserSessionRepository | None = None,
        currency_repo: CurrencyRepository | None = None,
    ) -> None:
        if db is not None:
            self.db = db
            self.user_repo = user_repo or UserRepository(db)
            self.session_repo = session_repo or UserSessionRepository(db)
            self.currency_repo = currency_repo or CurrencyRepository(db)
        elif user_repo is not None:
            self.user_repo = user_repo
            self.db = user_repo.db
            self.session_repo = session_repo or UserSessionRepository(self.db)
            self.currency_repo = currency_repo or CurrencyRepository(self.db)
        else:
            raise ValueError("Either db or repositories must be provided to AuthService")

    def register(self, data: UserCreate, request: Request) -> tuple[User, TokenPair]:
        if not self.currency_repo.exists(data.default_currency):
            raise RegistrationError("Unsupported default currency")

        user_role = self.user_repo.get_role_by_code("user")
        if user_role is None:
            raise RuntimeError("Required user role is missing; apply the database seed migration")

        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            default_currency=data.default_currency,
        )
        self.user_repo.create(user, role=user_role)

        pair = self._create_session(user, request)
        self.db.commit()
        self.user_repo.refresh(user)
        return user, pair

    def login(self, data: LoginRequest, request: Request) -> tuple[User, TokenPair]:
        user = self.user_repo.get_by_email(data.email, load_roles=True)
        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if user.status != "active":
            raise AuthenticationError("Account is locked")

        self.user_repo.update_last_login(user, datetime.now(timezone.utc))
        pair = self._create_session(user, request)
        self.db.commit()
        return user, pair

    def rotate_refresh_token(self, token: str) -> TokenPair:
        payload = self._decode(token)
        user_id = UUID(str(payload["sub"]))
        session_id = UUID(str(payload["sid"]))

        session = self.session_repo.get_by_id(session_id, for_update=True)
        now = datetime.now(timezone.utc)
        if (
            session is None
            or session.user_id != user_id
            or session.revoked_at is not None
            or session.expires_at <= now
            or not hmac.compare_digest(session.refresh_token_hash, hash_refresh_token(token))
        ):
            raise AuthenticationError("Invalid or expired refresh token")

        user = self.user_repo.get_active_by_id_with_roles(user_id)
        if user is None:
            raise AuthenticationError("Invalid or expired refresh token")

        refresh = create_refresh_token(user.id, session.id, session.expires_at)
        self.session_repo.update_hash(session, hash_refresh_token(refresh))
        self.db.commit()
        return TokenPair(
            access_token=create_access_token(user.id, [role.code for role in user.roles]),
            refresh_token=refresh,
        )

    def revoke_refresh_token(self, token: str) -> None:
        payload = self._decode(token)
        session_id = UUID(str(payload["sid"]))
        user_id = UUID(str(payload["sub"]))

        session = self.session_repo.get_by_id(session_id, for_update=True)
        if (
            session is None
            or session.user_id != user_id
            or not hmac.compare_digest(session.refresh_token_hash, hash_refresh_token(token))
        ):
            raise AuthenticationError("Invalid refresh token")

        if session.revoked_at is None:
            self.session_repo.revoke(session)
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
        self.session_repo.create(session)
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