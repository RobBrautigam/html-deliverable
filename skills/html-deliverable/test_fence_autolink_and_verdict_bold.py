#!/usr/bin/env python3
"""Pins two builder defects: a bare URL in a fenced block, and a verdict's bold.

    python -m pytest skills/html-deliverable/test_fence_autolink_and_verdict_bold.py

1. `autolink` skipped code by pairing single backticks, so a fence was not skipped whole: a bare
   URL inside a fence was wrapped as `<https://...>`, and inside a code block Markdown prints those
   angle brackets as text (a paste block rendered `&lt;https://...&gt;`). `autolink`'s pattern now
   has its own name, and it tries a whole fence before a single backtick, so a fence is skipped
   whole rather than by counting backticks inside it.
2. `--verdict` printed `**bold**` as literal asterisks. It now renders bold of any length, a bold
   run hugging a word on each side so a masked card number stays as written, and the lint's
   literal-bold check reads a verdict and a callout box too, with no length cap.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import lint  # noqa: E402

DOC = "https://docs.example.com/document/d/1AbCdEf/edit"
SITE = "https://example.com/pricing"
CODE_URL = "https://example.com/in-code"

SOURCE = f"""# A page with a paste block

A lead paragraph.

## 1. The message

The site is at {SITE} for reference.

The inline form is `open {CODE_URL}` and stays code.

```paste
Hi Sam, the order sheet is here: {DOC}
Thanks,
```

````paste
Paste this into a fresh conversation:
```
open {DOC}/nested
```
````

The dashboard is at {SITE}/after for reference.
"""

# A long bold lead, more than 80 characters between its asterisks.
LONG_LEAD = 'Pay the designer ($900.00, due October 7), send the three drafts, then say "go on all five":'
VERDICT = f"**{LONG_LEAD}** 822 threads leave the five Inboxes and 33 stay."


def build_page(text: str, *args: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "fence.md"
        source.write_text(text, encoding="utf-8")
        out = Path(tmp) / "fence.html"
        code = build.main([str(source), str(out), *args])
        assert code == 0, f"build returned {code}"
        return out.read_text(encoding="utf-8")


class AutolinkSkipsCode(unittest.TestCase):
    def test_a_bare_url_in_a_paste_fence_is_left_bare(self):
        text = f"```paste\nThe sheet: {DOC}\n```\n"
        self.assertEqual(text, build.autolink(text))

    def test_a_fence_is_skipped_whole_whatever_backticks_it_holds(self):
        # One backtick inside the fence: counting backticks pairs it with the closing fence and
        # leaves the URL between them outside every span.
        text = f"```paste\nRun `make, then open {DOC}\n```\n"
        self.assertEqual(text, build.autolink(text))

    def test_a_four_backtick_fence_leaves_the_prose_after_it_linked(self):
        # A review finding: a lazy ``` pair left the closing line's fourth
        # backtick to pair with the next one on the page, and the prose URL between went unlinked.
        text = f"````paste\nPaste this:\n{DOC}\n````\n\nThe site is at {SITE} today.\n\nRun `make` after.\n"
        out = build.autolink(text)
        self.assertIn(f"<{SITE}>", out)
        self.assertNotIn(f"<{DOC}>", out)

    def test_a_three_backtick_block_inside_a_paste_fence_is_left_bare(self):
        # A second review finding: the shape of a prompt carried as a paste block.
        text = f"````paste\nPaste this:\n```\nopen {DOC}\n```\n````\n"
        self.assertEqual(text, build.autolink(text))

    def test_a_tilde_fence_is_skipped(self):
        text = f"~~~paste\nThe sheet: {DOC}\n~~~\n"
        self.assertEqual(text, build.autolink(text))

    def test_a_bare_url_in_prose_is_still_wrapped(self):
        self.assertEqual(f"See <{SITE}>.", build.autolink(f"See {SITE}."))

    def test_an_inline_code_span_is_still_skipped(self):
        # A word before the URL: a URL right after a backtick is already passed over by BARE_URL_RE.
        text = f"The form is `open {CODE_URL}` here."
        self.assertEqual(text, build.autolink(text))


class TheBuiltPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = build_page(SOURCE)

    def test_the_paste_block_shows_the_url_without_angle_brackets(self):
        self.assertNotIn(f"&lt;{DOC}&gt;", self.page)
        self.assertIn(f"the order sheet is here: {DOC}", self.page)

    def test_the_prose_url_is_a_link(self):
        self.assertIn(f'href="{SITE}"', self.page)

    def test_the_nested_block_in_a_four_backtick_fence_is_bare(self):
        self.assertIn(f"open {DOC}/nested", self.page)
        self.assertNotIn(f"&lt;{DOC}/nested&gt;", self.page)

    def test_the_prose_after_a_four_backtick_fence_is_a_link(self):
        self.assertIn(f'href="{SITE}/after"', self.page)

    def test_the_inline_code_url_is_code_not_a_link(self):
        self.assertIn(f"<code>open {CODE_URL}</code>", self.page)
        self.assertNotIn(f"&lt;{CODE_URL}&gt;", self.page)


class VerdictBold(unittest.TestCase):
    def test_a_long_bold_lead_renders_bold(self):
        box = build.verdict_box(VERDICT)
        self.assertNotIn("**", box)
        self.assertIn(f"<strong>{build.esc(LONG_LEAD)}</strong>", box)

    def test_the_built_cover_carries_no_asterisks(self):
        page = build_page(SOURCE, "--verdict", VERDICT)
        start = page.index('<div class="verdict">')
        box = page[start:page.index("</div>", start)]
        self.assertNotIn("**", box)
        self.assertIn("<strong>Pay the designer", box)

    def test_masked_card_numbers_stay_as_written(self):
        # Two of them: without the hug on each side, the stars between them read as one bold run.
        text = "cards **** 4242 and **** 1234 are on file"
        self.assertEqual(text, build.flag_text(text))

    def test_the_lint_sees_a_long_literal_bold_in_a_box(self):
        html = f'<div class="verdict"><strong>The short answer:</strong> {build.esc(VERDICT)}</div>'
        self.assertTrue(lint.markdown_in_raw_html(html))

    # The lint check is widened, so the honest inputs that resemble the defect must still pass
    # (SKILL.md's self-improvement close, item 7 (c)).
    def test_the_lint_passes_masked_card_numbers_in_a_box(self):
        html = '<div class="verdict">Two cards are on file, **** 4242 and **** 1234, and both renew in October.</div>'
        self.assertEqual([], lint.markdown_in_raw_html(html))

    def test_the_lint_passes_a_long_starred_run_inside_code_in_a_box(self):
        run = "**" + "a glob that matches every file under the docs folder and its children, at any depth" + "**"
        html = f'<div class="callout">The pattern is <code>{run}</code>, read as code.</div>'
        self.assertEqual([], lint.markdown_in_raw_html(html))


def rebound_names(source: str) -> list[str]:
    """Module-level names assigned twice to DIFFERENT values: the later one silently wins."""
    seen: dict[str, str] = {}
    rebound: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    value = ast.dump(node.value)
                    if target.id in seen and seen[target.id] != value:
                        rebound.append(target.id)
                    seen[target.id] = value
    return rebound


class NoModuleNameIsRebound(unittest.TestCase):
    """The shape of the first defect above, checked where it happens: a second module-level pattern
    under a name already taken replaces the first for every caller above it."""

    def test_the_check_finds_the_shape(self):
        source = 'import re\nA = re.compile(r"x", re.S)\nB = 1\nA = re.compile(r"y")\n'
        self.assertEqual(["A"], rebound_names(source))

    def test_an_identical_rebinding_is_harmless(self):
        self.assertEqual([], rebound_names('import re\nA = re.compile(r"x")\nA = re.compile(r"x")\n'))

    def test_the_builder_and_the_lint_rebind_nothing(self):
        for name in ("build.py", "lint.py"):
            with self.subTest(file=name):
                self.assertEqual([], rebound_names((HERE / name).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
