"""Contracts for the trial bar: absent measurements must not look like zero."""
from __future__ import annotations

from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TrialStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        helper = ROOT / 'bin/vitreus-trial-status'
        self.assertTrue(helper.exists(), 'trial status helper has not been implemented')
        self.api = runpy.run_path(str(helper))

    def status(self, **overrides: object) -> dict[str, str]:
        inputs = dict(before=(100, 200), after=(125, 300),
                      mem={'used': 4 * 1024**2, 'total': 16 * 1024**2},
                      gpu={'util': 42, 'mem_used': 2048, 'mem_total': 8192},
                      weather={'temp_c': 24}, pomo={'text': 'Focus 24:59'},
                      updates='a\n\nb\n  \n', keyboard='English (US)\n',
                      now=1000.0, pomo_mtime=999.0)
        inputs.update(overrides)
        return self.api['build_status'](**inputs)

    def test_cpu_is_busy_delta_over_total_delta(self) -> None:
        self.assertEqual(self.status()['cpu'], 'CPU 25%')

    def test_cpu_counter_reset_is_unavailable(self) -> None:
        self.assertEqual(self.status(after=(1, 2))['cpu'], 'CPU —')

    def test_ram_kib_and_vram_mib_are_not_confused(self) -> None:
        self.assertEqual(self.status()['ram'], 'MEM 4.0 GiB')
        self.assertEqual(self.status()['vram'], 'VMEM 2.0 GiB')
        self.assertEqual(self.status()['gpu'], 'GPU 42%')

    def test_absent_gpu_never_reports_zero_usage(self) -> None:
        self.assertEqual(self.status(gpu=None)['gpu'], 'GPU —')
        self.assertEqual(self.status(gpu=None)['vram'], 'VMEM —')

    def test_zero_totals_and_nonfinite_values_are_unavailable(self) -> None:
        result = self.status(mem={'used': 0, 'total': 0},
                             gpu={'util': float('nan'), 'mem_used': 0, 'mem_total': 0})
        self.assertEqual(result['ram'], 'MEM —')
        self.assertEqual(result['gpu'], 'GPU —')
        self.assertEqual(result['vram'], 'VMEM —')

    def test_malformed_cache_values_do_not_crash_or_invent_measurements(self) -> None:
        result = self.status(weather=[], pomo={'text': []}, keyboard='', updates=None)
        self.assertEqual(result['weather'], 'Weather —')
        self.assertEqual(result['pomo'], 'Pomo idle')
        self.assertEqual(result['keyboard'], '—')
        self.assertEqual(result['updates'], '—')

    def test_cached_updates_count_only_nonblank_lines(self) -> None:
        self.assertEqual(self.status()['updates'], '2')

    def test_zero_usage_remains_valid_and_over_capacity_is_unavailable(self) -> None:
        self.assertEqual(self.status(mem={'used': 0, 'total': 1024})['ram'], 'MEM 0.0 GiB')
        self.assertEqual(self.status(mem={'used': 2048, 'total': 1024})['ram'], 'MEM —')
        self.assertEqual(self.status(mem={'used': float('inf'), 'total': 1024})['ram'], 'MEM —')

    def test_keyboard_maps_known_layout_names_to_short_text(self) -> None:
        for raw, expected in [('English (US)\n', 'US'), ('us', 'US'), ('en', 'US'),
                              ('Arabic', 'AR'), ('ar\n', 'AR'), ('Arabic (Egypt)', 'AR'),
                              ('unknown', '—'), ('', '—')]:
            with self.subTest(raw=raw):
                self.assertEqual(self.status(keyboard=raw)['keyboard'], expected)

    def test_existing_hypr_weather_cache_uses_temp_field(self) -> None:
        self.assertEqual(self.status(weather={'temp': 22, 'code': 1, 'day': 0})['weather'], '22°C')

    def test_weather_symbol_tracks_cached_condition_and_daylight(self) -> None:
        fixtures = [
            (0, 1, 'sunny'), (0, 0, 'clear_night'), (1, 1, 'sunny'),
            (2, 1, 'partly_cloudy_day'), (2, 0, 'partly_cloudy_night'),
            (3, 0, 'cloud'), (45, 1, 'foggy'), (48, 1, 'foggy'),
            (51, 1, 'rainy'), (61, 0, 'rainy'), (67, 0, 'rainy'),
            (71, 1, 'weather_snowy'), (77, 0, 'weather_snowy'),
            (80, 1, 'rainy'), (86, 1, 'weather_snowy'), (99, 0, 'thunderstorm'),
        ]
        for code, day, symbol in fixtures:
            with self.subTest(code=code, day=day):
                self.assertEqual(self.status(weather={'temp': 21, 'code': code, 'day': day})['weather_icon'], symbol)

    def test_unknown_weather_does_not_invent_a_clear_condition(self) -> None:
        for weather in [None, [], {}, {'temp': 21}, {'code': 0, 'day': 1},
                        {'temp': 21, 'code': True, 'day': 1},
                        {'temp': 21, 'code': float('nan'), 'day': 1},
                        {'temp': 21, 'code': 61.5, 'day': 1},
                        {'temp': 21, 'code': 999, 'day': 1}]:
            with self.subTest(weather=weather):
                self.assertEqual(self.status(weather=weather)['weather_icon'], 'cloud_off')
        self.assertEqual(self.status(weather={'temp': 21, 'code': 0})['weather_icon'], 'cloud')

    def test_dead_pomo_does_not_leave_frozen_countdown(self) -> None:
        self.assertEqual(self.status(pomo_mtime=900.0)['pomo'], 'Pomo idle')

    def test_keyboard_and_weather_are_bounded_display_strings(self) -> None:
        result = self.status(keyboard='English\nBAD\x00' + 'x' * 100)
        self.assertEqual(result['weather'], '24°C')
        self.assertLessEqual(len(result['keyboard']), 22)
        self.assertNotIn('\n', result['keyboard'])


if __name__ == '__main__':
    unittest.main()
