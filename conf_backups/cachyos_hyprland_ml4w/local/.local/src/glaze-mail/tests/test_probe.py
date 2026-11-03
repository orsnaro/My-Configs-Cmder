from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any
from unittest import TestCase, mock
import ssl

import probe


class MailServer:
    def __init__(self, failure: str = "") -> None:
        self.calls: list[str] = []
        self.failure = failure

    def authenticate(self, mechanism: str, responder: Any) -> tuple[str, list[bytes]]:
        self.calls.append("AUTHENTICATE")
        assert mechanism == "XOAUTH2"
        assert responder(b"") == b"user=omar.rashad.dev@gmail.com\x01auth=Bearer synthetic-access\x01\x01"
        if self.failure == "AUTHENTICATE":
            assert responder(b'{"status":"401"}') == b""
            raise OSError("synthetic-access must never be logged")
        return "OK", [b"authenticated"]

    def capability(self) -> tuple[str, list[bytes]]:
        self.calls.append("CAPABILITY")
        return ("NO" if self.failure == "CAPABILITY" else "OK"), [b"IMAP4rev1 IDLE X-GM-EXT-1"]

    def list(self) -> tuple[str, list[bytes]]:
        self.calls.append("LIST")
        return ("NO" if self.failure == "LIST" else "OK"), [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren) "/" "to omar33xd"',
            b'(\\HasNoChildren) "/" "Other arbitrary label"',
        ]

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.calls.append("EXAMINE")
        assert mailbox == "INBOX" and readonly is True
        return ("NO" if self.failure == "EXAMINE" else "OK"), [b"42"]

    def logout(self) -> tuple[str, list[bytes]]:
        self.calls.append("LOGOUT")
        return "BYE", [b"done"]


class ProbeTests(TestCase):
    def test_readonly_probe_preserves_folders_and_unlabelled_inbox(self) -> None:
        server = MailServer()
        with mock.patch("imaplib.IMAP4_SSL", return_value=server) as connect:
            result = probe.inspect_mailbox("synthetic-access", "omar.rashad.dev@gmail.com")
        self.assertEqual(result["inbox_messages"], 42)
        self.assertEqual(result["capabilities"], ["IMAP4rev1", "IDLE", "X-GM-EXT-1"])
        self.assertEqual(result["folders_raw"], [
            '(\\HasNoChildren) "/" "INBOX"',
            '(\\HasNoChildren) "/" "to omar33xd"',
            '(\\HasNoChildren) "/" "Other arbitrary label"',
        ])
        self.assertEqual(server.calls, ["AUTHENTICATE", "CAPABILITY", "LIST", "EXAMINE", "LOGOUT"])
        self.assertEqual(connect.call_args.args, ("imap.gmail.com", 993))
        self.assertEqual(connect.call_args.kwargs["timeout"], 30)
        context = connect.call_args.kwargs["ssl_context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertNotIn("synthetic-access", str(result))

    def test_every_server_failure_fails_instead_of_empty_success(self) -> None:
        for failure in ("AUTHENTICATE", "CAPABILITY", "LIST", "EXAMINE"):
            server = MailServer(failure)
            with self.subTest(failure=failure), mock.patch("imaplib.IMAP4_SSL", return_value=server):
                with self.assertRaises((OSError, ValueError)):
                    probe.inspect_mailbox("synthetic-access", "omar.rashad.dev@gmail.com")
            self.assertEqual(server.calls[-1], "LOGOUT")

    def test_wrong_username_is_rejected_before_connection(self) -> None:
        with mock.patch("imaplib.IMAP4_SSL", side_effect=AssertionError("must not connect")):
            with self.assertRaises(ValueError):
                probe.inspect_mailbox("synthetic-access", "other@example.com")

    def test_cli_redacts_provider_errors(self) -> None:
        output, error = StringIO(), StringIO()
        with mock.patch.object(probe, "access_token", return_value="synthetic-access"), \
             mock.patch.object(probe, "inspect_mailbox", side_effect=OSError("synthetic-access")), \
             redirect_stdout(output), redirect_stderr(error):
            self.assertNotEqual(probe.main(), 0)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("synthetic-access", error.getvalue())
