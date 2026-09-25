"""Spectral motifs: face-mesh constellation, detection brackets, frequency spectrum."""

from __future__ import annotations

from svgkit import geometry
from svgkit.svg import el, fmt

from .theme import Theme


def accent_gradient(gid: str, theme: Theme, x1: float, x2: float) -> str:
    """Horizontal accent ramp in user space, so a whole chart shifts hue across its width."""
    stops = el("stop", {"offset": "0", "stop-color": theme.accent_from}) + el(
        "stop", {"offset": "1", "stop-color": theme.accent_to}
    )
    return el(
        "linearGradient",
        {"id": gid, "gradientUnits": "userSpaceOnUse", "x1": x1, "y1": 0, "x2": x2, "y2": 0},
        stops,
    )


def mesh(x: float, y: float, w: float, h: float, *, dot: float = 1.3, mark: float = 2.2) -> str:
    """Abstract face-mesh constellation scaled into the box (x, y, w, h)."""
    m = geometry.face_mesh()
    pts = [(x + px * w, y + py * h) for px, py in m.points]
    marks = set(m.landmarks)
    lines = "".join(
        f'<path d="M{fmt(pts[a][0])} {fmt(pts[a][1])}L{fmt(pts[b][0])} {fmt(pts[b][1])}"/>'
        for a, b in m.edges
    )
    dots = "".join(
        f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(dot)}"/>'
        for i, (px, py) in enumerate(pts)
        if i not in marks
    )
    lands = "".join(
        f'<circle cx="{fmt(pts[i][0])}" cy="{fmt(pts[i][1])}" r="{fmt(mark)}"/>'
        for i in sorted(marks)
    )
    return f'<g class="me">{lines}</g><g class="mp">{dots}</g><g class="mm">{lands}</g>'


def brackets(x: float, y: float, w: float, h: float, k: float, cls: str) -> str:
    """Four corner brackets: the detection-box motif."""
    d = (
        f"M{fmt(x)} {fmt(y + k)}V{fmt(y)}H{fmt(x + k)}"
        f"M{fmt(x + w - k)} {fmt(y)}H{fmt(x + w)}V{fmt(y + k)}"
        f"M{fmt(x + w)} {fmt(y + h - k)}V{fmt(y + h)}H{fmt(x + w - k)}"
        f"M{fmt(x + k)} {fmt(y + h)}H{fmt(x)}V{fmt(y + h - k)}"
    )
    return el("path", {"class": cls, "d": d})


def spectrum(x: float, y: float, w: float, h: float, n: int, gradient: str) -> str:
    """Log power spectrum drawn as a line over a faint area, coloured across frequency."""
    values = geometry.spectrum(n)
    step = w / (n - 1)
    pts = [(x + i * step, y + h - v * h) for i, v in enumerate(values)]
    line = "M" + "L".join(f"{fmt(px)} {fmt(py)}" for px, py in pts)
    area = f"{line}L{fmt(x + w)} {fmt(y + h)}L{fmt(x)} {fmt(y + h)}Z"
    return el("path", {"d": area, "fill": f"url(#{gradient})", "fill-opacity": "0.14"}) + el(
        "path",
        {
            "d": line,
            "fill": "none",
            "stroke": f"url(#{gradient})",
            "stroke-width": "1.5",
            "stroke-linejoin": "round",
        },
    )
