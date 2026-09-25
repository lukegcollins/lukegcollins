"""The committed images and README must equal a fresh build, and the build must be stable."""

from __future__ import annotations

from spectral import assets
from spectral.validate import check_svg


def test_committed_files_match_a_fresh_build() -> None:
    built, _ = assets.build_all()
    assert assets.stale(built) == []


def test_build_is_deterministic() -> None:
    first, _ = assets.build_all()
    second, _ = assets.build_all()
    assert first == second


def test_every_string_is_legible() -> None:
    _, ledger = assets.build_all()
    assert ledger.entries, "the ledger recorded no text at all"
    assert ledger.failures(assets.TOKENS.min_text_px) == []


def test_every_committed_svg_passes_hygiene_checks() -> None:
    svgs = sorted(assets.ASSETS.rglob("*.svg"))
    assert len(svgs) > 50
    problems = [
        problem
        for path in svgs
        for problem in check_svg(
            str(path.relative_to(assets.ASSETS)), path.read_text(encoding="utf-8")
        )
    ]
    assert problems == []


def test_every_picture_has_both_variants() -> None:
    import re

    readme = assets.README.read_text(encoding="utf-8")
    sources = re.findall(r'(?:srcset|src)="(assets/[^"]+\.svg)"', readme)
    assert sources
    for rel in sources:
        assert (assets.ROOT / rel).exists(), rel
        twin = rel.replace("-dark", "-light") if "-dark" in rel else rel.replace("-light", "-dark")
        assert (assets.ROOT / twin).exists(), twin
