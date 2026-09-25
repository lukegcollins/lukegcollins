"""Private-aware GitHub statistics, reduced to aggregates before anything is written.

METRICS_TOKEN (fine-grained, resource owner lukegcollins, Metadata: read-only) sees every
repository Luke owns, private ones included. METRICS_TOKEN_ORG (same permission, resource owner
dynamis-group) optionally adds that organisation's repositories. Repository names are only
held in memory, as the list the leak check must never find in the output.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .data import Stats

GRAPHQL = "https://api.github.com/graphql"
EXCLUDED_LANGUAGES = ("Jupyter Notebook",)
USER_AGENT = "lukegcollins-profile/1.0 (+https://github.com/lukegcollins/lukegcollins)"

Post = Callable[[str, str, Mapping[str, Any]], Mapping[str, Any]]

CALENDAR = """
query {
  viewer {
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

REPO_FIELDS = """
pageInfo { hasNextPage endCursor }
nodes {
  name
  nameWithOwner
  isPrivate
  languages(first: 25, orderBy: {field: SIZE, direction: DESC}) {
    edges { size node { name } }
  }
}
"""

OWNED = (
    "query($cursor: String) { viewer { repositories(ownerAffiliations: OWNER, isFork: false, "
    "first: 100, after: $cursor) {" + REPO_FIELDS + "} } }"
)

ORG = (
    "query($org: String!, $cursor: String) { organization(login: $org) { "
    "repositories(isFork: false, first: 100, after: $cursor) {" + REPO_FIELDS + "} } }"
)


class GraphQLError(RuntimeError):
    pass


def http_post(token: str, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
    body = json.dumps({"query": query, "variables": dict(variables)}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (fixed URL)
        payload = json.load(response)
    if payload.get("errors"):
        messages = "; ".join(str(e.get("message", e)) for e in payload["errors"])
        raise GraphQLError(messages)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GraphQLError("GraphQL response carried no data")
    return data


@dataclass(frozen=True)
class Collected:
    stats: Stats
    forbidden: frozenset[str]


def _pages(
    post: Post, token: str, query: str, variables: dict[str, Any], path: tuple[str, ...]
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(50):  # 5,000 repositories is far beyond any real account
        data: Any = post(token, query, {**variables, "cursor": cursor})
        for key in path:
            data = (data or {}).get(key)
        if not isinstance(data, dict):
            raise GraphQLError(f"unexpected response shape at {'/'.join(path)}")
        nodes.extend(n for n in data.get("nodes") or [] if isinstance(n, dict))
        info = data.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return nodes
        cursor = info.get("endCursor")
    raise GraphQLError("pagination did not finish")


def _calendar(data: Mapping[str, Any]) -> tuple[int, int, tuple[tuple[str, int], ...]]:
    collection = data["viewer"]["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    days = sorted(
        (str(day["date"]), int(day["contributionCount"]))
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    )
    restricted = int(collection.get("restrictedContributionsCount") or 0)
    return int(calendar["totalContributions"]), restricted, tuple(days)


def aggregate(
    calendar: Mapping[str, Any],
    repos: list[dict[str, Any]],
    *,
    scope: str,
    orgs: tuple[str, ...] = (),
    excluded: tuple[str, ...] = EXCLUDED_LANGUAGES,
) -> Collected:
    total, restricted, days = _calendar(calendar)
    sizes: dict[str, int] = {}
    forbidden: set[str] = set()
    for repo in repos:
        if repo.get("isPrivate"):
            forbidden.update(str(repo[k]) for k in ("name", "nameWithOwner") if repo.get(k))
        for edge in (repo.get("languages") or {}).get("edges") or []:
            name = str(edge["node"]["name"])
            if name in excluded:
                continue
            sizes[name] = sizes.get(name, 0) + int(edge["size"])
    stats = Stats(
        as_of=days[-1][0] if days else None,
        total=total,
        private_counted=restricted,
        days=days,
        languages=tuple(sorted(sizes.items(), key=lambda item: (-item[1], item[0]))),
        language_scope=scope,
        language_orgs=orgs,
        excluded_languages=tuple(sorted(excluded)),
    )
    return Collected(stats=stats, forbidden=frozenset(forbidden))


def collect(
    token: str,
    *,
    org_token: str | None = None,
    org: str = "dynamis-group",
    post: Post = http_post,
) -> Collected:
    calendar = post(token, CALENDAR, {})
    repos = _pages(post, token, OWNED, {}, ("viewer", "repositories"))
    scope = "owned repos · private included"
    orgs: tuple[str, ...] = ()
    if org_token:
        repos += _pages(post, org_token, ORG, {"org": org}, ("organization", "repositories"))
        scope, orgs = "owned + org repos · private included", (org,)
    return aggregate(calendar, repos, scope=scope, orgs=orgs)
