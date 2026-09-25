"""Small linked images: the intro link badges and the featured-work cards."""

from __future__ import annotations

from dataclasses import dataclass

from svgkit.canvas import Canvas
from svgkit.color import Ledger
from svgkit.svg import el, fmt

from .theme import Theme, Tokens


@dataclass(frozen=True)
class Link:
    slug: str
    label: str
    href: str


@dataclass(frozen=True)
class Feature:
    slug: str
    eyebrow: str
    title: str
    lines: tuple[str, str]
    footer: str
    href: str


def arrow(x: float, y: float, size: float, colour: str, width: float = 1.5) -> str:
    """A north-east arrow drawn as strokes, so it never depends on a glyph."""
    return el(
        "path",
        {
            "d": f"M{fmt(x)} {fmt(y + size)}L{fmt(x + size)} {fmt(y)}"
            f"M{fmt(x + size * 0.3)} {fmt(y)}H{fmt(x + size)}V{fmt(y + size * 0.7)}",
            "fill": "none",
            "stroke": colour,
            "stroke-width": fmt(width),
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )


def badge(tokens: Tokens, theme: Theme, link: Link, ledger: Ledger, asset: str) -> str:
    height = 32
    probe = Canvas(asset, 0, height, ledger=Ledger(), bg=theme.surface, min_scale=1)
    probe.style("t", tokens.fonts.mono, 13, theme.text)
    width = round(12 + probe.measure(link.label, "t") + 10 + 9 + 12)
    c = Canvas(
        asset, width, height, ledger=ledger, bg=theme.surface, min_scale=tokens.min_scale(width)
    )
    c.style("t", tokens.fonts.mono, 13, theme.text)
    body = (
        el(
            "rect",
            {
                "x": 0.5,
                "y": 0.5,
                "width": width - 1,
                "height": height - 1,
                "rx": 7.5,
                "fill": theme.surface,
                "stroke": theme.hairline_strong,
            },
        )
        + c.text(link.label, 12, 20.5, "t")
        + arrow(width - 12 - 9, 11.5, 9, theme.accent_text)
    )
    return c.render(title=link.label, desc=f"Link to {link.label}.", body=body)


CARD_W, CARD_H = 400, 216


def frame(theme: Theme, width: float, height: float) -> str:
    """Card background: near-black panel, hairline edge, a short accent rule top-left."""
    return (
        el(
            "defs",
            None,
            el(
                "linearGradient",
                {"id": "a", "x1": "0", "x2": "1"},
                el("stop", {"offset": "0", "stop-color": theme.accent_from})
                + el("stop", {"offset": "1", "stop-color": theme.accent_to}),
            ),
        )
        + el("rect", {"width": width, "height": height, "rx": 12, "fill": theme.bg})
        + el(
            "rect",
            {
                "x": 0.5,
                "y": 0.5,
                "width": width - 1,
                "height": height - 1,
                "rx": 11.5,
                "fill": "none",
                "stroke": theme.hairline_strong,
            },
        )
        + el("rect", {"x": 24, "y": 24, "width": 32, "height": 2, "rx": 1, "fill": "url(#a)"})
    )


def feature(tokens: Tokens, theme: Theme, card: Feature, ledger: Ledger, asset: str) -> str:
    f = tokens.fonts
    c = Canvas(
        asset, CARD_W, CARD_H, ledger=ledger, bg=theme.bg, min_scale=tokens.min_scale(CARD_W)
    )
    c.style("e", f.mono, 15, theme.muted)
    c.style("t", f.display, 28, theme.text)
    c.style("d", f.text_regular, 17, theme.text)
    c.style("u", f.mono, 15, theme.accent_text)
    footer_w = c.measure(card.footer, "u")
    body = (
        frame(theme, CARD_W, CARD_H)
        + c.text(card.eyebrow, 24, 56, "e")
        + c.text(card.title, 24, 98, "t")
        + c.text(card.lines[0], 24, 134, "d")
        + c.text(card.lines[1], 24, 158, "d")
        + c.text(card.footer, 24, 192, "u")
        + arrow(24 + footer_w + 10, 181, 9, theme.accent_text)
    )
    desc = f"{card.eyebrow}. {card.title}: {card.lines[0]} {card.lines[1]} {card.footer}"
    return c.render(title=card.title, desc=desc, body=body)
