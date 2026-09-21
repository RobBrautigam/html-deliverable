#!/usr/bin/env python3
"""Generate components.html: every house component, live, with its copy-paste source.

    python build_gallery.py [output.html]

The gallery is built FROM template.html, so it proves the base template works, and every
component's demo and its printed snippet are the same string by construction - a snippet can
never drift from what the page above it renders.

A component that needs no CSS or JS of its own says so: the base template already carries it.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "template.html"


class Component:
    """One house component: what it is for, and the exact source that produces it.

    `live_on_page` marks the four components the BASE TEMPLATE already puts on every page (the
    section nav, the theme toggle, the width handles, the print block). Rendering a second copy
    of those inside a demo box would duplicate `id="sidenav"` and `.grip` on one document, which
    is invalid HTML, breaks getElementById for whoever copies the page, and leaves dead controls
    that look broken because nothing wired them. For those the gallery prints the source and
    points at the live one instead.
    """

    def __init__(
        self, cid: str, title: str, when: str, markup: str,
        css: str = "", js: str = "", nav: str = "", live_on_page: str = "", group: str = "Components",
        diagram: tuple[str, str, str] | None = None,
    ):
        self.cid = cid
        self.title = title
        self.when = when
        # A DIAGRAM component has no hand-written markup: the builder renders it from the same
        # markdown an author writes, at gallery build time. `diagram` is (kind, caption, source),
        # and the snippet under the demo shows that markdown rather than the generated SVG,
        # because the markdown is the thing anyone would actually copy.
        self.diagram = diagram
        self.markup = markup.strip("\n")
        self.css = css.strip("\n")
        self.js = js.strip("\n")
        self.nav = nav or title
        self.live_on_page = live_on_page
        # The gallery is itself a large document, so it wears the large-document rail: the groups
        # are the top level and only the open one lists its components. A flat rail of two dozen
        # entries is the defect this pass exists to fix, and the gallery must not carry it.
        self.group = group


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def clip(label: str, limit: int = 22) -> str:
    """Nav labels cut on a word boundary, the same rule build.py uses.

    A long label widens the whole rail, and a rail wider than the gutter hides itself rather
    than covering the column, which is how the gallery lost its nav below 1920.
    """
    if len(label) <= limit:
        return label
    cut = label[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:") + "…"


# --------------------------------------------------------------------------- the catalogue

COMPONENTS: list[Component] = [
    Component(
        "part-head",
        "Part heading",
        "A large document groups its sections under PARTS. The part heading opens its own block on "
        "the page ground, directly above the sections it introduces, never as the last child of the "
        "card before it. In markdown it is a level-1 heading in the body; the "
        "builder does the rest, and the right-side rail lists the parts rather than every section. "
        "Sizes step down: part, section, sub-section.",
        """
<div class="part-head" id="claim-one">
  <div class="part-num">Part 2</div>
  <h2 class="part-title">Claim one: client-facing emails are switched off</h2>
  <p>Who said it, what the switches actually read tonight, and what turning them on would send tomorrow.</p>
</div>
<section id="the-evidence">
  <div class="sec-num">2.1</div>
  <h3 class="sec-title">The evidence</h3>
  <p>The section the part heading introduces sits immediately under it, on its own card.</p>
</section>
""",
        group="Structure",
    ),
    Component(
        "stat-row",
        "Stat card row",
        "The executive summary of any multi-section document. Three or four numbers, center-aligned "
        "so mixed-size figures do not stagger. Color is FOCUS: green money and act-now, red risk, "
        "amber caution, accent context volume.",
        """
<div class="hero-stats">
  <div class="stat g"><div class="num">$48,200</div><div class="lbl"><b>Open pipeline</b> - three deals waiting on a yes</div></div>
  <div class="stat n"><div class="num">186</div><div class="lbl"><b>Documents measured</b> - the whole corpus</div></div>
  <div class="stat a"><div class="num">12</div><div class="lbl"><b>Needs a decision</b> - listed in section 4</div></div>
  <div class="stat r"><div class="num">2</div><div class="lbl"><b>Past the date</b> - both chased today</div></div>
</div>
""",
        group="Structure",
    ),
    Component(
        "chips",
        "Status chips",
        "A state inside a table cell or a fact grid, never a sentence. Four families only.",
        """
<p>
  <span class="chip g">SHIPPED</span>
  <span class="chip a">WAITING</span>
  <span class="chip r">BLOCKED</span>
  <span class="chip n">BACKLOG</span>
</p>
""",
        group="Structure",
    ),
    Component(
        "boxes",
        "Verdict, warn and callout",
        "The verdict carries the one-line bottom-up answer. The warn carries the single real caveat, "
        "one per document. The callout is a highlighted aside inside a section.",
        """
<div class="verdict">
  <strong>&#10004; The short answer:</strong> the work is done and live; nothing is waiting on you tonight.
</div>
<div class="warn">
  <strong>&#9888; One caveat:</strong> the reading width is set to 1080px, which is a change from the standing 1000px. Section 4 explains it.
</div>
<div class="callout">A callout holds the sentence a reader would otherwise miss in the paragraph above it.</div>
""",
        group="Structure",
    ),
    Component(
        "part-summary",
        "Part summary strip, with the detail folded under it",
        "The cure for the flat page. Every part or stage of a long document for "
        "somebody else opens with three short lines: what is agreed, what changes, what is added. The "
        "reader who stops there has still read the reply. The argument, the tables and the evidence go "
        "under the fold-out below it, whose open state is remembered per page like the reading width "
        "and the theme. Use the neutral 'line' row when a card has one summary line rather than three. "
        "A partner-facing page over about 2,000 words is composed this way and never built flat from a "
        "long markdown; the lint warns when it is, and refuses an external page.",
        """
<div class="stage-summary">
  <div class="ss-row agree"><span class="ss-k">Agree</span><span class="ss-v">What they already have right, in one line. <b>Bold the crux, never the whole sentence.</b></span></div>
  <div class="ss-row change"><span class="ss-k">Change</span><span class="ss-v">What moves, and whose call it was.</span></div>
  <div class="ss-row add"><span class="ss-k">Add</span><span class="ss-v">What is new, and why it belongs in the same pass rather than a later one.</span></div>
</div>
<details class="fold" data-fold="demo-part">
  <summary>Read the full reasoning</summary>
  <div class="fold-body">
    <p>The argument, the evidence, the tables and the numbers live here. Nothing that a reader
       must see to answer a question belongs under a fold: the fold carries the reasoning, the
       summary above it carries the decision.</p>
  </div>
</details>
""",
        css="""
  /* ---- the part summary strip: three short lines at the top of a part ---- */
  .stage-summary{display:grid; gap:1px; background:var(--line); border:1px solid var(--line);
    border-radius:var(--radius-sm); overflow:hidden; margin:0 0 14px}
  .ss-row{display:grid; grid-template-columns:86px 1fr; gap:14px; background:var(--panel-2); padding:11px 14px}
  .ss-k{font:700 .68rem/1.5 var(--font-body); letter-spacing:.1em; text-transform:uppercase; padding-top:2px}
  .ss-row.agree .ss-k{color:var(--green-ink)}
  .ss-row.change .ss-k{color:var(--amber-ink)}
  .ss-row.add .ss-k{color:var(--acc)}
  .ss-row.done .ss-k{color:var(--green-ink)}
  .ss-row.line .ss-k{color:var(--muted)}
  .ss-v{font-size:.94rem}
  @media screen and (max-width:600px){
    .ss-row{grid-template-columns:1fr; gap:2px}
    .ss-k{padding-top:0}
  }
  /* ---- the fold-out under it ---- */
  details.fold{border:1px solid var(--line); border-radius:var(--radius-sm); background:var(--panel-2); margin:0}
  details.fold > summary{cursor:pointer; padding:10px 15px; font:700 .84rem/1.4 var(--font-body);
    color:var(--acc); list-style:none; border-radius:var(--radius-sm)}
  details.fold > summary::-webkit-details-marker{display:none}
  details.fold > summary::before{content:"\\203A"; display:inline-block; width:14px;
    transition:transform .15s; transform-origin:35% 50%}
  details.fold[open] > summary::before{transform:rotate(90deg)}
  details.fold > summary:hover{color:var(--acc-2)}
  details.fold > summary:focus-visible{outline:2px solid var(--acc); outline-offset:2px}
  .fold-body{padding:2px 18px 14px; border-top:1px solid var(--line); font-size:.95rem}
  .fold-body > :first-child{margin-top:12px}
  .fold-body h4{margin:16px 0 6px; font-family:var(--font-body); font-size:.94rem; font-weight:700}
  @media print{
    details.fold > summary{display:none}
    details.fold{border:none; background:none}
    details.fold::details-content{content-visibility:visible}
    .fold-body{border-top:none; padding-left:0; padding-right:0}
  }
""",
        js="""
  /* the fold-outs: open state remembered per page, and every fold opened for printing */
  (function(){
    var key0 = 'hd-fold-' + location.pathname.replace(/[^a-z0-9]+/gi,'-').slice(-60) + '-';
    var folds = [].slice.call(document.querySelectorAll('details.fold[data-fold]'));
    folds.forEach(function(fold){
      var key = key0 + fold.getAttribute('data-fold');
      try { if (localStorage.getItem(key) === '1') fold.open = true; } catch (e) {}
      fold.addEventListener('toggle', function(){
        try { localStorage.setItem(key, fold.open ? '1' : '0'); } catch (e) {}
      });
    });
    var opened = [];
    window.addEventListener('beforeprint', function(){
      opened = folds.filter(function(f){ return !f.open; });
      opened.forEach(function(f){ f.open = true; });
    });
    window.addEventListener('afterprint', function(){
      opened.forEach(function(f){ f.open = false; });
      opened = [];
    });
  })();
""",
        group="Structure",
    ),
    Component(
        "asks",
        "Questions for the reader, in their own colored block",
        "One color, one meaning: everything this color touches is a question the reader has to answer, "
        "and it is never used for anything else on the page. The block sits at the "
        "foot of the part it belongs to, the questions keep their numbering from the document's one "
        "list of questions, and each carries its recommendation on its own line, because the house "
        "question shape is the question, then the options, then the recommendation. The token family "
        "is declared beside the house ones so the block reads a token and never a raw color.",
        """
<div class="asks">
  <div class="asks-head">Questions for you</div>
  <ol start="7">
    <li>The question, in one sentence a reader can answer in a line.<span class="rec"><b>Recommendation:</b> what I would do, and the one-line reason.</span></li>
    <li>The second question, which never hides inside a paragraph.<span class="rec"><b>Why it is your call:</b> the thing only they know.</span></li>
  </ol>
</div>
""",
        css="""
  /* ---- the questions block. --ask is a house token family in template.html, beside
         --green, --amber and --red, because a component that defines its own colors is
         exactly the drift the design system exists to stop. ---- */
  .asks{background:var(--ask-soft); border:1px solid var(--ask); border-left:4px solid var(--ask);
    border-radius:var(--radius-sm); padding:14px 18px 12px; margin:0 0 14px}
  .asks-head{font:700 .7rem/1 var(--font-body); letter-spacing:.12em; text-transform:uppercase;
    color:var(--ask-ink); margin:0 0 9px}
  .asks ol{margin:0; padding-left:22px}
  .asks li{margin:7px 0; font-size:.95rem}
  .asks li::marker{color:var(--ask); font-weight:700}
  .asks .rec{display:block; font-size:.88rem; color:var(--muted); margin-top:3px}
  .asks .rec b{color:var(--ask-ink)}
  /* the two chips that go with it: solid, so they read as a different register from the
     soft house chips. --on-acc, never a raw white: the accent is light in dark mode. */
  .chip.q{background:var(--ask); color:var(--on-acc)}
  .chip.k{background:var(--green); color:var(--on-acc)}
""",
        group="Structure",
    ),
    Component(
        "flow",
        "The picture: a lane-and-column map of a whole path",
        "<b>Every page that explains a workflow, a system, a pipeline or a path opens its explanation "
        "with this</b>: one map of the whole thing, before any prose, so the reader "
        "sees the shape before the detail. Boxes are real things with their real names; the lanes are "
        "who or what acts; the arrows are the path. It is inline SVG drawn on the tokens, so it works "
        "in both themes, and below 760px the figure scrolls sideways rather than shrinking the labels "
        "to nothing. Everything lives in the JSON block inside the figure, so a change is a data edit "
        "and there is no hand-placed coordinate to go stale. A workflow page with no picture is not "
        "done.",
        """
<figure class="flow" aria-label="How a buyer reply becomes a live link">
  <script type="application/json" class="flow-data">
  {
    "title": "How a reply becomes a live link",
    "lanes": [
      {"id": "machine", "label": "MACHINE", "tone": "acc"},
      {"id": "us", "label": "US", "tone": "violet"},
      {"id": "buyer", "label": "BUYER", "tone": "acc-2"}
    ],
    "nodes": [
      {"id": "send", "col": 0, "lane": "machine", "label": "The email goes out", "note": "LIVE", "tone": "green"},
      {"id": "reply", "col": 1, "lane": "buyer", "label": "They reply", "note": "the ask", "tone": "acc-2"},
      {"id": "draft", "col": 2, "lane": "machine", "label": "The offer drafts itself", "note": "LIVE", "tone": "green"},
      {"id": "send2", "col": 3, "lane": "us", "label": "We click send", "note": "the gate", "tone": "violet"},
      {"id": "pick", "col": 4, "lane": "buyer", "label": "They pick and pay", "note": "email only", "tone": "amber"},
      {"id": "fill", "col": 5, "lane": "us", "label": "We fulfill it", "note": "by hand", "tone": "amber"},
      {"id": "live", "col": 6, "lane": "machine", "label": "The link is live", "note": "HOLE", "tone": "red"}
    ],
    "edges": [
      {"from": "send", "to": "reply"},
      {"from": "reply", "to": "draft"},
      {"from": "draft", "to": "send2"},
      {"from": "send2", "to": "pick"},
      {"from": "pick", "to": "fill"},
      {"from": "fill", "to": "live"}
    ],
    "marks": [
      {"node": "send2", "label": "Q3"},
      {"node": "pick", "label": "Q8"},
      {"node": "fill", "label": "Q11"}
    ]
  }
  </script>
</figure>
""",
        css="""
  /* ---- THE PICTURE: one map of the whole path, drawn from the JSON inside the figure ---- */
  figure.flow{--flow-min:680px; margin:14px 0 18px; padding:0}
  figure.flow svg{display:block; width:100%; height:auto}
  figure.flow .flow-cap{font-size:.8rem; color:var(--muted); margin-top:8px; text-align:center}
  /* The renderer writes data-flow-layout after it has measured its own container, and the CSS
     keys off THAT rather than off a media query, because a media query reads the viewport and
     the figure lives in a column. The two used to disagree at exactly the widths readers
     use. */
  @media screen and (max-width:760px){
    /* A map still laid out in lanes is wider than the screen on purpose: it scrolls. */
    figure.flow[data-flow-layout="lanes"]{overflow-x:auto; -webkit-overflow-scrolling:touch}
    figure.flow[data-flow-layout="lanes"] svg{min-width:var(--flow-min, 680px)}
    figure.flow[data-flow-layout="lanes"] .flow-cap::before{content:"Swipe the map sideways. "; color:var(--acc); font-weight:700}
  }
  /* One column under a phone width: it fits, so it neither scrolls nor says to swipe. */
  figure.flow[data-flow-layout="stack"]{overflow-x:visible}
  figure.flow[data-flow-layout="stack"] svg{min-width:0}
""",
        js="""
  /* the picture: a lane-and-column flow map, laid out from the figure's own JSON */
  (function(){
    var NS = 'http://www.w3.org/2000/svg';
    /* Every number below has a reason, and the reasons come from the engines that solved this
       first. Read from the tools themselves (`d2 layout dagre`, `d2 layout elk`) and from their
       published references:
         - a box is WIDENED to its label and text wraps at a MEASURED width, never a character
           count: mermaid's minNodeWidth (120) and wrappingWidth (120).
         - edges keep their own clearance from nodes and run in the channel between layers:
           ELK's spacing.edgeNode and layered.spacing.edgeNodeBetweenLayers (default 40), beside
           dagre's edgesep (default 20) and nodesep (default 60).
         - a container's own label reserves padding at its border before children are placed:
           ELK's padding (left=50) and nodeLabels.padding.
       The character-count wrap this replaced fitted the gallery's demo with 4.7 user units to
       spare and put a 20-character program name 8.8px outside its box the first time a figure
       used a real one. A count of characters is not a width, and never was. */
    var PAD = 10, GUTTER_MIN = 40, GUTTER_TEXT_GAP = 16, LANE_LABEL_X = 12;
    /* 24, not 10: a mark tag is pinned 11px above its box, so a narrower gap puts the tag
       of one cell inside the box of the cell above it. Seen on a repaired figure, one pixel
       in. */
    var LANE_GAP = 22, LANE_PAD_Y = 11, CELL_GAP = 24;
    var NODE_W_WIDE = 112, NODE_W_TIGHT = 96, NODE_W_MAX = 196;
    var COL_GAP_WIDE = 30, COL_GAP_TIGHT = 22;
    var INNER_PAD_X = 9, PAD_TOP = 9, PAD_BOTTOM = 8;
    var LABEL_SIZE = 11.5, LABEL_LINE = 13, LABEL_MAX_LINES = 3;
    var NOTE_SIZE = 9.5, NOTE_LINE = 11, NOTE_MAX_LINES = 2, NOTE_GAP = 3;
    var LANE_LABEL_SIZE = 11, LANE_LABEL_SPACING = 1.1;
    var GUTTER_MAX_SHARE = 0.30;  /* past this the lane label goes ABOVE its band instead */
    var STACK_BELOW = 560;        /* one column under a phone width, never a shrunken map */
    var CLEAR = 2;                /* how close a connector may pass a box and still be clear */
    var ELLIPSIS = String.fromCharCode(8230);

    function el(name, attrs){
      var made = document.createElementNS(NS, name);
      for (var k in attrs) { if (attrs[k] !== null && attrs[k] !== undefined) made.setAttribute(k, attrs[k]); }
      return made;
    }
    function words(text){
      var parts = String(text).split(' '), out = [];
      for (var i = 0; i < parts.length; i++) { if (parts[i]) out.push(parts[i]); }
      return out;
    }
    /* One hidden text element does every measurement, in the figure's own font at the figure's own
       size. It is created before the viewBox exists, so a user unit is a CSS pixel here and the
       numbers it returns are the numbers the layout is written in. */
    function measurer(svg){
      var probe = el('text', { x: -9999, y: -9999, visibility: 'hidden', 'aria-hidden': 'true' });
      svg.appendChild(probe);
      return {
        width: function(text, size, weight, spacing){
          probe.setAttribute('font-size', size);
          probe.setAttribute('font-weight', weight || 400);
          probe.setAttribute('letter-spacing', spacing || 0);
          probe.textContent = String(text);
          return probe.getComputedTextLength();
        },
        done: function(){ if (probe.parentNode) probe.parentNode.removeChild(probe); }
      };
    }
    /* Wrap to a WIDTH. Returns the lines and the widest line, so the caller can grow the box to
       the text rather than clip the text to the box. A single token wider than the limit comes
       back whole and over-wide on purpose: growing the box is the next move, and truncation is
       the one after that. */
    function wrapTo(text, limit, maxLines, size, weight, spacing, measure){
      var list = words(text), lines = [], line = '';
      for (var i = 0; i < list.length; i++) {
        var next = line ? line + ' ' + list[i] : list[i];
        if (!line || measure.width(next, size, weight, spacing) <= limit) { line = next; }
        else { lines.push(line); line = list[i]; }
      }
      if (line) lines.push(line);
      if (!lines.length) lines = [''];
      if (lines.length > maxLines) {
        lines = lines.slice(0, maxLines);
        lines[maxLines - 1] = lines[maxLines - 1] + ' ' + ELLIPSIS;
      }
      var widest = 0;
      for (var j = 0; j < lines.length; j++) {
        widest = Math.max(widest, measure.width(lines[j], size, weight, spacing));
      }
      return { lines: lines, widest: widest };
    }
    /* THE LAST RESORT, and only that: a token that will not fit the widest box the figure is
       allowed to draw gets cut, with the whole string kept in a <title> so nothing is lost. */
    function fitLine(text, limit, size, weight, spacing, measure){
      if (measure.width(text, size, weight, spacing) <= limit) return { text: text, cut: false };
      var cut = String(text);
      while (cut.length > 1 && measure.width(cut + ELLIPSIS, size, weight, spacing) > limit) {
        cut = cut.slice(0, -1);
      }
      return { text: cut + ELLIPSIS, cut: true };
    }
    /* A segment is clear of a box when it does not pass through its interior. Used by the
       renderer to CHOOSE a route and by the lint to REFUSE one, so the two agree by construction
       rather than by argument. Every route drawn here is orthogonal, so an overlap of both
       extents is an intersection. */
    function segmentHitsBox(x1, y1, x2, y2, b){
      var loX = Math.min(x1, x2), hiX = Math.max(x1, x2);
      var loY = Math.min(y1, y2), hiY = Math.max(y1, y2);
      if (hiX <= b.x + CLEAR || loX >= b.x + b.w - CLEAR) return false;
      if (hiY <= b.y + CLEAR || loY >= b.y + b.h - CLEAR) return false;
      return true;
    }
    function routeIsClear(points, boxes){
      for (var i = 1; i < points.length; i++) {
        for (var k = 0; k < boxes.length; k++) {
          if (segmentHitsBox(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1], boxes[k])) return false;
        }
      }
      return true;
    }
    function pathOf(points){
      var d = 'M ' + points[0][0] + ' ' + points[0][1];
      for (var i = 1; i < points.length; i++) { d += ' L ' + points[i][0] + ' ' + points[i][1]; }
      return d;
    }

    function drawOne(figure, index){
      var source = figure.querySelector('script.flow-data');
      if (!source) return;
      var data;
      try { data = JSON.parse(source.textContent); } catch (e) { return; }
      var lanes = data.lanes || [{ id: '', label: '' }];
      var nodes = data.nodes || [];
      if (!nodes.length) return;
      var edges = data.edges || [];
      var marks = data.marks || [];
      var cols = data.cols || (Math.max.apply(null, nodes.map(function(n){ return n.col; })) + 1);
      var laneIndex = {};
      lanes.forEach(function(lane, i){ laneIndex[lane.id] = i; });
      var laneOf = function(item){ return laneIndex[item.lane] || 0; };
      var uid = 'flow' + index;

      /* a redraw takes out its own drawing rather than stacking a second one under it */
      var previous = figure.querySelector('svg');
      if (previous) previous.parentNode.removeChild(previous);
      var oldCap = figure.querySelector('.flow-cap');
      if (oldCap) oldCap.parentNode.removeChild(oldCap);

      var svg = el('svg', {
        width: '100%', role: 'img', 'font-family': 'var(--font-body)',
        'aria-labelledby': uid + '-t' + (data.description ? ' ' + uid + '-d' : '')
      });
      var title = el('title', { id: uid + '-t' });
      title.textContent = data.title || figure.getAttribute('aria-label') || 'Diagram';
      svg.appendChild(title);
      if (data.description) {
        var desc = el('desc', { id: uid + '-d' });
        desc.textContent = data.description;
        svg.appendChild(desc);
      }
      figure.insertBefore(svg, figure.firstChild);

      var available = figure.getBoundingClientRect().width || 900;
      var stacked = available < STACK_BELOW;
      var measure = measurer(svg);

      var defs = el('defs');
      var marker = el('marker', {
        id: uid + '-arrow', viewBox: '0 0 10 10', refX: 9, refY: 5,
        markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'
      });
      marker.appendChild(el('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: 'var(--muted)' }));
      defs.appendChild(marker);
      svg.appendChild(defs);
      var g = el('g');
      svg.appendChild(g);

      /* ---- size every box to its own text, then give every box the widest of them, because a
              lane-and-column map is a GRID: one column wider than the rest stops being a
              column. The cap is NODE_W_MAX; past it a line is cut and kept in a <title>. */
      var wMin = stacked ? Math.max(160, available - 30 - PAD * 2) : (cols > 6 ? NODE_W_TIGHT : NODE_W_WIDE);
      var wMax = stacked ? Math.max(wMin, available - 30 - PAD * 2) : NODE_W_MAX;
      var needed = wMin;
      nodes.forEach(function(item){
        var room = wMax - INNER_PAD_X * 2;
        var lab = wrapTo(item.label, room, LABEL_MAX_LINES, LABEL_SIZE, 600, 0, measure);
        needed = Math.max(needed, lab.widest + INNER_PAD_X * 2);
        if (item.note) {
          var nte = wrapTo(item.note, room, NOTE_MAX_LINES, NOTE_SIZE, 700, 0.6, measure);
          needed = Math.max(needed, nte.widest + INNER_PAD_X * 2);
        }
      });
      var NODE_W = Math.max(wMin, Math.min(needed, wMax));
      var inner = NODE_W - INNER_PAD_X * 2;

      /* ---- the final wrap, at the final width, plus the truncation of last resort */
      var laid = {}, tallest = 0;
      nodes.forEach(function(item){
        var lab = wrapTo(item.label, inner, LABEL_MAX_LINES, LABEL_SIZE, 600, 0, measure);
        var labelCut = false;
        lab.lines = lab.lines.map(function(line){
          var fit = fitLine(line, inner, LABEL_SIZE, 600, 0, measure);
          if (fit.cut) labelCut = true;
          return fit.text;
        });
        var note = null, noteCut = false;
        if (item.note) {
          var nte = wrapTo(item.note, inner, NOTE_MAX_LINES, NOTE_SIZE, 700, 0.6, measure);
          nte.lines = nte.lines.map(function(line){
            var fit = fitLine(line, inner, NOTE_SIZE, 700, 0.6, measure);
            if (fit.cut) noteCut = true;
            return fit.text;
          });
          note = nte.lines;
        }
        var contentH = lab.lines.length * LABEL_LINE + (note ? NOTE_GAP + note.length * NOTE_LINE : 0);
        var h = Math.max(58, PAD_TOP + contentH + PAD_BOTTOM);
        laid[item.id] = { label: lab.lines, labelCut: labelCut, note: note, noteCut: noteCut, h: h, contentH: contentH };
        tallest = Math.max(tallest, h);
      });
      var NODE_H = tallest;

      /* ---- TWO NODES IN ONE CELL. A lane and a column can hold more than one thing, and the
              first version of this renderer drew them at the same coordinates, one exactly on
              top of the other. A real page shipped that way: two boxes in one lane at column 2,
              and two more in another. A cell with n nodes is n slots tall, and the lane grows
              to fit its deepest cell. */
      var slot = {}, laneDepth = lanes.map(function(){ return 1; });
      var cellCount = {};
      nodes.forEach(function(item){
        var key = laneOf(item) + ':' + item.col;
        slot[item.id] = cellCount[key] || 0;
        cellCount[key] = slot[item.id] + 1;
        laneDepth[laneOf(item)] = Math.max(laneDepth[laneOf(item)], cellCount[key]);
      });

      /* ---- the gutter is the LONGEST LANE LABEL, not a number somebody typed once. Past
              GUTTER_MAX_SHARE of the figure the label moves ABOVE its band instead, which is
              also what one column gets. */
      var laneLabelW = 0;
      lanes.forEach(function(lane){
        laneLabelW = Math.max(laneLabelW, measure.width(lane.label || '', LANE_LABEL_SIZE, 700, LANE_LABEL_SPACING));
      });
      var wantGutter = Math.max(GUTTER_MIN, LANE_LABEL_X + laneLabelW + GUTTER_TEXT_GAP);
      var COL_GAP = cols > 6 ? COL_GAP_TIGHT : COL_GAP_WIDE;
      var pitch = NODE_W + COL_GAP;
      var provisional = wantGutter + cols * pitch + PAD;
      var labelAbove = stacked || wantGutter > provisional * GUTTER_MAX_SHARE;
      var GUTTER = labelAbove ? GUTTER_MIN : wantGutter;
      var LANE_LABEL_H = labelAbove ? LANE_LABEL_SIZE + 7 : 0;
      var laneHeight = laneDepth.map(function(depth){
        return LANE_LABEL_H + LANE_PAD_Y * 2 + depth * NODE_H + (depth - 1) * CELL_GAP;
      });
      var laneTop = [], running = PAD;
      laneHeight.forEach(function(h, i){ laneTop[i] = running; running += h + LANE_GAP; });

      var width, height, boxes = {}, order = [];
      if (stacked) {
        /* ONE COLUMN. A map shrunk to a phone is a map nobody reads, and a map that scrolls
           sideways is a map nobody scrolls. The nodes stack in reading order, each run of a
           lane is announced once, and the connectors that are not neighbours run in the rail
           on the left. */
        order = nodes.slice().sort(function(a, b){
          return (a.col - b.col) || (laneOf(a) - laneOf(b));
        });
        var RAIL = 22, STACK_GAP = 26;
        width = Math.max(240, Math.round(available));
        var y = PAD;
        order.forEach(function(item, i){
          var eyebrow = (i === 0 || order[i - 1].lane !== item.lane) ? LANE_LABEL_SIZE + 18 : 0;
          y += eyebrow;
          boxes[item.id] = {
            x: RAIL + PAD, y: y, w: Math.max(120, width - RAIL - PAD * 2), h: laid[item.id].h,
            eyebrow: eyebrow, lane: item.lane, col: item.col
          };
          y += laid[item.id].h + STACK_GAP;
        });
        height = y - STACK_GAP + PAD;
      } else {
        width = GUTTER + cols * pitch + PAD;
        height = running - LANE_GAP + PAD;
        nodes.forEach(function(item){
          var li = laneOf(item);
          boxes[item.id] = {
            x: GUTTER + item.col * pitch,
            y: laneTop[li] + LANE_LABEL_H + LANE_PAD_Y + slot[item.id] * (NODE_H + CELL_GAP)
               + (NODE_H - laid[item.id].h) / 2,
            w: NODE_W, h: laid[item.id].h, lane: item.lane, col: item.col
          };
        });
      }
      nodes.forEach(function(item){
        var b = boxes[item.id];
        b.cx = b.x + b.w / 2; b.cy = b.y + b.h / 2;
      });
      var boxList = nodes.map(function(item){ return boxes[item.id]; });

      svg.setAttribute('viewBox', '0 0 ' + Math.round(width) + ' ' + Math.round(height));

      /* ---- lane bands, under everything */
      if (!stacked) {
        lanes.forEach(function(lane, i){
          g.appendChild(el('rect', {
            'class': 'flow-lane', 'data-lane': lane.id, x: PAD, y: laneTop[i],
            width: width - PAD * 2, height: laneHeight[i], rx: 12,
            fill: i % 2 ? 'var(--panel-2)' : 'var(--panel)', stroke: 'var(--line)'
          }));
          var label = el('text', {
            'class': 'flow-lane-label', 'data-lane': lane.id,
            x: PAD + LANE_LABEL_X,
            y: labelAbove ? laneTop[i] + LANE_LABEL_SIZE + 3 : laneTop[i] + laneHeight[i] / 2 + 4,
            'font-size': LANE_LABEL_SIZE, 'letter-spacing': LANE_LABEL_SPACING,
            'font-weight': 700, fill: 'var(--' + (lane.tone || 'muted') + ')'
          });
          label.textContent = lane.label;
          g.appendChild(label);
        });
      }

      /* ---- the connectors, routed in the CHANNELS: the gaps between columns and the gaps
              between lanes. No segment may enter a box, and the renderer PROVES it rather than
              assuming it: a simple route is drawn only when routeIsClear says it is clear. */
      function channelRightOf(col){ return GUTTER + col * pitch + NODE_W + COL_GAP / 2; }
      function channelLeftOf(col){ return GUTTER + col * pitch - COL_GAP / 2; }
      function railBetween(from, to){
        var a = laneOf(from), b = laneOf(to);
        var gapAfter = a < b ? a : (a > b ? a - 1 : (a < lanes.length - 1 ? a : a - 1));
        gapAfter = Math.max(0, Math.min(lanes.length - 2, gapAfter));
        return laneTop[gapAfter] + laneHeight[gapAfter] + LANE_GAP / 2;
      }
      var byId = {};
      nodes.forEach(function(item){ byId[item.id] = item; });
      edges.forEach(function(edge, ei){
        var a = boxes[edge.from], b = boxes[edge.to];
        if (!a || !b) return;
        var others = boxList.filter(function(x){ return x !== a && x !== b; });
        var points = null;
        if (stacked) {
          var below = b.y >= a.y + a.h;
          var simple = below
            ? [[a.cx, a.y + a.h], [b.cx, b.y - 6]]
            : [[a.cx, a.y], [b.cx, b.y + b.h + 6]];
          if (routeIsClear(simple, others)) { points = simple; }
          else {
            var railX = 8 + (ei % 2) * 6;
            points = [[a.x, a.cy], [railX, a.cy], [railX, b.cy], [b.x - 6, b.cy]];
          }
        } else {
          var straight = Math.abs(a.cy - b.cy) < 1
            ? [[a.x + a.w, a.cy], [b.x - 6, b.cy]]
            : (Math.abs(a.cx - b.cx) < 1
              ? [[a.cx, a.cy < b.cy ? a.y + a.h : a.y], [b.cx, a.cy < b.cy ? b.y - 6 : b.y + b.h + 6]]
              : null);
          if (straight && routeIsClear(straight, others)) { points = straight; }
          else {
            /* the jitter keeps two edges sharing one channel from drawing on top of each other,
               which is what dagre's edgesep buys with its own 20 pixels */
            var jitter = ((ei % 5) - 2) * 3.5;
            var outX = channelRightOf(a.col) + jitter, inX = channelLeftOf(b.col) + jitter;
            if (Math.abs(outX - inX) < 1) {
              points = [[a.x + a.w, a.cy], [outX, a.cy], [outX, b.cy], [b.x - 6, b.cy]];
            } else {
              var railY = railBetween(byId[edge.from], byId[edge.to]) + jitter;
              points = [
                [a.x + a.w, a.cy], [outX, a.cy], [outX, railY],
                [inX, railY], [inX, b.cy], [b.x - 6, b.cy]
              ];
            }
          }
        }
        g.appendChild(el('path', {
          'class': 'flow-edge', 'data-edge': edge.from + '-' + edge.to, d: pathOf(points),
          fill: 'none', stroke: 'var(--' + (edge.tone || 'muted') + ')',
          'stroke-width': 1.6, 'stroke-dasharray': edge.dashed ? '5 4' : null,
          'marker-end': 'url(#' + uid + '-arrow)'
        }));
      });

      /* ---- the boxes, over the connectors */
      (stacked ? order : nodes).forEach(function(item){
        var b = boxes[item.id], L = laid[item.id], tone = item.tone || 'acc';
        if (stacked && b.eyebrow) {
          var lane = lanes[laneOf(item)] || { label: '' };
          var eye = el('text', {
            'class': 'flow-lane-label', 'data-lane': item.lane, x: b.x, y: b.y - 18,
            'font-size': LANE_LABEL_SIZE, 'letter-spacing': LANE_LABEL_SPACING,
            'font-weight': 700, fill: 'var(--' + (lane.tone || 'muted') + ')'
          });
          eye.textContent = lane.label;
          g.appendChild(eye);
        }
        g.appendChild(el('rect', {
          'class': 'flow-node', 'data-node': item.id, x: b.x, y: b.y, width: b.w, height: b.h, rx: 10,
          fill: 'var(--' + tone + '-soft, var(--panel))', stroke: 'var(--' + tone + ')', 'stroke-width': 1.4
        }));
        var top = b.y + (b.h - L.contentH) / 2 + LABEL_SIZE;
        L.label.forEach(function(line, i){
          var t = el('text', {
            'class': 'flow-label', 'data-node': item.id, x: b.cx, y: top + i * LABEL_LINE,
            'text-anchor': 'middle', 'font-size': LABEL_SIZE, 'font-weight': 600, fill: 'var(--ink)'
          });
          t.textContent = line;
          if (L.labelCut) { var tt = el('title'); tt.textContent = item.label; t.appendChild(tt); }
          g.appendChild(t);
        });
        if (L.note) {
          var noteTop = top + L.label.length * LABEL_LINE + NOTE_GAP;
          L.note.forEach(function(line, i){
            var n = el('text', {
              'class': 'flow-note', 'data-node': item.id, x: b.cx, y: noteTop + i * NOTE_LINE,
              'text-anchor': 'middle', 'font-size': NOTE_SIZE, 'letter-spacing': 0.6,
              'font-weight': 700, fill: 'var(--' + tone + '-ink, var(--muted))'
            });
            n.textContent = line;
            if (L.noteCut) { var nt = el('title'); nt.textContent = item.note; n.appendChild(nt); }
            g.appendChild(n);
          });
        }
      });

      /* ---- marks: a small tag pinned to a box, for the questions a stage carries */
      marks.forEach(function(mark){
        var b = boxes[mark.node];
        if (!b) return;
        var w = 12 + measure.width(mark.label, NOTE_SIZE, 700, 0);
        g.appendChild(el('rect', {
          'class': 'flow-mark', 'data-node': mark.node, x: b.cx - w / 2, y: b.y - 11,
          width: w, height: 16, rx: 8, fill: 'var(--' + (mark.tone || 'ask') + ')'
        }));
        var t = el('text', {
          'class': 'flow-mark-label', 'data-node': mark.node, x: b.cx, y: b.y + 1,
          'text-anchor': 'middle', 'font-size': NOTE_SIZE, 'font-weight': 700, fill: 'var(--on-acc)'
        });
        t.textContent = mark.label;
        g.appendChild(t);
      });

      measure.done();
      figure.setAttribute('data-flow-layout', stacked ? 'stack' : 'lanes');
      figure.style.setProperty('--flow-min', Math.min(Math.round(width), 1180) + 'px');
      if (data.caption) {
        var cap = document.createElement('figcaption');
        cap.className = 'flow-cap';
        cap.textContent = data.caption;
        figure.appendChild(cap);
      }
    }

    function drawAll(){
      [].slice.call(document.querySelectorAll('figure.flow')).forEach(drawOne);
    }
    drawAll();

    /* A phone that turns, or a window dragged narrow, crosses the one-column threshold. Redoing
       the layout is cheap, and the alternative is a map that is right in the test and wrong in
       the hand. Debounced, and a redraw takes out its own drawing rather than adding one. */
    var redrawTimer = null, lastWidth = window.innerWidth;
    window.addEventListener('resize', function(){
      if (window.innerWidth === lastWidth) return;
      lastWidth = window.innerWidth;
      clearTimeout(redrawTimer);
      redrawTimer = setTimeout(drawAll, 160);
    });
  })();
""",
        group="Structure",
    ),
    Component(
        "diagram-flowchart",
        "Diagram: a flowchart, from four lines of markdown",
        "<b>When the shape is a path with branches</b> and the lane-and-column map above is more "
        "machinery than the page needs. Write the boxes and the arrows in the markdown source and "
        "the builder pre-renders them to inline SVG at build time with <b>d2</b>, then "
        "re-colors the result onto the house tokens, so it follows the theme toggle like everything "
        "else on the page. Nothing is fetched and nothing is drawn in the reader's browser: the "
        "picture is in the file, and the file works on a plane. The pre-delivery check refuses a page "
        "that loads a diagram library or an image of a diagram instead.",
        "",
        diagram=(
            "flowchart",
            "How a request becomes a ticket",
            "request: A request lands\n"
            "triage: Triage reads it\n"
            "ticket: A ticket on the board\n"
            "review: The review queue\n\n"
            "request -> triage: email, form, phone\n"
            "triage -> ticket: clear\n"
            "triage -> review: unclear\n",
        ),
        group="Structure",
    ),
    Component(
        "diagram-sequence",
        "Diagram: a sequence, who says what to whom",
        "<b>When the shape is a conversation in time</b> - a request and its answer across two or "
        "more actors, an API round trip, an approval that goes out and comes back. One line per "
        "message; the builder wraps them in d2's sequence container so nobody writes the container "
        "by hand. The figure's caption is the only title it carries.",
        "",
        diagram=(
            "sequence",
            "What happens when the assistant is asked a question",
            "Reader -> Assistant: a question\n"
            "Assistant -> Database: read the records\n"
            "Database -> Assistant: the rows\n"
            "Assistant -> Reader: the answer, with the record ids\n",
        ),
        group="Structure",
    ),
    Component(
        "diagram-mindmap",
        "Diagram: a mind map, radial from one center",
        "<b>When the shape is one idea and everything hanging off it.</b> The source is an indented "
        "outline, which is how anyone writes a mind map anyway; the builder compiles it to DOT and "
        "renders it with <b>graphviz</b>'s radial layout. Two spaces is one level.",
        "",
        diagram=(
            "mindmap",
            "What the system holds",
            "The system\n"
            "  Capture\n"
            "    Chat\n"
            "    Email\n"
            "    Voice\n"
            "  Route\n"
            "    The board\n"
            "    The pipeline\n"
            "  Report\n"
            "    The dashboard\n"
            "    The weekly summary\n",
        ),
        group="Structure",
    ),
    Component(
        "diagram-tree",
        "Diagram: a tree, left to right",
        "<b>When the shape is a hierarchy</b> - a folder layout, an org, a taxonomy, a decision "
        "tree. The same indented outline as the mind map, laid out left to right by graphviz "
        "instead of around a center. Pick the one that reads better at the width the page uses.",
        "",
        diagram=(
            "tree",
            "How the plan nests",
            "The plan\n"
            "  Initiatives\n"
            "    Phases\n"
            "      Projects\n"
            "  Areas\n"
            "  Decisions\n"
            "    Open\n"
            "    Answered\n",
        ),
        group="Structure",
    ),
    Component(
        "facts",
        "Facts grid",
        "The at-a-glance pairs under the summary. Two columns, one on a phone.",
        """
<div class="facts">
  <div class="cell"><div class="k">Look</div><div class="v"><span class="chip n">TINT</span> cool ground plus graph paper</div></div>
  <div class="cell"><div class="k">Reading width</div><div class="v">1080px, draggable 720 to 1600</div></div>
  <div class="cell"><div class="k">Theme</div><div class="v"><span class="chip g">LIGHT</span> default, toggle keeps dark</div></div>
  <div class="cell"><div class="k">Works offline</div><div class="v"><span class="chip g">YES</span> nothing external is fetched</div></div>
</div>
""",
        group="Structure",
    ),
    Component(
        "links-table",
        "Key links table",
        "Every destination named anywhere in the document, copy-pasteable. Mandatory whenever a "
        "document names two or more.",
        """
<div class="scroll"><table>
  <thead><tr><th>Destination</th><th>URL (copy-paste or click)</th></tr></thead>
  <tbody>
    <tr><td>The documentation site</td><td><a href="https://docs.example.com/" target="_blank" rel="noopener noreferrer">https://docs.example.com/</a></td></tr>
    <tr><td>The shared document list</td><td><a href="https://app.example.com/documents" target="_blank" rel="noopener noreferrer">https://app.example.com/documents</a></td></tr>
  </tbody>
</table></div>
""",
        group="Structure",
    ),
    Component(
        "grouped-bar",
        "Grouped bar, one row per thing",
        "Three figures compared across a list of things: agreed against invoiced against paid, "
        "budget against spent against committed, quoted against delivered. One row per thing, three "
        "tracks in the row, every track scaled against the largest value on the whole chart so the "
        "rows are comparable to each other and not just to themselves. Every number rides in a "
        "data attribute and the widths are computed at load, so a rebuild is a data edit and there "
        "is no hand-written percentage to go stale. A row whose value is zero still renders its "
        "track, because an empty bar is the finding on a project that has never been invoiced.",
        """
<figure class="gbar" data-gbar data-prefix="$">
  <div class="gbar-legend">
    <span class="gk"><i class="t-muted"></i>Agreed</span>
    <span class="gk"><i class="t-acc"></i>Invoiced</span>
    <span class="gk"><i class="t-green"></i>Paid</span>
  </div>
  <div class="gbar-rows">
    <div class="gbar-row"><div class="gbar-name">Northwind Retail</div><div class="gbar-tracks">
      <div class="gtrack t-muted" data-v="1440"><span></span><b></b></div>
      <div class="gtrack t-acc" data-v="2090"><span></span><b></b></div>
      <div class="gtrack t-green" data-v="2090"><span></span><b></b></div>
    </div></div>
    <div class="gbar-row"><div class="gbar-name">Blue Harbor Clinic</div><div class="gbar-tracks">
      <div class="gtrack t-muted" data-v="720"><span></span><b></b></div>
      <div class="gtrack t-acc" data-v="760"><span></span><b></b></div>
      <div class="gtrack t-green" data-v="760"><span></span><b></b></div>
    </div></div>
    <div class="gbar-row"><div class="gbar-name">Summit Fitness</div><div class="gbar-tracks">
      <div class="gtrack t-muted" data-v="600"><span></span><b></b></div>
      <div class="gtrack t-acc" data-v="260"><span></span><b></b></div>
      <div class="gtrack t-green" data-v="260"><span></span><b></b></div>
    </div></div>
    <div class="gbar-row"><div class="gbar-name">Lighthouse Learning</div><div class="gbar-tracks">
      <div class="gtrack t-muted" data-v="600"><span></span><b></b></div>
      <div class="gtrack t-acc" data-v="0"><span></span><b></b></div>
      <div class="gtrack t-green" data-v="0"><span></span><b></b></div>
    </div></div>
  </div>
  <figcaption>Every track is scaled against the largest value on the chart, so a short bar is
    short compared to the whole picture and not only to its own row.</figcaption>
</figure>
""",
        css="""
  /* ---- grouped bar: one row per thing, three tracks, widths computed from data-v ---- */
  .gbar{margin:16px 0 6px; padding:0}
  .gbar-legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:0 0 12px}
  /* The tone rides on the SWATCH, never on the row: a row rule that sets its own color wins on
     specificity over a .t-* utility and the swatch renders black, which is the silent-CSS
     failure this component was built to avoid in the first place. */
  .gbar-legend .gk{display:inline-flex; align-items:center; gap:7px; font-size:.82rem; color:var(--ink)}
  .gbar-legend .gk i{width:18px; height:9px; border-radius:3px; background:currentColor; flex:0 0 auto}
  .gbar-legend .gk i.t-muted{background:var(--muted)}
  .gbar-legend .gk i.t-acc{background:var(--acc)}
  .gbar-legend .gk i.t-green{background:var(--green)}
  .gbar-legend .gk i.t-amber{background:var(--amber)}
  .gbar-legend .gk i.t-red{background:var(--red)}
  .gbar-legend .gk i.t-ink{background:var(--ink)}
  .gbar-rows{display:flex; flex-direction:column; gap:14px}
  .gbar-row{display:grid; grid-template-columns:minmax(120px, 210px) 1fr; gap:10px 14px; align-items:center}
  .gbar-name{font-size:.86rem; color:var(--ink); line-height:1.35}
  .gbar-tracks{display:flex; flex-direction:column; gap:4px; min-width:0}
  .gtrack{position:relative; display:flex; align-items:center; gap:8px; height:14px}
  .gtrack > span{
    display:block; height:14px; border-radius:3px; background:currentColor;
    width:0; min-width:2px; transition:width .35s ease; flex:0 0 auto;
  }
  .gtrack.zero > span{background:none; border:1px dashed currentColor; opacity:.55}
  .gtrack > b{
    font-size:.76rem; font-weight:600; color:var(--ink); white-space:nowrap;
    font-variant-numeric:tabular-nums;
  }
  @media screen and (max-width:600px){
    .gbar-row{grid-template-columns:1fr}
    .gbar-name{font-weight:600}
  }
  @media print{ .gtrack > span{transition:none} }
""",
        js="""
  /* ---- grouped bar: read every data-v, scale against the largest on the chart, label each
         track. No percentage is ever written by hand, so a data edit is the whole rebuild. ---- */
  [].slice.call(document.querySelectorAll('[data-gbar]')).forEach(function (fig) {
    var tracks = [].slice.call(fig.querySelectorAll('.gtrack'));
    if (!tracks.length) return;
    var prefix = fig.getAttribute('data-prefix') || '';
    var values = tracks.map(function (t) { return parseFloat(t.getAttribute('data-v')) || 0; });
    var max = Math.max.apply(null, values.concat([0]));
    tracks.forEach(function (t, i) {
      var v = values[i];
      var bar = t.querySelector('span');
      var label = t.querySelector('b');
      if (bar) bar.style.width = max > 0 ? (Math.max(v / max, 0) * 100).toFixed(2) + '%' : '0%';
      if (v === 0) t.classList.add('zero');
      if (label) {
        label.textContent = prefix + v.toLocaleString('en-US', {
          minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2
        });
      }
    });
  });
""",
        group="Data",
    ),
    Component(
        "data-table",
        "Filterable, sortable data table",
        "ANY table or list of data, without exception. Client-side, no network. "
        "Click a header to sort, type to filter. Dates never wrap. Rows carry content-visibility so "
        "a long body stays cheap to scroll. The CSS and the JS are already in the base template: "
        "give the table class=\"dt\", wrap it, and mark the sortable headers.",
        """
<div class="dt-wrap">
  <div class="dt-controls">
    <input type="search" class="dt-filter" placeholder="Filter these rows" aria-label="Filter the table">
    <span class="dt-count"></span>
  </div>
  <div class="scroll"><table class="dt">
    <thead><tr>
      <th data-sort="text">Document</th>
      <th data-sort="text">Audience</th>
      <th data-sort="num" class="num">Width</th>
      <th data-sort="text" class="nw">Built</th>
      <th data-sort="text">State</th>
    </tr></thead>
    <tbody>
      <tr><td>Weekly planning</td><td>Internal</td><td class="num">1080</td><td class="nw">Sep 16 '26</td><td><span class="chip g">LIVE</span></td></tr>
      <tr><td>Phase 1 plan</td><td>Client</td><td class="num">1000</td><td class="nw">Sep 11 '26</td><td><span class="chip g">LIVE</span></td></tr>
      <tr><td>Morning report</td><td>Internal</td><td class="num">1000</td><td class="nw">Sep 15 '26</td><td><span class="chip a">REBUILD</span></td></tr>
      <tr><td>Call agenda</td><td>Client</td><td class="num">1080</td><td class="nw">Sep 15 '26</td><td><span class="chip g">LIVE</span></td></tr>
      <tr><td>Data note</td><td>Client</td><td class="num">1000</td><td class="nw">Sep 11 '26</td><td><span class="chip n">DRAFT</span></td></tr>
    </tbody>
  </table></div>
</div>
""",
        group="Data",
    ),
    Component(
        "line-chart",
        "Line chart with a crosshair readout",
        "Several series over time, an optional shaded band between two of them for a best case and a "
        "worst case, milestone rules, a today rule, and a crosshair that reads EVERY line at once. "
        "Every value lives in the chart-data JSON block inside the figure, never in a hand-written "
        "path, so a rebuild is a data edit. It draws in real pixels and redraws on resize: a scaled "
        "viewBox shrinks the axis type to nothing at 390. It carries its own readout card rather "
        "than the shared tooltip, which renders one line and one value and fights a chart on every "
        "pointer move. Tones are ink, acc, green, amber, red and muted, so both themes follow.",
        """
<figure class="chart" data-chart>
  <script type="application/json" class="chart-data">
  {
    "axis": {"prefix": "$", "zeroLine": true},
    "today": "2026-09-18",
    "band": ["early", "late"],
    "bandTone": "green",
    "marks": [{"d": "2026-09-30", "l": "Month end"}],
    "days": {"2026-09-30": ["out $8,309: month end run"]},
    "series": [
      {"k": "hist", "name": "Posted", "tone": "ink", "width": 2.6, "dots": true,
       "note": "what has happened",
       "points": [["2026-07-21", 97305], ["2026-08-11", 71240], ["2026-09-01", 55118], ["2026-09-17", 42591]]},
      {"k": "early", "name": "Paid early", "tone": "green", "width": 2.2,
       "note": "every invoice lands on time",
       "points": [["2026-09-17", 42591], ["2026-09-24", 38870], ["2026-09-30", 31145]]},
      {"k": "late", "name": "Paid late", "tone": "green", "width": 2.2, "dash": "6 4",
       "note": "the slow case",
       "points": [["2026-09-17", 42591], ["2026-09-24", 33210], ["2026-09-30", 21980]]}
    ]
  }
  </script>
  <div class="chart-legend"></div>
  <div class="chart-plot">
    <svg role="img" aria-label="Cash on hand from July 21 to September 30, with the paid-early and paid-late cases"></svg>
    <div class="chart-read" role="status" aria-hidden="true"></div>
  </div>
  <figcaption>Hover anywhere across the plot: the readout lists every series at that date, plus
    anything that lands on it. Values are read from the JSON block above, never from the path.</figcaption>
</figure>
""",
        css="""
  /* ---- line chart (data in a chart-data JSON block; every value comes from there) ---- */
  .chart{margin:16px 0 6px; padding:0}
  .chart-legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:0 0 10px}
  .chart-legend .ck{display:inline-flex; align-items:center; gap:7px; font-size:.82rem}
  .chart-legend .ck .cl{color:var(--ink)}
  .chart-legend .ck small{color:var(--muted); font-size:.74rem}
  .chart-legend .ck i{width:18px; height:0; border-top:3px solid currentColor; border-radius:2px; display:inline-block}
  .chart-legend .ck.dash i{border-top-style:dashed}
  .chart-plot{position:relative; touch-action:pan-y}
  .chart-plot svg{display:block; width:100%; height:auto; overflow:visible}
  .chart figcaption{font-size:.8rem; color:var(--muted); margin-top:10px; line-height:1.55}

  /* the .t-* tone utilities live in the BASE template, because more than one component reads
     them and a class defined inside one component's CSS renders black in a page that did not
     pull that component in. */
  .cline{fill:none; stroke:currentColor; stroke-linejoin:round; stroke-linecap:round}
  .cdot{fill:currentColor; stroke:none}
  .cband{stroke:none; fill:currentColor; opacity:.15}
  .cg{stroke:var(--line); stroke-width:1}
  .cg.v{stroke:var(--line-2)}
  .cg.zero{stroke:var(--red); stroke-width:1.4; stroke-dasharray:4 4; opacity:.45}
  .cx{font-family:var(--font-body); font-size:11px; fill:var(--muted); font-variant-numeric:tabular-nums}
  .cx.today{font-size:10px; letter-spacing:.06em; text-transform:uppercase; fill:var(--acc)}
  .cmark{stroke:var(--line); stroke-width:1; stroke-dasharray:2 5}
  .ctoday{stroke:var(--acc); stroke-width:1.2; stroke-dasharray:3 4}
  .chair{stroke:var(--muted); stroke-width:1; pointer-events:none}
  .cknob{fill:var(--panel); stroke:currentColor; stroke-width:2.4; pointer-events:none}

  /* the crosshair readout: the chart's own card, so it can carry a line per series */
  .chart-read{
    position:absolute; top:10px; left:0; z-index:8; pointer-events:none; opacity:0;
    transform:translateY(4px); transition:opacity .12s, transform .12s; min-width:210px;
    background:var(--panel); border:1px solid var(--line); border-radius:10px;
    box-shadow:var(--shadow); padding:9px 12px; font-size:.8rem; line-height:1.5; color:var(--ink);
  }
  .chart-read.on{opacity:1; transform:translateY(0)}
  .chart-read b{display:block; font-size:.84rem; margin-bottom:4px}
  .chart-read .rr .cl{color:inherit}
  .chart-read .rr{display:flex; align-items:center; gap:7px; white-space:nowrap}
  .chart-read .rr b{margin:0 0 0 auto; font-variant-numeric:tabular-nums; display:inline; font-size:.8rem}
  .chart-read .rk{width:11px; height:0; border-top:3px solid currentColor; border-radius:2px; flex:0 0 auto}
  .chart-read .rd{margin-top:5px; padding-top:5px; border-top:1px solid var(--line-2); color:var(--muted); font-size:.75rem}
  .chart-read .rd span{display:block}
  @media print{ .chart-read{display:none} }
""",
        js="""
  /* ---- line chart: several series, an optional band between two of them, and a crosshair
         readout. Data rides in a <script type="application/json" class="chart-data"> inside the
         figure, so no value is ever baked into a path and a rebuild is a data edit. The SVG is
         drawn in REAL PIXELS and redrawn on resize: a scaled viewBox shrinks the axis type to
         nothing at 390. ---- */
  [].slice.call(document.querySelectorAll('[data-chart]')).forEach(function (fig) {
    var dataNode = fig.querySelector('.chart-data');
    var svg = fig.querySelector('svg');
    var plot = fig.querySelector('.chart-plot');
    var read = fig.querySelector('.chart-read');
    var legend = fig.querySelector('.chart-legend');
    if (!dataNode || !svg || !plot || !read) return;
    var cfg;
    try { cfg = JSON.parse(dataNode.textContent); } catch (e) { return; }
    if (!cfg.series || !cfg.series.length) return;

    var NS = 'http://www.w3.org/2000/svg';
    var DAY = 86400000;
    var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var pre = (cfg.axis && cfg.axis.prefix) || '';

    function ts(s) { var p = s.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }
    function money(v) {
      return (v < 0 ? '-' : '') + pre + Math.abs(Math.round(v)).toLocaleString('en-US');
    }
    function short(ms) { var d = new Date(ms); return MON[d.getUTCMonth()] + ' ' + d.getUTCDate(); }
    function longd(ms) {
      var d = new Date(ms);
      return MON[d.getUTCMonth()] + ' ' + d.getUTCDate() + ', ' + d.getUTCFullYear();
    }

    /* every series as a sorted array of [ms, value], plus a lookup by day */
    var series = cfg.series.map(function (s) {
      var pts = s.points.map(function (p) { return [ts(p[0]), p[1]]; })
        .sort(function (a, b) { return a[0] - b[0]; });
      var at = {};
      pts.forEach(function (p) { at[p[0]] = p[1]; });
      return {
        k: s.k, name: s.name, tone: s.tone || 'ink', width: s.width || 2,
        dash: s.dash || '', dots: !!s.dots, note: s.note || '', pts: pts, at: at
      };
    });
    var x0 = Math.min.apply(null, series.map(function (s) { return s.pts[0][0]; }));
    var x1 = Math.max.apply(null, series.map(function (s) { return s.pts[s.pts.length - 1][0]; }));
    var vals = [];
    series.forEach(function (s) { s.pts.forEach(function (p) { vals.push(p[1]); }); });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (cfg.axis && cfg.axis.zeroLine && lo > 0) lo = 0;
    /* a nice step off the 1-2-2.5-5-10 ladder, aiming for about six gridlines. Rounding the
       range to a bare power of ten wastes half the plot: a series running to -8,883 was given
       a -50,000 floor. */
    function niceStep(range, target) {
      var raw = Math.max(1, range) / target;
      var mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
      var norm = raw / mag;
      var mult = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
      return mult * mag;
    }
    var step = niceStep(hi - lo, 6);
    lo = Math.floor(lo / step) * step;
    hi = Math.ceil(hi / step) * step;

    /* linear interpolation so a hover on any day reads every line, not only its own points */
    function valueAt(s, ms) {
      if (ms < s.pts[0][0] || ms > s.pts[s.pts.length - 1][0]) return null;
      for (var i = 1; i < s.pts.length; i++) {
        if (ms <= s.pts[i][0]) {
          var a = s.pts[i - 1], b = s.pts[i];
          if (b[0] === a[0]) return b[1];
          return a[1] + (b[1] - a[1]) * ((ms - a[0]) / (b[0] - a[0]));
        }
      }
      return s.pts[s.pts.length - 1][1];
    }

    var geo = null;

    function draw() {
      var W = Math.max(280, Math.round(plot.clientWidth));
      var narrow = W < 560;
      var H = narrow ? 260 : 380;
      var padL = narrow ? 46 : 62, padR = narrow ? 10 : 16;
      var padT = 18, padB = narrow ? 34 : 40;
      var iw = W - padL - padR, ih = H - padT - padB;
      geo = { W: W, H: H, padL: padL, padT: padT, iw: iw, ih: ih, narrow: narrow };

      function X(ms) { return padL + ((ms - x0) / (x1 - x0)) * iw; }
      function Y(v) { return padT + (1 - (v - lo) / (hi - lo)) * ih; }
      geo.X = X; geo.Y = Y;

      while (svg.firstChild) svg.removeChild(svg.firstChild);
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      svg.setAttribute('width', W);
      svg.setAttribute('height', H);

      function el(name, attrs, cls) {
        var n = document.createElementNS(NS, name);
        for (var a in attrs) n.setAttribute(a, attrs[a]);
        if (cls) n.setAttribute('class', cls);
        svg.appendChild(n);
        return n;
      }

      /* horizontal grid and the money axis */
      for (var v = lo; v <= hi + 1; v += step) {
        var zero = Math.abs(v) < 0.5;
        el('line', { x1: padL, x2: padL + iw, y1: Y(v), y2: Y(v) }, zero ? 'cg zero' : 'cg');
        var lab = el('text', { x: padL - 8, y: Y(v) + 4, 'text-anchor': 'end' }, 'cx');
        lab.textContent = narrow
          ? (v < 0 ? '-' : '') + pre + Math.abs(Math.round(v / 1000)) + 'k'
          : money(v);
      }
      /* month boundaries on the date axis */
      var d = new Date(x0);
      var m = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
      while (m <= x1) {
        if (m >= x0) {
          el('line', { x1: X(m), x2: X(m), y1: padT, y2: padT + ih }, 'cg v');
          var t2 = el('text', { x: X(m), y: padT + ih + 18, 'text-anchor': 'middle' }, 'cx');
          t2.textContent = MON[new Date(m).getUTCMonth()];
        }
        var nd = new Date(m);
        m = Date.UTC(nd.getUTCFullYear(), nd.getUTCMonth() + 1, 1);
      }

      /* the band between two named series, drawn under every line */
      if (cfg.band && cfg.band.length === 2) {
        var a = series.filter(function (s) { return s.k === cfg.band[0]; })[0];
        var b = series.filter(function (s) { return s.k === cfg.band[1]; })[0];
        if (a && b) {
          var fwd = a.pts.map(function (p, i) {
            return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1);
          }).join(' ');
          var back = b.pts.slice().reverse().map(function (p) {
            return 'L' + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1);
          }).join(' ');
          el('path', { d: fwd + ' ' + back + ' Z' }, 'cband t-' + (cfg.bandTone || a.tone));
        }
      }

      /* the lines */
      series.forEach(function (s) {
        var dd = s.pts.map(function (p, i) {
          return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1);
        }).join(' ');
        var attrs = { d: dd, 'stroke-width': s.width, 'vector-effect': 'non-scaling-stroke' };
        if (s.dash) attrs['stroke-dasharray'] = s.dash;
        el('path', attrs, 'cline t-' + s.tone);
        if (s.dots) {
          s.pts.forEach(function (p) {
            el('circle', { cx: X(p[0]).toFixed(1), cy: Y(p[1]).toFixed(1), r: 2.6 }, 'cdot t-' + s.tone);
          });
        }
      });

      /* the milestone flags and the today rule */
      (cfg.marks || []).forEach(function (mk) {
        var mx = X(ts(mk.d));
        el('line', { x1: mx, x2: mx, y1: padT, y2: padT + ih }, 'cmark');
      });
      if (cfg.today) {
        var tx = X(ts(cfg.today));
        el('line', { x1: tx, x2: tx, y1: padT, y2: padT + ih }, 'ctoday');
        var tl = el('text', { x: tx + 5, y: padT + 11 }, 'cx today');
        tl.textContent = 'today';
      }

      /* the crosshair, hidden until a pointer arrives */
      geo.hair = el('line', { x1: 0, x2: 0, y1: padT, y2: padT + ih, opacity: 0 }, 'chair');
      geo.knobs = series.map(function (s) {
        return el('circle', { cx: 0, cy: 0, r: 4.5, opacity: 0 }, 'cknob t-' + s.tone);
      });
    }

    function paintLegend() {
      if (!legend) return;
      legend.innerHTML = '';
      series.forEach(function (s) {
        var b = document.createElement('span');
        b.className = 'ck t-' + s.tone + (s.dash ? ' dash' : '');
        /* the swatch takes the series color from the tone class through currentColor, so the
           label text carries its own color rather than the key doing it: a color set on .ck
           outranks the tone class and turned every swatch the same shade of ink. */
        b.innerHTML = '<i></i><span class="cl">' + s.name + '</span>' +
          (s.note ? ' <small>' + s.note + '</small>' : '');
        legend.appendChild(b);
      });
    }

    function hover(clientX) {
      if (!geo) return;
      var r = svg.getBoundingClientRect();
      var px = clientX - r.left;
      var frac = (px - geo.padL) / geo.iw;
      if (frac < -0.02 || frac > 1.02) { leave(); return; }
      frac = Math.min(1, Math.max(0, frac));
      var ms = Math.round((x0 + frac * (x1 - x0)) / DAY) * DAY;
      var lines = '';
      geo.knobs.forEach(function (kn, i) {
        var v = valueAt(series[i], ms);
        if (v === null) { kn.setAttribute('opacity', 0); return; }
        kn.setAttribute('cx', geo.X(ms).toFixed(1));
        kn.setAttribute('cy', geo.Y(v).toFixed(1));
        kn.setAttribute('opacity', 1);
        lines += '<div class="rr"><span class="rk t-' + series[i].tone + '"></span>' +
          series[i].name + '<b>' + money(v) + '</b></div>';
      });
      geo.hair.setAttribute('x1', geo.X(ms).toFixed(1));
      geo.hair.setAttribute('x2', geo.X(ms).toFixed(1));
      geo.hair.setAttribute('opacity', 1);
      var day = (cfg.days && cfg.days[new Date(ms).toISOString().slice(0, 10)]) || [];
      var extra = day.length
        ? '<div class="rd">' + day.map(function (s) { return '<span>' + s + '</span>'; }).join('') + '</div>'
        : '';
      read.innerHTML = '<b>' + longd(ms) + '</b>' + lines + extra;
      read.classList.add('on');
      var w = read.offsetWidth || 240;
      var left = geo.X(ms) + 16;
      if (left + w > geo.W - 6) left = geo.X(ms) - w - 16;
      read.style.left = Math.max(4, left) + 'px';
    }

    function leave() {
      read.classList.remove('on');
      if (!geo) return;
      geo.hair.setAttribute('opacity', 0);
      geo.knobs.forEach(function (k) { k.setAttribute('opacity', 0); });
    }

    plot.addEventListener('pointermove', function (e) { hover(e.clientX); });
    plot.addEventListener('pointerleave', leave);
    plot.addEventListener('pointerdown', function (e) { hover(e.clientX); });

    var pending = 0;
    function redraw() {
      clearTimeout(pending);
      pending = setTimeout(function () { draw(); leave(); }, 90);
    }
    draw();
    paintLegend();
    if (window.ResizeObserver) new ResizeObserver(redraw).observe(plot);
    else window.addEventListener('resize', redraw);
    document.addEventListener('hd:theme', function () { draw(); });
  });
""",
        group="Data",
    ),
    Component(
        "slider",
        "Range slider with a live readout",
        "Any number the reader might want to play with. The readout updates as it moves, the value "
        "is remembered per page, and the ticks say what the range means.",
        """
<div class="slider-row" data-slider data-store="gallery-weeks">
  <div class="slider-head">
    <label class="slab" for="weeks">Weeks to first delivery</label>
    <div class="slider-val"><span data-out>8</span> <small>weeks</small></div>
  </div>
  <input type="range" id="weeks" min="2" max="20" step="1" value="8" aria-label="Weeks to first delivery">
  <div class="ticks"><span>2</span><span>6</span><span>10</span><span>14</span><span>20</span></div>
</div>
""",
        css="""
  .slider-row{background:var(--panel-2); border:1px solid var(--line); border-radius:var(--radius-sm); padding:14px 16px; margin:12px 0}
  .slider-head{display:flex; justify-content:space-between; align-items:baseline; gap:12px; flex-wrap:wrap}
  .slab{font-size:.86rem; font-weight:600; color:var(--ink)}
  .slider-val{font-family:var(--font-head); font-size:1.5rem; font-weight:700; color:var(--acc); font-variant-numeric:tabular-nums}
  .slider-val small{font-size:.8rem; color:var(--muted); font-family:var(--font-body); font-weight:600}
  .slider-row input[type="range"]{width:100%; margin:10px 0 2px; accent-color:var(--acc); height:22px}
  .slider-row input[type="range"]:focus-visible{outline:2px solid var(--acc); outline-offset:3px}
  .ticks{display:flex; justify-content:space-between; font-size:.7rem; color:var(--muted); font-variant-numeric:tabular-nums}
""",
        js="""
  /* range slider: live readout, remembered per page */
  [].slice.call(document.querySelectorAll('[data-slider]')).forEach(function(row){
    var input = row.querySelector('input[type="range"]');
    var out = row.querySelector('[data-out]');
    if (!input || !out) return;   /* guard BEFORE the key: reading input.id on a null threw and
                                     killed the whole block, taking every later slider with it */
    var key = 'hd-' + (row.getAttribute('data-store') || input.id);
    try { var saved = localStorage.getItem(key); if (saved !== null) input.value = saved; } catch (e) {}
    function paint(){
      out.textContent = Number(input.value).toLocaleString();
      try { localStorage.setItem(key, input.value); } catch (e) {}
      row.dispatchEvent(new CustomEvent('hd:change', {bubbles:true}));
    }
    input.addEventListener('input', paint);
    paint();
  });
""",
        group="Interactive",
    ),
    Component(
        "calculator",
        "Inputs bound to a calculation (the ROI pattern)",
        "The canonical commercial component: a slider and a number input driving three live figures. "
        "Every number the reader would otherwise have to take on trust becomes one they can test. "
        "Put one on any document that makes a money argument.",
        """
<div class="calc" data-calc>
  <div class="slider-row" data-slider data-store="gallery-sites">
    <div class="slider-head">
      <label class="slab" for="sites">Sites built per month</label>
      <div class="slider-val"><span data-out>20</span> <small>/ month</small></div>
    </div>
    <input type="range" id="sites" min="0" max="60" step="1" value="20" aria-label="Sites built per month">
    <div class="ticks"><span>0</span><span>15</span><span>30</span><span>45</span><span>60</span></div>
  </div>
  <div class="calc-grid">
    <label class="calc-field"><span class="slab">Cost per site today</span>
      <span class="money"><span class="cur">$</span><input type="number" id="costNow" value="1000" min="0" max="20000" step="50"></span>
    </label>
    <label class="calc-field"><span class="slab">Cost per site after</span>
      <span class="money"><span class="cur">$</span><input type="number" id="costAfter" value="200" min="0" max="20000" step="25"></span>
    </label>
  </div>
  <div class="hero-stats">
    <div class="stat r"><div class="num" data-calc-out="today">$20,000</div><div class="lbl"><b>What it costs today</b></div></div>
    <div class="stat n"><div class="num" data-calc-out="after">$4,000</div><div class="lbl"><b>What it costs after</b></div></div>
    <div class="stat g"><div class="num" data-calc-out="saved">$16,000</div><div class="lbl"><b>What you keep, every month</b></div></div>
  </div>
</div>
""",
        css="""
  .calc-grid{display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin:12px 0}
  .calc-field{display:flex; flex-direction:column; gap:6px; background:var(--panel-2); border:1px solid var(--line); border-radius:var(--radius-sm); padding:12px 14px}
  .money{display:flex; align-items:center; gap:4px}
  .money .cur{color:var(--muted); font-weight:700}
  .calc-field input[type="number"]{width:100%; font:inherit; font-size:1.05rem; font-weight:700; font-variant-numeric:tabular-nums; color:var(--ink); background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:7px 10px}
  .calc-field input:focus{outline:2px solid var(--acc); outline-offset:1px; border-color:var(--acc)}
  @media screen and (max-width:600px){ .calc-grid{grid-template-columns:1fr} }
""",
        js="""
  /* calculator: recompute on any input in the block, including the slider above it */
  [].slice.call(document.querySelectorAll('[data-calc]')).forEach(function(box){
    var money = function(n){ return '$' + Math.round(n).toLocaleString(); };
    var out = function(name){ return box.querySelector('[data-calc-out="' + name + '"]'); };
    function recompute(){
      var sites = Number((box.querySelector('input[type="range"]') || {}).value || 0);
      var now = Number((box.querySelector('#costNow') || {}).value || 0);
      var after = Number((box.querySelector('#costAfter') || {}).value || 0);
      var a = sites * now, b = sites * after;
      if (out('today')) out('today').textContent = money(a);
      if (out('after')) out('after').textContent = money(b);
      if (out('saved')) out('saved').textContent = money(Math.max(0, a - b));
    }
    box.addEventListener('input', recompute);
    box.addEventListener('hd:change', recompute);
    recompute();
  });
""",
        group="Interactive",
    ),
    Component(
        "drag-rank",
        "Drag-rank list",
        "Asking someone to put priorities in order, live on a call. Drag a row or use the arrow keys "
        "when it has focus. Position drives the heat color, and the order is remembered.",
        """
<ol class="rank" data-rank data-store="gallery-rank">
  <li draggable="true" tabindex="0">Get the agenda in front of the client before the call</li>
  <li draggable="true" tabindex="0">Publish the plan to their workspace</li>
  <li draggable="true" tabindex="0">Send the one-pager as a PDF</li>
  <li draggable="true" tabindex="0">Book the follow-up while everyone is on the line</li>
</ol>
""",
        css="""
  .rank{list-style:none; margin:12px 0; padding:0; counter-reset:rank}
  .rank li{
    counter-increment:rank; position:relative; padding:12px 16px 12px 52px; margin:0 0 8px;
    background:var(--panel-2); border:1px solid var(--line); border-left:4px solid var(--acc);
    border-radius:var(--radius-sm); cursor:grab; font-size:.94rem;
    transition:border-left-color .2s, transform .12s, opacity .12s;
  }
  .rank li::before{
    content:counter(rank); position:absolute; left:14px; top:50%; transform:translateY(-50%);
    width:24px; height:24px; border-radius:50%; background:var(--acc); color:var(--panel);
    font:700 .78rem/24px var(--font-body); text-align:center;
  }
  .rank li:nth-child(1){border-left-color:var(--red)} .rank li:nth-child(1)::before{background:var(--red)}
  .rank li:nth-child(2){border-left-color:var(--amber)} .rank li:nth-child(2)::before{background:var(--amber)}
  .rank li:nth-child(3){border-left-color:var(--acc-2)} .rank li:nth-child(3)::before{background:var(--acc-2)}
  .rank li.dragging{opacity:.45; cursor:grabbing}
  .rank li.over{transform:translateX(5px)}
  .rank li:focus-visible{outline:2px solid var(--acc); outline-offset:2px}
""",
        js="""
  /* drag-rank: pointer drag plus arrow-key reorder, remembered per page */
  [].slice.call(document.querySelectorAll('[data-rank]')).forEach(function(list){
    var key = 'hd-' + (list.getAttribute('data-store') || 'rank');
    function save(){
      try {
        localStorage.setItem(key, JSON.stringify([].map.call(list.children, function(li){ return li.textContent.trim(); })));
      } catch (e) {}
    }
    try {
      var saved = JSON.parse(localStorage.getItem(key) || 'null');
      if (saved && saved.length) {
        var byText = {};
        [].forEach.call(list.children, function(li){ byText[li.textContent.trim()] = li; });
        saved.forEach(function(t){ if (byText[t]) list.appendChild(byText[t]); });
      }
    } catch (e) {}
    var dragged = null;
    list.addEventListener('dragstart', function(e){
      dragged = e.target.closest('li'); if (!dragged) return;
      dragged.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move';
    });
    list.addEventListener('dragend', function(){
      if (dragged) dragged.classList.remove('dragging');
      [].forEach.call(list.children, function(li){ li.classList.remove('over'); });
      dragged = null; save();
    });
    list.addEventListener('dragover', function(e){
      e.preventDefault();
      var over = e.target.closest('li');
      if (!over || !dragged || over === dragged) return;
      [].forEach.call(list.children, function(li){ li.classList.toggle('over', li === over); });
      var rect = over.getBoundingClientRect();
      list.insertBefore(dragged, (e.clientY - rect.top) > rect.height / 2 ? over.nextSibling : over);
    });
    list.addEventListener('keydown', function(e){
      var li = e.target.closest('li'); if (!li) return;
      if (e.key === 'ArrowUp' && li.previousElementSibling) { list.insertBefore(li, li.previousElementSibling); li.focus(); e.preventDefault(); save(); }
      if (e.key === 'ArrowDown' && li.nextElementSibling) { list.insertBefore(li.nextElementSibling, li); li.focus(); e.preventDefault(); save(); }
    });
  });
""",
        group="Interactive",
    ),
    Component(
        "checklist",
        "Tap-to-check checklist",
        "Decisions or steps to walk through live. Every tick is remembered per page, and the counter "
        "tells the reader how far through they are.",
        """
<div class="checklist" data-checklist data-store="gallery-check">
  <label><input type="checkbox"> <span>Confirm the scope in one sentence</span></label>
  <label><input type="checkbox"> <span>Agree who owns the data handover</span></label>
  <label><input type="checkbox"> <span>Pick the start date</span></label>
  <label><input type="checkbox"> <span>Book the next call before hanging up</span></label>
  <div class="check-count" data-check-count></div>
</div>
""",
        css="""
  .checklist{margin:12px 0}
  .checklist label{
    display:flex; align-items:flex-start; gap:11px; padding:11px 14px; margin:0 0 7px;
    background:var(--panel-2); border:1px solid var(--line); border-radius:var(--radius-sm);
    cursor:pointer; font-size:.94rem; transition:background .15s, border-color .15s;
  }
  .checklist label:hover{border-color:var(--acc)}
  .checklist input{margin:3px 0 0; width:17px; height:17px; accent-color:var(--green); flex:none}
  .checklist input:focus-visible{outline:2px solid var(--acc); outline-offset:2px}
  .checklist input:checked + span{color:var(--muted); text-decoration:line-through}
  .checklist label:has(input:checked){background:var(--green-soft); border-color:var(--green)}
  .check-count{font-size:.8rem; color:var(--muted); font-variant-numeric:tabular-nums; margin-top:8px}
""",
        js="""
  /* checklist: ticks remembered per page, with a live counter */
  [].slice.call(document.querySelectorAll('[data-checklist]')).forEach(function(box){
    var key = 'hd-' + (box.getAttribute('data-store') || 'check');
    var boxes = [].slice.call(box.querySelectorAll('input[type="checkbox"]'));
    var count = box.querySelector('[data-check-count]');
    try {
      var saved = JSON.parse(localStorage.getItem(key) || 'null');
      if (saved) boxes.forEach(function(b, i){ b.checked = !!saved[i]; });
    } catch (e) {}
    function paint(){
      var done = boxes.filter(function(b){ return b.checked; }).length;
      if (count) count.textContent = done + ' of ' + boxes.length + ' done';
      try { localStorage.setItem(key, JSON.stringify(boxes.map(function(b){ return b.checked; }))); } catch (e) {}
    }
    boxes.forEach(function(b){ b.addEventListener('change', paint); });
    paint();
  });
""",
        group="Interactive",
    ),
    Component(
        "decision-list",
        "Decision list with a copy-out block",
        "A list of things THE READER has to answer, each one already ticked with the recommendation, "
        "so a pass that changes nothing is still a valid answer. Every row carries its own context, "
        "one set of options with the recommended one pre-selected, and a free-text note. The button "
        "writes one plain-text block of every row's id, title, decision and note to the clipboard, "
        "which they paste back so the answers are applied in bulk. Answers survive a reload. Use it "
        "for any page whose job is to collect many small decisions at once; for a handful of live "
        "ticks on a call, the checklist above is the lighter tool.",
        """
<div class="dlist" id="decisions-demo">
  <div class="drow" data-id="D1" data-t="d1 send the reply">
    <div class="dhead"><code>D1</code><b>Send the drafted reply into the open thread</b></div>
    <div class="dmeta"><span class="chip n">2 min</span><span class="chip r">today</span></div>
    <div class="dfield"><b>What it is</b><span>One sentence of plain English that assumes the
      reader remembers nothing.</span></div>
    <div class="dfield"><b>Recommended</b><span><b>Send it as written.</b> One line saying
      why.</span></div>
    <div class="dpicks">
      <label class="dpick"><input type="radio" name="v-D1" value="Send it" checked><span>Send it</span></label>
      <label class="dpick"><input type="radio" name="v-D1" value="Edit it first"><span>Edit it first</span></label>
      <label class="dpick"><input type="radio" name="v-D1" value="Hold it"><span>Hold it</span></label>
    </div>
    <label class="dnotew"><span>A note, if you want one</span><textarea data-note="D1" rows="1"
      placeholder="optional"></textarea></label>
  </div>
  <div class="drow" data-id="D2" data-t="d2 pick the design">
    <div class="dhead"><code>D2</code><b>Pick the design that ships</b></div>
    <div class="dmeta"><span class="chip n">10 min</span></div>
    <div class="dfield"><b>What it is</b><span>Three complete designs, nothing that can send,
      and the live links beside them.</span></div>
    <div class="dfield"><b>Recommended</b><span><b>A, with B as a second view.</b> One line saying
      why.</span></div>
    <div class="dpicks">
      <label class="dpick"><input type="radio" name="v-D2" value="A" checked><span>A</span></label>
      <label class="dpick"><input type="radio" name="v-D2" value="B"><span>B</span></label>
      <label class="dpick"><input type="radio" name="v-D2" value="C"><span>C</span></label>
    </div>
    <label class="dnotew"><span>A note, if you want one</span><textarea data-note="D2" rows="1"
      placeholder="optional"></textarea></label>
  </div>
  <div class="dbar">
    <button type="button" class="dbtn" data-copy>Copy my decisions</button>
    <span class="dcount" data-said></span>
    <textarea class="dout" readonly aria-label="Your decisions, ready to paste"></textarea>
  </div>
</div>
""",
        css="""
  .dlist{margin:14px 0 0}
  .drow{
    content-visibility:auto; contain-intrinsic-size:auto 320px;
    border:1px solid var(--line); border-radius:var(--radius-sm); background:var(--panel);
    padding:13px 15px; margin:0 0 12px;
  }
  .drow[hidden]{display:none}
  .drow.changed{border-color:var(--acc); box-shadow:0 0 0 2px var(--acc-soft)}
  .dhead{display:flex; gap:10px; align-items:baseline; flex-wrap:wrap}
  .dhead code{
    font-family:var(--font-mono); font-size:12px; color:var(--acc-ink);
    background:var(--acc-soft); border-radius:6px; padding:2px 6px; flex:none;
  }
  .dhead b{font-weight:600; font-size:1.03rem; line-height:1.4}
  .dmeta{display:flex; gap:6px; flex-wrap:wrap; margin:9px 0 2px}
  .dfield{
    display:grid; grid-template-columns:168px 1fr; gap:10px; margin:8px 0 0;
    font-size:.88rem; line-height:1.62;
  }
  .dfield > *{min-width:0}
  .dfield > b{
    color:var(--muted); font-weight:600; font-size:.78rem; text-transform:uppercase;
    letter-spacing:.04em; padding-top:3px;
  }
  .dfield span b{font-weight:700; color:var(--ink); text-transform:none; letter-spacing:0;
    font-size:inherit}
  .dpicks{display:flex; gap:7px; flex-wrap:wrap; margin:12px 0 0}
  .dpick{
    display:inline-flex; align-items:center; gap:7px; font-size:.85rem; cursor:pointer;
    padding:6px 12px; border:1px solid var(--line); border-radius:999px;
    background:var(--panel-2);
  }
  .dpick:hover{border-color:var(--acc)}
  .dpick input{width:15px; height:15px; accent-color:var(--acc); margin:0; flex:none}
  .dpick:focus-within{outline:2px solid var(--acc); outline-offset:2px}
  .dpick:has(input:checked){
    background:var(--acc-soft); border-color:var(--acc); color:var(--acc-ink); font-weight:600;
  }
  .dnotew{display:block; margin:10px 0 0}
  .dnotew span{display:block; color:var(--muted); font-size:.78rem; margin:0 0 4px}
  .dnotew textarea{
    width:100%; min-height:34px; font:inherit; font-size:.85rem; line-height:1.5;
    padding:7px 9px; color:var(--ink); background:var(--panel-2);
    border:1px solid var(--line); border-radius:8px; resize:vertical;
  }
  .dnotew textarea:focus-visible{outline:2px solid var(--acc); outline-offset:2px}
  /* The bar is STICKY inside its own list here. On a whole page of decisions make it
     position:fixed with left:0; right:0; bottom:0 and give the body a matching
     padding-bottom, and keep some right padding clear if a hosting shell owns the
     bottom right corner at a higher stacking order. */
  .dbar{
    position:sticky; bottom:0; z-index:5; display:flex; flex-wrap:wrap; gap:10px;
    align-items:center; padding:10px 14px; background:var(--panel);
    border:1px solid var(--line); border-radius:var(--radius-sm); box-shadow:var(--shadow);
  }
  .dbtn{
    font:inherit; font-size:.88rem; font-weight:600; padding:8px 14px; border-radius:8px;
    cursor:pointer; background:var(--acc); color:var(--on-acc); border:1px solid var(--acc);
  }
  .dbtn.ghost{background:var(--panel-2); color:var(--ink); border-color:var(--line)}
  .dbtn:hover{filter:brightness(1.06)}
  .dbtn:focus-visible{outline:2px solid var(--acc); outline-offset:2px}
  .dcount{color:var(--muted); font-size:.82rem}
  .dout{
    display:none; width:100%; min-height:150px; margin:4px 0 0; font-family:var(--font-mono);
    font-size:.78rem; line-height:1.55; padding:10px; color:var(--ink);
    background:var(--panel-2); border:1px solid var(--line); border-radius:8px;
  }
  .dout.show{display:block}
  @media print{
    .drow{content-visibility:visible}
    .dbar,.dout,.dnotew{display:none}
  }
  @media screen and (max-width:900px){
    .dfield{grid-template-columns:1fr; gap:2px}
    .dfield > b{padding-top:6px}
  }
""",
        js="""
  /* decision list: pre-ticked answers, a note per row, remembered per page, copied as one block */
  [].slice.call(document.querySelectorAll('.dlist')).forEach(function(list){
    var rows = [].slice.call(list.querySelectorAll('.drow'));
    var btn = list.querySelector('[data-copy]');
    if (!rows.length || !btn) return;
    var said = list.querySelector('[data-said]');
    var out = list.querySelector('.dout');
    var key = 'hd-decisions-' + (list.id || 'list');
    var start = {};
    rows.forEach(function(r){
      var c = r.querySelector('input[type="radio"]:checked');
      start[r.dataset.id] = c ? c.value : '';
    });
    function pick(r){
      var c = r.querySelector('input[type="radio"]:checked');
      return c ? c.value : start[r.dataset.id];
    }
    function note(r){
      var t = r.querySelector('textarea[data-note]');
      return t ? t.value.trim() : '';
    }
    function mark(r){
      r.classList.toggle('changed', pick(r) !== start[r.dataset.id] || note(r) !== '');
    }
    function changed(){
      return rows.filter(function(r){ return r.classList.contains('changed'); }).length;
    }
    function save(){
      var obj = {};
      rows.forEach(function(r){
        if (pick(r) !== start[r.dataset.id] || note(r)) obj[r.dataset.id] = {d: pick(r), n: note(r)};
      });
      try { localStorage.setItem(key, JSON.stringify(obj)); } catch (e) {}
    }
    function refresh(){
      if (said) said.textContent = changed()
        ? changed() + ' changed, ' + (rows.length - changed()) + ' as recommended'
        : 'all ' + rows.length + ' as recommended';
    }
    try {
      var saved = JSON.parse(localStorage.getItem(key) || '{}') || {};
      rows.forEach(function(r){
        var s = saved[r.dataset.id];
        if (!s) return;
        if (s.d) [].slice.call(r.querySelectorAll('input[type="radio"]')).forEach(function(i){
          if (i.value === s.d) i.checked = true;
        });
        var t = r.querySelector('textarea[data-note]');
        if (s.n && t) t.value = s.n;
        mark(r);
      });
    } catch (e) {}
    list.addEventListener('change', function(ev){
      var r = ev.target.closest && ev.target.closest('.drow');
      if (r) { mark(r); save(); refresh(); }
    });
    list.addEventListener('input', function(ev){
      if (!ev.target.matches || !ev.target.matches('textarea[data-note]')) return;
      var r = ev.target.closest('.drow');
      ev.target.style.height = 'auto';
      ev.target.style.height = ev.target.scrollHeight + 'px';
      if (r) { mark(r); save(); refresh(); }
    });
    btn.addEventListener('click', function(){
      var lines = ['DECISIONS', rows.length + ' items. ' + changed() + ' changed.', ''];
      rows.forEach(function(r){
        var flag = pick(r) !== start[r.dataset.id] ? ' *CHANGED' : '';
        lines.push(r.dataset.id + ' | ' + r.querySelector('.dhead b').textContent + flag);
        lines.push('  decision: ' + pick(r));
        lines.push('  note: ' + (note(r) || '-'));
      });
      var text = lines.join('\\n');
      if (out) { out.value = text; out.classList.add('show'); }
      function done(ok){
        if (said) said.textContent = ok ? 'copied' : 'select the box below and copy it';
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function(){ done(true); }, function(){ done(false); });
      } else if (out) {
        out.select();
        try { document.execCommand('copy'); done(true); } catch (e) { done(false); }
      }
    });
    refresh();
  });
""",
        group="Interactive",
    ),
    Component(
        "run-of-show",
        "Run-of-show",
        "A call agenda's minute-by-minute spine: the clock, the beat, who leads it and what leaving "
        "it looks like. The one component that makes an agenda usable while the call is running.",
        """
<div class="ros">
  <div class="ros-row">
    <div class="ros-t">0:00</div>
    <div class="ros-b"><b>Where we landed last time</b><span class="ros-o">Out with: everyone agrees on the starting point</span></div>
    <div class="ros-w"><span class="chip n">US</span></div>
  </div>
  <div class="ros-row">
    <div class="ros-t">0:06</div>
    <div class="ros-b"><b>The plan, walked on screen</b><span class="ros-o">Out with: no surprises left in the scope</span></div>
    <div class="ros-w"><span class="chip n">US</span></div>
  </div>
  <div class="ros-row">
    <div class="ros-t">0:22</div>
    <div class="ros-b"><b>Questions and the parts that worry you</b><span class="ros-o">Out with: every objection named out loud</span></div>
    <div class="ros-w"><span class="chip a">THEM</span></div>
  </div>
  <div class="ros-row">
    <div class="ros-t">0:40</div>
    <div class="ros-b"><b>The date and the next step</b><span class="ros-o">Out with: a start date and the follow-up in the calendar</span></div>
    <div class="ros-w"><span class="chip g">BOTH</span></div>
  </div>
</div>
""",
        css="""
  .ros{margin:12px 0; border:1px solid var(--line); border-radius:var(--radius-sm); overflow:hidden}
  .ros-row{display:grid; grid-template-columns:70px 1fr 90px; gap:14px; align-items:start; padding:13px 16px; border-bottom:1px solid var(--line-2); background:var(--panel)}
  .ros-row:last-child{border-bottom:none}
  .ros-row:nth-child(even){background:var(--panel-2)}
  .ros-t{font-family:var(--font-mono); font-size:.86rem; font-weight:700; color:var(--acc); font-variant-numeric:tabular-nums; padding-top:1px}
  .ros-b b{display:block; font-size:.95rem; margin-bottom:2px}
  .ros-o{display:block; font-size:.82rem; color:var(--muted)}
  .ros-w{text-align:right}
  @media screen and (max-width:600px){ .ros-row{grid-template-columns:58px 1fr; } .ros-w{grid-column:2; text-align:left} }
""",
        group="Call documents",
    ),
    Component(
        "timeline",
        "Timeline, two tracks",
        "A plan with two parallel workstreams over the same weeks. Two tracks is the limit: a third "
        "stops being readable and becomes a Gantt, which belongs in a planning tool.",
        """
<div class="tl">
  <div class="tl-scale"><span>Week 1</span><span>Week 2</span><span>Week 3</span><span>Week 4</span><span>Week 5</span><span>Week 6</span></div>
  <div class="tl-track">
    <div class="tl-name">Build</div>
    <div class="tl-lane">
      <div class="tl-bar" style="--from:0; --span:3" data-tip="Data handover and the first import" data-tip-value="Weeks 1 to 3">Handover</div>
      <div class="tl-bar b" style="--from:3; --span:3" data-tip="The working system in front of you" data-tip-value="Weeks 4 to 6">First delivery</div>
    </div>
  </div>
  <div class="tl-track">
    <div class="tl-name">Review</div>
    <div class="tl-lane">
      <div class="tl-bar c" style="--from:2; --span:1" data-tip="Halfway walkthrough" data-tip-value="Week 3">Walkthrough</div>
      <div class="tl-bar c" style="--from:5; --span:1" data-tip="Sign-off on what shipped" data-tip-value="Week 6">Sign-off</div>
    </div>
  </div>
</div>
""",
        css="""
  .tl{margin:12px 0; --cols:6}
  .tl-scale{display:grid; grid-template-columns:120px repeat(var(--cols),1fr); font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px}
  .tl-scale span{grid-column:auto; padding-left:6px}
  .tl-scale span:first-child{grid-column:2}
  .tl-track{display:grid; grid-template-columns:120px 1fr; gap:12px; align-items:center; margin-bottom:8px}
  .tl-name{font-size:.82rem; font-weight:700; color:var(--muted); text-align:right}
  .tl-lane{display:grid; grid-template-columns:repeat(var(--cols),1fr); gap:0; background:var(--panel-2); border:1px solid var(--line); border-radius:8px; min-height:38px; align-items:center; padding:4px}
  .tl-bar{
    grid-column:calc(var(--from) + 1) / span var(--span);
    /* --on-acc, never a raw white: in dark mode the accent is light and white text on it
       would fail contrast. The token flips with the theme. */
    background:var(--acc); color:var(--on-acc); border-radius:6px; padding:6px 10px;
    font-size:.78rem; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }
  .tl-bar.b{background:var(--acc-2)}
  .tl-bar.c{background:var(--green)}
  @media screen and (max-width:600px){ .tl-scale,.tl-track{grid-template-columns:70px 1fr} .tl-name{font-size:.74rem} }
""",
        group="Call documents",
    ),
    Component(
        "comparison",
        "Two-column comparison with a shared band",
        "Before and after, or two options. The band underneath states the common ground once, so the "
        "reader argues about the difference rather than re-reading the same facts twice.",
        """
<div class="cmp">
  <div class="cmp-col">
    <h3>Keep it local</h3>
    <ul>
      <li>The file lives on your machine</li>
      <li>Nothing is visible to anyone else</li>
      <li>Sending it means attaching it every time</li>
    </ul>
  </div>
  <div class="cmp-col b">
    <h3>Publish a live copy</h3>
    <ul>
      <li>It sits in the other person's own rail</li>
      <li>An edit is on their screen in three seconds</li>
      <li>The link keeps working after the message scrolls away</li>
    </ul>
  </div>
  <div class="cmp-band"><b>True either way:</b> the local file stays the record, and the HTML is the format that goes into the message.</div>
</div>
""",
        css="""
  .cmp{display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:12px 0}
  .cmp-col{background:var(--panel-2); border:1px solid var(--line); border-top:4px solid var(--muted); border-radius:var(--radius-sm); padding:16px 18px}
  .cmp-col.b{border-top-color:var(--acc)}
  .cmp-col h3{margin:0 0 8px; font-size:1.02rem}
  .cmp-col ul{margin:0; padding-left:18px; font-size:.9rem}
  .cmp-band{grid-column:1 / -1; background:var(--acc-soft); border-radius:var(--radius-sm); padding:12px 16px; font-size:.9rem}
  @media screen and (max-width:700px){ .cmp{grid-template-columns:1fr} }
""",
        group="Call documents",
    ),
    Component(
        "problem-solution",
        "Problem to solution",
        "A pain and its fix, three points each, with the arrow between. The standard way to show a "
        "before and after on a client one-pager.",
        """
<div class="p2s">
  <div class="p2s-side">
    <div class="p2s-tag">Today</div>
    <ul>
      <li>Every document looks slightly different</li>
      <li>Tables cannot be sorted or searched</li>
      <li>The page width is whatever it was built at</li>
    </ul>
  </div>
  <div class="p2s-arrow" aria-hidden="true">&#8594;</div>
  <div class="p2s-side b">
    <div class="p2s-tag">After</div>
    <ul>
      <li>One look, chosen by audience, on every page</li>
      <li>Every data table filters and sorts</li>
      <li>Drag either edge to the width you want</li>
    </ul>
  </div>
</div>
""",
        css="""
  .p2s{display:grid; grid-template-columns:1fr 44px 1fr; gap:10px; align-items:center; margin:12px 0}
  .p2s-side{background:var(--panel-2); border:1px solid var(--line); border-radius:var(--radius-sm); padding:16px 18px}
  .p2s-side.b{background:var(--green-soft); border-color:var(--green)}
  .p2s-tag{font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; font-weight:700; color:var(--muted); margin-bottom:8px}
  .p2s-side.b .p2s-tag{color:var(--green-ink)}
  .p2s-side ul{margin:0; padding-left:18px; font-size:.9rem}
  .p2s-arrow{text-align:center; font-size:1.7rem; color:var(--acc); line-height:1}
  @media screen and (max-width:700px){ .p2s{grid-template-columns:1fr} .p2s-arrow{transform:rotate(90deg)} }
""",
        group="Call documents",
    ),
    Component(
        "paste",
        "Paste block",
        "A message the reader copies out of the page and sends somewhere else: a chat reply, a "
        "text message, a prompt. It is prose, not source code, so it WRAPS. A fenced block in "
        "markdown builds into this. Styled on the bare pre element in template.html, so nothing is "
        "needed here beyond the fence.",
        """
<pre><code>Hey team - the portal report is mine and I have been into it tonight. Here is what is actually going on, because it is not what it looks like.

*The report is hidden, not missing.* The campaign is in the system and syncing fine, but the switch that shows it on the portal was never turned on.</code></pre>
""",
        group="Call documents",
    ),
    Component(
        "age",
        "Countdown and computed age",
        "Any document with a clock in it. The label recomputes on open, so the page stays true without "
        "being rebuilt. Set the date in the attribute; the text is written by the script.",
        """
<p>
  Start date <b><span class="age" data-until="2026-12-01">1 December 2026</span></b>.
  The measurement behind this page was taken <b><span class="age" data-since="2026-09-16">16 September 2026</span></b>.
</p>
""",
        css="""
  .age{white-space:nowrap}
  .age[data-ago]::after{content:" (" attr(data-ago) ")"; color:var(--muted); font-weight:400}
""",
        js="""
  /* countdown and computed age: recomputed on every open, never baked in */
  [].slice.call(document.querySelectorAll('.age')).forEach(function(el){
    var until = el.getAttribute('data-until'), since = el.getAttribute('data-since');
    var target = new Date((until || since) + 'T00:00:00');
    if (isNaN(target)) return;
    var days = Math.round((target - new Date()) / 86400000);
    var weeks = Math.round(Math.abs(days) / 7);
    if (until) {
      el.setAttribute('data-ago', days > 13 ? ('in about ' + weeks + ' weeks') : days > 1 ? ('in ' + days + ' days') : days === 1 ? 'tomorrow' : days === 0 ? 'today' : ('passed ' + Math.abs(days) + ' days ago'));
    } else {
      var ago = Math.abs(days);
      el.setAttribute('data-ago', ago === 0 ? 'today' : ago === 1 ? 'yesterday' : ago > 13 ? ('about ' + weeks + ' weeks ago') : (ago + ' days ago'));
    }
  });
""",
        group="Call documents",
    ),
    Component(
        "grips",
        "Width handles",
        "On every page wider than a phone. Invisible at rest, revealed on hover or "
        "focus. Drag either edge outward to widen; double-click, Home or Escape resets; the arrow "
        "keys move it 40px at a time. The width is remembered per page.",
        """
<button class="grip l" aria-label="Narrow or widen the page from the left edge"></button>
<button class="grip r" aria-label="Narrow or widen the page from the right edge"></button>
""",
        live_on_page="Drag either edge of this window, or press the arrow keys once a grip has focus.",
        group="On every page",
    ),
    Component(
        "sidenav",
        "Right-side section nav",
        "Required on every page with two or more sections, whatever built it. Visible from the very "
        "top, never scroll-gated, hidden below 1200px and in print. The click is rAF-eased, never "
        "native smooth, because native silently jumps under reduced motion. ON A LARGE DOCUMENT it "
        "goes two-level: the PARTS are the top level and only the part the reader is in lists its "
        "sections, the rail caps its own height at the screen and takes a quiet scrollbar behind "
        "that, and the active entry is kept in view. A flat rail of forty entries rendered 1394px "
        "tall in a 900px viewport, which is a page the reader has to zoom out to 50 percent to read. "
        "Above about twelve top-level entries the builder groups a document on its "
        "own and the lint warns. The rail on THIS page is the two-level form.",
        """
<nav id="sidenav" aria-label="Sections">
  <button data-target="overview">Overview</button>
  <div class="nav-group" data-part="the-inbox-seen-whole">
    <button class="nav-part" data-target="the-inbox-seen-whole"><b>1</b>The inbox, seen whole</button>
    <div class="nav-kids">
      <button data-target="what-this-read-covers">What this read covers</button>
      <button data-target="what-this-read-cannot-see">What this read cannot…</button>
    </div>
  </div>
  <div class="nav-group" data-part="claim-one">
    <button class="nav-part" data-target="claim-one"><b>2</b>Claim one: the emails</button>
    <div class="nav-kids">
      <button data-target="the-evidence">The evidence</button>
      <button data-target="the-verdict">The verdict</button>
    </div>
  </div>
  <button data-target="links">Key links</button>
</nav>
""",
        live_on_page="The rail down the right of this page is it, in its two-level form; click any group.",
        group="On every page",
    ),
    Component(
        "theme",
        "Theme toggle",
        "Top right, never bottom right: a hosting shell may own the bottom corner. Light "
        "is the shipped default on every page; the toggle is the only way to dark, and the choice is "
        "remembered.",
        """
<button class="theme-toggle" onclick="(function(){var r=document.documentElement;var d=(r.getAttribute('data-theme')||'light')==='dark';r.setAttribute('data-theme',d?'light':'dark');try{localStorage.setItem('hd-theme',r.getAttribute('data-theme'))}catch(e){}})()">&#9680; theme</button>
""",
        live_on_page="The button at the top right of this page is it.",
        group="On every page",
    ),
    Component(
        "print",
        "Print block",
        "On every page, because these get printed and PDF'd. It hides the chrome, drops the shadows "
        "and the grid, releases the width cap, blackens links, and forces filtered and "
        "content-visibility rows back on so a printed table is complete.",
        """
<style>
@media print{
  .theme-toggle,#sidenav,.grip,#tip,.dt-controls{display:none}
  body{background:#fff; color:#000; background-image:none}
  section{box-shadow:none; break-inside:avoid; border-color:#ccc}
  .wrap{max-width:100%; padding:0}
  a{color:#000}
  table.dt tbody tr{content-visibility:visible}
  table.dt tbody tr.hide{display:table-row}
}
</style>
""",
        live_on_page="Print this page, or save it as a PDF, to see it.",
        group="On every page",
    ),
    Component(
        "lockup",
        "The maker's mark",
        "The line that says who built it, under the last block of a client build. All caps, mono, "
        "wide tracking, centered. It is OPT IN: the builder ships it only when --mark passes the text, "
        "no template carries a default, and an internal document never wears one.",
        """
<div class="lockup">Built by the studio that made it</div>
""",
        group="On every page",
    ),
    Component(
        "classic-header",
        "The classic header",
        "The formal cover: eyebrow, title, lede, and the prepared-for row over a 2px accent rule. This "
        "is what the cover looks like under <code>data-look=\"classic\"</code>, which is the look for "
        "formal reports and deliverables. Everything else on the page is identical between the looks.",
        """
<div data-look="classic" class="look-demo">
  <header class="cover">
    <div class="eyebrow">Quarterly review</div>
    <h1>Where the quarter landed</h1>
    <p class="lede">What moved, what did not, and the two decisions that carry into next quarter.</p>
    <div class="cover-meta">
      <span><b>Prepared for</b> the founders</span>
      <span><b>From</b> the operations desk</span>
      <span><b>Date</b> September 16, 2026</span>
    </div>
  </header>
</div>
""",
        css="""
  /* a look demo: scope the classic tokens to one block so both looks show on one page */
  .look-demo[data-look="classic"]{
    --bg:#f7f5f1; --panel:#ffffff; --panel-2:#fbfaf7; --ink:#1c1a17; --muted:#6b655c;
    --line:#e6e1d8; --line-2:#efebe3;
    --acc:#b8862f; --acc-2:#8a6320; --acc-soft:#f3e9d4; --acc-ink:#6d4f19;
    background:var(--bg); color:var(--ink); border-radius:var(--radius-sm); padding:20px 22px 4px;
  }
""",
        group="On every page",
    ),
]


# --------------------------------------------------------------------------- assembly


def replace_block(text: str, name: str, body: str) -> str:
    pattern = rf"(<!--\s*{re.escape(name)}\s*-->)(.*?)(<!--\s*/{re.escape(name)}\s*-->)"
    return re.sub(pattern, lambda m: m.group(1) + body + m.group(3), text, flags=re.S)


def snippet_block(label: str, code: str, language: str) -> str:
    if not code.strip():
        return ""
    return (
        f'      <details class="snip">\n'
        f'        <summary>{esc(label)}</summary>\n'
        f'        <pre class="code" data-lang="{language}"><code>{esc(code)}</code></pre>\n'
        f"      </details>\n"
    )


def anchor(cid: str) -> str:
    """Gallery section ids are namespaced.

    A component id is the component's own name, and some of those names ARE house ids: the
    section called "sidenav" collided with the real <nav id="sidenav"> and gave the document two
    elements sharing one id, which left the rail's own demo dead. The prefix makes a collision
    impossible for every present and future component.
    """
    return f"c-{cid}"


def diagram_markup(component: Component) -> str:
    """The live SVG for a diagram component, rendered by the builder, not written by hand."""
    from build import diagram_blocks  # late: build.py imports this module for the catalogue

    kind, caption, source = component.diagram
    hint = f"[diagram: {kind} | {caption}]" if caption else f"[diagram: {kind}]"
    rendered = f"<p>{hint}</p>\n<pre><code>{html.escape(source, quote=False)}</code></pre>"
    markup, used = diagram_blocks(rendered, prefix=f"g{component.cid}-")
    if not used:  # pragma: no cover - only if the hint syntax and the matcher ever disagree
        raise SystemExit(f"the gallery's {component.cid} demo did not render")
    return markup


def component_section(component: Component) -> str:
    if component.diagram:
        kind, caption, source = component.diagram
        hint = f"[diagram: {kind} | {caption}]" if caption else f"[diagram: {kind}]"
        markdown_source = f"{hint}\n\n```\n{source.strip()}\n```"
        return (
            f'  <section id="{anchor(component.cid)}">\n'
            f'    <div class="sec-num">{esc(component.title)}</div>\n'
            f'    <p class="sub">{component.when}</p>\n'
            f'    <div class="demo">\n{diagram_markup(component)}\n    </div>\n'
            f"{snippet_block('Copy the markdown', markdown_source, 'md')}"
            '      <p class="sub note">No CSS or JavaScript to copy: the builder ships the diagram '
            "styles with the page whenever a diagram is on it, and the SVG is already inside the "
            "file.</p>\n"
            f"  </section>\n"
        )
    snippets = snippet_block("Copy the HTML", component.markup, "html")
    snippets += snippet_block("Copy the CSS", component.css, "css")
    snippets += snippet_block("Copy the JavaScript", component.js, "js")
    if not component.css and not component.js:
        snippets += (
            '      <p class="sub note">No extra CSS or JavaScript: the base template already '
            "carries this one.</p>\n"
        )
    if component.live_on_page:
        demo = f'    <div class="demo live"><b>Already live on this page.</b> {component.live_on_page}</div>\n'
    else:
        demo = f'    <div class="demo">\n{component.markup}\n    </div>\n'
    return (
        f'  <section id="{anchor(component.cid)}">\n'
        f'    <div class="sec-num">{esc(component.title)}</div>\n'
        f'    <p class="sub">{component.when}</p>\n'
        f"{demo}"
        f"{snippets}"
        f"  </section>\n"
    )


GALLERY_CSS = """
  /* ---- the gallery's own chrome (not part of the house components) ---- */
  .demo{background:var(--bg); border:1px dashed var(--line); border-radius:var(--radius-sm); padding:18px 20px; margin:6px 0 12px}
  .demo > :first-child{margin-top:0}
  .demo > :last-child{margin-bottom:0}
  details.snip{border:1px solid var(--line); border-radius:8px; margin:0 0 7px; background:var(--panel-2)}
  details.snip > summary{cursor:pointer; padding:8px 13px; font-size:.82rem; font-weight:700; color:var(--acc); list-style:none}
  details.snip > summary::-webkit-details-marker{display:none}
  details.snip > summary::before{content:"\\203A "; display:inline-block; transition:transform .15s; margin-right:6px}
  details.snip[open] > summary::before{transform:rotate(90deg)}
  pre.code{
    margin:0; padding:13px 15px; overflow-x:auto; font-family:var(--font-mono); font-size:.79rem;
    line-height:1.55; background:var(--panel); border-top:1px solid var(--line); color:var(--ink);
    border-radius:0 0 8px 8px; white-space:pre;
  }
  p.sub.note{margin:0 0 6px; font-style:italic}
  .demo.live{background:var(--acc-soft); border-style:solid; border-color:var(--acc); font-size:.92rem}
"""


def grouped() -> list[tuple[str, list[Component]]]:
    """The catalogue in page order, as (group name, its components). Groups stay contiguous.

    The rail's order has to match the page's order, because the highlight is driven by which
    section is on screen: a group whose sections are scattered down the page would open and close
    as the reader scrolls past unrelated content.
    """
    out: list[tuple[str, list[Component]]] = []
    for component in COMPONENTS:
        if not out or out[-1][0] != component.group:
            out.append((component.group, []))
        out[-1][1].append(component)
    return out


def nav_groups() -> str:
    """The gallery wears the LARGE-DOCUMENT rail, because it is a large document.

    Two dozen flat entries is a rail the reader has to zoom out to 50 percent to read. The groups
    are the top level; the template's script opens the one the reader is in.
    """
    lines: list[str] = []
    for name, members in grouped():
        lines.append(f'  <div class="nav-group" data-part="{anchor(slug(name))}">')
        lines.append(f'    <button class="nav-part" data-target="{anchor(members[0].cid)}">{esc(name)}</button>')
        lines.append('    <div class="nav-kids">')
        lines += [f'      <button data-target="{anchor(c.cid)}">{esc(clip(c.nav))}</button>' for c in members]
        lines.append("    </div>")
        lines.append("  </div>")
    return "\n".join(lines)


def toc_groups() -> str:
    """The contents block follows the same tree, so the two never disagree about the shape."""
    out: list[str] = []
    number = 0
    for name, members in grouped():
        rows = []
        for component in members:
            number += 1
            rows.append(f'        <a href="#{anchor(component.cid)}"><b>{number}</b>{esc(component.title)}</a>')
        out.append(
            f'    <div class="toc-part">\n'
            f'      <a class="toc-part-name" href="#{anchor(members[0].cid)}">{esc(name)}</a>\n'
            f'      <div class="toc toc-kids">\n' + "\n".join(rows) + "\n      </div>\n    </div>"
        )
    return "\n".join(out)


CLIENT_SAFE_SECTION = """
  <section id="client-safe">
    <div class="sec-num">Before anything leaves the building</div>
    <h2>Client-safe by construction</h2>
    <p class="sub">A page is read by somebody who was never told which other companies exist. It should
       be impossible to hand them one that says.</p>
    <ul>
      <li><b>The tokens name nothing.</b> The look is <code>tint</code> or <code>classic</code>, never a
          client's initials or a product's name.</li>
      <li><b>The builder strips what a reader never needs</b> from the page it emits: every CSS comment,
          every HTML comment, and the maker's-mark rules on a page that renders no mark.</li>
      <li><b>The maker's mark is opt in.</b> It ships only when the build line passes the text for it.
          No template carries a company name as a default value.</li>
      <li><b>The lint reads the whole file</b>, not the visible words: attributes, comments and the
          stylesheet too, against the wall list that lives beside it. On a page for anybody outside the
          company it is a refusal; anywhere else it is a note. The page names its own audience, so
          nobody has to remember a flag.</li>
    </ul>
  </section>

"""


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build(destination: Path) -> str:
    base = BASE.read_text(encoding="utf-8-sig")

    body_parts = [
        """
  <header class="cover">
    <div class="eyebrow">House design system</div>
    <h1>The components gallery</h1>
    <p class="lede">Every component an HTML deliverable may use, live on this page, each with the exact
       markup that produced it. Paste a block into a copy of <code>template.html</code> and it works.
       This gallery and <code>DESIGN.md</code> are the only sources for how a page looks; nothing is
       ever rebuilt from an older document or from memory.</p>
    <div class="cover-meta">
      <span><b>Look</b> tint, one attribute away from classic</span>
      <span><b>Theme</b> light, toggle top right</span>
      <span><b>Width</b> drag either edge of the screen</span>
    </div>
  </header>

  <div class="verdict">
    <strong>&#10004; How to use this page:</strong> find the component, open the fold under it, copy the
    HTML and, where there is one, the CSS and the JavaScript. Every snippet is self-sufficient in a page
    built from <code>template.html</code>.
  </div>

  <section id="contents">
    <div class="sec-num">Contents</div>
"""
    ]
    body_parts.append(toc_groups())
    body_parts.append("\n  </section>\n\n")
    body_parts.append(CLIENT_SAFE_SECTION)
    body_parts.extend(component_section(c) for c in COMPONENTS)
    body_parts.append(
        '\n  <div class="foot">This gallery is generated by the gallery builder in this folder, so a snippet\n'
        "     and the demo above it are the same text by construction. Add a component there, never by hand\n"
        "     here.</div>\n"
    )

    nav = nav_groups()

    from build import DIAGRAM_CSS  # late, for the same cycle reason as the strip below

    css = GALLERY_CSS + "\n" + "\n".join(c.css for c in COMPONENTS if c.css)
    if any(c.diagram for c in COMPONENTS):
        # ONE definition: the diagram styles live in build.py beside the code that pre-renders
        # the SVG, and the gallery reads that same string rather than keeping a second copy.
        css += "\n" + DIAGRAM_CSS.strip("\n")
    js_parts = [c.js for c in COMPONENTS if c.js]
    js = "(function(){\n" + "\n".join(js_parts) + "\n})();"

    page = base.replace(
        "  /* BUILD:CSS - build.py appends the chosen surface's extra CSS here. Leave the marker in place. */",
        "  /* ---- gallery ---- */\n" + css,
    )
    page = replace_block(page, "BUILD:NAV", "\n" + nav + "\n  ")
    page = replace_block(page, "BUILD:BODY", "\n" + "".join(body_parts) + "\n  ")
    page = page.replace("<title>REPLACE - Document Title</title>", "<title>The components gallery</title>")
    # The gallery is an INTERNAL document and says so, so the lint treats a wall-list name in it
    # as a note rather than a refusal. It keeps its comments, which are its subject matter.
    page = page.replace('data-look="classic"', 'data-audience="internal" data-look="tint"', 1)
    # Imported here, not at the top: build.py imports THIS module for the component catalogue, so a
    # module-level import back into it would be a cycle. The rewrite has one definition either way.
    from build import new_tab_links

    # The gallery is a served page like any other, so it obeys the new-tab rule it documents.
    page = new_tab_links(page)
    page = page.replace("</body>", f"<script>\n{js}\n</script>\n</body>")

    destination.write_text(page, encoding="utf-8")
    return page


def main(argv: list[str]) -> int:
    destination = Path(argv[1]) if len(argv) > 1 else HERE / "components.html"
    page = build(destination)
    print(f"built {destination} ({len(page):,} bytes, {len(COMPONENTS)} components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
