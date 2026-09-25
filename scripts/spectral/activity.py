"""Private-aware activity images: an isometric contribution skyline and two glance cards.

Inputs are aggregates only (see data.py), so nothing drawn here can name a private repository.
"""

from __future__ import annotations

import math

from svgkit.canvas import Canvas
from svgkit.color import Ledger, parse
from svgkit.svg import el, fmt

from .cards import CARD_H, CARD_W, frame
from .data import Stats
from .theme import Theme, Tokens

SKY_W, SKY_H = 880, 264


RGB = tuple[float, float, float]


def _lerp(a: RGB, b: RGB, t: float) -> RGB:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _mix(a: str, b: str, t: float) -> RGB:
    return _lerp(parse(a)[0], parse(b)[0], t)


def _hex(rgb: RGB, shade: float = 1.0) -> str:
    r, g, b = (max(0, min(255, round(c * 255 * shade))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _grid(stats: Stats) -> list[list[tuple[int, int]]]:
    weeks = stats.weeks()
    if weeks:
        return weeks
    return [[(d, 0) for d in range(7)] for _ in range(53)]


def skyline(tokens: Tokens, theme: Theme, stats: Stats, ledger: Ledger, asset: str) -> str:
    """One column per day, 53 weeks deep, in a shallow dimetric projection."""
    weeks = _grid(stats)
    peak = max((count for week in weeks for _, count in week), default=0)
    step_w, step_d = 13.6, 13.0
    a, b = math.radians(8), math.radians(38)
    ux, uy = step_w * math.cos(a), step_w * math.sin(a)
    vx, vy = -step_d * math.cos(b), step_d * math.sin(b)
    tallest = 60.0
    span_x = len(weeks) * ux - 7 * vx
    span_y = len(weeks) * uy + 7 * vy + tallest
    x0 = (SKY_W - span_x) / 2 - 7 * vx
    y0 = (SKY_H - span_y) / 2 + tallest
    # Side faces are darker than the top; gentler on the light panel so columns stay clean.
    front_k, side_k = (0.72, 0.52) if theme.name == "dark" else (0.86, 0.74)

    def point(w: float, d: float, lift: float = 0.0) -> tuple[float, float]:
        return (x0 + w * ux + d * vx, y0 + w * uy + d * vy - lift)

    def poly(points: list[tuple[float, float]], fill: str) -> str:
        coords = "L".join(f"{fmt(x)} {fmt(y)}" for x, y in points)
        return f'<path d="M{coords}Z" fill="{fill}"/>'

    gap = 0.14
    cells: list[tuple[float, float, str]] = []
    for w, week in enumerate(weeks):
        hue = _mix(theme.accent_from, theme.accent_to, w / max(1, len(weeks) - 1))
        for d, count in week:
            w0, w1, d0, d1 = w + gap, w + 1 - gap, d + gap, d + 1 - gap
            order = point(w1, d1)
            if count <= 0 or peak <= 0:
                quad = [point(w0, d0), point(w1, d0), point(w1, d1), point(w0, d1)]
                cells.append((order[1], order[0], poly(quad, theme.hairline_strong)))
                continue
            level = math.sqrt(count / peak)
            h = max(2.5, tallest * level)
            # Quiet days sit closer to the panel colour, busy days carry the full hue.
            top_rgb = _lerp(parse(theme.bg)[0], hue, 0.4 + 0.6 * level)
            top, front, side = _hex(top_rgb), _hex(top_rgb, front_k), _hex(top_rgb, side_k)
            faces = (
                poly([point(w0, d1), point(w1, d1), point(w1, d1, h), point(w0, d1, h)], front)
                + poly([point(w1, d0), point(w1, d1), point(w1, d1, h), point(w1, d0, h)], side)
                + poly(
                    [point(w0, d0, h), point(w1, d0, h), point(w1, d1, h), point(w0, d1, h)], top
                )
            )
            cells.append((order[1], order[0], faces))
    cells.sort(key=lambda item: (item[0], item[1]))
    c = Canvas(asset, SKY_W, SKY_H, ledger=ledger, bg=theme.bg, min_scale=1)
    body = (
        el("rect", {"width": SKY_W, "height": SKY_H, "rx": 12, "fill": theme.bg})
        + el(
            "rect",
            {
                "x": 0.5,
                "y": 0.5,
                "width": SKY_W - 1,
                "height": SKY_H - 1,
                "rx": 11.5,
                "fill": "none",
                "stroke": theme.hairline,
            },
        )
        + "".join(face for _, _, face in cells)
    )
    if stats.ready and stats.total is not None:
        desc = (
            f"Isometric skyline of {stats.total:,} contributions over the last 12 months, "
            "one column per day, taller for busier days. Private work is included as counts."
        )
    else:
        desc = "Contribution skyline, waiting for the first data refresh."
    return c.render(title="Contribution skyline, last 12 months", desc=desc, body=body)


def contributions_card(
    tokens: Tokens, theme: Theme, stats: Stats, ledger: Ledger, asset: str
) -> str:
    f = tokens.fonts
    c = Canvas(
        asset, CARD_W, CARD_H, ledger=ledger, bg=theme.bg, min_scale=tokens.min_scale(CARD_W)
    )
    c.style("e", f.mono, 15, theme.muted)
    c.style("n", f.display, 40, theme.text)
    c.style("d", f.text_regular, 17, theme.text)
    number = f"{stats.total:,}" if stats.ready and stats.total is not None else "—"
    parts = [
        frame(theme, CARD_W, CARD_H),
        c.text(f"12 months to {stats.as_of}" if stats.as_of else "last 12 months", 24, 56, "e"),
        c.text(number, 24, 106, "n"),
        c.text("contributions, private work included", 24, 138, "d"),
    ]
    weekly = [sum(count for _, count in week) for week in stats.weeks()] or [0] * 53
    top = max(weekly) or 1
    x, width, base, height = 24.0, CARD_W - 48.0, 192.0, 28.0
    step = width / len(weekly)
    bars = "".join(
        el(
            "rect",
            {
                "x": x + i * step,
                "y": base - max(1.5, height * v / top),
                "width": step * 0.6,
                "height": max(1.5, height * v / top),
            },
        )
        for i, v in enumerate(weekly)
    )
    parts.append(
        el(
            "defs",
            None,
            el(
                "linearGradient",
                {
                    "id": "w",
                    "gradientUnits": "userSpaceOnUse",
                    "x1": x,
                    "y1": 0,
                    "x2": x + width,
                    "y2": 0,
                },
                el("stop", {"offset": "0", "stop-color": theme.accent_from})
                + el("stop", {"offset": "1", "stop-color": theme.accent_to}),
            ),
        )
        + el("g", {"fill": "url(#w)", "opacity": "0.9"}, bars)
    )
    desc = (
        f"{number} contributions in the last 12 months, including private work, with a "
        "bar per week."
        if stats.ready
        else "Contribution count, waiting for the first data refresh."
    )
    return c.render(title="Contributions, last 12 months", desc=desc, body="".join(parts))


def languages_card(tokens: Tokens, theme: Theme, stats: Stats, ledger: Ledger, asset: str) -> str:
    f = tokens.fonts
    c = Canvas(
        asset, CARD_W, CARD_H, ledger=ledger, bg=theme.bg, min_scale=tokens.min_scale(CARD_W)
    )
    c.style("e", f.mono, 15, theme.muted)
    c.style("l", f.text_regular, 16, theme.text)
    c.style("p", f.mono, 15, theme.muted)
    shares, other = stats.language_shares(4)
    parts = [frame(theme, CARD_W, CARD_H), c.text("top languages by bytes", 24, 56, "e")]
    x, width, y = 24.0, CARD_W - 48.0, 76.0
    n = len(shares)
    colours = [_hex(_mix(theme.accent_from, theme.accent_to, i / max(1, n - 1))) for i in range(n)]
    if not shares:
        parts.append(
            el(
                "rect",
                {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": 8,
                    "rx": 4,
                    "fill": theme.hairline_strong,
                },
            )
        )
        parts.append(c.text("waiting for the first refresh", 24, 124, "l"))
    else:
        cursor = x
        for colour, (_, share) in zip(colours, shares, strict=True):
            seg = width * share
            parts.append(
                el(
                    "rect",
                    {"x": cursor, "y": y, "width": max(0.0, seg - 2), "height": 8, "fill": colour},
                )
            )
            cursor += seg
        if other > 0:
            parts.append(
                el(
                    "rect",
                    {
                        "x": cursor,
                        "y": y,
                        "width": max(0.0, x + width - cursor),
                        "height": 8,
                        "fill": theme.hairline_strong,
                    },
                )
            )
        rows = [*shares, ("Other", other)] if other >= 0.005 else list(shares)
        for i, (name, share) in enumerate(rows[:6]):
            col, row = i % 2, i // 2
            cx, cy = 24 + col * 184, 116 + row * 28
            swatch = colours[i] if i < n else theme.hairline_strong
            parts.append(
                el(
                    "rect",
                    {"x": cx, "y": cy - 10, "width": 10, "height": 10, "rx": 2, "fill": swatch},
                )
            )
            parts.append(c.text(name, cx + 18, cy, "l"))
            parts.append(c.text(f"{share * 100:.1f}%", cx + 172, cy, "p", anchor="end"))
    parts.append(c.text(stats.language_scope or "owned repos · private included", 24, 200, "e"))
    listing = ", ".join(f"{name} {share * 100:.1f}%" for name, share in shares)
    desc = (
        f"Top languages by bytes: {listing}."
        if shares
        else "Languages, waiting for the first refresh."
    )
    return c.render(title="Top languages by bytes", desc=desc, body="".join(parts))
