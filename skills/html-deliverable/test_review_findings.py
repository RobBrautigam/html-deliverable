#!/usr/bin/env python3
"""One test per finding from a code review, so none of them can come back.

    python -m pytest skills/html-deliverable/test_review_findings.py

Each test names the finding it pins and the failure it would let through. Several of these are
silent-corruption bugs: content deleted from a deliverable, a hint applied to the wrong table, a
sort that reports success while doing nothing. None of them would show in a screenshot.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from test_design_system import (  # noqa: E402
    COMPONENT_MD,
    HERE,
    SAMPLE_MD,
    TempCase,
    _node_playwright,
    build_gallery,
    build_page,
    failures_of,
    lint,
)


MIXED_LIST_MD = """# Mixed content

Lead.

## 1. A list that is part tasks and part bullets

- [ ] first task
- [ ] second task
- a plain bullet that must survive
- another plain bullet that must survive

## 2. A real checklist

- [ ] alpha
- [x] beta
"""

STRAY_HINT_MD = """# Stray hints

Lead.

## 1. A hint that precedes no table at all

[table: plain]

Some prose instead of a table.

## 2. The table that asked to be sortable

[table: sortable]

| A | B |
|---|---|
| one | 1 |
| two | 2 |
"""

OPT_OUT_MD = """# Opting a long table out

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
"""

DUPLICATE_HEADER_MD = """# Duplicate headers

Lead.

## 1. Two columns with the same name

| Value | X | Value |
|---|---|---|
| alpha | a | 10 |
| bravo | b | 20 |
| charlie | c | 30 |
| delta | d | 40 |
| echo | e | 50 |
"""


class ReviewFindingTests(TempCase):
    def test_finding_2_a_mixed_list_keeps_every_plain_bullet(self):
        """Rebuilding the block from the task items alone DELETED the plain bullets: silent
        content loss in a deliverable."""
        html = build_page(self.tmp, MIXED_LIST_MD, "m.md").read_text(encoding="utf-8")
        self.assertIn("a plain bullet that must survive", html)
        self.assertIn("another plain bullet that must survive", html)
        # the mixed list stays a plain list; the pure task list still becomes a checklist
        self.assertEqual(html.count('class="checklist"'), 1)
        self.assertIn("alpha", html)
        self.assertIn("beta", html)

    def test_finding_3_a_stray_hint_is_not_applied_to_a_later_table(self):
        """Hints consumed from a flat list desynced, so a marker in one section silently
        governed a table in another."""
        html = build_page(self.tmp, STRAY_HINT_MD, "s.md").read_text(encoding="utf-8")
        self.assertIn('class="dt-wrap"', html, "the [table: sortable] table was not upgraded")
        self.assertNotIn("[table:", html, "a hint marker leaked into the rendered page")

    def test_finding_3b_an_opt_out_still_works_on_a_long_table(self):
        html = build_page(self.tmp, OPT_OUT_MD, "o.md").read_text(encoding="utf-8")
        self.assertNotIn('class="dt-wrap"', html, "[table: plain] did not opt the table out")
        self.assertNotIn("[table:", html)

    def test_finding_4_duplicate_headers_each_get_their_own_sort_type(self):
        """Matching a header by its own text rewrote the FIRST column with that label every
        time, so one column got the wrong type and one got none."""
        html = build_page(self.tmp, DUPLICATE_HEADER_MD, "d.md").read_text(encoding="utf-8")
        head = re.search(r"<thead>.*?</thead>", html, re.S).group(0)
        types = re.findall(r'<th data-sort="(\w+)"', head)
        self.assertEqual(len(types), 3, f"every column must be sortable, got {types}")
        self.assertEqual(types, ["text", "text", "num"], f"wrong types: {types}")

    def test_finding_6_persisted_keys_are_unique_per_document(self):
        """Every document's first slider wrote the same localStorage key, so one document
        restored another's state and the checklist restored BY INDEX onto unrelated items."""
        one, two = self.tmp / "one", self.tmp / "two"
        one.mkdir()
        two.mkdir()
        a = build_page(one, COMPONENT_MD, "weekly-plan.md").read_text(encoding="utf-8")
        b = build_page(two, COMPONENT_MD, "quarterly-plan.md").read_text(encoding="utf-8")
        stores_a = set(re.findall(r'data-store="([^"]+)"', a))
        stores_b = set(re.findall(r'data-store="([^"]+)"', b))
        self.assertTrue(stores_a, "no persisted stores were emitted")
        self.assertEqual(
            stores_a & stores_b,
            set(),
            f"two different documents share persisted keys: {sorted(stores_a & stores_b)}",
        )

    def test_the_same_document_built_twice_keeps_its_keys(self):
        """The flip side: a rebuild must not orphan the reader's saved state."""
        one, two = self.tmp / "one", self.tmp / "two"
        one.mkdir()
        two.mkdir()
        a = set(re.findall(r'data-store="([^"]+)"', build_page(one, COMPONENT_MD, "plan.md").read_text(encoding="utf-8")))
        b = set(re.findall(r'data-store="([^"]+)"', build_page(two, COMPONENT_MD, "plan.md").read_text(encoding="utf-8")))
        self.assertEqual(a, b)

    def test_finding_7_the_slider_guard_runs_before_the_key_is_built(self):
        """Reading input.id on a null threw and killed the component block, taking every later
        slider on the page with it."""
        slider = {c.cid: c for c in build_gallery.COMPONENTS}["slider"]
        guard = slider.js.index("if (!input || !out) return;")
        key = slider.js.index("var key =")
        self.assertLess(guard, key, "the null guard must come before the key is built")

    def test_finding_8_the_lint_warning_threshold_matches_the_builder(self):
        """The lint warned at four data rows while the builder upgraded at five, so a warning
        existed that rebuilding could not clear."""
        page = build_page(self.tmp, SAMPLE_MD, "r.md").read_text(encoding="utf-8")

        def warnings_for(data_rows: int):
            body = "".join(f"<tr><td>Row {i}</td><td>{i}</td></tr>" for i in range(data_rows))
            table = f"<table><thead><tr><th>Name</th><th>N</th></tr></thead><tbody>{body}</tbody></table>"
            return lint.check(
                page.replace("<p>A lead paragraph", table + "<p>A lead paragraph", 1),
                money=False, allow_commands=False,
            )[2]

        self.assertEqual(warnings_for(4), [], "four data rows is below the builder's threshold")
        self.assertTrue(any("sortable header" in w for w in warnings_for(5)), "five data rows must warn")

    def test_finding_9_pdf_flag_does_not_swallow_the_file_argument(self):
        """--pdf with nargs='?' bound the positional file to the flag, so the command only
        worked in one argument order."""
        if _node_playwright() is None:
            self.skipTest("no browser available")
        page = build_page(self.tmp, SAMPLE_MD, "r.md")
        self.assertEqual(lint.main(["--pdf", str(page)]), 0)  # the order that used to fail
        self.assertTrue(page.with_suffix(".pdf").is_file())

    def test_pdf_out_names_the_destination(self):
        if _node_playwright() is None:
            self.skipTest("no browser available")
        page = build_page(self.tmp, SAMPLE_MD, "r.md")
        target = self.tmp / "named.pdf"
        self.assertEqual(lint.main([str(page), "--pdf-out", str(target)]), 0)
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_bytes()[:5], b"%PDF-")

    def test_finding_10_domcheck_no_longer_carries_a_counter_that_cannot_fire(self):
        """querySelectorAll('p ul') is pinned at zero forever: the parser closes the paragraph
        before the list, so the DOM never contains that shape. A check that cannot fail is
        false assurance."""
        source = (HERE / "domcheck.js").read_text(encoding="utf-8")
        self.assertNotIn("'p ul'", source)
        self.assertIn("leakedSource", source)

    def test_the_command_token_check_holds_its_word_boundary(self):
        """A peer session reported that the check might match npm inside pnpm. Verified here
        rather than taken on trust: a real token fails, ordinary English does not."""
        page = build_page(self.tmp, SAMPLE_MD, "r.md").read_text(encoding="utf-8")
        for command in ("Run npm install first", "Run pnpm install first", "Run git pull first"):
            self.assertTrue(
                any("terminal command" in f for f in failures_of(page.replace("A lead paragraph", command))),
                f"{command!r} should fail",
            )
        for innocent in ("a six-digit month", "the Digit team", "a legitimate concern"):
            self.assertFalse(
                any("terminal command" in f for f in failures_of(page.replace("A lead paragraph", innocent))),
                f"{innocent!r} is not a command",
            )


if __name__ == "__main__":
    unittest.main()
