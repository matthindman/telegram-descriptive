"""Extract forwarded/reply/quote edges from message rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from telegram_descriptive.tables import stable_edge_id


def forwarding_edges(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for row in rows:
        source = row.get("canonical_channel_id") or row.get("channel_id")
        post_uid = row.get("post_uid")
        targets = {
            "forwarded_from": row.get("shared_id") or row.get("repost_channel_data"),
            "quoted_post": row.get("quoted_id"),
            "reply_to": row.get("replied_id") or row.get("root_post_id"),
        }
        for edge_type, target in targets.items():
            if not source or not target:
                continue
            edges.append(
                {
                    "edge_id": stable_edge_id(source, target, post_uid, edge_type),
                    "source_channel_id": str(source),
                    "target": str(target),
                    "edge_type": edge_type,
                    "post_uid": post_uid,
                    "is_artificial_crawl_edge": False,
                }
            )
    return edges

