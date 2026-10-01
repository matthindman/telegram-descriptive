"""Render the undirected quotient graph and an exact binned adjacency matrix.

Scientific artifacts are PNG/PDF figures and a local interactive atlas. No
graph sampling or validation filtering is used during layout or rendering.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import colors
from matplotlib.collections import LineCollection
from matplotlib.ticker import MaxNLocator, FuncFormatter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BACKGROUND = "#f7f6f2"
INK = "#173042"
TEAL = "#087f8c"
ORANGE = "#bf5825"
MUTED = "#64717b"


def no_frame(ax):
    ax.set_aspect("equal")
    ax.set_axis_off()


def community_panel(ax, communities, links, centers, giant_communities, label=True):
    chosen = communities.set_index("community").loc[giant_communities]
    segments = centers[links[["source_community", "target_community"]].to_numpy()]
    widths = 0.22 + 2.1 * np.log1p(links.undirected_links) / np.log1p(links.undirected_links.max())
    ax.add_collection(LineCollection(segments, linewidths=widths, colors="#65838d", alpha=0.4))
    ax.scatter(centers[giant_communities, 0], centers[giant_communities, 1],
               s=np.maximum(1.2, chosen.nodes.to_numpy() * 4500 / chosen.nodes.max()),
               color=TEAL, edgecolors=BACKGROUND, linewidths=0.5, alpha=0.8, zorder=3)
    largest = chosen.nlargest(8, "nodes")
    if label:
        for rank, (cid, _) in enumerate(largest.iterrows(), 1):
            x, y = centers[cid]
            offsets = {3: (4, 18), 4: (6, -15), 5: (20, -18), 6: (16, 9), 7: (-18, -12)}
            ax.annotate(str(rank), (x, y), xytext=offsets.get(rank, (5, 5)), textcoords="offset points",
                        arrowprops={"arrowstyle": "-", "lw": .5, "color": MUTED},
                        fontsize=10, weight="bold", color=INK, zorder=5,
                        bbox={"facecolor": BACKGROUND, "edgecolor": "none", "alpha": .85,
                              "boxstyle": "round,pad=0.12"})
    ax.autoscale()
    ax.margins(.12)
    no_frame(ax)
    return largest


def component_atlas(ax, all_xy, component, source, target, giant):
    sizes = np.bincount(component)
    ids = np.flatnonzero(np.arange(len(sizes)) != giant)
    ids = ids[np.argsort(-sizes[ids], kind="stable")]
    # Shelf-pack component boxes with area proportional to component size.
    radii = np.sqrt(sizes[ids])
    width = np.sqrt(np.sum((radii + 1.5) ** 2) * 1.35)
    offset = np.zeros((len(sizes), 2))
    scales = np.zeros(len(sizes))
    x = y = row_height = 0.0
    for comp, radius in zip(ids, radii):
        cell = radius + 1.5
        if x + cell > width and x > 0:
            y += row_height
            x = row_height = 0.0
        offset[comp] = [x + cell / 2, y + cell / 2]
        scales[comp] = radius * .84
        x += cell
        row_height = max(row_height, cell)
    small = component != giant
    packed = all_xy * scales[component, None] + offset[component]
    mask = small[source]
    ax.add_collection(LineCollection(packed[np.column_stack((source[mask], target[mask]))],
                                    linewidths=.35, colors="#54727f", alpha=.6))
    ax.scatter(packed[small, 0], packed[small, 1], s=1.3, c=TEAL, linewidths=0)
    ax.autoscale()
    ax.invert_yaxis()
    ax.margins(.02)
    no_frame(ax)
    return {"nodes": int(small.sum()), "edges": int(mask.sum()), "components": len(ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    out = args.root / 'visualization'
    summary = json.loads((out / 'layout_summary.json').read_text())
    inputs = np.load(out / 'layout_inputs.npz')
    source, target = inputs['source'], inputs['target']
    component, membership, degree = inputs['component'], inputs['membership'], inputs['degree']
    giant = summary['largest_component']
    gmask = component == giant
    communities = pd.read_parquet(out / 'communities.parquet')
    links = pd.read_parquet(out / 'community_edges.parquet')
    centers = np.load(out / 'community_layout.npy')
    gc = np.unique(membership[gmask])
    # Display-only rigid rotation: use the landscape panel efficiently while
    # preserving every relative distance in the saved force layout.
    centered = centers[gc] - centers[gc].mean(axis=0)
    _, _, rotation = np.linalg.svd(centered, full_matrices=False)
    centers[gc] = centered @ rotation.T
    largest_ids = communities.set_index('community').loc[gc].nodes.nlargest(2).index
    if centers[largest_ids[0], 0] < centers[largest_ids[1], 0]:
        centers[gc, 0] *= -1
    np.save(out / 'display_community_layout.npy', centers)
    giant_links = links[links.source_community.isin(gc) & links.target_community.isin(gc)]
    node_count = summary['nodes']
    edge_count = summary['undirected_edges']
    giant_percent = 100 * int(gmask.sum()) / node_count
    leaf_percent = 100 * summary['degree_one_nodes'] / node_count
    small_count = summary['components'] - 1
    small_edges = int((~gmask[source]).sum())
    isolates = summary.get('isolates', int((degree == 0).sum()))
    filter_note = (summary['validation_filter']['display_note'] if summary.get('validation_filter')
                   else 'All validation states retained')
    small_positions = pd.read_parquet(out / 'small_component_positions.parquet')
    coords = np.zeros((len(component), 2))
    coords[small_positions.node_id] = small_positions[['x', 'y']].to_numpy()
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
        'figure.facecolor': BACKGROUND, 'axes.facecolor': BACKGROUND,
        'text.color': INK, 'axes.labelcolor': INK, 'savefig.facecolor': BACKGROUND,
        'pdf.fonttype': 42})
    fig = plt.figure(figsize=(16, 11))
    fig.text(.045, .952, 'Telegram’s undirected link graph', fontsize=26, weight='bold')
    fig.text(.045, .916, f'{node_count:,} handles  ·  {edge_count:,} unique links  ·  aggregated overview',
             fontsize=13, color=MUTED)
    ax = fig.add_axes([.025, .18, .67, .69])
    largest = community_panel(ax, communities, giant_links, centers, gc)
    ax.set_title(f'Main component: {len(gc):,} communities · {giant_percent:.2f}% of all nodes',
                 fontsize=13, loc='left', pad=15)
    fig.text(.725, .855, 'Largest communities', fontsize=14, weight='bold')
    fig.text(.725, .83, 'Example hub · number of handles', fontsize=10, color=MUTED)
    for rank, (_, row) in enumerate(largest.iterrows(), 1):
        y = .790 - (rank-1)*.044
        fig.text(.725, y, f"{rank}  {row['highest_degree_handle']}", fontsize=11, weight='bold')
        fig.text(.745, y-.019, f"{row['nodes']:,}", fontsize=10, color=MUTED)
    fig.text(.725, .405, f'{small_count:,} smaller components', fontsize=13, weight='bold')
    fig.text(.725, .38, f"{summary['smaller_component_nodes']:,} nodes · {small_edges:,} links", fontsize=10, color=MUTED)
    small_ax = fig.add_axes([.72, .166, .23, .195])
    small_stats = component_atlas(small_ax, coords, component, source, target, giant)
    small_caption = (f'Includes {isolates:,} isolates; packed separately.' if isolates else
                     'Individual nodes and links; packed separately.')
    fig.text(.725, .14, small_caption, fontsize=9, color=MUTED)
    fig.text(.045, .125, 'Circle area follows community size; tiny groups have a minimum dot. '
             'Line width follows log(1 + links between groups).', fontsize=10.5)
    fig.text(.045, .091, 'Within-community links are counted inside groups. '
             f"{leaf_percent:.1f}% of handles have one neighbor; the largest hub has {summary['max_degree']:,}.", fontsize=10.5)
    fig.text(.045, .057, 'Groups are exploratory, not established topics. '
             f'Placement is not geographic. {filter_note}.', fontsize=10, color=MUTED)
    fig.savefig(out/'undirected_graph.png', dpi=220)
    fig.savefig(out/'undirected_graph.pdf', dpi=220)
    plt.close(fig)

    # Exact binned adjacency: each original edge enters once in each triangle.
    # No point sampling or percentile clipping. Store the rank-to-node mapping.
    n = len(component)
    corder = communities.sort_values(['nodes','community'], ascending=[False,True]).community.to_numpy()
    crank = np.empty(len(communities), dtype=int)
    crank[corder] = np.arange(len(corder))
    order = np.lexsort((np.arange(n), -degree.astype(np.int64), crank[membership]))
    rank = np.empty(n, dtype=np.int64)
    rank[order] = np.arange(n)
    bins = 2400
    r = rank[source]*bins//n
    c = rank[target]*bins//n
    density = np.bincount(r*bins+c, minlength=bins*bins).reshape(bins,bins)
    density += density.T.copy()
    assert int(density.sum()) == 2*len(source)
    np.savez_compressed(out/'adjacency_density.npz', counts=density, rank_to_node_id=order)
    pd.DataFrame({'matrix_rank':np.arange(n),'node_id':order,
                  'community':membership[order]}).to_parquet(out/'matrix_node_order.parquet',index=False)
    cmap = colors.LinearSegmentedColormap.from_list('links', ['#83b8bb','#347b89','#16394c'])
    cmap.set_bad(BACKGROUND)
    fig = plt.figure(figsize=(13,11))
    fig.text(.055,.95,'Every link, without a force layout',fontsize=25,weight='bold')
    fig.text(.055,.914,f'Adjacency density · {node_count:,} nodes and {edge_count:,} undirected links',
             fontsize=12,color=MUTED)
    ax=fig.add_axes([.10,.16,.68,.69])
    im=ax.imshow(np.ma.masked_equal(density,0),origin='upper',interpolation='nearest',
                extent=(0,n,n,0),cmap=cmap,norm=colors.LogNorm(vmin=1,vmax=int(density.max())))
    ax.set_xlim(-n*.01,n*1.01)
    ax.set_ylim(n*1.01,-n*.01)
    ax.set_xlabel('Node order: communities by size, then degree within each group',fontsize=10,labelpad=12)
    ax.set_ylabel('The same node order',fontsize=11)
    ticks=MaxNLocator(nbins=5).tick_values(0,n)
    ticks=ticks[(ticks>=0)&(ticks<=n)]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    formatter=FuncFormatter(lambda value,_: f'{value/1e6:g}m' if value>=1e6 else
                            (f'{value/1000:g}k' if value>=1000 else f'{value:g}'))
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)
    for spine in ax.spines.values(): spine.set_color('#c5cfce')
    cax=fig.add_axes([.83,.52,.02,.27])
    cb=fig.colorbar(im,cax=cax)
    cb.set_label('Adjacency entries per pixel · log scale',fontsize=10,labelpad=10)
    fig.text(.815,.43,'HOW TO READ',fontsize=10,weight='bold')
    fig.text(.815,.395,'Darker pixels contain\nmore links.\n\nBoth triangles are shown:\neach undirected edge\nappears twice.\n\nOne pixel spans about\n'
             f'{n/bins:.0f} × {n/bins:.0f} possible\nnode pairs.',fontsize=10,color=MUTED,linespacing=1.5,va='top')
    fig.text(.055,.077,f'All {2*edge_count:,} symmetric adjacency entries reconcile exactly. '
             'Empty areas contain no observed links at this resolution.',fontsize=10.5)
    fig.text(.055,.044,'Ordering changes the picture, not the graph. '
             'This is a count of links, not a normalized density or a probability.',fontsize=10,color=MUTED)
    fig.savefig(out/'undirected_adjacency.png',dpi=220)
    fig.savefig(out/'undirected_adjacency.pdf',dpi=220)
    plt.close(fig)

    indexed = communities.set_index('community')
    ranks = {int(cid):r for r,cid in enumerate(indexed.loc[gc].nodes.nlargest(8).index,1)}
    payload={'nodes':[{'id':int(cid),'x':float(centers[cid,0]),'y':float(-centers[cid,1]),
        'nodes':int(indexed.loc[cid,'nodes']),'internal':int(indexed.loc[cid,'internal_links']),
        'handle':str(indexed.loc[cid,'highest_degree_handle']),
        'degree':int(indexed.loc[cid,'highest_degree']),'rank':ranks.get(int(cid),0)} for cid in gc],
        'edges':giant_links[['source_community','target_community','undirected_links']].to_numpy().tolist(),
        'maxEdge':int(giant_links.undirected_links.max())}
    template=Path(__file__).with_name('undirected_atlas_template.html').read_text()
    template=template.replace('__ATLAS_DATA__',json.dumps(payload).replace('</','<\\/'))
    for key,value in {'__NODE_COUNT__':f'{node_count:,}', '__LINK_COUNT__':f'{edge_count:,}',
                      '__GIANT_PERCENT__':f'{giant_percent:.2f}%',
                      '__LEAF_PERCENT__':f'{leaf_percent:.1f}%',
                      '__SMALL_COMPONENTS__':f'{small_count:,}',
                      '__GIANT_COMMUNITIES__':f'{len(gc):,}',
                      '__FILTER_NOTE__':filter_note}.items():
        template=template.replace(key,value)
    for key,name in [('__IMAGE_DATA__','undirected_graph.png'),('__MATRIX_DATA__','undirected_adjacency.png')]:
        template=template.replace(key,base64.b64encode((out/name).read_bytes()).decode('ascii'))
    (out/'undirected_atlas.html').write_text(template)
    verification={'main_component_communities':len(gc),'between_community_connections':len(giant_links),
        'between_community_original_edges':int(links.undirected_links.sum()),
        'within_community_original_edges':int(communities.internal_links.sum()),
        'nodes_in_main_group_counts':int(indexed.loc[gc,'nodes'].sum()),
        'small_components':small_stats,'all_nodes_accounted_for':int(communities.nodes.sum()),
        'all_edges_accounted_for':int(communities.internal_links.sum()+links.undirected_links.sum()),
        'matrix_entries':int(density.sum()),'matrix_bins_per_axis':bins,
        'matrix_order_is_permutation':bool(np.array_equal(np.sort(order),np.arange(n))),
        'full_individual_force_layout':False}
    assert verification['all_edges_accounted_for']==summary['undirected_edges']
    assert verification['all_nodes_accounted_for']==summary['nodes']
    assert verification['nodes_in_main_group_counts']+small_stats['nodes']==n
    (out/'render_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(verification),flush=True)


if __name__=='__main__':
    main()
