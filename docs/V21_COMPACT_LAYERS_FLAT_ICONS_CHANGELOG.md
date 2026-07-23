# SkyRoute v21 — compact layers and flat map icons

- Replaced the large toggle panel with a compact inline Layers toolbar.
- Layer pills: population, environment, resources, and routes.
- Active pills use a restrained cyan state; inactive pills remain neutral.
- Removed the 3D building option and disabled illustrative building massing on every map.
- Kept the angled, rotatable map view without volumetric buildings.
- Moved operational PNG icons and text symbols into the geographic map plane (`billboard=False`).
- Disabled depth testing for those flat symbols to prevent clipping against the basemap.
- Removed redundant ASCII fallback glyphs beneath PNG icons to avoid visual collisions.
- Slightly reduced icon sizes.
- Removed the 3D-building card and language from Cases & Data.
