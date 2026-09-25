# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "brotli==1.2.0",
#   "fonttools[woff]==4.66.0",
#   "uharfbuzz==0.56.2",
# ]
# ///
"""Refresh publications (ORCID) and private-aware stats (GitHub), rebuild, validate, write.

    METRICS_TOKEN=... [METRICS_TOKEN_ORG=...] uv run scripts/refresh.py

Exit codes: 0 all sources refreshed; 3 a source failed but everything written is valid (the
workflow still commits it, then fails the run so the problem is visible); 1 validation
failed and nothing was written. Private repository names never touch the disk: they are
held in memory only, as the list the leak check must not find.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spectral import assets, data, github_stats, orcid, validate
from svgkit import leaks

ALLOWLIST = assets.ROOT / "data" / "public-names.txt"
PUBLIC_ORGS = ("dynamis-group", "dfwb-research", "CSCRC-SCREED", "NASA-Protocol-Exploits")


def output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main() -> int:
    status = 0
    old_pubs, old_stats = data.load_publications(), data.load_stats()

    try:
        pubs = orcid.fetch_publications()
    except (OSError, ValueError, KeyError) as exc:
        print(f"::warning::ORCID unavailable ({exc}); keeping the last publication list")
        pubs, status = old_pubs, 3

    forbidden: frozenset[str] = frozenset()
    token = os.environ.get("METRICS_TOKEN", "")
    if not token:
        print(
            "::error::METRICS_TOKEN is not set; stats were not refreshed (see docs/MAINTAINING.md)"
        )
        stats, status = old_stats, 3
    else:
        try:
            collected = github_stats.collect(
                token,
                org_token=os.environ.get("METRICS_TOKEN_ORG") or None,
                org=os.environ.get("METRICS_ORG", "dynamis-group"),
            )
            stats, forbidden = collected.stats, collected.forbidden
            if not stats.includes_private:
                print(
                    "::notice::GitHub reported no private contributions. Turn on 'Private "
                    "contributions' under Contribution settings on the profile to count them."
                )
        except (OSError, ValueError, KeyError, github_stats.GraphQLError) as exc:
            print(f"::error::GitHub stats failed ({exc}); keeping the last numbers")
            stats, status = old_stats, 3

    built, ledger = assets.build_all(stats, pubs)
    built[data.STATS] = data.dump_stats(stats)
    built[data.PUBLICATIONS] = data.dump_publications(pubs)

    problems = list(ledger.failures(assets.TOKENS.min_text_px))
    for path, content in built.items():
        if path.suffix == ".svg":
            problems += validate.check_svg(str(path.relative_to(assets.ASSETS)), content)
    outputs = {str(path.relative_to(assets.ROOT)): content for path, content in built.items()}
    problems += leaks.find_leaks(
        outputs, forbidden, [*leaks.read_allowlist(ALLOWLIST), *PUBLIC_ORGS]
    )
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        output("commit", "false")
        return 1

    changed = assets.write(built)
    parts = []
    if data.PUBLICATIONS in changed:
        parts.append("publications")
    if data.STATS in changed:
        parts.append("stats")
    output("commit", "true")
    output("what", " and ".join(parts) or "assets")
    print(f"{len(changed)} files changed" + (f" ({', '.join(parts)})" if parts else ""))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
