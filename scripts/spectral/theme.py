"""Load design/tokens.json into typed objects shared by every Spectral renderer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from svgkit import fonts

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "design" / "tokens.json"
FONT_DIR = ROOT / "design" / "fonts"


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    surface: str
    hairline: str
    hairline_strong: str
    text: str
    muted: str
    accent_from: str
    accent_to: str
    accent_text: str
    channels: tuple[str, str, str]
    channel_blend: str
    page_behind: str


@dataclass(frozen=True)
class Fonts:
    display: fonts.FontFace
    text: fonts.FontFace
    text_regular: fonts.FontFace
    mono: fonts.FontFace


@dataclass(frozen=True)
class Tokens:
    themes: dict[str, Theme]
    fonts: Fonts
    desktop_px: float
    mobile_px: float
    min_text_px: float
    loop_s: float

    def min_scale(self, width: float, *, mobile: bool = True) -> float:
        """Smallest scale an image of intrinsic ``width`` is shown at on the profile page."""
        widest = self.mobile_px if mobile else self.desktop_px
        return min(1.0, widest / width)


_ALIASES = {"display": "d", "text": "s", "text_regular": "r", "mono": "m"}


def _face(role: str, spec: dict[str, object]) -> fonts.FontFace:
    axes = spec.get("axes", {})
    assert isinstance(axes, dict)
    weight = spec["weight"]
    assert isinstance(weight, int)
    return fonts.FontFace(
        alias=_ALIASES[role],
        path=FONT_DIR / str(spec["file"]),
        weight=weight,
        axes=tuple(sorted((str(k), float(v)) for k, v in axes.items())),
    )


def load(path: Path = TOKENS) -> Tokens:
    data = json.loads(path.read_text(encoding="utf-8"))
    themes = {}
    for name, t in data["themes"].items():
        themes[name] = Theme(
            name=name,
            bg=t["bg"],
            surface=t["surface"],
            hairline=t["hairline"],
            hairline_strong=t["hairline_strong"],
            text=t["text"],
            muted=t["muted"],
            accent_from=t["accent_from"],
            accent_to=t["accent_to"],
            accent_text=t["accent_text"],
            channels=(t["channels"][0], t["channels"][1], t["channels"][2]),
            channel_blend=t["channel_blend"],
            page_behind=t["page_behind"],
        )
    types = data["type"]
    fonts = Fonts(
        display=_face("display", types["display"]),
        text=_face("text", types["text"]),
        text_regular=_face("text_regular", types["text_regular"]),
        mono=_face("mono", types["mono"]),
    )
    layout = data["layout"]
    return Tokens(
        themes=themes,
        fonts=fonts,
        desktop_px=float(layout["desktop_content_px"]),
        mobile_px=float(layout["mobile_content_px"]),
        min_text_px=float(layout["min_text_px"]),
        loop_s=float(data["motion"]["loop_s"]),
    )
