#!/usr/bin/env python3
"""Tests for the page contract: the clipping gate, the kind tag, the key-link labels and the
rail's keepInView arithmetic.

    python -m pytest skills/html-deliverable/test_page_contract.py

Four changes, four receipts:

1. **The clipping gate.** A stat card that read "$7,475 to $12,131" clipped: the text came out of
   the side of the box. The page-level overflow check cannot see it, because a nowrap value
   spills INSIDE a page that does not overflow. Proved here by inversion on a pair of fixtures
   that differ in one CSS declaration.
2. **The kind tag.** A document library that indexes built pages guesses the kind from the file
   name unless it is told. The builder is the one place that knows.
3. **The key-link labels.** A real page's harvested labels read the bare host three times over,
   which is a blank column.
4. **keepInView.** The rail is `position:fixed`, so it IS the offsetParent of its own buttons;
   subtracting `nav.offsetTop` drove every coordinate negative and snapped the rail to the top on
   every section change once the rail was taller than the viewport. Measured at 1440x900 on a
   220-section page: nav.offsetTop 450, rail 1149px in an 872px box, the active entry left at
   974px with scrollTop 0. After the fix, scrollTop 178 and the entry on screen.

The clipping tests need a browser and are skipped, loudly, when none is reachable. The rest are
pure source and string checks that run anywhere.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import lint  # noqa: E402

FIXTURES = HERE / "fixtures"


def a_browser_is_reachable() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        pass
    return any(r and (Path(r) / "playwright").is_dir() for r in lint.NODE_MODULE_ROOTS if r)


BROWSER = a_browser_is_reachable()

SAMPLE_MD = """# A page with several destinations on one host

A lead paragraph.

## 1. The first section

- The agreement is at https://docs.example.com/documents/the-agreement .
- The letter is at https://docs.example.com/documents/the-offer-letter .
- The guide is at https://docs.example.com/documents/the-onboarding-guide .
- An outside page sits at https://example.com/pricing .
"""


def build_page(tmp: Path, text: str, name: str, *args: str) -> Path:
    source = tmp / name
    source.write_text(text, encoding="utf-8")
    out = tmp / (source.stem + ".html")
    code = build.main([str(source), str(out), *args])
    assert code == 0, f"build returned {code}"
    return out


class ClippingGateTests(unittest.TestCase):
    """The inversion proof, as a test: the same value fails nowrap and passes wrapped."""

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the clipping gate cannot be proved")
    def test_the_overflowing_fixture_fails_and_names_the_value(self):
        failures, _ = lint.playwright_check(
            FIXTURES / "clipping-overflows.html", None, widths=[390, 1440]
        )
        clipped = [f for f in failures if "leaves its box" in f]
        self.assertTrue(clipped, f"the gate found no clipping at all; failures were {failures}")
        joined = "\n".join(clipped)
        self.assertIn("$7,475 to $12,131", joined)
        self.assertIn(".stat .num", joined)

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the clipping gate cannot be proved")
    def test_the_wrapped_twin_passes(self):
        failures, notes = lint.playwright_check(
            FIXTURES / "clipping-wraps.html", None, widths=[390, 1440]
        )
        self.assertEqual([f for f in failures if "leaves its box" in f], [])
        self.assertTrue(
            any("no value leaves its box" in n for n in notes),
            f"a clean page must SAY it was checked; notes were {notes}",
        )

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the clipping gate cannot be proved")
    def test_the_finding_names_every_width_and_theme_once(self):
        """One line per defect, naming where it happened. Six copies of one sentence is how a
        real failure gets skimmed past."""
        failures, _ = lint.playwright_check(
            FIXTURES / "clipping-overflows.html", None, widths=[390, 1440]
        )
        line = next(f for f in failures if "$7,475 to $12,131" in f)
        for where in ("390 (light)", "390 (dark)", "1440 (light)", "1440 (dark)"):
            self.assertIn(where, line)
        self.assertEqual(1, len([f for f in failures if "$7,475 to $12,131" in f]))

    def test_the_two_fixtures_differ_only_in_the_wrap_rule(self):
        """The pair proves the gate only if nothing else about them differs."""
        bad = (FIXTURES / "clipping-overflows.html").read_text(encoding="utf-8")
        good = (FIXTURES / "clipping-wraps.html").read_text(encoding="utf-8")
        for value in ("$41,014.06", "$7,475 to $12,131", "$0.00", "$28,131.94"):
            self.assertIn(value, bad)
            self.assertIn(value, good)
        self.assertIn("white-space:nowrap", bad.replace(" ", ""))
        self.assertNotIn("white-space:nowrap", good.replace(" ", ""))
        for both in ("grid-template-columns:repeat(4, 1fr)", "max-width: 760px"):
            self.assertIn(both, bad)
            self.assertIn(both, good)

    def test_the_selector_list_covers_the_card_that_clipped(self):
        self.assertIn(".stat .num", lint.CLIP_SELECTORS)
        self.assertIn(".stat .lbl", lint.CLIP_SELECTORS)
        self.assertIn("td", lint.CLIP_SELECTORS)

    def test_every_selector_names_a_class_the_house_actually_emits(self):
        """The first list carried three selectors that matched nothing (`.stat .lab`,
        `.kpi .num`, `.kpi .lab`). A selector that matches nothing checks nothing while
        counting toward "N selectors checked". Every class-bearing selector must appear in the
        template, a surface template, the builder, or the gallery catalogue (`build_gallery.py`,
        which is where copy-paste components such as the `.ss-k` / `.ss-v` agree-change-add rows
        live: real house classes that no builder emits)."""
        haystack = (HERE / "template.html").read_text(encoding="utf-8")
        haystack += (HERE / "build.py").read_text(encoding="utf-8")
        haystack += (HERE / "build_gallery.py").read_text(encoding="utf-8")
        for tpl in (HERE / "templates").glob("*.html"):
            haystack += tpl.read_text(encoding="utf-8")
        for sel in lint.CLIP_SELECTORS:
            classes = [part[1:].split(".")[0] for part in sel.split() if part.startswith(".")]
            for cls in classes:
                self.assertIn(cls, haystack, f"selector {sel!r}: class .{cls} is emitted nowhere")

    @unittest.skipUnless(BROWSER, "no Playwright reachable")
    def test_an_element_that_scrolls_by_design_is_not_a_clip(self):
        with tempfile.TemporaryDirectory() as raw:
            page = Path(raw) / "scroller.html"
            page.write_text(
                "<!doctype html><html><head><meta charset='utf-8'><style>"
                "td{display:block;max-width:120px;overflow-x:auto;white-space:nowrap}"
                "</style></head><body><table><tr><td>https://example.com/a/very/long/"
                "address/that/scrolls/by/design/and/is/not/a/clip</td></tr></table>"
                "</body></html>", encoding="utf-8")
            failures, _ = lint.playwright_check(page, None, widths=[1440])
        self.assertEqual([f for f in failures if "leaves its box" in f], [])

    def test_the_printed_numbers_add_up(self):
        """`over` and the box it was measured in come from the SAME width, whichever width was
        worst, so the printed subtraction is true."""
        out = lint.clipping_findings([
            {"width": 1440, "theme": "light", "clipped": [
                {"sel": ".stat .num", "over": 42, "scrollWidth": 219, "clientWidth": 177, "text": "$1"}]},
            {"width": 390, "theme": "light", "clipped": [
                {"sel": ".stat .num", "over": 71, "scrollWidth": 219, "clientWidth": 148, "text": "$1"}]},
        ])
        self.assertEqual(1, len(out))
        self.assertIn("overflows by 71px (219 of content in a 148px box)", out[0])

    def test_a_clean_measurement_produces_no_finding(self):
        self.assertEqual([], lint.clipping_findings([{"width": 1440, "theme": "light", "clipped": []}]))

    def test_a_measurement_without_the_key_is_not_an_error(self):
        """An older render, or one from a cached JSON, has no `clipped` key at all."""
        self.assertEqual([], lint.clipping_findings([{"width": 1440, "theme": "light"}]))


class KindTagTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_the_kind_is_emitted_when_it_is_given(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report",
                         "--kind", "decision pack")
        html = out.read_text(encoding="utf-8")
        self.assertIn('<meta name="document-kind" content="decision pack">', html)

    def test_no_tag_at_all_when_it_is_not_given(self):
        """An empty tag would look like an answer. A library should keep guessing rather than
        be told nothing in a way that reads as being told something."""
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        self.assertNotIn("document-kind", out.read_text(encoding="utf-8"))

    def test_an_unknown_kind_is_refused_before_a_page_is_built(self):
        """A library IGNORES a kind it does not know, so a typo would emit a tag that reads as
        an answer and is thrown away on registration. Refused here instead, one line from the
        person who typed it, with the known list printed."""
        source = self.tmp / "record.md"
        source.write_text(SAMPLE_MD, encoding="utf-8")
        out = self.tmp / "record.html"
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            code = build.main([str(source), str(out), "--surface", "report",
                               "--kind", 'a "quoted" kind'])
        self.assertEqual(2, code)
        self.assertFalse(out.exists(), "a refused build must not leave a page behind")
        self.assertIn("decision pack", err.getvalue())
        self.assertIn("not a kind this builder knows", err.getvalue())

    def test_the_kind_is_folded_the_way_the_library_folds_it(self):
        """Inner whitespace is collapsed and case is lowered before the compare, so the builder
        emits the folded form and accepts the unfolded one."""
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report",
                         "--kind", "Decision   Pack")
        html = out.read_text(encoding="utf-8")
        self.assertIn('<meta name="document-kind" content="decision pack">', html)

    def test_the_kind_attribute_is_escaped(self):
        self.assertNotIn('"', build.esc_attr('a "quoted" kind').replace("&quot;", ""))

    def test_the_help_text_is_built_from_the_one_list(self):
        """Two lists that must agree and nothing making them: the help text is derived, so a
        kind added to `KINDS` appears in `--help` without anyone remembering to add it twice."""
        import io
        from contextlib import redirect_stdout
        text = io.StringIO()
        with redirect_stdout(text), self.assertRaises(SystemExit):
            build.main(["--help"])
        for kind in build.KINDS:
            self.assertIn(kind, text.getvalue())

    def test_the_tag_survives_the_delivery_strip(self):
        """Every comment is stripped from a delivered page; a meta tag is not a comment."""
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report",
                         "--kind", "audit")
        html = out.read_text(encoding="utf-8")
        self.assertIn('content="audit"', html)
        self.assertLess(html.index("document-kind"), html.index("</head>"))


class KeyLinkLabelTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_three_destinations_on_one_host_get_three_different_labels(self):
        links = build.harvest_links(
            '<a href="https://docs.example.com/documents/the-agreement">a</a>'
            '<a href="https://docs.example.com/documents/the-offer-letter">b</a>'
            '<a href="https://docs.example.com/documents/the-onboarding-guide">c</a>',
            [],
        )
        labels = [label for label, _ in links]
        self.assertEqual(3, len(labels))
        self.assertEqual(3, len(set(labels)), f"labels collapsed to {labels}")
        self.assertNotEqual(["docs.example.com"] * 3, labels)

    def test_a_told_label_is_never_rewritten(self):
        links = build.harvest_links(
            '<a href="https://docs.example.com/documents/the-agreement">a</a>',
            ["The agreement=https://docs.example.com/documents/the-agreement"],
        )
        self.assertEqual([("The agreement", "https://docs.example.com/documents/the-agreement")], links)

    def test_a_bare_host_still_reads_as_the_host(self):
        links = build.harvest_links('<a href="https://example.com">x</a>', [])
        self.assertEqual("example.com", links[0][0])

    def test_the_label_drops_a_file_extension_but_keeps_a_version(self):
        self.assertEqual("example.com/the report",
                         build.host_label("https://example.com/docs/the-report.html"))
        self.assertEqual("example.com/1.2.3",
                         build.host_label("https://example.com/releases/1.2.3"))

    def test_a_query_string_does_not_become_the_label(self):
        self.assertEqual("docs.example.com/open",
                         build.host_label("https://docs.example.com/open?detail=abc-123"))

    def test_two_rows_that_still_collide_fall_back_to_the_full_address(self):
        """Same host, same last segment, different routes. Two identical labels is the defect
        this function exists to prevent, so both rows get longer rather than staying the same."""
        links = build.harvest_links(
            '<a href="https://example.com/a/report">1</a>'
            '<a href="https://example.com/b/report">2</a>',
            [],
        )
        labels = [label for label, _ in links]
        self.assertEqual(2, len(set(labels)), f"labels collapsed to {labels}")

    def test_http_and_https_twins_get_distinct_labels(self):
        links = build.harvest_links(
            '<a href="http://example.com/a/report">1</a>'
            '<a href="https://example.com/a/report">2</a>',
            [],
        )
        labels = [label for label, _ in links]
        self.assertEqual(2, len(set(labels)), f"labels collapsed to {labels}")

    def test_a_told_label_equal_to_a_fallback_does_not_collide(self):
        links = build.harvest_links(
            '<a href="https://e.com/a/report">1</a><a href="https://e.com/b/report">2</a>',
            ["e.com/a/report=https://other.com/z"],
        )
        labels = [label for label, _ in links]
        self.assertEqual(len(labels), len(set(labels)), f"labels collided: {labels}")
        self.assertEqual("e.com/a/report", labels[0], "the told label was rewritten")

    def test_the_built_page_carries_distinct_labels(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        html = out.read_text(encoding="utf-8")
        self.assertLessEqual(
            html.count("<td>docs.example.com</td>"), 1,
            "the Key links table repeated a bare host label",
        )


class RailKeepInViewTests(unittest.TestCase):
    """The rail is position:fixed, so its buttons' offsetTop is already relative to it."""

    def test_the_template_does_not_subtract_the_rails_own_offset(self):
        source = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertIn("var top = button.offsetTop;", source)
        self.assertNotIn("button.offsetTop - nav.offsetTop", source)

    def test_the_committed_gallery_carries_the_same_fix(self):
        """Every page emitted from the template carries a copy, so an emitted copy that differs
        from the template is a fork nobody meant to make."""
        gallery = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertNotIn("button.offsetTop - nav.offsetTop", gallery)

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the rail cannot be driven")
    def test_a_rail_taller_than_the_viewport_scrolls_its_active_entry_into_view(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            lines = ["# A page with a rail taller than the screen", ""]
            for n in range(1, 221):
                lines += [f"## Section number {n}", "",
                          f"A paragraph of ordinary prose so section {n} is tall enough to scroll "
                          "past and the observer has something to fire on.", ""]
            page = build_page(tmp, "\n".join(lines), "tall.md", "--surface", "report")
            script = tmp / "drive.js"
            script.write_text(DRIVE_JS, encoding="utf-8")
            root = next(r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir())
            result = subprocess.run(
                ["node", str(script), str(Path(root) / "playwright"), page.resolve().as_uri()],
                capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(0, result.returncode, result.stderr[:400])
            import json
            got = json.loads(result.stdout.strip().splitlines()[-1])

        self.assertTrue(got["taller"], "the fixture's rail did not exceed the viewport")
        self.assertTrue(
            got["activeVisible"],
            f"the active rail entry is off screen: {got}",
        )
        self.assertGreater(
            got["scrollTop"], 0,
            "the rail stayed at the top, which is the defect this test exists for",
        )


DRIVE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);
  const pre = await page.evaluate(() => {
    const nav = document.getElementById('sidenav');
    nav.classList.add('visible');
    const buttons = Array.from(nav.querySelectorAll('button[data-target]'));
    nav.scrollTop = 0;
    buttons[buttons.length - 1].click();
    return { taller: nav.scrollHeight > nav.clientHeight };
  });
  await page.waitForTimeout(1400);
  const post = await page.evaluate(() => {
    const nav = document.getElementById('sidenav');
    const active = nav.querySelector('button.active');
    if (!active) return { scrollTop: nav.scrollTop, activeVisible: false };
    const n = nav.getBoundingClientRect(), b = active.getBoundingClientRect();
    return { scrollTop: nav.scrollTop,
             activeVisible: b.top >= n.top - 1 && b.bottom <= n.bottom + 1 };
  });
  await browser.close();
  console.log(JSON.stringify({ ...pre, ...post }));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


class TabTitleTests(unittest.TestCase):
    """The tab reads the document's own title, exactly: no prefix or suffix, no kind label, equal
    to the h1; a description meta from the lede beside it. The lint refuses a generic title and a
    title that differs from the h1."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_a_built_page_titles_the_tab_with_its_own_h1(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report",
                         "--lede", "The first sentence, for the preview.")
        html = out.read_text(encoding="utf-8")
        self.assertIn("<title>A page with several destinations on one host</title>", html)
        self.assertIn('<meta name="description" content="The first sentence, for the preview.">', html)
        self.assertEqual([], lint.title_findings(html))

    def test_a_title_that_differs_from_the_h1_fails(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report")
        html = out.read_text(encoding="utf-8").replace(
            "<title>A page with several destinations on one host</title>",
            "<title>Something else entirely</title>", 1)
        findings = lint.title_findings(html)
        self.assertEqual(1, len(findings), findings)
        self.assertIn("differs from the page's <h1>", findings[0])
        failures, _, _ = lint.check(html, money=False, allow_commands=True, audience="internal")
        self.assertTrue(any("differs from the page's <h1>" in f for f in failures))

    def test_a_generic_title_fails(self):
        for generic in ("Document", "REPLACE - Document Title", "Untitled", ""):
            html = f"<html><head><title>{generic}</title></head><body><h1>Real</h1></body></html>"
            findings = lint.title_findings(html)
            self.assertTrue(findings, f"{generic!r} passed as a title")
            self.assertIn("generic <title>", findings[0])

    def test_a_product_affix_fails_because_it_differs_from_the_h1(self):
        for affixed in ("Product - The quarter", "The quarter | Product", "Product: The quarter"):
            html = f"<html><head><title>{affixed}</title></head><body><h1>The quarter</h1></body></html>"
            findings = lint.title_findings(html)
            self.assertTrue(any("differs from the page's <h1>" in f for f in findings), f"{affixed!r} passed: {findings}")

    def test_entities_and_whitespace_do_not_make_two_titles(self):
        html = ("<html><head><title>Costs &amp; returns</title></head>"
                "<body><h1>Costs &amp;\n   returns</h1></body></html>")
        self.assertEqual([], lint.title_findings(html))

    def test_a_missing_title_fails(self):
        self.assertIn("no <title>", lint.title_findings("<html><body><h1>x</h1></body></html>")[0])

    def test_the_description_is_the_lede_with_its_markup_gone(self):
        out = build_page(self.tmp, SAMPLE_MD, "record.md", "--surface", "report",
                         "--lede", 'A lede with "quotes" and <b>markup</b>.')
        html = out.read_text(encoding="utf-8")
        self.assertIn('<meta name="description" content="A lede with &quot;quotes&quot; and markup.">', html)


class ImageRuleTests(unittest.TestCase):
    """The house has an `img` rule. Proved by inversion at phone width: the SAME
    1,200px image passes at 390 with the rule and overflows the page without it. The twin is the
    built page plus one declaration, so nothing else about the pair differs."""

    IMAGE_MD = (
        "# A page with a capture pasted at its pixel width\n\n"
        "A paragraph before the picture.\n\n"
        '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 '
        "width=%271200%27 height=%27200%27%3E%3Crect width=%271200%27 height=%27200%27 "
        "fill=%27%23888%27/%3E%3C/svg%3E\" width=\"1200\" height=\"200\" "
        'alt="a 1,200 pixel wide capture">\n\n'
        "A paragraph after it.\n"
    )

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_the_template_carries_the_rule(self):
        source = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertIn("img{max-width:100%; height:auto}", source)

    def test_the_committed_gallery_carries_the_rule(self):
        self.assertIn("img{max-width:100%; height:auto}",
                      (HERE / "components.html").read_text(encoding="utf-8"))

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the image rule cannot be proved")
    def test_a_wide_image_fits_at_phone_width_and_overflows_without_the_rule(self):
        page = build_page(self.tmp, self.IMAGE_MD, "capture.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        self.assertIn('width="1200"', html, "the fixture lost its image on the way through the build")

        fits, _ = lint.playwright_check(page, None, widths=[390])
        self.assertEqual([f for f in fits if "horizontal overflow" in f], [],
                         f"the rule did not hold at 390: {fits}")

        twin = self.tmp / "capture-without-the-rule.html"
        twin.write_text(html.replace("</head>", "<style>img{max-width:none}</style></head>", 1),
                        encoding="utf-8")
        overflows, _ = lint.playwright_check(twin, None, widths=[390])
        self.assertTrue(any("horizontal overflow at 390" in f for f in overflows),
                        f"the inverted twin did not overflow, so the pair proves nothing: {overflows}")


class FrameContractTests(unittest.TestCase):
    """The template inside a frame.

    Inbound, any `{type:'<anything>-theme', theme}` sets `data-theme` (a hosting shell sends
    one; the template never spells a product name, which belongs on the wall list); the chrome
    hides under `html[data-framed]` once the frame is taller than the screen (or at once on a
    `data-embedded` page); the height is reported as `{type:'hd-document', height, sections}`
    after `{type:'hd-document-ready'}`, unless the page was served with the shell's own
    reporter (a script tagged `data-...-reporter`), which then owns the channel. A page in its
    own tab is untouched."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_the_template_speaks_the_contract(self):
        source = (HERE / "template.html").read_text(encoding="utf-8")
        for token in ("/-theme$/", "'hd-document'", "'hd-document-ready'",
                      "data-framed", "/-reporter$/", "data-embedded", "data-page-reporter"):
            self.assertIn(token, source, f"the template does not carry {token}")
        self.assertIn("html[data-framed] #sidenav", source)
        self.assertIn('<script data-page-frame="template">', source,
                      "the static marker a server greps for before appending its own reporter")
        self.assertEqual(lint.wall_hits(source), [],
                         "a wall-list name is in the template; a delivered page names nobody")

    def test_the_committed_gallery_carries_the_same_block(self):
        gallery = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertIn("'hd-document-ready'", gallery)
        self.assertIn('<script data-page-frame="template">', gallery)

    def _drive(self, extra_head: str = "", grow_to: int = 5000, send_theme: str = "dark") -> dict:
        page = build_page(self.tmp, SAMPLE_MD, "framed.md", "--surface", "report")
        if extra_head:
            page.write_text(page.read_text(encoding="utf-8").replace("</head>", extra_head + "</head>", 1),
                            encoding="utf-8")
        parent = self.tmp / "parent.html"
        parent.write_text(PARENT_HTML.replace("__CHILD__", page.name), encoding="utf-8")
        script = self.tmp / "drive-frame.js"
        script.write_text(FRAME_DRIVE_JS, encoding="utf-8")
        root = next(r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir())
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), parent.resolve().as_uri(),
             str(grow_to), send_theme],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(0, result.returncode, result.stderr[:600])
        import json
        return json.loads(result.stdout.strip().splitlines()[-1])

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_the_parent_theme_wins_and_the_height_is_reported(self):
        got = self._drive()
        self.assertEqual("light", got["themeBefore"], "the template must ship light")
        self.assertEqual("dark", got["themeAfter"], f"the parent's theme was not applied: {got}")
        self.assertTrue(got["ready"], "no hd-document-ready arrived")
        self.assertGreater(got["height"], 400, f"no usable height report: {got}")
        self.assertTrue(got["sections"], "the report named no sections")
        self.assertEqual("template", got["reporter"], "the template's own reporter did not start")

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_ready_is_announced_before_the_first_report(self):
        """The documented order is ready, then the report. A consumer that starts listening for
        the report only once ready has arrived must still receive the page's height; the first
        send once preceded ready and the de-duplicated second send never repeated it, so that
        consumer got nothing."""
        got = self._drive()
        self.assertGreater(got["heightAfterReady"], 400,
                           f"a consumer listening after ready received no height: {got}")

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_the_chrome_hides_once_the_frame_is_taller_than_the_screen_and_not_before(self):
        got = self._drive()
        self.assertFalse(got["framedBeforeGrow"], "the chrome hid in a short frame")
        self.assertTrue(got["framedAfterGrow"], "the chrome stayed once the frame outgrew the screen")
        self.assertEqual("none", got["navDisplayAfterGrow"])
        self.assertEqual("none", got["toggleDisplayAfterGrow"])

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_a_served_reporter_owns_the_channel(self):
        """A page a shell serves may carry its own reporter below this script. The template
        must stay quiet then, or the shell hears ready twice."""
        served = "<script data-library-reporter>/* the library's own reporter stands in here */</script>"
        got = self._drive(extra_head=served)
        self.assertEqual("", got["reporter"], "the template reported beside a served reporter")
        self.assertFalse(got["ready"], "the template announced ready beside a served reporter")
        self.assertEqual("dark", got["themeAfter"], "the theme must still be taken from the parent")

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_a_data_embedded_page_hides_its_chrome_at_once(self):
        page = build_page(self.tmp, SAMPLE_MD, "framed.md", "--surface", "report")
        html = page.read_text(encoding="utf-8")
        self.assertIn('<html lang="en"', html)
        page.write_text(html.replace('<html lang="en"', '<html lang="en" data-embedded', 1),
                        encoding="utf-8")
        parent = self.tmp / "parent.html"
        parent.write_text(PARENT_HTML.replace("__CHILD__", page.name), encoding="utf-8")
        script = self.tmp / "drive-frame.js"
        script.write_text(FRAME_DRIVE_JS, encoding="utf-8")
        root = next(r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir())
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), parent.resolve().as_uri(),
             "480", "light"],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(0, result.returncode, result.stderr[:600])
        import json
        got = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(got["framedBeforeGrow"], "data-embedded did not hide the chrome at load")

    @unittest.skipUnless(BROWSER, "no Playwright reachable: the frame cannot be driven")
    def test_a_page_opened_in_its_own_tab_is_untouched(self):
        page = build_page(self.tmp, SAMPLE_MD, "alone.md", "--surface", "report")
        script = self.tmp / "drive-alone.js"
        script.write_text(ALONE_DRIVE_JS, encoding="utf-8")
        root = next(r for r in lint.NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir())
        result = subprocess.run(
            ["node", str(script), str(Path(root) / "playwright"), page.resolve().as_uri()],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(0, result.returncode, result.stderr[:600])
        import json
        got = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertFalse(got["framed"], "a top-level page set data-framed")
        self.assertIsNone(got["frameMarker"], "a top-level page started the reporter")
        self.assertEqual("light", got["theme"])


PARENT_HTML = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<iframe id="f" src="__CHILD__" style="width:900px;height:480px;border:0"></iframe>
<script>
  /* Two listeners. The first records everything. The second is the CONSUMER SHAPE the contract
     documents (ready, then the report): it ignores every report until ready has arrived, so a
     page that reports before it announces ready leaves this consumer with no height at all. */
  window.__log = { ready: false, reports: [], afterReady: [] };
  window.addEventListener('message', function (ev) {
    var d = ev.data || {};
    if (d.type === 'hd-document-ready') window.__log.ready = true;
    if (d.type === 'hd-document') window.__log.reports.push({ height: d.height, sections: d.sections });
  });
  window.addEventListener('message', function (ev) {
    var d = ev.data || {};
    if (d.type === 'hd-document' && window.__log.ready) window.__log.afterReady.push(d.height);
  });
</script>
</body></html>
"""

FRAME_DRIVE_JS = """
const { chromium } = require(process.argv[2]);
const growTo = parseInt(process.argv[4], 10);
const theme = process.argv[5];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, screen: { width: 1440, height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(700);
  const frame = page.frames().find(f => f !== page.mainFrame());
  const before = await frame.evaluate(() => ({
    theme: document.documentElement.getAttribute('data-theme'),
    framed: document.documentElement.hasAttribute('data-framed'),
    reporter: document.documentElement.getAttribute('data-page-reporter') || '',
  }));
  await page.evaluate((t) => {
    document.getElementById('f').contentWindow.postMessage({ type: 'library-theme', theme: t }, '*');
  }, theme);
  await page.waitForTimeout(300);
  await page.evaluate((h) => { document.getElementById('f').style.height = h + 'px'; }, growTo);
  await page.waitForTimeout(500);
  const after = await frame.evaluate(() => {
    const nav = document.getElementById('sidenav');
    const toggle = document.querySelector('.theme-toggle');
    return {
      theme: document.documentElement.getAttribute('data-theme'),
      framed: document.documentElement.hasAttribute('data-framed'),
      navDisplay: nav ? getComputedStyle(nav).display : 'absent',
      toggleDisplay: toggle ? getComputedStyle(toggle).display : 'absent',
    };
  });
  const log = await page.evaluate(() => window.__log);
  const last = log.reports[log.reports.length - 1] || { height: 0, sections: [] };
  await browser.close();
  console.log(JSON.stringify({
    themeBefore: before.theme, themeAfter: after.theme, reporter: before.reporter,
    framedBeforeGrow: before.framed, framedAfterGrow: after.framed,
    navDisplayAfterGrow: after.navDisplay, toggleDisplayAfterGrow: after.toggleDisplay,
    ready: log.ready, height: last.height, sections: last.sections,
    heightAfterReady: log.afterReady.length ? log.afterReady[0] : 0,
  }));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""

ALONE_DRIVE_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(600);
  const got = await page.evaluate(() => ({
    framed: document.documentElement.hasAttribute('data-framed'),
    frameMarker: document.documentElement.getAttribute('data-page-reporter'),
    theme: document.documentElement.getAttribute('data-theme'),
  }));
  await browser.close();
  console.log(JSON.stringify(got));
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


if __name__ == "__main__":
    unittest.main(verbosity=2)
