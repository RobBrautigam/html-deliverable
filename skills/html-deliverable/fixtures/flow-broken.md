# The broken figure

A fixture, not a deliverable. Its figure is one that SHIPPED before the renderer was repaired,
extended with the one edge shape that produces the third defect: an edge that skips columns.

Three defects, all three measurable in a headless render:

1. The lane label `IT STARTS HELPERS` is longer than a fixed 92px gutter, so it runs into the
   node in column 0.
2. Text is wrapped at a CHARACTER count rather than a measured width, so `long-program-name-host`
   (one unbreakable 22-character token) is drawn wider than the box it sits in, and the note
   `1.6 GB IN 51 ORPHANS` is never wrapped or measured at all.
3. The edge from the session to the leak routes at the midpoint between its two boxes, which is
   the middle of the figure, so its horizontal run crosses the column 1 node and its vertical run
   crosses the column 3 node.

**The JSON below never changes.** The renderer is what gets repaired, and this same JSON has to
render clean afterwards, at every width and in both themes.

## The figure

<figure class="flow" aria-label="What one session puts on the machine">
  <script type="application/json" class="flow-data">
  {
    "title": "What one agent session puts on the machine",
    "caption": "Nine programs per session. The green step should end them all. The red one is where it failed.",
    "lanes": [
      {"id": "you", "label": "YOU RUN", "tone": "acc"},
      {"id": "helpers", "label": "IT STARTS HELPERS", "tone": "acc-2"},
      {"id": "after", "label": "WHEN IT ENDS", "tone": "violet"}
    ],
    "nodes": [
      {"id": "sess", "col": 0, "lane": "you", "label": "One agent session", "note": "SIX TODAY", "tone": "acc"},
      {"id": "pty", "col": 1, "lane": "you", "label": "Its own terminal host", "note": "PLUMBING", "tone": "acc"},
      {"id": "bridge", "col": 2, "lane": "helpers", "label": "long-program-name-host", "note": "TWICE", "tone": "amber"},
      {"id": "graph", "col": 3, "lane": "helpers", "label": "Code graph helper", "note": "5 PARTS", "tone": "amber"},
      {"id": "review", "col": 4, "lane": "helpers", "label": "Review helper tree", "note": "6 PARTS", "tone": "acc-2"},
      {"id": "clean", "col": 5, "lane": "after", "label": "The session closes", "note": "SHOULD TIDY UP", "tone": "green"},
      {"id": "left", "col": 6, "lane": "after", "label": "Review tree survives", "note": "1.6 GB IN 51 ORPHANS", "tone": "red"}
    ],
    "edges": [
      {"from": "sess", "to": "pty"},
      {"from": "pty", "to": "bridge"},
      {"from": "bridge", "to": "graph"},
      {"from": "graph", "to": "review"},
      {"from": "review", "to": "clean"},
      {"from": "clean", "to": "left", "tone": "red"},
      {"from": "sess", "to": "left", "tone": "red"}
    ],
    "marks": [
      {"node": "bridge", "label": "MH1"},
      {"node": "graph", "label": "MH1"}
    ]
  }
  </script>
</figure>

## Why it is here

A gate written from one observed instance tests the instance. This fixture carries all three
shapes at once so the gate is proved against each of them by inversion, and so a later change to
the renderer that reintroduces any one of them fails a test rather than reaching a page.
