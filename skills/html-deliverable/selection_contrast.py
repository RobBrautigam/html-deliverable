"""Is a page's selected text readable on every block it can be selected in?

A reader who highlights a sentence inside a tinted callout must see the highlight. The house
template once shipped `::selection{background:var(--acc-soft)}`, and its callouts, inline code and
code blocks are painted `var(--acc-soft)` too: a selection inside one was the block's own color, a
contrast of exactly 1.0, and the highlighted text vanished.

`lint.py` refuses a page whose own selection fails here. A server that hosts pages it did not build
can use the same measure: `page_selection_readable` decides whether a stored page's selection reads,
and `SELECTION_STYLE` is a style block to lay over the page only when it does not.

THE MEASURE (WCAG 2.x relative luminance). Selected text on the selection: at least 4.5 (SC 1.4.3,
body text). The selection against the block it sits on: at least 3.0 (SC 1.4.11, a state the reader
must see). A translucent selection is composited over each block first, the way a browser paints it.

WHICH BLOCKS. Every background the page's own CSS declares, in each mode, that its body text reads on
(the page ink on it at 4.5 or better): a white card, a tinted callout, a striped table row. A solid
accent fill carries its own light text and is not a reading block (the column grip is one), so a dark
selection is not failed for sitting near it.

THE SELECTION. Ink inverted, the reading of the best-made docs (Vercel's docs: `--geist-selection` is
its gray-1000 text color, with gray-100 text): near-black with white text in Light mode, near-white
with the page's dark ground for text in Dark mode. The ink already reads on every block, because the
body text is written in it, so its inverse is visible on every block by construction. Standard
library only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# The served selection, per mode: (background, text). Light: near-black, the Dark mode panel, with
# white. Dark: the Dark mode ink with the Dark mode ground.
SELECTION: dict[str, tuple[str, str]] = {
    "light": ("#1d1e20", "#ffffff"),
    "dark": ("#f0f1f2", "#161719"),
}
TEXT_FLOOR = 4.5
BLOCK_FLOOR = 3.0

_DARK_ATTR = '[data-theme="dark"]'
# (0,4,1) and (0,5,1): above a page's own `::selection` (0,0,1) and a scoped `.callout ::selection`
# (0,1,1) whatever order the page writes its styles in, without `!important`. The dark rule beats
# the light one. `::-moz-selection` is its own rule: in a selector list with `::selection`, a browser
# that does not know it drops the whole list.
_LIGHT_SCOPE = ":root:root:root:root"
_DARK_SCOPE = ":root" + _DARK_ATTR * 4


def selection_css() -> str:
    out = []
    for scope, (bg, fg) in ((_LIGHT_SCOPE, SELECTION["light"]), (_DARK_SCOPE, SELECTION["dark"])):
        for pseudo in ("::selection", "::-moz-selection"):
            out.append(f"{scope} {pseudo}{{background:{bg};color:{fg}}}")
    return "".join(out)


SELECTION_STYLE = f"<style data-selection>{selection_css()}</style>"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

Color = tuple[float, float, float, float]  # r, g, b in 0..255, alpha in 0..1

_NAMED: dict[str, Color] = {
    "white": (255, 255, 255, 1.0),
    "black": (0, 0, 0, 1.0),
    "transparent": (0, 0, 0, 0.0),
}
_HEX = re.compile(r"#([0-9a-f]{3,8})", re.I)
_FUNC = re.compile(r"(rgba?|hsla?)\(([^()]*)\)", re.I)


def _num(token: str, scale: float) -> float:
    token = token.strip()
    if token.endswith("%"):
        return float(token[:-1]) * scale / 100.0
    return float(token)


def parse_color(value: str | None) -> Color | None:
    """One CSS color: hex, rgb(a), hsl(a) or a few names. None for anything else."""
    if not value:
        return None
    v = value.strip().lower()
    if v in _NAMED:
        return _NAMED[v]
    m = _HEX.fullmatch(v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
    m = _FUNC.fullmatch(v)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) not in (3, 4):
        return None
    try:
        alpha = _num(parts[3], 1.0) if len(parts) == 4 else 1.0
        if m.group(1).startswith("rgb"):
            r, g, b = (_num(p, 255.0) for p in parts[:3])
        else:
            hue = float(parts[0].rstrip("deg")) % 360
            s, light = _num(parts[1], 1.0), _num(parts[2], 1.0)
            r, g, b = _hsl_to_rgb(hue, s, light)
    except ValueError:
        return None
    return (r, g, b, max(0.0, min(1.0, alpha)))


def _hsl_to_rgb(h: float, s: float, light: float) -> tuple[float, float, float]:
    c = (1 - abs(2 * light - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = light - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return ((r + m) * 255, (g + m) * 255, (b + m) * 255)


def over(top: Color, under: Color) -> Color:
    """`top` painted over an opaque `under`, the way a browser composites a translucent fill."""
    a = top[3]
    return (top[0] * a + under[0] * (1 - a), top[1] * a + under[1] * (1 - a),
            top[2] * a + under[2] * (1 - a), 1.0)


def luminance(c: Color) -> float:
    def ch(v: float) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a: Color, b: Color) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hex_of(c: Color) -> str:
    return "#" + "".join(f"{round(v):02x}" for v in c[:3])

# ---------------------------------------------------------------------------
# The page's CSS
# ---------------------------------------------------------------------------

_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
_COMMENT = re.compile(r"/\*.*?(?:\*/|\Z)", re.S)
_HTML_TAG = re.compile(r"<html\b([^>]*)>", re.I)
_TAG_ATTR = re.compile(r"""([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")
_SEL_ATTR = re.compile(r"""\[\s*([\w-]+)\s*(?:([~|^$*]?=)\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]*)))?\s*\]""")
_ROOT_ONLY = re.compile(r"^\s*(?::root|html)((?:\[[^\]]*\])*)\s*$", re.I)
_SELECTION = re.compile(r"::(?:-moz-)?selection\b", re.I)
_GLOBAL_SCOPE = re.compile(r"^(?:\s|\*|:root|html|body|\[[^\]]*\]|:where\(\s*:root\s*\))*$", re.I)
_DARK = re.compile(r"""\[\s*data-theme\s*=\s*["']?dark["']?\s*\]""", re.I)
_LIGHT = re.compile(r"""\[\s*data-theme\s*=\s*["']?light["']?\s*\]""", re.I)
_NOT_DARK = re.compile(r""":not\([^)]*data-theme\s*=\s*["']?dark""", re.I)


def _skip_string(css: str, i: int) -> int:
    quote, j, n = css[i], i + 1, len(css)
    while j < n:
        if css[j] == "\\":
            j += 2
            continue
        if css[j] == quote:
            return j + 1
        j += 1
    return n


def _rules(css: str) -> list[tuple[str, str]]:
    """Every style rule's (prelude, body), screen media kept and print dropped, in source order."""
    out: list[tuple[str, str]] = []
    i, n, start = 0, len(css), 0
    while i < n:
        ch = css[i]
        if ch in "\"'":
            i = _skip_string(css, i)
            continue
        if ch in ";}":
            start = i + 1
        elif ch == "{":
            prelude = css[start:i].strip()
            depth, j = 1, i + 1
            while j < n and depth:
                cj = css[j]
                if cj in "\"'":
                    j = _skip_string(css, j)
                    continue
                depth += (cj == "{") - (cj == "}")
                j += 1
            body = css[i + 1:j - 1]
            low = prelude.lower()
            if low.startswith("@media"):
                if not re.search(r"\bprint\b", low) or re.search(r"\bscreen\b", low):
                    out += _rules(body)
            elif low.startswith(("@supports", "@layer", "@container", "@scope")):
                out += _rules(body)
            elif not low.startswith("@"):
                out.append((prelude, body))
            i = start = j
            continue
        i += 1
    return out


def _split(prelude: str) -> list[str]:
    parts, cur, depth = [], [], 0
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur).strip())
    return [p for p in parts if p]


def _decls(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in re.split(r";(?![^(]*\))", body):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        name = name.strip().lower()
        value = re.sub(r"!\s*important\s*$", "", value.strip(), flags=re.I).strip()
        if name and value:
            out[name] = value
    return out


def _root_attrs(html: str) -> dict[str, str]:
    m = _HTML_TAG.search(html)
    if not m:
        return {}
    out: dict[str, str] = {}
    for a, q, s, b in _TAG_ATTR.findall(m.group(1)):
        out.setdefault(a.lower(), q or s or b)  # a repeated attribute: the first wins, as in a browser
    return out


def _root_applies(attrs: str, mode: str, root: dict[str, str]) -> bool:
    for name, op, q, s, b in _SEL_ATTR.findall(attrs):
        name = name.lower()
        want = next((g for g in (q, s, b) if g), "")
        have = mode if name == "data-theme" else root.get(name)
        if have is None:
            return False
        if op and want != have:
            return False
    return True


def _mode_of(selector: str) -> str | None:
    """'dark' or 'light' when a selector holds for one mode only, else None (both)."""
    if _DARK.search(selector) and not _NOT_DARK.search(selector):
        return "dark"
    if _LIGHT.search(selector) or _NOT_DARK.search(selector):
        return "light"
    return None


def _first_color(value: str, palette: dict[str, str], depth: int = 0) -> Color | None:
    """The color a `background` or `color` value paints, var() resolved, else None."""
    for token in _tokens(value):
        c = _resolve(token, palette, depth)
        if c is not None:
            return c
    return None


def _tokens(value: str) -> list[str]:
    out, cur, depth = [], [], 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


def _resolve(token: str, palette: dict[str, str], depth: int) -> Color | None:
    token = token.strip()
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,(.*))?\)", token, re.S)
    if m:
        if depth > 8:
            return None
        if m.group(1) in palette:
            return _first_color(palette[m.group(1)], palette, depth + 1)
        return _first_color(m.group(2), palette, depth + 1) if m.group(2) else None
    return parse_color(token)

# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    mode: str
    selector: str
    what: str  # "text" or "block"
    ratio: float
    selection: str
    against: str
    where: str

    def line(self) -> str:
        floor = TEXT_FLOOR if self.what == "text" else BLOCK_FLOOR
        if self.what == "text":
            return (f"{self.mode} mode: selected text {self.against} on the selection {self.selection} "
                    f"is {self.ratio:.2f}:1, under {floor}:1 ({self.selector})")
        return (f"{self.mode} mode: the selection {self.selection} on {self.where} ({self.against}) "
                f"is {self.ratio:.2f}:1, under {floor}:1, so a selection there cannot be seen "
                f"({self.selector})")


@dataclass
class Report:
    rules: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    unmeasured: list[str] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        """The page has its own selection and every one of them reads in every mode it has."""
        return bool(self.rules) and not self.findings and not self.unmeasured


def _palette(rules: list[tuple[str, str]], mode: str, root: dict[str, str],
             overlay: dict[str, str] | None) -> dict[str, str]:
    applied: list[tuple[int, int, dict[str, str]]] = []
    for index, (prelude, body) in enumerate(rules):
        for sel in _split(prelude):
            m = _ROOT_ONLY.match(sel)
            if not m or not _root_applies(m.group(1), mode, root):
                continue
            decls = {k: v for k, v in _decls(body).items() if k.startswith("--")}
            if decls:
                applied.append((len(_SEL_ATTR.findall(m.group(1))), index, decls))
    palette: dict[str, str] = {}
    for _, _, decls in sorted(applied, key=lambda t: (t[0], t[1])):
        palette.update(decls)
    if mode == "dark" and overlay:
        palette.update({(k if k.startswith("--") else f"--{k}"): v for k, v in overlay.items()})
    return palette


def page_report(html: str, dark_overlay: dict[str, str] | None = None) -> Report:
    """Every selection rule of the page, measured on every reading block in every mode it has.

    `dark_overlay` is the variables a server lays over the page's dark, if it lays any, names with
    or without their dashes.
    """
    css = "".join(_COMMENT.sub(" ", m.group(1)) for m in _STYLE.finditer(html or ""))
    rules = _rules(css)
    root = _root_attrs(html or "")
    report = Report()
    report.modes = ["light"] + (["dark"] if _DARK.search(css) else [])

    # (selector, (specificity, source order), declarations, global?) for every selection selector.
    selections: list[tuple[str, tuple, dict[str, str], bool]] = []
    for index, (prelude, body) in enumerate(rules):
        sels = [s for s in _split(prelude) if _SELECTION.search(s)]
        if sels:
            report.rules.append(", ".join(sels))
        for sel in sels:
            scope = _SELECTION.sub("", sel)
            selections.append((sel, (_specificity(scope), index), _decls(body),
                               bool(_GLOBAL_SCOPE.match(scope))))
    # `::selection` and `::-moz-selection` are separate cascades: a browser keeps the one it knows
    # and drops the other, so a good `-moz-` rule never covers for a bad `::selection` one.
    kinds = [[s for s in selections if ("-moz-" in s[0].lower()) == moz] for moz in (False, True)]

    for mode in report.modes:
        palette = _palette(rules, mode, root, dark_overlay)
        ground = _resolve("var(--bg)", palette, 0) or (
            (255, 255, 255, 1.0) if mode == "light" else (22, 23, 25, 1.0))
        ink = (_resolve("var(--ink)", palette, 0)
               or (_body_color(rules, mode, palette))
               or ((0, 0, 0, 1.0) if mode == "light" else (240, 241, 242, 1.0)))
        surfaces = _surfaces(rules, mode, palette, ground, ink)
        # The cascade, per mode: the page-wide selection is what wins among the page-wide rules that
        # hold in this mode, property by property; a scoped rule is measured only where it beats it.
        measured: list[tuple[str, dict[str, str]]] = []
        for kind in kinds:
            live = sorted((s for s in kind if _mode_of(s[0]) in (None, mode)), key=lambda s: s[1])
            page_wide: dict[str, str] = {}
            top: tuple = ((0, 0, 0), -1)
            names: list[str] = []
            for sel, rank, decls, is_global in live:
                if is_global:
                    page_wide.update({k: v for k, v in decls.items()
                                      if k in ("background", "background-color", "color")})
                    top, names = rank, names + [sel]
            measured += [(names[-1], page_wide)] if names else []
            measured += [(sel, {**page_wide, **decls}) for sel, rank, decls, is_global in live
                         if not is_global and rank > top]
        for selector, decls in measured:
            raw_bg = decls.get("background-color") or decls.get("background")
            if raw_bg is None:
                continue  # the browser's own highlight, which this page does not set
            bg = _first_color(raw_bg, palette)
            if bg is None:
                report.unmeasured.append(f"{mode} mode: the selection's background {raw_bg!r} "
                                         f"could not be measured ({selector})")
                continue
            fg = _first_color(decls["color"], palette) if "color" in decls else None
            for where, surface in surfaces:
                painted = over(bg, surface)
                text = over(fg, painted) if fg else ink
                t = contrast(text, painted)
                if t < TEXT_FLOOR:
                    report.findings.append(Finding(mode, selector, "text", t, hex_of(painted),
                                                   hex_of(text), where))
                    break
                b = contrast(painted, surface)
                if b < BLOCK_FLOOR:
                    report.findings.append(Finding(mode, selector, "block", b, hex_of(painted),
                                                   hex_of(surface), where))
    return report


def _specificity(selector: str) -> tuple[int, int, int]:
    """(ids, classes and attributes and pseudo-classes, types): `:where()` counts nothing."""
    s = re.sub(r":where\([^()]*\)", "", selector)
    ids = len(re.findall(r"#[\w-]+", s))
    classes = len(re.findall(r"\.[\w-]+|\[[^\]]*\]|(?<!:):(?!:)[\w-]+", s))
    types = len(re.findall(r"(?:^|[\s>+~(])(?![\d])([a-z][\w-]*)", s, re.I))
    return (ids, classes, types)


def _body_color(rules: list[tuple[str, str]], mode: str, palette: dict[str, str]) -> Color | None:
    for prelude, body in reversed(rules):
        for sel in _split(prelude):
            if re.fullmatch(r"\s*(?:body|html|:root)\s*", sel, re.I) and "color" in _decls(body):
                return _first_color(_decls(body)["color"], palette)
    return None


def _surfaces(rules: list[tuple[str, str]], mode: str, palette: dict[str, str], ground: Color,
              ink: Color) -> list[tuple[str, Color]]:
    """(where, color) for every opaque reading block in one mode, the ground first, deduped."""
    seen: dict[str, tuple[str, Color]] = {hex_of(ground): ("the page ground", ground)}
    for prelude, body in rules:
        sels = [s for s in _split(prelude) if not _SELECTION.search(s) and _mode_of(s) in (None, mode)]
        if not sels:
            continue
        decls = _decls(body)
        raw = decls.get("background-color") or decls.get("background")
        if not raw:
            continue
        c = _first_color(raw, palette)
        if c is None or c[3] == 0:
            continue
        c = over(c, ground)
        if contrast(ink, c) < TEXT_FLOOR:
            continue  # a solid fill with its own light text (a grip, a filled chip), not a reading block
        seen.setdefault(hex_of(c), (sels[0][:60], c))
    return list(seen.values())


def page_selection_readable(html: str, dark_overlay: dict[str, str] | None = None) -> bool:
    return page_report(html, dark_overlay).readable
