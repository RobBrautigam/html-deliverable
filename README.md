# html-deliverable

**Build polished, standalone HTML documents from markdown, CSV or JSON.** One command to build,
one command to check, and a mandatory lint that refuses the twenty-odd ways a generated document
usually embarrasses you. A Claude Code skill, and a plain Python toolchain underneath it.

**Version 1.1.0**, MIT licensed, Python 3.12 or newer. [What changed](CHANGELOG.md).

<p align="center">
  <img src="examples/sample-report-classic-1440.png" alt="A built report in the classic look at 1440px" width="100%" />
</p>

Markdown is good for the writer. HTML is good for the reader: it keeps the layout, the filters,
the sliders and the theme toggle, it opens anywhere with no app, and it still works when somebody
drags it into a chat message on a plane. This is the toolchain that turns the first into the
second without a design decision per document.

---

## Quick start (one minute, from a clean clone)

```bash
git clone https://github.com/RobBrautigam/html-deliverable.git
cd html-deliverable

# the only dependency, and only for markdown input
pip install markdown

# build the example report, then check it
python skills/html-deliverable/build.py examples/sample-report.md out.html \
  --verdict "Revenue is 24 percent above plan; one decision is open."
python skills/html-deliverable/lint.py out.html
```

The lint prints `PASS` and the path. Open `out.html` in any browser: it is the report in the
screenshot above with a plainer cover (the screenshot's build also passed the eyebrow, the lede,
who it is for and from, and the three headline numbers as flags), and the right-side nav, the theme toggle, the
sortable table and the workflow figure all work from one file, with nothing to install.

For your own notes, swap in your markdown, CSV or JSON, and add the render check once Playwright
is installed:

```bash
python skills/html-deliverable/build.py notes.md report.html --surface report \
  --title "The first quarter" --verdict "Revenue is above plan; one decision is open."
python skills/html-deliverable/lint.py report.html --playwright --money
```

[`examples/sample-report.md`](examples/sample-report.md) is the example's source, and
[`examples/sample-report.html`](examples/sample-report.html) is what the build produced with the
flags its cover shows; it passes the lint at 1440 and 390 in both themes.

## Install it as a Claude Code skill

**As a plugin** (Claude Code's plugin marketplace, so updates arrive with one command):

```
/plugin marketplace add RobBrautigam/html-deliverable
/plugin install html-deliverable@html-deliverable
```

**Or copy the skill folder** into your personal skills:

```bash
cp -R skills/html-deliverable ~/.claude/skills/
```

Then ask any Claude Code session for an HTML report, a one-pager or a formatted document, and the
skill fires on its own description.

**Or send this to your agent**, and let it do the install and the first build:

```
Install the html-deliverable skill from https://github.com/RobBrautigam/html-deliverable:
clone it, copy skills/html-deliverable into my personal skills folder, and run
`pip install markdown`. Then read its SKILL.md and DESIGN.md, build examples/sample-report.md
with build.py, run lint.py on the result, and tell me what the lint said.
```

**Requirements:** Python 3.12 or newer, the `markdown` package for markdown input (CSV and JSON
need nothing), and, for the render check, Playwright (`pip install playwright && playwright
install chromium`, or a Node `playwright` the lint can find). Two optional diagram engines, d2 and
Graphviz, are only needed if a document uses `[diagram:]` blocks; the builder names the install
command when one is missing.

---

## What's new in 1.1.0

The full list is in [CHANGELOG.md](CHANGELOG.md). The ones a reader notices:

- **Printing keeps what reads as one thing whole.** Folds print open, sort arrows stay off the
  paper, a callout or a figure is never split across two pages, a heading never sits alone at a
  page foot, and a short table prints on one page.
- **Reduced motion is honored**, and **selected text reads on every block**, including inside a
  tinted callout, where it used to vanish.
- **A page never names the local file it was built from.** `--source` names the record instead.
- **The lint reads inside `data:` URIs** for the wall list, refuses a text selection that cannot
  be read, refuses a workflow node with an undefined color, and warns on motion with no
  reduced-motion block.

---

## Why it exists

Generated HTML documents rot in a specific way. Each new one is built from a copy of the last one
rather than from a design system, so the look drifts backwards, and the checks nobody remembers to
run are the ones that catch the embarrassing defects.

A measured inventory of 186 documents built over two months, all by the same automation, found:

| Fact | Measurement |
|---|---|
| Reading width | **26 distinct values**, from 660px to 1500px |
| Section nav | **68 files had none**; 42 used a smooth scroll that silently jumps under reduced motion |
| Interactivity | **150 of 186 carried none at all**, including pages whose content is a table a reader would want to sort |
| Theme | 54 had no toggle; 30 switched to dark on the reader's OS setting, unasked |
| Print block | 44 had none, on documents that get printed |
| Punctuation | 43 carried a mid dot, one of them 103 times in entity form |

Every one of those is now either impossible (the builder does it) or refused (the lint fails the
file). That is the whole idea: **a page that has not been linted has not been checked.**

---

## What you get

### Four surfaces, one house style

Pick one before writing a line. The palette, the type, the theme toggle, the right-side nav and
the print block are identical across all four: only the structure changes.

| Surface | Use it for |
|---|---|
| **report** (the default) | anything somebody reads: a status report, an audit, a research brief, a decision pack |
| **deck** | a call document: an agenda you screen-share that keeps working after the call |
| **poster** | a client one-pager: hero, three numbers, problem to solution, one call to action |
| **data-report** | a numbers page from a CSV or a JSON export: KPI cards, charts, the table, the method |

### Two looks, one attribute

<p align="center">
  <img src="examples/sample-report-tint-1440.png" alt="The same report in the tint look at 1440px" width="100%" />
</p>

The same document above, in the tint look. The look is one attribute on `<html>`; nothing else
changes between them. Classic is a warm, formal report; tint is a cooler reading surface on 28px
graph paper. Both ship light by default with a dark toggle, and both read the same design tokens,
so a look change is one attribute rather than a rewrite.

### A gallery that is the source, not a picture of it

<p align="center">
  <img src="examples/gallery-1440.png" alt="The components gallery at 1440px" width="100%" />
</p>

`components.html` is generated from the same catalogue the builder imports, so a component's demo
and its copy-paste snippet are the same text by construction. Thirty-three components: stat rows,
status chips, verdict and warn boxes, part summary strips with fold-outs, a questions block, a
lane-and-column workflow map, four diagram kinds, facts grids, key-link tables, a grouped bar, a
filterable sortable table, a line chart with a crosshair readout, sliders, an ROI calculator, a
drag-rank list, a checklist, a decision list with a copy-out block, a run-of-show, a timeline, a
comparison, a problem-to-solution block, a countdown, and the four every page carries.

Open it in a browser before building anything non-trivial.

### A lint that refuses, rather than a style guide nobody reads

```bash
python lint.py out.html --playwright --money --widths 1440,1920,390
python lint.py out.html --audience external --allow "Acme"
```

- **The wall list.** No company or client name the page was not given, read over the WHOLE file:
  the visible words, the attributes, the comments and the stylesheet. On an external page it is a
  refusal. This exists because a one-pager built from a house template once carried another
  client's short name in a CSS selector and a third company's name in a comment, invisible on the
  page and one find-in-page away from the reader.
- **No value may leave its box.** A `white-space: nowrap` value too long for its card spills
  INSIDE a page that does not overflow at all, so the page-level check passes and the reader still
  sees a number running out of its box. The render measures every element a value can sit in, at
  every width and in both themes. Proved by inversion on a pair of fixtures that differ in exactly
  one CSS declaration.
- **Figures are measured, not looked at.** Seven refusals, each proved by a fixture that breaks
  exactly that rule: text outside the box it belongs to, a label painted under a shape that covers
  it, a connector routed through a node, two boxes on top of each other, a tag over somebody
  else's box, a figure that drew nothing, and a figure wider than its column.
- **Every dollar amount carries a dollar sign**, in prose, in tables, in cards and inside a
  figure's JSON block. Three ways an amount loses its sign, three arms, three fixtures.
- **The flat page.** Over about 3,000 prose words, every long section must open with a summary
  block and the page must use color to mark meaning. Missing either half is the hit.
- **Selected text has to read.** The page's own text selection is measured against every block
  its body text sits on, in Light and Dark, by WCAG contrast; a highlight that vanishes inside a
  tinted callout is refused.
- **Hidden payloads are read too.** The wall list runs inside every base64 or percent-encoded
  `data:` URI, so a company name inside an embedded SVG is caught like one in the prose.
- **Motion the reader cannot turn down** is named: an animation or transition with no
  `prefers-reduced-motion` block, or a transition on `all`, is a warning.
- Plus: em dashes and mid dots (raw and entity), terminal commands in reader-facing prose, a
  missing Key links table, an external link that does not open in a new tab, a missing section nav
  or width handles, a dark default, an external script or font, a leftover `REPLACE`, a `<ul>`
  inside a `<p>`, a nav taller than the viewport, a stranded heading, a tab title that disagrees
  with the page's own `<h1>`, literal `**` left in a verdict or a callout, and a workflow node
  colored with a tone the page never defines.

### Tested, including in a real browser

```bash
python -m pytest skills/html-deliverable
```

**466 tests.** They cover the builder, the lint, the design system, the diagram engines, the
figure gates, the large-document rules, the print rules and the page contract. Fifty of them
drive a headless browser: they click every filter, sort every table, drag the width handles, hover
the chart crosshair, flip the theme, drive a page inside a frame, print real pages to PDF and read
them back page by page, and measure the rendered geometry. Without Playwright those fifty SKIP
with a named reason rather than passing quietly, and the other 416 still run.

Thirty-two of the fifty drive the page through Node rather than Python. They find a Node
`playwright` module in the usual `node_modules` folders, or wherever `PLAYWRIGHT_NODE_ROOT`
points, and SKIP with that instruction when there is none. The print tests also need `pypdf`
(`pip install pypdf`) to read the printed pages back.

---

## What is in the box

```
html-deliverable/
├── README.md                    ← you are here
├── CHANGELOG.md                 ← what changed, version by version
├── LICENSE                      ← MIT
├── .claude-plugin/
│   ├── plugin.json              ← the Claude Code plugin manifest
│   └── marketplace.json         ← lets `/plugin marketplace add` install it
├── examples/
│   ├── sample-report.md         ← the source
│   ├── sample-report.html       ← what the build produced, lint-clean
│   └── *.png                    ← the screenshots above
└── skills/html-deliverable/
    ├── SKILL.md                 ← when to build one, and what goes in it
    ├── DESIGN.md                ← the authority on how a page LOOKS
    ├── components.html          ← the live gallery, generated
    ├── template.html            ← the house base: tokens, nav, handles, print, frame contract
    ├── templates/               ← the four surface modules
    ├── build.py                 ← markdown, CSV or JSON in, one HTML file out
    ├── lint.py                  ← the pre-delivery gate
    ├── selection_contrast.py    ← measures whether selected text reads on every block
    ├── build_gallery.py         ← the component catalogue, and the gallery it generates
    ├── serve.py                 ← local HTTP so the page live-reloads while you edit it
    ├── interactions.js          ← drives every interactive piece in a real browser
    ├── chartcheck.js            ← drives the line chart and reports what was drawn
    ├── domcheck.js              ← duplicate ids and leaked source, from the parsed DOM
    ├── wall-list.txt            ← the names a delivered page may never carry
    ├── fixtures/                ← the inversion proofs: one file per rule, each breaking it
    └── test_*.py                ← 466 tests
```

---

## Making it yours

Three files carry everything you would want to change:

1. **`wall-list.txt`** ships two fictional names. Replace them with your own companies, products
   and clients, one per line. That is the whole configuration of the leak check.
2. **`template.html`** carries the palette as CSS custom properties at the top of its `<style>`
   block, in five theme blocks. Change the accent pair and every component follows, because no
   component carries a raw hex value and a test enforces that.
3. **`DESIGN.md`** is prose you own. When somebody corrects a document you produced, fold the
   correction into that file in the same session, add the component to `build_gallery.py`, rebuild
   the gallery, and write the test. That loop is why the toolchain has 466 tests and not twelve.

A client build wears the client's own colors, which is one line overriding `--acc` on the page,
never a change to the design system.

---

## Help and updates

- **Something broke, or the lint refused a page you think is right?** Open an issue with the
  lint's output and the smallest input that reproduces it:
  [github.com/RobBrautigam/html-deliverable/issues](https://github.com/RobBrautigam/html-deliverable/issues).
- **Staying current:** installed as a plugin, run `claude plugin update
  html-deliverable@html-deliverable` in your shell, or choose **Update now** on the plugin in the
  **Installed** tab of `/plugin` (auto-update is off by default for a marketplace like this one,
  and the same tab turns it on). A copied folder updates with `git pull` and a fresh copy. Every
  release is listed in [CHANGELOG.md](CHANGELOG.md).

---

## Credits

The surface idea (choose the shape of the document before writing a line, and let the surface lock
the structure so the model cannot freestyle the layout) was taken from
[nexu-io/html-anything](https://github.com/nexu-io/html-anything), along with one hard-won
technical lesson: a responsive chart whose parent has no explicit height enters a ResizeObserver
feedback loop and grows until the tab hangs. None of its look ships here, and the surfaces are
deliberately different: this repository's deck is a call document rather than a swipe deck, and
its poster is a one-pager somebody reads on a laptop and prints rather than a social image.

The diagram engines are [d2](https://github.com/d2lang/d2) (MPL-2.0) and
[Graphviz](https://graphviz.org/) (EPL-2.0), both run locally at build time. `DESIGN.md`
section 3a carries the comparison that chose them over Mermaid, Excalidraw, Kroki and Penrose,
with the constraint each was measured against.

---

## License

MIT. Use it, fork it, change anything. See [LICENSE](LICENSE).
