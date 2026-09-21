#!/usr/bin/env python3
"""Tests for the figure gates, the money rule, and four lessons the lint learned.

    python -m pytest skills/html-deliverable/test_figure_gates.py

Two layers, the same shape the diagram tests use. The unit layer runs anywhere and reads the
finished markup; the render layer drives a headless browser and SKIPS with a named reason when
playwright is not on the machine, because a skill that refuses to run its own tests on a fresh
checkout is a skill nobody keeps green.

EVERY GATE HERE IS PROVED BY INVERSION. A rule with no page that breaks it is a rule nobody has
seen fire, which is exactly how `parts_without_a_card` first shipped silent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import build_gallery  # noqa: E402
import lint  # noqa: E402

FIXTURES = HERE / "fixtures"
INVERSIONS = FIXTURES / "figure-inversions"


def playwright_available() -> str:
    """"" when a render can run, otherwise the reason to skip."""
    try:
        import playwright.sync_api  # noqa: F401
        return ""
    except ImportError:
        pass
    for root in lint.NODE_MODULE_ROOTS:
        if root and (Path(root) / "playwright").is_dir():
            return ""
    return "no playwright: neither the python package nor a node module root"


def render_lint(path: Path, widths: str = "1440") -> list[str]:
    """The lint's failures for one page, with the render on. Raises SkipTest without playwright."""
    reason = playwright_available()
    if reason:
        raise unittest.SkipTest(reason)
    html = path.read_text(encoding="utf-8-sig")
    failures, _, _ = lint.check(html, money=False, allow_commands=True, allow_no_grips=True)
    more, _ = lint.playwright_check(path, None, [int(w) for w in widths.split(",")])
    return failures + more


class FigureGateInversions(unittest.TestCase):
    """One fixture per rule, each breaking exactly that rule, each refused BY NAME."""

    def assert_refused(self, fixture: str, phrase: str) -> None:
        failures = render_lint(INVERSIONS / fixture)
        joined = " | ".join(failures)
        self.assertIn(phrase, joined, f"{fixture} was not refused for {phrase!r}: {joined[:400]}")

    def test_a_figure_that_drew_nothing_is_refused_both_ways(self):
        failures = render_lint(INVERSIONS / "drew-nothing.html")
        joined = " | ".join(failures)
        self.assertIn("no <svg> in the figure", joined)
        self.assertIn("carries zero nodes", joined)

    def test_a_superseded_renderer_is_named_and_the_page_is_sent_back_to_the_builder(self):
        self.assert_refused("superseded-renderer.html", "superseded copy of the flow renderer")

    def test_a_figure_wider_than_its_column_is_refused(self):
        self.assert_refused("figure-wider-than-container.html", "wider than the column it sits in")

    def test_text_outside_its_box_is_refused_and_the_message_names_the_pixels(self):
        failures = render_lint(INVERSIONS / "text-outside-its-box.html")
        joined = " | ".join(failures)
        self.assertIn("draws text outside the box it belongs to", joined)
        self.assertIn("long-program-name-host", joined)
        self.assertIn("px over", joined)

    def test_a_label_under_a_shape_that_covers_it_is_refused(self):
        self.assert_refused("label-under-a-node.html", "paints a label under a shape that covers it")

    def test_a_connector_through_a_node_is_refused_and_the_message_names_both(self):
        failures = render_lint(INVERSIONS / "connector-through-node.html")
        joined = " | ".join(failures)
        self.assertIn("routes a connector through a node", joined)
        self.assertIn("node second", joined)
        self.assertIn("edge first-third", joined)


class TheRepairedRendererDrawsClean(unittest.TestCase):
    """The fixture whose JSON never changes. Before the repair it produced 44 findings."""

    def build_fixture(self, destination: Path) -> Path:
        result = subprocess.run(
            [sys.executable, str(HERE / "build.py"), str(FIXTURES / "flow-broken.md"),
             str(destination)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr[:400])
        return destination

    def test_the_broken_fixture_renders_clean_at_every_width_in_both_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.build_fixture(Path(tmp) / "flow.html")
            failures = render_lint(page, widths="1440,1920,390")
        figure = [f for f in failures if f.startswith("the figure")]
        self.assertEqual(figure, [], "the repaired fixture still has a figure defect")

    def test_one_column_under_a_phone_width_and_no_sideways_scroll(self):
        reason = playwright_available()
        if reason:
            self.skipTest(reason)
        with tempfile.TemporaryDirectory() as tmp:
            page = self.build_fixture(Path(tmp) / "flow.html")
            more, notes = lint.playwright_check(page, None, [390])
        self.assertEqual([f for f in more if "overflow" in f], [])
        self.assertEqual([f for f in more if f.startswith("the figure")], [])

    def test_the_renderer_marks_every_part_it_draws(self):
        """The lint measures against a CONTRACT. Without these classes it cannot measure at all."""
        component = {c.cid: c for c in build_gallery.COMPONENTS}["flow"]
        for marker in ("flow-node", "flow-edge", "flow-label", "flow-note",
                       "flow-lane", "flow-lane-label", "flow-mark", "flow-mark-label"):
            self.assertIn(marker, component.js, f"the renderer never writes {marker}")
        self.assertIn("data-node", component.js)
        self.assertIn("data-edge", component.js)

    def test_the_renderer_measures_text_rather_than_counting_characters(self):
        component = {c.cid: c for c in build_gallery.COMPONENTS}["flow"]
        self.assertIn("getComputedTextLength", component.js,
                      "a character count is not a width, and never was")
        self.assertNotIn("wrap(item.label, 16, 2)", component.js)

    def test_the_gutter_comes_from_the_longest_lane_label(self):
        component = {c.cid: c for c in build_gallery.COMPONENTS}["flow"]
        self.assertIn("laneLabelW", component.js)
        self.assertIn("GUTTER_MAX_SHARE", component.js,
                      "past a share of the figure the label moves above its band")

    def test_two_nodes_in_one_cell_are_stacked_rather_than_drawn_on_top_of_each_other(self):
        component = {c.cid: c for c in build_gallery.COMPONENTS}["flow"]
        self.assertIn("CELL_GAP", component.js)
        self.assertIn("laneDepth", component.js)


class TheMoneyRule(unittest.TestCase):
    """Every dollar amount carries a dollar sign, in prose, tables, cards and figures."""

    def failures_for(self, name: str) -> str:
        html = (FIXTURES / name).read_text(encoding="utf-8")
        failures, _, _ = lint.check(html, money=True, allow_commands=True, allow_no_grips=True)
        return " | ".join(failures)

    def test_all_three_arms_fire_on_the_page_that_breaks_them(self):
        joined = self.failures_for("money-without-signs.html")
        self.assertIn("10,298.92 dollars", joined, "arm 1: the prose calls it dollars")
        self.assertIn('the column "Amount"', joined, "arm 2: a header that names money")
        self.assertIn("the same amount written two ways", joined, "arm 3: the page's own token")

    def test_the_same_page_written_correctly_passes_and_a_count_column_is_left_alone(self):
        joined = self.failures_for("money-with-signs.html")
        self.assertNotIn("dollar sign", joined, joined[:300])
        self.assertNotIn("Receipts", joined, "a count column is not a money column")

    def test_a_marked_amount_is_never_reported_as_its_own_bare_copy(self):
        """GBP 25,000 matched its own numeral and was reported unsigned. The suite caught it."""
        html = "<html><body><p>The engagement is GBP 25,000 in total.</p></body></html>"
        failures, _, _ = lint.check(html, money=True, allow_commands=True, allow_no_grips=True)
        self.assertEqual([f for f in failures if "dollar sign" in f], [])

    # ARM 4: the two-currency format. The sign first, the currency after the number.

    def money_failures(self, fragment: str) -> list[str]:
        html = f"<html><body>{fragment}</body></html>"
        failures, _, _ = lint.check(html, money=True, allow_commands=True, allow_no_grips=True)
        return [f for f in failures if "sign" in f or "currency code" in f]

    def test_a_currency_code_before_the_number_is_refused(self):
        for bad in ("MXN 1,213.06", "USD 17.00", "GBP 25,000", "EUR 1,200", "MXN$1,213.06"):
            failures = self.money_failures(f"<p>The fan cost {bad} last year.</p>")
            self.assertEqual(len(failures), 1, (bad, failures))
            self.assertIn("puts the currency code before the number", failures[0])

    def test_a_number_followed_by_a_code_with_no_sign_is_refused(self):
        for bad in ("1,213.06 MXN", "25,000 EUR", "17.00 MXN"):
            failures = self.money_failures(f"<p>The fan cost {bad} last year.</p>")
            self.assertEqual(len(failures), 1, (bad, failures))
            self.assertIn("written without its $ sign", failures[0])

    def test_the_two_currency_format_passes_in_prose_and_in_a_table(self):
        page = (
            "<p>The office spend is $1,403.81 USD and $10,422.65 MXN, never added together.</p>"
            "<table><tr><th>Year</th><th>Currency</th><th>Business total</th></tr>"
            "<tr><td>2024</td><td>USD</td><td>$1,403.81 USD</td></tr>"
            "<tr><td>2024</td><td>MXN</td><td>$10,422.65 MXN</td></tr></table>"
        )
        self.assertEqual(self.money_failures(page), [])

    def test_a_signed_amount_is_never_read_from_its_own_tail(self):
        """"$1,249.99 USD" was reported as "249.99 USD" without a sign: the lookbehind let the
        second alternative start after the comma."""
        self.assertEqual(self.money_failures("<p>The laptop was $1,249.99 USD.</p>"), [])
        self.assertEqual(self.money_failures("<p>Total charged $1,428.87 USD.</p>"), [])

    def test_a_bare_amount_inside_a_money_figure_fails(self):
        """The figure's words live in a script block, which the prose scan strips."""
        figure = {
            "title": "Where every dollar goes",
            "lanes": [{"id": "a", "label": "THE MONEY"}],
            "nodes": [
                {"id": "all", "col": 0, "lane": "a", "label": "240,707 out", "note": "1,163 rows"},
                {"id": "x", "col": 1, "lane": "a", "label": "14,264 in the database"},
            ],
            "edges": [],
        }
        html = (
            '<figure class="flow"><script type="application/json" class="flow-data">'
            + json.dumps(figure) + "</script></figure>"
        )
        hits = " | ".join(lint.money_in_figures(html))
        self.assertIn("240,707 out", hits)
        self.assertIn("14,264 in the database", hits)
        self.assertNotIn("1,163 rows", hits, "a row count is not an amount")

    def test_a_figure_that_is_not_about_money_is_left_alone(self):
        figure = {
            "title": "What one session puts on the machine",
            "lanes": [{"id": "a", "label": "YOU RUN"}],
            "nodes": [{"id": "n", "col": 0, "lane": "a", "label": "708 processes"}],
            "edges": [],
        }
        html = (
            '<figure class="flow"><script type="application/json" class="flow-data">'
            + json.dumps(figure) + "</script></figure>"
        )
        self.assertEqual(lint.money_in_figures(html), [])


class TheDollarSignSurvivesTheDiagramEngine(unittest.TestCase):
    """d2 reads `$` as a variable substitution and refuses to compile without one."""

    def test_a_plain_dollar_is_escaped_and_a_substitution_is_not(self):
        self.assertEqual(build.escape_d2_dollars('a: "Costs $1,000"'), 'a: "Costs \\$1,000"')
        self.assertEqual(build.escape_d2_dollars('b: "${x}"'), 'b: "${x}"')
        self.assertEqual(build.escape_d2_dollars('c: "already \\$5"'), 'c: "already \\$5"')

    def test_a_flowchart_carrying_dollar_amounts_compiles_and_keeps_its_signs(self):
        spec = build.DIAGRAM_KINDS["flowchart"]
        try:
            build.diagram_binary("d2", spec["engine"])
        except SystemExit as missing:
            self.skipTest(str(missing)[:120])
        svg = build.run_engine("flowchart", 'a: "Spend $14,264"\nb: "List $10,298.92"\na -> b\n', "t")
        self.assertIn("$14,264", svg)
        self.assertIn("$10,298.92", svg)


class TheFourOwedLessons(unittest.TestCase):

    def test_markdown_inside_a_raw_html_block_is_refused(self):
        html = (FIXTURES / "markdown-in-raw-html.html").read_text(encoding="utf-8")
        failures, _, _ = lint.check(html, money=False, allow_commands=True, allow_no_grips=True)
        joined = " | ".join(failures)
        self.assertIn("literal Markdown bold reached the page", joined)
        self.assertIn("pipe table", joined)

    def test_a_page_written_in_real_html_is_left_alone(self):
        html = (
            '<html><body><details class="fold" data-fold="x"><summary>s</summary>'
            '<div class="fold-body"><p><b>The Agent API call</b> came in under its ceiling.</p>'
            "<table><tr><td>Search</td><td>sonar</td></tr></table></div></details></body></html>"
        )
        failures, _, _ = lint.check(html, money=False, allow_commands=True, allow_no_grips=True)
        self.assertEqual([f for f in failures if "Markdown" in f or "pipe table" in f], [])

    def test_a_component_in_the_markup_without_its_assets_is_refused(self):
        html = (FIXTURES / "component-without-assets.html").read_text(encoding="utf-8")
        failures, _, _ = lint.check(html, money=False, allow_commands=True, allow_no_grips=True)
        joined = " | ".join(failures)
        self.assertIn("uses the `flow` component", joined)
        self.assertIn("not evidence its assets shipped", joined)

    def test_a_real_build_carries_the_assets_of_every_component_it_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "flow.html"
            subprocess.run(
                [sys.executable, str(HERE / "build.py"), str(FIXTURES / "flow-broken.md"),
                 str(page)],
                capture_output=True, text=True, check=True,
            )
            failures, _, _ = lint.check(page.read_text(encoding="utf-8"), money=False,
                                        allow_commands=True, allow_no_grips=True)
        self.assertEqual([f for f in failures if "assets shipped" in f], [])

    def test_an_unknown_stat_tone_is_refused_rather_than_rendered_neutral(self):
        with self.assertRaises(SystemExit) as raised:
            build.hero_stat_cards(["47 | pages built | green"])
        self.assertIn("which is not a tone", str(raised.exception))
        self.assertIn("one letter", str(raised.exception))

    def test_the_four_real_tones_and_an_empty_one_still_build(self):
        for tone in ("g", "a", "r", "n", ""):
            card = build.hero_stat_cards([f"47 | pages built | {tone}".strip(" |")])
            self.assertIn("47", card)

    def test_skill_md_carries_the_dollar_sign_line_and_the_names_nobody_line(self):
        skill = (HERE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("every dollar amount carries a dollar sign", skill.lower())
        self.assertIn("names nobody", skill.lower())


if __name__ == "__main__":
    unittest.main()
