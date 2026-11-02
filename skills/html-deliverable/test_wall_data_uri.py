"""The wall reads inside a `data:` URI.

The defect: a page embedded its channel list as a download, `href="data:text/csv;base64,..."`,
and the CSV named an archived channel whose name is on the wall list. The lint scanned the raw file
and its entity-decoded text, so a base64 or percent-encoded payload passed unread; the page's
reviewer found it by hand.

Now every `data:` URI in the file is decoded (base64 or percent) and its text scanned against the
same list, and a hit names the attribute the URI sits in and the file line it starts on. A payload
is read as text when its type is textual or its bytes are valid UTF-8; a binary payload (an image,
a font) is not, because random bytes read as text match a three-letter entry sooner or later.

`fixtures/wall-in-data-uri.html` is the case: an external page whose download carries the name in
`data:text/csv;base64`. The old lint passed it; this one refuses it.
"""

from __future__ import annotations

import base64
import unittest
from html import unescape
from pathlib import Path

import lint

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "wall-in-data-uri.html"


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def found(page: str, **kwargs) -> list[tuple[str, int]]:
    return [(name, line) for name, line, _ in lint.wall_hits(page, **kwargs)]


class WallInsideADataUri(unittest.TestCase):
    def test_the_fixture_is_refused_and_the_failure_names_the_attribute_and_the_line(self):
        html = FIXTURE.read_text(encoding="utf-8")
        failures = lint.check(html, money=False, allow_commands=False)[0]
        wall = [f for f in failures if "wall list" in f]
        self.assertEqual(len(wall), 1, failures)
        self.assertIn("initech (inside a data: URI in the href attribute) at line 11", wall[0])

    def test_the_fixture_carries_no_name_the_raw_or_entity_pass_can_read(self):
        """The premise, pinned: only the decode finds this leak, so the fixture keeps testing it."""
        html = FIXTURE.read_text(encoding="utf-8")
        for name in lint.load_wall():
            self.assertIsNone(lint.wall_regex(name).search(html), name)
            self.assertIsNone(lint.wall_regex(name).search(unescape(html)), name)

    def test_a_percent_encoded_payload_is_read(self):
        page = '<p>x</p>\n<a href="data:text/plain;charset=utf-8,built%20by%20Initech%20staff">x</a>'
        self.assertEqual(
            found(page), [("initech (inside a data: URI in the href attribute)", 2)]
        )

    def test_an_svg_in_a_style_url_is_named_by_the_style_attribute_and_its_own_line(self):
        svg = b64('<svg xmlns="http://www.w3.org/2000/svg"><text>Initech</text></svg>')
        page = f'<div\n class="mark"\n style="background:url(data:image/svg+xml;base64,{svg})"></div>'
        self.assertEqual(
            found(page), [("initech (inside a data: URI in the style attribute)", 3)]
        )

    def test_a_uri_in_a_style_block_is_named_by_its_element(self):
        page = (
            "<style>\n"
            '.m{background:url("data:image/svg+xml,%3Csvg%3E%3Ctext%3EInitech%3C/text%3E%3C/svg%3E")}\n'
            "</style>"
        )
        self.assertEqual(found(page), [("initech (inside a data: URI in a <style> element)", 2)])

    def test_a_text_payload_under_a_binary_label_is_still_read(self):
        payload = b64("status\nInitech,kept")
        page = f'<a href="data:application/octet-stream;base64,{payload}">x</a>'
        self.assertEqual(found(page), [("initech (inside a data: URI in the href attribute)", 1)])

    def test_a_nested_uri_is_read_and_says_it_was_nested(self):
        inner = b64("owner,Initech")
        svg = b64(f'<svg xmlns="http://www.w3.org/2000/svg"><a href="data:text/csv;base64,{inner}"/></svg>')
        page = f'<img alt="" src="data:image/svg+xml;base64,{svg}">'
        self.assertEqual(
            found(page), [("initech (inside a data: URI nested in the src attribute)", 1)]
        )

    def test_one_uri_reports_each_name_once(self):
        csv = "\n".join(["initech-general,archived"] * 40)
        page = f'<a href="data:text/csv;base64,{b64(csv)}">x</a>'
        self.assertEqual(len(lint.wall_hits(page)), 1)

    def test_a_name_on_the_allow_list_is_cleared_inside_the_payload_too(self):
        html = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(lint.wall_hits(html, ["Initech"]), [])

    def test_a_binary_payload_is_not_read_as_text(self):
        """Random bytes read as text would match a short entry sooner or later; an image is not prose."""
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 64 + b" initech ").decode("ascii")
        page = f'<img alt="" src="data:image/png;base64,{png}">'
        self.assertEqual(lint.wall_hits(page), [])

    def test_the_word_data_in_prose_is_not_a_uri(self):
        page = "<p>metadata: the Initech count</p>\n<p>data: 12 rows, 3 columns</p>"
        self.assertEqual(found(page), [("initech", 1)])

    # ---- a code review's findings

    def test_an_unencoded_payload_is_reported_once_not_twice(self):
        page = '<a href="data:text/plain,made by Initech">x</a>'
        self.assertEqual(found(page), [("initech", 1)])

    def test_an_entity_written_plain_payload_is_reported_once(self):
        """The entity pass reads it; the data pass must not count it again (the re-check)."""
        page = '<a href="data:text/plain,made by Init&#101;ch">x</a>'
        self.assertEqual(len(lint.wall_hits(page)), 1, lint.wall_hits(page))

    def test_a_charset_that_is_not_a_text_encoding_is_read_as_utf8_never_a_traceback(self):
        """`charset=base64` once crashed the whole lint."""
        for charset in ("base64", "hex", "zlib", "undefined", "idna"):
            payload = b64("owner,Initech")
            page = f'<a href="data:text/plain;charset={charset};base64,{payload}">x</a>'
            names = [name for name, _, _ in lint.wall_hits(page)]
            self.assertLessEqual(len(names), 1, (charset, names))

    def test_a_utf16_payload_is_read_in_its_own_charset(self):
        utf16 = base64.b64encode("owner\r\nInitech\r\n".encode("utf-16le")).decode("ascii")
        page = f'<a href="data:text/csv;charset=utf-16le;base64,{utf16}">x</a>'
        self.assertEqual(found(page), [("initech (inside a data: URI in the href attribute)", 1)])
        bom = base64.b64encode("owner\r\nInitech\r\n".encode("utf-16")).decode("ascii")
        page = f'<a href="data:application/octet-stream;base64,{bom}">x</a>'
        self.assertEqual(found(page), [("initech (inside a data: URI in the href attribute)", 1)])

    def test_an_entity_written_payload_is_decoded_before_the_base64(self):
        payload = b64("owner,Initech")
        page = f'<a href="data:text/csv;base64,&#{ord(payload[0])};{payload[1:]}">x</a>'
        self.assertEqual(found(page), [("initech (inside a data: URI in the href attribute)", 1)])

    def test_a_control_byte_under_a_binary_label_is_skipped(self):
        payload = base64.b64encode(b"\x01\x02 Initech \x03").decode("ascii")
        page = f'<img alt="" src="data:application/octet-stream;base64,{payload}">'
        self.assertEqual(lint.wall_hits(page), [])

    def test_a_broken_payload_is_skipped_never_an_error(self):
        page = '<a href="data:text/csv;base64,@@@not-base64">x</a><a href="data:text/plain,%E0%A4%A">y</a>'
        self.assertEqual(lint.wall_hits(page), [])


if __name__ == "__main__":
    unittest.main()
