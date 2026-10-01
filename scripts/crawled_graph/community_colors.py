"""Assign palette colours so that spatially adjacent communities look different.

`community % len(palette)` gives neighbouring communities identical or nearly
identical hues by chance. Here adjacency is measured on the rendered layout: each
node's k nearest display neighbours that belong to another community add weight
to that community pair, with larger stored audiences counting slightly more
because their marks are larger. Communities are coloured greedily in order of
visual salience; each takes the palette entry least similar (CIELAB distance) to
its already-coloured neighbours, weighted by adjacency. The result is
deterministic for fixed inputs. Colours remain categorical identifiers only.
"""
import numpy as np
from scipy.spatial import cKDTree


def _lab(hex_color):
    c = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    c = np.where(c > .04045, ((c + .055) / 1.055) ** 2.4, c / 12.92)
    xyz = np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]]) @ c
    xyz = xyz / np.array([.95047, 1, 1.08883])
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def palette_similarity(palette):
    lab = np.array([_lab(h) for h in palette])
    delta = np.linalg.norm(lab[:, None] - lab[None], axis=2)
    return np.exp(-delta / 10.0), delta


def community_adjacency(xy, community, subscribers, k=6, salient_quantile=.95, radius=120.0, radius_weight=.5, min_cluster=20, region=None):
    """Two neighbourhoods: every node's k nearest marks, and all pairs of salient
    marks within a fixed display radius (world units), which link clusters that
    are separated by a small visible gap even when each cluster is dense.

    The radius term uses only communities with at least `min_cluster` members
    (visible clusters) and, when `region` is given, only nodes where region is
    true (e.g. the main component; component shelves are nonstructural)."""
    parts = []

    def accumulate(a, b, weight):
        ca, cb = community[a], community[b]
        keep = ca != cb
        parts.append((np.minimum(ca[keep], cb[keep]), np.maximum(ca[keep], cb[keep]), weight[keep]))

    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=k + 1)
    a = np.repeat(np.arange(len(xy)), k)
    b = idx[:, 1:].ravel()
    accumulate(a, b, 1 + np.log1p(np.minimum(subscribers[a], subscribers[b])) / 5)
    # Salient marks: globally large nodes plus each community's own largest members,
    # so a small cluster's visible core still links to a neighbouring cluster.
    order = np.lexsort((-subscribers, community))
    first = np.r_[0, np.flatnonzero(np.diff(community[order])) + 1]
    rank_in_group = np.arange(len(order)) - np.repeat(first, np.diff(np.r_[first, len(order)]))
    top_per_group = np.zeros(len(xy), dtype=bool)
    top_per_group[order[rank_in_group < 40]] = True
    sizes = np.bincount(np.unique(community, return_inverse=True)[1])[np.unique(community, return_inverse=True)[1]]
    eligible = sizes >= min_cluster
    if region is not None:
        eligible &= np.asarray(region, dtype=bool)
    salient = np.flatnonzero(((subscribers >= np.quantile(subscribers, salient_quantile)) | top_per_group) & eligible)
    close = cKDTree(xy[salient]).query_pairs(radius, output_type='ndarray')
    if len(close):
        a, b = salient[close[:, 0]], salient[close[:, 1]]
        accumulate(a, b, radius_weight * (1 - np.linalg.norm(xy[a] - xy[b], axis=1) / radius))
    lo = np.concatenate([x[0] for x in parts]); hi = np.concatenate([x[1] for x in parts]); w = np.concatenate([x[2] for x in parts])
    keys, inverse = np.unique(np.stack([lo, hi], axis=1), axis=0, return_inverse=True)
    totals = np.bincount(inverse.ravel(), w)
    neighbours = {}
    for (u, v), weight in zip(keys.tolist(), totals.tolist()):
        neighbours.setdefault(u, {})[v] = weight
        neighbours.setdefault(v, {})[u] = weight
    return neighbours


def assign_colors(xy, community, subscribers, palette, k=6, passes=6, region=None, extra_pairs=None):
    """Return (per-node palette index, per-community index dict, adjacency).

    `extra_pairs` maps (community, community) to an additional preference weight,
    e.g. so the most prominent named communities prefer mutually distinct colours
    even when they are not spatial neighbours."""
    community = np.asarray(community)
    similarity, _ = palette_similarity(palette)
    neighbours = community_adjacency(xy, community, subscribers, k, region=region)
    for (u, v), w in (extra_pairs or {}).items():
        neighbours.setdefault(u, {})[v] = neighbours.get(u, {}).get(v, 0.0) + w
        neighbours.setdefault(v, {})[u] = neighbours.get(v, {}).get(u, 0.0) + w
    ids, inverse = np.unique(community, return_inverse=True)
    position = {c: i for i, c in enumerate(ids.tolist())}
    # Compressed adjacency rows in community-index space.
    rows, cols, vals = [], [], []
    for c, nb in neighbours.items():
        for d, w in nb.items():
            rows.append(position[c]); cols.append(position[d]); vals.append(w)
    rows, cols, vals = np.array(rows, dtype=np.int64), np.array(cols, dtype=np.int64), np.array(vals)
    order_rows = np.argsort(rows, kind='stable')
    rows, cols, vals = rows[order_rows], cols[order_rows], vals[order_rows]
    indptr = np.searchsorted(rows, np.arange(len(ids) + 1))
    salience = np.bincount(inverse, np.sqrt(np.maximum(subscribers, 0)) + 1)
    order = np.lexsort((ids, -salience))
    colour = np.full(len(ids), -1, dtype=np.int64)
    usage = np.zeros(len(palette))
    tie = np.arange(len(palette))

    def cost_of(i, only_coloured):
        nb, w = cols[indptr[i]:indptr[i + 1]], vals[indptr[i]:indptr[i + 1]]
        c = colour[nb]
        if only_coloured:
            keep = c >= 0
            nb, w, c = nb[keep], w[keep], c[keep]
        return w @ similarity[c] if len(c) else np.zeros(len(palette))

    for i in order.tolist():
        cost = cost_of(i, True) + 1e-6 * usage  # usage spreads unconstrained groups
        best = int(np.lexsort((tie, cost))[0])
        colour[i] = best
        usage[best] += 1
    # Deterministic local refinement against all neighbours (not only earlier ones).
    for _ in range(passes):
        changed = 0
        for i in order.tolist():
            cost = cost_of(i, False)
            best = int(np.lexsort((tie, cost))[0])
            if cost[best] < cost[colour[i]] - 1e-12:
                colour[i] = best
                changed += 1
        if not changed:
            break
    chosen = {c: int(colour[i]) for c, i in position.items()}
    return colour[inverse].astype(np.uint8), chosen, neighbours


def adjacency_similarity(chosen, neighbours, palette, focus=None):
    """Weighted mean palette similarity between adjacent communities (lower is better)."""
    similarity, delta = palette_similarity(palette)
    total = weighted = 0.0
    worst = []
    for c, nb in neighbours.items():
        if focus is not None and c not in focus:
            continue
        for d, w in nb.items():
            total += w
            weighted += w * similarity[chosen[c], chosen[d]]
        if nb:
            strongest = max(nb, key=nb.get)
            worst.append(float(delta[chosen[c], chosen[strongest]]))
    return {'weighted_mean_similarity': weighted / total if total else 0.0,
            'strongest_neighbour_delta_e_min': min(worst) if worst else None,
            'strongest_neighbour_same_colour': int(sum(x == 0 for x in worst))}
