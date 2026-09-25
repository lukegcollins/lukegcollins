"""Procedural forensic motifs: an abstract face-mesh constellation and a synthetic spectrum.

Nothing here is derived from a real face or a real image. Points come from closed-form
curves, triangulated with Bowyer-Watson, so the output is fully deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True)
class Mesh:
    points: list[Point]
    edges: list[tuple[int, int]]
    landmarks: list[int]  # indices drawn as emphasised landmarks


def _ring(cx: float, cy: float, rx: float, ry: float, n: int, start: float = 0.0) -> list[Point]:
    return [
        (
            cx + rx * math.cos(start + 2 * math.pi * i / n),
            cy + ry * math.sin(start + 2 * math.pi * i / n),
        )
        for i in range(n)
    ]


def _arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, n: int) -> list[Point]:
    return [
        (
            cx + rx * math.cos(a0 + (a1 - a0) * i / (n - 1)),
            cy + ry * math.sin(a0 + (a1 - a0) * i / (n - 1)),
        )
        for i in range(n)
    ]


def face_points() -> tuple[list[Point], list[int]]:
    """Landmarks in a unit box (x, y in 0..1), roughly 90 points, plus emphasised indices."""
    pts: list[Point] = []
    marks: list[int] = []
    # Face contour (an egg curve, wider at the temples than the chin) and an inner ring that
    # keeps the tessellation between the contour and the features even.
    for scale, count, phase in ((1.0, 30, 0.0), (0.8, 22, math.pi / 22)):
        for i in range(count):
            t = phase + 2 * math.pi * i / count
            x = 0.5 + scale * 0.40 * math.cos(t) * (1 - 0.10 * math.sin(t))
            y = 0.52 + scale * 0.46 * math.sin(t) * (1 + 0.06 * math.sin(t))
            pts.append((x, y))
    # Brows.
    for side in (-1, 1):
        pts.extend(_arc(0.5 + side * 0.17, 0.36, 0.10, 0.035, math.pi * 1.1, math.pi * 1.9, 5))
    # Eyes: ring plus pupil.
    for side in (-1, 1):
        start = len(pts)
        pts.extend(_ring(0.5 + side * 0.165, 0.44, 0.07, 0.028, 8))
        marks.extend([start, start + 4])
        pts.append((0.5 + side * 0.165, 0.44))
    # Nose bridge and base.
    bridge = [(0.5, 0.44 + 0.045 * i) for i in range(4)]
    pts.extend(bridge)
    tip = len(pts)
    pts.extend(_arc(0.5, 0.60, 0.075, 0.03, math.pi * 0.05, math.pi * 0.95, 5))
    marks.append(tip + 2)
    # Mouth: outer and inner lips.
    mouth = len(pts)
    pts.extend(_ring(0.5, 0.735, 0.12, 0.04, 10))
    pts.extend(_ring(0.5, 0.735, 0.07, 0.012, 6, start=math.pi / 6))
    marks.extend([mouth, mouth + 5])
    # Cheeks and forehead fill so the tessellation stays even.
    fill = [(0.31, 0.57), (0.69, 0.57), (0.40, 0.66), (0.60, 0.66), (0.5, 0.27), (0.5, 0.33)]
    pts.extend(fill)
    return pts, marks


def _circumcircle(a: Point, b: Point, c: Point) -> tuple[float, float, float]:
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return 0.0, 0.0, math.inf
    ux = (
        (ax * ax + ay * ay) * (by - cy)
        + (bx * bx + by * by) * (cy - ay)
        + (cx * cx + cy * cy) * (ay - by)
    ) / d
    uy = (
        (ax * ax + ay * ay) * (cx - bx)
        + (bx * bx + by * by) * (ax - cx)
        + (cx * cx + cy * cy) * (bx - ax)
    ) / d
    return ux, uy, (ax - ux) ** 2 + (ay - uy) ** 2


def delaunay(points: list[Point]) -> list[tuple[int, int, int]]:
    """Bowyer-Watson triangulation (fine for a few hundred points)."""
    n = len(points)
    big = 1e3
    work = [*points, (-big, -big), (big * 2, -big), (-big, big * 2)]
    triangles: list[tuple[int, int, int]] = [(n, n + 1, n + 2)]
    for index in range(n):
        p = work[index]
        bad = []
        for tri in triangles:
            ux, uy, r2 = _circumcircle(work[tri[0]], work[tri[1]], work[tri[2]])
            if (p[0] - ux) ** 2 + (p[1] - uy) ** 2 < r2:
                bad.append(tri)
        boundary: dict[tuple[int, int], int] = {}
        for tri in bad:
            for edge in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                key = (min(edge), max(edge))
                boundary[key] = boundary.get(key, 0) + 1
        triangles = [t for t in triangles if t not in bad]
        for (a, b), count in sorted(boundary.items()):
            if count == 1:
                triangles.append((a, b, index))
    return sorted(tuple(sorted(t)) for t in triangles if max(t) < n)  # type: ignore[misc]


def face_mesh() -> Mesh:
    pts, marks = face_points()
    edges: set[tuple[int, int]] = set()
    for a, b, c in delaunay(pts):
        for u, v in ((a, b), (b, c), (a, c)):
            # Skip very long chords: they cut across the face and read as noise.
            if math.dist(pts[u], pts[v]) < 0.2:
                edges.add((min(u, v), max(u, v)))
    return Mesh(points=pts, edges=sorted(edges), landmarks=sorted(set(marks)))


def spectrum(n: int) -> list[float]:
    """A synthetic azimuthally averaged log power spectrum in 0..1.

    A 1/f fall-off with gentle texture, plus the regularly spaced high-frequency peaks that
    upsampling layers in image generators tend to leave behind.
    """
    values: list[float] = []
    for i in range(n):
        f = (i + 1) / n
        base = 0.92 - 0.62 * math.log1p(9 * f) / math.log(10)
        texture = 0.035 * math.sin(i * 1.7) + 0.02 * math.sin(i * 0.53 + 1.0)
        peaks = 0.0
        for centre in (0.5, 0.75, 1.0):
            peaks += 0.24 * math.exp(-(((f - centre) * n / 1.3) ** 2))
        values.append(max(0.04, min(1.0, base + texture + peaks)))
    return values
