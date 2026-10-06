"""Native resize_divider action probe.

Fails on stock Kitty, passes once the ORS patch (Tab.resize_divider +
resize_divider parser) is applied to the installed package. Run from anywhere:
python3 -m unittest discover -s ~/.config/kitty/tests -p 'test_native*'
"""

import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, '/usr/lib/kitty')


class NativeResizeTest(unittest.TestCase):
    def test_splits_does_not_compute_unused_neighbors(self):
        from kitty.tabs import Tab

        class SplitsLayout:
            name = 'splits'

            def neighbors_for_window(self, window, windows):
                raise AssertionError('splits must not compute unused neighbors')

        for direction, increment, horizontal in (
            ('left', 6, True), ('right', -6, True),
            ('up', 6, False), ('down', -6, False),
        ):
            with self.subTest(direction=direction):
                calls = []
                tab = SimpleNamespace(
                    active_window=SimpleNamespace(id=23),
                    current_layout=SplitsLayout(),
                    windows=object(),
                    _nearest_split_side=lambda window_id, axis: 'two',
                    resize_window_by=lambda window_id, step, axis: calls.append(
                        (window_id, step, axis)) or None,
                )
                Tab.resize_divider(tab, direction)
                self.assertEqual(calls, [(23, increment, horizontal)])

    def test_non_splits_still_uses_neighbors(self):
        from kitty.tabs import Tab

        class OtherLayout:
            name = 'tall'
            queries = 0

            def neighbors_for_window(self, window, windows):
                self.queries += 1
                return {'left': [22]}

        layout = OtherLayout()
        calls = []
        tab = SimpleNamespace(
            active_window=SimpleNamespace(id=23),
            current_layout=layout,
            windows=object(),
            resize_window_by=lambda window_id, increment, horizontal: calls.append(
                (window_id, increment, horizontal)) or None,
        )
        Tab.resize_divider(tab, 'left')
        self.assertEqual(layout.queries, 1)
        self.assertEqual(calls, [(23, 6, True)])

    def test_parser_accepts_absolute_directions(self):
        from kitty.options.utils import parse_key_action
        for direction in ('left', 'right', 'up', 'down'):
            with self.subTest(direction=direction):
                action = parse_key_action('resize_divider {}'.format(direction))
                self.assertEqual(action.func, 'resize_divider')
                self.assertEqual(tuple(action.args), (direction,))

    def test_parser_rejects_garbage_direction(self):
        from kitty.options.utils import parse_key_action
        action = parse_key_action('resize_divider sideways')
        self.assertEqual(action.func, 'resize_divider')
        self.assertEqual(tuple(action.args), ('right',))

    def test_tab_has_resize_divider_action(self):
        from kitty.tabs import Tab
        self.assertTrue(callable(getattr(Tab, 'resize_divider', None)))


if __name__ == '__main__':
    unittest.main()
