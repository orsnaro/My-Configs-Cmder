"""The speaker dropdown is shared by the main bar and the two side strips.

The main bar already owns the Controls drawer and its mixer.  The side strips
are 36px layer surfaces, so their dropdown is a second small surface that
follows the existing mixer model instead of starting another service.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from test_lite_bars import Lite

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "vitreus.plm"
LITE = ROOT / "pages/lite_bars.plm"
LOGIC = ROOT / "vitreus.luau"


class VolumePopupTest(unittest.TestCase):
    def test_main_speaker_opens_the_existing_mixer_on_the_next_panel_change(self) -> None:
        source = SCENE.read_text()
        page = (ROOT / "pages/trial_status.plm").read_text()
        self.assertIn("fact mixer_on_open = false", source)
        self.assertRegex(
            page,
            r"on press trial_volume_hit \{[^}]*mixer_on_open = true;[^}]*panel = controls",
        )
        self.assertIn("vm_open = if(mixer_on_open and panel == controls, true, false)", source)
        self.assertIn(
            "on change mixer_on_open while mixer_on_open and panel == controls",
            source,
        )

    def test_side_popup_surfaces_are_pointer_only_and_follow_the_strip(self) -> None:
        source = LITE.read_text()
        self.assertIn("fact lite_vol_dp1 = false", source)
        self.assertIn("fact lite_vol_hdmi = false", source)
        for name, screen, left, side in (
            ("lite_vol_popup_dp1", "DP-1", 750, 0),
            ("lite_vol_popup_hdmi", "HDMI-A-2", 720, 1),
        ):
            with self.subTest(surface=name):
                block = re.search(r"surface " + name + r" \{(.*?)\n    \}", source, re.S)
                self.assertIsNotNone(block, f"missing {name}")
                assert block is not None
                body = block.group(1)
                self.assertIn(f'screens: "{screen}"', body)
                self.assertIn("keyboard: none", body)
                self.assertIn("level: overlay", body)
                self.assertIn(f"margin: 54, 0, 0, {left}", body)
                fact = "lite_vol_dp1" if side == 0 else "lite_vol_hdmi"
                self.assertIn(f"open: bar_lite_{'dp1' if side == 0 else 'hdmi'} and {fact}", body)
                self.assertIn(f"LiteVolumePanel(340, 320, {side})", body)

    def test_side_popups_close_with_escape_or_keyboard_loss(self) -> None:
        scene = SCENE.read_text()
        surface = re.search(r"^    surface \{([^\n]*)\}", scene, re.M)
        self.assertIsNotNone(surface)
        assert surface is not None
        line = surface.group(1)
        self.assertIn("lite_vol_dp1", line)
        self.assertIn("lite_vol_hdmi", line)
        for key in ("Escape", "Ctrl+w"):
            self.assertIn(
                f"on key {key} while lite_vol_dp1 or lite_vol_hdmi "
                "{ lite_vol_dp1 = false; lite_vol_hdmi = false }",
                scene,
            )

    def test_focus_changes_close_side_popups_like_the_main_drawer(self) -> None:
        logic = (ROOT / "logic/trial_status.luau").read_text()
        self.assertIn('on("fact:lite_vol_dp1", side_opened)', logic)
        self.assertIn('on("fact:lite_vol_hdmi", side_opened)', logic)
        self.assertIn("fact.lite_vol_dp1 = false", logic)
        self.assertIn("fact.lite_vol_hdmi = false", logic)

    def test_side_speaker_left_click_toggles_only_its_own_popup(self) -> None:
        source = LITE.read_text()
        self.assertIn("component LiteStrip(sw: number, side: number)", source)
        self.assertIn("LiteStrip(lite_dp1.width, 0)", source)
        self.assertIn("LiteStrip(lite_hdmi.width, 1)", source)
        self.assertRegex(
            source,
            r"on press lite_volume \{[^}]*lite_vol_dp1 = if\(side == 0, not lite_vol_dp1, false\)[^}]*lite_vol_hdmi = if\(side == 1, not lite_vol_hdmi, false\)",
        )
        self.assertIn("on press right lite_volume { emit trial_volume_toggle }", source)
        self.assertIn("on scroll lite_volume { emit trial_volume_wheel(wheel) }", source)
        self.assertIn("zone box lite_vol_close", source)

    def test_popup_reuses_the_mixer_and_the_existing_volume_event(self) -> None:
        source = LITE.read_text()
        self.assertIn("component LiteVolumePanel(sw: number, sh: number, side: number)", source)
        self.assertIn("component LiteMixRow(m: record, set: event, mute: event)", source)
        self.assertIn("LiteMixRow(m, set: mix_set, mute: mix_mute)", source)
        self.assertIn("emit setvol(clamp((pointer.x - 22) / 296, 0, 1))", source)
        self.assertIn("lite_vol_dp1 = false", source)
        self.assertIn("lite_vol_hdmi = false", source)
        self.assertNotIn("every(", source)
        self.assertNotIn("spawn(", source)
        self.assertNotIn("run(", source)

    def test_logic_polls_only_while_a_side_popup_is_open(self) -> None:
        source = LOGIC.read_text()
        self.assertIn('on("fact:lite_vol_dp1"', source)
        self.assertIn('on("fact:lite_vol_hdmi"', source)
        self.assertIn("M.side1", source)
        self.assertIn("M.side2", source)
        self.assertIn("M.open = M.main or M.side1 or M.side2", source)


class OutputSelectorGeometryTest(unittest.TestCase):
    """The output selector shares the existing 340 x 320 card with the mixer."""

    CARD = 320

    def geometry(self, mixer: int = 0) -> Lite:
        g = Lite(340)
        g.values.update({"mixer.count": mixer, "outlist.count": mixer})
        return g

    def test_the_current_output_row_sits_below_the_slider_and_above_the_mixer(self) -> None:
        g = self.geometry()
        row, mix = g.value("lo.row"), g.value("lo.mix")
        self.assertGreaterEqual(row - 14, 58 + 14)  # clear of the master slider's zone
        self.assertLessEqual(row + 14, mix)  # and above the first mixer row

    def test_the_open_list_hangs_under_the_row_that_opens_it(self) -> None:
        g = self.geometry()
        self.assertGreaterEqual(g.value("lo.list") - 6, g.value("lo.row") + 14)

    def test_all_six_devices_fit_the_card_and_the_mixer_never_leaves_it(self) -> None:
        for count in (0, 1, 2, 5, 6, 40):
            with self.subTest(mixer=count):
                g = self.geometry(count)
                self.assertGreaterEqual(g.value("lo.mixh"), 1)
                self.assertLessEqual(g.value("lo.mix") + g.value("lo.mixh"), self.CARD - 12)
        g = self.geometry(6)
        top, rh = g.value("lo.list"), g.value("lo.rh")
        self.assertEqual(rh, 30)
        self.assertLessEqual(top + 6 * rh, self.CARD - 12)

    def test_the_open_list_covers_the_mixer_instead_of_being_cut_by_it(self) -> None:
        g = self.geometry(6)
        list_bottom = g.value("lo.list") + 6 * g.value("lo.rh")
        self.assertLessEqual(g.value("lo.mix") + g.value("lo.mixh"), list_bottom + 6)


class OutputSelectorSourceTest(unittest.TestCase):
    """The selector reuses outlist/outname/pick_out and nothing of its own."""

    def setUp(self) -> None:
        self.source = LITE.read_text()
        block = re.search(r"component LiteVolumePanel\([^\n]*\n(.*?)\n    \}", self.source, re.S)
        self.assertIsNotNone(block, "missing the shared side volume panel")
        assert block is not None
        self.panel = block.group(1)

    def test_the_panel_draws_the_outputs_it_is_given(self) -> None:
        self.assertIn("component LiteOutRow(o: record, pick: event)", self.source)
        self.assertIn("for o in outlist { LiteOutRow(o, pick: pick_out) }", self.panel)
        self.assertIn("emit pick(o.index)", self.source)
        self.assertIn("text outname", self.panel)
        self.assertIn("if(o.current, 100%, 0%)", self.source)  # the active device's dot

    def test_the_list_opens_from_its_row_and_closes_after_a_choice(self) -> None:
        self.assertIn("show: lv_out", self.panel)
        self.assertIn("on press lvo { toggle lv_out }", self.panel)
        self.assertIn("on pick_out { lv_out = false }", self.panel)
        self.assertIn("on change lite_vol_dp1 while not lite_vol_dp1 { lv_out = false }", self.panel)
        self.assertIn("on change lite_vol_hdmi while not lite_vol_hdmi { lv_out = false }", self.panel)

    def test_an_empty_model_falls_back_and_a_long_name_stays_inside(self) -> None:
        self.assertIn('text "No output"', self.panel)
        self.assertIn("show: outlist.count < 1", self.panel)
        name = re.search(r"text outname \{([^\n]+)", self.panel)
        self.assertIsNotNone(name, "the current device's name must be drawn in the card")
        assert name is not None
        at = re.search(r"at: ([\d.]+),", name.group(1))
        width = re.search(r"width: ([\d.]+);", name.group(1))
        self.assertIsNotNone(at)
        self.assertIsNotNone(width)
        assert at is not None and width is not None
        self.assertIn("lines: 1", name.group(1))
        self.assertLessEqual(float(at.group(1)) + float(width.group(1)), 340 - 24)

    def test_the_selector_adds_no_service_event_or_surface_of_its_own(self) -> None:
        for forbidden in ("service ", "every(", "spawn(", "run("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)
        self.assertEqual(self.source.count("LiteVolumePanel(340, 320,"), 2)


if __name__ == "__main__":
    unittest.main()
