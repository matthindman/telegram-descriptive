# Describing structural communities

Community structure and metadata need not coincide. Label the observed pattern
with a short description that can express language, subject, region explicitly
named by the channels, or linking function. A directory, marketplace, or link
exchange may connect very different topics. Preserve mixed and unresolved groups.

Before reviewing content, freeze the partition, IDs, membership hashes, target
community selection and sample seed. A useful interpretive sample combines the
largest members by the relevant audience measure with a disjoint uniform random
sample of the rest. Analyze these two strata separately: the largest nodes show
prominence, while the random remainder shows breadth. Do not pool their counts
as a prevalence estimate. For small communities use a census; never replace
inaccessible sampled members simply to obtain more convenient evidence.

Save timestamped source evidence and provide per-member annotations before the
community summary. A title or handle alone is usually insufficient. Preserve
source URLs, missingness, contrary examples and minorities. System events such
as “Channel created” are not substantive posts. Current previews do not verify
historical identity or the original crawl window; media-only content remains
uninterpreted unless actually inspected.

Use a common review schema across agents: language, subject/function, evidence
paraphrase, usability, fit to the proposed label, and qualitative uncertainty.
Separate top/random evidence denominators. A lead reviewer should reconcile
labels and check surprising or weakly supported interpretations against sources.
Do not call this human validation or report calibrated accuracy without a human
reference set. Model confidence and model agreement can both be wrong.

Store short label, longer account, confidence, coverage, counterexamples and
provenance as a versioned sidecar. Attach labels to the exact partition; do not
transfer them to another resolution or normalization by numeric community ID.
Allow inspection and revisions. On maps, use collision-aware labels and a
searchable community list; do not force every name into an overview or imply a
community's geometric envelope is a substantive boundary.

Sources consulted 2026-09-30:

- Peel, Larremore & Clauset (2017), [The ground truth about metadata and community detection](https://www.cs.cornell.edu/courses/cs6241/2019sp/readings/Peel-2017-truth.pdf): structural groups need not match metadata.
- Fortunato & Hric (2016), [Community detection in networks: A user guide](https://www.cs.cornell.edu/courses/cs6241/2020sp/readings/Fortunato-2016-guide.pdf): community definitions, validation and sensitivity.
- Törnberg (2024), [Best Practices for Text Annotation with Large Language Models](https://arxiv.org/abs/2402.05129): structured prompting, reproducibility and validation.
- Pangakis, Wolken & Fasching (2023), [Automated Annotation with Generative AI Requires Validation](https://arxiv.org/abs/2306.00176): task-dependent performance and need for human reference annotations.
- Microsoft [GraphRAG output schema](https://microsoft.github.io/graphrag/index/outputs/): a useful example of linked community IDs, evidence and reports; not validation of hyperlink-community semantics.

## Current rule for map names (2026-10-01)

This section is the rule to follow. Dated sections below are historical: they
record earlier approaches and why they failed, and are superseded wherever they
conflict with this one.

1. **Belong to own marks.** Attach each name's near text edge a fixed CSS-pixel
   gap beyond one real, displayed member's RENDERED circle. Prefer members on the
   community's outer edge (hull vertices, left/right extremes of label-height
   bands) — a preference, not a guarantee; an anchor can lie inside the full
   hull. Text to the right is left-aligned, to the left right-aligned.
2. **Score association over the whole active zoom range**, strongest penalty
   first: other communities' visible marks under the text; own marks under it;
   foreign dominance of nearby marks; a foreign mark nearer than the gap. Accept
   only under a stated cost (sampled zooms; say so); otherwise delay, or leave
   the name off the map with list/search/report access. The default-view tier
   must be fully visible; disclose its compromises.
3. **Colors:** assign categorical colors so spatial neighbours differ (measured
   on the rendered layout); keep names, list entries and nodes on the same entry.
4. **Stability and state:** freeze plans during pan/zoom; keep them on small
   resizes; re-anchor after persistent filter or node-size changes settle. Plan
   only from PERSISTENT eligibility (filters), never from temporary selection or
   neighbour focus, and include every planning dependency in the invalidation key.
5. **Visibility:** never draw names truncated at the map edge or beneath overlaid
   controls. Explicit Locate frames the members and the name in the uncovered map
   area and brings the map into the BROWSER viewport on stacked layouts.
6. **Verify like a user and independently of the planner:** renderer node sizes
   and brute-force scans for association; camera sweeps for controls/clipping;
   real-control sequences that combine features (e.g. focus → resize → Clear →
   Reset); Locate outcomes intersected with the page viewport, with expected
   success asserted; archived audit scripts that run on every compared version.

## Historical: 2026-09-30 — navigation stability and information hierarchy

A collision-free still frame can be a poor interactive map. Re-ranking by the
currently visible member count/audience, choosing another visible anchor, or
searching for a fresh empty label position on every frame makes descriptions
jump and breaks orientation. Keep these concerns separate:

- **Stable reference:** use an actual member near a declared community center,
  and fix that geometric attachment point in world coordinates. Attach the near
  edge or corner of the text box using a CSS-pixel gap; do not store an offset
  text center in world coordinates. Pan and zoom transform the geometric port,
  while the pixel gap and text extent remain screen-sized. Freeze placement and active zoom ranges for
  the current viewport; replan on a deliberate layout/viewport resize only.
- **Stable importance:** rank by the declared full-community measure. Do not
  substitute the viewport's visible audience or silently recompute rankings
  after filtering. Explain that summed subscriber counts are not unique people.
- **Progressive detail:** show a small number of high-priority names at overview,
  then monotonically activate more names at fixed scale thresholds. A name can
  leave the viewport naturally; don't replace it merely because another name
  is now locally more prominent. Use a small scale-based fade near thresholds.
- **Quiet labels:** short one-line aliases, fixed readable CSS font sizes, and
  restrained text halos usually beat large bordered multi-line cards and long
  leaders. Retain mixed/uncertain meaning in aliases. Put full descriptions,
  qualifications and samples in an inspection panel rather than on the map.
- **Persistent navigation:** a ranked list gives access to important groups even
  offscreen. Selection should highlight actual members and preserve context;
  make camera movement an explicit Locate action. Use accessible buttons,
  keyboard operation and visible selection states. Treat hover text as optional.
- **Honest tradeoffs:** text-text collision prevention matters, but hiding most
  descriptions until extreme zoom simply to avoid every node is not useful.
  Prefer empty space locally; minimize unavoidable mark occlusion, preserve
  stable positions, and disclose the tradeoff. Do not promise zero node-label
  collisions at every zoom unless measured. Filtering should not relocate names.

Test actual pointer drags and zoom controls. Compare every retained label's
translation with the camera transform, verify world-anchor invariance, fixed
font sizes, monotonic active ranges, and priority ordering. Test highlight
without camera/filter changes, saved view round trips, keyboard activation,
responsive replanning, alternative partition suppression, and filtered views.
Check screenshots at overview and intermediate zoom; measure pairwise label
collisions separately from node-label intersections. A frozen placement may
need a different plan for mobile; resizing is distinct from ordinary navigation.

Research supporting these principles (implementation choices remain specific
to the task, not a universal optimum):

- Been, Daiches & Yap (2006), [Dynamic Map Labeling](https://cs.nyu.edu/visual/home/pub/infovis06.pdf): consistency during continuous pan and zoom, including continuous positions and avoiding unnecessary label appearance/disappearance.
- Been et al. (2010), [Optimizing active ranges for consistent dynamic map labeling](https://www.sciencedirect.com/science/article/pii/S0925772109000649): scale-dependent active ranges for consistent labeling.
- Mapbox, [Optimize map label placement](https://docs.mapbox.com/help/dive-deeper/optimize-map-label-placement/): importance ordering and label hierarchy; library-specific behavior is not a requirement to adopt that library.
- Nielsen Norman Group, [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) and [Aesthetic and Minimalist Design](https://www.nngroup.com/articles/aesthetic-minimalist-design/): prioritize common interactions and reveal secondary detail on demand.

## Historical: 2026-09-30 — hull ports and screen-space attachment (superseded)

A later user review exposed another failure of the initial fixed-center design:
a text center offset in graph units moves farther from its community in screen
pixels as the user zooms. Temporal stability alone is insufficient. Measure the
near-edge-to-feature gap, not just whether the center obeys the camera transform.

For external descriptions of graph communities, derive a convex hull from the
full declared membership in the actual serialized display coordinates. Keep
analytical membership fixed. A full hull can contain empty areas and be affected
by peripheral members; do not silently trim it or treat it as a substantive
geographic/social boundary. Choose candidate ports on outward-facing hull edges.

Use the correct coordinate spaces and attachments:

- Project the geometric boundary port with the graph's camera.
- To its right, left-align text; to its left, right-align text. Attach the near
  side of the text rectangle, never its center with a pre-scaled world offset.
- Keep clearance and font size in CSS pixels. For sloping hull sides, attach the
  outward corner of the text box or adjust its vertical justification so the
  rectangle stays outside the hull without a large horizontal displacement.
- Singleton/collinear communities need an explicit fallback; include the actual
  screen-space glyph radius in the offset where the attachment is a node.
- Compare whitespace across zoom scales, including rendered node footprints and
  text boxes. Prefer close association with member marks over empty long hull
  edges; retain a declared importance ranking and stable ports during pan/zoom.
- Test future collisions, not just the entry scale. Opposite text alignments can
  produce collisions at an intermediate zoom even when they fit initially.
  Use interval analysis or a sufficiently dense scale sweep; a label-centered
  point-distance formula does not describe asymmetrically attached rectangles.
- Keep overview names inside the initial viewport and clear of fixed controls,
  but do not continually clamp them to screen edges as the camera pans.
- When space is insufficient, delaying a lower-priority label preserves a short
  attachment better than pushing it far from its community. Sidebar access
  remains available. Node-mark intersections should be measured and disclosed.

Verification should independently check that the port lies on a supporting hull
edge, all community centers are on its interior side, every label corner is on
the exterior side, the near text edge is the side closest to the community, and
the pixel gap stays bounded across a broad zoom sweep. Inspect intermediate
zoom screenshots and mobile views. Preserve matching node/label colors.

Sources (rules and general models, not optimality claims for our heuristic):

- GeoServer, [Labeling](https://docs.geoserver.org/main/en/user/styling/sld/reference/labeling/): label-box anchor fractions distinguish left, right and center; displacement is specified in pixels.
- Čmolík et al. (2020), [Mixed Labeling: Integrating Internal and External Labels](https://www.cg.tuwien.ac.at/research/publications/2020/cmolik-2020-tvcg/), [paper](https://www.cg.tuwien.ac.at/research/publications/2020/cmolik-2020-tvcg/cmolik-2020-tvcg-paper.pdf): screen-space candidate evaluation, silhouette ports, and corner or side-midpoint attachment for external labels.
- Bekos, Niedermann & Nöllenburg (2019), [External Labeling Techniques: A Taxonomy and Survey](https://arxiv.org/abs/1902.01454): external labeling models, ambiguity, layout quality and algorithmic approaches.
- Been, Daiches & Yap (2006), [Dynamic Map Labeling](https://cs.nyu.edu/visual/home/pub/infovis06.pdf): continuity during navigation. Correct geometric association must be checked in addition to continuity.

## Historical: 2026-10-01 — why names must associate with their own marks

An independent review of the hull-port design measured that names placed 6 px
outside a community's convex-hull line often sat on, or nearer to, another
community (up to 1,126 foreign marks under names on mobile at 8×), and that on
long hull edges the distance from a name to its own nearest mark again grew
linearly with zoom. A hull line is display geometry: it can run through empty
space and through neighbouring communities. The author's gap test measured
distance to the port it had just computed, which cannot detect either failure.

- **Anchor to a member glyph.** Attach the near text edge a fixed CSS-pixel gap
  beyond one real, displayed member's rendered circle, preferably on the
  community's outer edge (hull vertices, left/right extremes of label-height
  bands; boundary-preferred, not guaranteed). Distance to the own community is then bounded by construction at
  every zoom. Require the anchor to be visibly sized when the name activates.
- **Score association, not just whitespace.** Over the candidate's whole active
  range, penalize other communities' visible marks under the text most
  strongly, then own marks under it, foreign dominance of the surroundings and
  foreign marks nearer than the attachment gap. Area-weighted "occlusion" alone
  lets a name cover dozens of small foreign marks cheaply.
- **Delay or omit rather than mislabel.** Accept only placements under a stated
  cost; otherwise delay activation progressively, and leave a name off the map
  (keeping list/search/report access) if nothing is acceptable. Keep the
  default-view tier fully visible and disclose its compromises.
- **Do not chain activation to rank order.** Planning order gives priority;
  forcing monotone activation makes one delayed name delay all later ones.
- **Controls and edges.** Do not draw names beneath overlaid controls or
  truncated at the viewport edge. Locate should frame the name as well as
  the members, avoiding control areas.
- **Resize and filters.** Keep plans on small resizes (hysteresis by viewport
  class and overview scale). After filters or node-size changes settle,
  re-anchor to displayed members; never leave a name beside a hidden channel.
- **Colors.** Replace `id % palette` with an assignment that gives spatially
  adjacent communities dissimilar (CIELAB) colors; measure adjacency on the
  rendered layout, including nearby salient marks across small visible gaps.
- **Verify independently.** Use the renderer's node sizes and a brute-force
  scan of displayed nodes to measure, per name and zoom: nearest own vs foreign
  visible mark, foreign/own marks under the text, and surrounding mark area.
  Also sweep camera positions for control overlap and truncation, and check
  Locate outcomes, filters, sizing modes and resizes.

Tradeoff: fewer names are active at intermediate zoom once names may no longer
sit on other communities. Report it rather than hiding it.
