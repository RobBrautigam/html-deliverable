"""A page that moves honors the reader's reduced-motion setting.

The receipt: the house template, its gallery and every surface carried transform transitions (the
section rail's entrance, the tooltip's rise, the fold chevron, the chart readout, the drag-rank
lift) and not one `prefers-reduced-motion` block, measured by grep across `template.html`,
`components.html`, `templates/`, `lint.py` and `build.py` (0 matches in each). WCAG 2.2's
success criterion 2.3.3 (Animation from Interactions) and every serious interface guide read
motion that ignores the setting as a defect.

Now the template carries the block (the fade stays, the travel goes), and `lint.py` WARNS when a
page's stylesheet moves something (a transition or an animation on transform, translate, rotate,
scale, width, height, a position offset or a margin, outside a `no-preference` block) with no such
block, and when a transition animates `all`, written or implied. A CSS comment that mentions a
transition is not motion, nor is a fade, a custom property whose value is unknown, or a zero
duration. The section rail's eased scroll is JavaScript and is the declared exception. A code
review added the two case classes below, each red on the rule it corrected.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import lint

HERE = Path(__file__).resolve().parent

PAGE = """<!doctype html>
<html lang="en" data-theme="light" data-look="tint">
<head><meta charset="utf-8"><title>Motion</title>
<meta name="description" content="A page that moves.">
<style>
{css}
</style></head>
<body><h1>Motion</h1><p>One paragraph.</p></body></html>
"""

REDUCED = "@media (prefers-reduced-motion: reduce){ #tip{transition-property:opacity} }"


def warnings_for(css: str) -> list[str]:
    return lint.check(PAGE.replace("{css}", css), money=False, allow_commands=True)[2]


def motion_warnings(css: str) -> list[str]:
    return [w for w in warnings_for(css) if "reduced-motion" in w or "animates `all`" in w]


def moves(css: str) -> bool:
    """True when the lint says this stylesheet moves something and has no block for it."""
    return any("reduced-motion" in w for w in warnings_for(css))


class ReducedMotionLint(unittest.TestCase):
    def test_a_transform_transition_with_no_block_warns(self):
        found = motion_warnings("#tip{opacity:0; transition:opacity .12s, transform .12s}")
        self.assertEqual(len(found), 1, found)
        self.assertIn("prefers-reduced-motion", found[0])

    def test_a_keyframe_animation_with_no_block_warns(self):
        found = motion_warnings("@keyframes spin{to{transform:rotate(360deg)}} .s{animation:spin 1s linear infinite}")
        self.assertEqual(len(found), 1, found)

    def test_the_block_clears_it(self):
        self.assertEqual(motion_warnings("#tip{transition:opacity .12s, transform .12s}\n" + REDUCED), [])

    def test_a_fade_alone_is_not_motion(self):
        self.assertEqual(motion_warnings("#tip{transition:opacity .12s, color .2s}"), [])

    def test_a_comment_is_not_motion(self):
        self.assertEqual(motion_warnings("/* never transition: transform .5s here */ #tip{color:red}"), [])

    def test_animation_none_is_not_motion(self):
        self.assertEqual(motion_warnings("#tip{animation:none}"), [])

    def test_transition_all_is_named_with_its_line(self):
        found = [w for w in warnings_for("#a{color:red}\n#tip{transition: all .2s}\n" + REDUCED) if "animates `all`" in w]
        self.assertEqual(len(found), 1, found)
        self.assertRegex(found[0], r"line \d+")


class TheReviewCases(unittest.TestCase):
    """A code review probed the first version of the rule with these; each is held here, the
    red half and the quiet half."""

    def test_a_transition_with_no_property_name_means_all(self):
        css = ".a{transition:.25s ease} .a:hover{transform:translateY(-2px)}"
        self.assertTrue(moves(css))
        self.assertTrue(any("animates `all`" in w for w in warnings_for(css + REDUCED)))

    def test_all_later_in_the_segment_or_the_list_is_all(self):
        for value in (".3s ease all", "opacity .2s, all .3s", "opacity .2s cubic-bezier(.2, 1, .3, 1), all .3s"):
            with self.subTest(value=value):
                self.assertTrue(any("animates `all`" in w for w in warnings_for("#t{transition:" + value + "}")))

    def test_the_standalone_and_layout_properties_move(self):
        for prop in ("translate", "rotate", "scale", "width", "height", "top", "left", "margin-top"):
            with self.subTest(prop=prop):
                self.assertTrue(moves("#t{transition:" + prop + " .2s ease-out}"))

    def test_transform_origin_is_not_motion(self):
        self.assertFalse(moves("#t{transition:transform-origin .2s}"))

    def test_a_fade_only_keyframe_is_not_motion(self):
        self.assertFalse(moves("@keyframes glow{from{opacity:.4}to{opacity:1}} .g{animation:glow 2s infinite}"))

    def test_a_moving_keyframe_is_motion(self):
        self.assertTrue(moves("@keyframes rise{from{transform:translateY(8px)}to{transform:none}} .g{animation:rise .3s}"))

    def test_css_wide_keywords_are_not_motion(self):
        for value in ("inherit", "initial", "unset", "revert", "none"):
            with self.subTest(value=value):
                self.assertFalse(moves("#t{animation:" + value + "; transition:" + value + "}"))

    def test_motion_gated_on_no_preference_is_already_safe(self):
        self.assertFalse(moves("@media (prefers-reduced-motion: no-preference){ #t{transition:transform .2s} }"))

    def test_the_boolean_query_counts_as_the_block(self):
        self.assertFalse(moves("#t{transition:transform .2s} @media (prefers-reduced-motion){ #t{transition:none} }"))


class TheSecondRoundCases(unittest.TestCase):
    """The review's second round found these in the parser its first round produced."""

    def test_a_custom_property_is_unknown_not_all(self):
        self.assertEqual(motion_warnings("#t{transition:var(--t-fast)}"), [])

    def test_a_zero_duration_is_no_transition(self):
        self.assertEqual(motion_warnings("#t{transition:0s} #u{transition:0ms}"), [])

    def test_important_is_not_a_property_name(self):
        self.assertTrue(moves(".a{transition:.2s !important} .a:hover{transform:scale(1.02)}"))

    def test_keyframes_in_another_style_block_count(self):
        html = PAGE.replace("{css}", "@keyframes rise{from{transform:translateY(8px)}to{transform:none}}")
        html = html.replace("</head>", "<style>.g{animation:rise .3s}</style></head>")
        self.assertTrue(any("reduced-motion" in w for w in lint.motion_findings(html)))

    def test_a_vendor_prefixed_transition_moves(self):
        self.assertTrue(moves("#t{-webkit-transition:-webkit-transform .2s}"))

    def test_not_no_preference_is_not_a_gate(self):
        self.assertTrue(moves("@media not (prefers-reduced-motion: no-preference){ #t{transition:transform .2s} }"))


class TheHouseFilesPass(unittest.TestCase):
    """The template and the committed gallery carry the block, so a page built on them is quiet."""

    def test_template_has_the_block_and_no_motion_warning(self):
        html = (HERE / "template.html").read_text(encoding="utf-8-sig")
        self.assertRegex(html, r"@media[^{]*prefers-reduced-motion\s*:\s*reduce")
        self.assertEqual(lint.motion_findings(html), [])

    def test_gallery_has_no_motion_warning(self):
        html = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertEqual(lint.motion_findings(html), [])

    def test_every_moving_component_is_named_in_the_block(self):
        """Every gallery rule whose transition moves something is named in the block, found by
        reading the gallery's own stylesheet rather than a list written by hand (a review
        finding), so a new moving component that is not added fails here."""
        html = (HERE / "components.html").read_text(encoding="utf-8")
        block_text = re.sub(r"\s+", " ", lint.reduced_motion_blocks(html))
        block = {re.sub(r"^:root ", "", sel.strip()) for rule in re.findall(r"([^{}]+)\{[^{}]*\}", block_text)
                 for sel in rule.split(",")}
        moving = set()
        for _, css in lint.page_css(html):
            for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
                selector = re.sub(r"\s+", " ", rule.group(1)).strip()
                for decl in lint.TRANSITION_DECL_RE.finditer(rule.group(2)):
                    props = lint.transition_properties(decl.group(2), longhand=bool(decl.group(1)))
                    if any(p == "all" or p in lint.MOVING_PROPERTIES for p in props):
                        moving.add(selector)
        self.assertGreaterEqual(len(moving), 7, moving)
        for selector in sorted(moving):
            self.assertIn(selector, block, f"{selector} moves and the reduced-motion block misses it")

    def test_the_block_names_the_growing_bar(self):
        """The grouped bar grows by width, not by transform: the block drops that too (finding L2)."""
        self.assertIn(".gtrack > span", lint.reduced_motion_blocks((HERE / "template.html").read_text(encoding="utf-8-sig")))


if __name__ == "__main__":
    unittest.main()
