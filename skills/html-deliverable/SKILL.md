---
name: html-deliverable
description: >-
  Build a polished, standalone HTML file for a human to read: a client, partner or team
  deliverable, a report, a confirmation, a one-pager, a summary, an audit, or any "put this
  into a nicely formatted HTML file" request. Use whenever the ask is "make an HTML file",
  "create an HTML deliverable", "send X an HTML report", "one-pager", or a formatted document
  to hand somebody. Applies one house style (serif headings, light and dark, copy-pasteable
  link tables, print-ready) so every HTML file looks the same, everywhere. Four named surfaces
  (report, deck, poster, data-report), a one-command build from markdown, CSV or JSON
  (build.py), and a mandatory pre-delivery check (lint.py).
license: MIT
---

# HTML Deliverable

The one way to build an HTML file somebody will read. Every file, every repo, uses the same
formatting and the same checks. Do not invent a new look per document.

## READ FIRST: `DESIGN.md` is the authority on how a page LOOKS

This file says WHEN to build one and WHAT goes in it. **`DESIGN.md` beside it says how it looks
and behaves**, and **`components.html` is the live gallery** of every component with its
copy-paste source. Open the gallery in a browser before building anything non-trivial.

### The two looks (full detail in DESIGN.md section 1)

The look is one attribute on `<html>`; nothing else changes between them.

| | **Tint** `data-look="tint"` | **Classic** `data-look="classic"` |
|---|---|---|
| Use it for | agendas, call documents, client one-pagers, internal reading | formal reports, deliverables, agreements |
| Look | cool ground, 28px graph paper, 1080px column, blue accent | warm off-white, flat ground, 1000px column, gold accent |

`build.py --look auto|tint|classic`. `auto` gives **tint** for the deck and poster surfaces and
**classic** for the report and data-report surfaces. State it explicitly when you know the reader.

### The anti-regression law (the reason DESIGN.md exists)

**A page is NEVER built from an older document, from a one-off script, or from memory.** The only
sources are `template.html`, `templates/<surface>.html` and `components.html`. If a page needs
something none of them carries, add it to the gallery in the same session, then use it.

Two months of design work dies every time a page is rebuilt from a copy of last month's page, and
the reader sees it as the system forgetting.

### What every page carries, enforced by `lint.py`

- **The reading-width handles**: drag either edge of the page to resize the column, remembered per
  page. The lint REFUSES a multi-section page without them.
- **The right-side rAF section nav**, visible from the top, which never overlaps the column at any
  width or any dragged size.
- **Filtering and sorting on any table or list of data**, and any number the reader might play
  with as an input or a slider. `build.py` upgrades any markdown table of six rows or more
  automatically; `[table: plain]` opts one out.
- Light default, print block, self-contained, no em dashes or mid dots in any form.

## When this fires

Any request to produce an HTML file to hand to a human: a client or partner report, a
confirmation, an executive summary, a one-pager, an audit writeup, a "drop this into a nice HTML
file" ask. If somebody will open it, send it, or drag it into a message, this skill applies.

NOT for: application UI components (that is your frontend stack), email templates (those belong
in your email platform), or throwaway debug HTML.

## Install

The skill is a folder. Put it where your agent looks for skills:

```bash
# Claude Code, globally
cp -R skills/html-deliverable ~/.claude/skills/

# or install the whole repository as a plugin marketplace
# /plugin marketplace add <owner>/html-deliverable
```

Then ask for an HTML deliverable in any repo and the skill fires on its description.

**Python 3.12 or newer** (the builder uses PEP 701 quoting inside an f-string expression, so 3.11
dies with a `SyntaxError` before it reads an argument). The only dependency is the `markdown`
package, and only for markdown input: `pip install markdown`. CSV and JSON need nothing. The lint's
render check wants Playwright (`pip install playwright && playwright install chromium`, or a Node
`playwright` module it can find); without it the render check SAYS it could not run rather than
passing silently.

## The build (do this, in order)

0. **Pick the surface** (the table below) and decide whether to BUILD it or HAND-WRITE it.
   A markdown, CSV or JSON file that is already the content builds in one command:
   `python build.py <input> <output.html> --surface report`.
   Anything composed from many sources is hand-written from `template.html`.
1. **Copy `template.html`** as the starting point when hand-writing. It carries the full house
   style; do not hand-rebuild the CSS. Fill every `REPLACE` marker.
2. **Ground every fact in real data.** Pull the real numbers, URLs and ids from the database, the
   repo or the live system. Never a placeholder, never an invented figure.
3. **Structure:** cover header (eyebrow, h1, lede, prepared-for and date) then a `.verdict` box
   with the one-line bottom-up answer, an optional `.warn` box for the single real caveat, an
   `At a glance` fact grid, a **Key links table listing EVERY destination named anywhere in the
   document, copy-pasteable**, one `<section>` per logical part, and a `.foot` line.
4. **Save** to wherever your deliverables live, with a dated filename: `<slug>-YYYY-MM-DD.html`.
5. **Run the lint before delivering, every time:**
   `python lint.py <file.html> --playwright` (add `--money` for anything with figures in it, and
   `--audience external --allow "<the company this page may name>"` for anything leaving the
   building). It is the pre-delivery gate for every hard rule below, and it renders the page at
   1440 and 1920 to catch overflow. **A page that has not been linted has not been checked.**
6. **Open it and LOOK at it.** Screenshot at 1440, 1920 and 390, and read the rendered page rather
   than the source.
7. **If it accompanies a message**, keep the message short and high level. The depth lives in the
   HTML file.

## Hard rules (non-negotiable)

- **NO em dashes anywhere in the file**, including the CSS comments and the body copy. Both the
  raw character and the entity forms are refused. Use spaced hyphens or better punctuation.
- **NO compressed lists.** Any enumeration of two or more items renders as a real `<ul>` or `<ol>`,
  nested under its parent `<li>` when it belongs to a bullet, NEVER a single line joined with
  separator characters. Mid dots are refused in raw and entity form.
- **Every referenced destination is a real, working, copy-pasteable URL**, never a bare name. The
  Key links table is mandatory whenever the document names two or more destinations.
- **Every external link opens in a NEW TAB**: `target="_blank" rel="noopener noreferrer"`, on every
  file this skill produces. A reader keeps a deliverable open in one of many tabs; a link that
  navigates the document away costs them their place in it. `build.py` writes the attributes on
  every page it composes and `lint.py` REFUSES a page carrying an external `<a>` without them.
  In-page anchors and relative paths are left alone.
- **Self-contained**: all CSS inline in `<style>`, no external fonts, scripts or CDNs, images as
  data URIs. The file must render offline when it is dragged into a message.
- **Light is the DEFAULT rendering; dark stays reachable by the toggle only.** Ship
  `data-theme="light"` on `<html>`, no `prefers-color-scheme` auto-switch, the toggle seeded from
  `'light'`. Keep the full dark token set so the toggle works. Do not strip either theme.
- **EVERY DOLLAR AMOUNT CARRIES A DOLLAR SIGN**, in prose, in tables, in cards and in figures. A
  number without its sign is read as a count. `lint.py --money` refuses three shapes: a number the
  prose calls dollars ("10,298.92 dollars"), a bare number under a column header that names money,
  and a bare number the page itself writes WITH a sign somewhere else. It also reads inside a
  `flow` figure's JSON block, because a figure's amounts live in a script and the prose scan strips
  every script. Write `$` in a `[diagram:]` label too; the builder escapes it for d2, which would
  otherwise refuse to compile.
  **Two currencies on one page: the sign FIRST, the currency named AFTER the number.** Write
  `$10,422.65 MXN` and `$1,403.81 USD`. The lint refuses a currency code before a number
  (`MXN 1,234`) and a number followed by a code with no sign in front (`1,234.00 MXN`); a column of
  such amounts still sorts numerically, because the builder reads the trailing code as part of the
  number.
- **Real content, never lorem.** Real names, real copy, real links.
- **Print-ready**: keep the `@media print` block. These get printed and saved as PDFs.
- **NO terminal commands in the visible prose of a reader-facing deliverable.** Most readers do not
  run commands, and a "try it: `python build.py ...`" box is noise that confuses. Say what the
  capability DOES in plain English, or show its OUTPUT, never the invocation. Script and style
  blocks are exempt, and `--allow-commands` clears the check for an internal page.
- **Engineering units are not the headline.** "Six capabilities shipped", "five pull requests
  merged", "three migrations applied" mean nothing as summary numbers. Lead with what changed FOR
  THE READER in their own vocabulary, shown visually: mock what a screen looks like, walk a
  concrete story, prefer a picture of the thing over a count of the work.
- **The tab reads the document's own title, exactly.** No product prefix or suffix, no kind label,
  the same string the page's `<h1>` shows. The lint refuses a missing title, a generic one and a
  title that differs from the h1.

## The four surfaces

Pick one before writing a line. The palette, the type, the theme toggle, the right-side nav and
the print block are identical across all four: only the structure changes.

| Surface | Use it for | What it adds |
|---|---|---|
| **report** (default) | anything somebody READS: a status report, an audit, a research brief, a triage table, a decision pack | the shape the house style was extracted from: cover, verdict, at a glance, the links table, one section per part |
| **deck** | a CALL document: an agenda you screen-share that keeps working after the call | an agenda chip spine, a numbered beat per section, an outcome line, an owner-and-date action table, the "Live document" pill |
| **poster** | a CLIENT one-pager: the thing handed to a prospect or an owner | 28px graph-paper ground, a centered hero, three big numbers, problem-arrow-solution blocks, one CTA, an optional maker's mark, `--acc` for the client's own color |
| **data-report** | a numbers page from a CSV, a JSON export or a query | KPI cards, fixed-height chart frames with a premium custom tooltip, a zebra table with a sticky header and `content-visibility` rows, a methodology fold |

Each surface is a module in `templates/<surface>.html` holding two blocks: `SURFACE:CSS` (its
extra CSS) and `SURFACE:BODY` (its structure). `template.html` stays the single source of the
palette and the shared behavior, so a surface can never fork the house style. A surface module's
optional blocks (`OPTIONAL:ACTIONS`, `OPTIONAL:BIGNUMS`, `OPTIONAL:SHAPE`, `OPTIONAL:CTA`) are
DROPPED by the builder when there is no data for them, which is why a built page never ships a
stray `REPLACE`.

## The any-input recipe: `build.py`

```bash
python build.py <input> <output.html> --surface report \
  --title "..." --for "The board" --from "Operations" --date "September 15, 2026" \
  --verdict "the one-line answer" --link "The dashboard=https://..."
```

- **Input:** `.md` (the first `# ` line is the title, every `## ` starts a section, every LATER
  `# ` line starts a PART), `.csv`/`.tsv`, or `.json` (a list of objects behaves like a CSV, an
  object becomes a definition table).
- **Sections keep their own numbers.** A heading that already reads `## 3. The budget` keeps the 3;
  the builder never prints a second, disagreeing number beside it.
- **Links are harvested, not invented.** Every external href in the content, plus anything passed
  with `--link`, becomes the Key links table whenever there are two or more. A harvested label
  carries the host AND the path tail, so three destinations on one host are told apart.
- **Bare URLs become real links.** Markdown leaves a bare `https://...` as plain text, which
  silently breaks the always-link rule. The builder wraps every bare URL that is not already a
  link, a code span or a fenced block.
- **Every external link leaves with a new tab.** The rewrite runs on the FINISHED page, so it
  catches all three ways a destination reaches a deliverable: the markdown renderer's own `<a>`,
  raw HTML the author pasted into the source, and the Key links table the builder generates.
- **Diagrams are pre-rendered to inline SVG.** A `[diagram: <kind>]` line followed by a fenced
  block becomes a real picture in the file, re-colored onto the house tokens so it follows the
  theme toggle. Four kinds, each with a live demo and a copy-paste source in the gallery:

  | Kind | Engine | What goes in the fence |
  |---|---|---|
  | `flowchart` | d2 | d2's own language: `a: A request lands`, then `a -> b: it is read` |
  | `sequence` | d2 | one message per line: `Reader -> Assistant: a question`. The container is supplied |
  | `mindmap` | graphviz, radial | an indented outline, two spaces to a level |
  | `tree` | graphviz, left to right | the same indented outline |

  A caption goes after a pipe: `[diagram: mindmap | What the system holds]`. It becomes the
  figure's caption and its accessible name. **The engines are not bundled with this skill**: the
  builder finds them on PATH or in a per-user install, and names the exact install command when
  one is missing (`winget install Terrastruct.D2` and `winget install Graphviz.Graphviz`, or the
  release archives unpacked under a user-writable folder, which needs no elevation). The
  comparison that chose them is DESIGN.md section 3a.
- **Nav labels cut on a word boundary**, never mid-word.
- **Nothing is fabricated.** For tabular input the KPI cards are counts, sums and the change
  against the previous row; no insight text is written for you.
- **The surface's own blocks are filled from flags, or they do not ship.**
  `--action "Task|Owner|By|Status"` (repeatable) builds the deck's action table; `--stat
  "Number|Label|Tone"`, `--today`, `--after` and `--cta "Headline|Line"` build the poster's numbers,
  its problem-to-solution pair and its one next step. A block with no data is removed from the page
  rather than shipped with a placeholder in it, and `lint.py` fails any page that still carries a
  `REPLACE` or an unfilled `{{TOKEN}}`.
- **`--kind`** writes `<meta name="document-kind">` so a document library that indexes built pages
  reads the kind instead of guessing it from the file name. One vocabulary, `KINDS` in `build.py`;
  an unknown kind is refused before a page is built.
- It reads every file with `utf-8-sig`, because a file a PowerShell script wrote carries a BOM.

## The pre-delivery gate: `lint.py`

```bash
python lint.py <file.html> --playwright --money
python lint.py <file.html> --audience external --allow "Acme"
```

Every hard rule above, mechanically, in one pass: the wall list (no company or client name the page
was not given, read over the whole file including attributes, comments and CSS), em dashes, mid
dots, terminal-command tokens in the visible prose, the Key links table when two or more
destinations are named, `target="_blank" rel="noopener noreferrer"` on every external link, the
right-side nav when there are two or more sections, the rAF-eased scroll, `data-theme="light"` and
no `prefers-color-scheme`, self-containment, the tab title, a leftover `REPLACE`, lorem ipsum, and
a `<ul>` inside a `<p>`.

- `--money` lists every money token for a human eyeball and fails on a placeholder amount or an
  unsigned one.
- `--playwright` renders at every width in `--widths` (default 1440 and 1920; add 390 for the phone
  check) IN BOTH THEMES and fails on horizontal overflow, on a nav taller than the viewport, on a
  value that leaves its box, and on the figure defects below. When Playwright is not available it
  SAYS SO and does not pass silently.
- `--pdf` prints the page through its own print block, so there is one source and the print CSS is
  exercised rather than a second layout engine.

## Client-safe by construction

A page is read by somebody who was never told which other companies exist. It should be impossible
to hand them one that says. Four mechanisms, none of which anybody has to remember:

1. **The tokens name nobody.** The look is `data-look="tint"` or `data-look="classic"`, never a
   client's initials or a product's name.
2. **The builder strips what a reader never needs.** Every CSS comment, every HTML comment, and the
   maker's-mark rules on a page that renders no mark are gone from the emitted file. Comments
   inside `<script>` stay, because rewriting JavaScript with a regular expression turns a working
   page into a broken one; they name nobody, and the lint reads them anyway.
3. **The maker's mark is opt in.** `--mark "<text>"` puts it on a page. No template carries a
   company name as a default value, which is the shape the original defect had: a one-pager built
   from a house template and sent unchanged once carried another client's short name in a CSS
   selector and a third company's name in a comment, invisible on the page and one find-in-page
   away from the reader.
4. **The lint refuses a leak.** It reads the WHOLE file, not the visible words, against the wall
   list in `wall-list.txt` beside it. On a page whose audience is EXTERNAL it is a refusal;
   anywhere else it is a note. The page carries its own `data-audience`, written by the builder,
   which defaults to external, so the gate fires even when nobody passes a flag.

`--allow` names the companies this page is entitled to name. Adding a name to the wall is one line
in `wall-list.txt`; it is data on purpose. Matching is case-insensitive, whole word at the front,
and blind to the separator, so one entry for `acme holdings` catches `Acme Holdings`,
`acme-holdings` and `acmeholdings`. A person's signature is not a company: list a company's full
name, never a surname on its own.

**The line this draws:** a file whose text can end up inside a delivered page names nobody
(`template.html`, the four surface modules, the gallery's emitted HTML). The documents that never
ship keep the whole record: this file, `DESIGN.md` and the tests.

## Executive summary and navigation (REQUIRED on any multi-section report)

1. **Above the fold is an EXECUTIVE SUMMARY.** Hero stat cards with the headline figures, plus the
   one-sentence verdict in plain English. The reader should get the whole story without scrolling.
2. **Know the VIEWER and build for their motive.** Ask "who opens this and what do they want?"
   before choosing columns and colors. A revenue list whose viewer is a salesperson leads with
   money numbers and cuts the fields they will not act on.
3. **Colored stat cards: color is FOCUS, not decoration.** Green is money, opportunity and
   act-now; red is risk; amber is caution; the accent is context volume.
4. **A table of contents at the top**, anchor links to every section, right under the summary.
5. **A right-side floating section nav**, fixed right, vertically centered, small right-aligned
   labels, an IntersectionObserver highlight, **rAF-eased scrolling and never native smooth**
   (`scrollIntoView({behavior:"smooth"})` and CSS `scroll-behavior:smooth` silently degrade to an
   instant jump under reduced-motion settings and some browser builds, so the handler computes the
   target offset and eases it over about 480ms with `requestAnimationFrame`). Hidden below 1200px
   and in print, and **visible from the very top of the document, never scroll-gated**.
6. **Table craft:**
   - **Audience-driven columns:** cut or demote any field the viewer will not act on and give that
     width to what they will.
   - Stacked identity cells: name bold on line 1, email and phone muted on line 2, never separate
     half-empty columns.
   - Dates and numbers never wrap: `white-space: nowrap`, short formats.
   - Long free text goes on a full-width sub-row under the main row, never a wide column.
   - No horizontal scroll at 1440 or 1920: use the content width before adding a scroll wrapper.
7. **NUMBER CONSISTENCY ACROSS SURFACES.** Any stat that appears in more than one place must AGREE
   everywhere, and before summing a table into a headline number, DEDUPE the underlying entities.
   The caught case: the same deal appeared twice under a garbled name spelling, so the headline
   overstated by $75,000 and the counts drifted five against seven against eight across surfaces.
   Pre-delivery pass: list every number that appears twice or more and verify each pair matches;
   list the rows behind any summed headline and verify no two rows are the same entity under
   different names. When a correction lands after delivery, add a dated correction box to the
   document, never a silent edit.
8. **MANDATORY visual verification before delivery.** Render the file in a real browser, full-page
   screenshot at 1440 AND 1920 (plus 390 if it will be read on phones), actually LOOK at it
   (wrapped dates, dead columns, overflow) and iterate until clean. Shipping generated HTML
   unrendered is the same defect as claiming a page works without loading it.

## A page for a partner or a client is COMPOSED, never poured

`build.py` turns a markdown record into a uniform report: one card per heading, top to bottom. That
is the right output for a record somebody reads themselves and the wrong one for a partner reading
a reply to a page they designed.

1. **A page that replies to a document the counterpart designed speaks their visual language.**
   Read their file first. Carry their legend, their stage cards, their chips and their section
   order into the reply so the two pages read as one conversation; the house tokens still govern
   color and type underneath.
2. **A partner-facing page is HAND-COMPOSED from the components gallery**, never built flat from a
   long markdown. When the reader is a partner or a client and the source is over about 2,000
   words, the page is composed: a one-screen executive summary, a summary card at the top of every
   part or stage, the questions for the reader in their own colored blocks (one color, one
   meaning, used everywhere), and the detail folded under the summaries.
3. **Words are a budget.** State the reader's reading time in the cover line and keep it under
   about ten minutes for a partner; the long form lives in a markdown twin, linked once.
4. **The lint sees flatness.** Over about 3,000 prose words (code samples excluded), every section
   over 250 prose words must open with a summary block, and the page must carry at least one block
   that uses color to mark meaning. Missing EITHER half is the hit. A warning anywhere, a REFUSAL
   when the audience is external.

The page that produced this rule, rebuilt against it: 7,958 words in one flat column, about 36
minutes of reading, became 2,667 words of summaries (about 12 minutes) over eight stage cards on
the counterpart's own spine, with 5,059 words of argument folded underneath.

## A workflow page opens with a picture

**Draw a diagram whenever the content is a workflow, a system, a pipeline, a path, an automation, a
mind map or a concept**, and whenever somebody asks for a diagram, a map, a flowchart or a visual
depiction. The heading is the author's own words.

The house tool is the gallery's `flow` component: a lane-and-column map drawn from a JSON block,
inline SVG on the tokens, both themes, swipeable below 760px. A shape `flow` cannot draw (a
sequence, a tree, a mind map) is pre-rendered to inline SVG at build time by a proven open-source
engine, never loaded from a CDN. Every box is a real thing with its real name, and the detail
sections follow the diagram's order. **A workflow page with no picture is not done.**

**A part's own body renders inside a section card.** Content under a level-1 part heading that
carries no level-2 sections is wrapped in the same card a section gets; a part head is never
followed by bare prose on the page ground. The builder wraps it, and `lint.py` refuses a part head
whose next rendered block is not a section card.

## The figure is measured, not looked at

A figure is the one thing on a page a screenshot is worst at judging. Text 9 pixels outside its
box, a connector crossing a node, a tag painted over its own label: every one of those looks like a
picture in a thumbnail and like a mistake to the person reading it. So `--playwright` MEASURES,
box against box, and names the figure, the element and the pixels.

Seven refusals, each proved by a fixture in `fixtures/figure-inversions/` that breaks exactly that
rule:

1. **Text outside the box it belongs to.** The message names the text, the node and the pixels.
2. **A label painted under a shape that covers it.** Document order is paint order in SVG.
3. **A connector routed through a node.** The path is sampled, not parsed, so a future curve is
   judged the same way. On a d2 or graphviz drawing this is REPORTED rather than refused, because
   the router there is the engine and not this skill.
4. **Two node boxes on top of each other.**
5. **A tag pinned over a box that is not its own.**
6. **A figure that drew nothing**: no SVG, or an SVG with no shapes in it.
7. **A figure wider than the column it sits in**, unless that figure scrolls sideways on purpose.

`fixtures/flow-broken.md` carries a figure whose JSON is fixed. Before the repair it produced 44
findings across three widths and two themes; after it, none.

## No value may leave its box

The page-level overflow check cannot see a value that spills INSIDE a page that does not overflow.
`.stat .num` is `white-space: nowrap`, a four-card stat row gives each card 189 pixels, and
`$41,014.06` renders at 192. `--playwright` measures every element a value can sit in
(`CLIP_SELECTORS` in `lint.py`) and compares each one's scroll width against the box drawn around
it, at every width and in both themes the render already visits. An element that scrolls BY DESIGN
is skipped. A finding is reported ONCE, with every width and theme it happened at, and a clean page
SAYS it was checked, so silence is never mistaken for absence.

Proved by inversion, because a gate that cannot fail proves nothing:

```
python lint.py fixtures/clipping-overflows.html --playwright --widths 390,1440   # exit 1
python lint.py fixtures/clipping-wraps.html     --playwright --widths 390,1440   # exit 0
```

The two fixtures carry the SAME four values in the SAME four cards and differ in one CSS
declaration, `white-space`. The fix for a real page is to widen the box, shorten the value, or let
it wrap. Do not silence the gate.

## Large documents

### When it applies

Any document with more than about twelve sections. Below that a page stays flat: grouping four
sections is ceremony, not navigation.

### What the author writes

A **part** is a level-1 heading in the BODY of the markdown (the first `# ` line is still the
document's title). Sections stay level-2:

```markdown
# The document title

# 2. Claim one: client-facing emails are switched off
One sentence introducing the part.

## The evidence
Body copy.
```

### What the builder does on its own

- The part heading opens its own block above the sections it introduces, never inside a card.
- Heading sizes step down: part, section, sub-section, in both looks.
- Sections are numbered within their part (`2.4`), so the number says where the reader is.
- The rail goes two-level: the parts are the top level, only the part the reader is in lists its
  sections, the rail caps its own height at the screen with a quiet scrollbar behind that, and the
  active entry is kept in view.
- The contents block at the top follows the same grouping, never a flat list of forty chips.
- A document with more than twelve top-level entries and no parts of its own is grouped
  automatically, so a page author cannot produce an unusable rail by accident.
- `--unnumbered` turns section numbers off, and the label still renders as a real heading.

### What the lint refuses

A rendered nav taller than the viewport at 1440x900 (with `--playwright`), a heading that is the
last thing in its section, a heading with no content before the next heading of the same or a
higher level, and a part head that introduces nothing. It WARNS above twelve top-level nav
entries. Full detail in `DESIGN.md` section 11.

## Performance: a deliverable that bogs down a machine is broken

An 808-message record once shipped as 808 fully-styled blocks in a 723 KB, 165,000-pixel page. It
locked up a top-of-the-line machine for close to a minute on scroll, and would have done worse to
anyone it was sent to.

**Any page that will hold more than roughly 150 repeated blocks (messages, rows, cards, log lines)
MUST be built so the browser only does layout work for what is on screen.**

```css
.row { content-visibility: auto; contain-intrinsic-size: auto 92px; }
@media print { .row { content-visibility: visible } }
```

Measured on the same 808-message file: scroll operations went from a visible multi-second freeze to
**under 1 millisecond**, with identical content and a working search.

The rest of the discipline:

- **Debounce any live filter or search** at about 140ms. Filtering 800 nodes on every keystroke is
  its own freeze.
- **Keep per-block markup cheap.** Flex containers, borders, shadows and pseudo-elements are paid
  once per block. At scale, simple markup beats pretty markup.
- **Pick the format by size before writing a line.** Under about 150 blocks, ordinary HTML. Above
  it, HTML plus `content-visibility`. For a true bulk record somebody will grep, sort or import,
  ship markdown and CSV alongside the HTML rather than pretending one file serves everyone.
- **Verify it, do not assume it.** Scroll to the middle and to the end of any long page and time
  the layout before delivering.

**This generalizes beyond deliverables.** Never put an unbounded number of live nodes on a page. In
application code the tool is virtualization; in a static HTML file it is `content-visibility`.
Different mechanism, identical rule: the browser should only pay for what the reader can see.

## Inside a frame

A page inside a sandboxed frame cannot read its saved theme or width (`localStorage` throws in an
opaque origin, and every read is guarded), so a dark application would frame a light document, and
the page's fixed rail would sit thousands of pixels down a frame a shell has grown to the page's
height. The template carries a framed-mode block, gated on `window.parent !== window`; a page in
its own tab is untouched, and a test proves it.

| Direction | Message or attribute | What happens |
|---|---|---|
| inbound, from the parent | any `{type: "<anything>-theme", theme: "dark" or "light"}` | `data-theme` is set |
| on the page | `data-embedded` on `<html>` | the chrome hides at once |
| on the page | the frame taller than the screen, re-checked on resize | `data-framed` is set and the rail, the grips, the toggle and the tooltip hide |
| outbound, to the parent | `{type: "hd-document-ready"}` then `{type: "hd-document", height, sections}` | on load, after a theme change, on every resize; at most 40 sends; only numbers and strings cross |
| outbound, suppressed | a script tagged `data-...-reporter` is present | the template stays quiet; that reporter owns the channel |
| static, in the bytes | `<script data-page-frame="template">` | a server can grep the stored bytes and know the page speaks the contract |

## The client-build register

Patterns for client-facing builds (mockup sites, client one-pagers, portals):

- **Surface panels for delineation:** group related content on raised card surfaces instead of
  floating sections on the page ground.
- **28px graph-paper ground:** the subtle grid texture behind panels.
- **Pull the palette from the CLIENT's own site.** Client builds wear the client's colors, which is
  one line overriding `--acc`, never a change to the design system.
- **Mono font for domain codes:** part numbers, job codes, SKUs and IDs render in monospace.
- **Problem, arrow, solution blocks** with three-point lists: the standard way to show a
  before-and-after or a pain-and-fix pairing.
- **Big numbers align on CENTERS, not baselines**, so mixed-size figures in a row do not stagger.
- **Client builds carry NO presenter-side notes.** Speaker notes, internal margin math and any
  "what to say here" line never ship in a client-facing file. A page that has presenter-side
  content ships as TWO files: the shareable one, and a private twin beside it carrying the notes,
  marked private in both the eyebrow and the foot.

## The visual-first register

When the ask is a document with "visuals, colors and emojis", that is a REGISTER SELECTION, not
decoration on the default look:

- **Emojis as first-class design anchors.** Every card, section or concept gets ONE stable emoji
  anchor used everywhere it is referenced. Emoji is meaning and wayfinding, not garnish. This
  deliberately overrides the generic no-emoji default for documents in this register.
- **Color-coding as information.** Each parallel entity carries its own accent hue through a
  per-card CSS variable pair, with lighter variants for dark mode. Color answers "which one am I
  looking at" from across the room.
- **Visual step cards.** Numbered procedure steps render as tinted pill rows with a filled number
  badge, never a plain numbered list, when the document's job is walking a human through physical
  actions.
- **Dual navigation on content-heavy documents:** the right-side floating nav on desktop plus a
  sticky horizontally-scrolling emoji chip nav below 1200px.
- **Dynamic freshness elements** where the document has a clock in it: computed ages, countdowns,
  auto-updating labels, so the document stays true without republishing.

Audience calibration still rules: this suits guides, walkthroughs, agendas and anything read on a
phone mid-task. Formal financial and legal-adjacent deliverables stay in the classic register.

## Five bugs never to re-learn

- **A `<ul>` cannot live inside a `<p>`**: the browser silently closes the paragraph and the layout
  breaks. Close the paragraph first.
- **Declare `border` BEFORE `border-top`**: the shorthand declared after wipes the accent color set
  by the longhand.
- **A grid child's default `min-width` is `auto`, not `0`**, so one long word makes its track wider
  than its share and the whole layout overflows instead of wrapping.
- **Inline `code` needs `overflow-wrap: anywhere`**, or an unbreakable identifier overflows the
  column at 390px and takes the page with it.
- **`li::before` counts as a grid item.** A three-column `li` grid that also carries a counter
  pseudo-element wraps its fourth child onto a new row.

## Live reload during a call

Every file built from `template.html` carries a small self-poll script at the end of `<body>`:

- **Opened from disk (`file://`):** it does nothing. The file stays a plain static snapshot to drag
  into a message.
- **Served over HTTP from `serve.py`:** the page re-fetches itself every 2 seconds and reloads the
  moment the file on disk changes, preserving scroll position. Nobody presses F5.

```bash
python serve.py <path-to-file>.html --open
```

Run it in the background, share the printed `http://127.0.0.1:<port>/...` URL, then keep editing
the file: the browser tab follows along. Kill the server when you are done. `?static=1` on the URL
forces the poll off.

## The verification bar

```bash
python -m pytest skills/html-deliverable            # the suite
python lint.py <file.html> --playwright --widths 1440,1920,390
```

Then LOOK at the screenshots. A green lint is not a design pass.

## Extending

New patterns get added to `DESIGN.md` and the gallery, then noted here. This skill is the single
source of truth for HTML-file look and feel: when somebody corrects an HTML deliverable, fold the
delta into `DESIGN.md` in the same session, rebuild the gallery with `build_gallery.py`, and add a
test for it.
