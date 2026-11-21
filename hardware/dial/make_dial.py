#!/usr/bin/env python3
"""Generate the printable alethiometer dial-face sticker.

Reads the 36 symbols (wheel order) from ``js/symbols.js`` and writes, next to
this script:

  dial.svg               1:1 vector art (mm units) + <g id="cutlines">
  dial_print_letter.pdf  US Letter, 1:1, crop/registration marks, scale bar,
                         a cut-lined copy plus a spare without cutlines
  dial_1200dpi.png       dial only, transparent outside the annulus
  dial_preview.png       ~1000 px preview on a dark brass background

Glyphs come from Noto Emoji (monochrome, variable, instanced at wght=600)
and Noto Serif Bold for the Alpha & Omega letters; every glyph and every
piece of text is converted to outlined vector paths, so no output depends on
an installed font. Output is deterministic.

Usage:  python hardware/dial/make_dial.py
Requires: fonttools, pymupdf, pillow
"""

from __future__ import annotations

import hashlib
import math
import re
from html import escape
from pathlib import Path

import pymupdf
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SYMBOLS_JS = REPO / "js" / "symbols.js"
FONTS = HERE / "fonts"
EMOJI_FONT = FONTS / "NotoEmoji[wght].ttf"
SERIF_FONT = FONTS / "NotoSerif[wdth,wght].ttf"

# ---------------------------------------------------------------- geometry (mm)
R_CUT_IN, R_CUT_OUT = 29.0, 41.4
BLEED = 0.8
R_ART_IN, R_ART_OUT = R_CUT_IN - BLEED, R_CUT_OUT + BLEED  # 28.2 .. 42.2
R_GILT = (30.0, 40.4)  # 0.25 mm gilt rules
R_HAIR = (30.5, 39.9)  # 0.12 mm gilt hairlines
GILT_W, HAIR_W = 0.25, 0.12
TICK_R0, TICK_R1, TICK_W = 30.5, 39.9, 0.15
R_SYMBOL = 35.2
GLYPH_MAX = 5.0  # larger bbox dimension of each glyph
GLYPH_BOX = 5.6  # hard limit after optical correction
R_PIP, PIP_RADIUS = 29.6, 0.35
CUT_STROKE = 0.1
SIZE = 2 * R_ART_OUT  # 84.4 mm square artboard

# ---------------------------------------------------------------- colours
IVORY = "#EFE4C8"
IVORY_EDGE = "#E2D2AC"
GLYPH = "#2A1D0E"
GILT = "#A8813A"
TICK = "#5A4322"
CUT = "#FF0000"

EMOJI_WGHT = 600
SERIF_LOC = {"wght": 700, "wdth": 100}
CAPTION_LOC = {"wght": 400, "wdth": 100}

# Optical size tweaks (multiplier on GLYPH_MAX): compact, heavy silhouettes
# read larger than spindly ones at the same bbox, so they are trimmed and the
# thin/diagonal ones are nudged up. Kept small and explicit.
OPTICAL = {
    "Apple": 0.86,
    "Bread": 0.86,
    "Madonna": 0.90,
    "Globe": 0.90,
    "Wild Man": 0.94,
    "Angel": 0.96,
    "Sword": 1.06,
    "Thunderbolt": 1.10,
    "Lute": 1.08,
    "Candle": 1.06,
    "Serpent": 1.04,
}

LETTER_W, LETTER_H = 215.9, 279.4


# ================================================================= helpers
def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c) -> str:
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in c)


def polar(r: float, deg: float) -> tuple[float, float]:
    """0 deg = 12 o'clock, clockwise; SVG y axis points down."""
    a = math.radians(deg)
    return r * math.sin(a), -r * math.cos(a)


def circle_d(r: float, cx: float = 0.0, cy: float = 0.0) -> str:
    return (
        f"M{fmt(cx - r)} {fmt(cy)}A{fmt(r)} {fmt(r)} 0 1 0 {fmt(cx + r)} {fmt(cy)}"
        f"A{fmt(r)} {fmt(r)} 0 1 0 {fmt(cx - r)} {fmt(cy)}Z"
    )


def load_symbols() -> list[tuple[str, str]]:
    src = SYMBOLS_JS.read_text(encoding="utf-8")
    syms = re.findall(r"name:\s*'([^']+)'\s*,\s*glyph:\s*'([^']+)'", src)
    if len(syms) != 36:
        raise SystemExit(f"expected 36 symbols in {SYMBOLS_JS}, found {len(syms)}")
    return syms


# ================================================================= fonts
class Outliner:
    """Turns strings into outlined path data via a static font instance."""

    def __init__(self, path: Path, location: dict):
        font = TTFont(path)
        self.font = instancer.instantiateVariableFont(font, location)
        self.cmap = self.font.getBestCmap()
        self.gs = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]

    def has(self, cp: int) -> bool:
        return cp in self.cmap

    def layout(self, text: str, tracking: float = 0.0):
        """Return [(glyphName, x_offset_units)], total advance (units)."""
        out, x = [], 0.0
        for ch in text:
            gname = self.cmap[ord(ch)]
            out.append((gname, x))
            x += self.hmtx[gname][0] + tracking * self.upm
        return out, x - tracking * self.upm

    def bounds(self, run) -> tuple[float, float, float, float]:
        bp = BoundsPen(self.gs)
        for gname, dx in run:
            self.gs[gname].draw(TransformPen(bp, (1, 0, 0, 1, dx, 0)))
        return bp.bounds

    def draw(self, run, pen, matrix):
        """Draw run through `matrix` (font units, y-up) into pen."""
        a, b, c, d, e, f = matrix
        for gname, dx in run:
            # pre-translate by dx in font space
            m = (a, b, c, d, a * dx + e, b * dx + f)
            self.gs[gname].draw(TransformPen(pen, m))


class _FmtSVGPen(SVGPathPen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet, ntos=fmt)


def path_d(outliner: Outliner, run, matrix) -> str:
    pen = _FmtSVGPen(outliner.gs)
    outliner.draw(run, pen, matrix)
    return pen.getCommands()


def text_path(outliner: Outliner, text: str, x: float, y: float, size: float,
              anchor: str = "start", tracking: float = 0.0) -> str:
    """Outlined text; (x, y) is the baseline point in mm, size = em in mm."""
    run, adv = outliner.layout(text, tracking)
    s = size / outliner.upm
    w = adv * s
    x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    return path_d(outliner, run, (s, 0, 0, -s, x0, y))


# ================================================================= the dial
def symbol_paths(symbols, emoji: Outliner, serif: Outliner):
    """Return [(name, d)] with each glyph positioned/rotated in dial mm."""
    out = []
    for i, (name, glyph) in enumerate(symbols):
        text = glyph.replace("\ufe0f", "").replace("\u200d", "")
        if all(emoji.has(ord(ch)) for ch in text):
            ol, run = emoji, emoji.layout(text)[0]
        elif all(serif.has(ord(ch)) for ch in text):
            ol, run = serif, serif.layout(text, tracking=0.02)[0]
        else:
            missing = [f"U+{ord(ch):04X}" for ch in text if not emoji.has(ord(ch))]
            raise SystemExit(f"{name}: no glyph for {missing}; add a substitution")
        xmin, ymin, xmax, ymax = ol.bounds(run)
        gw, gh = xmax - xmin, ymax - ymin
        target = min(GLYPH_MAX * OPTICAL.get(name, 1.0), GLYPH_BOX)
        s = target / max(gw, gh)
        cxu, cyu = (xmin + xmax) / 2, (ymin + ymax) / 2
        ang = i * 360 / len(symbols)
        px, py = polar(R_SYMBOL, ang)
        t = math.radians(ang)
        cos_t, sin_t = math.cos(t), math.sin(t)
        # font (u, v), y-up -> local mm (s*(u-cx), -s*(v-cy)) -> rotate(ang) -> translate
        a, b = s * cos_t, s * sin_t
        c, d = s * sin_t, -s * cos_t
        e = px - a * cxu - c * cyu
        f = py - b * cxu - d * cyu
        out.append((name, path_d(ol, run, (a, b, c, d, e, f))))
    return out


# Vignette: colour as a function of radius (piecewise linear between stops,
# with eased intermediate stops). Shared by the SVG gradient and the stepped
# vector rings used for PDF/PNG (MuPDF does not render SVG gradients).
def _vignette_stops():
    edge, mid = hex_rgb(IVORY_EDGE), hex_rgb(IVORY)
    stops = [(0.0, edge), (R_ART_IN, edge)]
    n = 6
    for k in range(1, n + 1):  # ease-out from inner edge to 31.8
        u = k / n
        r = R_ART_IN + u * 3.6
        w = 1 - (1 - u) ** 2
        stops.append((r, tuple(e + (m - e) * w for e, m in zip(edge, mid))))
    for k in range(0, n + 1):  # ease-in from 38.4 to outer edge
        u = k / n
        r = 38.4 + u * (R_ART_OUT - 38.4)
        w = u * u
        stops.append((r, tuple(m + (e - m) * w for e, m in zip(edge, mid))))
    return stops


VIGNETTE = _vignette_stops()


def vignette_color(r: float):
    for (r0, c0), (r1, c1) in zip(VIGNETTE, VIGNETTE[1:]):
        if r0 <= r <= r1:
            u = 0 if r1 == r0 else (r - r0) / (r1 - r0)
            return tuple(a + (b - a) * u for a, b in zip(c0, c1))
    return VIGNETTE[-1][1]


def background_svg(gradient: bool) -> tuple[str, str]:
    """Return (defs, body) for the ivory annulus."""
    ring = circle_d(R_ART_OUT) + circle_d(R_ART_IN)
    if gradient:
        stops = "".join(
            f'<stop offset="{fmt(r / R_ART_OUT)}" stop-color="{rgb_hex(c)}"/>' for r, c in VIGNETTE
        )
        defs = (
            '<radialGradient id="vignette" gradientUnits="userSpaceOnUse" '
            f'cx="0" cy="0" r="{fmt(R_ART_OUT)}">{stops}</radialGradient>'
        )
        return defs, f'<path id="ground" d="{ring}" fill="url(#vignette)" fill-rule="evenodd"/>'
    # stepped concentric rings, 0.1 mm wide, slightly overlapping
    parts = [f'<path d="{ring}" fill="{IVORY}" fill-rule="evenodd"/>']
    step = 0.1
    n = round((R_ART_OUT - R_ART_IN) / step)
    for k in range(n):
        r0, r1 = R_ART_IN + k * step, R_ART_IN + (k + 1) * step
        col = rgb_hex(vignette_color((r0 + r1) / 2))
        if col == IVORY.upper():
            continue
        lo, hi = max(R_ART_IN, r0 - 0.02), min(R_ART_OUT, r1 + 0.02)
        parts.append(f'<path d="{circle_d(hi)}{circle_d(lo)}" fill="{col}" fill-rule="evenodd"/>')
    return "", '<g id="ground">' + "".join(parts) + "</g>"


def dial_group(glyphs, gradient: bool, cutlines: bool) -> tuple[str, str]:
    """Return (defs, body) of the dial centred on (0,0), in mm."""
    defs, ground = background_svg(gradient)
    body = [ground]
    body.append(f'<g id="gilt" fill="none" stroke="{GILT}">')
    for r in R_GILT:
        body.append(f'<path d="{circle_d(r)}" stroke-width="{fmt(GILT_W)}"/>')
    for r in R_HAIR:
        body.append(f'<path d="{circle_d(r)}" stroke-width="{fmt(HAIR_W)}"/>')
    body.append("</g>")
    ticks = []
    for i in range(36):
        x0, y0 = polar(TICK_R0, (i + 0.5) * 10)
        x1, y1 = polar(TICK_R1, (i + 0.5) * 10)
        ticks.append(f"M{fmt(x0)} {fmt(y0)}L{fmt(x1)} {fmt(y1)}")
    body.append(
        f'<path id="ticks" d="{"".join(ticks)}" fill="none" stroke="{TICK}" '
        f'stroke-width="{fmt(TICK_W)}" stroke-linecap="butt"/>'
    )
    pips = "".join(circle_d(PIP_RADIUS, *polar(R_PIP, i * 10)) for i in range(36))
    body.append(f'<path id="pips" d="{pips}" fill="{GLYPH}"/>')
    body.append(f'<g id="symbols" fill="{GLYPH}">')
    for i, (name, d) in enumerate(glyphs):
        body.append(f'<path id="sym{i:02d}" data-name="{escape(name)}" d="{d}"/>')
    body.append("</g>")
    if cutlines:
        body.append(
            f'<g id="cutlines" fill="none" stroke="{CUT}" stroke-width="{fmt(CUT_STROKE)}">'
            f'<path d="{circle_d(R_CUT_OUT)}"/><path d="{circle_d(R_CUT_IN)}"/></g>'
        )
    return defs, "\n".join(body)


def svg_doc(width: float, height: float, viewbox: str, defs: str, body: str, title: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{fmt(width)}mm" height="{fmt(height)}mm" viewBox="{viewbox}">\n'
        f"<title>{title}</title>\n"
        + (f"<defs>{defs}</defs>\n" if defs else "")
        + body
        + "\n</svg>\n"
    )


def dial_svg(glyphs, gradient=True, cutlines=True) -> str:
    defs, body = dial_group(glyphs, gradient, cutlines)
    r = R_ART_OUT
    return svg_doc(SIZE, SIZE, f"{fmt(-r)} {fmt(-r)} {fmt(SIZE)} {fmt(SIZE)}", defs, body,
                   "Alethiometer dial face, 1:1, mm")


# ================================================================= print page
def crop_marks(cx: float, cy: float) -> str:
    """Corner crop marks on the cut-circle bounding square, outside the bleed."""
    h = R_CUT_OUT
    gap, ln = R_ART_OUT - R_CUT_OUT + 2.0, 5.0
    d = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * h, cy + sy * h
            d.append(f"M{fmt(x)} {fmt(cy + sy * (h + gap))}L{fmt(x)} {fmt(cy + sy * (h + gap + ln))}")
            d.append(f"M{fmt(cx + sx * (h + gap))} {fmt(y)}L{fmt(cx + sx * (h + gap + ln))} {fmt(y)}")
    # centre cross (inside the waste hole) as a compass-cutter pivot point
    c = 1.5
    d.append(f"M{fmt(cx - c)} {fmt(cy)}L{fmt(cx + c)} {fmt(cy)}M{fmt(cx)} {fmt(cy - c)}L{fmt(cx)} {fmt(cy + c)}")
    return f'<path d="{"".join(d)}" fill="none" stroke="#000" stroke-width="0.12"/>'


def reg_mark(x: float, y: float) -> str:
    r, a = 2.2, 3.6
    d = circle_d(r, x, y) + f"M{fmt(x - a)} {fmt(y)}L{fmt(x + a)} {fmt(y)}M{fmt(x)} {fmt(y - a)}L{fmt(x)} {fmt(y + a)}"
    return (f'<path d="{d}" fill="none" stroke="#000" stroke-width="0.15"/>'
            f'<path d="{circle_d(r * 0.45, x, y)}" fill="#000"/>')


def letter_svg(glyphs, caption: Outliner) -> str:
    W, H = LETTER_W, LETTER_H
    cx = W / 2
    y1, y2 = 66.0, 172.0  # dial centres
    parts = []
    for cy, cut in ((y1, True), (y2, False)):
        _, body = dial_group(glyphs, gradient=False, cutlines=cut)
        parts.append(f'<g transform="translate({fmt(cx)} {fmt(cy)})">{body}</g>')
        parts.append(crop_marks(cx, cy))
        for dx in (-1, 1):
            parts.append(reg_mark(cx + dx * (R_ART_OUT + 14), cy))
    # labels
    ink = "#222"
    parts.append(f'<path d="{text_path(caption, "with cut lines (red: cut on the line)", cx, y1 + R_ART_OUT + 9.5, 2.8, "middle")}" fill="{ink}"/>')
    parts.append(f'<path d="{text_path(caption, "spare (no cut lines)", cx, y2 + R_ART_OUT + 9.5, 2.8, "middle")}" fill="{ink}"/>')
    # 50 mm scale-check bar
    by = 236.0
    bx0, bx1 = cx - 25.0, cx + 25.0
    bar = [f'<rect x="{fmt(bx0)}" y="{fmt(by)}" width="50" height="2.0" fill="#000"/>']
    tk = []
    for k in range(0, 51, 5):
        th = 3.2 if k % 10 == 0 else 2.2
        x = bx0 + k
        tk.append(f"M{fmt(x)} {fmt(by - th + 2.0)}L{fmt(x)} {fmt(by + 2.0)}")
    # end ticks extend above for precise measuring
    tk.append(f"M{fmt(bx0)} {fmt(by - 3.0)}L{fmt(bx0)} {fmt(by + 3.5)}M{fmt(bx1)} {fmt(by - 3.0)}L{fmt(bx1)} {fmt(by + 3.5)}")
    bar.append(f'<path d="{"".join(tk)}" fill="none" stroke="#000" stroke-width="0.15"/>')
    bar.append(f'<path id="scalebar-label" d="{text_path(caption, "50 mm \u2014 verify before cutting", cx, by + 8.5, 3.4, "middle")}" fill="#000"/>')
    parts.append(f'<g id="scalebar">{"".join(bar)}</g>')
    parts.append(f'<path id="caption" d="{text_path(caption, "Alethiometer dial \u2014 print at 100% / actual size", cx, 258.0, 4.2, "middle")}" fill="#000"/>')
    parts.append(f'<path d="{text_path(caption, "Disable \u201cfit to page\u201d. Cut circles: \u00d8 82.8 mm outer, \u00d8 58.0 mm inner. Centre cross marks the compass-cutter pivot.", cx, 265.0, 2.6, "middle")}" fill="#333"/>')
    return svg_doc(W, H, f"0 0 {fmt(W)} {fmt(H)}", "", "\n".join(parts),
                   "Alethiometer dial print sheet, US Letter, 1:1")


# ================================================================= outputs
FIXED_DATE = "D:20260101000000Z"


def write_pdf(svg_text: str, out: Path):
    src = pymupdf.open("svg", svg_text.encode("utf-8"))
    pdf = pymupdf.open("pdf", src.convert_to_pdf())
    pdf.set_metadata({
        "title": "Alethiometer dial \u2014 print at 100% / actual size",
        "author": "alethiometer",
        "subject": "Dial-face sticker, 1:1, US Letter",
        "creator": "hardware/dial/make_dial.py",
        "producer": "PyMuPDF",
        "creationDate": FIXED_DATE,
        "modDate": FIXED_DATE,
    })
    pdf.save(out, garbage=4, deflate=True, no_new_id=True)


def render_svg(svg_text: str, dpi: int, alpha: bool) -> pymupdf.Pixmap:
    doc = pymupdf.open("svg", svg_text.encode("utf-8"))
    return doc[0].get_pixmap(dpi=dpi, alpha=alpha)


def write_preview(svg_text: str, out: Path, width: int = 1000):
    margin = 60
    dial_px = width - 2 * margin
    dpi = dial_px / (SIZE / 25.4)
    pix = render_svg(svg_text, round(dpi), alpha=True)
    dial = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    bg = Image.new("RGB", (width, width))
    # dark brass radial background
    c0, c1 = hex_rgb("#6B5228"), hex_rgb("#22180A")
    px = bg.load()
    m = width / 2
    for y in range(width):
        for x in range(width):
            t = min(1.0, math.hypot(x - m, y - m) / (m * 1.35))
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    # brass bezel ring behind the dial, and a dark centre (the movement)
    d = ImageDraw.Draw(bg)
    rr = dial.width / 2 + 10
    d.ellipse([m - rr, m - rr, m + rr, m + rr], fill=hex_rgb("#8C6A30"))
    rr -= 4
    d.ellipse([m - rr, m - rr, m + rr, m + rr], fill=hex_rgb("#5E4520"))
    bg = bg.convert("RGBA")
    bg.alpha_composite(dial, (round(m - dial.width / 2), round(m - dial.height / 2)))
    bg.convert("RGB").save(out, optimize=True)


def verify_pdf(out: Path):
    doc = pymupdf.open(out)
    page = doc[0]
    assert abs(page.rect.width - 612) < 0.01 and abs(page.rect.height - 792) < 0.01, page.rect
    pt2mm = 25.4 / 72
    diams = sorted({round(dr["rect"].width * pt2mm, 3) for dr in page.get_drawings()
                    if dr.get("color") and tuple(round(c, 3) for c in dr["color"]) == (1.0, 0.0, 0.0)})
    # stroke bbox may include half the stroke width depending on MuPDF version
    ok_out = any(abs(d - 2 * R_CUT_OUT) < 0.15 for d in diams)
    ok_in = any(abs(d - 2 * R_CUT_IN) < 0.15 for d in diams)
    print(f"  PDF red cut circles (mm): {diams}")
    if not (ok_out and ok_in):
        raise SystemExit("PDF cut-circle size check FAILED")
    print(f"  PDF scale check OK: outer {2 * R_CUT_OUT} mm, inner {2 * R_CUT_IN} mm")


def main():
    symbols = load_symbols()
    emoji = Outliner(EMOJI_FONT, {"wght": EMOJI_WGHT})
    serif = Outliner(SERIF_FONT, SERIF_LOC)
    caption = Outliner(SERIF_FONT, CAPTION_LOC)
    glyphs = symbol_paths(symbols, emoji, serif)

    outputs = {}
    p = HERE / "dial.svg"
    p.write_text(dial_svg(glyphs, gradient=True, cutlines=True), encoding="utf-8", newline="\n")
    outputs["dial.svg"] = p

    p = HERE / "dial_print_letter.pdf"
    write_pdf(letter_svg(glyphs, caption), p)
    outputs["dial_print_letter.pdf"] = p
    verify_pdf(p)

    art = dial_svg(glyphs, gradient=False, cutlines=False)
    p = HERE / "dial_1200dpi.png"
    pix = render_svg(art, 1200, alpha=True)
    pix.set_dpi(1200, 1200)
    pix.save(p)
    outputs["dial_1200dpi.png"] = p
    print(f"  dial_1200dpi.png: {pix.width}x{pix.height} px "
          f"= {pix.width / 1200 * 25.4:.2f} mm @1200dpi")

    p = HERE / "dial_preview.png"
    write_preview(art, p)
    outputs["dial_preview.png"] = p

    for name, path in outputs.items():
        h = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        print(f"  wrote {name:24s} {path.stat().st_size:>9,d} B  sha256:{h}")


if __name__ == "__main__":
    main()
