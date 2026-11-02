#!/usr/bin/env python3
"""Pins one escape, never two, on a Key links URL that carries an ampersand.

    python -m pytest skills/html-deliverable/test_links_ampersand.py

A page once carried a link in its Key links table as `...?mode=show&amp;section=...`:
the harvest read the address out of the rendered page, where Markdown had already written `&` as
`&amp;`, and the table escaped it a second time (`&amp;amp;`). A browser decodes an attribute's
character references once (HTML Living Standard, 13.2.5.36, the attribute value double-quoted
state), so the link carried a literal `&amp;`, and the URL Standard splits a query on `&` alone
(5.1, application/x-www-form-urlencoded parsing), so the server read a parameter named `amp;section`.

The fix decodes each harvested address once, where it is read, so the table holds the real URL
and writes it with one escape, the way a `--link` URL (which arrives raw) always was.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402

RULES = "https://example.com/rules/index.cfm?mode=show&section=12-04"
ORDER = "https://example.org/orders?view=list&item=42"

SOURCE = f"""# A page with two query-string links

A lead paragraph.

## 1. The section

- The rules page is at {RULES} .
- The order is at {ORDER} .
"""


class LinksTable(HTMLParser):
    """Reads the Key links table the way a browser does: every attribute decoded once."""

    def __init__(self) -> None:
        super().__init__()
        self.inside = False
        self.in_link = False
        self.hrefs: list[str] = []
        self.texts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and attrs.get("id") == "links":
            self.inside = True
        elif self.inside and tag == "a":
            self.hrefs.append(attrs.get("href") or "")
            self.texts.append("")
            self.in_link = True

    def handle_endtag(self, tag):
        if tag == "section":
            self.inside = False
        elif tag == "a":
            self.in_link = False

    def handle_data(self, data):
        if self.inside and self.in_link:
            self.texts[-1] += data


def build_page(text: str, *args: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "ampersand.md"
        source.write_text(text, encoding="utf-8")
        out = Path(tmp) / "ampersand.html"
        code = build.main([str(source), str(out), *args])
        assert code == 0, f"build returned {code}"
        return out.read_text(encoding="utf-8")


class HarvestDecodesOnce(unittest.TestCase):
    def test_a_harvested_address_is_the_real_url(self):
        links = build.harvest_links(
            '<a href="https://example.com/a?b=1&amp;c=2">x</a>'
            '<a href="https://example.com/d?e=3">y</a>',
            [],
        )
        self.assertEqual(["https://example.com/a?b=1&c=2", "https://example.com/d?e=3"],
                         [url for _, url in links])

    def test_a_raw_ampersand_before_a_legacy_entity_name_is_left_alone(self):
        # Raw HTML passed through Markdown keeps a bare `&` in its href. A browser does not decode
        # `&region` or `&copy=` inside an attribute (no semicolon, a letter or `=` follows), so the
        # harvest must not either: html.unescape alone read them as `(R)egion` and `(C)=` (a
        # code review finding).
        links = build.harvest_links(
            '<a href="https://z.com/?a=1&region=us&copy=2&not=3">x</a>'
            '<a href="https://z.com/b">y</a>',
            [],
        )
        self.assertEqual("https://z.com/?a=1&region=us&copy=2&not=3", links[0][1])

    def test_a_numeric_reference_is_decoded_once(self):
        links = build.harvest_links('<a href="https://z.com/?a=1&#38;b=2">x</a>', [])
        self.assertEqual("https://z.com/?a=1&b=2", links[0][1])

    def test_a_told_link_and_the_same_harvested_link_are_one_row(self):
        links = build.harvest_links(
            '<a href="https://example.com/a?b=1&amp;c=2">x</a>',
            ["The page=https://example.com/a?b=1&c=2"],
        )
        self.assertEqual([("The page", "https://example.com/a?b=1&c=2")], links)


class TheBuiltTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = build_page(SOURCE)
        cls.table = LinksTable()
        cls.table.feed(cls.page)

    def test_no_address_is_escaped_twice(self):
        self.assertNotIn("&amp;amp;", self.page)

    def test_every_href_decodes_to_the_real_url(self):
        self.assertEqual([RULES, ORDER], self.table.hrefs)

    def test_the_visible_address_is_the_real_url(self):
        self.assertEqual([RULES, ORDER], self.table.texts)


if __name__ == "__main__":
    unittest.main()
