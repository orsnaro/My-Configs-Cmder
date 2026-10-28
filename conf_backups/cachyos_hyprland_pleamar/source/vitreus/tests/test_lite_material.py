"""Execute the compact material declarations with controlled shared scene facts."""
from __future__ import annotations

import re
import unittest

from test_lite_bars import LITE, ROOT


def bodies(source: str) -> list[dict[str, str]]:
    return [dict(re.findall(r'^ {12}(\w+): ([^\n]+)', match.group(1), re.M))
            for match in re.finditer(r'^ {8}body \{\n(.*?)^ {8}\}', source, re.M | re.S)]


def evaluate(expression: str, facts: dict[str, float | bool]) -> float | bool:
    expression = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1 / 100)', expression)
    return eval(expression.replace('false', 'False').replace('true', 'True'),
                 {'__builtins__': {}}, dict(facts, clamp=lambda v, a, b: max(a, min(b, v))))


def native_layers() -> list[dict[str, str]]:
    # v0.2.0 adds separate visualizer geometry variants; compare the six base material recipes.
    return [layer for layer in bodies((ROOT / 'pages/bar_glass.plm').read_text())
            if 'fw_act < 0.5' in layer.get('show', '')][:6]


class LiteMaterialTests(unittest.TestCase):
    def layers(self) -> list[dict[str, str]]:
        source = LITE.read_text()
        self.assertIn('component LiteMaterial(', source, 'compact surfaces need actual material layers, not a flat color')
        section = source.split('component LiteMaterial(', 1)[1].split('component LiteStrip(', 1)[0]
        layers = bodies(section)
        self.assertGreaterEqual(len(layers), 6)
        return layers[:6]

    def test_shared_material_controls_produce_the_native_layer_visibility_and_opacity(self) -> None:
        native = native_layers()
        compact = self.layers()
        cases = (
            ({'obs': 0}, (0,)),
            ({'obs': 0, 'glass_auto': True}, (1,)),
            ({'obs': .5}, (0, 3)),
            ({'obs': 1}, (2, 3)),
            ({'obs': 1, 'hy_blur': 0}, (2, 3)),
            ({'obs': 1, 'pk': 1, 'cas_k': 1}, (2, 3, 4)),
            ({'obs': 1, 'pk': 1, 'uwu_k': 1}, (2, 3, 5)),
        )
        for changes, expected in cases:
            facts: dict[str, float | bool] = dict(obs=0, glass_auto=False, glass_op=.38,
                                                hy_blur=4, pk=0, cas_k=0, uwu_k=0, pv=0, fw_act=0)
            facts.update(changes)
            with self.subTest(facts=changes):
                got = tuple(i for i, layer in enumerate(compact[:6]) if evaluate(layer['show'], facts))
                self.assertEqual(got, expected)
                for i in range(6):
                    for field in ('show', 'opacity'):
                        self.assertAlmostEqual(evaluate(compact[i][field], facts),
                                               evaluate(native[i][field], facts))

    def test_glass_parameters_follow_main_controls_instead_of_side_defaults(self) -> None:
        compact = self.layers()
        native = native_layers()
        facts: dict[str, float | bool] = dict(glass_bend=True, glass_clear=.27,
                                            glass_refr=.63, glass_disp=.42, glass_rim=1.4, pv=.2,
                                            glass_dome=.3, glass_milk=.2)
        for index in (0, 1):
            for field in ('glass', 'lens', 'refraction', 'dispersion', 'rim', 'dome', 'milk'):
                with self.subTest(layer=index, field=field):
                    self.assertAlmostEqual(evaluate(compact[index][field], facts),
                                           evaluate(native[index][field], facts))
        self.assertAlmostEqual(evaluate(compact[0]['frost'], facts), .27)
        self.assertEqual(compact[1]['frost'], 'auto')

    def test_material_transitions_return_to_glass_without_retaining_plastic_layers(self) -> None:
        compact = self.layers()
        states = ((0, 0, 0), (1, 1, 0), (1, 0, 1), (0, 0, 0))
        results: list[tuple[int, ...]] = []
        for obs, retro, uwu in states:
            facts: dict[str, float | bool] = dict(obs=obs, glass_auto=False, cas_k=retro, uwu_k=uwu)
            results.append(tuple(i for i, layer in enumerate(compact[:6]) if evaluate(layer['show'], facts)))
        self.assertEqual(results, [(0,), (2, 3, 4), (2, 3, 5), (0,)])


if __name__ == '__main__':
    unittest.main()
