#!/usr/bin/env python3
"""Tests for build.py and lint.py. Stdlib plus the markdown package (build only).

    python skills/html-deliverable/test_build_lint.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
import lint  # noqa: E402


SAMPLE_MD = """# The September record

A lead paragraph before any section, which becomes the Overview block.

## 1. Say publish tonight

- The three pages sit on disk, not on the workspace at https://workspace.example.com/dana-priya .
- Dana says one word.

## 2. Send Priya the short message

Two lines by text message. The record is at https://records.example.com/priya .

## The part with no number of its own

Body text.
"""

SAMPLE_CSV = """Month,Signups,Revenue
January,120,4200
February,145,5100
March,132,4780
"""


def build_page(tmp: Path, text: str, name: str, *args: str) -> Path:
    source = tmp / name
    source.write_text(text, encoding="utf-8")
    out = tmp / (source.stem + ".html")
    code = build.main([str(source), str(out), *args])
    assert code == 0, f"build returned {code}"
    return out


class BuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_markdown_report_has_every_required_part(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report", "--verdict", "One word does it.")
        html = out.read_text(encoding="utf-8")
        self.assertIn("<title>The September record</title>", html)
        self.assertIn('data-theme="light"', html)
        self.assertIn('<nav id="sidenav"', html)
        self.assertIn("Key links", html)
        self.assertIn("The short answer", html)
        self.assertNotIn("REPLACE", html)
        self.assertNotIn("{{", html)

    def test_source_numbers_are_kept_not_doubled(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        html = out.read_text(encoding="utf-8")
        self.assertIn('<div class="sec-num">1</div>', html)
        self.assertIn("<h2>Say publish tonight</h2>", html)
        self.assertNotIn("<h2>1. Say publish tonight</h2>", html)
        self.assertIn('<div class="sec-num">Overview</div>', html)

    def test_unnumbered_heading_gets_the_running_number(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        html = out.read_text(encoding="utf-8")
        self.assertIn("<h2>The part with no number of its own</h2>", html)
        self.assertIn('<div class="sec-num">3</div>', html)

    def test_links_are_harvested_into_the_table(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        html = out.read_text(encoding="utf-8")
        self.assertIn("workspace.example.com", html)
        self.assertIn("records.example.com", html)
        self.assertIn("Every destination named in this document", html)

    def test_one_link_means_no_links_table(self):
        single = "# One link\n\n## A section\n\nOnly https://example.com/a is named.\n"
        out = build_page(self.tmp, single, "one.md", "--surface", "report")
        self.assertNotIn("Key links", out.read_text(encoding="utf-8"))

    def test_deck_surface_drops_the_unfilled_action_table(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "deck")
        html = out.read_text(encoding="utf-8")
        self.assertIn("The agenda", html)
        self.assertIn("Live document", html)
        self.assertNotIn("REPLACE", html)
        self.assertNotIn("What happens next", html)

    def test_deck_action_table_appears_when_rows_are_given(self):
        out = build_page(
            self.tmp, SAMPLE_MD, "record.md", "--surface", "deck",
            "--action", "Send the plan|Dana|Friday|open",
            "--action", "Reply on price|Priya|Monday|blocked",
        )
        html = out.read_text(encoding="utf-8")
        self.assertIn("What happens next", html)
        self.assertIn('<td class="who">Dana</td>', html)
        self.assertIn('<span class="chip r">BLOCKED</span>', html)
        self.assertNotIn("{{", html)

    def test_poster_blocks_appear_when_filled(self):
        out = build_page(
            self.tmp, SAMPLE_MD, "record.md", "--surface", "poster",
            "--stat", "42 days|from kickoff to live",
            "--today", "Three systems, none of them talking",
            "--after", "One place to look",
            "--cta", "Start Monday|Reply with a yes and we book the kickoff.",
        )
        html = out.read_text(encoding="utf-8")
        self.assertIn("42 days", html)
        self.assertIn("<h3>Today</h3>", html)
        self.assertIn("Start Monday", html)
        self.assertNotIn("REPLACE", html)
        self.assertNotIn("{{", html)

    def test_unfilled_build_token_is_a_lint_failure(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        broken = out.read_text(encoding="utf-8").replace("<h2>Say publish tonight</h2>", "<h2>{{TITLE}}</h2>")
        failures, _, _ = lint.check(broken, money=False, allow_commands=False)
        self.assertTrue(any("build token" in f for f in failures), failures)

    def test_poster_surface_drops_every_unfilled_block(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "poster")
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("REPLACE", html)
        self.assertNotIn("bignum", html.split("<style>")[-1].split("</style>")[-1])
        # the maker's mark is one of those blocks now: no --mark, no mark, and no rule for it
        self.assertNotIn('class="mark"', html)
        self.assertNotIn(".mark{", html)

    def test_the_makers_mark_ships_only_when_it_is_asked_for(self):
        """No template carries a company name as a default value."""
        out = build_page(
            self.tmp, SAMPLE_MD, "mark.md", "--surface", "poster", "--mark", "Built by the studio"
        )
        html = out.read_text(encoding="utf-8")
        self.assertIn('<div class="mark">Built by the studio</div>', html)
        self.assertIn(".mark{", html)

    def test_csv_builds_kpis_a_fixed_height_chart_and_the_table(self):
        out = build_page(self.tmp, SAMPLE_CSV, "growth.csv", "--surface", "data-report")
        html = out.read_text(encoding="utf-8")
        self.assertIn('class="kpi', html)
        self.assertIn("397", html)  # 120 + 145 + 132 signups, summed honestly
        self.assertIn('class="chart-frame"', html)
        self.assertIn("height:280px", html)
        self.assertIn('data-label="February"', html)
        self.assertIn("<table class=\"dt data\"", html)
        self.assertNotIn("REPLACE", html)

    def test_json_list_behaves_like_a_csv(self):
        payload = '[{"name":"a","count":2},{"name":"b","count":5}]'
        out = build_page(self.tmp, payload, "rows.json", "--surface", "data-report")
        html = out.read_text(encoding="utf-8")
        self.assertIn("<td>a</td>", html)
        self.assertIn('class="kpi', html)

    def test_a_blank_cell_does_not_shift_the_chart_labels(self):
        gappy = "Month,Revenue\nJan,100\nFeb,\nMar,300\nApr,400\n"
        out = build_page(self.tmp, gappy, "gappy.csv", "--surface", "data-report")
        html = out.read_text(encoding="utf-8")
        self.assertIn('data-label="Jan" data-value="100 Revenue"', html)
        self.assertIn('data-label="Mar" data-value="300 Revenue"', html)
        self.assertIn('data-label="Apr" data-value="400 Revenue"', html)
        self.assertNotIn('data-label="Feb"', html)

    def test_a_year_column_is_never_summed_or_charted(self):
        yearly = "Year,Client,Conversion rate,Revenue\n2024,Acme,20%,1000\n2025,Beta,15%,2000\n2026,Gamma,20%,3000\n"
        out = build_page(self.tmp, yearly, "yearly.csv", "--surface", "data-report")
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("Year, summed", html)
        self.assertNotIn("6,075", html)
        self.assertIn("Revenue, summed over 3 rows", html)
        self.assertIn("Conversion rate, the latest of 3 rows", html)
        self.assertIn("<h2>Revenue across 3 rows</h2>", html)

    def test_a_quote_in_a_cell_cannot_break_out_of_an_attribute(self):
        quoted = 'Month,Revenue\n"Jan ""peak"" onsite",100\nFeb,200\n'
        out = build_page(self.tmp, quoted, "quoted.csv", "--surface", "data-report")
        html = out.read_text(encoding="utf-8")
        self.assertIn("&quot;peak&quot;", html)
        self.assertNotIn('data-label="Jan "peak"', html)

    def test_missing_input_returns_two(self):
        self.assertEqual(build.main([str(self.tmp / "nope.md"), str(self.tmp / "x.html")]), 2)

    def test_every_external_link_opens_in_a_new_tab(self):
        """The markdown renderer's links, the Key links table and pasted raw HTML alike."""
        source = SAMPLE_MD + (
            "\n## Raw markup the author pasted\n\n"
            '<p>A hand-written <a href="https://pasted.example.com/thing">destination</a>.</p>\n'
        )
        html = build_page(self.tmp, source, "tabs.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertEqual(lint.links_not_new_tab(html), [])
        for url in ("https://workspace.example.com/dana-priya", "https://pasted.example.com/thing"):
            self.assertIn(url, html)
        # and the in-page anchors the table of contents is built from stay in this tab
        self.assertIn('href="#', html)
        for tag in build.A_TAG_RE.finditer(html):
            href = build.HREF_ATTR_RE.search(tag.group(1))
            if href and href.group(1).startswith("#"):
                self.assertNotIn("_blank", tag.group(1), tag.group(0))

    def test_new_tab_rewrite_keeps_an_authors_own_rel_tokens(self):
        rewritten = build.new_tab_links(
            '<a class="x" rel="sponsored" href="https://example.com/a">a</a>'
            '<a href="https://example.com/b" target="_self">b</a>'
            '<a href="/internal">c</a><a href="#top">d</a>'
        )
        self.assertIn('rel="sponsored noopener noreferrer"', rewritten)
        self.assertIn('target="_blank"', rewritten)
        self.assertNotIn('target="_self"', rewritten)
        self.assertIn('<a href="/internal">c</a>', rewritten)
        self.assertIn('<a href="#top">d</a>', rewritten)
        self.assertEqual(rewritten, build.new_tab_links(rewritten))  # idempotent

    def test_nav_labels_cut_on_a_word_boundary(self):
        self.assertEqual(build.clip("short"), "short")
        clipped = build.clip("Two mobile fixes, found by looking at the page")
        self.assertTrue(clipped.endswith("…"))
        self.assertLessEqual(len(clipped), 26)
        self.assertFalse(clipped[:-1].endswith(" "))


class LintTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.page = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        self.html = self.page.read_text(encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def failures(self, html: str, **kwargs):
        options = {"money": False, "allow_commands": False}
        options.update(kwargs)
        return lint.check(html, **options)[0]

    def test_a_built_page_passes(self):
        self.assertEqual(self.failures(self.html), [])

    def test_em_dash_fails(self):
        failures = self.failures(self.html.replace("A lead paragraph", "A lead — paragraph"))
        self.assertTrue(any("em dash" in f for f in failures), failures)

    def test_mid_dot_fails(self):
        failures = self.failures(self.html.replace("A lead paragraph", "one · two · three"))
        self.assertTrue(any("mid dot" in f for f in failures), failures)

    def test_command_token_fails_and_allow_commands_clears_it(self):
        broken = self.html.replace("A lead paragraph", "Run python build.py to see it")
        self.assertTrue(any("terminal command" in f for f in self.failures(broken)), "expected a command failure")
        self.assertEqual(self.failures(broken, allow_commands=True), [])

    def test_digit_is_not_a_git_command(self):
        clean = self.html.replace("A lead paragraph", "We hit a six-digit month and double-digit growth")
        self.assertEqual(self.failures(clean), [])

    def test_a_real_command_still_fails(self):
        broken = self.html.replace("A lead paragraph", "Run git pull and then npm install")
        failures = self.failures(broken)
        self.assertTrue(any("terminal command" in f for f in failures), failures)

    def test_a_requested_render_that_cannot_run_is_a_failure(self):
        original_roots = lint.NODE_MODULE_ROOTS[:]
        original_python = lint.playwright_python
        try:
            lint.NODE_MODULE_ROOTS = [""]
            lint.playwright_python = lambda path, pattern, widths: None
            failures, _ = lint.playwright_check(self.page, None)
        finally:
            lint.NODE_MODULE_ROOTS = original_roots
            lint.playwright_python = original_python
        self.assertTrue(any("did NOT run" in f for f in failures), failures)

    def test_missing_links_table_fails(self):
        broken = self.html.replace("Key links", "Some links")
        self.assertTrue(any("Key links table" in f for f in self.failures(broken)))

    def test_an_external_link_without_a_new_tab_fails(self):
        for broken in (
            self.html.replace(' target="_blank" rel="noopener noreferrer"', "", 1),
            self.html.replace('rel="noopener noreferrer"', 'rel="noopener"', 1),
            self.html.replace('target="_blank" rel="noopener noreferrer"', 'rel="noopener noreferrer"', 1),
        ):
            failures = self.failures(broken)
            self.assertTrue(any("new tab" in f for f in failures), failures)

    def test_an_in_page_anchor_is_not_asked_to_open_a_new_tab(self):
        self.assertEqual(lint.links_not_new_tab('<a href="#summary">go</a><a href="notes.html">n</a>'), [])

    def test_missing_nav_fails(self):
        broken = lint.re.sub(r'<nav id="sidenav".*?</nav>', "", self.html, flags=lint.re.S)
        self.assertTrue(any("section nav" in f for f in self.failures(broken)))

    def test_dark_default_fails(self):
        broken = self.html.replace('data-theme="light"', 'data-theme="dark"', 1)
        self.assertTrue(any("data-theme" in f for f in self.failures(broken)))

    def test_prefers_color_scheme_fails(self):
        broken = self.html.replace("</style>", "@media (prefers-color-scheme: dark){body{background:#000}}</style>")
        self.assertTrue(any("prefers-color-scheme" in f for f in self.failures(broken)))

    def test_external_script_fails(self):
        broken = self.html.replace("</body>", '<script src="https://cdn.example.com/x.js"></script></body>')
        self.assertTrue(any("external script" in f for f in self.failures(broken)))

    def test_leftover_replace_fails(self):
        self.assertTrue(any("REPLACE" in f for f in self.failures(self.html.replace("Overview", "REPLACE"))))

    def test_ul_inside_p_fails(self):
        broken = self.html.replace("<h2>Say publish tonight</h2>", "<h2>x</h2><p>text<ul><li>a</li></ul></p>")
        self.assertTrue(any("<ul> inside a <p>" in f for f in self.failures(broken)))

    def test_money_placeholder_fails_and_real_money_does_not(self):
        # "$25,000 GBP", not "GBP 25,000": the sign goes first and the currency code after the
        # number on every page (TheMoneyRule in test_figure_gates.py proves the old shape is
        # refused).
        real = self.html.replace("A lead paragraph", "The invoice is $18,757.50 and $25,000 GBP staged")
        failures, notes, _ = lint.check(real, money=True, allow_commands=False)
        self.assertEqual(failures, [])
        self.assertTrue(any("18,757.50" in n and "$25,000" in n for n in notes), notes)
        placeholder = self.html.replace("A lead paragraph", "The invoice is $X,XXX")
        self.assertTrue(any("placeholder amount" in f for f in self.failures(placeholder, money=True)))

    def test_missing_file_returns_two(self):
        self.assertEqual(lint.main([str(self.tmp / "nope.html")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
