"""WCAG contrast arithmetic and a ledger that records every piece of text an image draws."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RGB = tuple[float, float, float]

_RGBA = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)")


def parse(colour: str) -> tuple[RGB, float]:
    """Parse ``#rgb``, ``#rrggbb`` or ``rgba(r,g,b,a)`` into 0..1 channels and alpha."""
    value = colour.strip()
    if value.startswith("#"):
        digits = value[1:]
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
        return (r, g, b), 1.0
    match = _RGBA.fullmatch(value)
    if not match:
        raise ValueError(f"unsupported colour {colour!r}")
    r, g, b = (float(match.group(i)) / 255 for i in (1, 2, 3))
    alpha = float(match.group(4)) if match.group(4) is not None else 1.0
    return (r, g, b), alpha


def over(fg: str, bg: str) -> RGB:
    """Composite ``fg`` (which may carry alpha) over an opaque ``bg``."""
    (fr, fg_, fb), alpha = parse(fg)
    (br, bg_, bb), _ = parse(bg)
    return (
        fr * alpha + br * (1 - alpha),
        fg_ * alpha + bg_ * (1 - alpha),
        fb * alpha + bb * (1 - alpha),
    )


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(rgb: RGB) -> float:
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    a = luminance(over(fg, bg))
    b = luminance(parse(bg)[0])
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def is_large(size_px: float, weight: int) -> bool:
    """WCAG 'large text': at least 24 px, or at least 18.66 px (14 pt) when bold."""
    return size_px >= 24 or (size_px >= 18.66 and weight >= 700)


@dataclass(frozen=True)
class TextEntry:
    asset: str
    label: str
    fg: str
    bg: str
    size: float
    weight: int
    min_display_scale: float

    @property
    def ratio(self) -> float:
        return contrast(self.fg, self.bg)

    @property
    def required(self) -> float:
        return 3.0 if is_large(self.size, self.weight) else 4.5

    @property
    def smallest_px(self) -> float:
        return self.size * self.min_display_scale


@dataclass
class Ledger:
    """Collects text drawn into images so the build can refuse illegible output."""

    entries: list[TextEntry] = field(default_factory=list)
    decorative: list[str] = field(default_factory=list)

    def add(self, entry: TextEntry) -> None:
        self.entries.append(entry)

    def failures(self, min_px: float = 12.0) -> list[str]:
        problems: list[str] = []
        for e in self.entries:
            if e.ratio + 1e-9 < e.required:
                problems.append(
                    f"{e.asset}: '{e.label}' contrast {e.ratio:.2f} < {e.required} "
                    f"({e.fg} on {e.bg}, {e.size}px)"
                )
            if e.smallest_px + 1e-9 < min_px:
                problems.append(
                    f"{e.asset}: '{e.label}' renders at {e.smallest_px:.1f}px (< {min_px}px)"
                )
        return problems
