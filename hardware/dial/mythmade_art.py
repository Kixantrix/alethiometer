"""Use Myth Made's hand-drawn symbol art (the BBC prop's set) on the dial.

Myth Made's free "Alethiometer Symbols.svg" (https://mythmade.gumroad.com/l/trhgos)
is an xTool laser layout: 36 tile outlines, each holding a small embedded
raster symbol (~60-90 px, ~0.074 mm/px, i.e. ~340 dpi at their native size).
This module turns each symbol upright relative to its tile (so "up" points
away from the dial centre) and converts it into a sepia ink layer with
transparency, upsampled smoothly for printing. Rasters keep the hatching of
the original drawings far better than vector tracing does at this size.

The art isn't ours to redistribute, so nothing from that file is committed:
pass its path to make_dial.py (``--art``) and the outputs go to the
git-ignored ``hardware/dial/local/`` folder.
"""
from __future__ import annotations

import base64
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

# Their tile index -> website symbol name (js/symbols.js), identified by eye.
# The BBC set has a salamander where the books have a garland; the website
# uses "Salamander" to match.
MYTHMADE_NAMES = {
    0: "Helmet", 1: "Apple", 2: "Bird", 3: "Beehive", 4: "Moon", 5: "Madonna",
    6: "Hourglass", 7: "Owl", 8: "Sun", 9: "Alpha & Omega", 10: "Serpent",
    11: "Marionette", 12: "Cauldron", 13: "Anchor", 14: "Angel", 15: "Griffin",
    16: "Horse", 17: "Sword", 18: "Elephant", 19: "Salamander", 20: "Camel",
    21: "Compasses", 22: "Baby", 23: "Lute", 24: "Tree", 25: "Wild Man",
    26: "Globe", 27: "Walled Garden", 28: "Dolphin", 29: "Thunderbolt",
    30: "Chameleon", 31: "Cornucopia", 32: "Candle", 33: "Bread", 34: "Bull",
    35: "Ant",
}

UPSAMPLE = 6                  # smooth (Lanczos) upsampling of the source rasters
PAPER, INK = 0.90, 0.22       # luminance mapped to fully transparent / fully opaque


@dataclass
class ArtSymbol:
    index: int                # tile index in their file
    name: str
    png: bytes                # RGBA, sepia ink, transparent ground, upright
    size_px: tuple            # (w, h) of the PNG
    mm_per_px: float          # native scale of the PNG
    ink_box: tuple            # (x0, y0, x1, y1) px of visible ink within the PNG


def _matrix(s: str) -> np.ndarray:
    a, b, c, d, e, f = (float(v) for v in re.findall(r"-?[\d.]+(?:e-?\d+)?", s))
    return np.array([[a, c, e], [b, d, f], [0.0, 0.0, 1.0]])


def _apply(m: np.ndarray, x: float, y: float) -> tuple[float, float]:
    v = m @ np.array([x, y, 1.0])
    return float(v[0]), float(v[1])


def _parse(svg_text: str):
    tiles = []
    for tag in re.findall(r"<path[^>]*>", svg_text):
        m = _matrix(re.search(r'transform="matrix\(([^)]+)\)"', tag).group(1))
        nums = [float(v) for v in re.findall(r"-?[\d.]+", re.search(r' d="([^"]+)"', tag).group(1))]
        pts = list(zip(nums[0::2], nums[1::2]))
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        tiles.append((m, _apply(m, cx, cy)))
    images = []
    for tag in re.findall(r"<image[^>]*>", svg_text):
        m = _matrix(re.search(r'transform="matrix\(([^)]+)\)"', tag).group(1))
        w = float(re.search(r' width="([^"]+)"', tag).group(1))
        h = float(re.search(r' height="([^"]+)"', tag).group(1))
        data = base64.b64decode(re.search(r'href="data:image/\w+;base64,([^"]+)"', tag).group(1))
        images.append((m, w, h, Image.open(io.BytesIO(data))))
    if len(images) != 36 or len(tiles) != 36:
        raise ValueError(f"expected 36 tiles and 36 images, found {len(tiles)} and {len(images)}")
    return tiles, images


def _upright(m_img, w, h, img, tiles) -> tuple[Image.Image, float]:
    """Greyscale symbol rotated so tile-up (away from dial centre) is image-up."""
    centre = _apply(m_img, w / 2, h / 2)
    m_tile = min(tiles, key=lambda t: math.dist(t[1], centre))[0]
    rel = np.linalg.inv(m_tile) @ m_img          # image px -> tile-local mm (outward = -y)
    lin = rel[:2, :2]
    if np.linalg.det(lin) < 0:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        lin = lin @ np.array([[-1.0, 0.0], [0.0, 1.0]])
    scale = math.sqrt(abs(np.linalg.det(lin)))  # mm per source px
    alpha = math.degrees(math.atan2(lin[1, 0], lin[0, 0]))
    rgba = img.convert("RGBA")
    ground = Image.new("RGBA", rgba.size, "white")
    ground.alpha_composite(rgba)
    grey = ground.convert("L")
    # SVG y points down, so a positive angle is clockwise on screen; PIL rotates CCW.
    return grey.rotate(-alpha, resample=Image.BICUBIC, expand=True, fillcolor=255), scale


def _ink_layer(grey: Image.Image, ink_rgb: tuple) -> tuple[Image.Image, tuple]:
    big = grey.resize((grey.width * UPSAMPLE, grey.height * UPSAMPLE), Image.LANCZOS)
    lum = np.asarray(big, dtype=np.float32) / 255.0
    a = np.clip((PAPER - lum) / (PAPER - INK), 0.0, 1.0)
    rgba = np.zeros((*a.shape, 4), dtype=np.uint8)
    rgba[..., :3] = ink_rgb
    rgba[..., 3] = (a * 255).round().astype(np.uint8)
    ys, xs = np.nonzero(a > 0.25)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    return Image.fromarray(rgba, "RGBA"), box


def load(path: Path, ink_hex: str = "#2A1D0E") -> dict[str, ArtSymbol]:
    """Return {website symbol name: ArtSymbol} from Myth Made's symbols SVG."""
    ink = tuple(int(ink_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    tiles, images = _parse(Path(path).read_text(encoding="utf-8"))
    out = {}
    for i, (m, w, h, img) in enumerate(images):
        grey, mm_px = _upright(m, w, h, img, tiles)
        layer, box = _ink_layer(grey, ink)
        buf = io.BytesIO()
        layer.save(buf, "PNG", optimize=True)
        name = MYTHMADE_NAMES[i]
        out[name] = ArtSymbol(i, name, buf.getvalue(), layer.size, mm_px / UPSAMPLE, box)
    return out
