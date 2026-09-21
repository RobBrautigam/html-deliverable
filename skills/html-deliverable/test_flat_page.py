#!/usr/bin/env python3
"""Tests for the flat page, the picture, and the part that lost its card.

    python -m pytest skills/html-deliverable/test_flat_page.py

The defect this covers: a 7,900-word reply to a partner's designed page was built flat from a
markdown record with build.py, linted green at three widths, and still read as a wall of words:
"a written document from top to bottom". A green lint was not a design pass, so the lint
learned to see it.
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
import build_gallery  # noqa: E402
import lint  # noqa: E402


FILLER = (
    "The order record should be able to answer, with no human memory involved, what we charged "
    "and what it cost us and what the gross profit was and what each partner is owed. "
)


def long_section(index: int, *, summary: bool = False, words: int = 400) -> str:
    """One section of real prose, optionally opening with a summary strip."""
    body = (FILLER * ((words // len(FILLER.split())) + 1)).strip()
    strip = (
        '<div class="stage-summary">'
        '<div class="ss-row agree"><span class="ss-k">Agree</span><span class="ss-v">The one line.</span></div>'
        "</div>"
        if summary
        else ""
    )
    return f'<section id="s{index}"><div class="sec-num">{index}</div><h2>Stage {index}</h2>{strip}<p>{body}</p></section>'


def page(body: str, *, audience: str = "") -> str:
    """A minimal page that satisfies every OTHER lint rule, so one check is under test."""
    tag = f' data-audience="{audience}"' if audience else ""
    return (
        f'<!doctype html><html lang="en" data-theme="light" data-look="tint"{tag}><head><style>'
        ":root{--wrap-w:1080px}\n/* requestAnimationFrame */\n</style></head><body>"
        '<button class="grip l"></button><button class="grip r"></button>'
        '<nav id="sidenav"><button data-target="s1">A</button><button data-target="s2">B</button></nav>'
        f'<div class="wrap">{body}</div>'
        "<script>requestAnimationFrame(function(){});</script></body></html>"
    )


def flat_hits(html: str, audience: str = "auto") -> tuple[list[str], list[str]]:
    failures, _notes, warnings = lint.check(
        html, money=False, allow_commands=True, audience=audience
    )
    return (
        [f for f in failures if "reads flat" in f],
        [w for w in warnings if "reads flat" in w],
    )


class TheFlatPageCheck(unittest.TestCase):
    def test_a_long_page_with_no_summary_blocks_warns(self):
        html = page("".join(long_section(n) for n in range(1, 10)))
        failures, warnings = flat_hits(html)
        self.assertEqual(failures, [], "an internal page is warned, never refused")
        self.assertTrue(
            any("no summary block" in w for w in warnings),
            f"nine long sections with no summary strip drew no warning: {warnings}",
        )

    def test_the_same_page_is_REFUSED_when_the_audience_is_external(self):
        html = page("".join(long_section(n) for n in range(1, 10)))
        failures, _ = flat_hits(html, audience="external")
        self.assertTrue(
            any("no summary block" in f for f in failures),
            f"an external flat page must fail, not warn: {failures}",
        )

    def test_the_page_own_audience_attribute_is_enough_to_refuse_it(self):
        html = page("".join(long_section(n) for n in range(1, 10)), audience="external")
        failures, _ = flat_hits(html)
        self.assertTrue(failures, "the page declares itself external and must still be refused")

    def test_a_composed_page_passes(self):
        body = "".join(long_section(n, summary=True) for n in range(1, 10))
        body += '<div class="asks"><div class="asks-head">Questions for you</div><ol><li>One.</li></ol></div>'
        failures, warnings = flat_hits(page(body), audience="external")
        self.assertEqual(failures, [], "a summary strip per part plus a colored block is the fix")
        self.assertEqual(warnings, [])

    def test_summaries_without_any_color_are_still_reported(self):
        """The rule needs BOTH halves. The page that produced it carried one verdict box."""
        body = "".join(long_section(n, summary=True) for n in range(1, 10))
        _failures, warnings = flat_hits(page(body))
        self.assertTrue(
            any("color" in w for w in warnings),
            f"a page with no colored block at all drew no warning: {warnings}",
        )

    def test_a_short_page_never_trips_however_flat_it_is(self):
        html = page(long_section(1) + long_section(2))
        failures, warnings = flat_hits(html, audience="external")
        self.assertEqual((failures, warnings), ([], []), "under 3,000 words the check is silent")

    def test_a_part_made_of_code_samples_is_not_a_wall_of_argument(self):
        """The gallery is 28 sections of demo plus snippet, and it is not the defect."""
        sample = "<pre><code>" + ("a_long_identifier_name " * 300) + "</code></pre>"
        body = "".join(
            f'<section id="s{n}"><h2>S{n}</h2><p>Two lines of prose above it.</p>{sample}</section>'
            for n in range(1, 10)
        ) + '<div class="callout">A colored aside.</div>'
        _failures, warnings = flat_hits(page(body))
        self.assertEqual(warnings, [], f"code samples counted as prose: {warnings}")


class TheTwoComponentsAreInTheGallery(unittest.TestCase):
    def setUp(self):
        self.catalogue = {c.cid: c for c in build_gallery.COMPONENTS}
        self.gallery = (HERE / "components.html").read_text(encoding="utf-8")

    def test_the_part_summary_strip_is_a_house_component(self):
        self.assertIn("part-summary", self.catalogue)
        markup = self.catalogue["part-summary"].markup
        self.assertIn('class="stage-summary"', markup)
        self.assertIn('class="ss-row agree"', markup)
        self.assertIn('<details class="fold" data-fold=', markup)

    def test_the_questions_block_is_a_house_component(self):
        self.assertIn("asks", self.catalogue)
        component = self.catalogue["asks"]
        self.assertIn('class="asks"', component.markup)
        self.assertIn('class="rec"', component.markup)
        self.assertIn("--ask-soft", component.css)

    def test_the_fold_remembers_its_state_and_opens_for_printing(self):
        js = self.catalogue["part-summary"].js
        self.assertIn("localStorage", js)
        self.assertIn("beforeprint", js)
        self.assertIn("afterprint", js)
        self.assertIn("try {", js, "every storage read is guarded: a private window throws")

    def test_the_solid_chips_read_a_token_rather_than_a_raw_white(self):
        """In dark mode the accent is LIGHT, so white text on it fails contrast."""
        css = self.catalogue["asks"].css
        self.assertIn(".chip.q{background:var(--ask); color:var(--on-acc)}", css)
        self.assertNotIn("#ffffff", css)

    def test_the_built_gallery_carries_both_demos_and_both_snippets(self):
        for anchor in ('id="c-part-summary"', 'id="c-asks"'):
            self.assertIn(anchor, self.gallery, f"{anchor} is missing: rebuild the gallery")
        # the demo and the snippet are the same text by construction, so one escaped copy of a
        # distinctive line proves the pair
        self.assertIn('&lt;div class="stage-summary"&gt;', self.gallery)
        self.assertIn('&lt;div class="asks"&gt;', self.gallery)

    def test_the_design_authority_lists_them_too(self):
        design = (HERE / "DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("Part summary strip", design)
        self.assertIn("Questions for the reader", design)
        self.assertIn("`.asks > .asks-head", design)

    def test_the_interactions_harness_drives_a_fold(self):
        harness = (HERE / "interactions.js").read_text(encoding="utf-8")
        self.assertIn("results.folds", harness)
        self.assertIn("details.fold[data-fold]", harness)


# --------------------------------------------------------------------------- the second delta


# A real explainer page as it SHIPPED, parts 4 and 5, trimmed to the shape and kept otherwise
# verbatim. The fix was one diff: the head's own `</div>` is missing after the title, so the body
# is inside the part head and the div that closes at the end of the part is the head's, not a
# section's.
EXPLAINER_PRE_FIX = """  <section id="the-alarm"><h3 class="sec-title">The alarm</h3><p>It already proved itself.</p>
  </section>

  <div class="part-head" id="where-a-person-touches-it">
    <div class="part-num">Part 4</div>
    <h2 class="part-title">Where a person touches it</h2>
<p>Five things, and only five. Everything else runs on its own.</p>
<ol>
<li><strong>Pasting the share link.</strong> Someone opens the client's page and pastes it.</li>
<li><strong>Setting the views target.</strong> A number typed into the card.</li>
</ol>
<p>The first four are all done from that one tab.</p>
  </div>

  <div class="part-head" id="glossary">
    <div class="part-num">Part 5</div>
    <h2 class="part-title">Glossary</h2>
<table>
<thead><tr><th>Term</th><th>What it means</th></tr></thead>
<tbody><tr><td>Campaign</td><td>One client's run on the platform.</td></tr></tbody>
</table>
  </div>
"""

# The same markup after the fix: the head closes on its title and a section opens.
EXPLAINER_POST_FIX = (
    EXPLAINER_PRE_FIX.replace(
        '<h2 class="part-title">Where a person touches it</h2>\n',
        '<h2 class="part-title">Where a person touches it</h2>\n  </div>\n\n'
        '  <section id="where-a-person-touches-it-body">\n',
    )
    .replace(
        '<h2 class="part-title">Glossary</h2>\n',
        '<h2 class="part-title">Glossary</h2>\n  </div>\n\n  <section id="glossary-body">\n',
    )
    .replace("</ol>\n<p>The first four are all done from that one tab.</p>\n  </div>",
             "</ol>\n<p>The first four are all done from that one tab.</p>\n  </section>")
    .replace("</table>\n  </div>", "</table>\n  </section>")
)

PART_MD = """# The record

A lead paragraph before any part.

# Where a person touches it

Three places, and each one is a person rather than a job: the send, the fulfilment and the
statuses. None of them is automated today and none of them is about to be.

# The map

## What runs when

The job wakes on a thirty minute tick and dispatches whatever is due.
"""


class APartBodyGetsACard(unittest.TestCase):
    """Two parts of a real page were not wrapped in the white card every section gets. The fix
    is in the builder; these tests make sure it never happens again."""

    def build(self, text: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "doc.md"
            source.write_text(text, encoding="utf-8")
            out = source.with_suffix(".html")
            self.assertEqual(build.main([str(source), str(out)]), 0)
            return out.read_text(encoding="utf-8")

    def test_a_part_with_no_sections_under_it_renders_its_body_in_a_card(self):
        html = self.build(PART_MD)
        self.assertIn('<section id="where-a-person-touches-it-body">', html)
        self.assertIn("Three places, and each one is a person", html)

    def test_the_body_is_not_left_inside_the_part_head(self):
        html = self.build(PART_MD)
        start = html.index('<div class="part-head" id="where-a-person-touches-it"')
        head = html[start : html.index("<section", start)]
        self.assertNotIn("Three places, and each one is a person", head)

    def test_a_part_that_opens_sections_keeps_its_lede_where_it_was(self):
        """The approved shape does not move: only a SECTIONLESS part changes."""
        html = self.build(PART_MD)
        start = html.index('<div class="part-head" id="the-map"')
        head = html[start : html.index("<section", start)]
        self.assertIn('<h2 class="part-title">The map</h2>', head)
        self.assertNotIn('id="the-map-body"', html)

    def test_the_built_page_passes_the_lint(self):
        failures = lint.check(self.build(PART_MD), money=False, allow_commands=True)[0]
        self.assertEqual([f for f in failures if "part" in f], [], failures)

    def test_the_lint_refuses_a_part_head_followed_by_bare_prose(self):
        broken = page(
            '<div class="part-head" id="p1"><div class="part-num">Part 1</div>'
            '<h2 class="part-title">Where a person touches it</h2></div>'
            "<p>Bare prose on the page ground, with no card around it.</p>"
            '<section id="s1"><h2>After</h2><p>Body.</p></section>'
        )
        failures = lint.check(broken, money=False, allow_commands=True)[0]
        self.assertTrue(
            any("bare content" in f for f in failures),
            f"the lint let a part head introduce bare prose: {failures}",
        )

    def test_the_lint_passes_a_part_head_followed_by_a_card(self):
        fine = page(
            '<div class="part-head" id="p1"><div class="part-num">Part 1</div>'
            '<h2 class="part-title">Where a person touches it</h2></div>'
            '<section id="p1-body"><p>The same words, in a card.</p></section>'
            '<section id="s1"><h2>After</h2><p>Body.</p></section>'
        )
        failures = lint.check(fine, money=False, allow_commands=True)[0]
        self.assertEqual([f for f in failures if "bare content" in f], [], failures)

    def test_the_lint_refuses_a_part_head_that_swallowed_its_own_body(self):
        """The form that SHIPPED, taken from a real explainer's pre-fix markup.

        The part head's `</div>` is never written after the title, so the heading and the whole
        part body live in one div and the next part head is what "follows" the part. The
        followed-by test alone reads that as clean, which is why two uncarded parts reached the
        reader.
        """
        failures = lint.check(page(EXPLAINER_PRE_FIX), money=False, allow_commands=True)[0]
        carried = [f for f in failures if "carries its body inside the part head" in f]
        self.assertEqual(len(carried), 2, f"expected parts 4 and 5 to be caught: {failures}")
        self.assertTrue(any("Where a person touches it" in f for f in carried), carried)
        self.assertTrue(any("Glossary" in f for f in carried), carried)

    def test_the_lint_clears_the_same_two_parts_once_they_are_carded(self):
        """The same markup with the fix applied: `</div>` closes the head, a section opens."""
        failures = lint.check(page(EXPLAINER_POST_FIX), money=False, allow_commands=True)[0]
        self.assertEqual([f for f in failures if "part" in f], [], failures)

    def test_a_part_that_opens_sections_may_still_carry_a_lede(self):
        """The approved shape is not collateral damage: a lede above real cards is fine."""
        fine = page(
            '<div class="part-head" id="p1"><div class="part-num">Part 1</div>'
            '<h2 class="part-title">The map</h2><p>One paragraph of lede.</p></div>'
            '<section id="s1"><h3>After</h3><p>Body.</p></section>'
        )
        failures = lint.check(fine, money=False, allow_commands=True)[0]
        self.assertEqual([f for f in failures if "part head" in f], [], failures)

    def test_the_nested_part_num_div_does_not_close_the_block_early(self):
        """The bug this found: a non-greedy match closed on the inner div, so the part's own
        heading looked like the content that followed it."""
        body = (
            '<div class="part-head" id="p1"><div class="part-num">Part 1</div>'
            '<h2 class="part-title">A part</h2><p>Its lede.</p></div>'
            '<section id="s1"><h2>After</h2><p>Body.</p></section>'
        )
        blocks = lint.part_head_blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertIn("Its lede.", blocks[0][2])


class ThePicture(unittest.TestCase):
    """A workflow page with no picture is not done."""

    def setUp(self):
        self.component = {c.cid: c for c in build_gallery.COMPONENTS}["flow"]
        self.gallery = (HERE / "components.html").read_text(encoding="utf-8")

    def test_the_map_is_drawn_from_the_json_inside_the_figure(self):
        self.assertIn('<script type="application/json" class="flow-data">', self.component.markup)
        self.assertIn('"lanes"', self.component.markup)
        self.assertIn('"edges"', self.component.markup)
        self.assertIn("JSON.parse", self.component.js)

    def test_it_is_inline_svg_on_the_tokens_rather_than_an_image(self):
        self.assertIn("createElementNS", self.component.js)
        self.assertIn("var(--", self.component.js)
        self.assertNotIn("<img", self.component.markup)

    def test_a_phone_scrolls_the_map_instead_of_shrinking_it(self):
        self.assertIn("min-width:var(--flow-min", self.component.css)
        self.assertIn("--flow-min:680px", self.component.css)
        self.assertIn("Swipe the map sideways", self.component.css)

    def test_the_built_gallery_carries_the_figure_and_its_snippet(self):
        self.assertIn('id="c-flow"', self.gallery)
        self.assertIn('<figure class="flow"', self.gallery)
        self.assertIn("&lt;figure class=\"flow\"", self.gallery)

    def test_the_design_authority_names_it_and_calls_it_mandatory(self):
        design = (HERE / "DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("The picture: a lane-and-column map of a whole path", design)
        self.assertIn("A workflow page with no picture is not done", design)

    def test_the_two_token_families_are_house_tokens_in_every_theme(self):
        """A component that defines its own house colors is the drift the system exists to stop."""
        template = (HERE / "template.html").read_text(encoding="utf-8")
        for token in ("--violet:", "--violet-soft:", "--violet-ink:", "--ask:", "--ask-soft:", "--ask-ink:"):
            self.assertGreaterEqual(
                template.count(token), 4, f"{token} is missing from a theme block"
            )
        self.assertNotIn("--ask:#", self.component.css)


if __name__ == "__main__":
    unittest.main()
