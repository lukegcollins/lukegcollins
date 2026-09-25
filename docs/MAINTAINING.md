# Maintaining this profile

Everything you see on the profile is generated. The hand-written parts are the prose in
`README.md` outside the `<!-- NAME:START -->` / `<!-- NAME:END -->` markers, the design tokens,
and the lists in `scripts/spectral/` (links, featured cards, stack groups).

## Layout

| Path | What it is |
|---|---|
| `design/tokens.json` | The single source of truth for the Spectral identity: colours for both themes, type, layout limits, motion. |
| `design/fonts/` | Unbounded, Instrument Sans and Martian Mono, unmodified from `google/fonts` at `23e54b51`, each with its OFL text. |
| `design/icons/` | Vendored skill-icons (MIT, `tandpfun/skill-icons` at `7f7e691`) and the Simple Icons 16.32.0 paths used on chips (CC0). |
| `scripts/build_assets.py` | Builds every image in `assets/` and the generated README blocks from the tokens and `data/`. |
| `scripts/refresh.py` | Fetches publications and stats, rebuilds, validates, writes. Run daily by the workflow. |
| `scripts/svgkit/` | Font subsetting, text measurement, contrast ledger, SVG writing, leak check. |
| `scripts/spectral/` | The renderers for this identity. |
| `data/` | `publications.json` (from ORCID) and `stats.json` (aggregates only). |
| `tests/` | Golden files, fixtures and invariants. |

## Rebuild

```bash
uv sync                                   # dev environment from uv.lock
uv run scripts/build_assets.py            # rewrite assets/ and the README blocks
uv run scripts/build_assets.py --check    # what CI runs: fail if anything is stale
uv run pytest                             # UPDATE_GOLDEN=1 regenerates goldens after a deliberate change
uv run ruff check && uv run ruff format --check && uv run mypy
```

The build refuses to write anything that fails WCAG AA contrast or would render below 12 px
on a 390 px phone, and the tests check every SVG for a `viewBox`, `role="img"`, a title and
description, no external references, CSS-only motion on `transform` and `opacity` with a
reduced-motion fallback, and the size budgets (250 KB for the hero and skyline, 80 KB for
everything else).

To change the look, edit `design/tokens.json` and rebuild. Fonts are subset per image and
embedded as WOFF2; the subsets are renamed, as the OFL requires for a modified font.

## The daily refresh

`.github/workflows/refresh.yml` runs at 17:23 UTC every day and on demand
(Actions → refresh → Run workflow). It:

1. reads Luke's works from the ORCID public API (one call) and fills missing venues from
   Crossref (at most 20 calls, with a `mailto`);
2. reads the contribution calendar and language byte counts through GitHub GraphQL;
3. rebuilds, validates, and commits only when something changed, as
   `chore(profile): refresh <what>`.

If ORCID or GitHub is unreachable, or a token has expired, the job still commits whatever did
refresh, then fails so the run shows red. Validation failures commit nothing.

The daily commit also keeps the repository inside GitHub's 60-day activity window, after which
scheduled workflows in public repositories are switched off. If that ever happens, re-enable
the workflow from the Actions tab.

## Secrets

Both tokens are fine-grained personal access tokens with one permission, **Metadata:
read-only**. They can list repositories and read language byte counts and contribution counts.
They cannot read code or write anything. Both are used by the refresh step only.

| Secret | Resource owner | Repositories | Used for |
|---|---|---|---|
| `METRICS_TOKEN` (required) | `lukegcollins` | All repositories | The contribution calendar and language totals across repositories Luke owns, private ones included. |
| `METRICS_TOKEN_ORG` (optional) | `dynamis-group` | All repositories | Adds that organisation's repositories to the language totals. |

`GITHUB_TOKEN` is GitHub's automatic token. The refresh job gets `contents: write` so it can
push its own commit; nothing else is granted.

The tokens expire after a year. When the refresh starts failing with a 401, create a new one
with the same settings (github.com/settings/personal-access-tokens/new) and replace the secret
under Settings → Secrets and variables → Actions.

## Privacy

Private repository names never reach the disk. The refresh holds them in memory only as the
list the leak check must not find: it scans every SVG's visible text, titles and labels, the
README and the data files, and fails the run if any private name shows up. `stats.json`
contains daily counts and language totals, nothing else.

If a private repository's name becomes public on purpose (a method name after its paper is
out, say), add it to `data/public-names.txt` so the check stops flagging it.

Jupyter notebooks are left out of the language totals: their size is mostly embedded output,
not code. Forks are left out too.
