# Changelog

Every change that reaches a reader or an author, newest first. The version lives in
`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, and the two always agree.

## 1.1.0 (2026-11-02)

What two more months of building real documents with this toolchain taught it.

### Pages

- **Printing keeps what reads as one thing whole.** Every fold prints open with its marker gone,
  and sort arrows no longer print as stray glyphs. A callout, a summary strip, a figure, a stat
  card or a table row is never split across two pages; a heading never sits alone at a page foot;
  a table of twelve body rows or fewer prints on one page, while a longer one starts where it
  falls. A `beforeprint` handler opens closed folds for browsers without `::details-content`.
- **Reduced motion is honored.** Under `prefers-reduced-motion: reduce` a page keeps its fades and
  color changes and drops the travel (the nav's slide, the tooltip's rise, the chevron's turn, the
  chart readout, the drag lift, the bar's growth).
- **Selected text reads on every block.** The selection is the ink inverted, so a highlight inside
  a tinted callout or a code block no longer vanishes into the block's own color.
- **A page never names the local file it was built from.** The footer, the method note, the lede
  and the data report's Source line used to print the input's file name. `--source` now names
  the record a page was read from; with no `--source` the Source line is removed.

### The builder

- A `[table: ...]` hint written directly above its table, or directly under a line of prose,
  still binds to that table instead of joining the paragraph as text.
- A bare URL inside a code fence (backticks or tildes, any length) is left bare, so a paste-ready
  block keeps its addresses as written; an inline code span was already skipped.
- `--verdict` and the verdict box render markdown `**bold**` as real bold.
- A harvested Key links URL with `&` in its query string is decoded once before it is escaped, so
  it is never double-escaped.

### The lint

- **The wall list is read inside every `data:` URI**, base64 or percent encoded, and inside one
  nested in another, so a name hidden in an embedded SVG or a text export is caught.
- **A selection that cannot be read is refused**, measured against every block the body text reads
  on in Light and Dark mode (`selection_contrast.py`, WCAG contrast).
- **A flow node tone with no `-soft` and `-ink` pair is refused**: it rendered as an unstyled box.
  The example report carried one, and now uses a defined tone.
- **Literal `**` inside a verdict or a callout is refused**, outside code.
- **Motion with no reduced-motion block is a warning**, and so is a transition on `all`.
- The assets proof reads the part-summary strip's class attribute, so the print block's selector
  is not mistaken for the component in use.

### Tests

- 466 tests, up from 350. Every new test file was run against the 1.0.0 code and fails there,
  so each one is known to measure its change.
- The page contract tests that drive a page through Node now SKIP with a named reason when no Node
  `playwright` module is found, instead of erroring; point `PLAYWRIGHT_NODE_ROOT` at a
  `node_modules` folder that holds one to run them.

## 1.0.0 (2026-09-21)

The first public cut: four surfaces (report, deck, poster, data report), two looks, a generated
gallery of thirty-three components, `build.py` for markdown, CSV and JSON, and `lint.py` as the
pre-delivery gate, with 348 tests. The same day: the figure gate stopped refusing every Graphviz
diagram and every chart (350 tests).
