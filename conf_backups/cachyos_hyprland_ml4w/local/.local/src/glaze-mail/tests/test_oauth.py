from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import TestCase, mock
import json
import stat
import time

import oauth


EMAIL = "omar.rashad.dev@gmail.com"
MAIL_SCOPE = "https://mail.google.com/"


def stored_credentials(token: str = "old", expired: bool = False) -> dict[str, Any]:
    return {
        "token": token, "refresh_token": "synthetic-refresh",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "synthetic-client", "client_secret": "synthetic-secret",
        "scopes": [MAIL_SCOPE, "openid", "https://www.googleapis.com/auth/userinfo.email"],
        "expiry": "2000-01-01T00:00:00Z" if expired else "2099-01-01T00:00:00Z",
        "glaze_mail_email": EMAIL,
    }


class OAuthTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"

    def save(self, payload: dict[str, Any]) -> Path:
        target = self.state / "oauth.json"
        oauth.save_credentials(target, json.dumps(payload))
        return target

    def client(self, config: dict[str, Any] | None = None) -> Path:
        directory = self.root / "clients"
        directory.mkdir(exist_ok=True)
        payload = config if config is not None else {"installed": {
            "client_id": "synthetic-client", "client_secret": "synthetic-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }}
        (directory / "client_secret_test.json").write_text(json.dumps(payload))
        return directory

    def test_wrong_or_unverified_google_identity_is_rejected(self) -> None:
        oauth.validate_identity({"email": EMAIL, "email_verified": True}, EMAIL)
        for claims in ({"email": "other@example.com", "email_verified": True},
                       {"email": EMAIL, "email_verified": False}, {}):
            with self.subTest(claims=claims), self.assertRaises(ValueError):
                oauth.validate_identity(claims, EMAIL)

    def test_calendar_scope_cannot_be_used_as_mail_scope(self) -> None:
        oauth.validate_mail_scope([MAIL_SCOPE])
        for scopes in ([], ["https://www.googleapis.com/auth/calendar.readonly"]):
            with self.assertRaises(ValueError):
                oauth.validate_mail_scope(scopes)

    def test_save_and_replace_are_private_complete_json(self) -> None:
        target = self.save(stored_credentials())
        target.chmod(0o644)
        oauth.save_credentials(target, json.dumps(stored_credentials("new")))
        self.assertEqual(json.loads(target.read_text())["token"], "new")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(list(self.state.glob(".oauth-*.tmp")), [])

    def test_invalid_json_does_not_replace_existing_credentials(self) -> None:
        target = self.save(stored_credentials())
        before = target.read_bytes()
        with self.assertRaises(ValueError):
            oauth.save_credentials(target, "not-json")
        self.assertEqual(target.read_bytes(), before)

    def test_symlink_token_and_state_directory_are_refused(self) -> None:
        victim = self.root / "victim"
        victim.write_text("untouched")
        self.state.mkdir()
        (self.state / "oauth.json").symlink_to(victim)
        with self.assertRaises(ValueError):
            self.save(stored_credentials())
        self.assertEqual(victim.read_text(), "untouched")
        alias = self.root / "alias"
        alias.symlink_to(self.state, target_is_directory=True)
        with self.assertRaises(ValueError):
            oauth.save_credentials(alias / "different.json", "{}")

    def test_calendar_state_is_refused_before_any_file_read(self) -> None:
        with mock.patch.object(Path, "home", return_value=self.root):
            target = self.root / ".config/gcal/token.json"
            with self.assertRaises(ValueError):
                oauth.save_credentials(target, "{}")
            with self.assertRaises(ValueError):
                oauth.access_token(target.parent)
        self.assertFalse((self.root / ".config").exists())

    def test_missing_or_unscoped_mail_token_fails_closed(self) -> None:
        with self.assertRaises((ValueError, FileNotFoundError)):
            oauth.access_token(self.state)
        payload = stored_credentials()
        payload["scopes"] = ["https://www.googleapis.com/auth/tasks.readonly"]
        self.save(payload)
        with self.assertRaises(ValueError):
            oauth.access_token(self.state)

    def test_valid_mail_token_needs_no_network_or_stdout(self) -> None:
        self.save(stored_credentials("synthetic-access"))
        output = StringIO()
        with redirect_stdout(output), mock.patch("google.oauth2.credentials.Credentials.refresh", side_effect=AssertionError("no refresh expected")):
            self.assertEqual(oauth.access_token(self.state), "synthetic-access")
        self.assertEqual(output.getvalue(), "")

    def test_refresh_failure_preserves_valid_json(self) -> None:
        target = self.save(stored_credentials(expired=True))
        before = target.read_bytes()
        with mock.patch("google.oauth2.credentials.Credentials.refresh", side_effect=RuntimeError("synthetic-secret")):
            with self.assertRaises(RuntimeError):
                oauth.access_token(self.state)
        self.assertEqual(target.read_bytes(), before)

    def test_concurrent_refresh_is_serialized_and_saves_one_token(self) -> None:
        target = self.save(stored_credentials(expired=True))
        calls: list[int] = []

        def refresh(credentials: Any, request: Any) -> None:
            calls.append(1)
            time.sleep(0.03)
            credentials.token = "refreshed"
            credentials.expiry = datetime(2099, 1, 1)

        with mock.patch("google.oauth2.credentials.Credentials.refresh", new=refresh):
            with ThreadPoolExecutor(max_workers=4) as pool:
                tokens = list(pool.map(lambda _: oauth.access_token(self.state), range(4)))
        self.assertEqual(tokens, ["refreshed"] * 4)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(target.read_text())["glaze_mail_email"], EMAIL)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_unsafe_stored_token_permissions_are_rejected(self) -> None:
        target = self.save(stored_credentials())
        target.chmod(0o644)
        with self.assertRaises(ValueError):
            oauth.access_token(self.state)

    def test_missing_ambiguous_or_non_google_client_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            oauth.authorize(self.root / "missing", self.state, EMAIL)
        for config in ({"web": {}}, {"installed": {"auth_uri": "https://evil.invalid", "token_uri": "https://oauth2.googleapis.com/token"}}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                oauth.authorize(self.client(config), self.state, EMAIL)
        directory = self.client()
        (directory / "client_secret_second.json").write_text("{}")
        with self.assertRaises(ValueError):
            oauth.authorize(directory, self.state, EMAIL)

    def test_authorization_checks_identity_and_scope_before_saving(self) -> None:
        directory = self.client()
        credentials = mock.Mock()
        credentials.id_token = "synthetic-id"
        credentials.granted_scopes = [MAIL_SCOPE]
        credentials.to_json.return_value = json.dumps(stored_credentials("authorized"))
        flow = mock.Mock(credentials=credentials)
        with mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", return_value=flow) as constructor, \
             mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value={"email": EMAIL, "email_verified": True}):
            oauth.authorize(directory, self.state, EMAIL)
        self.assertEqual(json.loads((self.state / "oauth.json").read_text())["token"], "authorized")
        self.assertTrue(constructor.call_args.kwargs["autogenerate_code_verifier"])
        self.assertEqual(flow.run_local_server.call_args.kwargs["host"], "127.0.0.1")
        self.assertEqual(flow.run_local_server.call_args.kwargs["port"], 0)
        self.assertEqual(flow.run_local_server.call_args.kwargs["timeout_seconds"], 300)

    def test_wrong_authorized_account_never_saves(self) -> None:
        directory = self.client()
        credentials = mock.Mock(id_token="synthetic-id", granted_scopes=[MAIL_SCOPE])
        with mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", return_value=mock.Mock(credentials=credentials)), \
             mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value={"email": "wrong@example.com", "email_verified": True}):
            with self.assertRaises(ValueError):
                oauth.authorize(directory, self.state, EMAIL)
        self.assertFalse((self.state / "oauth.json").exists())

    def test_declined_mail_permission_never_saves(self) -> None:
        directory = self.client()
        credentials = mock.Mock(id_token="synthetic-id", granted_scopes=[])
        with mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", return_value=mock.Mock(credentials=credentials)), \
             mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value={"email": EMAIL, "email_verified": True}):
            with self.assertRaises(ValueError):
                oauth.authorize(directory, self.state, EMAIL)
        self.assertFalse((self.state / "oauth.json").exists())

    def test_cli_error_does_not_print_credential_values(self) -> None:
        output, error = StringIO(), StringIO()
        with mock.patch.object(oauth, "access_token", side_effect=RuntimeError("synthetic-secret")), redirect_stdout(output), redirect_stderr(error):
            self.assertNotEqual(oauth.main(["token"]), 0)
        self.assertNotIn("synthetic-secret", output.getvalue() + error.getvalue())

    def test_consent_failure_reports_safe_stage_and_type(self) -> None:
        directory = self.client()
        flow = mock.Mock()
        flow.run_local_server.side_effect = Warning("synthetic-secret-token")
        output, error = StringIO(), StringIO()
        with mock.patch.object(oauth, "CLIENT_DIRECTORY", directory), \
             mock.patch.object(oauth, "STATE_DIRECTORY", self.state), \
             mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config", return_value=flow), \
             redirect_stdout(output), redirect_stderr(error):
            self.assertEqual(oauth.main(["authorize"]), 1)
        self.assertIn("Google consent/token exchange", error.getvalue())
        self.assertIn("Warning", error.getvalue())
        self.assertNotIn("synthetic-secret-token", output.getvalue() + error.getvalue())
        self.assertFalse((self.state / "oauth.json").exists())

    def test_only_token_subcommand_deliberately_prints_token(self) -> None:
        output = StringIO()
        with mock.patch.object(oauth, "access_token", return_value="synthetic-access"), redirect_stdout(output):
            self.assertEqual(oauth.main(["token"]), 0)
        self.assertEqual(output.getvalue(), "synthetic-access\n")
