"""Golden files for every renderer.

Static renderers (hero, badges, cards, stack tiles) are compared with the committed assets,
which are their goldens. Data-driven renderers are compared with tests/golden/, built from the
synthetic fixture data so the goldens never change when real data refreshes.
"""

from __future__ import annotations

from pathlib import Path

from conftest import FIXTURES, assert_golden
from spectral import activity, assets, cards, hero, readme, stack
from spectral.data import Publications, load_stats
from svgkit.color import Ledger

SAMPLE = load_stats(FIXTURES / "stats_sample.json")


def committed(rel: str) -> str:
    return (assets.ASSETS / rel).read_text(encoding="utf-8")


def test_hero_wide_and_compact() -> None:
    for name, theme in assets.TOKENS.themes.items():
        wide = hero.render(assets.TOKENS, theme, hero.WIDE, Ledger(), "hero")
        compact = hero.render(assets.TOKENS, theme, hero.COMPACT, Ledger(), "hero")
        assert wide == committed(f"hero-{name}.svg")
        assert compact == committed(f"hero-{name}-compact.svg")


def test_badges_cards_and_stack() -> None:
    theme = assets.TOKENS.themes["dark"]
    for link in assets.LINKS:
        rendered = cards.badge(assets.TOKENS, theme, link, Ledger(), "badge")
        assert rendered == committed(f"links/{link.slug}-dark.svg")
    for feature in assets.FEATURES:
        rendered = cards.feature(assets.TOKENS, theme, feature, Ledger(), "card")
        assert rendered == committed(f"cards/{feature.slug}-dark.svg")
    for _, tools in stack.GROUPS:
        for tool in tools:
            rendered = stack.render(assets.TOKENS, theme, tool, Ledger(), "tile")
            assert rendered == committed(f"stack/{tool.slug}-dark.svg")


def test_activity_images_from_fixture_data() -> None:
    for name, theme in sorted(assets.TOKENS.themes.items()):
        ledger = Ledger()
        assert_golden(
            f"skyline-{name}.svg", activity.skyline(assets.TOKENS, theme, SAMPLE, ledger, "s")
        )
        assert_golden(
            f"contributions-{name}.svg",
            activity.contributions_card(assets.TOKENS, theme, SAMPLE, ledger, "c"),
        )
        assert_golden(
            f"languages-{name}.svg",
            activity.languages_card(assets.TOKENS, theme, SAMPLE, ledger, "l"),
        )
        assert ledger.failures(assets.TOKENS.min_text_px) == []


def test_activity_images_before_the_first_refresh() -> None:
    from spectral.data import Stats

    theme = assets.TOKENS.themes["dark"]
    empty = Stats()
    ledger = Ledger()
    card = activity.contributions_card(assets.TOKENS, theme, empty, ledger, "c")
    assert "—" in card
    langs = activity.languages_card(assets.TOKENS, theme, empty, ledger, "l")
    assert "waiting for the first refresh" in langs
    assert ledger.failures(assets.TOKENS.min_text_px) == []


def test_readme_blocks_from_fixture_data() -> None:
    assert_golden("activity-block.md", readme.activity_block(SAMPLE) + "\n")
    assert_golden("stack-block.md", readme.stack_block() + "\n")
    assert_golden("links-block.md", readme.links_block() + "\n")
    assert_golden("features-block.md", readme.features_block() + "\n")
    assert "ORCID" in readme.publications_block(Publications())


def test_replace_block_requires_markers() -> None:
    import pytest

    with pytest.raises(ValueError, match="STACK"):
        readme.replace_block("no markers here", "STACK", "x")
    text = "a\n<!-- X:START -->\nold\n<!-- X:END -->\nb"
    assert readme.replace_block(text, "X", "new") == "a\n<!-- X:START -->\nnew\n<!-- X:END -->\nb"


def test_markdown_escaping_covers_maths_and_emphasis() -> None:
    assert readme.md_escape("costs $5 *now*") == r"costs \$5 \*now\*"
    assert readme.md_escape("a\n  b") == "a b"


def test_goldens_directory_has_no_strays() -> None:
    expected = {
        *(
            f"{kind}-{t}.svg"
            for kind in ("skyline", "contributions", "languages")
            for t in ("dark", "light")
        ),
        "activity-block.md",
        "stack-block.md",
        "links-block.md",
        "features-block.md",
        "publications-block.md",
        "publications.json",
        "stats.json",
    }
    present = {p.name for p in (Path(__file__).parent / "golden").iterdir()}
    assert present == expected
