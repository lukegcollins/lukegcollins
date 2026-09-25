"""The profile hero: name in RGB register, headline, roles, spectrum and a scanned face mesh.

Two layouts share one drawing routine: ``wide`` for desktop and ``compact`` for phones (the
README swaps them with a ``max-width`` media query). Every animated element's resting style
is the settled frame, so reduced motion simply switches the keyframes off.
"""

from __future__ import annotations

from dataclasses import dataclass

from svgkit.canvas import Canvas
from svgkit.color import Ledger
from svgkit.svg import el, fmt

from . import motifs
from .theme import Theme, Tokens

NAME = "Luke Collins"
HEADLINE = ("Deepfake detection researcher", "who ships production systems.")
ROLES = (
    "PhD candidate · Deakin University",
    "Managing Director · Dynamis Group",
    "Lead maintainer · DFWB",
)
READOUT = "p(synthetic) = 0.03"
FACE_LABEL = "face 01"
TIMECODE = "TC 00:00:04:12"
AXIS = "log |F(u)|"

TITLE = f"{NAME}: deepfake detection researcher who ships production systems."
DESC = (
    "Luke Collins's name, drawn as red, green and blue channels that drift apart and lock "
    "back into register. Beside it, an abstract face-mesh constellation inside detection "
    "brackets with the readout p(synthetic) = 0.03, and a frequency spectrum with a slow "
    "sweep. Roles: PhD candidate at Deakin University, Managing Director of Dynamis Group, "
    "lead maintainer of DFWB."
)


@dataclass(frozen=True)
class Layout:
    width: float
    height: float
    name: tuple[float, float, float]  # x, baseline, size
    headline: tuple[float, float, float, float]  # x, first baseline, line gap, size
    panel: tuple[float, float, float, float]  # x, y, w, h
    brackets: tuple[float, float, float, float, float]  # x, y, w, h, arm
    face_label: tuple[float, float]
    timecode: tuple[float, float] | None
    readout: tuple[float, float, float]  # x, baseline, size
    spectrum: tuple[float, float, float, float]  # x, y, w, h
    axis: tuple[float, float] | None
    rule_y: float
    roles: tuple[float, float, float, float]  # x, first baseline, line gap (0 = one line), size
    label_size: float
    drift: float
    mobile: bool


WIDE = Layout(
    width=880,
    height=400,
    name=(40, 128, 62),
    headline=(40, 176, 32, 22),
    panel=(584, 40, 256, 288),
    brackets=(616, 84, 192, 196, 16),
    face_label=(604, 70),
    timecode=(820, 70),
    readout=(604, 312, 14),
    spectrum=(40, 256, 480, 64),
    axis=(40, 244),
    rule_y=352.5,
    roles=(40, 380, 0, 13),
    label_size=12.5,
    drift=2,
    mobile=False,
)

COMPACT = Layout(
    width=400,
    height=456,
    name=(24, 64, 40),
    headline=(24, 104, 26, 19),
    panel=(24, 160, 352, 176),
    brackets=(40, 176, 112, 144, 12),
    face_label=(168, 200),
    timecode=None,
    readout=(168, 228, 15),
    spectrum=(168, 252, 192, 60),
    axis=None,
    rule_y=352.5,
    roles=(24, 384, 26, 15),
    label_size=15,
    drift=1.5,
    mobile=True,
)


def _css(theme: Theme, layout: Layout, loop: float) -> str:
    bh = layout.brackets[3]
    sw = layout.spectrum[2]
    d = layout.drift
    return (
        f".rgb{{isolation:isolate}}.ch{{mix-blend-mode:{theme.channel_blend}}}"
        f".me{{stroke:{theme.accent_from};stroke-opacity:.3;stroke-width:.7}}"
        f".mp{{fill:{theme.muted}}}.mm{{fill:{theme.accent_from}}}"
        f".bk{{fill:none;stroke:{theme.text};stroke-width:1.5}}"
        f".bka{{fill:none;stroke:{theme.accent_from};stroke-width:1.5;opacity:0}}"
        f".sw,.sc{{opacity:0}}"
        f"@keyframes r{{0%,3%,15%,100%{{transform:none}}6%{{transform:translate({fmt(-d)}px,0)}}"
        f"9%{{transform:translate({fmt(-d * 0.6)}px,1px)}}"
        f"12%{{transform:translate({fmt(-d * 0.8)}px,0)}}}}"
        f"@keyframes g{{0%,3%,15%,100%{{transform:none}}6%{{transform:translate(1px,-1px)}}"
        f"9%{{transform:translate(0,1px)}}12%{{transform:translate(.5px,0)}}}}"
        f"@keyframes b{{0%,3%,15%,100%{{transform:none}}6%{{transform:translate({fmt(d)}px,0)}}"
        f"9%{{transform:translate({fmt(d * 0.6)}px,-1px)}}"
        f"12%{{transform:translate({fmt(d * 0.8)}px,0)}}}}"
        f"@keyframes p{{0%,2%,17%,100%{{opacity:1}}4%,15%{{opacity:0}}}}"
        f"@keyframes sw{{0%,17%{{transform:none;opacity:0}}19%{{opacity:.85}}"
        f"50%{{transform:translateX({fmt(sw)}px);opacity:.85}}52%,100%{{transform:translateX({fmt(sw)}px);opacity:0}}}}"
        f"@keyframes sc{{0%,17%{{transform:none;opacity:0}}19%{{opacity:.9}}"
        f"45%{{transform:translateY({fmt(bh)}px);opacity:.9}}47%,100%{{transform:translateY({fmt(bh)}px);opacity:0}}}}"
        f"@keyframes v{{0%,17%,48%,100%{{opacity:1}}20%,46%{{opacity:.25}}}}"
        f"@keyframes l{{0%,46%,62%,100%{{opacity:0}}48%{{opacity:1}}}}"
        f".cr{{animation:r {fmt(loop)}s ease-in-out infinite}}"
        f".cg{{animation:g {fmt(loop)}s ease-in-out infinite}}"
        f".cb{{animation:b {fmt(loop)}s ease-in-out infinite}}"
        f".pl{{animation:p {fmt(loop)}s linear infinite}}"
        f".sw{{animation:sw {fmt(loop)}s ease-in-out infinite}}"
        f".sc{{animation:sc {fmt(loop)}s ease-in-out infinite}}"
        f".vd{{animation:v {fmt(loop)}s ease-in-out infinite}}"
        f".bka{{animation:l {fmt(loop)}s ease-out infinite}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )


def render(tokens: Tokens, theme: Theme, layout: Layout, ledger: Ledger, asset: str) -> str:
    f = tokens.fonts
    scale = tokens.min_scale(layout.width, mobile=layout.mobile)
    c = Canvas(asset, layout.width, layout.height, ledger=ledger, bg=theme.bg, min_scale=scale)
    nx, ny, ns = layout.name
    hx, hy, hgap, hs = layout.headline
    px, py, pw, ph = layout.panel
    bx, by, bw, bh, arm = layout.brackets
    sx, sy, sw, sh = layout.spectrum
    rx, ry, rgap, rs = layout.roles

    c.style("n", f.display, ns, theme.text)
    c.style("h", f.text, hs, theme.text)
    c.style("k", f.mono, layout.label_size, theme.muted)
    c.style("o", f.mono, layout.readout[2], theme.accent_text)
    c.style("q", f.mono, rs, theme.muted)

    parts: list[str] = [
        el("defs", None, motifs.accent_gradient("sg", theme, sx, sx + sw)),
        el("rect", {"width": layout.width, "height": layout.height, "rx": 12, "fill": theme.bg}),
        el(
            "rect",
            {
                "x": 0.5,
                "y": 0.5,
                "width": layout.width - 1,
                "height": layout.height - 1,
                "rx": 11.5,
                "fill": "none",
                "stroke": theme.hairline,
            },
        ),
    ]

    # Name: three channel layers that drift, and a plain layer that hides them at rest.
    # A class rule would override a fill attribute, so each channel gets its own style.
    for index, colour in enumerate(theme.channels):
        c.style(f"n{index}", f.display, ns, colour)
    channels = "".join(
        el("g", {"class": f"ch {cls}"}, c.text(NAME, nx, ny, f"n{index}", decorative=True))
        for index, cls in enumerate(("cr", "cg", "cb"))
    )
    parts.append(el("g", {"class": "rgb", "aria-hidden": "true"}, channels))
    parts.append(el("g", {"class": "pl"}, c.text(NAME, nx, ny, "n")))

    for i, line in enumerate(HEADLINE):
        parts.append(c.text(line, hx, hy + i * hgap, "h"))

    # The panel frame goes down first: on phones the spectrum sits inside it.
    parts.append(
        el(
            "rect",
            {
                "x": px + 0.5,
                "y": py + 0.5,
                "width": pw - 1,
                "height": ph - 1,
                "rx": 8,
                "fill": theme.surface,
                "stroke": theme.hairline,
            },
        )
    )

    # Spectrum with its sweep line.
    parts.append(motifs.spectrum(sx, sy, sw, sh, 120 if not layout.mobile else 64, "sg"))
    parts.append(
        el(
            "path",
            {
                "d": f"M{fmt(sx)} {fmt(sy + sh + 0.5)}H{fmt(sx + sw)}",
                "stroke": theme.hairline_strong,
            },
        )
    )
    if layout.axis:
        parts.append(c.text(AXIS, layout.axis[0], layout.axis[1], "k"))
    parts.append(
        el(
            "g",
            {"class": "sw"},
            el("path", {"d": f"M{fmt(sx)} {fmt(sy - 4)}V{fmt(sy + sh)}", "stroke": theme.text}),
        )
    )

    # Analysis panel: the detection brackets, the mesh, the scan line, the verdict.
    parts.append(
        c.text(FACE_LABEL, layout.face_label[0], layout.face_label[1], "k", bg=theme.surface)
    )
    if layout.timecode:
        parts.append(
            c.text(
                TIMECODE,
                layout.timecode[0],
                layout.timecode[1],
                "k",
                anchor="end",
                bg=theme.surface,
            )
        )
    inset = arm
    parts.append(motifs.mesh(bx + inset, by + inset * 0.75, bw - 2 * inset, bh - 1.5 * inset))
    parts.append(motifs.brackets(bx, by, bw, bh, arm, "bk"))
    parts.append(motifs.brackets(bx, by, bw, bh, arm, "bka"))
    parts.append(
        el(
            "g",
            {"class": "sc"},
            el(
                "path",
                {"d": f"M{fmt(bx + 4)} {fmt(by)}H{fmt(bx + bw - 4)}", "stroke": theme.accent_from},
            ),
        )
    )
    rox, roy, _ = layout.readout
    parts.append(el("g", {"class": "vd"}, c.text(READOUT, rox, roy, "o", bg=theme.surface)))

    parts.append(
        el(
            "path",
            {
                "d": f"M{fmt(rx)} {fmt(layout.rule_y)}H{fmt(layout.width - rx)}",
                "stroke": theme.hairline,
            },
        )
    )
    if rgap:
        for i, role in enumerate(ROLES):
            parts.append(c.text(role, rx, ry + i * rgap, "q"))
    else:
        parts.append(c.text(" / ".join(ROLES), rx, ry, "q"))

    return c.render(
        title=TITLE, desc=DESC, body="".join(parts), extra_css=_css(theme, layout, tokens.loop_s)
    )
