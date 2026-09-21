#!/usr/bin/env python3
"""Tests for the design system: the two looks, the width handles, the components from markdown,
the extended lint and the gallery.

    python -m pytest skills/html-deliverable/test_design_system.py

Companion to test_build_lint.py, which covers the build and lint contract.
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
import build_gallery  # noqa: E402
import lint  # noqa: E402


SAMPLE_MD = """# The September record

A lead paragraph before any section, which becomes the Overview block.

## 1. Say publish tonight

- The three pages sit on disk, not on the workspace at https://workspace.example.com/dana-priya .
- Dana says one word.

## 2. Send the short message

Two lines by text message. The record is at https://records.example.com/short .

## The part with no number of its own

Body text.
"""

COMPONENT_MD = """# The weekly plan

A lead paragraph.

## 1. The table that must sort

| Item | Owner | Days |
|---|---|---|
| Publish the plan | Dana | 2 |
| Send the message | Dana | 1 |
| Book the call | Priya | 3 |
| Read the record | Dana | 1 |
| Check the numbers | Dana | 5 |
| Close the loop | Priya | 2 |

## 2. The short table that must not

| Key | Value |
|---|---|
| Look | Tint |
| Width | 1080 |

## 3. The checklist

- [ ] Confirm the scope
- [x] Agree the owner
- [ ] Pick the date

## 4. The slider

[slider: Weeks to delivery | 2 | 20 | 1 | 8 | weeks]

Body text after it.
"""


def build_page(tmp: Path, text: str, name: str, *args: str) -> Path:
    source = tmp / name
    source.write_text(text, encoding="utf-8")
    out = source.with_suffix(".html")
    code = build.main([str(source), str(out), *args])
    assert code == 0, f"build.py exited {code}"
    return out


def failures_of(html: str, **kwargs):
    options = {"money": False, "allow_commands": False}
    options.update(kwargs)
    return lint.check(html, **options)[0]


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# --------------------------------------------------------------------------- the two looks


class LookTests(TempCase):
    def test_look_tint_is_explicit_and_sets_the_attribute(self):
        html = build_page(self.tmp, SAMPLE_MD, "r.md", "--look", "tint").read_text(encoding="utf-8")
        self.assertIn('data-look="tint"', html)
        self.assertNotIn('data-look="classic"', html)

    def test_the_base_template_carries_both_looks(self):
        base = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertIn('data-look="classic"', base, "the base template does not ship in the classic look")
        self.assertIn('[data-look="tint"]', base, "the base template carries no tint rules")

    def test_look_classic_is_explicit(self):
        html = build_page(self.tmp, SAMPLE_MD, "r.md", "--look", "classic").read_text(encoding="utf-8")
        self.assertIn('data-look="classic"', html)

    def test_auto_resolves_by_surface(self):
        # the deck and the poster are tint; the report and the data-report are classic
        self.assertEqual(build.resolve_look("auto", "deck"), "tint")
        self.assertEqual(build.resolve_look("auto", "poster"), "tint")
        self.assertEqual(build.resolve_look("auto", "report"), "classic")
        self.assertEqual(build.resolve_look("auto", "data-report"), "classic")
        # an explicit look always wins over the resolution
        self.assertEqual(build.resolve_look("classic", "deck"), "classic")
        self.assertEqual(build.resolve_look("tint", "report"), "tint")

    def test_the_look_is_the_only_difference_between_two_builds(self):
        one, two = self.tmp / "one", self.tmp / "two"
        one.mkdir()
        two.mkdir()
        tint = build_page(one, SAMPLE_MD, "a.md", "--look", "tint").read_text(encoding="utf-8")
        classic = build_page(two, SAMPLE_MD, "a.md", "--look", "classic").read_text(encoding="utf-8")
        self.assertEqual(
            tint.replace('data-look="tint"', "LOOK", 1),
            classic.replace('data-look="classic"', "LOOK", 1),
            "the two looks must differ by the attribute alone, never by forked markup",
        )

    def test_both_looks_define_every_token_the_components_read(self):
        html = (HERE / "template.html").read_text(encoding="utf-8")
        for token in ("--acc", "--acc-soft", "--acc-ink", "--grid", "--wrap-w", "--panel-2", "--line-2"):
            self.assertIn(f"{token}:", html, f"{token} is not defined")
        tint = html[html.index('data-look="tint"]') :][:1600]
        for token in ("--bg:", "--acc:", "--grid:", "--wrap-w:"):
            self.assertIn(token, tint, f"the tint look does not set {token}")

    def test_the_grid_is_transparent_in_classic_so_one_code_path_serves_both(self):
        html = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertIn("--grid:transparent", html)
        self.assertIn("background-size:28px 28px", html)

    def test_no_component_carries_a_raw_hex_color(self):
        """A look change is one attribute only while every component reads tokens."""
        offenders = []
        exempt = {
            # the look demo deliberately redefines the classic tokens in place
            "classic-header",
            # print colors are PAPER colors: black ink on white stock, not theme tokens
            "print",
        }
        for component in build_gallery.COMPONENTS:
            if component.cid in exempt:
                continue
            for blob in (component.css, component.markup):
                for line in blob.splitlines():
                    if "#" in line and any(
                        c in line for c in ("color:", "background", "border", "fill:")
                    ):
                        import re

                        if re.search(r"#[0-9a-fA-F]{3,8}\b", line):
                            offenders.append(f"{component.cid}: {line.strip()}")
        self.assertEqual(offenders, [], "components must read tokens, never raw hex")


# --------------------------------------------------------------------------- the width handles


class WidthHandleTests(TempCase):
    def setUp(self):
        super().setUp()
        self.html = build_page(self.tmp, SAMPLE_MD, "r.md").read_text(encoding="utf-8")

    def test_a_built_page_carries_both_handles(self):
        self.assertIn('class="grip l"', self.html)
        self.assertIn('class="grip r"', self.html)
        self.assertIn("--wrap-w", self.html)

    def test_the_handles_are_wired_to_drag_persist_and_reset(self):
        for behavior in ("pointerdown", "setPointerCapture", "dblclick", "ArrowLeft", "localStorage"):
            self.assertIn(behavior, self.html, f"the handles do not implement {behavior}")

    def test_the_width_is_clamped_to_the_declared_bounds(self):
        self.assertIn("--wrap-min", self.html)
        self.assertIn("--wrap-max", self.html)
        self.assertIn("Math.max(b.min, Math.min(b.max", self.html)

    def test_lint_fails_a_page_with_no_handles(self):
        stripped = self.html.replace('<button class="grip l"', '<button class="gone-l"')
        self.assertTrue(any("handles" in f for f in failures_of(stripped)))

    def test_allow_no_grips_clears_it_for_a_fragment(self):
        stripped = self.html.replace('<button class="grip l"', '<button class="gone-l"')
        self.assertFalse(any("handles" in f for f in failures_of(stripped, allow_no_grips=True)))

    def test_handles_present_but_wired_to_nothing_still_fails(self):
        inert = self.html.replace("--wrap-w", "--unused-w")
        self.assertTrue(any("--wrap-w" in f for f in failures_of(inert)))

    def test_the_handles_are_hidden_on_a_phone_and_in_print(self):
        # SCREEN-scoped: a Letter page prints at about 720 CSS pixels, so an unscoped phone query
        # fires on paper and collapses the columns.
        self.assertIn("@media screen and (max-width:1199px){ .grip{display:none} }", self.html)
        self.assertRegex(self.html, r"@media print\{\s*\.theme-toggle,#sidenav,\.grip")

    def test_no_layout_media_query_fires_on_paper(self):
        """A Letter print is about 720 CSS pixels wide. An unscoped max-width query fires there."""
        unscoped = re.findall(r"@media\s*\((?:max|min)-width", self.html)
        self.assertEqual(
            unscoped, [],
            "a width media query is not scoped to screen, so it applies to the printed page too",
        )


# --------------------------------------------------------------------------- punctuation


class PunctuationEntityTests(TempCase):
    """The entity forms slipped past the lint twice before they were matched explicitly."""

    def setUp(self):
        super().setUp()
        self.html = build_page(self.tmp, SAMPLE_MD, "r.md").read_text(encoding="utf-8")

    def test_entity_em_dashes_fail(self):
        for entity in ("&mdash;", "&#8212;", "&#x2014;"):
            broken = self.html.replace("A lead paragraph", f"A lead {entity} paragraph")
            self.assertTrue(any("em dash" in f for f in failures_of(broken)), entity)

    def test_entity_mid_dots_fail(self):
        for entity in ("&middot;", "&#183;", "&#xb7;"):
            broken = self.html.replace("A lead paragraph", f"one {entity} two")
            self.assertTrue(any("mid dot" in f for f in failures_of(broken)), entity)

    def test_raw_forms_still_fail(self):
        self.assertTrue(any("em dash" in f for f in failures_of(self.html.replace("A lead", "A — lead"))))
        self.assertTrue(any("mid dot" in f for f in failures_of(self.html.replace("A lead", "A · lead"))))

    def test_documenting_the_prefers_color_scheme_ban_is_not_a_breach_of_it(self):
        # a CSS comment may NAME the rule; naming it is not doing it. The builder strips its
        # own comments now, so the comment under test is put back in deliberately.
        documented = self.html.replace(
            "@media print{", "/* never add a prefers-color-scheme block */\n  @media print{", 1
        )
        self.assertIn("prefers-color-scheme", documented)
        self.assertFalse(any("prefers-color-scheme" in f for f in failures_of(documented)))

    def test_a_real_prefers_color_scheme_block_still_fails(self):
        broken = self.html.replace(
            "@media print{", "@media (prefers-color-scheme: dark){ body{color:#fff} }\n  @media print{", 1
        )
        self.assertTrue(any("prefers-color-scheme" in f for f in failures_of(broken)))


# --------------------------------------------------------------------------- components


class MarkdownComponentTests(TempCase):
    def setUp(self):
        super().setUp()
        self.html = build_page(self.tmp, COMPONENT_MD, "plan.md", "--look", "tint").read_text(encoding="utf-8")

    def test_a_six_row_table_becomes_filterable_and_sortable(self):
        self.assertIn('class="dt-wrap"', self.html)
        self.assertIn('class="dt-filter"', self.html)
        self.assertIn('<table class="dt">', self.html)
        self.assertIn('data-sort="text"', self.html)
        self.assertIn('data-sort="num"', self.html)  # the Days column is numeric

    def test_a_two_row_table_is_left_alone(self):
        # the short key and value table must not grow a filter box of its own
        self.assertEqual(self.html.count('class="dt-filter"'), 1)

    def test_table_plain_opts_a_long_table_out(self):
        opted = COMPONENT_MD.replace(
            "## 1. The table that must sort\n", "## 1. The table that must sort\n\n[table: plain]\n"
        )
        html = build_page(self.tmp, opted, "plain.md").read_text(encoding="utf-8")
        self.assertNotIn('class="dt-filter"', html)
        self.assertNotIn("[table:", html)

    def test_a_task_list_becomes_a_persisted_checklist(self):
        self.assertIn('class="checklist"', self.html)
        self.assertIn("data-checklist", self.html)
        self.assertIn('type="checkbox"', self.html)
        self.assertIn('type="checkbox" checked', self.html)  # the [x] line keeps its tick
        self.assertIn("data-check-count", self.html)

    def test_a_slider_marker_becomes_a_slider_with_its_readout(self):
        self.assertIn('class="slider-row"', self.html)
        self.assertIn('type="range"', self.html)
        self.assertIn('min="2"', self.html)
        self.assertIn('max="20"', self.html)
        self.assertIn("data-out", self.html)
        self.assertNotIn("[slider:", self.html)

    def test_component_css_and_js_ship_only_when_the_page_uses_them(self):
        plain = build_page(self.tmp, SAMPLE_MD, "plain2.md").read_text(encoding="utf-8")
        self.assertNotIn(".slider-row{", plain)
        self.assertNotIn("data-checklist", plain)
        self.assertIn(".slider-row{", self.html)
        self.assertIn("data-checklist", self.html)

    def test_the_component_source_is_the_gallery_not_a_second_copy(self):
        slider_css = dict(build.COMPONENT_ASSETS)["slider"][0]
        self.assertTrue(slider_css.strip(), "the slider has no CSS in the gallery catalogue")
        self.assertIn(slider_css.strip().splitlines()[0].strip(), self.html)

    def test_the_built_page_passes_the_lint_with_no_warnings(self):
        failures, _, warnings = lint.check(self.html, money=False, allow_commands=False)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])


class SortWarningTests(TempCase):
    def setUp(self):
        super().setUp()
        self.html = build_page(self.tmp, SAMPLE_MD, "r.md").read_text(encoding="utf-8")

    def test_a_long_table_with_no_sortable_header_warns_without_failing(self):
        rows = "".join(f"<tr><td>Row {i}</td><td>{i}</td></tr>" for i in range(8))
        table = f"<table><thead><tr><th>Name</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table>"
        broken = self.html.replace("<p>A lead paragraph", table + "<p>A lead paragraph", 1)
        failures, _, warnings = lint.check(broken, money=False, allow_commands=False)
        self.assertEqual(failures, [])
        self.assertTrue(any("sortable header" in w for w in warnings), warnings)

    def test_the_key_links_table_is_never_warned_about(self):
        _, _, warnings = lint.check(self.html, money=False, allow_commands=False)
        self.assertEqual(warnings, [])

    def test_a_short_table_is_not_warned_about(self):
        table = "<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
        page = self.html.replace("<p>A lead paragraph", table + "<p>A lead paragraph", 1)
        _, _, warnings = lint.check(page, money=False, allow_commands=False)
        self.assertEqual(warnings, [])


# --------------------------------------------------------------------------- the gallery


class GalleryTests(TempCase):
    """The gallery is the component SOURCE, so it must build, pass, and match itself."""

    def setUp(self):
        super().setUp()
        self.html = build_gallery.build(self.tmp / "components.html")

    def test_the_gallery_builds_and_passes_the_lint(self):
        failures, _, _ = lint.check(self.html, money=False, allow_commands=False)
        self.assertEqual(failures, [])

    def test_every_component_is_live_on_the_page_and_printed_beneath_it(self):
        for component in build_gallery.COMPONENTS:
            self.assertIn(f'id="c-{component.cid}"', self.html, component.cid)
            if component.diagram:
                # A diagram component has no hand-written markup: its demo is rendered by the
                # builder from the markdown under it, so the pair is the HINT plus the SVG.
                kind, caption, _source = component.diagram
                self.assertIn(f"[diagram: {kind} | {caption}]", self.html, component.cid)
                self.assertIn('class="dgm-art"', self.html, f"{component.cid}: the demo is missing")
                continue
            first_line = component.markup.splitlines()[0]
            if not component.live_on_page:
                self.assertIn(first_line, self.html, f"{component.cid}: the demo is missing")
            escaped = build_gallery.esc(first_line)
            self.assertIn(escaped, self.html, f"{component.cid}: the snippet is missing")

    def test_the_four_base_template_components_are_not_duplicated_as_demos(self):
        """A second <nav id="sidenav"> or a second .grip on one page is invalid HTML and leaves
        dead controls; those four are documented by source and by the live one on the page."""
        live = {c.cid for c in build_gallery.COMPONENTS if c.live_on_page}
        self.assertEqual(live, {"grips", "sidenav", "theme", "print"})
        self.assertEqual(self.html.count('<nav id="sidenav"'), 1)
        self.assertEqual(self.html.count('<button class="grip l"'), 1)
        self.assertEqual(self.html.count('<button class="theme-toggle"'), 1)

    def test_gallery_section_ids_are_namespaced_so_they_cannot_collide(self):
        for component in build_gallery.COMPONENTS:
            self.assertIn(f'<section id="c-{component.cid}">', self.html, component.cid)
            self.assertIn(f'data-target="c-{component.cid}"', self.html, component.cid)

    def test_every_component_css_and_js_reaches_the_page(self):
        for component in build_gallery.COMPONENTS:
            if component.css:
                self.assertIn(component.css.strip().splitlines()[0].strip(), self.html, component.cid)
            if component.js:
                self.assertIn(component.js.strip().splitlines()[-1].strip(), self.html, component.cid)

    def test_the_gallery_is_in_the_tint_look_and_carries_the_nav(self):
        self.assertIn('data-look="tint"', self.html)
        self.assertIn('id="sidenav"', self.html)

    def test_the_gallery_says_who_reads_it(self):
        self.assertIn('data-audience="internal"', self.html)

    def test_the_gallery_documents_the_client_safe_rules(self):
        self.assertIn("Client-safe by construction", self.html)

    def test_the_committed_gallery_is_up_to_date_with_its_builder(self):
        committed = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertEqual(
            committed.strip(),
            self.html.strip(),
            "components.html is stale: rebuild it with the gallery builder and commit the result",
        )

    def test_the_catalogue_covers_every_component_design_md_names(self):
        ids = {c.cid for c in build_gallery.COMPONENTS}
        for required in (
            "stat-row", "chips", "boxes", "facts", "links-table", "data-table", "slider",
            "calculator", "drag-rank", "checklist", "run-of-show", "timeline", "comparison",
            "problem-solution", "age", "grips", "sidenav", "theme", "print", "lockup",
            "classic-header",
        ):
            self.assertIn(required, ids, f"{required} is missing from the gallery")

    def test_design_md_names_every_component_in_the_catalogue(self):
        design = (HERE / "DESIGN.md").read_text(encoding="utf-8")
        for component in build_gallery.COMPONENTS:
            self.assertIn(
                component.title.split(",")[0].split("(")[0].strip().lower(),
                design.lower(),
                f"DESIGN.md does not name {component.title}",
            )


# --------------------------------------------------------------------------- the pdf path


class PdfTests(TempCase):
    def test_pdf_export_writes_a_real_pdf_or_says_it_could_not(self):
        page = build_page(self.tmp, SAMPLE_MD, "r.md")
        destination = self.tmp / "r.pdf"
        failures, notes = lint.export_pdf(page, destination)
        if failures:
            # a renderer that is genuinely absent must FAIL loudly, never pass quietly
            self.assertTrue(any("could NOT" in f or "FAILED" in f for f in failures), failures)
            self.assertFalse(destination.exists())
            self.skipTest("no playwright available in this environment: the failure path is correct")
        self.assertTrue(destination.is_file())
        self.assertGreater(destination.stat().st_size, 1000)
        self.assertEqual(destination.read_bytes()[:5], b"%PDF-")
        self.assertTrue(any("pdf written" in n for n in notes))


# --------------------------------------------------------------------------- the whole chain


class EndToEndTests(TempCase):
    def test_every_script_in_the_skill_compiles(self):
        for script in sorted(HERE.glob("*.py")):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, f"{script.name}: {result.stderr}")

    def test_no_skill_file_carries_a_stray_control_character(self):
        """A heredoc once turned every regex word boundary into a backspace byte."""
        for path in list(HERE.glob("*.py")) + list(HERE.glob("*.html")) + list(HERE.glob("templates/*.html")):
            raw = path.read_bytes()
            for code in (8, 11, 12):
                self.assertEqual(raw.count(bytes([code])), 0, f"{path.name} carries control byte {code}")

    def test_the_four_surfaces_all_build_in_both_looks_and_pass(self):
        for surface in ("report", "deck", "poster"):
            for look in ("tint", "classic"):
                page = build_page(
                    self.tmp, SAMPLE_MD, f"{surface}-{look}.md", "--surface", surface, "--look", look
                )
                html = page.read_text(encoding="utf-8")
                self.assertIn(f'data-look="{look}"', html)
                self.assertEqual(failures_of(html), [], f"{surface}/{look}")

    def test_the_data_report_surface_builds_from_csv_and_sorts(self):
        csv_text = "Month,Signups,Revenue\nJanuary,120,4200\nFebruary,145,5100\nMarch,132,4780\n"
        page = build_page(self.tmp, csv_text, "data.csv", "--surface", "data-report")
        html = page.read_text(encoding="utf-8")
        self.assertIn('<table class="dt data"', html)
        self.assertIn('data-sort="num"', html)
        self.assertIn('class="dt-filter"', html)
        self.assertEqual(failures_of(html), [])


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- browser checks


def _node_playwright() -> str | None:
    for root in lint.NODE_MODULE_ROOTS:
        if root and (Path(root) / "playwright").is_dir():
            return str(Path(root) / "playwright")
    return None


def _run_browser_script(script: str, page: Path) -> dict:
    module = _node_playwright()
    if module is None:
        raise unittest.SkipTest("no node playwright module root available")
    result = subprocess.run(
        ["node", str(HERE / script), module, page.resolve().as_uri()],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(f"{script} failed: {result.stderr[:400]}")
    return json.loads(result.stdout)


class BrowserStructureTests(TempCase):
    """Checks only a parsed document can answer honestly.

    A snippet printed inside <pre><code> carries the same attribute TEXT as the element it
    documents, so grepping the source reports duplicate ids the browser never builds.
    """

    def test_the_gallery_has_no_duplicate_ids_and_one_of_each_fixed_control(self):
        gallery = HERE / "components.html"
        out = _run_browser_script("domcheck.js", gallery)
        self.assertEqual(out["duplicateIds"], [], "duplicate ids in the gallery")
        self.assertEqual(out["sidenavs"], 1)
        self.assertEqual(out["grips"], 2)
        self.assertEqual(out["themeToggles"], 1)
        self.assertEqual(out["nativeTitles"], 0, "native title tooltips are banned")
        self.assertEqual(out["leakedSource"], 0, "a stylesheet or script is rendering as visible text")

    def test_a_built_page_has_no_duplicate_ids(self):
        page = build_page(self.tmp, COMPONENT_MD, "plan.md", "--look", "tint")
        out = _run_browser_script("domcheck.js", page)
        self.assertEqual(out["duplicateIds"], [])
        self.assertEqual(out["sidenavs"], 1)
        self.assertEqual(out["grips"], 2)


class ChartComponentTests(TempCase):
    """The line chart.

    Everything here is measured in the browser, because a chart is the component a screenshot
    lies about most: a path can be drawn from the wrong numbers and look perfect.
    """

    def setUp(self):
        super().setUp()
        self.out = _run_browser_script("chartcheck.js", HERE / "components.html")

    def test_no_console_error(self):
        self.assertEqual(self.out.get("consoleErrors"), [])

    def test_the_chart_is_on_the_gallery(self):
        self.assertIs(self.out.get("present"), True, "the gallery carries no line chart")

    def test_every_value_rides_in_the_json_block(self):
        """A rebuild is a data edit, never a hand-written path."""
        self.assertIs(self.out.get("dataInJsonBlock"), True)

    def test_it_draws_in_real_pixels_and_redraws_on_resize(self):
        """A scaled viewBox shrinks the axis type to nothing at 390."""
        self.assertIs(self.out.get("realPixels"), True, "the svg is scaled rather than drawn at size")
        self.assertIs(self.out.get("redrawsOnResize"), True, "the chart did not redraw when the window changed")

    def test_the_band_between_the_two_cases_is_a_real_shape(self):
        self.assertIs(self.out.get("band"), True, "the best-case to worst-case band did not render")

    def test_the_crosshair_reads_every_line_at_once(self):
        self.assertIs(self.out.get("crosshairReadsEveryLine"), True,
                      "the readout did not list every series at the hovered date")
        self.assertIs(self.out.get("crosshairKnob"), True, "no knob marked the hovered point on the lines")

    def test_the_chart_follows_both_themes(self):
        self.assertIs(
            self.out.get("followsTheTheme"), True,
            f"the line color did not change with the theme: light {self.out.get('lightColor')}, "
            f"dark {self.out.get('darkColor')}",
        )

    def test_each_legend_swatch_wears_its_own_series_color(self):
        """A color set on the legend ROW outranks the tone class and rendered every swatch alike."""
        self.assertIs(self.out.get("legendSwatchColors"), True)


class BrowserInteractionTests(TempCase):
    """Every interactive piece is CLICKED. A filter that does not filter and a sort that does not
    reorder both look perfect in a screenshot."""

    def test_every_interactive_piece_in_the_gallery_works(self):
        out = _run_browser_script("interactions.js", HERE / "components.html")
        self.assertEqual(out.pop("consoleErrors"), [], "the gallery logged a console error")
        broken = [name for name, value in out.items() if value is False]
        self.assertEqual(broken, [], f"these did not work: {broken}")
        # the gallery carries every one of them, so nothing may report "not on this page"
        absent = [name for name, value in out.items() if value is None]
        self.assertEqual(absent, [], f"the gallery should carry these: {absent}")

    def test_a_built_page_with_components_is_interactive(self):
        page = build_page(self.tmp, COMPONENT_MD, "plan.md", "--look", "tint")
        out = _run_browser_script("interactions.js", page)
        self.assertEqual(out.pop("consoleErrors"), [])
        broken = [name for name, value in out.items() if value is False]
        self.assertEqual(broken, [], f"these did not work: {broken}")
        for required in ("tableFilter", "tableSort", "slider", "checklist", "widthHandles", "navScroll", "navClear", "theme"):
            self.assertIs(out[required], True, f"{required} did not work on a built page")

    def test_a_plain_report_still_has_a_working_nav_handles_and_theme(self):
        page = build_page(self.tmp, SAMPLE_MD, "r.md")
        out = _run_browser_script("interactions.js", page)
        self.assertEqual(out.pop("consoleErrors"), [])
        for required in ("navScroll", "navClear", "widthHandles", "theme"):
            self.assertIs(out[required], True, f"{required} did not work")


# --------------------------------------------------------------------------- token integrity


class TokenIntegrityTests(unittest.TestCase):
    """Every token a surface module or a component reads must be DEFINED by the base template.

    This is the test that would have caught the regression it was written for: renaming --gold to
    --acc left three surface modules reading a token that no longer existed, so the data-report's
    chart bars rendered BLACK and the deck's agenda numbers and "Live document" pill lost their
    color. CSS fails silently on an undefined variable, so nothing errored and nothing warned.
    """

    def defined_tokens(self) -> set[str]:
        base = (HERE / "template.html").read_text(encoding="utf-8")
        import re

        return set(re.findall(r"(--[a-z0-9-]+)\s*:", base))

    def used_tokens(self, text: str) -> set[str]:
        """Tokens READ but not defined locally.

        A component may define its own local custom properties (the timeline sets --cols on the
        block and --from/--span per bar); those are layout parameters, not house tokens, and are
        defined in the same text that reads them.
        """
        import re

        used = set(re.findall(r"var\((--[a-z0-9-]+)", text))
        local = set(re.findall(r"(--[a-z0-9-]+)\s*:", text))
        return used - local

    def test_every_surface_module_reads_only_defined_tokens(self):
        defined = self.defined_tokens()
        for module in sorted((HERE / "templates").glob("*.html")):
            used = self.used_tokens(module.read_text(encoding="utf-8"))
            missing = sorted(used - defined)
            self.assertEqual(missing, [], f"{module.name} reads undefined tokens: {missing}")

    def test_every_gallery_component_reads_only_defined_tokens(self):
        defined = self.defined_tokens()
        for component in build_gallery.COMPONENTS:
            used = self.used_tokens(component.css + component.markup)
            missing = sorted(used - defined)
            self.assertEqual(missing, [], f"{component.cid} reads undefined tokens: {missing}")

    def test_the_built_gallery_reads_only_defined_tokens(self):
        defined = self.defined_tokens()
        used = self.used_tokens((HERE / "components.html").read_text(encoding="utf-8"))
        self.assertEqual(sorted(used - defined), [])

    def test_a_built_page_of_every_surface_reads_only_defined_tokens(self):
        defined = self.defined_tokens()
        tmp = tempfile.TemporaryDirectory()
        try:
            for surface in ("report", "deck", "poster"):
                page = build_page(Path(tmp.name), SAMPLE_MD, f"{surface}.md", "--surface", surface)
                used = self.used_tokens(page.read_text(encoding="utf-8"))
                self.assertEqual(sorted(used - defined), [], surface)
        finally:
            tmp.cleanup()


class ChartTests(TempCase):
    def test_a_whole_number_column_gets_whole_number_axis_labels(self):
        csv_text = "Month,Signups\nJanuary,120\nFebruary,145\nMarch,132\nApril,168\n"
        page = build_page(self.tmp, csv_text, "d.csv", "--surface", "data-report")
        html = page.read_text(encoding="utf-8")
        import re

        labels = re.findall(r'<text class="axlabel" x="0"[^>]*>([^<]+)</text>', html)
        self.assertTrue(labels, "no axis labels were drawn")
        for label in labels:
            self.assertNotIn(".", label, f"a count axis was labeled {label}, a value it cannot hold")

    def test_the_chart_bars_carry_the_tooltip_attributes(self):
        csv_text = "Month,Signups\nJanuary,120\nFebruary,145\n"
        page = build_page(self.tmp, csv_text, "d.csv", "--surface", "data-report")
        html = page.read_text(encoding="utf-8")
        self.assertIn("data-label=", html)
        self.assertIn("data-value=", html)
        # look inside the CHART, not the whole body: the surface module's own comment says
        # "nothing uses a native <title>", and a naive search finds that sentence
        import re

        svg = re.search(r"<svg\b.*?</svg>", html, re.S)
        self.assertIsNotNone(svg, "no chart was drawn")
        self.assertNotIn("<title>", svg.group(0), "native SVG title tooltips are banned")


# --------------------------------------------------------------- the grouped bar

def test_grouped_bar_is_in_the_gallery_catalogue():
    """The component exists in the ONE catalogue, with its own CSS and its own JS."""
    from build_gallery import COMPONENTS

    hit = [c for c in COMPONENTS if c.cid == "grouped-bar"]
    assert hit, "grouped-bar is not in the gallery catalogue"
    comp = hit[0]
    assert comp.css and ".gtrack" in comp.css
    assert comp.js and "data-gbar" in comp.js
    # no hand-written percentage: the widths are computed from data-v
    assert "data-v" in comp.markup
    assert "width:" not in comp.markup, "a width written by hand is a percentage that goes stale"


def test_grouped_bar_reads_only_defined_tokens():
    """Token integrity: every var() the component reads is defined by the base template."""
    import re
    from pathlib import Path

    from build_gallery import COMPONENTS

    comp = [c for c in COMPONENTS if c.cid == "grouped-bar"][0]
    base = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    for token in set(re.findall(r"var\((--[a-z0-9-]+)\)", comp.css)):
        assert token + ":" in base, f"{token} is read by the grouped bar and defined nowhere"


def test_grouped_bar_raw_html_in_markdown_gets_its_assets(tmp_path):
    """A figure written as raw HTML in the source ships with its CSS and its JS, not unstyled."""
    import subprocess
    import sys
    from pathlib import Path

    src = tmp_path / "in.md"
    src.write_text(
        "# A page\n\n## One section\n"
        '<figure class="gbar" data-gbar data-prefix="$">\n'
        '<div class="gbar-rows"><div class="gbar-row"><div class="gbar-name">A</div>\n'
        '<div class="gbar-tracks"><div class="gtrack t-acc" data-v="10"><span></span><b></b></div>'
        "</div></div></div>\n</figure>\n\n## Two section\n\nBody copy.\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.html"
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("build.py")), str(src), str(out),
         "--surface", "report", "--verdict", "v"],
        check=True, capture_output=True,
    )
    page = out.read_text(encoding="utf-8")
    assert ".gtrack" in page, "the grouped bar shipped with no CSS"
    assert "data-gbar" in page and "toLocaleString" in page, "the grouped bar shipped with no JS"


# ------------------------------------ the report surface's stat row above the fold

def test_report_stat_row_sits_above_the_contents_and_the_links(tmp_path):
    """The rule: the executive summary is what a reader sees WITHOUT scrolling.

    A links table of a dozen rows between the verdict and the numbers pushes the summary off the
    first screen, which is why the report surface gets its own stat slot ahead of both.
    """
    import subprocess
    import sys
    from pathlib import Path

    src = tmp_path / "in.md"
    src.write_text(
        "# A page\n\n## One\n\nSee https://example.com/a for one.\n\n"
        "## Two\n\nAnd https://example.com/b for two.\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.html"
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("build.py")), str(src), str(out),
         "--surface", "report", "--verdict", "the answer",
         "--stat", "$9,804.04|Invoiced all time|n", "--stat", "$0.00|Owed today|g",
         "--stat", "$12,000|Estimates with no invoice|a"],
        check=True, capture_output=True,
    )
    page = out.read_text(encoding="utf-8")
    assert 'class="hero-stats"' in page, "the report surface shipped no stat row"
    assert '<div class="stat a">' in page, "the tone field did not reach the card"
    assert "$9,804.04" in page
    # order on the page: verdict, then the numbers, then the contents, then the links
    assert page.index('class="verdict"') < page.index('class="hero-stats"')
    assert page.index('class="hero-stats"') < page.index("Every destination named"),         "the links table is above the numbers, so the summary is off the first screen"
    assert page.index('class="hero-stats"') < page.index("<section"),         "the numbers are inside the content rather than above it"


def test_report_without_stats_ships_no_empty_stat_row(tmp_path):
    """A block with no data is REMOVED, never shipped with a placeholder in it."""
    import subprocess
    import sys
    from pathlib import Path

    src = tmp_path / "in.md"
    src.write_text("# A page\n\n## One\n\nBody.\n\n## Two\n\nBody.\n", encoding="utf-8")
    out = tmp_path / "out.html"
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("build.py")), str(src), str(out),
         "--surface", "report", "--verdict", "the answer"],
        check=True, capture_output=True,
    )
    page = out.read_text(encoding="utf-8")
    assert 'class="hero-stats"' not in page
    assert "HERO_STATS" not in page and "REPLACE" not in page


def test_stat_number_never_wraps_and_the_row_fits_four():
    """A nine-character figure in a four-card row broke mid-number before this rule.

    Two halves of the fix: the row auto-fits so a fourth card is not stranded on its own line,
    and the number is nowrap with a size that gives way before the digits do.
    """
    from pathlib import Path

    base = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    row = [ln for ln in base.splitlines() if ".hero-stats{" in ln][0]
    assert "auto-fit" in row, "a fixed column count strands the fourth stat card"
    num = [ln for ln in base.splitlines() if ".stat .num{" in ln][0]
    assert "white-space:nowrap" in num, "a figure that wraps mid-number is a broken page"
    assert "clamp(" in num, "nowrap without a flexible size overflows instead of wrapping"


def test_tone_utilities_live_in_the_base_template_only():
    """A tone defined inside one component's CSS renders BLACK on a page without that component.

    Caught live: the grouped bar's tracks drew black because .t-acc and friends were declared in
    the LINE CHART's CSS and the page had pulled in no line chart.
    """
    from pathlib import Path

    from build_gallery import COMPONENTS

    base = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    assert ".t-acc{color:var(--acc)}" in base, "the tone utilities are not in the base template"
    for comp in COMPONENTS:
        assert ".t-acc{color:" not in comp.css, (
            f"{comp.cid} redefines a tone utility; the base template owns them"
        )


def test_grouped_bar_legend_swatch_carries_the_tone():
    """The swatch, not the row: a row rule setting its own color out-specifies a .t-* utility."""
    from build_gallery import COMPONENTS

    comp = [c for c in COMPONENTS if c.cid == "grouped-bar"][0]
    assert '<i class="t-acc"></i>' in comp.markup, "the tone is on the row, so the swatch is black"
    assert ".gbar-legend .gk i.t-acc{background:var(--acc)}" in comp.css
