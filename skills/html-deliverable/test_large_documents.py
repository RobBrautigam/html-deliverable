#!/usr/bin/env python3
"""Tests for the large-document pass.

Two defects a reader named on a 38-section audit page, reproduced here as failing tests before
either was fixed:

1. **The nav ran off the screen.** A 38-section document produced a 40-entry flat rail measuring
   1394px in a 900px viewport, so the top and the bottom of the rail were both off screen and the
   page had to be zoomed to 50 percent to read it.
2. **A part heading was stranded at the foot of the previous section.** The source wrote its six
   parts as level-1 headings and its sections as level-2, and the splitter only knew about level 2,
   so every part heading landed as the last child of the card before it.

The rendered measurements need a browser, so those tests skip when neither Playwright binding is
reachable. The structural tests need nothing.

    python -m pytest skills/html-deliverable/test_large_documents.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import lint  # noqa: E402


# --------------------------------------------------------------------------- fixtures


def _forty_section_markdown() -> str:
    """Forty sections under six part headings: the shape of the audit page that failed.

    Part headings are level 1 and carry their own numbers, exactly as the audit source wrote them.
    """
    parts = [
        ("1. The inbox, seen whole", ["What this read covers", "What this read cannot see",
                                      "Every conversation waiting on you", "What the earlier triage got wrong"]),
        ("2. Claim one: client-facing emails are switched off",
         ["The claim, with who said it and when", "The evidence", "When it was switched off, and by whom",
          "Whether any client email has gone out", "What switching it on would send tomorrow",
          "The verdict on claim one", "The root cause of claim one", "The fix options for claim one"]),
        ("3. Claim two: the numbers are not reaching the portal",
         ["Who said it and when", "The pipeline, end to end", "The three campaigns",
          "The numbers, per client, three ways", "Why the clip list is frozen",
          "Why the report shows nothing at all", "The verdict on claim two", "The root cause of claim two"]),
        ("4. Everything else in the inbox",
         ["The launch message", "The partner thread", "The finance pack",
          "The funding thread", "The four asks the triage never saw"]),
        ("5. The drafts", [f"Draft {n}, the reply that is ready" for n in range(1, 12)]),
        ("6. What was done, and what was not", ["What was read", "What was written", "What was never touched",
                                                "What is owed next"]),
    ]
    out = ["# The forty section record", "", "A lead paragraph before any part, which becomes the Overview block.", ""]
    for part_label, sections in parts:
        out += [f"# {part_label}", "", "One sentence introducing the part it heads.", ""]
        for section in sections:
            out += [f"## {section}", "", f"Body copy for {section.lower()}, long enough to be a real block.", ""]
    return "\n".join(out) + "\n"


FORTY_SECTION_MD = _forty_section_markdown()

FLAT_FOURTEEN_MD = "# A flat record\n\nA lead paragraph.\n\n" + "".join(
    f"## Section number {n}\n\nBody copy for section {n}.\n\n" for n in range(1, 15)
)


def build_page(tmp: Path, text: str, name: str, *args: str) -> Path:
    source = tmp / name
    source.write_text(text, encoding="utf-8")
    out = source.with_suffix(".html")
    code = build.main([str(source), str(out), *args])
    assert code == 0, f"build.py exited {code}"
    return out


# --------------------------------------------------------------------------- the browser


MEASURE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);
  const m = await page.evaluate(() => {
    const nav = document.getElementById('sidenav');
    if (!nav) return { nav: false };
    const r = nav.getBoundingClientRect();
    const buttons = [].slice.call(nav.querySelectorAll('button'));
    const shown = buttons.filter(b => b.offsetParent !== null);
    return {
      nav: true,
      top: r.top, bottom: r.bottom, height: r.height,
      viewport: window.innerHeight,
      scrollHeight: nav.scrollHeight, clientHeight: nav.clientHeight,
      overflowY: getComputedStyle(nav).overflowY,
      buttons: buttons.length, shown: shown.length,
      reachable: shown.every(b => {
        const br = b.getBoundingClientRect();
        return br.top >= r.top - 1 && br.bottom <= r.bottom + 1;
      }),
    };
  });
  console.log(JSON.stringify(m));
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


def measure_nav(path: Path) -> dict | None:
    """The rendered nav at 1440x900, or None when no Playwright binding is reachable."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        sync_playwright = None  # type: ignore
    if sync_playwright is not None:
        with sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(path.resolve().as_uri())
            page.wait_for_timeout(400)
            result = page.evaluate(_MEASURE_EXPRESSION)
            browser.close()
        return result
    root = next((r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir()), None)
    if root is None:
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "measure.js"
        script.write_text(MEASURE_JS, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), path.resolve().as_uri()],
            capture_output=True, text=True, timeout=180,
        )
    if result.returncode != 0:
        raise AssertionError(f"the measurement did not run: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


_MEASURE_EXPRESSION = """() => {
  const nav = document.getElementById('sidenav');
  if (!nav) return { nav: false };
  const r = nav.getBoundingClientRect();
  const buttons = [].slice.call(nav.querySelectorAll('button'));
  const shown = buttons.filter(b => b.offsetParent !== null);
  return {
    nav: true, top: r.top, bottom: r.bottom, height: r.height,
    viewport: window.innerHeight, scrollHeight: nav.scrollHeight, clientHeight: nav.clientHeight,
    overflowY: getComputedStyle(nav).overflowY, buttons: buttons.length, shown: shown.length,
    reachable: shown.every(b => {
      const br = b.getBoundingClientRect();
      return br.top >= r.top - 1 && br.bottom <= r.bottom + 1;
    }),
  };
}"""


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# --------------------------------------------------------------------------- defect one: the nav


class NavFitsTheViewport(TempCase):
    """A nav taller than the screen is an unusable page."""

    def test_the_rendered_nav_fits_inside_a_900px_viewport(self):
        page = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report", "--look", "tint")
        measured = measure_nav(page)
        if measured is None:
            self.skipTest("no playwright binding reachable")
        self.assertTrue(measured["nav"], "the page has no section nav at all")
        self.assertLessEqual(
            measured["height"], measured["viewport"],
            f"the nav renders {measured['height']:.0f}px tall in a {measured['viewport']}px viewport: "
            "this is the defect the reader had to zoom out to 50 percent to read",
        )
        self.assertGreaterEqual(measured["top"], 0, "the nav starts above the top of the screen")
        self.assertLessEqual(measured["bottom"], measured["viewport"], "the nav ends below the bottom of the screen")

    def test_every_visible_nav_entry_is_reachable_without_zooming(self):
        page = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report", "--look", "tint")
        measured = measure_nav(page)
        if measured is None:
            self.skipTest("no playwright binding reachable")
        self.assertTrue(
            measured["reachable"],
            "a nav entry sits outside the nav's own box, so it cannot be clicked without zooming out",
        )
        if measured["scrollHeight"] > measured["clientHeight"]:
            self.assertIn(
                measured["overflowY"], {"auto", "scroll"},
                "the nav is taller than its box and does not scroll: the overflow is simply lost",
            )

    def test_the_nav_lists_the_parts_not_all_forty_sections(self):
        page = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        nav = re.search(r'<nav id="sidenav".*?</nav>', html, re.S)
        self.assertIsNotNone(nav, "no section nav was built")
        top_level = re.findall(r'<button[^>]*class="[^"]*\bnav-part\b', nav.group(0))
        self.assertGreaterEqual(len(top_level), 2, "the nav has no top level at all")
        self.assertLessEqual(
            len(top_level), 12,
            "more than twelve top-level nav entries is the wall of labels nobody can read",
        )

    def test_the_contents_block_is_grouped_the_same_way(self):
        page = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        toc = re.search(r'<section id="toc".*?</section>', html, re.S)
        self.assertIsNotNone(toc, "no contents block was built")
        self.assertIn(
            "toc-part", toc.group(0),
            "the contents block is a flat list of forty chips, which is the same wall in another shape",
        )

    def test_a_flat_document_over_the_threshold_is_grouped_automatically(self):
        """A page author must not be able to produce an unusable nav by accident."""
        page = build_page(self.tmp, FLAT_FOURTEEN_MD, "flat.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        nav = re.search(r'<nav id="sidenav".*?</nav>', html, re.S).group(0)
        top_level = re.findall(r'<button[^>]*class="[^"]*\bnav-part\b', nav)
        self.assertTrue(top_level, "fourteen sections were left as fourteen flat nav entries")
        self.assertLessEqual(len(top_level), 12)

    def test_a_small_document_is_left_flat(self):
        """Grouping a four-section page would be ceremony, not navigation."""
        small = "# Small\n\nLead.\n\n## One\n\nBody.\n\n## Two\n\nBody.\n\n## Three\n\nBody.\n"
        html = build_page(self.tmp, small, "small.md", "--surface", "report").read_text(encoding="utf-8")
        nav = re.search(r'<nav id="sidenav".*?</nav>', html, re.S).group(0)
        self.assertNotIn("nav-part", nav, "a three-section page does not need parts")
        self.assertEqual(nav.count("<button"), 4)  # the Overview block plus the three sections

    def test_the_nav_keeps_the_raf_ease_and_the_observer(self):
        """The two behaviors that must survive the rewrite."""
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("requestAnimationFrame", html)
        self.assertIn("IntersectionObserver", html)
        self.assertNotIn("scrollIntoView({behavior", html)

    def test_the_nav_is_still_hidden_on_a_phone_and_in_print(self):
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertRegex(html, r"@media[^{]*max-width:\s*1199px\)\s*\{\s*#sidenav\{display:none\}")
        print_block = re.search(r"@media print\{(.*?)\n  \}", html, re.S)
        self.assertIsNotNone(print_block)
        self.assertIn("#sidenav", print_block.group(1))


# --------------------------------------------------------------------------- defect two: headings


class HeadingsOpenTheirOwnBlock(TempCase):
    """A heading at the foot of the previous section reads as a broken page."""

    HEADING_RE = re.compile(r"<(h[1-6])\b[^>]*>.*?</\1>", re.S | re.I)

    def test_no_heading_is_the_last_child_of_a_section(self):
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        stranded = lint.stranded_headings(html)
        self.assertEqual(
            stranded, [],
            "a heading closes a section card with nothing under it: "
            f"{stranded}",
        )

    def test_every_part_heading_sits_directly_above_the_content_it_introduces(self):
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        for label in ("1. The inbox, seen whole", "5. The drafts"):
            marker = re.search(
                r'<h2[^>]*class="[^"]*part-title[^"]*"[^>]*>\s*(?:<[^>]+>\s*)*' + re.escape(label.split(". ", 1)[1]),
                html,
            )
            self.assertIsNotNone(marker, f"the part heading {label!r} is not a part title in the page")
            after = html[marker.end() : marker.end() + 1200]
            self.assertNotRegex(
                after.split("</h2>", 1)[-1][:400],
                r"^\s*</div>\s*</section>",
                f"the part heading {label!r} is the last thing in its block",
            )

    def test_a_part_heading_is_never_swallowed_by_the_previous_section(self):
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        for section in re.findall(r"<section\b.*?</section>", html, re.S):
            self.assertNotIn(
                "part-title", section,
                "a part heading is rendered inside a section card: that is the stranded heading",
            )

    def test_the_heading_sizes_step_down_from_part_to_section_to_sub_section(self):
        html = build_page(self.tmp, FORTY_SECTION_MD, "forty.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("part-title", html)
        self.assertRegex(html, r"\.part-title\{[^}]*font-size:")
        # the part opens a level-2 heading, the section a level-3, so the document outline is real
        self.assertRegex(html, r'<h3 class="sec-title">')

    def test_both_looks_size_the_part_heading(self):
        for look in ("tint", "classic"):
            html = build_page(
                self.tmp, FORTY_SECTION_MD, f"forty-{look}.md", "--surface", "report", "--look", look
            ).read_text(encoding="utf-8")
            self.assertIn(".part-title{", html.replace("\n", ""), f"{look} has no part title rule")

    def test_a_sub_section_heading_inside_a_section_still_opens_its_own_content(self):
        source = (
            "# A record\n\nLead.\n\n# 1. The part\n\nIntro.\n\n## The section\n\n"
            "### The sub section\n\nThe clause under the sub section.\n\n## Another section\n\nBody.\n"
        )
        html = build_page(self.tmp, source, "sub.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertEqual(lint.stranded_headings(html), [])


# --------------------------------------------------------------------------- the lint learns both


class LintRefusesBothDefects(TempCase):
    def test_the_lint_fails_a_heading_that_closes_a_section(self):
        broken = _page_with(
            '<section id="a"><div class="sec-num">1</div><h2>A section</h2><p>Body.</p>'
            "<h2>A stranded heading</h2></section>"
            '<section id="b"><div class="sec-num">2</div><h2>Next</h2><p>Body.</p></section>'
        )
        failures = lint.check(broken, money=False, allow_commands=True)[0]
        self.assertTrue(
            any("heading" in f and "no content" in f for f in failures),
            f"the lint let the stranded heading through: {failures}",
        )

    def test_the_lint_passes_a_heading_that_opens_its_own_content(self):
        fine = _page_with(
            '<section id="a"><div class="sec-num">1</div><h2>A section</h2><p>Body.</p></section>'
            '<section id="b"><div class="sec-num">2</div><h2>Next</h2><p>Body.</p></section>'
        )
        failures = lint.check(fine, money=False, allow_commands=True)[0]
        self.assertFalse([f for f in failures if "heading" in f and "no content" in f], failures)

    def test_the_lint_warns_above_twelve_top_level_nav_entries(self):
        buttons = "".join(f'<button data-target="s{n}">Section {n}</button>' for n in range(1, 16))
        page = _page_with(
            '<section id="a"><h2>A</h2><p>Body.</p></section><section id="b"><h2>B</h2><p>Body.</p></section>',
            nav=buttons,
        )
        warnings = lint.check(page, money=False, allow_commands=True)[2]
        self.assertTrue(
            any("top-level" in w for w in warnings),
            f"fifteen top-level entries drew no warning: {warnings}",
        )

    def test_twelve_top_level_entries_do_not_warn(self):
        buttons = "".join(f'<button data-target="s{n}">Section {n}</button>' for n in range(1, 13))
        page = _page_with(
            '<section id="a"><h2>A</h2><p>Body.</p></section><section id="b"><h2>B</h2><p>Body.</p></section>',
            nav=buttons,
        )
        warnings = lint.check(page, money=False, allow_commands=True)[2]
        self.assertFalse([w for w in warnings if "top-level" in w], warnings)

    def test_a_grouped_nav_counts_only_its_top_level(self):
        groups = "".join(
            f'<div class="nav-group"><button class="nav-part" data-target="p{n}">Part {n}</button>'
            '<div class="nav-kids">'
            + "".join(f'<button data-target="p{n}s{m}">Section {m}</button>' for m in range(1, 9))
            + "</div></div>"
            for n in range(1, 6)
        )
        page = _page_with(
            '<section id="a"><h2>A</h2><p>Body.</p></section><section id="b"><h2>B</h2><p>Body.</p></section>',
            nav=groups,
        )
        warnings = lint.check(page, money=False, allow_commands=True)[2]
        self.assertFalse(
            [w for w in warnings if "top-level" in w],
            f"forty-five buttons in five groups is five top-level entries, not forty-five: {warnings}",
        )

    def test_the_rendered_nav_height_is_a_playwright_failure(self):
        """The render check is what actually stops the defect recurring."""
        source = lint.PLAYWRIGHT_JS + lint.__doc__
        self.assertIn("navHeight", lint.PLAYWRIGHT_JS)
        failures, notes = lint.report_measurements(
            [{"width": 1440, "scrollWidth": 1440, "innerWidth": 1440, "height": 9000,
              "navHeight": 1394, "navViewport": 900}], [], [],
        )
        self.assertTrue(any("nav" in f for f in failures), f"a 1394px nav in a 900px viewport passed: {failures}")

    def test_a_nav_inside_the_viewport_passes_the_render_check(self):
        failures, notes = lint.report_measurements(
            [{"width": 1440, "scrollWidth": 1440, "innerWidth": 1440, "height": 9000,
              "navHeight": 420, "navViewport": 900}], [], [],
        )
        self.assertEqual(failures, [])


# --------------------------------------------------------------------------- the owed fixes


class TheFixesOwedToThisSkill(TempCase):
    """Five fixes carried for four sessions, cleared in the same pass as the two defects."""

    def test_the_phone_media_queries_are_scoped_to_screen(self):
        """A Letter print is about 720 CSS pixels wide."""
        html = build_page(self.tmp, FLAT_FOURTEEN_MD, "q.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertEqual(
            re.findall(r"@media\s*\((?:max|min)-width", html), [],
            "an unscoped width media query fires on paper and collapses the printed columns",
        )
        self.assertIn("@media screen and (max-width:", html)

    def test_the_eyebrow_names_nothing_unless_it_is_given(self):
        for surface in ("report", "deck", "poster", "data-report"):
            source = FLAT_FOURTEEN_MD if surface != "data-report" else "Month,Signups\nJan,10\nFeb,12\n"
            name = f"e-{surface}." + ("md" if surface != "data-report" else "csv")
            html = build_page(self.tmp, source, name, "--surface", surface).read_text(encoding="utf-8")
            self.assertEqual(lint.wall_hits(html), [], f"the {surface} surface names a company by default")
            self.assertNotIn('<div class="eyebrow"></div>', html, "an empty eyebrow shipped as reserved space")

    def test_a_given_eyebrow_still_ships(self):
        html = build_page(
            self.tmp, FLAT_FOURTEEN_MD, "e2.md", "--surface", "report", "--eyebrow", "Northwind operations"
        ).read_text(encoding="utf-8")
        self.assertIn('<div class="eyebrow">Northwind operations</div>', html)

    def test_no_company_is_named_in_the_template_css(self):
        """The base ships inside every page, including a one-pager for a different client."""
        base = (HERE / "template.html").read_text(encoding="utf-8")
        style = re.search(r"<style>(.*?)</style>", base, re.S).group(1)
        self.assertEqual(lint.wall_hits(style), [], "a wall-list name is in the base CSS every page carries")

    def test_unnumbered_sections_still_render_a_real_heading(self):
        html = build_page(
            self.tmp, FLAT_FOURTEEN_MD, "u.md", "--surface", "report", "--unnumbered"
        ).read_text(encoding="utf-8")
        self.assertIn("<h2>Section number 1</h2>", html)
        self.assertNotIn('<div class="sec-num">Section number 1</div>', html)
        self.assertEqual(lint.stranded_headings(html), [])

    def test_numbered_is_still_the_default(self):
        html = build_page(self.tmp, FLAT_FOURTEEN_MD, "n.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn('<div class="sec-num">1</div>', html)

    def test_a_nested_list_keeps_its_nesting(self):
        source = "# T\n\nLead.\n\n## A section\n\n- One\n  - Nested a\n  - Nested b\n\nThe clause after the list.\n"
        html = build_page(self.tmp, source, "nest.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("<li>One<ul>", html.replace("\n", ""), "a two-space nested list was flattened")
        self.assertIn("<p>The clause after the list.</p>", html)

    def test_a_nested_list_under_an_ordered_parent_is_not_literal_text(self):
        source = "# T\n\nLead.\n\n## A section\n\n1. One\n   - Nested a\n   - Nested b\n\n2. Two\n"
        html = build_page(self.tmp, source, "ord.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertNotIn("   - Nested a", html, "the sub-bullets rendered as literal text inside the paragraph")
        self.assertIn("<li>Nested a</li>", html)

    def test_a_clause_after_a_list_is_never_swallowed_into_the_last_bullet(self):
        source = "# T\n\nLead.\n\n## A section\n\n- One\n- Two\nThe clause that belongs to the section.\n"
        html = build_page(self.tmp, source, "lazy.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("<p>The clause that belongs to the section.</p>", html)
        self.assertNotIn("Two\nThe clause", html)

    def test_a_fenced_block_is_left_exactly_as_written(self):
        """A fence holds a paste-ready message: reindenting one changes what the reader pastes."""
        source = "# T\n\nLead.\n\n## A section\n\nMessage:\n\n```\n- not a list\n  - still not\n```\n\nAfter.\n"
        html = build_page(self.tmp, source, "fence.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("- not a list\n  - still not", html)

    def test_an_unbreakable_token_breaks_instead_of_widening_the_page(self):
        """Found by the regression rebuild of a research page.

        One 90-character documentation URL took that page to 967px at 390, and one italic method
        signature to 495px. Real documents are full of unbreakable tokens.
        """
        source = (
            "# T\n\nLead.\n\n## A section\n\n"
            "See https://developer.apple.com/documentation/healthkit/hkhealthstore/"
            "enablebackgrounddelivery(for:frequency:withcompletion:) for the detail.\n\n"
            "> *enableBackgroundDelivery(for:frequency:withCompletion:)* is the call.\n\n"
            "## Another section\n\nBody.\n"
        )
        page = build_page(self.tmp, source, "long.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        self.assertRegex(html, r"\.wrap\{[^}]*overflow-wrap:break-word")
        measured = _width_measure(page, 390)
        if measured is None:
            self.skipTest("no playwright binding reachable")
        self.assertLessEqual(
            measured["scrollWidth"], measured["innerWidth"] + 1,
            f"the page is {measured['scrollWidth']}px wide in a 390px viewport",
        )

    def test_a_real_zero_amount_is_not_a_placeholder(self):
        """The lint once read a genuine $0.00 as an unfilled cell."""
        page = _page_with('<section id="a"><h2>Spend</h2><p>The total is $0.00 this month.</p></section>'
                          '<section id="b"><h2>Next</h2><p>Body.</p></section>')
        failures, notes, _ = lint.check(page, money=True, allow_commands=True)
        self.assertFalse([f for f in failures if "placeholder amount" in f], failures)
        self.assertTrue(any("zero amount" in n for n in notes), notes)

    def test_a_placeholder_amount_still_fails(self):
        page = _page_with('<section id="a"><h2>Spend</h2><p>The total is $XX.XX this month.</p></section>'
                          '<section id="b"><h2>Next</h2><p>Body.</p></section>')
        failures = lint.check(page, money=True, allow_commands=True)[0]
        self.assertTrue([f for f in failures if "placeholder amount" in f], failures)


# --------------------------------------------------------------------------- the code review


class ReviewFindings(TempCase):
    """Seven defects a code review returned, each with the input that breaks it."""

    def test_an_indented_code_block_of_dashes_is_not_turned_into_a_list(self):
        source = (
            "# T\n\nLead.\n\n## A section\n\nThe block below is code, not bullets:\n\n"
            "    - this should stay paste-ready\n    - so should this\n\nAfter.\n"
        )
        html = build_page(self.tmp, source, "code.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn("- this should stay paste-ready", html)
        self.assertNotIn("<li>this should stay paste-ready</li>", html)

    def test_a_wrapped_bullet_keeps_wrapping(self):
        """A continuation starts lowercase; a clause of the document opens with a capital."""
        source = (
            "# T\n\nLead.\n\n## A section\n\n- This is one bullet whose prose\ncontinues on the next line.\n"
        )
        html = build_page(self.tmp, source, "wrap.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertNotIn("<p>continues on the next line.</p>", html)
        self.assertIn("continues on the next line.", html)

    def test_a_heading_may_carry_a_dotted_number_of_its_own(self):
        source = "# Report\n\nLead.\n\n# 2. Inbox\n\nIntro.\n\n## 2.4 Escalations\n\nBody.\n"
        html = build_page(self.tmp, source, "dotted.md", "--surface", "report").read_text(encoding="utf-8")
        self.assertIn('<div class="sec-num">2.4</div>', html)
        self.assertIn('<h3 class="sec-title">Escalations</h3>', html)
        self.assertNotIn("2.4 Escalations</h3>", html)

    def test_a_part_and_a_section_with_the_same_words_get_different_ids(self):
        source = "# Report\n\nLead.\n\n# Findings\n\nIntro.\n\n## Findings\n\nBody.\n"
        html = build_page(self.tmp, source, "dupe.md", "--surface", "report").read_text(encoding="utf-8")
        ids = re.findall(r'<(?:section|div class="part-head") id="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)), f"two blocks share an id: {ids}")

    def test_a_heading_followed_by_a_chart_or_an_image_is_not_stranded(self):
        page = _page_with(
            '<section id="a"><h2>Trend chart</h2><img src="t.png" alt="Revenue trend">'
            "<h2>Interpretation</h2><p>Revenue rose.</p></section>"
            '<section id="b"><h2>Next</h2><p>Body.</p></section>'
        )
        failures = lint.check(page, money=False, allow_commands=True)[0]
        self.assertFalse([f for f in failures if "no content" in f], failures)

    def test_the_nav_is_found_when_an_attribute_precedes_its_id(self):
        buttons = "".join(f'<button data-target="s{n}">Section {n}</button>' for n in range(1, 16))
        page = _page_with(
            '<section id="a"><h2>A</h2><p>Body.</p></section><section id="b"><h2>B</h2><p>Body.</p></section>',
            nav=buttons,
        ).replace('<nav id="sidenav">', '<nav class="rail" id="sidenav">')
        self.assertEqual(lint.top_level_nav_entries(page), 15)
        warnings = lint.check(page, money=False, allow_commands=True)[2]
        self.assertTrue(any("top-level" in w for w in warnings), warnings)

    def test_a_fractional_amount_is_not_read_as_a_zero(self):
        page = _page_with('<section id="a"><h2>Fees</h2><p>The fee is $0.50 per unit.</p></section>'
                          '<section id="b"><h2>Next</h2><p>Body.</p></section>')
        notes = lint.check(page, money=True, allow_commands=True)[1]
        self.assertFalse([n for n in notes if "zero amount" in n], notes)

    def test_the_rail_and_the_grips_are_hidden_on_paper(self):
        """The reviewer's one template finding: does scoping to screen leak the rail into print?"""
        page = build_page(self.tmp, FORTY_SECTION_MD, "print.md", "--surface", "report")
        measured = _print_measure(page)
        if measured is None:
            self.skipTest("no playwright binding reachable")
        self.assertEqual(measured["nav"], "none", "the section nav renders on paper")
        self.assertEqual(measured["grip"], "none", "a width grip renders on paper")
        self.assertEqual(measured["toggle"], "none", "the theme toggle renders on paper")

    def test_a_printed_page_does_not_collapse_its_columns(self):
        """The reason the queries were scoped: a Letter page is about 720 CSS pixels wide."""
        source = FLAT_FOURTEEN_MD + "\n## The grid\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        page = build_page(self.tmp, source, "cols.md", "--surface", "data-report")
        measured = _print_measure(page)
        if measured is None:
            self.skipTest("no playwright binding reachable")
        self.assertTrue(measured["wide"], "the printed page collapsed to a phone layout at 720px")


PRINT_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 720, height: 1000 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);
  await page.emulateMedia({ media: 'print' });
  await page.waitForTimeout(200);
  const out = await page.evaluate(() => {
    const show = (sel) => { const el = document.querySelector(sel); return el ? getComputedStyle(el).display : 'none'; };
    const wrap = document.querySelector('.wrap');
    return {
      nav: show('#sidenav'), grip: show('.grip.l'), toggle: show('.theme-toggle'),
      wide: wrap ? wrap.getBoundingClientRect().width > 640 : false,
    };
  });
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


WIDTH_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: Number(process.argv[4]), height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);
  const out = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
  }));
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


def _width_measure(path: Path, width: int) -> dict | None:
    root = next((r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir()), None)
    if root is None:
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "width.js"
        script.write_text(WIDTH_JS, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), path.resolve().as_uri(), str(width)],
            capture_output=True, text=True, timeout=180,
        )
    if result.returncode != 0:
        raise AssertionError(f"the width measurement did not run: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def _print_measure(path: Path) -> dict | None:
    root = next((r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir()), None)
    if root is None:
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "print.js"
        script.write_text(PRINT_JS, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), path.resolve().as_uri()],
            capture_output=True, text=True, timeout=180,
        )
    if result.returncode != 0:
        raise AssertionError(f"the print measurement did not run: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def _page_with(body: str, nav: str = '<button data-target="a">A</button><button data-target="b">B</button>') -> str:
    """A minimal page that satisfies every OTHER lint rule, so one check is under test at a time."""
    return (
        '<!doctype html><html lang="en" data-theme="light" data-look="tint"><head><style>'
        ":root{--wrap-w:1080px}\n/* requestAnimationFrame */\n</style></head><body>"
        '<button class="grip l"></button><button class="grip r"></button>'
        f'<nav id="sidenav">{nav}</nav><div class="wrap">{body}</div>'
        "<script>requestAnimationFrame(function(){});</script></body></html>"
    )


if __name__ == "__main__":
    unittest.main()
