# V23 — Zoom-scaled incident icons

- Incident markers now use meter-based IconLayer sizing.
- Markers grow smoothly when zooming in and shrink when zooming out.
- A minimum of 18 px preserves readability at city scale.
- A maximum of 46 px prevents oversized symbols at street scale.
- Existing billboard orientation, elevation and disabled depth testing are retained.
- No routing, risk, dispatch, plume or layer-control logic was changed.
