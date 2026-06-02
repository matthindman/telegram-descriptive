"""Extract URL/domain edges from message rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from telegram_descriptive.tables import stable_edge_id


def domain_from_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc.lower().removeprefix("www.")


def url_edges(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for row in rows:
        source = row.get("canonical_channel_id") or row.get("channel_id")
        post_uid = row.get("post_uid")
        urls = row.get("urls") or row.get("outlinks") or []
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            domain = domain_from_url(str(url))
            if not source or not domain:
                continue
            edges.append(
                {
                    "edge_id": stable_edge_id(source, domain, post_uid, "url_link"),
                    "source_channel_id": str(source),
                    "target": domain,
                    "edge_type": "url_link",
                    "post_uid": post_uid,
                    "is_artificial_crawl_edge": False,
                }
            )
    return edges

