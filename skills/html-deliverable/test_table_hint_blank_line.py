"""A `[table: ...]` hint written on the line directly above its table still binds to that table.

The receipt: an architecture page's first build carried `[table: plain]` directly
above a markdown table, with no blank line between them; Markdown read the hint and every row of
the table as ONE paragraph, so the table reached the reader as pipes in a sentence, and the lint
passed a page that measured one table instead of two. Caught only by looking at the capture.

The builder now puts the blank line in, so the hint binds to the table the way its author meant,
and a fenced block (a paste-ready example that shows the hint) is left exactly as written.
"""
from __future__ import annotations

import unittest

from test_design_system import TempCase, build, build_page  # noqa: E402

HINT_NO_BLANK_MD = """# A hint with no blank line

Lead.

## 1. The long table that must stay plain

[table: plain]
| Item | N |
|---|---|
| one | 1 |
| two | 2 |
| three | 3 |
| four | 4 |
| five | 5 |
| six | 6 |
| seven | 7 |

## 2. A second table, written the usual way

| Name | Score |
|---|---|
| alpha | 10 |
| bravo | 20 |
"""


class TableHintBlankLineTests(TempCase):
    def test_a_hint_directly_above_a_table_still_binds_to_it(self):
        html = build_page(self.tmp, HINT_NO_BLANK_MD, "h.md").read_text(encoding="utf-8")
        self.assertEqual(html.count("<table"), 2, "the hinted table was swallowed into a paragraph")
        self.assertNotIn("[table:", html, "the hint reached the reader as text")
        self.assertNotIn("| Item | N |", html, "the table's rows reached the reader as pipes")
        # the hint still did its job: the seven-row table stays plain (a long table is otherwise
        # upgraded to the sortable data table)
        self.assertNotIn('class="dt-wrap"', html.split("A second table")[0])

    def test_sortable_hint_directly_above_a_short_table_still_forces_it_in(self):
        md = "# S\n\nLead.\n\n## 1. Short\n\n[table: sortable]\n| A | B |\n|---|---|\n| one | 1 |\n| two | 2 |\n"
        html = build_page(self.tmp, md, "s.md").read_text(encoding="utf-8")
        self.assertIn('class="dt-wrap"', html)
        self.assertNotIn("[table:", html)

    def test_the_separation_leaves_a_fenced_block_as_written(self):
        fenced = "```\n[table: plain]\n| a | b |\n|---|---|\n```\n"
        self.assertEqual(build.separate_table_hints(fenced), fenced)
        tilde = "~~~\n[table: sortable]\n| a | b |\n~~~\n"
        self.assertEqual(build.separate_table_hints(tilde), tilde)

    def test_a_four_backtick_fence_holding_a_three_backtick_fence_is_left_as_written(self):
        # A review finding: a paste-ready prompt is a four-backtick fence, and a
        # three-backtick line inside it does not close it.
        paste = "````\nPaste this:\n```\n[table: plain]\n| a | b |\n|---|---|\n```\n````\n"
        self.assertEqual(build.separate_table_hints(paste), paste)

    def test_fences_are_tracked_the_way_the_renderer_tracks_them(self):
        # Python-Markdown opens a fence at column 0 and closes it only on the
        # exact opening run, so a longer run or an indented run inside it is content.
        for src in ("```\n````\n[table: plain]\n| a |\n|---|\n```\n",
                    "```\n  ```\n[table: plain]\n| a |\n|---|\n```\n",
                    "````\n`````\n[table: plain]\n| a |\n|---|\n````\n"):
            with self.subTest(src=src):
                self.assertEqual(build.separate_table_hints(src), src)
        # and an indented run at the top level opens no fence, so the hint under it still binds
        self.assertEqual(build.separate_table_hints("  ```\n[table: plain]\n| a |\n|---|\n"),
                         "  ```\n\n[table: plain]\n\n| a |\n|---|\n")

    def test_a_hint_indented_as_code_is_left_alone(self):
        # Four spaces make an indented code block, never a hint.
        src = "    code line\n    [table: plain]\n    | a |\n    |---|\n"
        self.assertEqual(build.separate_table_hints(src), src)

    def test_a_setext_underline_is_not_a_pipeless_delimiter_row(self):
        # "---" under a line is a heading or a rule, not a table's delimiter.
        src = "[table: plain]\nCosts | Notes\n---\n"
        self.assertEqual(build.separate_table_hints(src), src)

    def test_a_pipeless_table_and_a_hint_under_prose_are_separated(self):
        # A review finding: the tables extension renders a table whose rows carry
        # no leading pipe, and a hint written under a line of prose joined that paragraph.
        self.assertEqual(build.separate_table_hints("[table: plain]\na | b\n--|--\n1 | 2\n"),
                         "[table: plain]\n\na | b\n--|--\n1 | 2\n")
        self.assertEqual(build.separate_table_hints("Some prose.\n[table: plain]\n| a |\n|---|\n"),
                         "Some prose.\n\n[table: plain]\n\n| a |\n|---|\n")
        # a pipe in prose under a hint, with no delimiter row after it, is not a table
        self.assertEqual(build.separate_table_hints("[table: plain]\nthis a | b line\nmore prose\n"),
                         "[table: plain]\nthis a | b line\nmore prose\n")

    def test_a_hint_under_prose_still_opts_its_long_table_out(self):
        md = ("# P\n\nLead.\n\n## 1. Long\n\nSome prose above.\n[table: plain]\n| Item | N |\n|---|---|\n"
              + "".join(f"| r{i} | {i} |\n" for i in range(7)))
        html = build_page(self.tmp, md, "p.md").read_text(encoding="utf-8")
        self.assertNotIn("[table:", html)
        self.assertNotIn('class="dt-wrap"', html)
        self.assertEqual(html.count("<table"), 1)

    def test_the_separation_touches_only_a_hint_followed_by_a_pipe_row(self):
        src = ("[table: plain]\n| a |\n\n[table: plain]\n\n| b |\n\n[table: plain]\nprose\n"
               "  [TABLE: Sortable]  \n  | c |\n")
        self.assertEqual(
            build.separate_table_hints(src),
            ("[table: plain]\n\n| a |\n\n[table: plain]\n\n| b |\n\n[table: plain]\nprose\n\n"
             "  [TABLE: Sortable]  \n\n  | c |\n"),
        )


if __name__ == "__main__":
    unittest.main()
