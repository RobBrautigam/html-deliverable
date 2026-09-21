# DESIGN.md - the single authority for how an HTML deliverable looks and behaves

Every HTML file this skill builds, in any repo, on any machine. `SKILL.md` says WHEN to build and
WHAT to put in it. This file says how it LOOKS. `template.html` and `components.html` are this
file's implementation; `lint.py` enforces the parts a machine can check.

Written after a measured inventory of 186 HTML files built over two months. The inventory, the
variation it found and the regressions it named are in section 9.

---

## 0. The anti-regression law (the reason this file exists)

The finding that produced it: a large body of HTML documents, built by automation over two months,
kept reverting to the look of their earliest iterations, because each new page was rebuilt from a
copy of an older one rather than from the design system.

**The law, in four clauses:**

1. **A page is NEVER built from an older document, a one-off script, or memory.** Not by copying a
   previous deliverable, not by pattern-matching one seen in a transcript, not by writing the CSS
   from recollection. Two months of design work dies every time that happens, and the reader sees
   it as the system forgetting.
2. **The only sources are `template.html` (the base), `templates/<surface>.html` (the surface) and
   `components.html` (the gallery).** If a page needs something none of them carries, add it to the
   gallery in the same session, then use it.
3. **One-off build scripts are retired.** Anything that re-implements the house style in a
   throwaway script is superseded by `build.py`.
4. **`lint.py` is the gate, not a suggestion.** A page that has not been linted has not been
   checked. The lint refuses the mechanical half of this file; the visual half is refused by
   looking at the rendered screenshot.

---

## 1. The two looks

One file carries both. The look is an attribute on `<html>`, so switching it moves nothing else:

```html
<html lang="en" data-theme="light" data-look="tint">
```

| | **Tint** (`data-look="tint"`) | **Classic** (`data-look="classic"`) |
|---|---|---|
| **Use it for** | agendas, call documents, client one-pagers, internal reading | formal reports, deliverables, agreements |
| **Character** | cool tint, 28px graph paper, a wider column | warm off-white, flat ground, the gold rule |
| **Accent** | `--acc:#1b4d7a` deep blue, `--acc-2:#0e7490` teal | `--acc:#b8862f` gold, `--acc-2:#8a6320` |
| **Ground** | `--bg:#edf1f5` with `--grid:#e8edf2` | `--bg:#f7f5f1` with `--grid:transparent` |
| **Panel** | `#ffffff` on the tint, so cards lift off the grid | `#ffffff` on the off-white |
| **Reading width** | `--wrap-w:1080px` | `--wrap-w:1000px` |
| **Shadow** | `0 1px 2px rgba(16,24,64,.05), 0 10px 30px rgba(16,24,64,.07)` | `0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.05)` |

**Which one, mechanically.** `build.py --look` takes `auto`, `tint` or `classic`. `auto` resolves to
**tint** for the `deck` and `poster` surfaces and **classic** for the `report` and `data-report`
surfaces. An author who knows the audience states it rather than relying on `auto`.

**The accent is swappable for a client build.** A client one-pager wears the client's own colors
(the standing client-build rule). That is one line, and it never touches the look:

```html
<style>:root[data-look="tint"]{--acc:#03045e; --acc-2:#017194; --acc-soft:#e4f1f6}</style>
```

The tint look's own blue is a HOUSE blue, deliberately not any client's brand navy. Wearing a
client's palette is a per-document override, never a change to this file.

### Client-safe by construction

A reader was never told which other companies exist. It should be impossible to hand them a page
that says. Four mechanisms, none of which anybody has to remember:

1. **The tokens name nobody.** The look is `tint` or `classic`, never a client's initials or a
   product's name.
2. **The builder strips what a reader never needs.** Every CSS comment, every HTML comment and the
   maker's-mark rules on a page with no mark are gone from the emitted file. Comments inside
   `<script>` stay, because rewriting JavaScript with a regular expression is how a working page
   becomes a broken one; they name nobody, and the lint below reads them anyway.
3. **The maker's mark is opt in.** `build.py --mark "<text>"` puts it on the page. No template
   carries a company name as a default value, which is the shape the original defect had.
4. **The lint refuses a leak.** `lint.py` reads the WHOLE file, not the visible words: attributes,
   comments and the stylesheet too, against the wall list in `wall-list.txt` beside it. On a page
   whose audience is external it is a refusal; anywhere else it is a note. The page carries its
   own `data-audience`, written by the builder, which defaults to external. `--allow "Acme"` names
   the company this page is entitled to name.

```bash
python lint.py <file.html> --audience external --allow "Acme"
```

**Adding a name** is one line in `wall-list.txt`. It is data, deliberately: a list of companies
grows faster than anyone edits a linter. Matching is case-insensitive, whole word at the front,
and blind to the separator, so one entry for `acme holdings` catches `Acme Holdings`,
`acme-holdings` and `acmeholdings`, and `initech` catches `initech-audit`. A person's signature is
not a company: list a company's full name, never a surname on its own, so an author line reading
their own name on their own document is not a leak.

**What this came from.** A client one-pager built from a house template and sent unchanged carried
another client's short name in a CSS selector and a third company's name in a comment, invisible
on the page and one find-in-page away from the reader. It was caught by hand, stripping comments
per file; this is that fix moved into the skill.


### The named tokens

Every component reads these. No component carries a raw hex value, which is what makes a look
change one attribute instead of a rewrite.

| Token | What it is |
|---|---|
| `--bg` `--panel` `--panel-2` | page ground, card surface, the second surface (zebra rows, inputs) |
| `--ink` `--muted` | body text, secondary text |
| `--line` `--line-2` | borders, and the lighter internal rule |
| `--grid` | the 28px graph-paper line color. `transparent` in classic, so one code path serves both |
| `--acc` `--acc-2` `--acc-soft` `--acc-ink` | the accent, its second, its wash, and the text color that is readable ON the wash |
| `--green/-soft/-ink` `--amber/-soft/-ink` `--red/-soft/-ink` | status families, each with a wash and a readable-on-wash ink |
| `--violet/-soft/-ink` | the human-actor family: a person in a lane diagram, an actor chip, anything that means "one of us did this" rather than a status |
| `--ask/-soft/-ink` | the question family: **one color, one meaning.** Everything it touches is a question the reader has to answer. Never used for anything else, and deliberately not the red that marks a weak spot |
| `--shadow` | the one shadow. It carries an offset and a soft blur; a zero-offset halo is decoration |
| `--radius` `--radius-sm` | 14px panels, 10px boxes |
| `--font-head` `--font-body` `--font-mono` | Georgia serif, system sans, system mono |
| `--wrap-w` `--wrap-min` `--wrap-max` | the reading width and the range the handles may drag it through (720px to 1600px) |

**The `-ink` tokens are load-bearing.** Status text sits on its own wash, so it is tinted from that
hue rather than using the base status color, which fails contrast on a pale background. Body and
placeholder text hold 4.5:1; large text holds 3:1.

### Theme

Light is the shipped default on every page, always. Dark is reachable only by the toggle.
Mechanically: `data-theme="light"` on `<html>`, **no `prefers-color-scheme` block anywhere**,
and the boot line applies a saved value only when one exists:

```js
var saved = localStorage.getItem('hd-theme'); if (saved) root.setAttribute('data-theme', saved);
```

A bare `applyTheme(localStorage.getItem(KEY) || '')` strips the light default and is the trap that
has caught this twice. The dark token set stays complete so the toggle is never a dead end.

---

## 2. Layout rules

1. **The cover.** Eyebrow, h1, lede, then a `cover-meta` row carrying prepared-for, from and date.
   A 2px accent rule closes it. Every document has one; it is what makes a file look prepared
   rather than dumped.
2. **The executive summary is above the fold** on any multi-section document: the one-sentence
   plain-English verdict with the headline numbers bolded, then the stat row. The reader gets the
   whole story without scrolling. Color is FOCUS, never decoration: green is money and act-now, red
   is risk, amber is caution, accent is context volume.
3. **Contents chips** sit right under the summary on any document with three or more sections, one
   chip per section, each an anchor.
4. **The right-side section nav is REQUIRED on every page with two or more sections**, whatever
   built it. Fixed right, vertically centered, small right-aligned
   labels, IntersectionObserver highlight at `rootMargin:'-40% 0px -55% 0px'`, **visible from the
   very top and never scroll-gated**, hidden below 1200px and in print.
   **The click scroll is rAF-eased, never native.** `scrollIntoView({behavior:'smooth'})` and CSS
   `scroll-behavior:smooth` silently degrade to an instant jump under OS reduced-motion, some
   browser configurations and certain Chromium builds. The handler computes the offset and eases it
   over about 480ms with `requestAnimationFrame`. Inside a hosting shell that installs its own
   handler, an interim listener must run in the CAPTURE phase, because the shell has already
   jumped the page by the time a bubbling listener runs.
5. **Width handles on every page wider than a phone.**
   A 22px strip down each edge, the grip invisible at rest and revealed on hover, focus or drag.
   Dragging either edge
   outward widens the column; the left grip reads inverted. The chosen width is clamped to
   `--wrap-min`/`--wrap-max`, written to `--wrap-w` on `<html>` and remembered per page in
   `localStorage`. Double-click, `Home` or `Escape` resets to the look's default; the arrow keys
   move it 40px at a time when a grip has focus. Hidden below 1200px and in print.
6. **The theme toggle** sits top right at `position:fixed; right:14px; top:14px`, never bottom
   right, because a hosting shell's own bar often owns that corner at a higher stacking order.
7. **The print block** stays on every page. It hides the toggle, the nav, the grips, the tooltip and
   the table controls; removes the shadows, the grid and the width cap; makes links black; and
   forces `content-visibility:visible` plus `display:table-row` on filtered rows so a printed table
   is complete. These get PDF'd.
8. **Section cards, not floating prose.** Related content groups on a raised `<section>` panel.
9. **Reading measure.** Body copy runs 65 to 75 characters at the default width. A wide DATA table
   is the one thing allowed to use the full column; prose never is.
10. **Mobile is designed, not inherited.** The nav and the grips disappear below 1200px, the stat
    row collapses to two columns at 980px and one at 600px, the facts grid collapses at 560px.
    Every page is checked at 390px before it ships.

---

## 3. The component catalogue

Every component below is live in **`components.html`** with its paste-ready HTML, CSS and JS. That
gallery is the source. Nothing here is written from memory.

| Component | Class | When to use it |
|---|---|---|
| Part heading | `.part-head > .part-num + h2.part-title` | a document with more than about twelve sections. It opens its own block on the page ground, above the sections it introduces, never at the foot of the card before it (section 11) |
| Stat card row | `.hero-stats > .stat.g/.a/.r/.n` | the executive summary of any multi-section document. Three or four numbers, center-aligned so mixed-size figures do not stagger |
| Line chart with a crosshair readout | `figure.chart[data-chart]` | several series over time, with an optional shaded band between a best case and a worst case. Every value lives in the `chart-data` JSON block inside the figure, so a rebuild is a data edit; it draws in real pixels and redraws on resize; it carries its own readout card because the shared tooltip renders one line and one value |
| Status chips | `.chip.g/.a/.r/.n` | a state inside a table cell or a fact grid. Never a sentence |
| Verdict box | `.verdict` | the one-line bottom-up answer, green when it is good news |
| Warn box | `.warn` | the single real caveat or owed action. One per document; a page of amber says nothing |
| Callout | `.callout` | a highlighted aside inside a section |
| Part summary strip, with the detail folded under it | `.stage-summary > .ss-row.agree/.change/.add/.done/.line`, then `details.fold[data-fold] > summary + .fold-body` | **every part or stage of a long document written for somebody else.** Three short lines at the top: what is agreed, what changes, what is added, so the reader who stops there has still read the reply. The argument, the tables and the evidence go under the fold-out, whose open state is remembered per page and which opens itself for printing. The neutral `.line` row is for a card with one summary line rather than three. A partner-facing page over about 2,000 words is composed this way and never built flat from a long markdown: `lint.py` warns when it is and refuses an external page (section 6) |
| The picture: a lane-and-column map of a whole path | `figure.flow > script.flow-data` | **the opening of any page that explains a workflow, a system, a pipeline or a path**: one map of the whole thing before any prose, so the reader sees the shape before the detail. Boxes are real things with their real names, lanes are who or what acts, arrows are the path, and an optional mark pins a tag (a question number, an owner) to a box. Inline SVG drawn on the tokens, both themes, and below 760px the figure scrolls sideways at full size rather than shrinking its labels. Everything is in the JSON block inside the figure: a change is a data edit, and there is no hand-placed coordinate to go stale. **A workflow page with no picture is not done** |
| Diagram: a flowchart, from four lines of markdown | `figure.dgm > .dgm-art[data-engine="d2"]` | a path with branches, when the lane-and-column map above is more machinery than the page needs. Written as `[diagram: flowchart]` plus a fenced block in the markdown source; the builder pre-renders it to inline SVG at build time with **d2** and re-colors it onto the house tokens, so it follows the theme toggle. Nothing is fetched and nothing draws in the reader's browser (section 3a) |
| Diagram: a sequence, who says what to whom | `figure.dgm > .dgm-art[data-engine="d2"]` | a conversation in time: a request and its answer across two or more actors, an API round trip, an approval that goes out and comes back. One line per message; the builder supplies d2's sequence container and blanks its label so the figure's caption is the only title |
| Diagram: a mind map, radial from one center | `figure.dgm > .dgm-art[data-engine="graphviz"]` | one idea and everything hanging off it. The source is an indented outline, two spaces to a level, which the builder compiles to DOT and renders with **graphviz**'s radial layout |
| Diagram: a tree, left to right | `figure.dgm > .dgm-art[data-engine="graphviz"]` | a hierarchy: a folder layout, an org, a taxonomy, a decision tree. The same indented outline as the mind map, laid out left to right instead of around a center. Pick whichever reads better at the width the page uses |
| Questions for the reader | `.asks > .asks-head + ol > li > .rec`, chips `.chip.q` and `.chip.k` | the questions the reader has to answer, at the foot of the part they belong to, numbered as in the document's one list of questions, each carrying its recommendation on its own line. **One color, one meaning:** the `--ask` token family is used for questions and for nothing else on the page, and the two solid chips (`.q` a question, `.k` a ruling already made) read as a different register from the four soft house chips |
| Paste block | `pre > code` | a message the reader copies out and sends elsewhere: a chat reply, a text message, a prompt. It is PROSE, so it wraps; a fenced markdown block builds into it. Never let one set the page width |
| Facts grid | `.facts > .cell` | the at-a-glance pairs under the summary. Two columns, one on a phone |
| Key links table | `.scroll > table` | EVERY destination named anywhere in the document, copy-pasteable. Mandatory whenever a document names two or more |
| Filterable, sortable data table | `.dt-wrap`, `table.dt`, `th[data-sort]` | **any table or list of data, without exception** (section 4). Client-side, no network, `content-visibility` on rows, nowrap dates |
| Grouped bar, one row per thing | `figure.gbar[data-gbar]`, `.gbar-row`, `.gtrack[data-v]` | three figures compared across a list of things: agreed against invoiced against paid, budget against spent against committed. Every number rides in `data-v` and the widths are computed at load against the largest value on the whole chart, so the rows compare to each other and no percentage is written by hand. A zero value still renders its track as a dashed outline, because an empty bar is the finding |
| Range slider with a live readout | `.slider-row` | any number the reader might want to play with |
| Number and text inputs bound to a calculation | `.calc-grid` | the ROI calculator pattern. The worked example in the gallery is the canonical one |
| Drag-rank list | `.rank` | asking someone to order priorities on a call. Heat colors by position |
| Decision list with a copy-out block | `.dlist`, `.drow`, `.dpicks > .dpick`, `.dbar` | a page whose job is to collect MANY decisions at once. Every row carries its own context and is already ticked with the recommendation, so a pass that changes nothing is a valid answer; each row also takes a free-text note. The button writes one plain-text block of every row's id, title, decision and note to the clipboard, which the reader pastes back for a bulk apply. Answers persist per page in `localStorage`, every read and write in `try`/`catch`. The bar is sticky inside its list in the gallery and `position:fixed` on a whole page of decisions, keeping some right padding clear in case a hosting shell owns that corner. For a handful of live ticks on a call the checklist is the lighter tool |
| Tap-to-check checklist | `.checklist` | decisions to walk through live. State persists per page |
| Run-of-show | `.ros` | a call agenda's minute-by-minute spine: time, beat, owner, outcome |
| Timeline, two tracks | `.tl` | a plan with two parallel workstreams over the same weeks |
| Two-column comparison with a shared band | `.cmp` | before and after, or two options, with the common ground stated once underneath |
| Problem to solution | `.p2s` | a pain and its fix, three points each, with the arrow between |
| Countdown and computed age | `.age[data-until]`, `.age[data-since]` | any document with a clock in it, so it stays true without a rebuild |
| Width handles | `.grip.l` `.grip.r` | every page (section 2.5) |
| Section nav | `#sidenav` | every page with two or more sections |
| Theme toggle | `.theme-toggle` | every page |
| Print block | `@media print` | every page |
| The maker's mark | `.lockup` | client builds only, and only when `--mark` gives the text. No default, ever |
| The classic header | `header.cover` under `data-look="classic"` | formal reports and deliverables |
| Premium tooltip | `[data-tip]` + `#tip` | every chart mark and any truncated cell. **Native `<title>` tooltips are banned** as the primary hover affordance |

**Five bugs never to re-learn:**

- A `<ul>` cannot live inside a `<p>`: the browser silently closes the paragraph and the layout
  breaks.
- `border` must be declared BEFORE `border-top`: the shorthand declared after wipes the accent the
  longhand set.
- **A grid child's default `min-width` is `auto`, not `0`**, so one long word makes its track wider
  than its share and the whole layout overflows instead of wrapping. The base template sets
  `min-width:0` on the grid children it owns; a new grid needs the same.
- **Inline `code` needs `overflow-wrap:anywhere`**, or an unbreakable identifier overflows the
  column at 390px and takes the page with it.
- **`li::before` counts as a grid item.** A three-column `li` grid that also carries a counter
  pseudo-element wraps its fourth child onto a new row.

---

## 3a. Diagram engines: the comparison, and what was chosen

**The job, stated exactly.** A Python build script, on Windows 11, turns a fenced text block into
**inline SVG at build time**, with no service to run, no Node, no Docker, no CDN and no runtime
script in the delivered file. The SVG then has to be re-colorable onto the house tokens, because a
diagram that ignores the theme toggle is a white rectangle in a dark document.

**How the comparison was made.** A research pass over the candidates, the GitHub API for stars,
license and last push on one day, and then an install and a render of the two finalists. The two
the table rejects on installability were rejected against the sentence above, not in general:
Mermaid in particular is excellent and simply needs Node.

| Engine | Installs locally on Windows with no service | SVG at build time | Styleable with the house tokens | License | Activity (read September 2026) | Verdict |
|---|---|---|---|---|---|---|
| **D2** ([d2lang/d2](https://github.com/d2lang/d2)) | **Yes.** One Go binary. `winget install Terrastruct.D2`, or the windows-amd64 tarball unpacked anywhere | **Yes.** `d2 in.d2 out.svg`, plus `--no-xml-tag`, `--bundle=false`, `--salt` and `--omit-version`, which are exactly the flags an inline embed wants | **Good.** Theme-slot classes (`fill-B5`, `stroke-B1`, `fill-N2`) on every shape, and the palette rides in presentation attributes, which any stylesheet rule outranks | MPL-2.0 | 25,469 stars, pushed 2026-09-15, v0.9.0 released 2026-09-07 | **CHOSEN** for `flowchart` and `sequence` |
| **Graphviz** ([graphviz.org](https://graphviz.org/download/), source on [GitLab](https://gitlab.com/graphviz/graphviz)) | **Yes.** `winget install Graphviz.Graphviz`, or the `windows_10_cmake_Release` zip plus one `dot -c` | **Yes.** `dot -Tsvg` reads stdin and writes stdout | **Excellent.** `class="node"`, `class="edge"`, `class="graph"` on real groups, text stays text | EPL-2.0 | 16.1.0, released 2026-09-04; docs and Windows downloads updated through 2026 | **CHOSEN** for `mindmap` (twopi) and `tree` (dot) |
| **Mermaid** ([mermaid-js/mermaid](https://github.com/mermaid-js/mermaid)) | **No, for this job.** The renderer is JavaScript; `mmdc` needs Node and drives a headless browser | Yes, once Node is accepted | Very good: semantic classes and themable CSS variables | MIT | 90,307 stars, pushed 2026-09-18 | Rejected on the no-Node constraint only. The best native coverage of mind maps and state machines if that constraint is ever lifted |
| **Excalidraw** ([excalidraw/excalidraw](https://github.com/excalidraw/excalidraw)) | **No.** A browser application; local export needs npm and a headless browser | Only through the Node exporter | **Poor.** Its SVG is an illustration, not a semantic node-and-edge document; ids carry no stable meaning | MIT | 132,447 stars, pushed 2026-09-19 | Rejected. A whiteboard, not a text-to-diagram engine |
| **Kroki** ([yuzutech/kroki](https://github.com/yuzutech/kroki)) | **No.** It is an HTTP service in front of other engines; self-hosting means running the server | Only through a request to that service | Whatever the chosen backend produces; it defines no styling model of its own | AGPL-3.0 (its own code) | 4,338 stars, pushed 2026-09-19 | Rejected on the no-service constraint, which is the whole point of the job |
| **Penrose** ([penrose/penrose](https://github.com/penrose/penrose)) | **No.** A TypeScript platform; the normal path is npm | Yes, after installing its toolchain | Styling is upstream in its Style program rather than after the fact | MIT | 7,981 stars, pushed 2026-08-31 | Rejected. Built for constraint-based mathematical figures, not ordinary flowcharts |

**Why two engines rather than one.** D2 has a native sequence-diagram shape and Graphviz does not;
Graphviz has a radial layout that makes a real mind map and D2 does not. One engine for both jobs
would have meant drawing one of them badly. Both are a single local executable, so the second one
costs a download, not an architecture.

**What the builder does with the output** (`build.py`, the diagrams section):

1. Runs the engine into a temporary directory. Nothing is fetched and nothing is cached.
2. Strips the standalone wrapper: the XML declaration, the doctype, the generator comment, and the
   **embedded base64 web fonts**, about 7 KB per diagram, on a file somebody forwards by hand.
3. Namespaces every id in the drawing with that block's own prefix. Graphviz names its groups
   `graph0`, `node1`, `edge1` in every drawing it makes, so two on one page is a dozen duplicate ids.
4. Drops the engine's fixed `width`/`height` and keeps the `viewBox`, so the figure fits the
   reading column and scales on a phone.
5. Re-colors it with **CSS over presentation attributes**, never by rewriting geometry. That is
   what makes the theme toggle re-color a diagram live, and what stops a future engine version
   drifting the palette back.

**The gate.** `lint.py` refuses an `<img>` the file does not carry, a remote frame, a diagram or
chart library loaded by filename, an unrendered `class="mermaid"` element, and a mermaid runtime
initializer. Prose that merely names these engines is fine, which is what lets this section exist.

---

## 4. Interactivity rules (the measured gap)

The inventory found 150 of 186 pages with no interactive element at all. These are now rules, not
options.

1. **Any table or list of data ships with filtering and sorting.** A filter input above it, sortable
   headers on every column worth sorting. `lint.py` warns on a data table with no sortable header.
   The Key links table and a two-row facts table are not data tables; a table of rows a reader will
   scan, compare or search is.
2. **Any number the reader might play with ships as an input or a slider.** A cost, a rate, a count,
   a timeline length. Not a static figure with the assumption in a footnote.
3. **State persists in `localStorage`, keyed per page.** The filter text, the sort column, the
   checklist ticks, the slider positions, the chosen width and the theme. A reader who scrolls away
   and comes back finds the page as they left it. Wrap every read and write in `try/catch`: a
   private window throws.
4. **Everything is keyboard reachable.** Sortable headers take `role="button"` and `tabindex="0"`
   and respond to Enter and Space. Grips respond to the arrow keys. Every focusable element has a
   visible focus ring.
5. **Nothing needs a network.** No CDN, no font host, no analytics, no API. The file must work when
   someone opens it from a chat message on a plane. All CSS and JS inline, images as `data:` URIs.
6. **Debounce any live filter at about 140ms.** Filtering 800 nodes on every keystroke is its own
   freeze.
7. **One authored motion moment per page**, eased out from an already-visible default. Never an
   identical entrance animation on every section.

---

## 5. Performance

**Any page holding more than roughly 150 repeated blocks must be built so the browser only does
layout work for what is on screen.** An 808-block page once locked up a top-of-the-line machine for
close to a minute on scroll.

```css
.row, table.dt tbody tr { content-visibility: auto; contain-intrinsic-size: auto 42px; }
@media print { .row, table.dt tbody tr { content-visibility: visible } }
```

Measured on the same file: scroll operations went from a multi-second freeze to under 1 millisecond
with identical content and a working search. The rest of the discipline: keep per-block markup cheap
(flex containers, borders and pseudo-elements are paid once per block), pick the format by size
before writing a line, and for a true bulk record that someone will grep or import, ship markdown
and CSV alongside the HTML rather than pretending one file serves everyone.

**Verify it, do not assume it.** Scroll to the middle and the end of any long page and time the
layout before delivering.

---

## 6. Audience rules

- **Client builds carry NO presenter-side notes.** Speaker notes, internal margin math, your own
  framing and any "what to say here" line never ship in a client-facing file.
- **The private twin is a named surface.** A page that has presenter-side content ships as TWO
  files: the shareable one, and a private twin beside it carrying the notes, the margins and the
  framing. The twin is marked private in BOTH the eyebrow and the foot so a glance at any part of
  it says so, and it is never published. Naming: `<slug>-call-agenda.html` for the client,
  `<slug>-call-presenter-notes.html` for you. Build the twin at the same time as the page, not
  afterwards: a retrofit re-derives judgment already made and risks the notes landing in the
  shared copy.
- **The wall greps, now mechanical.** `lint.py --audience external` reads the whole file against
  `wall-list.txt` and refuses it (Client-safe by construction, section 1). The judgment that is
  still a human's: the numbers and internal terms that are not names. One company's document
  carries nothing from another's, and a document for a jointly-owned entity carries nothing from
  the ventures that are not part of it.
- **No terminal commands in the visible prose of a reader-facing deliverable.** Most readers do not
  run commands. Say what the capability does in plain English, or show the output itself, never the
  invocation. `lint.py` greps the finished file for `python `, `.py`, `npm ` and `git `.
- **Engineering units are not the headline.** Pull-request counts, migrations applied and
  capabilities shipped mean nothing as summary numbers. Lead with what changed FOR THE READER in
  their own vocabulary, shown visually.
- **Know the viewer's motive before choosing columns and colors.** Cut or demote any field the
  viewer will not act on, and give that width to what they will.
- **A page for a partner or a client is COMPOSED, never poured.** Over about 2,000 words,
  `build.py` is the wrong tool: it turns a markdown record into one uniform card per heading, top
  to bottom, which is right for a record you read yourself and flat for anyone else.
  Compose it by hand from the gallery instead: a one-screen executive summary, a summary strip at
  the top of every part, the questions for the reader in their own colored block, the detail
  folded under the summaries. **Words are a budget:** state the reader's reading time on the cover
  and aim under about ten minutes for the summaries, with the long form living in the markdown
  twin and linked once.
- **A page that replies to a document the counterpart designed speaks his visual language.** Read
  his file first and carry his legend, his cards, his chips and his section order into the reply,
  so the two read as one conversation. The house tokens still govern color and type underneath; a
  color his legend needs that the house has no token for is added as a TOKEN pair in both themes,
  never as a raw hex inside a component.
- **`lint.py` enforces the first of those two.** Over 3,000 prose words it requires a summary block
  at the top of every long section and at least one block that uses color to mark meaning. Missing
  either is a warning, and a refusal when `--audience external` is set.

---

## 7. Punctuation and prose

- **No em dashes anywhere in the file**, in the body copy, the CSS comments or the JavaScript. Both
  the raw character and the entity forms (`&mdash;`, `&#8212;`, `&#x2014;`) are refused. The entity
  forms slipped past the lint twice, which is why they are now checked explicitly.
- **No mid dots.** `·`, `&middot;`, `&#183;` and `&#xb7;` are all refused. Any enumeration of two or
  more items is a real `<ul>` or `<ol>`, nested under its parent `<li>` when it belongs to a bullet,
  never one line joined with separator characters.
- **American English.** Center, behavior, organize. Normalize before delivery.
- **Real content, never lorem.** Real names, real copy, real links, real numbers read from the
  database, the repo or the live system.
- **Every referenced destination is a real, working, copy-pasteable URL**, deep-linked to the exact
  screen, verified before sending. A 404 inside a live-claim is worse than no link.
- **Numbers agree across every surface of the document.** Before summing a table into a headline,
  dedupe the underlying entities; list every figure that appears twice and verify each pair matches.

---

## 8. Verification before delivery

1. `python lint.py <file.html> --playwright` (add `--money` for anything client-facing). It
   renders at 1440 and 1920 and fails on horizontal overflow.
2. Screenshot at **1440, 1920 and 390** and actually look at them: wrapped dates, dead columns,
   overlap, alignment, the nav present, the grips reachable, the theme correct.
3. Click every interactive control. A filter that does not filter is worse than no filter.
4. Read the rendered page, not the source.
5. `document.scrollWidth <= window.innerWidth` at every width.

---

## 9. What the inventory measured

186 HTML files built over two months across four repositories, measured mechanically for every
design fact. The finding:

| Fact | Measurement |
|---|---|
| Reading width | **26 distinct values** across the 163 files whose width is readable, from 660px to 1500px. 72 sit at 1000px, 26 are still on the retired 860px |
| Background | 104 tint, 43 flat, 39 carrying the 28px graph-paper grid |
| Section nav | 68 files have **none**; 42 use the banned native smooth scroll; 77 use the rAF ease (one file has both) |
| Width handles | **0 files.** The 20 that appeared to have them were reading a hosting shell's own injected grips. No on-disk deliverable had them |
| Theme | 102 light-default, 54 with no toggle at all, 30 still auto-switching on `prefers-color-scheme` |
| Print block | 44 files have none |
| Interactivity | **150 of 186 carry none.** 11 have a filter, 11 a sort, 6 a slider, 6 a calculator, 2 a checklist, 1 a drag-rank |
| Punctuation | 43 files carry a mid dot, including one with 103 in entity form; 3 carry an em dash |

**Where the best pieces lived.** One set of agenda pages carried the only working ROI calculator
(slider plus number input plus three live stat cards). One set of call and plan pages carried the
grid ground, the rAF nav and the computed-age labels. One set of mockups carried the only
filter-and-sort tables. One training guide carried the emoji-anchored visual register. Not one file
carried more than three of those at once, and no file carried all of them.

**Where the regressions happened.** Every automated report in the last five weeks of the window,
built by one-off scripts, converged on the same reduced page: 1000px, flat ground, rAF nav, print
block, and **zero interactive elements** even where the content is a table a reader would want to
sort. One of them had thirty tables and a text input but no sort. That is the whole regression, and
it has one cause: those pages were built by scripts that each re-implemented the house style from
an older copy instead of calling the skill.

---

## 10. Sharing and publishing: the game plan

### (a) File types

| Format | When it is right | Why |
|---|---|---|
| **HTML** (the default) | a chat message, an email, anything read on a phone or a laptop | self-contained, opens anywhere with no app, keeps the nav, the filters, the sliders and the theme toggle, and stays under a few hundred KB. It is the only format that keeps a document interactive |
| **PDF** | print, signature, a reader who genuinely cannot open an HTML attachment, and any document going into a records file | fixed pagination, universally previewable inline on a phone, and the format a signature block belongs in. Produced from the SAME HTML through Playwright's print path, so there is one source and the print block is exercised: `python lint.py <file.html> --pdf`. No new dependency: Playwright is already installed for the render check |
| **Markdown** | machine-read records only | the records another program reads: logs, indexes, notes a tool parses. A person reads a document in a browser, not in an editor |
| **CSV** | alongside the HTML for a true bulk record | someone will want to sort it in Excel or import it |

**Not worth adopting, and why.** **docx** costs a converter and a template to maintain, loses every
interactive element, renders differently in Word, Pages and Google Docs, and is only genuinely
needed when a counterparty will redline the text; when that day comes the answer is to write that
one document in Google Docs, not to make Word a format this skill produces. **A hosted notes
platform** would put a deliverable behind a login on a service the reader may not use, and such a
page cannot be dragged into a chat message.

### (b) Local versus live

**The rule: a page meant for another person gets a live copy in the same session that builds it.**
The local file stays the record; the live copy is what the other person opens.

Three clauses:

1. A page built for a named person who has a place to read it (a shared workspace, a document
   library, a client portal) is published there in the same session, before the message that
   carries it is drafted.
2. The message carries **both** the live link and the file, because the link is what stays current
   and the file is what survives a revoked token.
3. **Private pages stay local.** Nothing private is published to a shared surface.

The mechanism is yours: this skill produces a self-contained file, which is exactly what a static
host, a document library or a workspace artifact wants. `serve.py` covers the case where you want
the page live on your own screen while you edit it.

### (c) The decisions the author owns

1. **The default look for your own documents.** Tint is a cool, modern reading surface; classic is
   a formal report. Pick one and put it in your own copy of this file.
2. **The reading width.** 1080px on tint and 1000px on classic are the shipped defaults; the
   handles let any reader move it anyway, and a saved width wins for that reader only.
3. **Live copies by default for shared pages.** A document a partner cannot open in their own rail
   is a document they do not read.
4. **The PDF export path through the print block.** No new dependency, one source of truth, and it
   exercises the print CSS every page already carries. The alternative, a dedicated PDF library,
   means a second layout engine and a second set of bugs.

---

## 11. Large documents

The correction that produced this section, on a 38-section audit page: the 38 content items made
the right-side nav unusable, the page had to be zoomed out to 50 percent or less to see the whole
rail, and a part heading sat strangely at the very bottom of the section before it.

Both defects came from one place: the builder split the document on level-2 headings only. The
source wrote its six parts as level-1 headings, so every part heading stayed inside the previous
section's body, and the nav listed all 38 sections flat. **Measured: the rail rendered 1394px tall
inside a 900px viewport at 1440x900**, top and bottom both off screen.

### When this applies

Any document with more than about twelve sections: an audit, a long record, a research brief, a
triage of many threads. Below that a page stays flat, because grouping four sections is ceremony.

### What the author writes

A **part** is a level-1 heading in the body of the markdown (the first `# ` line is still the
document title). Sections are level-2 headings as before:

```markdown
# The document title

# 1. The inbox, seen whole
One sentence introducing the part.

## What this read covers
Body copy.
```

### What the builder does on its own

1. **A part heading opens its own block.** `.part-head` sits on the page ground, carries its
   number and its one-line intro, and the sections it introduces follow as their own cards. A part
   heading is never rendered inside a section card.
2. **Headings step down**: part is `h2.part-title` at 1.95rem, section is `h3.sec-title` at
   1.5rem, sub-section is `h4` at 1.12rem. In a grouped document the content's own `###` headings
   are demoted one level so nothing collides. A flat document keeps the sizes it has always had.
3. **Sections are numbered within their part** (`2.4`), so the number says where the reader is.
4. **The rail goes two-level.** The parts are the top level; only the part the reader is in lists
   its sections, and it opens and closes as the reader scrolls. The rail caps itself at
   `max-height: calc(100vh - 28px)` with a quiet scrollbar as the backstop, keeps the active entry
   in view, and keeps the rAF ease, the IntersectionObserver highlight, the 1200px cut-off and the
   print block exactly as before.
5. **The contents block follows the same tree**: each part is a row with its sections indented
   under it, never a flat wall of forty chips.
6. **A document with more than twelve top-level entries and no parts of its own is grouped
   automatically**, in chunks labeled by the range they cover ("Sections 9 to 16"). The label
   states a fact about position and nothing else, because a group name nobody wrote is a name
   nobody can trust. It exists so a page author cannot produce an unusable rail by accident; the
   right answer is still to write the parts.

### What the lint refuses

| Check | Verdict |
|---|---|
| The rendered nav is taller than the viewport at 1440x900 | **FAIL** (needs `--playwright`; only the render can see it) |
| A heading is the last thing in its section card | **FAIL** |
| A heading has no content before the next heading of the same or a higher level | **FAIL** |
| A part head introduces nothing (no section follows it) | **FAIL** |
| More than twelve TOP-LEVEL nav entries (a collapsed group counts as one) | **WARN** |

A rule in prose is not what stops this recurring; the lint is.

---

*Companion files: `SKILL.md` (when and what), `components.html` (the live gallery), `template.html`
(the base), `templates/<surface>.html` (the four surfaces), `build.py` (the one-command build),
`lint.py` (the gate). When somebody corrects an HTML deliverable, fold the delta into THIS file in
the same session, rebuild the gallery, and add a test for it.*
