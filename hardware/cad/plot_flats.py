"""Plot every laser-cut flat pattern to out/flats/*.png for visual review."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

import design as D  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out" / "flats"


def poly_path(poly) -> MPath:
    verts, codes = [], []
    for ring in [poly.exterior, *poly.interiors]:
        pts = list(ring.coords)
        verts += pts
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
    return MPath(verts, codes)


def plot(part, path: Path) -> None:
    prof = part.profile
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(PathPatch(poly_path(prof.poly), facecolor="#d4a64f", edgecolor="#5a4322", lw=0.4))
    for x, y, r in prof.holes:
        ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor="#5a4322", lw=0.3))
    for (x0, y0), (x1, y1) in part.bends:
        ax.plot([x0, x1], [y0, y1], "r--", lw=0.6)
    x0, y0, x1, y1 = prof.poly.bounds
    ax.set_xlim(x0 - 3, x1 + 3)
    ax.set_ylim(y0 - 3, y1 + 3)
    ax.set_aspect("equal")
    ax.set_title(f"{part.name} — {part.material} — {x1 - x0:.1f}×{y1 - y0:.1f} mm", fontsize=9)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    flats = [p for p in D.all_parts() + D.tooling() if p.kind in ("scs", "scs-bent") and p.profile is not None]
    keep = {f"{p.name}.png" for p in flats}
    for old in OUT.glob("*.png"):          # parts that no longer exist
        if old.name not in keep:
            old.unlink()
    for p in flats:
        plot(p, OUT / f"{p.name}.png")
        print("plotted", p.name)


if __name__ == "__main__":
    main()
