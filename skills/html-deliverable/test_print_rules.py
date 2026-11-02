#!/usr/bin/env python3
"""The printed page: what paper needs that a screen does not.

    python -m pytest skills/html-deliverable/test_print_rules.py

Paper cannot be clicked open, and it breaks where it likes. A data report's method note once
printed as a closed fold with its paragraph hidden, every sortable header printed a stray arrow,
a callout printed half on one page and half on the next, tables of six rows split across two
pages, and headings sat alone at a page foot. The template's print block now:

1. opens every `<details>` on paper (`details::details-content{content-visibility:visible}`),
   drops the summary marker and hides `th[data-sort]::after`; a `beforeprint` handler also sets
   `open` on every closed fold for a browser without `::details-content`, and `afterprint` puts
   them back;
2. keeps every box that reads as one thing whole (`break-inside:avoid`);
3. keeps a heading with what follows it, and a table of twelve body rows or fewer on one page,
   while a longer table starts where it falls and splits.

Two kinds of proof: the string pins fail on the template as it was, and the browser tests print
real built pages and read the PDF's own text back page by page, each beside an inverted twin with
the rule switched off, so the measurement is known to see the rule.
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

import lint  # noqa: E402
from test_page_contract import BROWSER, build_page, node_playwright_root  # noqa: E402

PRINT_RULES = (
    "details::details-content{content-visibility:visible}",
    "details > summary{list-style:none}",
    "details > summary::-webkit-details-marker{display:none}",
    "table.dt th[data-sort]::after{content:none}",
    ".callout,.warn,.verdict,.facts,.stage-summary,.cmp,.tl,figure.flow,figure.dgm,figure.chart,.stat,.kpi,tr{break-inside:avoid}",
    "h2,h3,h4{break-after:avoid}",
    ".dt-wrap:not(:has(tbody tr:nth-child(13))),table:not(:has(tbody tr:nth-child(13))){break-inside:avoid}",
)

SAMPLE_CSV = """Month,Signups,Revenue
January,120,1400
February,145,1720
March,170,2010
"""

FILLER = "The paragraph carries the argument of this part in plain words for the reader. "

# One long section holding fourteen callouts, each about two fifths of an A4 page tall, so that
# several of them land on a page boundary. `section{break-inside:avoid}` cannot help here: the
# section is taller than a page, and a box that cannot fit is split by the browser anyway.
CALLOUTS_MD = "# Breaks\n\nA lead.\n\n## 1. One long section\n\n" + "\n\n".join(
    ("The paragraph before the callout says what the reader needs and then the callout carries "
     "the one sentence they would otherwise miss. ") * 3
    + '\n\n<div class="callout">'
    + "A callout tall enough to straddle a page break when it lands near one. " * 14
    + f" Callout {i}.</div>\n"
    for i in range(1, 15)
) + "\n"

# Twenty-four short parts, each a heading and then a box that keeps itself whole, after fillers
# of different lengths. A heading followed by a paragraph is never left alone (the paragraph's own
# lines can break); a heading followed by a box that moves to the next page is.
HEADINGS_MD = "# Headings\n\nA lead.\n\n## 1. One long section\n\n" + "\n\n".join(
    FILLER * (3 + (i * 5) % 11)
    + f'\n\n### Heading {i} here\n\n<div class="callout">Body {i} begins here. ' + FILLER * 6 + "</div>"
    for i in range(1, 25)
) + "\n"

# Twelve six-row tables after fillers of different lengths, so that several of them straddle a
# page break when nothing keeps them whole.
TABLES_MD = "# Tables\n\nA lead.\n\n## 1. One long section\n\n" + "\n\n".join(
    FILLER * (2 + (i * 7) % 13)
    + "\n\n| Item | Detail |\n|---|---|\n"
    + "".join(f"| T{i} row {r} | The detail of row {r} of table {i} |\n" for r in range(1, 7))
    for i in range(1, 13)
) + "\n"

# One seventy-row table after a short lead: taller than a page, so it must START where it falls
# and split, never jump to a fresh page and leave the first one half empty. (An unscoped
# whole-table rule moved the heading and row 1 to page 2 and left page 1 half empty.)
TALL_MD = (
    "# A long table\n\nA lead.\n\n## 1. The data\n\n" + FILLER * 4
    + "The long table follows this sentence."
    + "\n\n| Item | Detail |\n|---|---|\n"
    + "".join(f"| Tall row {r} | The detail of row {r} of the long table |\n" for r in range(1, 71))
)

PDF_WRITE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(process.argv[3]);
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: process.argv[4], format: 'A4', printBackground: true });
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(3); });
"""

# The PDF path, with JavaScript OFF. `page.pdf()` renders with print media and never dispatches
# `beforeprint`, so on the delivery path (`lint.py --pdf`) the CSS is the only thing working.
NO_JS_DRIVE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(process.argv[3]);
  await page.emulateMedia({ media: 'print' });
  const got = await page.evaluate(() => {
    const details = document.querySelector('details.method');
    // The FOLD's own box is what moves: a child of a closed <details> reports a non-zero rect
    // in Chromium either way, so measuring the paragraph proves nothing.
    return { open: details.hasAttribute('open'),
             foldHeight: Math.round(details.getBoundingClientRect().height),
             contentVisibility: getComputedStyle(details, '::details-content').contentVisibility };
  });
  await browser.close();
  console.log(JSON.stringify(got));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""

PRINT_DRIVE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(300);
  await page.emulateMedia({ media: 'print' });
  const styles = await page.evaluate(() => {
    const details = document.querySelector('details.method');
    const th = document.querySelector('table.dt th[data-sort]');
    return {
      detailsContent: getComputedStyle(details, '::details-content').contentVisibility,
      summaryMarker: getComputedStyle(details.querySelector('summary')).listStyleType,
      arrow: getComputedStyle(th, '::after').content,
      openBefore: details.hasAttribute('open'),
    };
  });
  const events = await page.evaluate(() => {
    const details = document.querySelector('details.method');
    window.dispatchEvent(new Event('beforeprint'));
    window.dispatchEvent(new Event('beforeprint'));
    const duringPrint = details.hasAttribute('open');
    window.dispatchEvent(new Event('afterprint'));
    return { duringPrint, afterPrint: details.hasAttribute('open') };
  });
  await browser.close();
  console.log(JSON.stringify(Object.assign(styles, events)));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


# The fold component remembers its open state per page. Printing opens it, and a browser may fire
# beforeprint twice for one print: neither may leave the fold open afterwards or write "open" into
# the reader's saved state. `toggle` is queued, so each step waits a moment before reading.
FOLD_PRINT_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(process.argv[3]);
  await page.waitForTimeout(200);
  const saved = () => page.evaluate(() => Object.keys(localStorage)
    .filter(k => k.startsWith('hd-fold-')).map(k => localStorage.getItem(k)));
  const open = () => page.evaluate(() => document.querySelector('details.fold[data-fold]').open);
  const before = await open();
  await page.evaluate(() => { window.dispatchEvent(new Event('beforeprint')); });
  await page.waitForTimeout(100);
  await page.evaluate(() => { window.dispatchEvent(new Event('beforeprint')); });
  await page.waitForTimeout(100);
  const during = await open();
  const savedDuring = await saved();
  await page.evaluate(() => { window.dispatchEvent(new Event('afterprint')); });
  await page.waitForTimeout(200);
  const after = await open();
  const savedAfter = await saved();
  await browser.close();
  console.log(JSON.stringify({ before, during, after, savedDuring, savedAfter }));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""

FOLD_MD = """# Folds

A lead.

## 1. The part

<details class="fold" data-fold="one"><summary>The detail</summary><div class="fold-body">The argument.</div></details>
"""


def print_block(source: str) -> str:
    """The body of the first `@media print{...}`, brace-balanced. Slicing to the end of the file
    would pass for a rule moved OUT of the print block into the screen CSS below it, which is how
    every sort arrow would vanish on screen with this test still green."""
    start = source.index("@media print{") + len("@media print{")
    depth, i = 1, start
    while depth and i < len(source):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        i += 1
    return source[start:i - 1]


def run_node(tmp: Path, js: str, *args: str) -> str:
    script = tmp / "drive.js"
    script.write_text(js, encoding="utf-8")
    root = node_playwright_root()
    result = subprocess.run(["node", str(script), str(Path(root) / "playwright"), *args],
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[:600]
    return result.stdout


def pdf_pages(tmp: Path, page: Path) -> list[str]:
    from pypdf import PdfReader

    out = page.with_suffix(".pdf")
    run_node(tmp, PDF_WRITE_JS, page.resolve().as_uri(), str(out))
    return [re.sub(r"\s+", " ", p.extract_text() or "") for p in PdfReader(str(out)).pages]


def page_of(pages: list[str], needle: str) -> int | None:
    return next((n for n, text in enumerate(pages) if needle in text), None)


def callouts_split(pages: list[str]) -> list[int]:
    """Every callout whose fourteen sentences did not all print on the page of its sentinel."""
    split = []
    for i in range(1, 15):
        end = page_of(pages, f"Callout {i}.")
        assert end is not None, f"callout {i} is missing from the printed pages"
        before = pages[end].split(f"Callout {i}.")[0]
        if i > 1 and f"Callout {i - 1}." in before:
            before = before.split(f"Callout {i - 1}.")[-1]
        if before.count("A callout tall enough") < 14:
            split.append(i)
    return split


def headings_alone(pages: list[str]) -> list[int]:
    """Every heading printed on a different page from the first words of its own body."""
    alone = []
    for i in range(1, 25):
        head, body = page_of(pages, f"Heading {i} here"), page_of(pages, f"Body {i} begins")
        assert head is not None and body is not None, f"part {i} is missing from the printed pages"
        if head != body:
            alone.append(i)
    return alone


def tables_split(pages: list[str]) -> list[int]:
    """Every table whose first and last rows printed on different pages."""
    split = []
    for i in range(1, 13):
        first, last = page_of(pages, f"T{i} row 1 "), page_of(pages, f"T{i} row 6 ")
        assert first is not None and last is not None, f"table {i} is missing from the printed pages"
        if first != last:
            split.append(i)
    return split


def twin(page: Path, css: str) -> Path:
    """The same page with the rule under test switched off, so the pair measures something."""
    out = page.with_name(page.stem + "-twin.html")
    out.write_text(page.read_text(encoding="utf-8").replace(
        "</head>", f"<style>@media print{{{css}}}</style></head>", 1), encoding="utf-8")
    return out


class TheRulesArePinned(unittest.TestCase):
    def test_the_slice_is_the_print_block_and_not_the_rest_of_the_file(self):
        source = "a{x}\n@media print{ .one{y} }\n.two{z}\n"
        self.assertIn(".one{y}", print_block(source))
        self.assertNotIn(".two{z}", print_block(source))

    def test_the_template_print_block_carries_every_rule(self):
        block = print_block((HERE / "template.html").read_text(encoding="utf-8"))
        for rule in PRINT_RULES:
            self.assertIn(rule, block, rule)

    def test_the_committed_gallery_carries_every_rule(self):
        block = print_block((HERE / "components.html").read_text(encoding="utf-8"))
        for rule in PRINT_RULES:
            self.assertIn(rule, block, rule)

    def test_the_copyable_print_snippet_carries_the_rules_and_the_fallback_script(self):
        """The gallery entry is what a hand-written page copies. ::details-content is Chrome 131
        and later, so a snippet with only the CSS ships the closed fold to Safari and Firefox."""
        gallery = (HERE / "components.html").read_text(encoding="utf-8")
        snippet = gallery[gallery.index('id="c-print"'):]
        snippet = snippet[:snippet.index("</section>")]
        self.assertIn("beforeprint", snippet)
        self.assertIn("details:not([open]):not([data-fold])", snippet)
        for rule in PRINT_RULES:
            self.assertIn(rule.replace(">", "&gt;"), snippet, rule)

    def test_the_handler_is_idempotent_and_leaves_the_fold_component_alone(self):
        source = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertIn("window.addEventListener('beforeprint'", source)
        self.assertIn("window.addEventListener('afterprint'", source)
        self.assertIn("if (opened.length) return;", source,
                      "a second beforeprint would capture an empty list and leave every fold open")
        self.assertIn("details:not([open]):not([data-fold])", source,
                      "details[data-fold] has its own handler, which persists state on toggle")


class TheSelectorIsNotTheComponent(unittest.TestCase):
    """The print block names `.stage-summary` in a selector on every page. The lint's assets
    proof once read the bare class name as the part-summary component in use, and refused every
    built page for "not carrying its CSS"."""

    def test_a_built_page_with_the_print_rule_is_not_read_as_using_the_strip(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = build_page(Path(tmp), "# A page\n\nA lead.\n\n## 1. One\n\nText.\n", "page.md")
            html = page.read_text(encoding="utf-8")
            self.assertIn(".stage-summary,", html, "the built page lost the print rule")
            self.assertEqual([], [h for h in lint.components_without_assets(html) if "part-summary" in h])

    def test_a_strip_with_no_css_is_still_refused(self):
        for attribute in ('class="stage-summary"', 'class="stage-summary tight"',
                          "class='x stage-summary'", 'class="a stage-summary b"'):
            html = f'<html><body><div {attribute}><div class="ss-row">x</div></div></body></html>'
            self.assertTrue([h for h in lint.components_without_assets(html) if "part-summary" in h], attribute)

    def test_a_longer_class_name_is_not_the_strip(self):
        html = '<html><body><div class="stage-summary-note">x</div></body></html>'
        self.assertEqual([], [h for h in lint.components_without_assets(html) if "part-summary" in h])


@unittest.skipUnless(BROWSER, "no Playwright reachable: the print styles cannot be measured")
class FoldsAndArrowsOnPaper(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)
        self.page = build_page(self.tmp, SAMPLE_CSV, "growth.csv", "--surface", "data-report")
        self.assertIn('<details class="method">', self.page.read_text(encoding="utf-8"),
                      "the fixture lost its method note")

    def tearDown(self):
        self.dir.cleanup()

    def measure(self, js: str, page: Path) -> dict:
        return json.loads(run_node(self.tmp, js, page.resolve().as_uri()).strip().splitlines()[-1])

    def test_the_method_note_prints_open_and_the_headers_print_without_arrows(self):
        got = self.measure(PRINT_DRIVE_JS, self.page)
        self.assertEqual("visible", got["detailsContent"], got)
        self.assertEqual("none", got["summaryMarker"], got)
        self.assertEqual("none", got["arrow"], got)
        self.assertFalse(got["openBefore"], "the fold must start closed for the test to mean anything")
        self.assertTrue(got["duringPrint"], f"beforeprint (fired twice) did not open the fold: {got}")
        self.assertFalse(got["afterPrint"], f"afterprint did not close it again: {got}")

    def test_the_inverted_twin_prints_the_fold_closed_and_the_arrow_back(self):
        got = self.measure(PRINT_DRIVE_JS, twin(
            self.page, 'details::details-content{content-visibility:hidden}'
                       ' table.dt th[data-sort]::after{content:"\\2195"}'))
        self.assertEqual("hidden", got["detailsContent"], f"the twin's fold did not read closed: {got}")
        self.assertNotEqual("none", got["arrow"], f"the twin's arrow did not come back: {got}")

    def test_a_remembered_fold_survives_a_double_beforeprint(self):
        page = build_page(self.tmp, FOLD_MD, "folds.md", "--surface", "report")
        self.assertIn("data-print-opened", page.read_text(encoding="utf-8"), "the fold script did not ship")
        got = self.measure(FOLD_PRINT_JS, page)
        self.assertFalse(got["before"], f"the fixture's fold must start closed: {got}")
        self.assertTrue(got["during"], f"beforeprint did not open the fold: {got}")
        self.assertFalse(got["after"], f"a second beforeprint left the fold open after printing: {got}")
        self.assertNotIn("1", got["savedDuring"] + got["savedAfter"],
                         f"printing wrote 'open' into the reader's saved fold state: {got}")

    def test_the_pdf_path_shows_the_method_note_with_no_javascript_at_all(self):
        got = self.measure(NO_JS_DRIVE_JS, self.page)
        self.assertFalse(got["open"], "the fold must still be closed: the CSS is what reveals it")
        self.assertEqual("visible", got["contentVisibility"], got)
        blind_page = self.page.with_name("growth-without-the-rule.html")
        blind_page.write_text(self.page.read_text(encoding="utf-8").replace(
            "details::details-content{content-visibility:visible}", "", 1), encoding="utf-8")
        blind = self.measure(NO_JS_DRIVE_JS, blind_page)
        self.assertEqual("hidden", blind["contentVisibility"], f"the twin kept the rule: {blind}")
        self.assertGreater(got["foldHeight"], blind["foldHeight"],
                           f"the fold did not grow on paper: {got} against {blind}")


@unittest.skipUnless(BROWSER, "no Playwright reachable: the printed pages cannot be produced")
class BreaksOnPaper(unittest.TestCase):
    def setUp(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf is not installed: the printed pages cannot be read back")
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_a_callout_is_never_split_and_would_be_without_the_rule(self):
        page = build_page(self.tmp, CALLOUTS_MD, "breaks.md", "--surface", "report")
        self.assertEqual([], callouts_split(pdf_pages(self.tmp, page)))
        self.assertTrue(callouts_split(pdf_pages(self.tmp, twin(page, ".callout{break-inside:auto}"))),
                        "the twin printed every callout whole, so the pair proves nothing")

    def test_no_heading_is_left_alone_at_a_page_foot_and_would_be_without_the_rule(self):
        page = build_page(self.tmp, HEADINGS_MD, "headings.md", "--surface", "report")
        self.assertEqual([], headings_alone(pdf_pages(self.tmp, page)))
        self.assertTrue(headings_alone(pdf_pages(self.tmp, twin(page, "h2,h3,h4{break-after:auto}"))),
                        "the twin kept every heading with its body, so the pair proves nothing")

    def test_no_table_that_fits_a_page_is_split_and_would_be_without_the_rule(self):
        page = build_page(self.tmp, TABLES_MD, "tables.md", "--surface", "report")
        self.assertEqual([], tables_split(pdf_pages(self.tmp, page)))
        self.assertTrue(tables_split(pdf_pages(self.tmp, twin(page, ".dt-wrap,table{break-inside:auto !important}"))),
                        "the twin printed every table whole, so the pair proves nothing")

    def test_a_table_taller_than_a_page_starts_where_it_falls(self):
        """The half that must NOT fire: a long table is not kept whole, so it never moves to a
        fresh page; its first row prints on the page that carries the sentence above it."""
        page = build_page(self.tmp, TALL_MD, "tall.md", "--surface", "report")
        pages = pdf_pages(self.tmp, page)
        above = page_of(pages, "The long table follows this sentence.")
        first, last = page_of(pages, "Tall row 1 "), page_of(pages, "Tall row 70 ")
        self.assertIsNotNone(first)
        self.assertEqual(above, first, f"row 1 moved to page {first} from the sentence's page {above}")
        self.assertNotEqual(first, last, "the fixture fits one page, so it proves nothing about a tall table")


if __name__ == "__main__":
    unittest.main(verbosity=2)
