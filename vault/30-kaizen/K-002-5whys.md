# 5 Whys — root cause (K-002)

- **Kaizen item:** K-002
- **Problem statement:** Running comps for 119 Countryside Ln (Henrico), the
  skill's headline technique (query the county live ArcGIS sales FeatureServer)
  failed — Henrico has no usable sales layer — forcing slow improvisation.

1. Why did the technique fail? -> Henrico's only public parcel layer is a
   735-record sample and exposes no queryable sales endpoint.
2. Why did the skill assume one existed? -> The headline technique was generalized
   from counties that DO have one (Hanover, Chesterfield).
3. Why was a county-specific assumption made the default? -> County record systems
   were treated as uniform; the skill had no routing layer to branch on.
4. Why no routing layer? -> County specifics lived as loose notes in
   va-data-sources.md, not as a structured registry the skill keys off.
5. Why notes instead of a registry? -> The skill grew subject + comp logic
   together; the two concerns (assessment SOR vs comp source) were never split.

- **Root cause:** No routing/registry layer separating subject-verification
  (assessment SOR, per-vendor) from comp-pull (MLS-first; GIS only where a sales
  layer exists). One technique was hardcoded as the default for all counties.
- **Countermeasure (specifically):** (1) ADR-002 two-module + adapter design;
  (2) `county-registry.md` with Sales-GIS?/Comp-source columns; (3) reframe SKILL
  Step 1 as registry-driven routing and demote the ArcGIS technique to one
  adapter; (4) `matrix-comp-search.md` playbook for the MLS-only path.
