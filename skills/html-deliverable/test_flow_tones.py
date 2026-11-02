"""A flow node's tone needs its soft and ink pair, or the lint refuses it.

The flow renderer fills a node with `var(--<tone>-soft, var(--panel))` and writes its note in
`var(--<tone>-ink, var(--muted))`. The template declares `--acc-2` and no `--acc-2-soft` or
`--acc-2-ink`, so an `acc-2` node filled with the panel color in silence, and the gallery's own demo
colored its "They reply" node that way: a reader saw a white box where a colored one was meant. The
stat card's tone already had the same refusal; this carries it to the flow.

The tones are read from the page's own CSS, never from a list in the lint: a node tone passes when
the page defines `--<tone>`, `--<tone>-soft` and `--<tone>-ink`; a lane, edge or mark tone when it
defines `--<tone>`. So the day the template gains an `acc-2` pair, `acc-2` passes with no change here.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import lint
HERE = Path(__file__).resolve().parent


def _component(cid: str):
    from build_gallery import COMPONENTS

    hit = [c for c in COMPONENTS if c.cid == cid]
    assert hit, f"{cid} is not in the gallery catalogue"
    return hit[0]

STYLE = (
    "<style>:root{--acc:#1f3a5f; --acc-soft:#e8eef5; --acc-ink:#12243c; --acc-2:#0e7490;"
    " --green:#2f6b3a; --green-soft:#e6f0e8; --green-ink:#1d4424; --muted:#6b655c}</style>"
)


def page(data: dict, style: str = STYLE) -> str:
    return (
        f"<html><head>{style}</head><body>"
        '<figure class="flow" aria-label="The path">'
        f'<script type="application/json" class="flow-data">{json.dumps(data)}</script>'
        "</figure></body></html>"
    )


def flow(nodes: list[dict], lanes: list[dict] | None = None, edges: list[dict] | None = None) -> dict:
    return {
        "lanes": lanes or [{"id": "a", "label": "A", "tone": "acc"}],
        "nodes": nodes,
        "edges": edges or [],
    }


class FlowTones(unittest.TestCase):
    def test_a_node_tone_with_no_soft_pair_is_refused_by_name(self):
        html = page(flow([{"id": "reply", "col": 0, "lane": "a", "label": "They reply", "tone": "acc-2"}]))
        found = lint.flow_tone_findings(html)
        self.assertEqual(len(found), 1, found)
        self.assertIn('node "They reply"', found[0])
        self.assertIn("`acc-2`", found[0])
        self.assertIn("--acc-2-soft", found[0])
        self.assertIn("acc, green", found[0], "the message lists the tones this page can color a node with")

    def test_a_known_tone_and_no_tone_at_all_pass(self):
        html = page(flow([
            {"id": "x", "col": 0, "lane": "a", "label": "Green", "tone": "green"},
            {"id": "y", "col": 1, "lane": "a", "label": "The default, acc"},
        ]))
        self.assertEqual(lint.flow_tone_findings(html), [])

    def test_a_lane_or_edge_tone_needs_only_its_base_token(self):
        ok = page(flow([{"id": "x", "col": 0, "lane": "b", "label": "X"}],
                       lanes=[{"id": "b", "label": "B", "tone": "acc-2"}]))
        self.assertEqual(lint.flow_tone_findings(ok), [])
        bad = page(flow([{"id": "x", "col": 0, "lane": "b", "label": "X"}],
                        lanes=[{"id": "b", "label": "B", "tone": "blue"}],
                        edges=[{"from": "x", "to": "x", "tone": "teal"}]))
        found = lint.flow_tone_findings(bad)
        self.assertEqual(len(found), 2, found)
        self.assertTrue(any('lane "B"' in f and "`blue`" in f for f in found), found)
        self.assertTrue(any("edge" in f and "`teal`" in f for f in found), found)

    def test_the_pair_defined_on_the_page_clears_the_tone(self):
        style = STYLE.replace("--acc-2:#0e7490;", "--acc-2:#0e7490; --acc-2-soft:#e0f2f5; --acc-2-ink:#0b4f5c;")
        html = page(flow([{"id": "reply", "col": 0, "lane": "a", "label": "They reply", "tone": "acc-2"}]), style)
        self.assertEqual(lint.flow_tone_findings(html), [])

    def test_check_refuses_it(self):
        html = page(flow([{"id": "reply", "col": 0, "lane": "a", "label": "They reply", "tone": "acc-2"}]))
        failures = lint.check(html, money=False, allow_commands=False)[0]
        self.assertTrue(any("flow" in f and "`acc-2`" in f for f in failures), failures)

    def test_the_gallery_colors_no_node_without_its_pair_and_its_entry_names_the_tones(self):
        gallery = (HERE / "components.html").read_text(encoding="utf-8")
        self.assertEqual(lint.flow_tone_findings(gallery), [])
        when = _component("flow").when
        self.assertIn("acc, green, amber, red, violet and ask, or muted for a box that is off", when)

    # ---- a code review's findings, and a source fragment

    def test_a_muted_node_is_the_neutral_box_and_passes(self):
        """A page may draw a box that is off as a muted node."""
        html = page(flow([{"id": "m", "col": 0, "lane": "a", "label": "Not connected", "note": "DARK", "tone": "muted"}]))
        self.assertEqual(lint.flow_tone_findings(html), [])

    def test_a_pair_set_inline_on_the_figure_counts_and_one_in_a_comment_does_not(self):
        node = [{"id": "t", "col": 0, "lane": "a", "label": "Teal", "tone": "teal"}]
        inline = page(flow(node)).replace(
            '<figure class="flow"', '<figure style="--teal:#0e7490; --teal-soft:#e0f2f5; --teal-ink:#0b4f5c" class="flow"'
        )
        self.assertEqual(lint.flow_tone_findings(inline), [])
        commented = page(flow(node), STYLE.replace("</style>", "/* --teal:#0; --teal-soft:#1; --teal-ink:#2; */</style>"))
        self.assertEqual(len(lint.flow_tone_findings(commented)), 1)

    def test_a_soft_fill_without_its_ink_is_refused(self):
        style = STYLE.replace("--acc-2:#0e7490;", "--acc-2:#0e7490; --acc-2-soft:#e0f2f5;")
        html = page(flow([{"id": "r", "col": 0, "lane": "a", "label": "Half a pair", "tone": "acc-2"}]), style)
        self.assertEqual(len(lint.flow_tone_findings(html)), 1)

    def test_a_node_with_no_tone_is_read_as_acc(self):
        style = STYLE.replace(" --acc-soft:#e8eef5;", "")
        html = page(flow([{"id": "n", "col": 0, "lane": "a", "label": "No tone given"}]), style)
        found = lint.flow_tone_findings(html)
        self.assertEqual(len(found), 1, found)
        self.assertIn("`acc`", found[0])

    def test_a_source_fragment_with_no_tokens_is_not_judged(self):
        """A composed page's `source/` body carries the flow and no stylesheet; the page built
        from it is what the lint judges."""
        html = page(flow([{"id": "r", "col": 0, "lane": "a", "label": "They reply", "tone": "acc-2"}]), style="")
        self.assertEqual(lint.flow_tone_findings(html), [])
        # a fragment may carry a timeline's inline position tokens and still have no theme
        gantt = '<div class="tl-bar" style="--from:1; --span:3; --fq:1; --sq:1">Build</div>'
        self.assertEqual(lint.flow_tone_findings(gantt + html), [])


if __name__ == "__main__":
    unittest.main()
