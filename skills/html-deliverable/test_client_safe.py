"""Client-safe by construction.

A page is read by somebody who was never told which other companies exist. These tests hold the
four promises that make it impossible to hand them one that says:

1. the look token names nobody;
2. the builder strips what a reader never needs, including the maker's mark nobody asked for;
3. the lint reads the WHOLE file against the wall list, and refuses a page bound for outside;
4. the shipping templates themselves carry no company, client or person in their comments.

The defect they are written against: a client one-pager built from the house template and sent
unchanged carried another client's short name in a CSS selector and a third company's name in a
comment, with nothing visible on the page to show for it.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

import build
import lint

HERE = Path(__file__).resolve().parent

SAMPLE_MD = """# The record

A lead paragraph that says what this is.

## One
Body copy, and a destination https://example.com/a to name.

## Two
More body copy, and a second destination https://example.com/b for the table.
"""

LEAKY_MD = """# The record

A lead paragraph that says what this is.

## One
The work ran through Initech and the build was done by Acme Holdings.

## Two
More body copy, and a destination https://example.com/b for the table.
"""


class TempCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, text: str, name: str, *args: str) -> str:
        source = self.tmp / name
        source.write_text(text, encoding="utf-8")
        out = source.with_suffix(".html")
        self.assertEqual(build.main([str(source), str(out), *args]), 0)
        return out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- 1. the token


class LookTokenTests(TempCase):
    def test_every_emitted_page_wears_a_neutral_look_token_and_nothing_from_the_wall(self):
        for surface in ("report", "deck", "poster", "data-report"):
            args = ["--surface", surface]
            text = "Month,Signups\nJanuary,120\nFebruary,145\n" if surface == "data-report" else SAMPLE_MD
            name = "d.csv" if surface == "data-report" else f"{surface}.md"
            html = self.build(text, name, *args)
            look = re.search(r'data-look="([^"]+)"', html)
            self.assertIsNotNone(look, f"{surface} emits no look token")
            self.assertIn(look.group(1), {"tint", "classic"}, f"{surface} emits a look that is not a house look")
            self.assertEqual(lint.wall_hits(html), [], f"{surface} carries a wall-list name")

    def test_the_tint_dark_rule_survives_the_strip(self):
        html = self.build(SAMPLE_MD, "r.md", "--look", "tint")
        self.assertIn(':root[data-look="tint"][data-theme="dark"]{', html)
        # the rule still sets its tokens: stripping comments must never take the block with it
        # the window is a slice of the block, so it grows when the block does
        dark = html[html.index(':root[data-look="tint"][data-theme="dark"]{') :][:900]
        for token in ("--bg:", "--acc:", "--grid:", "--on-acc:"):
            self.assertIn(token, dark)


# --------------------------------------------------------------------------- 2. the strip


class StripTests(TempCase):
    def setUp(self) -> None:
        super().setUp()
        self.html = self.build(SAMPLE_MD, "r.md")

    def test_no_css_comment_survives_in_the_emitted_page(self):
        style = self.html[self.html.index("<style>") : self.html.index("</style>")]
        self.assertNotIn("/*", style)

    def test_no_html_comment_survives_in_the_emitted_page(self):
        outside = build.SCRIPT_OR_STYLE_RE.split(self.html)
        for index in range(0, len(outside), 3):
            self.assertNotIn("<!--", outside[index])

    def test_the_page_still_renders_its_content_after_the_strip(self):
        for expected in ("<h1>The record", "Body copy", "Key links", 'id="sidenav"', "requestAnimationFrame"):
            self.assertIn(expected, self.html)
        self.assertEqual(lint.check(self.html, money=False, allow_commands=False)[0], [])

    def test_a_comment_marker_inside_a_script_string_is_not_treated_as_a_comment(self):
        page = '<html><body><script>var a = "<!-- not a comment -->";</script><!-- gone --></body></html>'
        stripped = build.strip_comments(page)
        self.assertIn('"<!-- not a comment -->"', stripped)
        self.assertNotIn("<!-- gone -->", stripped)

    def test_stripping_a_page_with_no_comments_changes_nothing_at_all(self):
        """The invariant that catches a strip which ADDS text.

        The first version rejoined re.split's tag-name group and wrote `</style>style` into every
        page, which no comment test would ever have noticed: the comments were gone, and two
        stray words were not.
        """
        page = (
            "<!doctype html>\n<html><head><style>\n  body{color:#000}\n</style>\n</head>\n"
            "<body><h1>A title</h1>\n<script>\n  var a = 1;\n</script>\n"
            "<script>\n  var b = 2;\n</script>\n</body></html>\n"
        )
        self.assertEqual(build.strip_comments(page), page)

    def test_no_tag_name_is_written_back_into_a_built_page(self):
        for stray in ("</style>style", "</script>script", "</style>\nstyle", "</script>\nscript"):
            self.assertNotIn(stray, self.html)

    def test_a_comment_inside_a_css_string_is_content_not_a_comment(self):
        """`content:"a /* b */ c"` is what the page RENDERS."""
        css = '.badge::after{content:"literal /* not a comment */ text"}\n'
        self.assertEqual(build.strip_css_comments(css), css)
        self.assertEqual(build.strip_css_comments(".a{color:red} /* gone */\n"), ".a{color:red}\n")

    def test_a_multi_line_css_comment_takes_its_own_lines_and_nothing_else(self):
        css = ".a{color:red}\n  /* one\n     two */\n.b{color:blue}\n"
        self.assertEqual(build.strip_css_comments(css), ".a{color:red}\n.b{color:blue}\n")

    def test_a_shared_selector_list_is_left_alone_rather_than_broken(self):
        """Dropping one name out of a list by regex leaves `.mark,` behind, which is broken CSS."""
        page = "<style>\n.mark, .lockup{display:flex}\n.lockup{color:red}\n</style>"
        dropped = build.drop_css_rule(page, ".lockup")
        self.assertIn(".mark, .lockup{display:flex}", dropped)
        self.assertNotIn(".lockup{color:red}", dropped)

    def test_dropping_a_rule_never_matches_a_longer_class_name(self):
        page = "<style>\n.mark{a:1}\n.marker{b:2}\n.mark-alt{c:3}\n</style>"
        dropped = build.drop_css_rule(page, ".mark")
        self.assertNotIn(".mark{a:1}", dropped)
        self.assertIn(".marker{b:2}", dropped)
        self.assertIn(".mark-alt{c:3}", dropped)

    def test_the_mark_rules_go_when_no_mark_renders(self):
        self.assertNotIn(".lockup{", self.html)
        self.assertNotIn(".mark{", self.html)

    def test_the_mark_rule_stays_when_a_mark_renders(self):
        html = self.build(SAMPLE_MD, "m.md", "--surface", "poster", "--mark", "Built by the studio")
        self.assertIn(".mark{", html)
        self.assertIn(">Built by the studio<", html)

    def test_no_surface_template_hard_codes_a_mark(self):
        for path in (HERE / "templates").glob("*.html"):
            body = path.read_text(encoding="utf-8")
            self.assertNotIn("BUILT BY", body.upper().replace("BUILT BY {{MARK}}", ""), path.name)


# --------------------------------------------------------------------------- 3. the wall


class WallListTests(unittest.TestCase):
    def test_the_list_is_data_and_it_loads(self):
        """The shipped list carries two fictional samples; replace them with your own names."""
        names = lint.load_wall()
        self.assertGreaterEqual(len(names), 2)
        for required in ("acme", "acme holdings", "acmeholdings.com", "initech"):
            self.assertIn(required, names, f"{required} is not on the wall list")

    def test_a_missing_list_is_an_error_not_a_quiet_pass(self):
        with self.assertRaises(FileNotFoundError):
            lint.load_wall(HERE / "no-such-wall-list.txt")

    def test_the_match_is_whole_word_and_blind_to_the_separator(self):
        self.assertTrue(lint.wall_regex("acme holdings").search("the Acme Holdings invoice"))
        self.assertTrue(lint.wall_regex("acme holdings").search("acme-holdings"))
        self.assertTrue(lint.wall_regex("acme holdings").search("acmeholdings"))
        self.assertTrue(lint.wall_regex("initech").search("c:/work/initech-audit"))
        self.assertTrue(lint.wall_regex("initech").search('data-client="initech"'))

    def test_an_ordinary_word_is_not_a_hit(self):
        for innocent in ("macme", "acmes", "the initechnical team", "reinitech", "a holdings company"):
            for name in lint.load_wall():
                self.assertIsNone(
                    lint.wall_regex(name).search(innocent), f"{name} matched inside {innocent}"
                )

    def test_a_persons_signature_is_not_a_company(self):
        """A person's name on their own document is not a leak: the wall lists companies."""
        line = "<span><b>From</b> Dana Whitfield</span>"
        self.assertEqual(lint.wall_hits(line), [])

    def test_overlapping_names_report_once_as_the_longest(self):
        hits = lint.wall_hits("delivered by Acme Holdings")
        self.assertEqual([name for name, _, _ in hits], ["acme holdings"])

    def test_allow_switches_off_a_name_and_its_spellings(self):
        page = "Acme runs acmeholdings.com and also names Initech"
        names = [name for name, _, _ in lint.wall_hits(page, ["Acme"])]
        self.assertEqual(names, ["initech"])


class WallVerdictTests(TempCase):
    def failures(self, html: str, **kwargs) -> list[str]:
        return lint.check(html, money=False, allow_commands=False, **kwargs)[0]

    def warnings(self, html: str, **kwargs) -> list[str]:
        return lint.check(html, money=False, allow_commands=False, **kwargs)[2]

    def test_an_external_page_fails_on_a_leak(self):
        html = self.build(LEAKY_MD, "leak.md", "--for", "A client")
        self.assertTrue(any("wall list" in f for f in self.failures(html)), self.failures(html))

    def test_an_internal_page_only_warns(self):
        html = self.build(LEAKY_MD, "leak.md", "--audience", "internal")
        self.assertEqual([f for f in self.failures(html) if "wall list" in f], [])
        self.assertTrue(any("wall list" in w for w in self.warnings(html)))

    def test_the_page_carries_its_own_audience_so_nobody_has_to_remember_a_flag(self):
        html = self.build(LEAKY_MD, "leak.md", "--for", "A client")
        self.assertIn('data-audience="external"', html)
        self.assertEqual(lint.resolve_audience(html), "external")
        # and the flag still wins over the page
        self.assertEqual(lint.resolve_audience(html, "internal"), "internal")

    def test_a_page_with_no_audience_attribute_is_treated_as_internal(self):
        self.assertEqual(lint.resolve_audience("<html><body>x</body></html>"), "internal")

    def test_the_audience_is_read_however_a_hand_written_page_quotes_it(self):
        """Reading a quoted-differently attribute as internal downgrades a refusal to a note."""
        for tag in (
            '<html data-audience="external">',
            "<html data-audience='external'>",
            "<html data-audience=external>",
            '<html lang="en" data-theme="light" data-audience="external" data-look="tint">',
        ):
            self.assertEqual(lint.resolve_audience(tag), "external", tag)

    def test_a_name_hidden_behind_an_entity_is_still_a_leak(self):
        """The browser renders `Acme&nbsp;Holdings` as the company."""
        names = [name for name, _, _ in lint.wall_hits("<p>Acme&nbsp;Holdings delivered it</p>")]
        self.assertTrue(any(name.startswith("acme holdings") for name in names), names)

    def test_a_tag_name_is_html_syntax_not_a_company(self):
        wall = ["meta", "acme"]
        page = '<head><meta charset="utf-8"></head><body>built by Acme</body>'
        names = [name for name, _, _ in lint.wall_hits(page, names=wall)]
        self.assertEqual(names, ["acme"])

    def test_allow_clears_the_company_this_page_is_entitled_to_name(self):
        html = self.build(LEAKY_MD, "leak.md", "--for", "A client")
        cleared = self.failures(html, allow=["Acme Holdings", "Initech"])
        self.assertEqual([f for f in cleared if "wall list" in f], [])

    def test_the_check_reads_attributes_and_stylesheets_not_only_the_prose(self):
        page = (
            '<!doctype html><html data-audience="external" data-client="initech"><head>'
            "<style>/* built for Acme Holdings */</style></head><body>Nothing visible.</body></html>"
        )
        names = [name for name, _, _ in lint.wall_hits(page)]
        self.assertIn("initech", names)
        self.assertIn("acme holdings", names)

    def test_the_builder_defaults_to_external(self):
        self.assertEqual(build.resolve_audience("auto"), "external")
        self.assertEqual(build.resolve_audience("internal"), "internal")
        self.assertEqual(build.resolve_audience("external"), "external")

    def test_the_builder_warns_at_build_time_so_the_author_hears_it_first(self):
        html = self.build(LEAKY_MD, "leak.md", "--for", "A client")
        notice = build.wall_notice(html, [], "external")
        self.assertTrue(notice and "REFUSE" in notice[0], notice)
        self.assertEqual(build.wall_notice(html, ["Acme Holdings", "Initech"], "external"), [])


# --------------------------------------------------------------------------- 4. the templates


# The people the sample documents in this suite name. Extend it with the people your own
# documents name, so a shipping file that mentions one of them is caught here.
PERSON_RE = re.compile(r"\b(Dana|Whitfield|Priya|Marcus)\b")


def person_lines(text: str) -> list[str]:
    """The lines naming a person, reported as themselves."""
    return [line.strip()[:90] for line in text.splitlines() if PERSON_RE.search(line)]


class ShippingFileTests(unittest.TestCase):
    """Every byte of these files ends up inside a delivered page, so they name nobody."""

    def test_the_surface_templates_name_no_company_client_or_person(self):
        for path in sorted((HERE / "templates").glob("*.html")):
            text = path.read_text(encoding="utf-8")
            hits = lint.wall_hits(text)
            self.assertEqual(hits, [], f"{path.name}: {hits}")
            self.assertEqual(person_lines(text), [], path.name)

    def test_the_base_template_names_nobody(self):
        text = (HERE / "template.html").read_text(encoding="utf-8")
        self.assertEqual(lint.wall_hits(text), [], "the base template carries a wall-list name")
        self.assertEqual(person_lines(text), [], "the base template's comments name no person")

    def test_the_gallery_names_the_rules_and_says_who_reads_it(self):
        gallery = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertIn("Client-safe by construction", gallery)
        self.assertIn('data-audience="internal"', gallery)

    def test_the_skill_and_design_docs_carry_the_section(self):
        for name in ("SKILL.md", "DESIGN.md"):
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertIn("Client-safe by construction", text, name)


if __name__ == "__main__":
    unittest.main()
