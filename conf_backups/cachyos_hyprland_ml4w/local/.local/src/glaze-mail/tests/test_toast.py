from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
from unittest import TestCase, mock
import subprocess

import toast


class ToastTests(TestCase):
    def environment(self, **changes: str) -> dict[str, str]:
        return {"AERC_ACCOUNT_BACKEND": "imap", "AERC_FOLDER": "INBOX",
                "AERC_ACCOUNT": "Central Gmail", "AERC_FROM_NAME": "Alice",
                "AERC_SUBJECT": "Hello", **changes}

    def test_inbox_notification_uses_safe_argv(self) -> None:
        self.assertEqual(toast.notification_args(self.environment()), [
            "notify-send", "-a", "Mail", "-i", "mail-message-new", "--",
            "Alice (Central Gmail)", "Hello",
        ])

    def test_other_folders_and_backends_do_not_duplicate_toasts(self) -> None:
        for changes in ({"AERC_FOLDER": "Sent"}, {"AERC_FOLDER": "to omar33xd"},
                        {"AERC_ACCOUNT_BACKEND": "notmuch"}, {"AERC_ACCOUNT_BACKEND": "maildir"}):
            with self.subTest(changes=changes):
                self.assertIsNone(toast.notification_args(self.environment(**changes)))

    def test_subject_markup_newlines_and_shell_text_are_data(self) -> None:
        args = toast.notification_args(self.environment(AERC_SUBJECT='<b>Hi</b>\n$(touch /nonexistent) & "x"'))
        assert args is not None
        self.assertEqual(args[-1], '&lt;b&gt;Hi&lt;/b&gt; $(touch /nonexistent) &amp; &quot;x&quot;')
        self.assertNotIn("\n", args[-1])
        self.assertEqual(args[5], "--")

    def test_subject_is_limited_without_fetching_body(self) -> None:
        args = toast.notification_args(self.environment(AERC_SUBJECT="x" * 500))
        assert args is not None
        self.assertEqual(args[-1], "x" * 200)

    def test_notification_failure_is_not_reported_as_success(self) -> None:
        for failure in (FileNotFoundError(), subprocess.CalledProcessError(1, "notify-send"), subprocess.TimeoutExpired("notify-send", 5)):
            error = StringIO()
            with self.subTest(failure=failure), mock.patch.dict("os.environ", self.environment(), clear=True), \
                 mock.patch("subprocess.run", side_effect=failure), redirect_stderr(error):
                self.assertEqual(toast.main(), 1)
                self.assertTrue(error.getvalue())

    def test_main_sends_once_without_shell(self) -> None:
        with mock.patch.dict("os.environ", self.environment(), clear=True), \
             mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertEqual(toast.main(), 0)
        self.assertEqual(len(run.call_args_list), 1)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], 5)
