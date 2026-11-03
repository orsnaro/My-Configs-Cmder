#!/usr/bin/env python3
"""Mail-only Google consent and short-lived credential command."""
from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import argparse
import fcntl
import json
import os
import stat
import sys
import tempfile

from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


EXPECTED_EMAIL = "omar.rashad.dev@gmail.com"
MAIL_SCOPE = "https://mail.google.com/"
SCOPES = [MAIL_SCOPE, "openid", "https://www.googleapis.com/auth/userinfo.email"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
STATE_DIRECTORY = Path.home() / ".local/state/glaze-mail"
CLIENT_DIRECTORY = Path("/shared_across_des")


class AuthorizationFailure(ValueError):
    """Safe stage/type metadata, without a provider's secret-bearing message."""

    def __init__(self, stage: str, error_kind: str) -> None:
        self.stage = stage
        self.error_kind = error_kind
        super().__init__(f"{stage} ({error_kind})")


@contextmanager
def _authorization_stage(stage: str) -> Iterator[None]:
    try:
        yield
    except Exception as error:
        raise AuthorizationFailure(stage, type(error).__name__) from None


def validate_identity(claims: Mapping[str, Any], expected_email: str) -> None:
    email = claims.get("email")
    if expected_email != EXPECTED_EMAIL or not isinstance(email, str) or \
            email.casefold() != expected_email.casefold() or claims.get("email_verified") is not True:
        raise ValueError("The verified Google account is not the configured central mailbox")


def validate_mail_scope(scopes: Collection[str]) -> None:
    if MAIL_SCOPE not in scopes:
        raise ValueError("Gmail IMAP permission was not granted")


def _guard_mail_path(path: Path) -> None:
    calendar = Path.home() / ".config/gcal"
    if path.absolute().is_relative_to(calendar.absolute()) or path.resolve().is_relative_to(calendar.resolve()):
        raise ValueError("Calendar state is not a mail credential location")


def _private_directory(directory: Path) -> None:
    _guard_mail_path(directory)
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError("Symlinked credential directories are not supported")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_uid != os.getuid():
        raise ValueError("Credential directory has a different owner")
    directory.chmod(0o700)


def save_credentials(destination: Path, serialized: str) -> None:
    _guard_mail_path(destination)
    if not isinstance(json.loads(serialized), dict):
        raise ValueError("Credentials must be a JSON object")
    _private_directory(destination.parent)
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError("Unsafe credential destination")
    fd, temporary = tempfile.mkstemp(prefix=".oauth-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _locked_state(directory: Path) -> Iterator[None]:
    _private_directory(directory)
    fd = os.open(directory / ".oauth.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
            raise ValueError("Unsafe credential lock")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _client_config(directory: Path) -> dict[str, Any]:
    _guard_mail_path(directory)
    candidates = sorted(directory.glob("client_secret_*.json"))
    if len(candidates) != 1 or candidates[0].is_symlink():
        raise ValueError("Expected exactly one approved Desktop OAuth client")
    document = json.loads(candidates[0].read_text())
    client = document.get("installed", {})
    if not isinstance(client, dict) or not client.get("client_id") or not client.get("client_secret") or \
            client.get("auth_uri") not in {"https://accounts.google.com/o/oauth2/auth", "https://accounts.google.com/o/oauth2/v2/auth"} or \
            client.get("token_uri") != TOKEN_URI:
        raise ValueError("Expected a Desktop client with Google authorization endpoints")
    return {"installed": client}


def _effective_scopes(credentials: Credentials) -> Collection[str]:
    granted = credentials.granted_scopes
    return granted if granted is not None else (credentials.scopes or [])


def _serialized_mail_credentials(credentials: Credentials) -> str:
    document = json.loads(credentials.to_json())
    document["glaze_mail_email"] = EXPECTED_EMAIL
    return json.dumps(document)


def authorize(client_directory: Path, state_directory: Path, expected_email: str) -> None:
    _guard_mail_path(state_directory)
    if expected_email != EXPECTED_EMAIL:
        raise ValueError("Only the configured central mailbox is supported")
    config = _client_config(client_directory)
    flow = InstalledAppFlow.from_client_config(config, SCOPES, autogenerate_code_verifier=True)
    with _authorization_stage("Google consent/token exchange"):
        flow.run_local_server(
            host="127.0.0.1", port=0, open_browser=True, timeout_seconds=300,
            access_type="offline", prompt="consent", login_hint=expected_email,
            authorization_prompt_message="Approve the mail login in your browser: {url}",
            success_message="Mail authorization received. You may close this tab.",
        )
    credentials = flow.credentials
    with _authorization_stage("Google ID-token verification"):
        claims = id_token.verify_oauth2_token(credentials.id_token, Request(), config["installed"]["client_id"])
    with _authorization_stage("central-account verification"):
        validate_identity(claims, expected_email)
    with _authorization_stage("mail-permission verification"):
        validate_mail_scope(_effective_scopes(credentials))
        if not credentials.refresh_token:
            raise ValueError("No refresh token was returned; repeat explicit mail consent")
    with _authorization_stage("separate credential storage"):
        with _locked_state(state_directory):
            save_credentials(state_directory / "oauth.json", _serialized_mail_credentials(credentials))


def _read_credentials(path: Path) -> dict[str, Any]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("Mail credentials must be an owner-only regular file (0600)")
        document = json.load(stream)
    if document.get("glaze_mail_email") != EXPECTED_EMAIL or document.get("token_uri") != TOKEN_URI:
        raise ValueError("Not this mailbox's separately authorized mail credentials")
    validate_mail_scope(document.get("scopes", []))
    return document


def access_token(state_directory: Path) -> str:
    _guard_mail_path(state_directory)
    with _locked_state(state_directory):
        target = state_directory / "oauth.json"
        credentials = Credentials.from_authorized_user_info(_read_credentials(target))
        validate_mail_scope(_effective_scopes(credentials))
        if not credentials.valid:
            if not credentials.refresh_token:
                raise ValueError("Mail consent is missing a refresh token")
            credentials.refresh(Request())
            validate_mail_scope(_effective_scopes(credentials))
            if not credentials.valid:
                raise ValueError("Mail token refresh did not produce a valid credential")
            save_credentials(target, _serialized_mail_credentials(credentials))
        if not isinstance(credentials.token, str) or not credentials.token:
            raise ValueError("No valid mail access token")
        return credentials.token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("authorize", "token"))
    args = parser.parse_args(argv)
    try:
        if args.command == "authorize":
            authorize(CLIENT_DIRECTORY, STATE_DIRECTORY, EXPECTED_EMAIL)
            print("Separate mail credentials saved for the central Gmail account.")
        else:
            print(access_token(STATE_DIRECTORY))
        return 0
    except AuthorizationFailure as error:
        print(f"Mail login failed at {error.stage} ({error.error_kind}); no credential values were logged.", file=sys.stderr)
        return 1
    except Exception:
        # Provider/transport exception strings can contain secret request data.
        print("Mail authorization/credential operation failed; no credential values were logged.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
