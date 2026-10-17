from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from app.schemas.user import ForgotPasswordRequest
from app.services.auth_service import AuthService, PasswordResetError


class PasswordResetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.user = SimpleNamespace(
            id=self.user_id,
            email="member@example.com",
            status="active",
            password_hash="old-hash",
        )
        self.token = SimpleNamespace(
            user_id=self.user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            used_at=None,
            revoked_at=None,
        )
        self.service = AuthService.__new__(AuthService)
        self.service.db = Mock()
        self.service.user_repo = Mock()
        self.service.user_repo.get_by_email.return_value = self.user
        self.service.user_repo.get_by_id_for_update.return_value = self.user
        self.service.session_repo = Mock()
        self.service.reset_token_repo = Mock()
        self.service.reset_token_repo.get_by_hash.return_value = self.token
        self.service.reset_token_repo.mark_used.side_effect = (
            lambda token, used_at: setattr(token, "used_at", used_at)
        )

    def test_valid_token_changes_password_and_revokes_sessions(self) -> None:
        with patch("app.services.auth_service.hash_password", return_value="new-hash"):
            self.service.reset_password("raw-token", "new-password")

        self.assertEqual(self.user.password_hash, "new-hash")
        self.assertIsNotNone(self.token.used_at)
        self.service.session_repo.revoke_all_by_user_id.assert_called_once_with(
            self.user_id, self.token.used_at
        )
        self.service.db.commit.assert_called_once()

    def test_expired_token_is_rejected_without_commit(self) -> None:
        self.token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        with self.assertRaises(PasswordResetError):
            self.service.reset_password("raw-token", "new-password")

        self.service.db.commit.assert_not_called()
        self.service.session_repo.revoke_all_by_user_id.assert_not_called()

    def test_used_or_revoked_token_is_rejected(self) -> None:
        for state in ("used_at", "revoked_at"):
            with self.subTest(state=state):
                setattr(self.token, state, datetime.now(timezone.utc))
                with self.assertRaises(PasswordResetError):
                    self.service.reset_password("raw-token", "new-password")
                setattr(self.token, state, None)

        self.service.db.commit.assert_not_called()

    def test_unknown_email_does_not_create_a_reset_token(self) -> None:
        self.service.user_repo.get_by_email.return_value = None

        self.service.request_password_reset("missing@example.com", Mock())

        self.service.reset_token_repo.create.assert_not_called()
        self.service.db.commit.assert_not_called()

    def test_request_stores_only_hashed_token_and_metadata(self) -> None:
        request = SimpleNamespace(
            client=SimpleNamespace(host="192.0.2.1"),
            headers={"user-agent": "password-reset-test"},
        )

        with patch("app.services.auth_service.settings.debug", False):
            self.service.request_password_reset("member@example.com", request)

        token = self.service.reset_token_repo.create.call_args.args[0]
        self.assertEqual(len(token.token_hash), 64)
        self.assertNotEqual(token.token_hash, "raw-token")
        self.assertGreater(token.expires_at, datetime.now(timezone.utc))
        self.assertEqual(token.ip_address, "192.0.2.1")
        self.assertEqual(token.user_agent, "password-reset-test")
        self.service.db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()