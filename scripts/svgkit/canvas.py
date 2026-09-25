"""A drawing surface for one SVG asset.

It remembers which characters each face draws (so the embedded subsets stay small), turns
named text styles into CSS classes, and records every visible string in a contrast ledger so
the build can refuse text that fails WCAG AA or renders below the minimum size.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from . import fonts
from .color import Ledger, TextEntry
from .svg import AttrValue, document, el, esc, fmt


@dataclass(frozen=True)
class TextStyle:
    face: fonts.FontFace
    size: float
    fill: str
    extra_css: str = ""


class Canvas:
    def __init__(
        self,
        asset: str,
        width: float,
        height: float,
        *,
        ledger: Ledger,
        bg: str,
        min_scale: float,
    ) -> None:
        self.asset = asset
        self.width = width
        self.height = height
        self.ledger = ledger
        self.bg = bg
        self.min_scale = min_scale
        self.styles: dict[str, TextStyle] = {}
        self.used: dict[fonts.FontFace, list[str]] = defaultdict(list)

    def style(
        self, name: str, face: fonts.FontFace, size: float, fill: str, extra_css: str = ""
    ) -> str:
        self.styles[name] = TextStyle(face, size, fill, extra_css)
        return name

    def measure(self, content: str, style: str, tracking: float = 0.0) -> float:
        s = self.styles[style]
        return fonts.measure(s.face, content, s.size, tracking)

    def _record(
        self, content: str, style: str, bg: str | None, label: str | None, decorative: bool
    ) -> None:
        s = self.styles[style]
        self.used[s.face].append(content)
        if not decorative:
            self.ledger.add(
                TextEntry(
                    asset=self.asset,
                    label=label or content,
                    fg=s.fill,
                    bg=bg or self.bg,
                    size=s.size,
                    weight=s.face.weight,
                    min_display_scale=self.min_scale,
                )
            )

    def text(
        self,
        content: str,
        x: float,
        y: float,
        style: str,
        *,
        bg: str | None = None,
        anchor: str | None = None,
        attrs: Mapping[str, AttrValue] | None = None,
        label: str | None = None,
        decorative: bool = False,
    ) -> str:
        self._record(content, style, bg, label, decorative)
        values: dict[str, AttrValue] = {"x": x, "y": y, "class": style}
        if anchor:
            values["text-anchor"] = anchor
        values.update(attrs or {})
        return el("text", values, esc(content))

    def tracked(
        self,
        content: str,
        x: float,
        y: float,
        style: str,
        tracking: float,
        *,
        bg: str | None = None,
        anchor: str | None = None,
        attrs: Mapping[str, AttrValue] | None = None,
    ) -> str:
        """Letter-spaced text with the spacing baked into per-glyph x positions.

        SVG ``letter-spacing`` is unreliable across engines, so each glyph gets its own x.
        """
        self._record(content, style, bg, None, False)
        s = self.styles[style]
        widths = fonts.advances(s.face, content, s.size)
        gap = tracking * s.size
        total = sum(widths) + gap * (len(content) - 1)
        start = x - total if anchor == "end" else x - total / 2 if anchor == "middle" else x
        xs: list[str] = []
        cursor = start
        for width in widths:
            xs.append(fmt(cursor))
            cursor += width + gap
        values: dict[str, AttrValue] = {"x": " ".join(xs), "y": y, "class": style}
        values.update(attrs or {})
        return el("text", values, esc(content))

    def css(self) -> str:
        faces = "".join(
            fonts.font_face_css(face, "".join(texts))
            for face, texts in sorted(self.used.items(), key=lambda item: item[0].alias)
        )
        rules = "".join(
            f".{name}{{font-family:'{s.face.alias}';font-size:{fmt(s.size)}px;"
            f"font-weight:{s.face.weight};fill:{s.fill}{';' + s.extra_css if s.extra_css else ''}}}"
            for name, s in self.styles.items()
        )
        return faces + rules

    def render(self, *, title: str, desc: str, body: str, extra_css: str = "") -> str:
        return document(
            width=self.width,
            height=self.height,
            title=title,
            desc=desc,
            css=self.css() + extra_css,
            body=body,
        )
