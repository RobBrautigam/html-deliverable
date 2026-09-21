#!/usr/bin/env python3
"""Check a finished HTML deliverable against every hard rule in SKILL.md, in one pass.

    python lint.py <file.html> [--money] [--playwright] [--pdf] [--allow-commands]
    python lint.py <file.html> --audience external --allow "Acme"

Exit codes: 0 clean, 1 at least one hard rule broken, 2 the file could not be read.

What it checks (each maps to a named rule, with the reason it exists):
    0. NO LEAK. The whole file, not just the prose: visible text, attributes, comments and CSS
       are read against the wall list in `wall-list.txt`, so a company or client name cannot
       ride out inside a class name, a data attribute or a stylesheet comment. A page whose
       audience is EXTERNAL fails on a hit; any other page is warned. The audience comes from
       --audience, or from the page's own data-audience attribute, which build.py writes.
       --allow names the companies this page is allowed to name (repeatable, or comma-separated).
    1. no em dashes anywhere, including CSS comments, RAW or in entity form
    2. no mid dots as separators, RAW or in entity form - a list is a real <ul>/<ol>
    3. no terminal commands in the reader-facing prose (script and style blocks are exempt)
    4. the Key links table exists whenever the page names two or more destinations
    5. the right-side section nav AND the width handles exist on any page with two or more
       sections (drag the edges to resize the page width)
    6. light is the default theme and nothing auto-switches on the OS setting
    7. the file is self-contained - no external script, stylesheet or font
    8. no REPLACE marker, no lorem ipsum, no <ul> inside a <p>
    9. --money lists every money token, fails on a placeholder amount, and fails on a DOLLAR
       AMOUNT WITH NO DOLLAR SIGN - a number the prose calls dollars, a bare number under a
       column header that names money, or a bare number the page itself writes with a dollar
       sign somewhere else
   10. --playwright renders the page (--widths, default 1440 and 1920; add 390 for the phone
       check) IN BOTH THEMES and fails on horizontal overflow, and on five things a figure can
       do that a screenshot never shows: text drawn outside the box it belongs to, a label
       painted under a shape that covers it, a connector routed through a node, a figure that
       drew nothing at all, and a figure wider than the column it sits in. The message names the
       figure, the node and the pixels.
   11. --pdf writes <file>.pdf (or --pdf-out PATH) through the same browser's print path, so the
       page's own print block is exercised rather than a second layout engine

WARNINGS (printed, never fatal): a data table with no sortable header, because any table or
list of data ships with filtering and sorting.

The Playwright check uses the Python package when it is installed, otherwise the Node package
from a known module root (`PLAYWRIGHT_NODE_ROOT`, a `node_modules` beside this file, or one in
the current directory). When neither is present, a render that was ASKED FOR and did not happen
is reported as a FAILURE, never as a pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

NODE_MODULE_ROOTS = [
    os.environ.get("PLAYWRIGHT_NODE_ROOT", ""),
    str(Path(__file__).resolve().parent / "node_modules"),
    str(Path.cwd() / "node_modules"),
    str(Path.home() / "node_modules"),
]

# --------------------------------------------------------------------------- the wall
#
# A delivered page names nobody it was not given. The list of names is DATA, in one file beside
# this one, because a list of companies grows faster than anyone edits a linter.

WALL_LIST_FILE = Path(__file__).resolve().parent / "wall-list.txt"
# Quoted either way, or not at all: the builder always writes double quotes, but a page written by
# hand may not, and reading it as internal would downgrade a refusal to a note.
AUDIENCE_RE = re.compile(r"""<html[^>]*\bdata-audience=["']?(external|internal)\b""", re.I)


def load_wall(path: Path | None = None) -> list[str]:
    """Read the wall list. A missing file is an ERROR, never a quiet pass with no names."""
    source = path or WALL_LIST_FILE
    if not source.is_file():
        raise FileNotFoundError(f"the wall list is missing: {source}")
    names = []
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            names.append(entry)
    return names


def squash(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def wall_regex(name: str) -> re.Pattern[str]:
    """Whole-word, case-insensitive, and blind to the separator between the words.

    One line for "acme holdings" therefore catches "Acme Holdings", "acme-holdings" and
    "acmeholdings", and "initech" catches "initech-audit" because the trailing guard is a word
    character, not any character.
    """
    parts = [re.escape(p) for p in re.split(r"[\s\-_]+", name) if p]
    return re.compile(r"(?<!\w)" + r"[\s\-_]*".join(parts) + r"(?!\w)", re.I)


def allowed_entries(names: list[str], allow: list[str]) -> set[str]:
    """Which wall entries this page is allowed to name.

    An allow of "Acme" switches off "acme", "acme holdings" AND "acmeholdings.com", because one
    contains the other once the punctuation is squashed out. That is the behavior an author
    expects from naming their own company once.
    """
    allowed: set[str] = set()
    for permitted in allow:
        a = squash(permitted)
        if not a:
            continue
        for name in names:
            w = squash(name)
            if w and (a in w or w in a):
                allowed.add(name)
    return allowed


def wall_hits(html: str, allow: list[str] | None = None, names: list[str] | None = None) -> list[tuple[str, int, str]]:
    """Every wall name in the WHOLE file. Returns (name, line, the text around it).

    Overlapping entries report ONCE, as the longest name that covers the text. "Acme Holdings"
    is one leak, not a hit for "acme" and another for "acme holdings", and a count that says
    five when three names are on the page is a count nobody reads twice.
    """
    names = names if names is not None else load_wall()
    skip = allowed_entries(names, allow or [])

    def scan(text: str) -> list[tuple[int, int, str]]:
        spans: list[tuple[int, int, str]] = []
        for name in names:
            if name in skip:
                continue
            for match in wall_regex(name).finditer(text):
                # a TAG NAME is HTML syntax, not a word on the page: <meta> is not a company
                before = text[max(0, match.start() - 2) : match.start()]
                if before.endswith("<") or before.endswith("</"):
                    continue
                spans.append((match.start(), match.end(), name))
        kept: list[tuple[int, int, str]] = []
        for start, end, name in sorted(spans, key=lambda s: (s[0], -(s[1] - s[0]))):
            if any(start < k_end and end > k_start for k_start, k_end, _ in kept):
                continue
            kept.append((start, end, name))
        return sorted(kept)

    hits: list[tuple[str, int, str]] = []
    seen: set[str] = set()
    for start, end, name in scan(html):
        seen.add(name)
        hits.append((name, line_of(html, start), re.sub(r"\s+", " ", html[max(0, start - 24) : end + 24]).strip()))

    # A name the browser RENDERS is a leak even when the source spells it with entities:
    # "Acme&nbsp;Holdings" reads as the company on screen. The second
    # pass reports what only the decoded text shows, and says so, because its line number is the
    # decoded text's rather than the file's.
    decoded = unescape(html)
    if decoded != html:
        for start, end, name in scan(decoded):
            if name in seen:
                continue
            seen.add(name)
            window = re.sub(r"\s+", " ", decoded[max(0, start - 24) : end + 24]).strip()
            hits.append((f"{name} (written with entities)", line_of(decoded, start), window))
    return sorted(hits, key=lambda hit: hit[1])


def resolve_audience(html: str, flag: str = "auto") -> str:
    """The flag wins; otherwise the page says who it is for; otherwise treat it as internal.

    Internal is the safe default for the LINT because the lint runs on every page ever written,
    including your own internal records, which name your own company on purpose. The BUILDER
    defaults the other way, to external, because a page prepared for somebody else is the
    dangerous one.
    """
    if flag in {"external", "internal"}:
        return flag
    match = AUDIENCE_RE.search(html)
    return match.group(1).lower() if match else "internal"

# Word-boundary patterns, not substrings: "digit " contains "git " and "six-digit month" is
# ordinary business English.
COMMAND_TOKEN_RE = re.compile(
    r"(?<![\w-])(python|npm|npx|pnpm|git|curl|bash|powershell|node)\s|\b\w+\.py\b",
    re.I,
)
MONEY_RE = re.compile(
    r"(?:[$£€]\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?"
    r"|\b(?:USD|GBP|EUR|MXN)\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?"
    r"|\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?(?:USD|GBP|EUR|MXN)\b)"
)
# A zero amount is a FACT, not a placeholder: "$0.00 owed" and "$0 spent this month" are the
# answer on plenty of real pages, and failing them
# taught authors to pass --money never, which is worse than the check it replaced. The placeholder
# forms are the ones nobody would ever write on purpose.
PLACEHOLDER_MONEY_RE = re.compile(r"[$£€]\s?(?:X+[,.X]*|REPLACE|TBD)", re.I)
# The negative lookahead matters: without it "$0.50 per unit" matches "$0" and is reported as a
# zero amount.
ZERO_MONEY_RE = re.compile(r"[$£€]\s?0(?:\.00?)?(?![\d.])")

# --------------------------------------------------------------------------- every dollar
# amount carries a dollar sign
#
# An amount without its sign is a number, and a number on a finance page is read as a count. Two
# real instances: "10,298.92 dollars" in prose, and a bare "14,264" inside a figure whose
# neighbors all carried signs. The arms below are the ways an amount loses its sign, and each one
# is proved by its own fixture.
#
# ARM 1: the prose calls it dollars. "10,298.92 dollars", "14,264 dollars", "1,200 USD" with no
#        mark in front of the number.
#        The lookbehind refuses a digit, a comma and a dot as well as the signs: without them the
#        second alternative started INSIDE "$1,249.99 USD" at "249.99" and reported a correctly
#        signed amount as unsigned.
DOLLARS_WORD_RE = re.compile(
    r"(?<![$£€\d,.])\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2})\s+(?:dollars?|USD)\b", re.I
)
# ARM 4: the two-currency format. The sign goes FIRST and the currency code goes AFTER the
#        number: "$10,422.65 MXN", "$1,403.81 USD". Two shapes are
#        refused: a currency code before a number ("MXN 1,234", "USD 17.00", "GBP 25,000"), and a
#        number followed by a code with no sign in front ("1,234.00 MXN", "25,000 EUR").
CURRENCY_CODES = r"(?:USD|MXN|GBP|EUR|CAD|AUD|JPY|CHF)"
CODE_BEFORE_NUMBER_RE = re.compile(
    r"\b" + CURRENCY_CODES + r"\s?\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b"
)
CODE_AFTER_BARE_NUMBER_RE = re.compile(
    r"(?<![$£€\d,.])\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s?" + CURRENCY_CODES + r"\b"
)
# ARM 2: a column header that names money. The unambiguous ones fire on their own; the ambiguous
#        ones fire only when the table already carries a marked amount, so a table of counts with
#        a "Total" column is never refused.
MONEY_HEADER_RE = re.compile(
    r"\b(?:amount|amounts|cost|costs|price|prices|spend|spending|revenue|fee|fees|budget|"
    r"reimbursement|reimbursed|paid|payable|invoice|invoiced|usd|dollars?|charge|charges)\b|[$£€]",
    re.I,
)
SOFT_MONEY_HEADER_RE = re.compile(r"\b(?:total|totals|value|balance|subtotal|net|gross)\b", re.I)
BARE_NUMBER_RE = re.compile(r"^\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?$|^\(?-?\d+\.\d{2}\)?$")
# ARM 3: the page's own tokens. An amount the page writes as "$10,298.92" somewhere and as a bare
#        "10,298.92" elsewhere is the same amount, written twice, once wrongly.
TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<(t[hd])\b[^>]*>(.*?)</\1>", re.S | re.I)


FLOW_DATA_RE = re.compile(
    r'<script[^>]*class="flow-data"[^>]*>(.*?)</script>', re.S | re.I
)
# A figure is a MONEY figure when it says so itself, in its title, its caption, its description
# or a lane label. Inside one, a bare number is an amount unless the same string names what it
# counts, which is how "1,163 rows" stays a row count on a page about dollars.
FIGURE_MONEY_WORD_RE = re.compile(
    r"\b(?:dollar|dollars|money|spend|spending|cost|costs|revenue|paid|budget|"
    r"reimburse\w*|invoice\w*|expense\w*|deduct\w*|tax|taxes|price|pricing)\b", re.I
)
COUNTING_NOUN_RE = re.compile(
    r"\b(?:rows?|items?|lines?|records?|entries|entry|files?|people|persons?|days?|weeks?|"
    r"months?|years?|sessions?|calls?|cards?|accounts?|questions?|pages?|users?|clients?|"
    r"agents?|jobs?|tokens?|runs?|tests?|commits?|processes|steps?)\b", re.I
)
FIGURE_AMOUNT_RE = re.compile(r"(?<![$£€\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,}(?:\.\d+)?)(?!\d|[.,]\d)")


def figure_strings(html: str) -> list[tuple[str, list[str], str]]:
    """(all of the figure's own words, its labels and notes, its title) for each flow figure."""
    out: list[tuple[str, list[str], str]] = []
    for block in FLOW_DATA_RE.findall(html):
        try:
            data = json.loads(unescape(block))
        except ValueError:
            continue
        # the whole of the figure's own words decide whether it is about money; its TITLE is
        # what the message calls it, because that is what a reader would call it
        name = str(data.get("title") or "").strip()
        heading = " ".join(
            str(part) for part in (
                name, data.get("caption", ""), data.get("description", ""),
                *[lane.get("label", "") for lane in data.get("lanes") or []],
            )
        )
        labels: list[str] = []
        for node in data.get("nodes") or []:
            labels.extend(str(node.get(key, "")) for key in ("label", "note") if node.get(key))
        for mark in data.get("marks") or []:
            if mark.get("label"):
                labels.append(str(mark["label"]))
        out.append((heading, labels, name))
    return out


def money_in_figures(html: str) -> list[str]:
    """Every bare amount inside a figure that says, in its own words, that it is about money.

    The figure's text lives in a JSON block, and a JSON block is a <script>, so the prose scan
    strips it along with every other script. Eleven bare amounts rode out that way on one real
    page under a title reading "Where every dollar goes".
    """
    hits: list[str] = []
    for heading, labels, name in figure_strings(html):
        if not FIGURE_MONEY_WORD_RE.search(heading):
            continue
        bare = [
            label for label in labels
            if FIGURE_AMOUNT_RE.search(label) and not COUNTING_NOUN_RE.search(label)
        ]
        if bare:
            shown = "; ".join(f'"{label}"' for label in bare[:4])
            more = f" and {len(bare) - 4} more" if len(bare) > 4 else ""
            hits.append(
                f'the figure "{(name or heading).strip()[:56]}" says it is about money and '
                f"carries {len(bare)} amount(s) with no dollar sign: {shown}{more}"
            )
    return hits


# --------------------------------------------------------------------------- Markdown in raw HTML
#
# Markdown is NOT processed inside a raw HTML block. A fold body written in Markdown therefore
# ships to the reader exactly as typed: literal asterisks where bold was meant, and a pipe table
# as a row of pipes.
FOLD_BODY_RE = re.compile(r'<div[^>]*class="[^"]*\bfold-body\b[^"]*"[^>]*>(.*?)</div>', re.S | re.I)
RAW_BLOCK_RE = re.compile(
    r'<(?:div|section|aside|details)[^>]*class="[^"]*\b(?:fold-body|ros|asks|stage-summary)\b[^"]*"[^>]*>(.*?)</(?:div|section|aside|details)>',
    re.S | re.I,
)
LITERAL_BOLD_RE = re.compile(r"\*\*[^*\n]{1,80}\*\*")
PIPE_ROW_RE = re.compile(r"^[ \t]*\|.*\|[ \t]*$", re.M)


def markdown_in_raw_html(html: str) -> list[str]:
    """Literal Markdown that reached the page because it was written inside a raw HTML block."""
    hits: list[str] = []
    for body in RAW_BLOCK_RE.findall(html):
        text = strip_text(body)
        bold = LITERAL_BOLD_RE.search(text)
        if bold:
            hits.append(
                f'literal Markdown bold reached the page: {bold.group(0)[:44]}. Markdown is not '
                "processed inside a raw HTML block, so write <b> there or move the text into the "
                "markdown source"
            )
        rows = PIPE_ROW_RE.findall(text)
        if len(rows) >= 2:
            hits.append(
                f"a pipe table with {len(rows)} rows is sitting inside a raw HTML block as text: "
                f"{rows[0].strip()[:44]}. Markdown is not processed there, so the reader sees the "
                "pipes. Write a real <table> or move it into the markdown source"
            )
    return hits


# --------------------------------------------------------------------------- the assets proof
#
# A build line that NAMES a component is not evidence its assets shipped. One real page printed
# "components: asks, flow, part-summary" and shipped with none of their CSS or JS: the flow
# figure rendered as nothing at all. The build was fixed; this is the check that would have
# caught it from the finished file, which is the only thing the reader ever sees.
COMPONENT_ASSETS_EXPECTED: dict[str, tuple[str, str, str]] = {
    # id: (a signature of its markup, of its CSS, of its JS - "" where it has none)
    "flow": ('class="flow-data"', "figure.flow{--flow-min", "script.flow-data"),
    "part-summary": ("stage-summary", ".stage-summary{", "data-fold"),
    "asks": ('class="asks"', ".asks{", ""),
    "timeline": ('class="tl"', ".tl-scale{", ""),
    "grouped-bar": ("data-gbar", ".gbar{", "data-gbar"),
    "checklist": ("data-checklist", ".checklist label", "data-checklist"),
    "slider": ("slider-row", ".slider-head{", "data-slider"),
    "data-table": ("table class=\"dt\"", ".dt-filter", "dt-filter"),
}


def components_without_assets(html: str) -> list[str]:
    """A component in the markup whose CSS or JS is not in the same file."""
    hits: list[str] = []
    for cid, (markup, css, js) in COMPONENT_ASSETS_EXPECTED.items():
        if markup not in html:
            continue
        missing = []
        if css and css not in html:
            missing.append("its CSS")
        if js and js not in html:
            missing.append("its JS")
        if missing:
            hits.append(
                f"the page uses the `{cid}` component and does not carry {' or '.join(missing)}. "
                "A build line that names a component is not evidence its assets shipped: this "
                "one renders as unstyled markup, or as nothing at all"
            )
    return hits


def money_without_a_sign(html: str, prose: str) -> list[str]:
    """Every dollar amount on the page that is missing its dollar sign, in plain English."""
    hits: list[str] = []

    # one line per distinct amount, with its count. Eight copies of one sentence is how a real
    # failure gets skimmed past.
    spoken: dict[str, int] = {}
    for match in DOLLARS_WORD_RE.finditer(prose):
        key = re.sub(r"\s+", " ", match.group(0)).strip()
        spoken[key] = spoken.get(key, 0) + 1
    for key, count in sorted(spoken.items()):
        times = f" ({count} times)" if count > 1 else ""
        hits.append(
            f'"{key}"{times} is an amount in dollars written without a dollar sign '
            "(every dollar amount carries one, in prose, tables, cards and figures)"
        )

    # ARM 4, both shapes. "USD 17.00" is caught by the code-before-number arm and not repeated by
    # the code-after arm, because that arm refuses a numeral preceded by a digit or a sign only.
    code_first: dict[str, int] = {}
    for match in CODE_BEFORE_NUMBER_RE.finditer(prose):
        key = re.sub(r"\s+", " ", match.group(0)).strip()
        code_first[key] = code_first.get(key, 0) + 1
    for key, count in sorted(code_first.items()):
        times = f" ({count} times)" if count > 1 else ""
        code = key.split()[0]
        number = key.split()[-1].lstrip("$")
        hits.append(
            f'"{key}"{times} puts the currency code before the number: the format is the sign '
            f"first and the currency after the amount, ${number} {code}"
        )
    code_after: dict[str, int] = {}
    for match in CODE_AFTER_BARE_NUMBER_RE.finditer(prose):
        key = re.sub(r"\s+", " ", match.group(0)).strip()
        if DOLLARS_WORD_RE.fullmatch(key):
            continue  # arm 1 already reported this one as dollars without a sign
        code_after[key] = code_after.get(key, 0) + 1
    for key, count in sorted(code_after.items()):
        times = f" ({count} times)" if count > 1 else ""
        hits.append(
            f'"{key}"{times} is an amount written without its $ sign: the format is '
            f"${key} (the sign first, the currency named after the number)"
        )

    for table in TABLE_RE.findall(html):
        rows = [
            [(tag.lower(), strip_text(cell)) for tag, cell in CELL_RE.findall(row)]
            for row in TR_RE.findall(table)
        ]
        header = next((row for row in rows if any(tag == "th" for tag, _ in row)), None)
        if not header:
            continue
        marked = bool(MONEY_RE.search(strip_text(table)))
        for index, (_, name) in enumerate(header):
            hard = bool(MONEY_HEADER_RE.search(name))
            soft = bool(SOFT_MONEY_HEADER_RE.search(name))
            if not (hard or (soft and marked)):
                continue
            bare = [
                row[index][1].strip()
                for row in rows
                if row is not header and len(row) > index and BARE_NUMBER_RE.match(row[index][1].strip())
            ]
            if bare:
                shown = ", ".join(bare[:4]) + (f" and {len(bare) - 4} more" if len(bare) > 4 else "")
                hits.append(
                    f'the column "{name.strip()}" names money and carries {len(bare)} amount(s) '
                    f"with no dollar sign: {shown}"
                )

    # The spans MONEY_RE already claimed. A loose occurrence inside one of them is the marked
    # amount itself, not a second bare copy of it: "GBP 25,000" matched its own numeral and was
    # reported as unsigned until this was exact (the suite caught it).
    claimed = [(m.start(), m.end()) for m in MONEY_RE.finditer(prose)]
    numerals = set()
    for token in MONEY_RE.findall(prose):
        number = re.search(r"\d[\d,]*(?:\.\d+)?", token)
        if number:
            numerals.add(number.group(0))
    numerals = {n for n in numerals if ("," in n or "." in n) and len(n) >= 4}
    for numeral in sorted(numerals):
        pattern = re.compile(r"(?<![$£€\d.,])" + re.escape(numeral) + r"(?!\d|[.,]\d)")
        loose = [
            m for m in pattern.finditer(prose)
            if not any(start <= m.start() and m.end() <= end for start, end in claimed)
        ]
        if loose:
            hits.append(
                f'"{numeral}" appears {len(loose)} time(s) with no dollar sign and elsewhere on '
                "the same page WITH one: it is the same amount written two ways"
            )
    return hits
EM_DASH_RE = re.compile(r"—|&mdash;|&#8212;|&#x2014;", re.I)
MID_DOT_RE = re.compile(r"·|&middot;|&#183;|&#xb7;", re.I)
TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.S | re.I)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="(https?://[^"]+)"', re.I)


def visible_text(html: str) -> str:
    """Body prose only: scripts, styles and comments removed, tags stripped."""
    text = SCRIPT_STYLE_RE.sub(" ", html)
    text = COMMENT_RE.sub(" ", text)
    return TAG_RE.sub(" ", text)


def line_of(html: str, index: int) -> int:
    return html.count("\n", 0, index) + 1


SECTION_RE = re.compile(r"<section\b[^>]*>(.*?)</section>", re.S | re.I)
PART_HEAD_RE = re.compile(r'<div class="part-head"[^>]*>(.*?)</div>', re.S | re.I)
HEADING_RE = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.S | re.I)
TRAILING_CLOSE_RE = re.compile(r"(?:\s*</(?:div|p|span|article|aside|li|ul|ol)>)*\s*$", re.I)
# A heading followed by a chart, an image or a table introduces something real even though the
# stripped text between them is empty.
MEDIA_RE = re.compile(r"<(img|svg|canvas|video|iframe|table|figure|pre|hr)\b", re.I)
# Attributes may precede the id on a hand-written page: <nav class="rail" id="sidenav">.
NAV_RE = re.compile(r'<nav\b[^>]*\bid="sidenav"[^>]*>.*?</nav>', re.S | re.I)


def stranded_headings(html: str) -> list[str]:
    """Every heading must open the content it introduces. Returns a list of plain-English hits.

    The defect: a heading that reads as strangely placed at the very bottom of one section. The
    builder used to split the document on level-2 headings only, so a level-1 part heading stayed
    inside the previous section's body and closed the card with nothing under it.

    Two shapes are refused, which are the two ways a heading can be orphaned:

    1. a heading is the LAST thing in its section card, so it introduces nothing;
    2. a heading is followed, with no content in between, by another heading of the SAME or a
       HIGHER level, so what it introduces is somebody else's heading.

    A part head whose only child is its heading is fine when a section follows it immediately:
    that IS the content it introduces.
    """
    hits: list[str] = []
    body = COMMENT_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", html))

    for match in SECTION_RE.finditer(body):
        inner = match.group(1)
        line = line_of(body, match.start())
        trimmed = TRAILING_CLOSE_RE.sub("", inner)
        last = HEADING_RE.search(trimmed[-400:] if len(trimmed) > 400 else trimmed)
        if trimmed.rstrip().endswith(tuple(f"</h{n}>" for n in range(1, 7))):
            label = strip_text(last.group(2))[:60] if last else ""
            hits.append(f"line {line}: the heading {label!r} is the last thing in its section, with no content after it")
            continue
        headings = list(HEADING_RE.finditer(inner))
        for index, heading in enumerate(headings[:-1]):
            nxt = headings[index + 1]
            gap = inner[heading.end() : nxt.start()]
            if strip_text(gap) or MEDIA_RE.search(gap):
                continue
            if int(nxt.group(1)[1]) <= int(heading.group(1)[1]):
                label = strip_text(heading.group(2))[:60]
                hits.append(
                    f"line {line}: the heading {label!r} has no content before the next heading of the same or a higher level"
                )

    for match in PART_HEAD_RE.finditer(body):
        inner = TRAILING_CLOSE_RE.sub("", match.group(1))
        if not inner.rstrip().endswith(tuple(f"</h{n}>" for n in range(1, 7))):
            continue
        after = body[match.end() :].lstrip()
        if not after.startswith("<section"):
            label = strip_text(HEADING_RE.search(inner).group(2))[:60] if HEADING_RE.search(inner) else ""
            hits.append(f"line {line_of(body, match.start())}: the part heading {label!r} introduces nothing")
    return hits


def strip_text(fragment: str) -> str:
    return TAG_RE.sub(" ", fragment).replace("&nbsp;", " ").strip()


# --------------------------------------------------------------------------- the flat page
#
# A 7,900-word reply built flat from a markdown record and linted green at three widths still
# read as "a written document from top to bottom". A green lint was not a design pass, so the
# lint learns to see it.
#
# The rule, as built: a long page must carry BOTH a summary block at the top of every long part
# AND at least one block that uses color to mark meaning. Missing EITHER is the hit, not only
# missing both, because the page that produced this rule already carried one verdict box and
# nothing else, and a rule that needed both to be absent would have passed it.

FLAT_WORD_FLOOR = 3000
# Prose only: a part whose words are mostly a code sample or a paste block is not a wall of
# argument, and the gallery is made of those.
LONG_PART_WORDS = 250
PRE_CODE_RE = re.compile(r"<(pre|code)\b.*?</\1>", re.S | re.I)
SUMMARY_BLOCK_RE = re.compile(
    r'(?:class|id)="[^"]*\b(?:stage-summary|summary|verdict|ss-row)\b', re.I
)
COLOR_BLOCK_RE = re.compile(r'class="[^"]*\b(?:asks|callout|warn|verdict|ruling|chip)\b', re.I)


def prose_words(fragment: str) -> int:
    return len(visible_text(PRE_CODE_RE.sub(" ", fragment)).split())


def flat_page(html: str) -> list[str]:
    """Every reason this page reads as a wall of words. Empty when it does not.

    A part is a `.part-head` block's section when the document has parts, otherwise a
    `<section>`. Only LONG parts are judged: a contents block, a facts grid and a links table
    introduce nothing and need no summary of their own.
    """
    body = COMMENT_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", html))
    if prose_words(body) < FLAT_WORD_FLOOR:
        return []

    long_parts, summarized = 0, 0
    for match in SECTION_RE.finditer(body):
        inner = match.group(1)
        if prose_words(inner) < LONG_PART_WORDS:
            continue
        long_parts += 1
        if SUMMARY_BLOCK_RE.search(inner):
            summarized += 1

    reasons: list[str] = []
    missing = long_parts - summarized
    if missing:
        reasons.append(
            f"{missing} of its {long_parts} long sections open with no summary block "
            "(every part of a long document opens with a summary strip, and the detail folds "
            "under it. Copy the part-summary component from the gallery)"
        )
    if not COLOR_BLOCK_RE.search(body):
        reasons.append(
            "nothing on the page uses color to mark meaning: no questions block, callout, warn, "
            "verdict or chip (color is focus, and a page of one color is a wall)"
        )
    return reasons


PART_HEAD_OPEN_RE = re.compile(r'<div class="part-head"[^>]*>', re.I)
DIV_TAG_RE = re.compile(r"<(/?)div\b[^>]*>", re.I)


def part_head_blocks(body: str) -> list[tuple[int, int, str]]:
    """(start, end, inner) for every part head, matched on BALANCED div depth.

    A part head contains a nested `<div class="part-num">`, so a non-greedy `.*?</div>` closes on
    the wrong tag and reports the heading itself as the content that follows the part.
    """
    found: list[tuple[int, int, str]] = []
    for opening in PART_HEAD_OPEN_RE.finditer(body):
        depth, cursor = 1, opening.end()
        for tag in DIV_TAG_RE.finditer(body, opening.end()):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                cursor = tag.end()
                break
        else:
            continue  # unbalanced markup: the HTML is broken in a way this check cannot judge
        found.append((opening.start(), cursor, body[opening.end() : cursor]))
    return found


PART_NUM_RE = re.compile(r'<div class="part-num"[^>]*>.*?</div>', re.S | re.I)


def part_head_extras(inner: str) -> str:
    """What a part head carries BESIDES its "Part 4" marker and its title."""
    rest = HEADING_RE.sub(" ", PART_NUM_RE.sub(" ", inner))
    return TRAILING_CLOSE_RE.sub("", rest).strip()


def parts_without_a_card(html: str) -> list[str]:
    """A part head must be followed by a section card, never by bare prose on the page ground.

    The defect: two parts of a real page were not wrapped in the white card every section gets.
    The builder now renders a sectionless part's body in its own card; this is the gate that
    keeps it that way, including for a hand-written page.

    The bare shape comes in TWO forms and the first one is the one that shipped. In it the part
    head's own `</div>` is never written after the title: the heading and the whole part body
    share one div, closed at the very end of the part. `part_head_blocks` walks balanced depth,
    so it reports the part as ending after its body, and what "follows" it is the NEXT part head
    - which the followed-by check reads as clean. That is why the page passed this lint with two
    uncarded parts on it. The condition below judges the part head's own contents, not only what
    comes after it.
    """
    body = COMMENT_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", html))
    hits: list[str] = []
    for start, end, inner in part_head_blocks(body):
        after = body[end:].lstrip()
        heading = HEADING_RE.search(inner)
        label = strip_text(heading.group(2))[:60] if heading else ""
        # A part that OPENS SECTIONS keeps its body as the lede inside the head. That is the
        # approved shape, and it is the one case where content inside a part head is right.
        if after.startswith("<section"):
            continue
        # form 1: the body is inside the part head itself (the shape that shipped)
        extras = part_head_extras(inner)
        if strip_text(extras) or MEDIA_RE.search(extras):
            hits.append(
                f"line {line_of(body, start)}: the part {label!r} carries its body inside the "
                "part head instead of a section card"
            )
            continue
        if after.startswith('<div class="part-head"'):
            continue
        # the end of the document is fine only when the part head carried its own content,
        # which the stranded-heading check judges separately
        if not after or after.startswith("</div>") or after.startswith('<div class="foot"'):
            continue
        # form 2: the body sits on the page ground after a properly closed part head
        hits.append(
            f"line {line_of(body, start)}: the part {label!r} is followed by bare content "
            "instead of a section card"
        )
    return hits


A_TAG_RE = re.compile(r"<a\b([^>]*)>", re.I)
HREF_ATTR_RE = re.compile(r'\bhref\s*=\s*"([^"]*)"', re.I)
REL_ATTR_RE = re.compile(r'\brel\s*=\s*"([^"]*)"', re.I)
TARGET_ATTR_RE = re.compile(r'\btarget\s*=\s*"([^"]*)"', re.I)
EXTERNAL_HREF_RE = re.compile(r'\s*(?:https?:)?//', re.I)


def links_not_new_tab(html: str) -> list[str]:
    """Every external `<a>` that would navigate the reader's tab away instead of opening one.

    A reader keeps a deliverable open in one of many tabs; a link that replaces the document
    costs them their place in it. `build.py` writes the attributes on every page it composes, so
    a hit here means a hand-written page or an anchor pasted in after the build.

    `noreferrer` is required beside `noopener`: a bare `target="_blank"` hands the page it opens
    a live `window.opener` handle back into the deliverable.
    """
    body = COMMENT_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", html))
    hits: list[str] = []
    for tag in A_TAG_RE.finditer(body):
        attrs = tag.group(1)
        href = HREF_ATTR_RE.search(attrs)
        if not href or not EXTERNAL_HREF_RE.match(href.group(1)):
            continue
        target = TARGET_ATTR_RE.search(attrs)
        rel_attr = REL_ATTR_RE.search(attrs)
        rel = set(rel_attr.group(1).split()) if rel_attr else set()
        missing = []
        if not target or target.group(1).strip() != "_blank":
            missing.append('target="_blank"')
        if not {"noopener", "noreferrer"} <= rel:
            missing.append('rel="noopener noreferrer"')
        if missing:
            url = href.group(1)[:60]
            hits.append(f"line {line_of(body, tag.start())}: {url} is missing {' and '.join(missing)}")
    return hits


def top_level_nav_entries(html: str) -> int:
    """Buttons the reader sees at rest: a collapsed group counts as ONE, not as its whole list."""
    nav = NAV_RE.search(html)
    if not nav:
        return 0
    visible = re.sub(r'<div class="nav-kids">.*?</div>', " ", nav.group(0), flags=re.S | re.I)
    return len(re.findall(r"<button\b", visible, re.I))


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
# A title that says nothing about the document: the template's own placeholder, the builder's
# old fallback, and the plain words a lazy title is made of.
GENERIC_TITLES = frozenset({
    "", "document", "untitled", "page", "report", "index", "home",
    "html deliverable", "deliverable",
})


def title_findings(html: str) -> list[str]:
    """The browser tab reads the document's own title, exactly.

    Two things a page's `<title>` may not be: absent or generic ("Document", the template's
    placeholder), or different from the page's own `<h1>`. The h1 is what the reader sees at the
    top of the page and the tab is what they hover in a window of many tabs; when the two
    disagree the tab is lying about the page behind it. A product name prefixed or suffixed to
    the title ("Product - The quarter") fails the same way, because it differs from the h1.
    Whitespace is folded and entities are unescaped on both sides, so an `&amp;` in the heading
    and an `&` in the title are the same title.
    """
    import html as html_lib

    def fold(text: str) -> str:
        return " ".join(html_lib.unescape(TAG_RE.sub("", text)).split())

    out: list[str] = []
    title_match = TITLE_RE.search(html)
    title = fold(title_match.group(1)) if title_match else ""
    if not title_match:
        return ["no <title>: the browser tab would read the file name"]
    if title.lower() in GENERIC_TITLES or title.startswith("REPLACE"):
        out.append(f"generic <title> {title!r}: the tab must read the document's own title")
        return out
    h1_match = H1_RE.search(html)
    if h1_match:
        heading = fold(h1_match.group(1))
        if heading and heading != title:
            out.append(
                f"<title> {title!r} differs from the page's <h1> {heading!r}: the tab must read "
                "exactly what the page says at the top"
            )
    return out


def check(
    html: str,
    *,
    money: bool,
    allow_commands: bool,
    allow_no_grips: bool = False,
    audience: str = "auto",
    allow: list[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    warnings: list[str] = []
    prose = visible_text(html)

    # THE TAB TITLE: the document's own title, exactly, no affix, no kind label, equal to the h1.
    # A description meta from the lede rides beside it (the builder writes it; a hand-written
    # page without one gets a note, not a failure).
    failures += title_findings(html)
    if not re.search(r'<meta\s+name="description"\s+content="[^"]+"', html, re.I):
        warnings.append("no <meta name=\"description\">: the builder writes one from the lede")

    # 0. THE WALL. The whole file, not the prose: a name rides out just as easily inside a class,
    #    a data attribute or a stylesheet comment as it does inside a sentence. Measured on a real
    #    template: a client one-pager built from it and shipped unchanged carried another client's
    #    short name in a CSS selector and a third company's name in a comment, with nothing
    #    visible on the page to show for it.
    who = resolve_audience(html, audience)
    notes.append(f"audience: {who}" + (f", allowed to name {', '.join(allow)}" if allow else ""))
    try:
        hits = wall_hits(html, allow or [])
    except FileNotFoundError as missing:
        failures.append(f"{missing}. The leak check could not run, so the page is not cleared")
    else:
        if hits:
            shown = "; ".join(f"{name} at line {line}" for name, line, _ in hits[:8])
            more = f" and {len(hits) - 8} more" if len(hits) > 8 else ""
            message = (
                f"{len(hits)} name(s) from the wall list are in this file: {shown}{more}. "
                "A delivered page names nobody it was not given. Pass --allow for a company this "
                "page is entitled to name"
            )
            (failures if who == "external" else warnings).append(message)

    # 1. em dashes, RAW and in entity form. The entity forms slipped past this lint twice, which
    #    is why they are matched explicitly rather than by the character alone.
    em = EM_DASH_RE.search(html)
    if em:
        failures.append(
            f"em dash ({em.group(0)}) at line {line_of(html, em.start())} "
            "(never, in any file, raw or as an entity)"
        )

    # 2. mid dots, RAW and in entity form
    dot = MID_DOT_RE.search(html)
    if dot:
        failures.append(
            f"mid dot ({dot.group(0)}) at line {line_of(html, dot.start())} "
            "(a list is a real <ul>/<ol>, never dots on one line)"
        )

    # 3. terminal commands in prose
    if not allow_commands:
        hits = sorted({match.group(0).strip().lower() for match in COMMAND_TOKEN_RE.finditer(prose)})
        if hits:
            failures.append(
                f"terminal command tokens in the visible prose: {', '.join(hits)} "
                "(a reader does not run commands; say what they do in plain words, or show the output)"
            )

    # 4. the links table
    destinations = {url for url in HREF_RE.findall(html) if "127.0.0.1" not in url}
    if len(destinations) >= 2 and not re.search(r"Key links", html, re.I):
        failures.append(
            f"{len(destinations)} destinations are named but there is no Key links table (the always-link rule)"
        )

    # 4b. every external link opens in a NEW TAB
    bad_tabs = links_not_new_tab(html)
    if bad_tabs:
        shown = "; ".join(bad_tabs[:5])
        more = f" and {len(bad_tabs) - 5} more" if len(bad_tabs) > 5 else ""
        failures.append(
            f"{len(bad_tabs)} external link(s) do not open in a new tab: {shown}{more} "
            '(every external <a> carries target="_blank" rel="noopener noreferrer". '
            "A reader keeps a deliverable in one of many tabs and a link that navigates the page "
            "away loses their place in it. build.py writes this automatically)"
        )

    # 5. the right-side nav
    section_count = len(re.findall(r"<section\b", html, re.I))
    nav_buttons = len(NAV_RE.findall(html))
    buttons_inside = 0
    nav_match = NAV_RE.search(html)
    if nav_match:
        buttons_inside = len(re.findall(r"<button\b", nav_match.group(0), re.I))
    if section_count >= 2 and (nav_buttons == 0 or buttons_inside < 2):
        failures.append(
            f"{section_count} sections but no working right-side section nav "
            "(every multi-section page carries it, visible from the top)"
        )
    if nav_match and "requestAnimationFrame" not in html:
        failures.append(
            "the section nav does not use an rAF-eased scroll (native smooth silently jumps)"
        )

    # 5d. WARNING: too many TOP-LEVEL nav entries. Measured: 40 flat entries rendered a 1394px
    #     rail inside a 900px viewport. The builder groups automatically above this count,
    #     so a warning here means a hand-written page, or a grouping that did not take.
    top_level = top_level_nav_entries(html)
    if top_level > 12:
        warnings.append(
            f"the section nav carries {top_level} top-level entries "
            "(above about twelve the rail is taller than the screen. Group the document into "
            "parts: a level-1 heading in the source opens one)"
        )

    # 5e. no heading may close a section or introduce nothing. This is the OTHER half of the
    #     stranded-heading correction, and it is the half a screenshot at the top of the page misses.
    for hit in stranded_headings(html):
        failures.append(
            f"{hit} (a heading at the foot of a card reads as a broken page)"
        )

    # 5g. A PART'S BODY LIVES IN A CARD. A part heading followed by bare prose on the page
    #     ground is the defect; the builder wraps it now, and this refuses the shape however the
    #     page was written.
    for hit in parts_without_a_card(html):
        failures.append(
            f"{hit} (a part's own body is wrapped in the same section card a section gets, "
            "never left on the page ground)"
        )

    # 5f. THE FLAT PAGE. A long document for somebody else is composed, not
    #     poured: a summary block at the top of every long part, the detail folded under it, and
    #     color used to mark meaning. A warning anywhere, a REFUSAL on an external page, because
    #     the page that produced this rule was for a partner.
    for reason in flat_page(html):
        message = f"this page reads flat: {reason}"
        (failures if who == "external" else warnings).append(message)

    # 5b. width handles: same trigger as the nav, because the same page needs both
    if section_count >= 2 and not allow_no_grips:
        has_left = re.search(r'class="[^"]*\bgrip\b[^"]*\bl\b', html) is not None
        has_right = re.search(r'class="[^"]*\bgrip\b[^"]*\br\b', html) is not None
        if not (has_left and has_right):
            failures.append(
                "the reading-width handles are missing (drag the left and right edges of the "
                "page to resize it). Copy the .grip buttons from template.html"
            )
        elif "--wrap-w" not in html:
            failures.append(
                "the width handles are present but nothing reads --wrap-w: the drag would move nothing"
            )

    # 5c. WARNING, never fatal: a data table with no sortable header. Any table or list of data
    #     ships with filtering and sorting.
    for match in TABLE_RE.finditer(html):
        table = match.group(0)
        rows = len(re.findall(r"<tr\b", table, re.I))
        cols = len(re.findall(r"<th\b", table, re.I))
        if rows < 6 or cols < 2:
            # the SAME threshold build.py upgrades at: five data rows plus the header. A warning
            # the author cannot clear by rebuilding is a warning that trains people to ignore it.
            continue  # a short or single-column table is a layout, not a data table
        preceding = html[max(0, match.start() - 400) : match.start()]
        if re.search(r"Key links|every destination", preceding, re.I):
            continue  # the links table is a reference, not data to sort
        if "data-sort" not in table:
            warnings.append(
                f"the table at line {line_of(html, match.start())} has {rows - 1} rows and no sortable header "
                "(any table or list of data ships with filtering and sorting)"
            )

    # 6. light default, no OS auto-switch
    if not re.search(r'<html[^>]*data-theme="light"', html, re.I):
        failures.append('the <html> tag does not ship data-theme="light" (light is the default rendering)')
    # the AT-RULE, not the bare word: a CSS comment documenting the ban is not a breach of it
    if re.search(r"@media[^{]*prefers-color-scheme", html, re.I):
        failures.append(
            "a @media (prefers-color-scheme) block is present: a dark-OS machine would render this dark unasked"
        )

    # 7. self-contained
    for pattern, label in (
        (r'<script[^>]+src="https?://', "an external script"),
        (r'<link[^>]+href="https?://', "an external stylesheet or font"),
        (r"@import\s+url\(https?://", "an @import of a remote stylesheet"),
        (r'<img[^>]+src="(?!data:)[^"]', "an image the file does not carry"),
        (r'<(?:iframe|object|embed)\b[^>]+(?:src|data)="https?://', "a remote frame or embed"),
    ):
        if re.search(pattern, html, re.I):
            failures.append(f"{label} is loaded: the file must render offline when dragged into a message")

    # 7b. a diagram that is not really in the file. The three shapes this catches are the three
    #     ways a diagram usually arrives: a picture of one from a URL (caught by 7 above), a
    #     CDN renderer that draws it in the reader's browser, and an element left for that
    #     renderer to fill. All three are blank in the one place the reader opens the page:
    #     offline, in a message, on a plane. A diagram in a house deliverable is PRE-RENDERED
    #     inline SVG.
    for pattern, label in (
        (r"\b(?:mermaid|viz\.js|vis-network|cytoscape|chart\.js|plotly|d3)\b[^<]{0,40}\.js\b",
         "a diagram or chart library loaded by filename"),
        (r'<(?:div|pre)[^>]+class="[^"]*\b(?:mermaid|graphviz|plantuml)\b', "an unrendered diagram element"),
        (r"\bmermaid\.initialize\s*\(", "a mermaid runtime initializer"),
    ):
        found = re.search(pattern, html, re.I)
        if found:
            failures.append(
                f"{label} at line {line_of(html, found.start())}: a diagram in a house deliverable is "
                "PRE-RENDERED to inline SVG at build time ([diagram: <kind>] in the markdown source), "
                "never drawn in the reader's browser and never fetched from a CDN"
            )

    # 8. leftovers
    if "REPLACE" in html:
        failures.append(f"a REPLACE marker survives at line {line_of(html, html.index('REPLACE'))}")
    token = re.search(r"\{\{[A-Z_]+\}\}", html)
    if token:
        failures.append(f"an unfilled build token {token.group(0)} survives at line {line_of(html, token.start())}")
    if re.search(r"lorem ipsum", html, re.I):
        failures.append("lorem ipsum in a deliverable (real content only)")
    if re.search(r"<p\b[^>]*>(?:(?!</p>).)*?<ul\b", html, re.S | re.I):
        failures.append("a <ul> inside a <p>: the browser closes the paragraph and the layout breaks")
    failures.extend(markdown_in_raw_html(html))
    failures.extend(components_without_assets(html))

    # 9. money
    if money:
        tokens = MONEY_RE.findall(prose)
        if tokens:
            counts: dict[str, int] = {}
            for token in tokens:
                key = re.sub(r"\s+", " ", token).strip()
                counts[key] = counts.get(key, 0) + 1
            notes.append("money tokens: " + ", ".join(f"{k} x{v}" for k, v in sorted(counts.items())))
        else:
            notes.append("money tokens: none found")
        if PLACEHOLDER_MONEY_RE.search(prose):
            failures.append("a placeholder amount is still in the page (client-facing pages carry real figures only)")
        failures.extend(money_without_a_sign(html, prose))
        failures.extend(money_in_figures(html))
        zeros = ZERO_MONEY_RE.findall(prose)
        if zeros:
            notes.append(
                f"{len(zeros)} zero amount(s) on the page. A zero is a valid figure here; "
                "confirm each one is the real number and not an unfilled cell."
            )

    return failures, notes, warnings


# --------------------------------------------------------------------------- the figures
#
# A figure is the one thing on a page a screenshot is worst at judging. Text 9 pixels outside its
# box, a connector crossing a node, a tag painted over its own label: every one of those looks
# like a picture in a thumbnail and like a mistake to the person reading it. So the render
# MEASURES, box against box, and the message it prints names the figure, the element and the
# pixels rather than saying something looks wrong.
#
# The `flow` component is measured against its own contract: it marks every node `.flow-node`,
# every connector `.flow-edge` and every piece of text `.flow-label`, `.flow-note`,
# `.flow-lane-label` or `.flow-mark-label`, each carrying the `data-node` it belongs to. A d2 or
# graphviz drawing is measured against the classes those engines write (`g.shape > rect`,
# `g.node > path`, `path.connection`), and its connector routing is REPORTED rather than refused,
# because the router there is the engine and not this skill. A CHART is measured only for having
# drawn marks at all: it has no node boxes, so every box-based rule below would be a false
# finding on it.
#
# Proved by inversion on `fixtures/flow-broken.md`, whose figure is one that shipped on a real
# page: before the repair it produced 44 findings across three widths and two themes, and its
# JSON has not changed since.
FIGURE_MEASURE = """(() => {
  const round = (n) => Math.round(n * 10) / 10;
  const boxOf = (el) => {
    const b = el.getBoundingClientRect();
    return { x: round(b.left), y: round(b.top), r: round(b.right), b: round(b.bottom),
             w: round(b.width), h: round(b.height) };
  };
  const area = (b) => b.w * b.h;
  const overlap = (a, b) => Math.min(a.r, b.r) - Math.max(a.x, b.x) > 0.5 &&
                            Math.min(a.b, b.b) - Math.max(a.y, b.y) > 0.5;
  const out = [];
  const figures = document.querySelectorAll('figure.flow, figure.dgm, figure.chart, .dgm-art');
  figures.forEach((figure, fi) => {
    const kind = figure.classList.contains('flow') ? 'flow'
      : (figure.classList.contains('chart') ? 'chart' : 'diagram');
    const name = figure.getAttribute('aria-label') || figure.getAttribute('id') ||
                 (figure.querySelector('figcaption') || {}).textContent || (kind + ' ' + (fi + 1));
    const entry = { index: fi, kind, name: String(name).trim().slice(0, 70), findings: [], notes: [] };
    const svg = figure.querySelector('svg');
    const figBox = boxOf(figure);

    // ---- drew nothing. A figure with no SVG, or an SVG with no shape in it, is the failure a
    //      screenshot shows as white space and a reader shows as a missing explanation.
    if (!svg) { entry.findings.push({ rule: 'drew-nothing', detail: 'no <svg> in the figure' }); out.push(entry); return; }
    const svgBox = boxOf(svg);
    entry.svgWidth = svgBox.w; entry.figureWidth = figBox.w;

    let nodes, edges, texts;
    if (kind === 'flow') {
      nodes = [].slice.call(svg.querySelectorAll('rect.flow-node')).map((el) => ({ el, box: boxOf(el), id: el.getAttribute('data-node') }));
      edges = [].slice.call(svg.querySelectorAll('path.flow-edge'));
      if (!nodes.length && svg.querySelectorAll('rect').length) {
        entry.findings.push({ rule: 'superseded-renderer', detail:
          'the figure drew rectangles but no rect.flow-node: this page carries an older copy of the flow renderer. Rebuild it with build.py' });
        out.push(entry); return;
      }
    } else if (kind === 'chart') {
      // A CHART HAS NO NODES, and never did. It draws lines, dots and an axis, so the box-based
      // rules below cannot say anything true about it. The one rule that still applies is that it
      // drew SOMETHING: an empty plot is the failure a reader sees as white space.
      const marks = svg.querySelectorAll('path, circle, rect, line, polyline');
      entry.nodes = marks.length;
      if (!marks.length) {
        entry.findings.push({ rule: 'drew-nothing', detail: 'the chart <svg> is present and drew no marks at all' });
      }
      out.push(entry); return;
    } else {
      // `g.node > path` is load-bearing: graphviz renders `shape=box, style=rounded` as a PATH,
      // not a polygon, so a selector list of polygon and ellipse alone matched nothing on every
      // mindmap and every tree and refused them as "drew nothing". Measured on this machine
      // against real `twopi` and `dot` output.
      nodes = [].slice.call(svg.querySelectorAll(
        'g.shape > rect, g.shape > polygon, g.shape > path, g.node > polygon, g.node > ellipse, g.node > path'))
        .map((el) => ({ el, box: boxOf(el), id: (el.parentNode.parentNode.getAttribute('class') || '').slice(0, 24) }));
      edges = [].slice.call(svg.querySelectorAll('path.connection, g.edge path'));
    }
    entry.nodes = nodes.length;
    if (!nodes.length) {
      entry.findings.push({ rule: 'drew-nothing', detail: 'the <svg> is present and carries zero nodes' });
      out.push(entry); return;
    }

    // ---- wider than its container. The figure is the column's width; an SVG wider than it is a
    //      page that scrolls sideways in the reader's hand.
    if (svgBox.w > figBox.w + 1) {
      const scrolls = getComputedStyle(figure).overflowX;
      if (scrolls !== 'auto' && scrolls !== 'scroll') {
        entry.findings.push({ rule: 'figure-wider-than-container', overflowPx: round(svgBox.w - figBox.w),
          detail: 'svg ' + svgBox.w + 'px inside a ' + figBox.w + 'px figure, and the figure does not scroll' });
      } else {
        entry.notes.push('wider than its column by ' + round(svgBox.w - figBox.w) + 'px and scrolls sideways on purpose');
      }
    }

    // ---- text outside its box. A text belongs to the SMALLEST shape whose box contains its
    //      center; if its own box is not inside that shape, it is outside the box it belongs to.
    texts = [].slice.call(svg.querySelectorAll('text'));
    texts.forEach((t) => {
      const label = (t.textContent || '').trim();
      if (!label) return;
      const box = boxOf(t);
      const cx = (box.x + box.r) / 2, cy = (box.y + box.b) / 2;
      let owner = null;
      nodes.forEach((n) => {
        if (cx < n.box.x || cx > n.box.r || cy < n.box.y || cy > n.box.b) return;
        if (!owner || area(n.box) < area(owner.box)) owner = n;
      });
      if (!owner) return;
      const over = Math.max(owner.box.x - box.x, box.r - owner.box.r,
                            owner.box.y - box.y, box.b - owner.box.b);
      if (over > 0.5) {
        entry.findings.push({ rule: 'text-outside-its-box', text: label.slice(0, 40),
          node: owner.id || '(unnamed)', overflowPx: round(over),
          detail: 'text ' + box.w + 'px wide in a ' + owner.box.w + 'px box' });
      }
    });

    // ---- a label under a node. Document order IS paint order in SVG, so a text with a filled
    //      shape after it that overlaps it is a label the reader cannot read. This is the one
    //      that caught the lane eyebrow under its own tag on the phone layout.
    const painted = [].slice.call(svg.querySelectorAll('rect, polygon, ellipse, circle'));
    const all = [].slice.call(svg.querySelectorAll('text, rect, polygon, ellipse, circle'));
    texts.forEach((t) => {
      const label = (t.textContent || '').trim();
      if (!label) return;
      const box = boxOf(t);
      const after = all.indexOf(t);
      painted.forEach((shape) => {
        if (all.indexOf(shape) < after) return;
        const fill = shape.getAttribute('fill') || getComputedStyle(shape).fill;
        if (!fill || fill === 'none' || fill === 'transparent') return;
        if (shape.contains(t) || t.contains(shape)) return;
        const sBox = boxOf(shape);
        // a shape that CONTAINS the text is its own box, which the rule above already judges
        if (sBox.x <= box.x + 0.5 && sBox.r >= box.r - 0.5 && sBox.y <= box.y + 0.5 && sBox.b >= box.b - 0.5) return;
        if (overlap(box, sBox)) {
          entry.findings.push({ rule: 'label-under-a-node', text: label.slice(0, 40),
            coveredBy: shape.getAttribute('class') || shape.tagName,
            detail: 'a filled shape painted after it overlaps it' });
        }
      });
    });

    // ---- two node boxes on top of each other. A lane and a column can hold more than one
    //      thing, and a renderer that does not know that draws them at the same coordinates.
    //      A real figure shipped with two pairs stacked that way.
    if (kind === 'flow') {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          if (overlap(nodes[i].box, nodes[j].box)) {
            entry.findings.push({ rule: 'nodes-overlap', node: nodes[i].id || '(unnamed)',
              text: nodes[j].id || '(unnamed)',
              detail: 'two boxes occupy the same space at ' + nodes[i].box.x + ',' + nodes[i].box.y });
          }
        }
      }
      // a tag is pinned to its own box on purpose and may cover NOBODY else's
      [].slice.call(svg.querySelectorAll('rect.flow-mark')).forEach((tag) => {
        const own = tag.getAttribute('data-node');
        const tBox = boxOf(tag);
        nodes.forEach((n) => {
          if (n.id === own) return;
          if (overlap(tBox, n.box)) {
            entry.findings.push({ rule: 'tag-over-another-node', node: n.id || '(unnamed)',
              text: own || '(unnamed)', detail: 'the tag pinned to one box covers another' });
          }
        });
      });
    }

    // ---- a connector through a node. The path is SAMPLED, so the check does not assume the
    //      renderer only ever draws straight segments, and 1.5px of slack keeps an arrow that
    //      ENDS on a border from reading as one that goes through it.
    const ctm = svg.getScreenCTM();
    if (ctm) {
      edges.forEach((p) => {
        const total = p.getTotalLength ? p.getTotalLength() : 0;
        if (!total) return;
        const steps = Math.max(40, Math.min(600, Math.ceil(total / 2)));
        const hit = {};
        for (let s = 0; s <= steps; s++) {
          const pt = p.getPointAtLength((total * s) / steps);
          const q = new DOMPoint(pt.x, pt.y).matrixTransform(ctm);
          nodes.forEach((n, ni) => {
            if (q.x > n.box.x + 1.5 && q.x < n.box.r - 1.5 && q.y > n.box.y + 1.5 && q.y < n.box.b - 1.5) {
              hit[ni] = (hit[ni] || 0) + 1;
            }
          });
        }
        Object.keys(hit).forEach((ni) => {
          const record = { rule: 'connector-through-node', edge: p.getAttribute('data-edge') || '(unnamed)',
            node: nodes[ni].id || '(unnamed)', samplesInside: hit[ni],
            detail: 'the connector passes through the box at ' + nodes[ni].box.x + ',' + nodes[ni].box.y };
          if (kind === 'flow') entry.findings.push(record);
          else entry.notes.push('connector ' + record.edge + ' crosses node ' + record.node + ' (routed by the diagram engine, not by this skill)');
        });
      });
    }
    out.push(entry);
  });
  return out;
})()"""

# --------------------------------------------------------------------------- the clipping gate
#
# NO VALUE MAY LEAVE ITS BOX. A stat card that read "$7,475 to $12,131" clipped: the text came
# out of the side of the box on a page the lint had passed.
#
# The page-level overflow check above cannot see this. `.stat .num` is `white-space: nowrap`, so a
# value too long for its card spills INSIDE a page that does not overflow at all, and the lint
# passed both of the pages it happened on. A four-card stat row gives each card 189 pixels and
# `$41,014.06` renders at 192.
#
# This walks the elements a value can sit in and compares each one's scroll width against the box
# drawn around it, at every width and in both themes the render already visits.
#
# Proved by inversion on `fixtures/clipping-overflows.html` and `fixtures/clipping-wraps.html`:
# the same value in the same card, once nowrap and once wrapped, fails and passes.
# The classes the BUILDER actually emits, read off build.py and the surface templates rather than
# guessed (the first list carried three selectors that matched nothing: `.stat .lab`, `.kpi .num`,
# `.kpi .lab`; the real names are `.stat .lbl`, `.kpi .n/.l/.d`, and the poster's `.bignum .n/.l`).
# Then every house class that carries `white-space: nowrap`, because nowrap is how a value leaves
# its box in silence.
CLIP_SELECTORS = [
    ".stat .num", ".stat .lbl",                 # the stat row, the card that clipped
    ".kpi .n", ".kpi .l", ".kpi .d",            # data-report KPI cards
    ".bignum .n", ".bignum .l",                 # the poster's three numbers
    ".chip", ".actions .who", ".actions .due",  # nowrap by design in the house CSS
    ".dt-count", "table.data td.num",           # nowrap by design in the house CSS
    "td", "th", ".ss-v", ".ss-k", "h1", "h2", "h3",
]

CLIP_MEASURE = """(() => {
  const sels = CLIP_SELECTORS_HERE;
  const bad = [];
  for (const sel of sels) {
    for (const el of document.querySelectorAll(sel)) {
      // An element that scrolls BY DESIGN is not a value leaving its box; the reader can reach
      // the rest. Only an element that hides or ignores its overflow is clipping.
      const ox = getComputedStyle(el).overflowX;
      if (ox === 'auto' || ox === 'scroll') continue;
      const over = el.scrollWidth - el.clientWidth;
      if (over > 1) {
        bad.push({ sel: sel, over: over, scrollWidth: el.scrollWidth,
                   clientWidth: el.clientWidth,
                   text: (el.textContent || '').trim().slice(0, 60) });
      }
    }
  }
  return bad;
})()""".replace("CLIP_SELECTORS_HERE", json.dumps(CLIP_SELECTORS))

MEASURE_EXPRESSION = """() => {
  const nav = document.getElementById('sidenav');
  const navBox = nav ? nav.getBoundingClientRect() : null;
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    height: document.documentElement.scrollHeight,
    navVisible: !!nav,
    navHeight: navBox ? Math.round(navBox.height) : 0,
    navViewport: window.innerHeight,
    navHidden: nav ? getComputedStyle(nav).display === 'none' : true,
    figures: FIGURES_HERE,
    clipped: CLIPPED_HERE,
  };
}""".replace("FIGURES_HERE", FIGURE_MEASURE).replace("CLIPPED_HERE", CLIP_MEASURE)

# 900 CSS pixels, not the browser default, because 1440x900 is an ordinary laptop screen and it
# is the viewport the nav-height rule is written against.
RENDER_HEIGHT = 900

# Both themes, always. A figure whose text is drawn in the box's own fill is invisible in one
# theme and perfect in the other, and the light render is the one everybody looks at.
THEMES = ("light", "dark")

PLAYWRIGHT_JS = """
const { chromium } = require(process.argv[2]);
const MEASURE = %s;
const THEMES = %s;
(async () => {
  const browser = await chromium.launch();
  const out = [];
  for (const width of JSON.parse(process.argv[5] || "[1440,1920]")) {
    for (const theme of THEMES) {
      const page = await browser.newPage({ viewport: { width, height: %d } });
      await page.goto(process.argv[3]);
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
      await page.waitForTimeout(350);
      const m = await page.evaluate(MEASURE);
      if (process.argv[4] && theme === 'light') {
        await page.screenshot({ path: process.argv[4].replace('WIDTH', String(width)), fullPage: true });
      }
      out.push({ width, theme, ...m });
      await page.close();
    }
  }
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(String(e)); process.exit(3); });
""" % (MEASURE_EXPRESSION, json.dumps(list(THEMES)), RENDER_HEIGHT)


def playwright_python(path: Path, shot_pattern: str | None, widths: list[int]) -> list[dict] | None:
    """Measure with the Python package when it is installed. Returns None when it is not."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return None
    measurements: list[dict] = []
    with sync_playwright() as api:
        browser = api.chromium.launch()
        for width in widths:
            for theme in THEMES:
                page = browser.new_page(viewport={"width": width, "height": RENDER_HEIGHT})
                page.goto(path.resolve().as_uri())
                page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                page.wait_for_timeout(350)
                entry = page.evaluate(MEASURE_EXPRESSION)
                if shot_pattern and theme == "light":
                    page.screenshot(path=shot_pattern.replace("WIDTH", str(width)), full_page=True)
                entry["width"] = width
                entry["theme"] = theme
                measurements.append(entry)
                page.close()
        browser.close()
    return measurements


def playwright_check(path: Path, shot_pattern: str | None, widths: list[int] | None = None) -> tuple[list[str], list[str]]:
    """A requested render that could not run is a FAILURE, never a quiet pass."""
    failures: list[str] = []
    notes: list[str] = []

    widths = widths or [1440, 1920]
    measurements = playwright_python(path, shot_pattern, widths)
    if measurements is not None:
        return report_measurements(measurements, failures, notes)

    module_root = next((r for r in NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir()), None)
    if module_root is None:
        failures.append(
            "the render was asked for and did NOT run: no playwright python package and "
            "no node module root (set PLAYWRIGHT_NODE_ROOT, or pip install playwright)"
        )
        return failures, notes
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "shot.js"
        script.write_text(PLAYWRIGHT_JS, encoding="utf-8")
        # a real file:// URL built in Python: escaping a Windows path inside embedded JS is how
        # the pdf path broke, and as_uri() also handles a directory name with a space in it
        args = ["node", str(script), str(Path(module_root) / "playwright"), path.resolve().as_uri()]
        args.append(shot_pattern or "")
        args.append(json.dumps(widths))
        result = subprocess.run(args, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        failures.append(f"the render was asked for and FAILED: {result.stderr.strip()[:200]}")
        return failures, notes
    try:
        measurements = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        failures.append("the render was asked for and produced no measurement")
        return failures, notes
    return report_measurements(measurements, failures, notes)


# A finding is reported ONCE with every width and theme it happened at, rather than six times
# over. Six copies of one sentence is how a real failure gets skimmed past.
FIGURE_RULE_TEXT = {
    "drew-nothing": "drew nothing",
    "superseded-renderer": "was drawn by a superseded copy of the flow renderer",
    "figure-wider-than-container": "is wider than the column it sits in",
    "text-outside-its-box": "draws text outside the box it belongs to",
    "label-under-a-node": "paints a label under a shape that covers it",
    "connector-through-node": "routes a connector through a node",
    "nodes-overlap": "draws two node boxes on top of each other",
    "tag-over-another-node": "pins a tag over a box that is not its own",
}


def figure_findings(measurements: list[dict]) -> tuple[list[str], list[str]]:
    """Fold every figure finding into one line per distinct defect, naming where it happened."""
    seen: dict[tuple, list[str]] = {}
    detail: dict[tuple, dict] = {}
    notes: list[str] = []
    note_seen: set[tuple[str, str]] = set()
    for entry in measurements:
        where = f"{entry.get('width')}px {entry.get('theme', 'light')}"
        for figure in entry.get("figures") or []:
            for note in figure.get("notes") or []:
                key = (figure["name"], note)
                if key not in note_seen:
                    note_seen.add(key)
                    notes.append(f"figure \"{figure['name']}\": {note}")
            for hit in figure.get("findings") or []:
                key = (
                    figure["name"], hit["rule"], hit.get("node", ""),
                    hit.get("text", ""), hit.get("edge", ""),
                )
                seen.setdefault(key, []).append(where)
                detail.setdefault(key, hit)
    failures: list[str] = []
    for key, wheres in seen.items():
        name, rule = key[0], key[1]
        hit = detail[key]
        what = FIGURE_RULE_TEXT.get(rule, rule)
        parts = [f'the figure "{name}" {what}']
        if hit.get("node"):
            parts.append(f"node {hit['node']}")
        if hit.get("edge"):
            parts.append(f"edge {hit['edge']}")
        if hit.get("text"):
            parts.append(f'text "{hit["text"]}"')
        if hit.get("overflowPx"):
            parts.append(f"{hit['overflowPx']}px over")
        if hit.get("samplesInside"):
            parts.append(f"{hit['samplesInside']} sampled points inside the box")
        if hit.get("detail"):
            parts.append(hit["detail"])
        parts.append("at " + ", ".join(sorted(set(wheres))))
        failures.append(": ".join(parts[:2]) + (" - " + "; ".join(parts[2:]) if len(parts) > 2 else ""))
    return failures, notes


def clipping_findings(measurements: list[dict]) -> list[str]:
    """One line per clipped element, naming every width and theme it clipped at.

    Folded the way the figure findings are folded: six copies of one sentence is how a real
    failure gets skimmed past. The key is the selector plus the text, because the same value in
    the same card is the same defect whichever width found it.
    """
    seen: dict[tuple[str, str], dict] = {}
    for entry in measurements:
        where = f"{entry['width']} ({entry.get('theme', 'light')})"
        for hit in entry.get("clipped") or []:
            key = (hit["sel"], hit["text"])
            row = seen.setdefault(key, {"where": [], "over": -1, "hit": hit})
            row["where"].append(where)
            # The whole hit travels with its maximum, so the printed scrollWidth and clientWidth
            # are the pair that produced the printed overflow rather than the first pair seen.
            if hit["over"] > row["over"]:
                row["over"] = hit["over"]
                row["hit"] = hit
    out: list[str] = []
    for (sel, text), row in seen.items():
        hit = row["hit"]
        out.append(
            f"text leaves its box: {sel} overflows by {row['over']}px "
            f"({hit['scrollWidth']} of content in a {hit['clientWidth']}px box) at "
            f"{', '.join(row['where'])}: {text!r}. No value may leave its box; "
            "widen the box, shorten the value, or let it wrap."
        )
    return out


def report_measurements(measurements: list[dict], failures: list[str], notes: list[str]) -> tuple[list[str], list[str]]:
    figure_failures, figure_notes = figure_findings(measurements)
    failures += figure_failures
    notes += figure_notes
    clip_failures = clipping_findings(measurements)
    failures += clip_failures
    if not clip_failures:
        widths = sorted({m["width"] for m in measurements})
        themes = sorted({m.get("theme", "light") for m in measurements})
        notes.append(
            f"no value leaves its box: {len(CLIP_SELECTORS)} selectors checked at "
            f"{', '.join(str(w) for w in widths)} in {', '.join(themes)}"
        )
    for entry in measurements:
        if entry["scrollWidth"] > entry["innerWidth"] + 1:
            failures.append(
                f"horizontal overflow at {entry['width']} ({entry.get('theme', 'light')}): "
                f"scrollWidth {entry['scrollWidth']} > innerWidth {entry['innerWidth']}"
            )
        # The nav must fit the screen it is read on. A 40-entry rail had to be zoomed to 50 percent
        # to be seen whole; a rail taller than the viewport is an unusable page, and only the
        # render can tell, which is why this check lives here and not in check().
        nav_height = entry.get("navHeight") or 0
        viewport = entry.get("navViewport") or RENDER_HEIGHT
        if nav_height and not entry.get("navHidden") and nav_height > viewport:
            failures.append(
                f"the section nav renders {nav_height}px tall at {entry['width']}x{viewport}, "
                f"taller than the screen (group the document into parts so the rail lists the "
                "parts, not every section)"
            )
        notes.append(
            f"rendered at {entry['width']}: {entry['height']}px tall, no overflow"
            + (f", nav {nav_height}px of {viewport}px" if nav_height else "")
            if entry["scrollWidth"] <= entry["innerWidth"] + 1
            else f"rendered at {entry['width']}: overflow"
        )
    return failures, notes


PDF_JS = """
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: process.argv[4], format: 'A4', printBackground: true,
                   margin: { top: '14mm', bottom: '14mm', left: '12mm', right: '12mm' } });
  await browser.close();
  console.log('ok');
})().catch(e => { console.error(String(e)); process.exit(3); });
"""


def export_pdf(path: Path, destination: Path) -> tuple[list[str], list[str]]:
    """Print the page to PDF through the SAME browser that renders it.

    One source of truth: the PDF is the page's own @media print block, so a print rule that is
    wrong shows up here rather than in whoever opens the attachment. No new dependency - this is
    the Playwright that lint.py already needs for the render check.
    """
    failures: list[str] = []
    notes: list[str] = []
    margin = {"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"}
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        pass
    else:
        with sync_playwright() as api:
            browser = api.chromium.launch()
            page = browser.new_page()
            page.goto(path.resolve().as_uri())
            page.wait_for_timeout(400)
            page.emulate_media(media="print")
            page.pdf(path=str(destination), format="A4", print_background=True, margin=margin)
            browser.close()
        notes.append(f"pdf written: {destination} ({destination.stat().st_size:,} bytes)")
        return failures, notes

    module_root = next((r for r in NODE_MODULE_ROOTS if r and (Path(r) / "playwright").is_dir()), None)
    if module_root is None:
        failures.append(
            "a pdf was asked for and could NOT be produced: no playwright python package and no node "
            "module root (set PLAYWRIGHT_NODE_ROOT, or pip install playwright)"
        )
        return failures, notes
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "pdf.js"
        script.write_text(PDF_JS, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script), str(Path(module_root) / "playwright"), path.resolve().as_uri(), str(destination.resolve())],
            capture_output=True, text=True, timeout=180,
        )
    if result.returncode != 0 or not destination.is_file():
        failures.append(f"the pdf was asked for and FAILED: {result.stderr.strip()[:200]}")
        return failures, notes
    notes.append(f"pdf written: {destination} ({destination.stat().st_size:,} bytes)")
    return failures, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a finished HTML deliverable.")
    parser.add_argument("file")
    parser.add_argument("--money", action="store_true", help="list money tokens and fail on placeholder amounts")
    parser.add_argument("--playwright", action="store_true", help="render and check for horizontal overflow")
    parser.add_argument("--widths", default="1440,1920", help="the viewport widths to render at (add 390 for the phone check)")
    parser.add_argument("--screenshots", default="", help="screenshot path pattern containing WIDTH")
    parser.add_argument(
        "--audience", default="auto", choices=["auto", "internal", "external"],
        help="external (a client, a partner, a teammate of another company) FAILS on a wall-list "
             "name; internal warns. auto reads the page's own data-audience, else internal.",
    )
    parser.add_argument(
        "--allow", action="append", default=[], metavar="NAME",
        help="a company this page is entitled to name. Repeatable, or one comma-separated list.",
    )
    parser.add_argument("--allow-commands", action="store_true", help="internal page: allow command tokens in prose")
    parser.add_argument("--allow-no-grips", action="store_true", help="a fragment or an embed: skip the width-handle rule")
    parser.add_argument("--pdf", action="store_true",
                        help="also print the page to PDF through its own print block")
    parser.add_argument("--pdf-out", default="", metavar="OUT.pdf",
                        help="where the PDF goes (default: <file>.pdf). Implies --pdf.")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"lint: cannot read {path}", file=sys.stderr)
        return 2
    html = path.read_text(encoding="utf-8-sig")

    allow = [part.strip() for entry in args.allow for part in entry.split(",") if part.strip()]
    failures, notes, warnings = check(
        html,
        money=args.money,
        allow_commands=args.allow_commands,
        allow_no_grips=args.allow_no_grips,
        audience=args.audience,
        allow=allow,
    )
    if args.playwright:
        widths = [int(w) for w in args.widths.split(",") if w.strip()]
        more_failures, more_notes = playwright_check(path, args.screenshots or None, widths)
        failures += more_failures
        notes += more_notes
    if args.pdf or args.pdf_out:
        destination = Path(args.pdf_out) if args.pdf_out else path.with_suffix(".pdf")
        more_failures, more_notes = export_pdf(path, destination)
        failures += more_failures
        notes += more_notes

    for note in notes:
        print(f"  . {note}")
    for warning in warnings:
        print(f"  ! {warning}")
    if failures:
        print(f"FAIL {path}")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"PASS {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
