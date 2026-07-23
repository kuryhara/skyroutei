# Incident icon update

- Added a self-contained red incident-alert SVG as an embedded data URI.
- Added a correctly configured PyDeck `IconLayer` with consistent per-row `icon_data`.
- Added an always-present `TextLayer` warning fallback beneath the SVG icon.
- Updated all incident markers across city, incident, population, dispatch, traffic, environmental, consolidated-plan and live-case maps.
- Updated every matching legend to render the same embedded incident icon.
- Preserved city-map incident selection through the existing `incidents-points` layer id.
- No external icon file is required at runtime; the SVG in `assets/` is included only as a design source/reference.
