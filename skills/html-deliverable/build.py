#!/usr/bin/env python3
"""Turn a markdown, CSV or JSON file into one self-contained HTML page in the house style.

    python build.py <input> <output.html> --surface report|deck|poster|data-report [options]

The page is composed from two files in this skill directory, and only from those two, so the
palette, the theme toggle, the right-side rAF nav and the print block can never drift:

    template.html            the house base (CSS, nav, toggle, live-reload) - never duplicated
    templates/<surface>.html the surface module: its extra CSS and its body skeleton

Surfaces:
    report       the default. A document somebody reads: a report, an audit, a brief.
    deck         a call document with an agenda spine and an owner-dated action table.
    poster       a client one-pager: hero, three numbers, problem to solution, one CTA.
    data-report  KPI cards, inline-SVG charts with a custom tooltip, the table, the method.

Looks (DESIGN.md is the authority):
    tint         the cool ground plus 28px graph paper, 1080px. Agendas, call documents, client
                 one-pagers, internal reading.
    classic      the warm gold report look, 1000px. Formal reports and deliverables.
    auto         the default resolution: tint for the deck and poster surfaces, classic for the
                 report and data-report surfaces. State it explicitly when you know the reader.

Client-safe by construction:
    The emitted page names no company, client or person it was not given. Every CSS and HTML
    comment is stripped from it, and the maker's mark ships only when `--mark "<text>"` asks for
    one. `--audience` rides along on the page so `lint.py` knows whether a wall-list name in it
    is a warning or a refusal; it defaults to EXTERNAL, because a page prepared for somebody
    else is the dangerous one and the builder cannot know who that is.

Inputs:
    .md          the first "# " line is the title; every "## " starts a section; every LATER
                 "# " line starts a PART, which groups the sections under it (see below).
    .csv / .tsv  rows become the data table; numeric columns become KPI cards and the chart.
    .json        a list of objects behaves like a CSV; an object becomes a definition table.

Large documents:
    A later "# " line is a PART heading. It opens its own block on the page ground, above the
    sections it introduces, and it is what the right-side nav lists at the top level; only the
    ACTIVE part's sections are expanded beneath it. The contents block follows the same grouping.
    A document with more than twelve top-level nav entries and NO parts of its own is grouped
    automatically, so a page author cannot produce a nav taller than the screen by accident.
    Headings step down consistently: part, section, sub-section.

Components from markdown (any table or list of data ships with filter and sort):
    Any rendered table of five rows or more becomes a FILTERABLE, SORTABLE table automatically.
    Put [table: plain] on the line before one to opt out; [table: sortable] forces a short one in.
    - [ ] task lines           become the persisted tap-to-check checklist
    [slider: Label | min | max | step | value | unit]   becomes a slider with a live readout
    The CSS and JS for those come from the components gallery, so there is one definition of each.

Nothing is invented. Every optional block that gets no data is removed rather than shipped with
a REPLACE marker in it, and `lint.py` fails the page if a REPLACE survives.

Requires the `markdown` package for .md input (pip install markdown). CSV and JSON need nothing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import itertools
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "template.html"
SURFACES = HERE / "templates"

# The kinds a page can declare with `--kind`. A document library that indexes built pages can
# read the tag instead of guessing the kind from the file name. ONE list: the help text is built
# from this tuple and an unknown `--kind` is refused before a page is built, because a typo would
# emit a tag that reads as an answer. Extend the tuple if your own library knows more kinds.
KINDS: tuple[str, ...] = (
    "report", "decision pack", "agenda", "audit", "research", "guide",
    "brief", "register", "list", "record", "mockup", "triage",
)

# The component catalogue lives in ONE place: the gallery builder. Importing it here means a
# component's CSS and JS can never drift between the gallery that documents it and the pages
# that ship it - which is the whole point of DESIGN.md's anti-regression law.
sys.path.insert(0, str(HERE))
try:
    from build_gallery import COMPONENTS as GALLERY_COMPONENTS  # noqa: E402
except ImportError:  # pragma: no cover - only if the gallery builder is missing
    GALLERY_COMPONENTS = []

COMPONENT_ASSETS = {c.cid: (c.css, c.js) for c in GALLERY_COMPONENTS}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
HREF_RE = re.compile(r'href="(https?://[^"]+)"')
H2_RE = re.compile(r"<h2>(.*?)</h2>", re.S)

# Every destination that leaves this document opens in a NEW TAB. A reader keeps a deliverable
# open in one of many tabs; a link that navigates the page away loses their place in the document
# and the back button does not always bring the scroll position with it. `noreferrer` rides with
# `noopener` because a bare `target="_blank"` hands the opened page a live `window.opener` handle
# back into this one.
NEW_TAB_REL = "noopener noreferrer"
A_TAG_RE = re.compile(r"<a\b([^>]*)>", re.I)
HREF_ATTR_RE = re.compile(r'\bhref\s*=\s*"([^"]*)"', re.I)
REL_ATTR_RE = re.compile(r'\brel\s*=\s*"([^"]*)"', re.I)
TARGET_ATTR_RE = re.compile(r'\btarget\s*=\s*"([^"]*)"', re.I)
# http, https and protocol-relative. A link to your own served documents is an https destination
# like any other, so it is covered by the same rule and needs no special case.
EXTERNAL_HREF_RE = re.compile(r'\s*(?:https?:)?//', re.I)


# --------------------------------------------------------------------------- helpers


def slugify(text: str, fallback: str = "s") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", strip_tags(text).lower()).strip("-")
    return slug or fallback


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def esc(text: str) -> str:
    """Escape for TEXT content. Never use this inside an attribute - see esc_attr."""
    return html.escape(str(text), quote=False)


def esc_attr(text: str) -> str:
    """Escape for an ATTRIBUTE value: quotes too, or a cell containing " ends the attribute early."""
    return html.escape(str(text), quote=True)


def read_text(path: Path) -> str:
    # utf-8-sig: a file a PowerShell script wrote carries a BOM.
    return path.read_text(encoding="utf-8-sig")


def block(text: str, name: str) -> str:
    """Return the contents between <!-- name --> and <!-- /name -->."""
    match = re.search(rf"<!--\s*{re.escape(name)}\s*-->(.*?)<!--\s*/{re.escape(name)}\s*-->", text, re.S)
    if not match:
        raise ValueError(f"marker {name} not found")
    return match.group(1)


def replace_block(text: str, name: str, body: str) -> str:
    pattern = rf"(<!--\s*{re.escape(name)}\s*-->)(.*?)(<!--\s*/{re.escape(name)}\s*-->)"
    return re.sub(pattern, lambda m: m.group(1) + body + m.group(3), text, flags=re.S)


def drop_block(text: str, name: str) -> str:
    pattern = rf"<!--\s*{re.escape(name)}\s*-->.*?<!--\s*/{re.escape(name)}\s*-->\s*"
    return re.sub(pattern, "", text, flags=re.S)


CURRENCY_SUFFIX_RE = re.compile(r"\s*(?:USD|MXN|GBP|EUR|CAD)$", re.I)


def is_number(value: str) -> bool:
    """A cell is numeric when it is a number, a money amount, or a percentage. The house money
    format names the currency AFTER the amount ("$1,403.81 USD", "$10,422.65 MXN"), so a trailing
    currency code is part of the number and the column still sorts numerically."""
    if value is None:
        return False
    cleaned = CURRENCY_SUFFIX_RE.sub("", str(value).strip())
    cleaned = cleaned.replace(",", "").replace("$", "").replace("%", "").replace("£", "")
    if not cleaned or cleaned in {"-", "."}:
        return False
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def to_number(value: str) -> float:
    cleaned = str(value).strip().replace(",", "").replace("$", "").replace("%", "").replace("£", "")
    return float(cleaned)


def fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.2f}"


# --------------------------------------------------------------------------- markdown


# "3. The budget" and, since parts exist, "2.4 Escalations" as well: the builder GENERATES dotted
# numbers, so an author who writes one back must not get a second, disagreeing number printed
# beside it.
NUMBERED_LABEL_RE = re.compile(r"^(\d+(?:\.\d+)*)[.)]\s+(.*)$|^(\d+(?:\.\d+)+)\s+(.*)$")


def own_number(label: str) -> tuple[str, str] | None:
    """(number, label without it) when the heading carries its own number, else None."""
    match = NUMBERED_LABEL_RE.match(label)
    if not match:
        return None
    number = match.group(1) or match.group(3)
    return number.rstrip("."), (match.group(2) if match.group(1) else match.group(4))


# Both levels split the document. Level 1 opens a PART, level 2 opens a section inside it.
# Splitting on level 2 alone strands every part heading at the foot of the card before it: an
# <h1> the splitter does not know about simply stays in the previous section's body.
HEADING_SPLIT_RE = re.compile(r"(<h1[^>]*>.*?</h1>|<h2[^>]*>.*?</h2>)", re.S | re.I)
# More top-level nav entries than this and the rail stops being readable at 100 percent zoom.
# Measured: 40 flat entries rendered a 1394px rail inside a 900px viewport.
NAV_GROUP_THRESHOLD = 12
# The size of an automatic group when the author declared no parts of their own.
AUTO_GROUP_SIZE = 8
BARE_URL_RE = re.compile(r"(?<![(<\[`\"'])\bhttps?://[^\s<>()\[\]\"'`]+")
CODE_SPAN_RE = re.compile(r"`[^`]*`|```.*?```", re.S)


def autolink(md_text: str) -> str:
    """Wrap bare URLs in angle brackets so Markdown renders them as real links.

    Authors write bare URLs constantly, and a destination that is not clickable breaks the
    always-link rule. URLs already inside a markdown link, a code span or a fenced block are
    left exactly as they are.
    """
    spans = [(m.start(), m.end()) for m in CODE_SPAN_RE.finditer(md_text)]

    def inside_code(index: int) -> bool:
        return any(start <= index < end for start, end in spans)

    out: list[str] = []
    last = 0
    for match in BARE_URL_RE.finditer(md_text):
        if inside_code(match.start()):
            continue
        url = match.group(0).rstrip(".,;:!?")
        out.append(md_text[last : match.start()])
        out.append(f"<{url}>")
        out.append(match.group(0)[len(url) :])
        last = match.end()
    out.append(md_text[last:])
    return "".join(out)


def demote_headings(html_text: str) -> str:
    """Push h3..h5 down one level, so a grouped document's outline steps down cleanly.

    In a grouped document the part takes h2 and the section takes h3, so a markdown "###"
    sub-section has to become an h4 or it collides with the section title it sits under.
    Descending order matters: shifting h3 first would shift the same heading twice.
    """
    for level in (5, 4, 3):
        html_text = re.sub(rf"<h{level}(\b[^>]*)>", rf"<h{level + 1}\1>", html_text, flags=re.I)
        html_text = re.sub(rf"</h{level}>", f"</h{level + 1}>", html_text, flags=re.I)
    return html_text


LIST_MARKER_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+\S")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def normalize_lists(md_text: str) -> str:
    """Fix the two nested-list shapes that silently lose content before anything is rendered.

    1. **A nested list indented by one to three spaces is not nested at all.** Python-Markdown's
       `sane_lists` wants four, so "- One" with "  - Nested a" under it renders as three flat
       bullets, and under an ORDERED parent it renders as literal text inside the paragraph:
       `<p>One    - Nested a</p>`. The sub-bullets are simply gone. Indents are snapped to
       multiples of four, so the nesting the author wrote is the nesting the reader sees.
    2. **A line of prose directly under a bullet, with no blank line, is swallowed INTO it**
       (markdown calls this lazy continuation). The clause after the list disappears inside the
       last bullet. A blank line is inserted so it stays its own paragraph.

    Fenced blocks are left exactly as written: a code fence holds a paste-ready message, and
    reindenting one would change what the reader pastes.
    """
    out: list[str] = []
    fence: str | None = None
    levels: list[tuple[int, int]] = []  # (indent as written, indent as rendered)
    after_marker = False
    for line in md_text.split("\n"):
        fence_hit = FENCE_RE.match(line)
        if fence_hit:
            fence = None if fence and line.lstrip().startswith(fence) else (fence or fence_hit.group(1))
            out.append(line)
            after_marker = False
            continue
        if fence is not None:
            out.append(line)
            continue
        marker = LIST_MARKER_RE.match(line)
        if marker:
            indent = len(marker.group(1))
            # An INDENTED CODE BLOCK whose lines happen to start with "- " is not a list. Four or
            # more spaces with no list open above it is code, and reindenting it would turn a
            # paste-ready block into bullets.
            if not levels and indent >= 4:
                out.append(line)
                after_marker = False
                continue
            while levels and indent < levels[-1][0]:
                levels.pop()
            if not levels:
                levels = [(indent, 0)]
            elif indent > levels[-1][0]:
                levels.append((indent, levels[-1][1] + 4))
            out.append(" " * levels[-1][1] + line[indent:])
            after_marker = True
            continue
        if not line.strip():
            out.append(line)
            after_marker = False
            continue
        # A bullet whose own prose wraps onto the next line keeps wrapping: that line continues a
        # sentence and starts lowercase. A line that OPENS something (a capital, a bold run, a
        # quote) directly under a bullet is a clause of the document, and swallowing it into the
        # bullet is what loses it.
        if after_marker and not line[:1].isspace() and not line[:1].islower():
            out.append("")  # the clause keeps its own block instead of vanishing into the bullet
            out.append(line)
            levels = []
            after_marker = False
            continue
        if not after_marker and not line[:1].isspace():
            levels = []
        out.append(line)
        after_marker = False
    return "\n".join(out)


def markdown_to_sections(
    md_text: str, used: set[str] | None = None, prefix: str = "", numbered: bool = True
) -> tuple[str, list[dict[str, str]]]:
    """Return (title, blocks). Blocks split on level-1 AND level-2 headings.

    Each block is {kind, id, label, num, html, part}: `kind` is "part" for a level-1 heading and
    "section" for a level-2 one, and a section's `part` is the id of the part it belongs to.

    A heading that already carries its own number ("## 3. The tax sitting") keeps THAT number;
    the builder never adds a second, disagreeing one beside it. A section inside a part is
    numbered within its part ("2.4"), so the number says where the reader is.

    `used` collects the component ids the content asked for, so only their CSS and JS ship.
    """
    try:
        import markdown as md_lib
    except ImportError:  # pragma: no cover - environment dependent
        raise SystemExit("build.py needs the markdown package for .md input: pip install markdown")

    if used is None:
        used = set()

    # The component counters restart for EVERY document. They are module-level generators, so
    # without this a second build in the same process numbered its first slider sl2, and the
    # reader's saved state for that page would be orphaned by an ordinary rebuild.
    global _slider_seq, _checklist_seq
    _slider_seq = itertools.count(1)
    _checklist_seq = itertools.count(1)

    lines = md_text.splitlines()
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]

    body_md = autolink(normalize_lists("\n".join(lines)))
    before = body_md
    body_md = slider_markers(body_md, prefix)
    if body_md != before:
        used.add("slider")
    rendered = md_lib.markdown(body_md, extensions=["extra", "sane_lists"])
    rendered, has_checklist = checklist_blocks(rendered, prefix)
    if has_checklist:
        used.add("checklist")
    rendered, has_dt = upgrade_tables(rendered)
    if has_dt:
        used.add("data-table")
    rendered, has_diagram = diagram_blocks(rendered, prefix)
    if has_diagram:
        used.add("diagram")
    # A component written as raw HTML in the source still needs its CSS and its JS. Detecting it
    # by its own data attribute means the gallery stays the one definition and a hand-written
    # figure is not a silently unstyled block.
    if "data-gbar" in rendered:
        used.add("grouped-bar")
    if 'class="tl"' in rendered:
        used.add("timeline")
    # The three components a HAND-COMPOSED page uses. Without these, a page that follows the
    # skill's own instruction to compose from the gallery ships with the markup and none of the
    # CSS or JS: the flow figure renders as nothing at all, and the summary strips and the
    # questions block render as unstyled divs.
    if 'class="flow"' in rendered or "flow-data" in rendered:
        used.add("flow")
    if "stage-summary" in rendered or 'class="fold"' in rendered or "data-fold" in rendered:
        used.add("part-summary")
    if 'class="asks"' in rendered:
        used.add("asks")

    pieces = HEADING_SPLIT_RE.split(rendered)
    blocks: list[dict[str, str]] = []
    lead = pieces[0].strip()
    if lead:
        blocks.append(
            {"kind": "section", "id": "intro", "label": "Overview", "num": "", "html": lead, "part": "", "lead": "1"}
        )
    part_counter = 0
    section_counter = 0
    in_part = ""
    in_part_num = ""
    within_part = 0
    # A part and a section may carry the same words ("Findings" under "Findings"), and two ids the
    # same makes the nav point at whichever the browser finds first.
    taken: set[str] = {b["id"] for b in blocks}

    def unique(base: str) -> str:
        candidate, suffix = base, 2
        while candidate in taken:
            candidate, suffix = f"{base}-{suffix}", suffix + 1
        taken.add(candidate)
        return candidate

    for index in range(1, len(pieces), 2):
        heading = pieces[index]
        body = (pieces[index + 1] if index + 1 < len(pieces) else "").strip()
        label = strip_tags(heading)
        own = own_number(label)
        if re.match(r"<h1", heading, re.I):
            part_counter += 1
            within_part = 0
            num = own[0] if own else str(part_counter)
            if own:
                label = own[1]
            in_part = unique(slugify(label, f"part{part_counter}"))
            in_part_num = num
            blocks.append(
                {"kind": "part", "id": in_part, "label": label, "num": num if numbered else "",
                 "html": body, "part": "", "lead": ""}
            )
            continue
        section_counter += 1
        within_part += 1
        if own:
            num, label = own
        elif not numbered:
            num = ""
        elif in_part:
            num = f"{in_part_num}.{within_part}" if in_part_num else str(within_part)
        else:
            num = str(section_counter)
        blocks.append(
            {"kind": "section", "id": unique(slugify(label, f"s{len(blocks) + 1}")), "label": label,
             "num": num, "html": body, "part": in_part, "lead": ""}
        )

    # A document with parts of its own runs part (h2), section (h3), sub-section (h4). Only then
    # does the content need demoting; a flat document keeps the sizes it has always had.
    if any(b["kind"] == "part" for b in blocks):
        for b in blocks:
            b["html"] = demote_headings(b["html"])
    return title, blocks


# --------------------------------------------------------------------------- components

SLIDER_RE = re.compile(r"^\[slider:\s*(.+?)\]\s*$", re.M)
TABLE_HINT_RE = re.compile(r"<p>\[table:\s*(plain|sortable)\]</p>\s*", re.I)
TASK_ITEM_RE = re.compile(r"<li>\s*\[([ xX])\]\s*(.*?)</li>", re.S)
TABLE_BLOCK_RE = re.compile(r"<table>(.*?)</table>", re.S | re.I)

_slider_seq = itertools.count(1)
_checklist_seq = itertools.count(1)


def store_prefix(destination: Path) -> str:
    """A per-document prefix for every persisted key.

    localStorage is shared across one origin, and a local server or a workspace serves many
    deliverables from the same one. Without this, every document's first slider wrote the same
    key and the checklist restored BY INDEX, so opening one document put another's ticks on
    unrelated items.
    """
    digest = hashlib.sha1(destination.name.encode("utf-8")).hexdigest()[:8]
    return f"{digest}-"


def slider_markers(md_text: str, prefix: str = "") -> str:
    """Turn [slider: Label | min | max | step | value | unit] into the house slider component.

    Rendered BEFORE markdown runs, so the markdown library never sees the brackets and never
    turns them into a stray link reference.
    """

    def build_one(match: re.Match[str]) -> str:
        parts = [p.strip() for p in match.group(1).split("|")]
        label = parts[0] if parts else "Value"
        low = parts[1] if len(parts) > 1 else "0"
        high = parts[2] if len(parts) > 2 else "100"
        step = parts[3] if len(parts) > 3 else "1"
        value = parts[4] if len(parts) > 4 else high
        unit = parts[5] if len(parts) > 5 else ""
        number = next(_slider_seq)
        ident = f"sl{number}"          # the input id: kept short and valid
        store = f"{prefix}sl{number}"  # the localStorage key: unique per document
        ticks = "".join(f"<span>{esc(t)}</span>" for t in tick_marks(low, high, step))
        return (
            f'<div class="slider-row" data-slider data-store="{store}">\n'
            f'  <div class="slider-head">\n'
            f'    <label class="slab" for="{ident}">{esc(label)}</label>\n'
            f'    <div class="slider-val"><span data-out>{esc(value)}</span>'
            + (f" <small>{esc(unit)}</small>" if unit else "")
            + "</div>\n  </div>\n"
            f'  <input type="range" id="{ident}" min="{esc_attr(low)}" max="{esc_attr(high)}" '
            f'step="{esc_attr(step)}" value="{esc_attr(value)}" aria-label="{esc_attr(label)}">\n'
            f'  <div class="ticks">{ticks}</div>\n'
            f"</div>"
        )

    return SLIDER_RE.sub(build_one, md_text)


def tick_marks(low: str, high: str, step: str = "1") -> list[str]:
    """Five evenly spaced labels. An integer-stepped slider gets integer ticks.

    Caught by looking at the render: a 5-to-40 slider stepping by 1 was labeled 13.75 and 31.25,
    which are values it cannot take.
    """
    try:
        a, b = float(low), float(high)
    except ValueError:
        return [low, high]
    try:
        whole = float(step).is_integer() and a.is_integer() and b.is_integer()
    except ValueError:
        whole = False
    values = [a + (b - a) * i / 4 for i in range(5)]
    if whole:
        values = [float(round(v)) for v in values]
    return [fmt_number(v) for v in values]


LI_RE = re.compile(r"<li>.*?</li>", re.S)


def checklist_blocks(rendered: str, store_prefix: str = "") -> tuple[str, bool]:
    """Turn a GFM task list into the persisted tap-to-check checklist.

    A list is converted ONLY when EVERY item in it is a task item. A mixed list is left exactly
    as it is: rebuilding the block from the task items alone silently deleted the plain bullets,
    which is content loss in a deliverable and breaks the module's own "nothing is invented"
    contract.
    """
    used = False

    def convert(match: re.Match[str]) -> str:
        nonlocal used
        body = match.group(1)
        all_items = LI_RE.findall(body)
        items = TASK_ITEM_RE.findall(body)
        if len(items) < 2 or len(items) != len(all_items):
            return match.group(0)  # not a task list, or a MIXED list: leave every bullet intact
        used = True
        ident = f"{store_prefix}cl{next(_checklist_seq)}"
        rows = "".join(
            f'  <label><input type="checkbox"{" checked" if mark.lower() == "x" else ""}> '
            f"<span>{text.strip()}</span></label>\n"
            for mark, text in items
        )
        return (
            f'<div class="checklist" data-checklist data-store="{ident}">\n{rows}'
            f'  <div class="check-count" data-check-count></div>\n</div>'
        )

    out = re.sub(r"<ul>(.*?)</ul>", convert, rendered, flags=re.S)
    return out, used


TH_RE = re.compile(r"<th\b[^>]*>(.*?)</th>", re.S | re.I)
# an optional hint bound to the table it precedes, matched in ONE pass so a stray marker
# elsewhere in the document can never be handed to a different table
HINTED_TABLE_RE = re.compile(
    r"(?:<p>\[table:\s*(plain|sortable)\]</p>\s*)?<table>(.*?)</table>", re.S | re.I
)


def upgrade_tables(rendered: str) -> tuple[str, bool]:
    """Any table of five DATA rows or more gets the filter and the sortable headers.

    The rule: a filtering and sorting mechanism whenever there is a table or a list of data.
    Five data rows, because a three-row layout table is not data. A [table: plain] hint on
    the line before opts one out; [table: sortable] forces a short one in. The hint is captured in
    the SAME match as the table it precedes: consuming hints from a separate list let a stray
    marker in one section silently apply to a table in another.
    """
    used = False

    def convert(match: re.Match[str]) -> str:
        nonlocal used
        forced = (match.group(1) or "").lower()
        inner = match.group(2)
        rows = len(re.findall(r"<tr\b", inner, re.I))  # header included
        if forced == "plain" or (rows < 6 and forced != "sortable"):
            return f"<table>{inner}</table>"  # the hint is consumed either way, never rendered
        used = True
        head_match = re.search(r"<thead>.*?</thead>", inner, re.S | re.I)
        body_match = re.search(r"<tbody>(.*?)</tbody>", inner, re.S | re.I)
        head = head_match.group(0) if head_match else ""
        columns = TH_RE.findall(head)
        body_rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", body_match.group(1) if body_match else "", re.S | re.I)
        cells_by_column: list[list[str]] = [[] for _ in columns]
        for row in body_rows:
            cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S | re.I)
            for index, cell in enumerate(cells[: len(columns)]):
                cells_by_column[index].append(strip_tags(cell))

        def kind(index: int) -> str:
            values = [v for v in cells_by_column[index] if v]
            return "num" if values and all(is_number(v) for v in values) else "text"

        # rewrite POSITIONALLY. Matching a header by its own text rewrote the first <th> with
        # that label every time, so a table with two columns named the same got one marked with
        # the other's type and one left unsortable.
        counter = iter(range(len(columns)))

        def stamp(cell: re.Match[str]) -> str:
            index = next(counter, None)
            if index is None:
                return cell.group(0)
            return f'<th data-sort="{kind(index)}">{cell.group(1)}</th>'

        new_head = TH_RE.sub(stamp, head)
        inner = inner.replace(head, new_head, 1) if head else inner
        return (
            '<div class="dt-wrap">\n'
            '  <div class="dt-controls">\n'
            '    <input type="search" class="dt-filter" placeholder="Filter these rows" aria-label="Filter the table">\n'
            '    <span class="dt-count"></span>\n'
            "  </div>\n"
            f'  <div class="scroll"><table class="dt">{inner}</table></div>\n'
            "</div>"
        )

    out = HINTED_TABLE_RE.sub(convert, rendered)
    # a hint that precedes no table at all is dropped rather than shown to the reader
    out = TABLE_HINT_RE.sub("", out)
    return out, used


def component_assets(used: set[str]) -> tuple[str, str]:
    """The CSS and the JS for the components a page actually used, and nothing else."""
    css_parts, js_parts = [], []
    # The diagram CSS lives in build.py, not in the gallery catalogue, because the builder is
    # what pre-renders the SVG and the two have to change together. The gallery's diagram demos
    # import this same string, so there is still exactly one definition.
    if "diagram" in used:
        css_parts.append(DIAGRAM_CSS.strip("\n"))
    # Every component the page used that has assets in the catalogue, not a hard-coded handful.
    # A hard-coded tuple was the reason a hand-composed page could be detected correctly, print
    # "components: asks, flow, part-summary" in the build line, and still ship with none of their
    # CSS or JS. Sorted so a rebuild of the same page is byte-identical.
    for cid in sorted(used):
        if cid in COMPONENT_ASSETS:
            css, js = COMPONENT_ASSETS[cid]
            if css:
                css_parts.append(css)
            if js:
                js_parts.append(js)
    js = "(function(){\n" + "\n".join(js_parts) + "\n})();" if js_parts else ""
    return "\n".join(css_parts), js


def sections_to_html(blocks: list[dict[str, str]]) -> str:
    """The page body: a part opens its own block, a section is a card.

    A part heading is NEVER rendered inside a section card. That is the whole stranded-heading
    defect: a part heading sat as the last child of the card before it, with nothing under it,
    because the splitter did not know level-1 headings existed.
    """
    grouped = any(b["kind"] == "part" for b in blocks)
    out: list[str] = []
    for index, block in enumerate(blocks):
        if block["kind"] == "part":
            marker = f'    <div class="part-num">Part {esc(block["num"])}</div>\n' if block["num"] else ""
            # A PART'S OWN BODY GETS A CARD. A part that opens sections keeps its body as the lede
            # above them. A part with NO sections under it is a section in everything but name, so
            # its body is rendered in the same card a section gets rather than as bare prose on
            # the page ground. lint.py refuses the bare form.
            following = blocks[index + 1] if index + 1 < len(blocks) else None
            alone = not (following and following["kind"] == "section")
            intro = "" if (alone and block["html"]) else (f'\n{block["html"]}' if block["html"] else "")
            out.append(
                f'  <div class="part-head" id="{block["id"]}">\n{marker}'
                f'    <h2 class="part-title">{esc(block["label"])}</h2>{intro}\n  </div>\n'
            )
            if alone and block["html"]:
                out.append(f'  <section id="{block["id"]}-body">\n{block["html"]}\n  </section>\n')
            continue
        tag = "h3" if grouped else "h2"
        title_class = ' class="sec-title"' if grouped else ""
        if block["num"]:
            head = (
                f'    <div class="sec-num">{esc(block["num"])}</div>\n'
                f'    <{tag}{title_class}>{esc(block["label"])}</{tag}>\n'
            )
        elif block.get("lead"):
            # the Overview block has no heading of its own: its label IS the marker
            head = f'    <div class="sec-num">{esc(block["label"])}</div>\n'
        else:
            # --unnumbered: the label is still a real heading, never a bare eyebrow line
            head = f'    <{tag}{title_class}>{esc(block["label"])}</{tag}>\n'
        out.append(f'  <section id="{block["id"]}">\n{head}{block["html"]}\n  </section>\n')
    return "\n".join(out)


# --------------------------------------------------------------------------- diagrams
#
# A shape the `flow` component cannot draw is PRE-RENDERED to inline SVG at build time by a real
# diagram engine and restyled onto the house tokens. Never a CDN, never a runtime script: a
# deliverable has to render offline when it is dragged into a message, and a diagram that needs
# the network is a diagram that is blank in the one place the reader opens it.
#
# Two engines, chosen after the comparison in DESIGN.md section 3a:
#   d2 (MPL-2.0)        flowchart, sequence  - a single Go binary, its own language, native
#                                              sequence diagrams, theme-slot classes on the SVG
#   graphviz (EPL-2.0)  mindmap, tree        - the twopi radial and dot hierarchical layouts,
#                                              from an indented outline this module compiles
#                                              into DOT so nobody writes DOT by hand
#
# Both run locally, offline, with no service and no Node. Neither is bundled with this skill;
# `diagram_binary` says exactly how to install a missing one rather than printing a stack trace.

DIAGRAM_HINT_RE = re.compile(
    r"<p>\s*\[diagram:\s*([a-z][a-z-]*)\s*(?:\|\s*(.*?))?\]\s*</p>\s*"
    r"<pre><code[^>]*>(.*?)</code></pre>",
    re.S | re.I,
)
# Every kind names its engine, the layout program, and whether its source is the engine's own
# language or the indented outline this module compiles.
DIAGRAM_KINDS: dict[str, dict[str, str]] = {
    "flowchart": {"engine": "d2", "layout": "dagre", "source": "d2"},
    "sequence": {"engine": "d2", "layout": "dagre", "source": "d2-sequence"},
    "mindmap": {"engine": "graphviz", "layout": "twopi", "source": "outline"},
    "tree": {"engine": "graphviz", "layout": "dot", "source": "outline"},
}
DIAGRAM_INSTALL = {
    "d2": "winget install Terrastruct.D2, or the windows-amd64 tarball from "
          "https://github.com/d2lang/d2/releases (a single d2.exe, no service)",
    "graphviz": "winget install Graphviz.Graphviz, or the windows_10_cmake_Release zip from "
                "https://gitlab.com/graphviz/graphviz/-/releases, then run `dot -c` once",
}
# Searched after PATH, so a per-user install that never touched PATH still builds. The glob
# matters: Graphviz's portable zip unpacks to a version-stamped folder.
DIAGRAM_BIN_GLOBS = (
    "~/AppData/Local/Programs/d2",
    "~/AppData/Local/Programs/Graphviz*/bin",
    "C:/Program Files/Graphviz/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
)
XML_DECL_RE = re.compile(r"<\?xml[^>]*\?>\s*", re.I)
DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>\s*", re.I | re.S)
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.S | re.I)
FONT_FAMILY_RULE_RE = re.compile(r"font-family:\s*[^;}]*;?", re.I)
SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.I)
SVG_SIZE_ATTR_RE = re.compile(r'\s(?:width|height)="[^"]*"', re.I)


def diagram_binary(name: str, engine: str) -> str:
    """The executable for `name`, from PATH or a known per-user install, or an actionable exit."""
    import shutil

    import glob as globlib

    found = shutil.which(name)
    if found:
        return found
    for pattern in DIAGRAM_BIN_GLOBS:
        # expanduser FIRST, then glob the whole path: the wildcard is in the middle of the
        # Graphviz pattern (a version-stamped folder), not only in the last segment.
        for root in sorted(globlib.glob(str(Path(pattern).expanduser()))):
            for candidate in (Path(root) / f"{name}.exe", Path(root) / name):
                if candidate.is_file():
                    return str(candidate)
    raise SystemExit(
        f"build.py needs `{name}` on PATH to render a [diagram:] block. Install {engine}: "
        f"{DIAGRAM_INSTALL[engine]}"
    )


def outline_rows(text: str) -> list[tuple[int, str]]:
    """(depth, label) per line of an indented outline. Two spaces or a tab is one level."""
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = raw.replace("\t", "  ").rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        label = line.strip().lstrip("-*+ ").strip()
        if label:
            rows.append((indent // 2, label))
    return rows


def outline_to_dot(text: str, layout: str) -> str:
    """Compile an indented outline into DOT, so nobody writes DOT by hand for a mind map.

    The outline is the shape everyone already writes a mind map in. `twopi` reads the root as
    the center and spreads the branches around it; `dot` reads the same rows as a left-to-right
    tree. Colors and fonts are deliberately NOT set here - the restyling pass owns those, and a
    color baked into DOT would win over the house token in one of the two themes.
    """
    rows = outline_rows(text)
    if not rows:
        raise SystemExit("a [diagram:] outline block is empty")
    # bgcolor=transparent, so graphviz does not paint a white ground polygon under the drawing.
    # That polygon is the one piece of its output a stylesheet cannot reach reliably (it is a
    # class-less child of the graph group), and in dark mode it renders as a white card behind
    # every node, measured on the first dark screenshot of the tree demo.
    lines = ["digraph G {", "  bgcolor=transparent;"]
    if layout == "twopi":
        lines += ["  layout=twopi;", "  ranksep=1.6;", "  overlap=false;"]
    else:
        lines += ["  layout=dot;", "  rankdir=LR;", "  ranksep=0.7;", "  nodesep=0.22;"]
    lines += ['  node [shape=box, style="rounded", margin="0.16,0.09", fontsize=13];', "  edge [];"]
    stack: list[str] = []
    for index, (depth, label) in enumerate(rows):
        node = f"n{index}"
        safe = label.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'  {node} [label="{safe}"];')
        del stack[depth:]
        if stack:
            lines.append(f"  {stack[-1]} -> {node};")
        stack.append(node)
    lines.append("}")
    return "\n".join(lines)


def d2_sequence_source(text: str) -> str:
    """Wrap plain messages in a sequence container, so the author writes only the conversation.

    The container's label is blanked. d2 prints a container's name as a 28px title above the
    diagram, and a wrapper this module invented has no business putting a heading on the page -
    the figure's caption is the author's own words and the only title the figure needs.
    """
    if "sequence_diagram" in text:
        return text
    body = "\n".join("  " + line if line.strip() else line for line in text.splitlines())
    return 'seq: {\n  shape: sequence_diagram\n  label: ""\n' + body + "\n}"


D2_DOLLAR_RE = re.compile(r"(?<!\\)\$(?!\{)")


def escape_d2_dollars(text: str) -> str:
    """Let an author write a dollar amount in a d2 label.

    d2 reads `$` as the opening of a variable substitution and REFUSES to compile without one:
    `a: "Costs $1,000"` answers `substitutions must begin on {` and the entire figure is lost,
    with nothing on the page to show for it. A backslash in front of it compiles and renders as a
    plain dollar sign.

    A `$` already escaped is left alone, and so is a deliberate `${name}` substitution, so this
    only ever rescues the case nobody meant to write in d2's language.
    """
    return D2_DOLLAR_RE.sub(r"\\$", text)


def run_engine(kind: str, source: str, salt: str) -> str:
    """The engine's raw SVG for one block. Runs offline; nothing is fetched."""
    import subprocess
    import tempfile

    spec = DIAGRAM_KINDS[kind]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if spec["engine"] == "d2":
            text = d2_sequence_source(source) if spec["source"] == "d2-sequence" else source
            text = escape_d2_dollars(text)
            src = work / "d.d2"
            src.write_text(text, encoding="utf-8")
            out = work / "d.svg"
            command = [
                diagram_binary("d2", "d2"),
                "--layout", spec["layout"], "--theme", "0", "--pad", "12", "--scale", "1",
                "--bundle=false", "--no-xml-tag", "--omit-version", "--salt", salt,
                str(src), str(out),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 or not out.exists():
                raise SystemExit(f"the [diagram: {kind}] block did not compile: {result.stderr.strip()[:400]}")
            return out.read_text(encoding="utf-8")
        dot_source = outline_to_dot(source, spec["layout"])
        command = [diagram_binary(spec["layout"], "graphviz"), "-Tsvg"]
        result = subprocess.run(command, input=dot_source, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0 or not result.stdout.strip():
            raise SystemExit(f"the [diagram: {kind}] block did not compile: {result.stderr.strip()[:400]}")
        return result.stdout


SVG_ID_RE = re.compile(r'\bid="([^"]+)"')
SVG_ID_REF_RE = re.compile(r'url\(#([^)"]+)\)|(?:xlink:)?href="#([^"]+)"')


def namespace_svg_ids(svg: str, uid: str) -> str:
    """Prefix every id in one diagram, and every reference to one, with that diagram's uid.

    Graphviz names its groups `graph0`, `node1`, `edge1` in EVERY drawing it makes, so two of
    its diagrams on one page ship a dozen duplicate ids - invalid HTML, and getElementById
    returns whichever the browser met first. d2 salts its own ids, but is namespaced here too so
    there is one rule rather than a per-engine exception. Caught by the gallery's duplicate-id
    check the moment a second graphviz demo joined the page.
    """
    names = set(SVG_ID_RE.findall(svg))
    if not names:
        return svg
    svg = SVG_ID_RE.sub(lambda m: f'id="{uid}-{m.group(1)}"', svg)

    def ref(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in names:
            return match.group(0)  # a reference out of this diagram is not ours to rewrite
        return f"url(#{uid}-{name})" if match.group(1) else match.group(0).replace(f"#{name}", f"#{uid}-{name}")

    return SVG_ID_REF_RE.sub(ref, svg)


def restyle_svg(svg: str, engine: str, uid: str) -> str:
    """Strip what an engine ships for standalone viewing, and put the house tokens back on top.

    Both engines write their palette as PRESENTATION ATTRIBUTES (`fill="#F7F8FE"`), which every
    stylesheet rule outranks. So the diagram is re-colored by a scoped CSS block rather than by
    rewriting the geometry, which means a theme toggle re-colors it live and a future engine
    version cannot silently drift the palette back.

    The engines' embedded web fonts go: a deliverable already declares the house font, and a
    base64 font subset per diagram is tens of kilobytes of a file somebody forwards by hand.
    """
    svg = DOCTYPE_RE.sub("", XML_DECL_RE.sub("", svg)).strip()
    svg = HTML_COMMENT_RE.sub("", svg)
    svg = FONT_FACE_RE.sub("", svg)
    svg = FONT_FAMILY_RULE_RE.sub("", svg)
    svg = namespace_svg_ids(svg, uid)
    # The engine's own width/height would pin the drawing at its natural pixel size; the viewBox
    # plus the figure's CSS is what lets it fit the reading column and scale on a phone.
    opening = SVG_OPEN_RE.search(svg)
    if opening:
        attrs = SVG_SIZE_ATTR_RE.sub("", opening.group(1))
        svg = svg[: opening.start()] + f'<svg{attrs} class="dgm-svg">' + svg[opening.end() :]
    return f'<div class="dgm-art" id="{uid}" data-engine="{engine}">{svg}</div>'


DIAGRAM_CSS = """
  .dgm{margin:22px 0; padding:0}
  .dgm-art{background:var(--panel-2); border:1px solid var(--line); border-radius:var(--radius);
    padding:18px 14px; overflow-x:auto}
  .dgm-art svg{display:block; margin:0 auto; max-width:100%; height:auto}
  .dgm figcaption{margin-top:10px; color:var(--muted); font:400 .86rem/1.5 var(--font-body)}
  .dgm-art text{font-family:var(--font-body); fill:var(--ink)}
  /* graphviz: class-tagged groups, palette in presentation attributes that CSS outranks */
  /* the graph's ground polygon, for a hand-written DOT that did not set bgcolor */
  .dgm-art[data-engine="graphviz"] .graph > polygon{fill:none; stroke:none}
  .dgm-art[data-engine="graphviz"] .node polygon,
  .dgm-art[data-engine="graphviz"] .node ellipse,
  .dgm-art[data-engine="graphviz"] .node path{fill:var(--acc-soft); stroke:var(--acc)}
  .dgm-art[data-engine="graphviz"] .node text{fill:var(--acc-ink)}
  .dgm-art[data-engine="graphviz"] .edge path{stroke:var(--muted); fill:none}
  .dgm-art[data-engine="graphviz"] .edge polygon{fill:var(--muted); stroke:var(--muted)}
  .dgm-art[data-engine="graphviz"] .edge text{fill:var(--muted)}
  .dgm-art[data-engine="graphviz"] .cluster polygon{fill:var(--panel); stroke:var(--line)}
  /* d2: theme-slot classes. B* is the accent family, N* the neutrals. */
  .dgm-art[data-engine="d2"] .fill-N7,
  .dgm-art[data-engine="d2"] .fill-N6{fill:transparent}
  .dgm-art[data-engine="d2"] .fill-B6,
  .dgm-art[data-engine="d2"] .fill-B5,
  .dgm-art[data-engine="d2"] .fill-B4{fill:var(--acc-soft)}
  .dgm-art[data-engine="d2"] .stroke-B1,
  .dgm-art[data-engine="d2"] .stroke-B2{stroke:var(--acc)}
  .dgm-art[data-engine="d2"] .fill-B1,
  .dgm-art[data-engine="d2"] .fill-B2{fill:var(--acc)}
  .dgm-art[data-engine="d2"] .fill-N1{fill:var(--ink)}
  .dgm-art[data-engine="d2"] .fill-N2,
  .dgm-art[data-engine="d2"] .fill-N3{fill:var(--muted)}
  .dgm-art[data-engine="d2"] .stroke-N1,
  .dgm-art[data-engine="d2"] .stroke-N2,
  .dgm-art[data-engine="d2"] .stroke-N3{stroke:var(--muted)}
  /* A connection label sits ON the line it labels, and d2 punches a hole in that line with a
     mask sized to ITS font. We ship the house font, which measures wider, so the ends of a
     long label stuck out past the hole and the arrow ran through the words. A halo in the
     art's own background hides the line whatever the font measures, with no geometry at all.
     Only `text-italic` is haloed: that is d2's class for a connection label, and a box label
     sits on a filled shape where a halo would show as a ring. */
  .dgm-art[data-engine="d2"] text.text-italic{paint-order:stroke; stroke:var(--panel-2);
    stroke-width:6px; stroke-linejoin:round; stroke-linecap:round}
  @media (max-width:760px){.dgm-art{padding:12px 8px}}
"""


def diagram_blocks(rendered: str, prefix: str = "") -> tuple[str, bool]:
    """Replace every `[diagram: <kind>]` hint plus its fenced block with pre-rendered inline SVG.

    Written as a pass over the RENDERED html for the same reason `upgrade_tables` is: the author
    writes ordinary markdown, and the fence the renderer produced is the one place the engine
    source survives intact.
    """
    used = False
    counter = itertools.count(1)

    def one(match: re.Match[str]) -> str:
        nonlocal used
        kind = match.group(1).lower()
        caption = (match.group(2) or "").strip()
        if kind not in DIAGRAM_KINDS:
            known = ", ".join(sorted(DIAGRAM_KINDS))
            raise SystemExit(f"[diagram: {kind}] is not a kind this builder draws. Known kinds: {known}")
        source = html.unescape(match.group(3))
        uid = f"{prefix}dgm{next(counter)}"
        art = restyle_svg(run_engine(kind, source, uid), DIAGRAM_KINDS[kind]["engine"], uid)
        used = True
        label = f"\n    <figcaption>{esc(caption)}</figcaption>" if caption else ""
        aria = esc_attr(caption or f"{kind} diagram")
        return f'<figure class="dgm" role="img" aria-label="{aria}">\n    {art}{label}\n  </figure>'

    return DIAGRAM_HINT_RE.sub(one, rendered), used


# --------------------------------------------------------------------------- tabular


def load_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = [{"key": k, "value": v} for k, v in data.items()]
        if not isinstance(data, list) or not data:
            raise SystemExit("build.py: the JSON file must hold a non-empty list of objects or an object")
        headers = list(dict.fromkeys(key for row in data for key in row))
        rows = [[("" if row.get(h) is None else str(row.get(h))) for h in headers] for row in data]
        return headers, rows

    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    table = [row for row in reader if any(cell.strip() for cell in row)]
    if not table:
        raise SystemExit("build.py: the data file is empty")
    return table[0], table[1:]


YEAR_RE = re.compile(r"^(19|20)\d{2}$")
IDENTIFIER_HINTS = ("year", "id", "no.", "number", "code", "rank", "zip", "postcode", "sku", "#", "quarter", "week")
RATE_HINTS = ("rate", "percent", "%", "share", "margin", "ratio", "average", "avg", "score", "index")


def numeric_columns(headers: list[str], rows: list[list[str]]) -> list[int]:
    out = []
    for index in range(len(headers)):
        values = [row[index] for row in rows if index < len(row) and str(row[index]).strip()]
        if values and all(is_number(v) for v in values):
            out.append(index)
    return out


def column_kind(header: str, values: list[str]) -> str:
    """sum, rate or identifier. Summing a year column is the wrong number in the biggest type."""
    name = header.strip().lower()
    if "%" in name or any(hint in name for hint in RATE_HINTS) or any("%" in str(v) for v in values):
        return "rate"
    if any(name == hint or name.startswith(hint) or name.endswith(hint) for hint in IDENTIFIER_HINTS):
        return "identifier"
    cleaned = [str(v).strip() for v in values if str(v).strip()]
    if cleaned and all(YEAR_RE.match(v) for v in cleaned):
        return "identifier"
    return "sum"


def column_values(rows: list[list[str]], index: int) -> list[float]:
    return [to_number(row[index]) for row in rows if index < len(row) and is_number(row[index])]


def classify(headers: list[str], rows: list[list[str]], numeric: list[int]) -> dict[int, str]:
    return {
        index: column_kind(headers[index], [row[index] for row in rows if index < len(row)])
        for index in numeric
    }


def kpi_cards(headers: list[str], rows: list[list[str]], numeric: list[int], kinds: dict[int, str]) -> str:
    cards = [f'    <div class="kpi n"><div class="n">{len(rows):,}</div><div class="l">rows in the source</div></div>']
    for index in numeric:
        kind = kinds.get(index, "sum")
        if kind == "identifier":
            continue  # a year or an id has no meaningful total, and a wrong total is worse than none
        values = column_values(rows, index)
        if not values:
            continue
        last, previous = values[-1], (values[-2] if len(values) > 1 else None)
        delta = ""
        if previous not in (None, 0):
            change = (last - previous) / abs(previous) * 100
            direction = "up" if change >= 0 else "down"
            delta = f'<div class="d {direction}">{change:+.1f}% on the previous row</div>'
        if kind == "rate":
            figure, caption = fmt_number(last), f"{esc(headers[index])}, the latest of {len(values):,} rows"
        else:
            figure, caption = fmt_number(sum(values)), f"{esc(headers[index])}, summed over {len(values):,} rows"
        cards.append(f'    <div class="kpi g"><div class="n">{figure}</div><div class="l">{caption}</div>{delta}</div>')
        if len(cards) == 4:
            break
    return "\n".join(cards)


def svg_bars(pairs: list[tuple[str, float]], unit: str) -> str:
    """A dependency-free bar chart. Every bar carries data-label and data-value for the tooltip.

    Takes PAIRS, not two lists: a blank cell in the charted column used to shift every later label
    by one, so a bar read March's number under February's name.
    """
    if not pairs:
        return ""
    labels = [label for label, _ in pairs]
    values = [value for _, value in pairs]
    width, height = 900, 260
    pad_left, pad_bottom, pad_top = 46, 34, 10
    top = max(values + [0])
    bottom = min(values + [0])
    span = (top - bottom) or 1
    plot_h = height - pad_bottom - pad_top
    slot = (width - pad_left) / len(values)
    bar_w = max(2.0, slot * 0.62)
    parts = [f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" aria-label="{esc_attr(unit)}">']
    # whole-number data gets whole-number axis labels: a count axis reading 132.75 is labelling a
    # value the column cannot hold. Caught by looking at the render.
    whole = all(abs(v - round(v)) < 1e-9 for v in values)
    for tick in range(5):
        y = pad_top + plot_h * tick / 4
        value = top - span * tick / 4
        if whole:
            value = float(round(value))
        parts.append(f'<line class="gridline" x1="{pad_left}" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" />')
        parts.append(f'<text class="axlabel" x="0" y="{y + 4:.1f}">{esc(fmt_number(value))}</text>')
    zero_y = pad_top + plot_h * (top / span if span else 0)
    for index, value in enumerate(values):
        x = pad_left + slot * index + (slot - bar_w) / 2
        y = pad_top + plot_h * ((top - max(value, 0)) / span)
        bar_h = max(1.0, abs(value) / span * plot_h)
        label = labels[index] if index < len(labels) else str(index + 1)
        parts.append(
            f'<rect class="bar" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="2" '
            f'data-label="{esc_attr(label)}" data-value="{esc_attr(fmt_number(value) + " " + unit)}" />'
        )
    parts.append(f'<line class="axis" x1="{pad_left}" y1="{zero_y:.1f}" x2="{width}" y2="{zero_y:.1f}" />')
    # category labels under the bars, while they still fit: a chart nobody can read the axis of
    # is a picture, not a chart. Above 14 bars the tooltip carries the label instead.
    if len(values) <= 14:
        for index, label in enumerate(labels):
            if not label:
                continue
            x = pad_left + slot * index + slot / 2
            text = label if len(label) <= 12 else label[:11] + "…"
            parts.append(
                f'<text class="axlabel" x="{x:.1f}" y="{height - 8}" text-anchor="middle">{esc(text)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def data_table(headers: list[str], rows: list[list[str]], numeric: list[int], limit: int) -> str:
    # Every column is sortable and the whole table filters: any table or list of data ships with
    # both. The controls are hidden in print.
    head = "".join(
        f'<th data-sort="{"num" if index in numeric else "text"}"'
        f'{" class=\"num\"" if index in numeric else ""}>{esc(h)}</th>'
        for index, h in enumerate(headers)
    )
    body_rows = []
    for row in rows[:limit]:
        cells = []
        for index, header in enumerate(headers):
            value = row[index] if index < len(row) else ""
            css = ' class="num"' if index in numeric else ""
            cells.append(f"<td{css}>{esc(value)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    note = ""
    if len(rows) > limit:
        note = f'<p class="sub">Showing the first {limit:,} of {len(rows):,} rows. The source file holds them all.</p>'
    return (
        f'  <section id="table">\n    <div class="sec-num">The data</div>\n'
        f"    <h2>Every row behind the numbers above</h2>\n{note}\n"
        f'    <div class="dt-wrap">\n'
        f'      <div class="dt-controls">\n'
        f'        <input type="search" class="dt-filter" placeholder="Filter these rows" aria-label="Filter the table">\n'
        f'        <span class="dt-count"></span>\n'
        f"      </div>\n"
        f'      <div class="scroll"><table class="dt data"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>\n'
        f"    </div>\n  </section>\n"
    )


# --------------------------------------------------------------------------- assembly


def links_section(links: list[tuple[str, str]]) -> str:
    if len(links) < 2:
        return ""
    rows = "".join(
        f'<tr><td>{esc(label)}</td><td><a href="{esc_attr(url)}" target="_blank" '
        f'rel="{NEW_TAB_REL}">{esc(url)}</a></td></tr>'
        for label, url in links
    )
    return (
        '  <section id="links">\n    <div class="sec-num">Key links</div>\n'
        "    <h2>Every destination named in this document</h2>\n"
        '    <div class="scroll"><table><thead><tr><th>What it is</th><th>Link</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>\n  </section>\n"
    )


def host_label(url: str) -> str:
    """The host, plus enough of the path to tell one destination from another on the same host.

    The old fallback was the host ALONE, so three links to `docs.example.com` arrived in the Key
    links table as `docs.example.com` three times over and the table told the reader nothing. A
    label is what the reader scans, and a label that is the same on every row is a blank column.

    `--link "What it is=<url>"` still overrides this per URL and is still the better answer,
    because a real name beats any derivation. This is the fallback getting less useless.
    """
    rest = url.split("//", 1)[-1]
    host, _, path = rest.partition("/")
    host = host.split("@")[-1]
    parts = [p for p in path.split("?")[0].split("#")[0].split("/") if p]
    if not parts:
        return host
    tail = parts[-1]
    # A trailing file name reads better without its extension. A version-looking tail (1.2.3) is
    # left alone, because dropping its last segment would change what it says.
    if "." in tail and not tail.replace(".", "").isdigit():
        tail = tail.rsplit(".", 1)[0]
    tail = tail.replace("-", " ").replace("_", " ").strip()
    if len(tail) > 40:
        tail = tail[:37].rstrip() + "..."
    return f"{host}/{tail}" if tail else host


def harvest_links(content_html: str, given: list[str]) -> list[tuple[str, str]]:
    """The Key links table: the labels given by hand first, then one row per harvested URL.

    Two rules, both learned the same day. A harvested label carries the host AND the path tail,
    so destinations on one host are told apart. And when two harvested rows still land on the same
    label, both fall back to the full address, because two identical labels on one table is the
    exact defect this function exists to prevent, and a wrong-looking long row is better than a
    row the reader cannot distinguish from the one above it.

    A label passed with `--link` is never rewritten. The author said what it is.
    """
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    told: set[str] = set()
    for item in given:
        label, _, url = item.partition("=")
        url = url.strip()
        if url and url not in seen:
            seen.add(url)
            told.add(url)
            links.append((label.strip(), url))
    for url in HREF_RE.findall(content_html):
        if url not in seen:
            seen.add(url)
            links.append((host_label(url), url))

    # Dedupe on the FINAL labels, and keep going until nothing collides: a scheme-stripped
    # fallback still collides for http and https twins of one address, and a told label can equal
    # another row's fallback. A told label is never rewritten; the harvested rows around it are.
    for _ in range(3):
        counts: dict[str, int] = {}
        for label, _ in links:
            counts[label] = counts.get(label, 0) + 1
        if all(c == 1 for c in counts.values()):
            break
        out: list[tuple[str, str]] = []
        for label, url in links:
            if url in told or counts[label] == 1:
                out.append((label, url))
            elif label != url.split("//", 1)[-1]:
                out.append((url.split("//", 1)[-1] or label, url))
            else:
                out.append((url, url))          # the full address, scheme and all
        links = out
    return links


def resolve_look(look: str, surface: str) -> str:
    """auto resolves by SURFACE, which is how DESIGN.md states the rule.

    The tint look is for agendas, call documents and client one-pagers, so the deck and the
    poster take it; the classic look is for formal reports, so the report and the data-report
    take that. An explicit `--look` always wins, and an author who knows the reader states it.
    """
    if look in {"tint", "classic"}:
        return look
    return "tint" if surface in {"deck", "poster"} else "classic"


def resolve_audience(audience: str) -> str:
    """Who reads this page. EXTERNAL unless the author says otherwise.

    The builder defaults the opposite way from the lint on purpose. The lint runs over every page
    that has ever been written, including your own internal records, which name your own company
    because that is their subject. The builder is making a NEW page, and a new page is presumed to
    be for somebody else until the author says `--audience internal`.
    """
    return audience if audience in {"internal", "external"} else "external"


# --------------------------------------------------------------------------- strip for delivery
#
# What a reader never needs does not ship. Two things go: the comments, and the maker's-mark
# rules on a page that renders no mark. The reason is the same for both: a client one-pager built
# from a house template and sent unchanged once carried another client's short name in a CSS
# selector and a third company's name in a comment, invisible on the page and one Ctrl-F away
# from the reader.

STYLE_BLOCK_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)
SCRIPT_OR_STYLE_RE = re.compile(r"(<(script|style)\b[^>]*>.*?</\2>)", re.S | re.I)
HTML_COMMENT_LINE_RE = re.compile(r"^[ \t]*<!--.*?-->[ \t]*\r?\n", re.S | re.M)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HOLE = "\x00"


def strip_css_comments(css: str) -> str:
    """Remove CSS comments without reading inside a CSS STRING.

    `content:"literal /* not a comment */ text"` is content, and a regex that does not know about
    quoting silently edits what the page renders. So this walks the
    sheet, skips over anything quoted, and marks each real comment with a hole. A line that is
    nothing but a hole goes with the hole, which is what keeps the page from filling with blanks.
    """
    out: list[str] = []
    index, end = 0, len(css)
    while index < end:
        char = css[index]
        if char in "\"'":
            close = index + 1
            while close < end:
                if css[close] == "\\":
                    close += 2
                    continue
                if css[close] == char:
                    close += 1
                    break
                close += 1
            out.append(css[index:close])
            index = close
            continue
        if css.startswith("/*", index):
            stop = css.find("*/", index + 2)
            out.append(HOLE)
            index = end if stop == -1 else stop + 2
            continue
        out.append(char)
        index += 1

    kept = []
    for line in "".join(out).splitlines(keepends=True):
        if HOLE in line and not line.replace(HOLE, "").strip():
            continue  # the comment was the whole line
        kept.append(line.replace(HOLE, ""))
    # an inline comment at the end of a declaration leaves its indentation behind
    return re.sub(r"[ \t]+(\r?\n)", r"\1", "".join(kept))


def strip_comments(page: str) -> str:
    """Every CSS comment and every HTML comment, and nothing else.

    A comment that sits alone on its line takes the line with it, so the page does not fill with
    blank lines. CSS comments are only hunted INSIDE <style>, and HTML comments only OUTSIDE
    <script> and <style>, so a `/*` in a script string or a `<!--` in page content is untouched.
    Whitespace inside <pre> is never rewritten, because there a blank line is content.
    """

    def de_css(match: re.Match[str]) -> str:
        return match.group(1) + strip_css_comments(match.group(2)) + match.group(3)

    page = STYLE_BLOCK_RE.sub(de_css, page)

    # re.split on a pattern with two groups hands back a repeating triple: the text between the
    # blocks, the whole block, and the TAG NAME the backreference needed. The name is not part of
    # the document and joining it back in writes "</style>style" into the page. Drop it.
    parts = SCRIPT_OR_STYLE_RE.split(page)
    out: list[str] = []
    for index, part in enumerate(parts):
        if index % 3 == 2:
            continue
        if index % 3 == 0:
            part = HTML_COMMENT_RE.sub("", HTML_COMMENT_LINE_RE.sub("", part))
        out.append(part)
    return "".join(out)


def drop_css_rule(page: str, selector: str) -> str:
    """Remove one `selector{...}` rule, and ONLY when that selector is the whole list.

    `.mark, .lockup{display:flex}` is left alone: dropping one name out of a list by regex leaves
    `.mark,` behind, which is broken CSS. A rule that survives because it shares a list is
    harmless, since nothing on the page wears the class.
    """

    # The selector must OPEN its rule: what sits between the previous brace (or the line start)
    # and the selector can only be whitespace. `.mark, .lockup{...}` therefore matches neither
    # name, which is the point.
    pattern = re.compile(
        rf"(?P<lead>^|[{{}}])[ \t\r\n]*{re.escape(selector)}(?![\w-])[ \t]*\{{[^}}]*\}}", re.M
    )

    def drop(css: str) -> str:
        return pattern.sub(lambda m: m.group("lead"), css)

    if not STYLE_BLOCK_RE.search(page):
        return drop(page)
    return STYLE_BLOCK_RE.sub(lambda m: m.group(1) + drop(m.group(2)) + m.group(3), page)


def new_tab_links(page: str) -> str:
    """Give every external `<a>` `target="_blank"` and `rel="noopener noreferrer"`.

    This runs on the FINISHED page rather than on the markdown, because a destination reaches a
    deliverable three ways and only the last one sees all three: the markdown renderer's own
    `<a>`, a block of raw HTML the author pasted into the source, and the Key links table the
    builder generates. An in-page anchor (`#section`) and a relative path are left alone - they
    do not leave the document, so a new tab for them is just a duplicate of the page.

    An anchor that already declares a rel keeps its own tokens; the two are added beside them.
    """

    def fix(match: re.Match[str]) -> str:
        attrs = match.group(1)
        href = HREF_ATTR_RE.search(attrs)
        if not href or not EXTERNAL_HREF_RE.match(href.group(1)):
            return match.group(0)
        rel = REL_ATTR_RE.search(attrs)
        tokens = rel.group(1).split() if rel else []
        tokens += [token for token in ("noopener", "noreferrer") if token not in tokens]
        if rel:
            attrs = attrs[: rel.start(1)] + " ".join(tokens) + attrs[rel.end(1) :]
        else:
            attrs = f'{attrs.rstrip()} rel="{" ".join(tokens)}"'
        # re-searched on the REWRITTEN attribute string: the rel edit above moved every offset
        # after it, so a target match taken before the edit would splice at the wrong place.
        target = TARGET_ATTR_RE.search(attrs)
        if not target:
            attrs = f'{attrs.rstrip()} target="_blank"'
        elif target.group(1).strip() != "_blank":
            attrs = attrs[: target.start(1)] + "_blank" + attrs[target.end(1) :]
        return f"<a{attrs}>"

    return A_TAG_RE.sub(fix, page)


def strip_for_delivery(page: str) -> str:
    page = new_tab_links(page)
    page = strip_comments(page)
    if 'class="mark"' not in page:
        page = drop_css_rule(page, ".mark")
    if 'class="lockup"' not in page:
        page = drop_css_rule(page, ".lockup")
    return page


def wall_notice(page: str, allow: list[str], audience: str) -> list[str]:
    """Say at BUILD time that a wall-list name went into the page, while the author is still here.

    `lint.py` owns the wall list and owns the refusal; this is only the early word, because the
    name usually comes in from the markdown source, which is the one place the builder can see
    and the author cannot.
    """
    try:
        from lint import wall_hits  # the wall list has ONE home, and it is lint.py
    except ImportError:  # pragma: no cover - only if the lint is missing from the skill folder
        return []
    try:
        hits = wall_hits(page, allow)
    except FileNotFoundError:
        return ["  ! the wall list could not be read here, so run lint.py before this page goes out"]
    if not hits:
        return []
    verdict = "the lint will REFUSE this page" if audience == "external" else "the lint will warn"
    shown = "; ".join(f"{name} at line {line}" for name, line, _ in hits[:5])
    more = f" and {len(hits) - 5} more" if len(hits) > 5 else ""
    return [f"  ! {len(hits)} wall-list name(s) in the page: {shown}{more}. On audience {audience}, {verdict}"]


def compose(
    surface: str,
    fields: dict[str, str],
    nav: str,
    keep: set[str],
    look: str = "classic",
    extra_css: str = "",
    extra_js: str = "",
    audience: str = "internal",
    kind: str = "",
) -> str:
    base = read_text(BASE)
    module = read_text(SURFACES / f"{surface}.html")

    surface_css = block(module, "SURFACE:CSS")
    surface_body = block(module, "SURFACE:BODY")

    for name in re.findall(r"<!--\s*OPTIONAL:([A-Z]+)\s*-->", surface_body):
        if name not in keep:
            surface_body = drop_block(surface_body, f"OPTIONAL:{name}")

    for key, value in fields.items():
        surface_body = surface_body.replace("{{" + key + "}}", value)
    surface_body = PLACEHOLDER_RE.sub("", surface_body)
    # An eyebrow nobody filled is removed, not shipped as an empty line of reserved space, and
    # so is a cover-meta entry (Prepared for, From, By) that nobody filled.
    surface_body = re.sub(r'\s*<div class="eyebrow">\s*</div>\n?', "\n", surface_body)
    surface_body = re.sub(r'[ \t]*<span><b>(?:Prepared for|From|By)</b>\s*</span>\n?', "", surface_body)

    css = f"  /* ---- surface: {surface} ---- */\n{surface_css}"
    if extra_css:
        css += f"\n  /* ---- components used by this page ---- */\n{extra_css}"
    page = base.replace(
        "  /* BUILD:CSS - build.py appends the chosen surface's extra CSS here. Leave the marker in place. */",
        css,
    )
    page = replace_block(page, "BUILD:NAV", "\n" + nav + "\n  ")
    page = replace_block(page, "BUILD:BODY", "\n" + surface_body + "\n  ")
    # THE TAB TITLE IS THE DOCUMENT'S OWN TITLE, EXACTLY: no prefix or suffix, no kind label, the
    # same string the page's <h1> shows, because the tab is what a reader hovers in a window of
    # many tabs. The description meta is the lede, so a link preview and a search result read
    # the page's own first sentence. lint.py refuses a generic title and a title that differs
    # from the h1.
    page = page.replace("<title>REPLACE - Document Title</title>", f"<title>{esc(fields.get('TITLE', 'Document'))}</title>")
    # The LEDE field is already text-escaped, so unescape first, then drop any markup the author
    # typed, then attribute-escape once for the meta.
    lede_text = " ".join(re.sub(r"<[^>]+>", "", html.unescape(fields.get("LEDE", ""))).split())
    if lede_text:
        page = page.replace(
            "<meta name=\"viewport\"",
            f"<meta name=\"description\" content=\"{esc_attr(lede_text[:300])}\">\n<meta name=\"viewport\"",
            1,
        )
    # What KIND of document this is, said by the builder rather than guessed later from the file
    # name by whatever indexes the page. The builder is the one place that actually knows. Emitted
    # only when it was given: an empty tag would look like an answer. The tag is named
    # `document-kind`, never after a product: a product name is the kind of thing a wall list
    # carries, and every byte of this page ships to the reader.
    if kind:
        page = page.replace(
            '<meta name="viewport"',
            f'<meta name="document-kind" content="{esc_attr(kind)}">\n<meta name="viewport"',
            1,
        )
    page = page.replace('data-look="classic"', f'data-audience="{audience}" data-look="{look}"', 1)
    if extra_js:
        page = page.replace("</body>", f"<script>\n{extra_js}\n</script>\n</body>")
    return strip_for_delivery(page)


def clip(label: str, limit: int = 22) -> str:
    """Nav labels cut on a word boundary. A label sliced mid-word reads as a broken page."""
    if len(label) <= limit:
        return label
    cut = label[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:") + "…"


NavTree = tuple[
    list[dict[str, str]], list[tuple[dict[str, str], list[dict[str, str]]]], list[dict[str, str]]
]


def nav_tree(
    entries: list[dict[str, str]], threshold: int = NAV_GROUP_THRESHOLD, group_size: int = AUTO_GROUP_SIZE
) -> NavTree:
    """Return (loose, groups, trailing): what sits above the parts, the parts, and what sits below.

    Three cases, in order:
    1. The author declared parts. The parts ARE the top level, and nothing is invented.
    2. No parts and more than `threshold` entries. The sections are chunked mechanically and each
       chunk is labeled by the range it covers. The label states a fact about position and
       nothing else, because a group name nobody wrote is a name nobody can trust.
    3. No parts and a short document. It stays flat, which is what a short document wants.

    An entry marked `kind: "top"` (the Key links table) always stays at the top level, whichever
    case applies, so it can never be folded into somebody else's part.
    """
    trailing = [e for e in entries if e.get("kind") == "top"]
    body = [e for e in entries if e.get("kind") != "top"]
    groups: list[tuple[dict[str, str], list[dict[str, str]]]] = []

    if any(e.get("kind") == "part" for e in body):
        loose = list(itertools.takewhile(lambda e: e.get("kind") != "part", body))
        for entry in body[len(loose) :]:
            if entry.get("kind") == "part":
                groups.append((entry, []))
            else:
                groups[-1][1].append(entry)
        return loose, groups, trailing

    if len(body) + len(trailing) <= threshold:
        return body, [], trailing

    loose = [e for e in body if e.get("lead")]
    rest = [e for e in body if not e.get("lead")]
    for start in range(0, len(rest), group_size):
        chunk = rest[start : start + group_size]
        first, last = start + 1, start + len(chunk)
        label = f"Sections {first} to {last}" if len(chunk) > 1 else f"Section {first}"
        groups.append(({"kind": "part", "id": chunk[0]["id"], "label": label, "num": ""}, chunk))
    return loose, groups, trailing


def nav_buttons(entries: list[dict[str, str]]) -> str:
    """The right-side rail. One level when the document is small, two when it is not.

    Only the ACTIVE part's sections are shown; the template's script opens and closes the groups.
    A rail that lists forty sections at once is taller than the screen, which is a page the
    reader has to zoom out to 50 percent to read.
    """
    loose, groups, trailing = nav_tree(entries)
    lines = [f'  <button data-target="{e["id"]}">{esc(clip(e["label"]))}</button>' for e in loose]
    for part, children in groups:
        lines.append(f'  <div class="nav-group" data-part="{part["id"]}">')
        number = f'<b>{esc(part["num"])}</b>' if part.get("num") else ""
        lines.append(
            f'    <button class="nav-part" data-target="{part["id"]}">{number}{esc(clip(part["label"], 26))}</button>'
        )
        if children:
            lines.append('    <div class="nav-kids">')
            lines += [
                f'      <button data-target="{c["id"]}">{esc(clip(c["label"]))}</button>' for c in children
            ]
            lines.append("    </div>")
        lines.append("  </div>")
    lines += [f'  <button data-target="{e["id"]}">{esc(clip(e["label"]))}</button>' for e in trailing]
    return "\n".join(lines)


def chip_links(entries: list[dict[str, str]], indent: str = "      ") -> str:
    return "\n".join(
        f'{indent}<a href="#{e["id"]}">' + (f'<b>{esc(e["num"])}</b>' if e.get("num") else "") + f'{esc(e["label"])}</a>'
        for e in entries
    )


def toc_section(entries: list[dict[str, str]]) -> str:
    """The contents block, grouped exactly the way the rail is grouped.

    A flat list of forty chips is the same wall of labels in another shape, so it follows the
    same tree: each part is a row with its sections indented under it.
    """
    if len(entries) < 3:
        return ""
    loose, groups, trailing = nav_tree(entries)
    body = []
    if loose or (trailing and not groups):
        body.append(f'    <div class="toc">\n{chip_links(loose + (trailing if not groups else []))}\n    </div>')
    for part, children in groups:
        number = f'<b>{esc(part["num"])}</b>' if part.get("num") else ""
        body.append(
            f'    <div class="toc-part">\n'
            f'      <a class="toc-part-name" href="#{part["id"]}">{number}{esc(part["label"])}</a>\n'
            + (f'      <div class="toc toc-kids">\n{chip_links(children, "        ")}\n      </div>\n' if children else "")
            + "    </div>"
        )
    if trailing and groups:
        body.append(f'    <div class="toc">\n{chip_links(trailing)}\n    </div>')
    return (
        '  <section id="toc">\n    <div class="sec-num">Contents</div>\n'
        + "\n".join(body)
        + "\n  </section>\n"
    )


def agenda_chips(sections: list[dict[str, str]]) -> str:
    return chip_links(sections)


def verdict_box(text: str) -> str:
    if not text:
        return ""
    return f'  <div class="verdict"><strong>The short answer:</strong> {esc(text)}</div>\n'


CHIP_BY_STATUS = {"open": "a", "doing": "n", "done": "g", "blocked": "r"}


def split_fields(value: str, count: int) -> list[str]:
    """Split a CLI value on | and pad to count. Missing fields stay empty rather than guessed."""
    parts = [p.strip() for p in value.split("|")]
    return (parts + [""] * count)[:count]


def action_rows(actions: list[str]) -> str:
    rows = []
    for action in actions:
        task, owner, by, status = split_fields(action, 4)
        chip = CHIP_BY_STATUS.get(status.lower(), "n")
        rows.append(
            f'        <tr><td>{esc(task)}</td><td class="who">{esc(owner)}</td>'
            f'<td class="due">{esc(by)}</td>'
            f'<td><span class="chip {chip}">{esc((status or "open").upper())}</span></td></tr>'
        )
    return "\n".join(rows)


def stat_cards(stats: list[str], css_class: str) -> str:
    cards = []
    for stat in stats:
        number, label = split_fields(stat, 2)
        cards.append(
            f'    <div class="{css_class}"><div class="n">{esc(number)}</div>'
            f'<div class="l">{esc(label)}</div></div>'
        )
    return "\n".join(cards)


def hero_stat_cards(stats: list[str]) -> str:
    """The report surface's stat row: .hero-stats > .stat with a tone class per card.

    Tone rides on the stat as a fourth field, because color is FOCUS and not decoration
    (DESIGN.md section 3): g for money and act-now, r for risk, a for caution, n for context.
    A stat with no tone given is context, which is the safe default.

    An UNKNOWN tone is refused rather than rendered neutral. The field takes single letters, and
    writing the word ("green", "red") used to produce a context-colored card in silence: the
    author read their own intent back off the page and never learned it had been dropped. A wrong
    spelling now says what the four letters are.
    """
    tones = {"g", "a", "r", "n"}
    cards = []
    for stat in stats:
        number, label, tone = split_fields(stat, 3)
        if tone and tone not in tones:
            raise SystemExit(
                f"the stat `{number} | {label}` asks for tone `{tone}`, which is not a tone. "
                "The field takes one letter: g for money and act-now, a for caution, r for "
                "risk, n for context. Leave it empty for context."
            )
        cls = tone if tone in tones else "n"
        cards.append(
            f'    <div class="stat {cls}"><div class="num">{esc(number)}</div>'
            f'<div class="lbl">{esc(label)}</div></div>'
        )
    return "\n".join(cards)


def side_list(items: list[str], heading: str) -> str:
    lines = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f'      <div class="side"><h3>{esc(heading)}</h3><ul>{lines}</ul></div>'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a house-style HTML page from markdown, CSV or JSON.")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--surface", default="report", choices=["report", "deck", "poster", "data-report"])
    parser.add_argument(
        "--look", default="auto", choices=["auto", "tint", "classic"],
        help="tint (cool ground plus graph paper, 1080px) or classic (gold, 1000px). auto picks by "
             "surface: tint for deck and poster, classic for report and data-report.",
    )
    parser.add_argument(
        "--audience", default="auto", choices=["auto", "internal", "external"],
        help="who reads it. external (the default) makes a wall-list name in the page a lint "
             "FAILURE rather than a warning; internal makes it a warning.",
    )
    parser.add_argument(
        "--allow", action="append", default=[], metavar="NAME",
        help="a company this page is entitled to name, passed straight to the wall check.",
    )
    parser.add_argument(
        "--mark", default="", metavar="TEXT",
        help="poster: the maker's mark under the last block, for example the name of the company "
             "that built it. OFF unless given; no template carries a default.",
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--eyebrow", default="")
    parser.add_argument("--lede", default="")
    parser.add_argument("--for", dest="prepared_for", default="",
                        help="who the page is prepared for. Omitted means the line is not shown.")
    parser.add_argument("--from", dest="prepared_from", default="",
                        help="who prepared it. Omitted means the line is not shown.")
    parser.add_argument("--date", default=date.today().strftime("%B %d, %Y"))
    parser.add_argument(
        "--kind", default="",
        help="what kind of document this is (one of: " + ", ".join(KINDS) + "). Emitted as "
             "<meta name=\"document-kind\">, so a document library that indexes the page stops "
             "guessing it from the file name. Omitted means no tag rather than an empty one; an "
             "unknown kind is refused here rather than thrown away there.",
    )
    parser.add_argument("--verdict", default="")
    parser.add_argument("--foot", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--method", default="")
    parser.add_argument("--link", action="append", default=[], metavar="LABEL=URL")
    parser.add_argument(
        "--numbered", action="store_true",
        help="number the sections. This is already the default; the flag is kept so existing build lines run.",
    )
    parser.add_argument(
        "--unnumbered", action="store_true",
        help="do NOT number the sections. Each heading still renders as a real heading, never a bare eyebrow line.",
    )
    parser.add_argument(
        "--action", action="append", default=[], metavar="TASK|OWNER|BY|STATUS",
        help="deck: one row of the action table, repeatable. STATUS is one of open, doing, done, blocked.",
    )
    parser.add_argument(
        "--stat", action="append", default=[], metavar="NUMBER|LABEL|TONE",
        help="one big number, repeatable. On the report surface it builds the stat row above the "
             "contents and the links table; three or four read best. TONE is g, a, r or n and "
             "defaults to n.",
    )
    parser.add_argument("--cta", default="", metavar="HEADLINE|LINE", help="poster: the one next step")
    parser.add_argument("--today", action="append", default=[], help="poster: one 'Today' line, repeatable")
    parser.add_argument("--after", action="append", default=[], help="poster: one 'After' line, repeatable")
    parser.add_argument("--chart-col", default="", help="data-report: the column to chart (default: the first numeric one)")
    parser.add_argument("--label-col", default="", help="data-report: the column for the x labels")
    parser.add_argument("--row-limit", type=int, default=400)
    args = parser.parse_args(argv)

    source = Path(args.input)
    if not source.is_file():
        print(f"build.py: no such input file: {source}", file=sys.stderr)
        return 2
    destination = Path(args.output)
    # A library that indexes pages ignores a kind it does not know, silently. Refuse it here,
    # where the typo is one line away from the person who typed it. Inner whitespace and case
    # are folded, and the tag is emitted in that folded form.
    args.kind = " ".join(args.kind.split()).lower()
    if args.kind and args.kind not in KINDS:
        print(f"build.py: --kind {args.kind!r} is not a kind this builder knows. "
              f"One of: {', '.join(KINDS)}", file=sys.stderr)
        return 2

    keep: set[str] = set()
    if args.action:
        keep.add("ACTIONS")
    if args.stat and args.surface in ("poster", "report"):
        # The report surface puts its numbers ABOVE the contents and the links table, because the
        # executive summary is what a reader sees without scrolling. A thirteen-row links table
        # between the verdict and the numbers pushes the summary off the first screen, which is
        # the defect this slot fixes.
        keep.add("BIGNUMS")
    if args.today or args.after:
        keep.add("SHAPE")
    if args.cta:
        keep.add("CTA")
    if args.mark:
        keep.add("MARK")
    cta_head, cta_line = split_fields(args.cta, 2) if args.cta else ("", "")

    fields: dict[str, str] = {
        "ACTION_ROWS": action_rows(args.action),
        "BIGNUM_CARDS": stat_cards(args.stat, "bignum"),
        "HERO_STATS": hero_stat_cards(args.stat),
        "SHAPE_TODAY": side_list(args.today, "Today"),
        "SHAPE_AFTER": side_list(args.after, "After"),
        "CTA_HEAD": esc(cta_head),
        "CTA_LINE": esc(cta_line),
        # The maker's mark is OPT IN. A default string in a template is how one company's name
        # ends up on another company's one-pager.
        "MARK": esc(args.mark),
        # The eyebrow NAMES NOTHING unless the author says what it is. A default company name
        # in a template is the wall rule broken by a default value.
        "EYEBROW": esc(args.eyebrow),
        "PREPARED_FOR": esc(args.prepared_for),
        "FROM": esc(args.prepared_from),
        "DATE": esc(args.date),
        "SOURCE": esc(args.source or source.name),
        "METHOD": esc(args.method or f"Built from {source.name} on {args.date}. Every figure is read from that file, none is estimated."),
        "FOOT": esc(args.foot or f"Prepared {args.date}. Built from {source.name}."),
        "VERDICT": verdict_box(args.verdict),
    }

    look = resolve_look(args.look, args.surface)
    audience = resolve_audience(args.audience)
    allow = [part.strip() for entry in args.allow for part in entry.split(",") if part.strip()]
    used_components: set[str] = set()

    if source.suffix.lower() in {".md", ".markdown"}:
        title, sections = markdown_to_sections(
            read_text(source), used_components, store_prefix(destination), numbered=not args.unnumbered
        )
        title = args.title or title or source.stem.replace("-", " ").title()
        nav_pairs = [
            {"id": s["id"], "label": s["label"], "num": s["num"], "kind": s["kind"], "lead": s.get("lead", "")}
            for s in sections
        ]
        content = sections_to_html(sections)
        links = harvest_links(content, args.link)
        fields.update(
            {
                "TITLE": esc(title),
                "LEDE": esc(args.lede or "Built from the source record. Every figure and link below is read from it."),
                "CONTENT": content,
                "TOC": toc_section(nav_pairs),
                "AGENDA": agenda_chips(nav_pairs),
                "LINKS": links_section(links),
                "KPIS": "",
            }
        )
        nav_sections = list(nav_pairs)
        if len(links) >= 2:
            nav_sections.append({"id": "links", "label": "Key links", "num": "", "kind": "top"})
    else:
        headers, rows = load_rows(source)
        numeric = numeric_columns(headers, rows)
        kinds = classify(headers, rows, numeric)
        title = args.title or source.stem.replace("-", " ").replace("_", " ").title()

        chart_index = None
        if args.chart_col and args.chart_col in headers:
            chart_index = headers.index(args.chart_col)
        else:
            # never default to a year or an id column: charting one says nothing and captions it wrong
            chart_index = next(
                (i for i in numeric if kinds.get(i) == "sum"),
                next((i for i in numeric if kinds.get(i) == "rate"), None),
            )
        label_index = headers.index(args.label_col) if args.label_col in headers else (
            next((i for i in range(len(headers)) if i not in numeric), 0)
        )

        chart_html = ""
        if chart_index is not None:
            # one pass, so a blank cell drops its own row rather than shifting every later label
            pairs = [
                (row[label_index] if label_index < len(row) else "", to_number(row[chart_index]))
                for row in rows
                if chart_index < len(row) and is_number(row[chart_index])
            ]
            svg = svg_bars(pairs, headers[chart_index])
            if svg:
                chart_html = (
                    f'  <section id="chart">\n    <div class="sec-num">The shape of it</div>\n'
                    f"    <h2>{esc(headers[chart_index])} across {len(pairs):,} rows</h2>\n"
                    f'    <p class="sub">Hover any bar for its exact value. The frame has a fixed height on purpose.</p>\n'
                    f'    <div class="chart-frame">{svg}</div>\n  </section>\n'
                )

        content = chart_html + data_table(headers, rows, numeric, args.row_limit)
        links = harvest_links(content, args.link)
        fields.update(
            {
                "TITLE": esc(title),
                "LEDE": esc(args.lede or f"Read straight from {source.name}: {len(rows):,} rows, {len(headers)} columns."),
                "CONTENT": content,
                "KPIS": stat_cards(args.stat, "kpi g") if args.stat else kpi_cards(headers, rows, numeric, kinds),
                "TOC": "",
                "AGENDA": "",
                "LINKS": links_section(links),
            }
        )
        nav_sections = ([{"id": "chart", "label": "The shape of it", "num": ""}] if chart_html else [])
        nav_sections.append({"id": "table", "label": "The data", "num": ""})
        if len(links) >= 2:
            nav_sections.append({"id": "links", "label": "Key links", "num": "", "kind": "top"})

    extra_css, extra_js = component_assets(used_components)
    page = compose(
        args.surface, fields, nav_buttons(nav_sections), keep,
        look=look, extra_css=extra_css, extra_js=extra_js, audience=audience,
        kind=args.kind.strip(),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    extras = ", ".join(sorted(used_components)) or "none"
    print(
        f"built {destination} ({len(page):,} bytes, surface {args.surface}, look {look}, "
        f"audience {audience}, kind {args.kind.strip() or 'not given'}, "
        f"{len(nav_sections)} nav sections, components: {extras})"
    )
    for line in wall_notice(page, allow, audience):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
