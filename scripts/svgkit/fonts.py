"""Embed subset fonts in SVG images and measure text with the same fonts.

GitHub serves README images from a sandbox that blocks every external request, so an SVG can
only use a font it carries itself. Each face is instanced at a fixed axis location, subset to
the characters the image actually draws, compressed to WOFF2 and inlined as a data URI.

The subset is a Modified Version under the SIL OFL, so it is renamed (clause 3: no Reserved
Font Name on a Modified Version) while the copyright and licence records stay in the file
(clause 2). The unmodified originals and their OFL texts live in design/fonts/.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# Name records kept in the subset: copyright (0), subfamily (2), version (5), licence (13, 14).
# Records 1, 3, 4 and 6 are rewritten to the alias; everything else is dropped.
_KEEP_NAME_IDS = (0, 1, 2, 3, 4, 5, 6, 13, 14)
_RENAMED_IDS = (1, 3, 4, 6)
# Always embedded so that numbers and punctuation in data-driven text never fall back.
BASELINE_CHARS = " 0123456789.,:;·-–—/()%+=±→"


@dataclass(frozen=True)
class FontFace:
    """One embedded face: a source file, a variable-font location and a CSS alias."""

    alias: str
    path: Path
    weight: int = 400
    axes: tuple[tuple[str, float], ...] = ()
    features: tuple[str, ...] = ("kern", "liga", "calt")

    @property
    def location(self) -> dict[str, float]:
        return dict(self.axes)


def _static_instance(face: FontFace) -> TTFont:
    font = TTFont(str(face.path), recalcTimestamp=False, recalcBBoxes=True)
    if "fvar" in font:
        axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
        axes.update(face.location)
        font = instancer.instantiateVariableFont(font, axes, inplace=False)
    return font


def _rename(font: TTFont, face: FontFace) -> None:
    name = font["name"]
    postscript = f"{face.alias}-{face.weight}".replace(" ", "")
    values = {1: face.alias, 3: postscript, 4: f"{face.alias} {face.weight}", 6: postscript}
    for name_id in _RENAMED_IDS:
        name.removeNames(nameID=name_id)
        name.setName(values[name_id], name_id, 3, 1, 0x409)


@lru_cache(maxsize=256)
def _woff2(face: FontFace, chars: str) -> bytes:
    font = _static_instance(face)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = list(face.features)
    options.name_IDs = list(_KEEP_NAME_IDS)
    options.name_languages = [0x409]
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True
    options.drop_tables = [*options.drop_tables, "meta"]  # no rendering role in a subset
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    _rename(font, face)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer, reorderTables=True)
    return buffer.getvalue()


def woff2(face: FontFace, text: str) -> bytes:
    """Subset WOFF2 bytes covering ``text`` plus digits and common punctuation."""
    chars = "".join(sorted(set(text) | set(BASELINE_CHARS)))
    return _woff2(face, chars)


def font_face_css(face: FontFace, text: str) -> str:
    data = base64.b64encode(woff2(face, text)).decode("ascii")
    return (
        f"@font-face{{font-family:'{face.alias}';font-weight:{face.weight};"
        f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    )


@lru_cache(maxsize=64)
def _hb_font(path: Path, axes: tuple[tuple[str, float], ...]) -> tuple[hb.Font, int]:
    blob = hb.Blob.from_file_path(str(path))
    hb_face = hb.Face(blob)
    font = hb.Font(hb_face)
    if axes:
        font.set_variations(dict(axes))
    return font, hb_face.upem


def advances(face: FontFace, text: str, size: float) -> list[float]:
    """Per-character advances in px at ``size``, one entry per input character."""
    font, upem = _hb_font(face.path, face.axes)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer, dict.fromkeys(face.features, True))
    scale = size / upem
    out = [0.0] * len(text)
    # Cluster values are UTF-8 byte offsets; map them back to character indices.
    byte_to_char: dict[int, int] = {}
    offset = 0
    for index, char in enumerate(text):
        byte_to_char[offset] = index
        offset += len(char.encode("utf-8"))
    for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        out[byte_to_char.get(info.cluster, 0)] += pos.x_advance * scale
    return out


def measure(face: FontFace, text: str, size: float, tracking: float = 0.0) -> float:
    """Rendered width in px, with ``tracking`` (in em) added between characters."""
    if not text:
        return 0.0
    return sum(advances(face, text, size)) + tracking * size * (len(text) - 1)


@lru_cache(maxsize=64)
def _cap_units(path: Path) -> tuple[int, int]:
    font = TTFont(str(path), lazy=True)
    upem = int(font["head"].unitsPerEm)
    cap = int(getattr(font["OS/2"], "sCapHeight", 0) or upem * 0.7)
    return cap, upem


def cap_height(face: FontFace, size: float) -> float:
    cap, upem = _cap_units(face.path)
    return cap * size / upem
