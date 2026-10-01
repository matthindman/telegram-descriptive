---
name: large-network-visualization
description: Research and build reproducible interactive visualizations of large, heterogeneous networks, with explicit cohort definitions, hub discounting, graph-derived layouts, and scalable rendering. Use for networks with tens of thousands of nodes or more, or dense smaller graphs where aggregation and visual clutter affect interpretation.
---

# Large network visualization

Build a faithful, inspectable view of observed relationships. The graph is an
analytical object; layout, styling, and display filters are separate derivatives.
Read [research and decision notes](references/research.md) when choosing methods,
and [Telegram context](references/telegram.md) only for that dataset.

## Establish the graph before drawing it

- Resolve the node cohort independently of the edge table. Preserve eligible
  isolates and distinguish discovered, validated, visited, and fully scanned.
  Reconcile approximate requested counts with measured counts; never pad a cohort.
- Record directedness, self-link policy, duplicate handling, evidence unit,
  observation window, endpoint eligibility, and frozen inputs. A visit count is
  not a post-level mention count. Missing observed edges do not prove no ties.
- Resolve identities before graph construction when stable entity IDs exist: merge aliases, remove entity self-links, and deduplicate both edges and denominator destinations. Preserve alias observations and count conflicts; do not sum subscriber counts across aliases. A snapshot ID does not resolve historical handle reassignment.
- Keep raw directed relationships. For an undirected view specify the union and
  symmetrization formula; preserve whether each pair is reciprocal.
- Report eligible but unobserved nodes and components. If handles can be renamed
  or reassigned, flag the absence of stable entity IDs and time-resolved identity.

## Discount hubs explicitly

There is no universal best discount. Select a model suited to the question and
save its parameters. For an attention-like view of a directed hyperlink graph,
a useful default is source fractional weighting:

  q(u,v) = A(u,v) / d_out(u)^alpha, with alpha = 1
  w({u,v}) = q(u,v) + q(v,u)

Here A indicates a distinct observed directed relationship. Compute d_out on
the declared full eligible reference graph BEFORE restricting to the displayed
cohort. Otherwise an induced subgraph can inflate contributions from sources
whose other links lie outside the view. Under alpha=1 a source contributes at
most one unit to any induced subgraph. Preserve alpha=0 (binary contribution)
and alpha=0.5 as possible sensitivity choices; neither is automatically better.

Eligibility affects normalization: invalid or non-channel destinations may still represent real outgoing attention. Preserve an all-observed-target denominator sensitivity when this distinction matters; report local inflation as well as global correlation.

Do not invent posting frequency from repeated crawl encounters. If trustworthy
post-level counts become available, document the action/time unit before using
them. Distinguish the analytical weight from logarithmic or other display
transforms. If a layout uses weights, confirm its algorithm actually consumes
those weights rather than merely storing an unused edge attribute.

## Layout and community structure

- For ~10^5 nodes and ~10^6 edges, prefer WebGL rendering and precomputed positions;
  avoid thousands of DOM/SVG objects and an uncontrolled browser force simulation.
- Use graph-based multilevel or accelerated force placement. A community quotient
  can seed a node-level layout, but do not pass off random within-cluster jitter
  as channel-level placement. Keep isolated nodes in an explicitly labeled shelf
  or separate view: their screen distances have no graph meaning.
- Weighted Leiden is a reasonable community default. Record objective,
  resolution, iterations, seeds, library versions and partition stability.
  Compare more than one seed and, when decisions depend on it, resolutions.
  A community is structural, not automatically a language, ideology, or topic.
- Measure the final displayed geometry, not just intermediate force coordinates. Repacking can erase cross-community relationships. Report a before/after fidelity diagnostic and imposed local scale/shape. Normalize local force weights where absolute scale overwhelms attraction, and avoid handle-ordered starting positions.
- Give each stochastic stage its own seed; validate clean versus cached runs, fingerprint cache inputs/code/parameters, and reject stale layouts.
- Keep reference positions fixed during color/style/core-filter changes. Save
  node IDs and positions so subsequent refinements preserve the viewer's mental
  map. For a changed graph, initialize from previous positions where appropriate.
- Save unweighted coreness separately from weights. A k-core filter means the
  maximal induced subgraph with minimum internal degree k, not total-degree
  thresholding. Verify maximality by independent peeling, not only minimum degree. State whether coreness is recomputed after other filters. Disclose blocks dominating edge/core totals, provide exclusion sensitivity, and use attained-value or log controls when core values are highly skewed.

## Size-aware overlap removal

If subscriber-sized circles occlude each other, consult [overlap notes](references/overlap.md). Treat this as a separate display-layout operation; retain source coordinates and analytical communities/weights. Measure actual circle collisions and geometric distortion. Removing overlap can change distances materially, so do not preserve earlier fidelity claims after postprocessing. The goal is inspectable nodes, not a zero-overlap number achieved only by making every node microscopic.

Verify the packed geometry after serialization and at different viewport sizes, zoom levels and node-size settings. A fit-to-window step can reintroduce collisions when glyphs use screen-space sizes. A disclosed common scaling guard preserves quantitative size ratios; individual per-node caps do not. Subscriber filters should remove incident edges at both endpoints, preserve positions, have usable skew-aware controls plus exact input, and survive save/load.

## Visual encoding

For semantic community names, read [community labeling notes](references/community-labels.md). Freeze partition-specific samples before reading content, separate influential members from random members, and retain evidence, missingness, disagreements and uncertainty. Structural membership is not a topic label. Reviewers' model agreement is not human validation.

- Honor the requested quantitative mapping exactly. If diameter is proportional
  to sqrt(subscribers), disc area is proportional to subscribers. Use a global
  multiplier and a size legend. Do not silently log, clip, cap, or floor positive
  node sizes. Unknown and zero values require explicit non-area markers or a
  stated separate treatment; they must not masquerade as positive counts.
- Check pixel coverage, not just the diameter formula: inward-only antialiasing shrinks circles and subpixel quads can miss samples. Integrate circle/pixel coverage or use area-preserving fractional marks. Measure averaged rendered ink across pixel phases, relevant sizes, actual colors, and device pixel ratios; disclose remaining display quantization and overlap. Zero/unknown markers should not dominate small positive nodes; hiding them behind an explicit toggle is one option.
- Draw edge layers first, then filled nodes, then selected-node details/labels.
  Prefer subdued neutral edges and stronger node color. For dense overview ties,
  use bounded opacity as the main strength cue and modest width as redundancy.
  State any log compression and show reference weights. Very low alpha in an 8-bit framebuffer can vanish or plateau instead of accumulating. Use a tested floating-point density/composite pass or a measured visibility floor; generate legend swatches through the actual renderer. Overlap density does not support precise per-edge comparisons.
- Check where tie ink actually goes before tuning tone curves. A per-edge
  brightness floor plus long lines makes ink follow LINE LENGTH, not weight:
  long weak ties paint a uniform wash while short strong ties vanish under
  nodes. Make each tie's total ink proportional to its weight (density ∝
  weight / layout length, zoom-invariant, no floor), use a fixed log exposure
  calibrated once per viewport (never re-normalized on pan/zoom), and measure
  near-ceiling share, ink-vs-weight agreement, and buffer integrals against an
  independent sum. Check whether strong long ties even exist before trading
  them off.
- Show long-range and group-to-group structure on demand rather than as an
  overview hairball: a separate highlight channel (own calibration, distinct
  colour, partial length compensation; keep its ceiling modest, about 0.5 or less,
  so nodes stay dominant) for a selected channel/community/pair,
  plus a ranked partner panel (raw weight, share, direction, and an affinity
  measured against between-group weight with minimum group size). State that
  per-selection brightness calibration is relative within that selection.
- Show exact weights in local details. Allow edge visibility/contrast controls,
  neighborhood emphasis, and search. Avoid arrowhead clutter in an undirected
  overview; direction can remain in the inspected relationship details.
- Dense labels need temporal stability as well as collision handling. Fix world
  geometric anchors, attach the nearest text edge with a screen-pixel gap (not
  an offset world-space text center), rank by a declared full-community measure,
  and reveal more short names
  at predetermined zoom levels. Do not re-anchor or re-rank from visible members
  during navigation. Use a persistent ranked list, keep selection distinct from
  camera movement, and put detailed reports on demand. Test actual pan/zoom
  transforms and monotonic activation, not only still-frame collisions. See the
  navigation section of the community labeling notes. Avoid an enormous
  categorical legend or suggesting every reused color is unique.
- A community name must visibly belong to its own marks. Anchor it to a real,
  displayed member glyph (gap measured from the rendered circle edge), and
  score candidates over their whole zoom range for OTHER communities' marks
  under or near the text; a hull line or port is not evidence of association.
  Prefer delaying or omitting a name to drawing it on another community.
  Test association against the renderer's node sizes, not the planner's own
  gap formula. Assign categorical colors so spatial neighbors differ. Plan names
  from persistent filters only (never temporary selection/focus), and make an
  explicit Locate reach the browser viewport on stacked layouts. Follow the
  "Current rule" section of the community labeling notes; later dated sections
  there are history.
- Color modes and core thresholds should be presentation controls, not silent
  reconstruction of the underlying graph. Include a readable alternative to
  color alone and clarify when filtering hides nodes or edges.

## Iteration and delivery

Separate frozen exports, graph construction, weights, partitions/core values,
positions, visual configuration, and renderer. Use portable relative references, validate saved-view fields atomically, and save camera zoom relative to a defined reference viewport. Keep editable style parameters separate from derived descriptions; reject unsupported keys. Persist a parameter manifest and
reproduction commands. Save views without altering analytical inputs. Prefer
self-contained or locally bundled artifacts when remote assets would make the
result fragile. Include a shareable static preview alongside the interactive
artifact when useful; it cannot replace access to individual nodes.

Verify invariants against source totals: unique nodes/pairs, no unwanted loops,
cohort completeness, nonnegative finite weights, source-budget normalization,
finite node coordinates, node/subscriber mapping, and expected symmetry. Check
coreness against the induced minimum degree for selected k values. Measure
layout sensitivity instead of choosing only the most attractive seed.

Exercise the rendered artifact in a real browser: initial GPU draw, search,
selection, pan/zoom, measured pixel-area ratios, weak-edge traces and accumulation, color changes, edge controls, core filters,
reset/export, and narrow-screen layout. Inspect screenshots; a successful build
is not evidence of a legible or functioning graph. Report measured scale and
limitations rather than extrapolated performance claims.
