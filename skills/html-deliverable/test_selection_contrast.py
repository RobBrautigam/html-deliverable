"""Selected text reads on every block, in every look and both modes.

The template's selection was --acc-soft, the callouts' and code's own ground: 1.0:1 inside one, so
text highlighted inside a tinted callout was the same color as the callout.

What this file holds:

1. THE TEMPLATE'S RULE reads on every reading block of the classic look, the tint look and Dark mode.
2. THE LINT REFUSES THE OLD RULE (the planted case, seen red first): the template with its old
   `::selection{background:var(--acc-soft)}` fails `lint.selection_findings`, naming the callout.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lint  # noqa: E402
import selection_contrast as sc  # noqa: E402

TEMPLATE = HERE / "template.html"
NEW_RULE = "::selection{background:var(--ink); color:var(--panel)}"
OLD_RULE = "::selection{background:var(--acc-soft); color:var(--acc-ink)}"


def template(look: str = "") -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    if look:
        assert 'data-look="classic"' in html
        html = html.replace('data-look="classic"', f'data-look="{look}"', 1)
    return html


class TemplateRule(unittest.TestCase):
    def test_the_rule_is_the_ink_inverted(self):
        html = template()
        self.assertIn(NEW_RULE, html)
        self.assertIn(NEW_RULE.replace("::selection", "::-moz-selection"), html)
        self.assertNotIn(OLD_RULE, html)

    def test_it_reads_in_every_look_and_both_modes(self):
        for look in ("", "tint"):
            with self.subTest(look=look or "classic"):
                report = sc.page_report(template(look))
                self.assertEqual(report.modes, ["light", "dark"])
                self.assertTrue(report.readable, [f.line() for f in report.findings] + report.unmeasured)
                self.assertEqual(lint.selection_findings(template(look)), [])

    def test_the_components_gallery_carries_it_too(self):
        html = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertTrue(sc.page_report(html).readable)


class PlantedCase(unittest.TestCase):
    def test_the_old_rule_is_refused_on_the_callout(self):
        for look, callout in (("", "#f3e9d4"), ("tint", "#e4f1f6")):
            with self.subTest(look=look or "classic"):
                bad = template(look).replace(NEW_RULE, OLD_RULE)
                found = lint.selection_findings(bad)
                self.assertTrue(found, "the planted page passed")
                self.assertTrue(any(".callout" in f and callout in f for f in found), found)

    def test_a_page_with_no_selection_rule_keeps_the_browsers(self):
        bare = template().replace(NEW_RULE, "").replace(NEW_RULE.replace("::selection", "::-moz-selection"), "")
        self.assertEqual(lint.selection_findings(bare), [])


if __name__ == "__main__":
    unittest.main()
