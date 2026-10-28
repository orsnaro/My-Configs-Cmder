"""TV TLS policy using real contexts, without certificates or network traffic."""
from __future__ import annotations

from pathlib import Path
import runpy
import ssl
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings

HELPER = Path(__file__).resolve().parents[2] / 'conf_backups/cachyos_hyprland_pleamar/source/vitreus/bin/vitreus-tvremote'


class TvTlsTests(unittest.TestCase):
    def connect(self, minimum: ssl.TLSVersion, port: int = 6466) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            context.minimum_version = minimum
        raw, wrapped = object(), object()
        function = runpy.run_path(str(HELPER))['connect_tls']

        def create_connection(address: tuple[str, int], *, timeout: int) -> object:
            self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
            self.assertEqual(address, ('tv.invalid', port))
            self.assertEqual(timeout, 8)
            return raw

        ssl_api = SimpleNamespace(SSLContext=lambda protocol: context,
                                  PROTOCOL_TLS_CLIENT=ssl.PROTOCOL_TLS_CLIENT,
                                  TLSVersion=ssl.TLSVersion, CERT_NONE=ssl.CERT_NONE)
        with mock.patch.dict(function.__globals__, {
            'ssl': ssl_api, 'socket': SimpleNamespace(create_connection=create_connection),
            'CERT': 'fixture-cert.pem', 'KEY': 'fixture-key.pem',
        }), mock.patch.object(context, 'load_cert_chain') as load, \
                mock.patch.object(context, 'wrap_socket', return_value=wrapped) as wrap:
            self.assertIs(function('tv.invalid', port), wrapped)
        load.assert_called_once_with('fixture-cert.pem', 'fixture-key.pem')
        wrap.assert_called_once_with(raw, server_hostname='tv.invalid')
        return context

    def test_old_runtime_minimum_is_raised_before_connecting(self) -> None:
        for minimum in (ssl.TLSVersion.MINIMUM_SUPPORTED, ssl.TLSVersion.TLSv1_1):
            for port in (6466, 6467):
                with self.subTest(minimum=minimum, port=port):
                    self.assertEqual(self.connect(minimum, port).minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_stricter_runtime_minimum_is_preserved(self) -> None:
        self.assertEqual(self.connect(ssl.TLSVersion.TLSv1_3).minimum_version, ssl.TLSVersion.TLSv1_3)

    def test_newer_tls_is_not_capped(self) -> None:
        context = self.connect(ssl.TLSVersion.TLSv1_2)
        self.assertEqual(context.maximum_version, ssl.TLSVersion.MAXIMUM_SUPPORTED)


if __name__ == '__main__':
    unittest.main()
