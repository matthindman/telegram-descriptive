# Research and design decisions

Reviewed 2026-09-30. These sources support methodological choices; the particular
parameters and their transfer to a Telegram hyperlink graph are design decisions.
There is no single empirically best recipe for every large graph.

## Scale, navigation, and rendering

[Shneiderman, 1996, The Eyes Have It](https://www.cs.umd.edu/users/ben/papers/Shneiderman1996eyes.pdf)
organizes visual exploration around overview, zoom/filter and details on demand.
For a channel graph this motivates a complete overview, search, local-neighborhood
inspection and reversible filters. An overview cannot carry all individual labels.

[Sigma renderers](https://www.sigmajs.org/docs/advanced/renderers/) and
[layers](https://www.sigmajs.org/docs/advanced/layers/) document a practical WebGL
architecture with edges underneath nodes and a separate label/hover layer. They
also distinguish hardware line primitives from triangle-based thick edges.
Adopt that architecture without assuming a particular library is mandatory.
A standalone local renderer can be appropriate when exact circle sizing and
offline reproducibility matter. Measure it on the actual target graph.

[Jacomy et al., 2014, ForceAtlas2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4051631/)
describes continuous force-directed graph exploration, LinLog attraction and
hub-related settings. Its published performance scope is not a guarantee for
larger current datasets. Hub dissuasion in a force algorithm is also not a
substitute for an explicit analytical link-weight definition. Precompute the
layout for a large static dataset, and save the coordinates rather than making
the user's browser recompute them each time.

[Fruchterman and Reingold, 1991](https://doi.org/10.1002/spe.4380211102)
provides the force-placement basis. Accelerated grid/Barnes–Hut/multilevel methods
trade exactness for tractability. A weighted community quotient followed by
node-level force refinement is a defensible engineering choice. Record the
coarse initialization and final refinement so artificial packing is not mistaken
for a measured graph distance. Disconnected-component packing is presentational.

## Normalization

[Perianes-Rodriguez, Waltman and van Eck, 2016](https://arxiv.org/abs/1607.02452)
compares full and fractional counting in bibliometric networks. Its key idea is
equal total contribution per action, divided across the links it creates. That
principle motivates allocating a channel a fixed total outgoing budget when
visualizing selective connections. Applying it to distinct Telegram destinations
is an adaptation, not the paper's tested dataset or a universal optimal formula.

At alpha=1, a source with 10 distinct valid targets contributes 0.1 per direction;
a source with 100,000 contributes 0.00001. Reciprocal contributions add. Sources
without observed outgoing links contribute no outgoing weight. Calculate the
denominator before an induced-cohort restriction, and retain the full degree.
A repeated extraction on multiple crawl visits does not establish repeated posts.

Do not confuse source fractional weights with Adamic–Adar/resource allocation,
which commonly weight shared neighbors in similarity or link-prediction tasks.
Using a shared-neighbor index for direct hyperlink evidence changes the question.

## Clustering and k-core

[Traag, Waltman and van Eck, 2019](https://doi.org/10.1038/s41598-019-41695-z)
introduces Leiden and its connectivity improvements over Louvain. Its guarantees
do not imply that a partition matches substantive social categories, or remove
the need to inspect resolution and stochastic sensitivity. Keep community IDs
stable for style iterations and report seed comparisons on non-isolated nodes.

Coreness is a different structural summary from community membership. It supports
progressively revealing a densely connected interior; peripheral channels are
not necessarily unimportant, particularly when subscriber count is independent
of degree. A k-core uses recursive pruning. Computing total degree >= k is not
an equivalent implementation.

## Visual decisions for dense channel maps

The user's requested diameter sqrt(N) makes circle area proportional to N.
Do not log subscribers a second time. Tiny positive values may be subpixel at
overview; zoom, search, a global size control and an optional explicit visibility
marker are more honest remedies than hidden minimum sizes. A zero/unknown marker
should be distinguishable from a quantitatively sized disc.

Use edge opacity as the primary relative strength cue, with a restrained width
range. This is a design choice for a dense overview, not an experimentally proven
optimal encoding for this dataset. Give a legend, explain any logarithmic mapping,
and expose exact weights on selection. Overlapping ties can encode density as well as individual strength, but accumulation must be verified in the actual framebuffer; 8-bit rounding can erase weak contributions or prevent accumulation.
Retain every edge in the data; distinguish any display sparsification or threshold.

Large numbers of clusters exceed reliable categorical color discrimination.
Use a limited palette, ID/details lookup, and alternatives such as coreness,
subscriber level or monochrome. Palette reuse must not imply merged clusters.
Save positions when changing style to preserve spatial orientation.

## Rendering correction after the September 30 independent audit

Use [Khronos EXT_color_buffer_float](https://registry.khronos.org/webgl/extensions/EXT_color_buffer_float/) for float render targets and [EXT_float_blend](https://registry.khronos.org/webgl/extensions/EXT_float_blend/) for blending into 32-bit float buffers. Check extension availability and framebuffer completeness; do not silently use a visually incorrect 8-bit fallback. An additive density pass followed by alpha = cap × (1 − exp(−density)) preserves weak contributions until final tone mapping. This specific transfer function is an engineering choice, not a claim from the specification.

For node size, an exact circle–pixel intersection or an area-preserving subpixel kernel avoids inward-only antialiasing bias. Final 8-bit display rounding remains; quantify it. White-on-black shader tests isolate coverage, while production-color tests assess actual contrast. Tests must vary subpixel phase and DPR.

Community packing is not a graph metric. Compare final center-distance/weight association with the raw force result; also examine local edge distances versus random pairs and sensitivity to initialization. A favorable correlation is a diagnostic, not proof of faithful pairwise graph distances.
