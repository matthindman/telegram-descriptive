# Node overlap in large subscriber-weighted networks

[PRISM, Gansner and Hu](https://yifanhu.net/PUB/overlap.pdf) treats overlap removal as a tradeoff between proximity preservation and drawing area. Uniform enlargement preserves shape but can produce an impractically large map. Its stress approach uses a proximity scaffold and needs an all-overlaps check beyond Delaunay neighbors.

[GTree, Nachmanson et al.](https://arxiv.org/abs/1608.02653) is a faster tree-growth alternative; its published comparison also shows an area tradeoff. For this atlas the implementation adapts the overlap geometry to circles, caps each growth factor at 1.5, and checks all remaining collisions with a separate spatial index. This is a local implementation, not the authors’ reference code.

[Graphviz overlap documentation](https://graphviz.org/docs/attrs/overlap/) describes several available strategies. Plain repulsion, jitter and opacity changes do not establish that collisions are eliminated. Aggregation or semantic zoom can help navigation, but should not silently replace an individual-channel task with cluster bubbles.

Implementation measurements for the September 30 v3 Telegram atlas are under outputs/crawled_channel_graph_v3_2026-09-30/layout/overlap_removal.json and revision/overlap_verification.json. The unchanged graph has 72,326 entities and 820,041 ties. Display positions account for subscriber-sized circles; clustering remains graph-only. Record the substantial distortion instead of calling this a distance-preserving transformation.

A subscriber threshold operates on stored counts and both endpoints of every displayed edge. Use logarithmic slider travel plus exact numeric entry and explicitly labelled presets. Keep full-reference weights and coreness fixed. Test CPU counts against GPU rendering, reset, empty/singleton selections, search behavior and saved views.
