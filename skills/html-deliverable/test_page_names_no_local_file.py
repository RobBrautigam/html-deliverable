#!/usr/bin/env python3
"""A built page never names the local file it was built from.

    python -m pytest skills/html-deliverable/test_page_names_no_local_file.py

The builder's defaults once ended every page "Prepared <date>. Built from <file>.md.", wrote the
same file name into the data-report surface's Source line, its method note and its lede. A page is
handed to a reader; the name of a file on the author's disk says nothing to them, and it can say
too much (an internal project name, a client's name, a draft number). The page names the record
it was read from when the author passes `--source`, and nothing when they do not.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402

STEM = "zz-internal-draft-7"
PAGE = """# The pilot record

The pilot opened on the first and closed on the third.

## What happened

Four of five checks passed, and the fifth is owed.
"""
DATA = "Month,Signups,Revenue\nJanuary,40,1200\nFebruary,52,1500\n"


def build_from(text: str, suffix: str, *args: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / f"{STEM}{suffix}"
        source.write_text(text, encoding="utf-8")
        out = Path(tmp) / "out.html"
        code = build.main([str(source), str(out), "--title", "The pilot record", *args])
        assert code == 0, f"build returned {code}"
        return out.read_text(encoding="utf-8")


# The old defaults' shape: "Built from <file>.md" or "Read straight from <file>.csv".
NAMES_A_FILE = r"(?:Built|Read straight) from [\w.-]+\.(?:md|csv|tsv|json)\b"


class NoLocalFileName(unittest.TestCase):
    def test_a_report_never_names_its_file(self):
        page = build_from(PAGE, ".md")
        self.assertNotIn(STEM, page)
        self.assertNotRegex(page, NAMES_A_FILE)

    def test_a_data_report_never_names_its_file(self):
        page = build_from(DATA, ".csv", "--surface", "data-report")
        self.assertNotIn(STEM, page)
        self.assertNotRegex(page, NAMES_A_FILE)

    def test_an_unfilled_source_line_is_removed_not_left_empty(self):
        page = build_from(DATA, ".csv", "--surface", "data-report")
        self.assertNotRegex(page, r"<span><b>Source</b>\s*</span>")

    def test_a_title_made_from_the_file_name_is_said_out_loud(self):
        """With no `# ` heading and no --title, the file name becomes the title: the one place it
        still reaches a page, so the builder prints a note naming the two ways around it."""
        untitled = PAGE.replace("# The pilot record\n", "")
        for text, suffix in ((untitled, ".md"), (DATA, ".csv")):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / f"{STEM}{suffix}"
                source.write_text(text, encoding="utf-8")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(build.main([str(source), str(Path(tmp) / "out.html")]), 0)
                self.assertIn("title is made from the file name", err.getvalue())
                self.assertIn("--title", err.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / f"{STEM}.md"
            source.write_text(PAGE, encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                build.main([str(source), str(Path(tmp) / "out.html")])
            self.assertNotIn("file name", err.getvalue())

    def test_a_named_source_and_foot_still_print(self):
        page = build_from(DATA, ".csv", "--surface", "data-report",
                          "--source", "The billing export, read on the first",
                          "--foot", "Prepared for the board.")
        self.assertIn("The billing export, read on the first", page)
        self.assertIn("Prepared for the board.", page)


if __name__ == "__main__":
    unittest.main()
