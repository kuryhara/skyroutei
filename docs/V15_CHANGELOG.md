# SkyRoute map cleanup

- Removed the visible 3D building and population-volume controls.
- Forced tactical maps to a flat camera and disabled extrusion layers.
- Replaced fragile Unicode/emoji map markers with robust badge markers:
  P police, F fire, H HazMat, A EMS, + hospital, B bus, E environmental, S sensor.
- Added a dark text shadow so badge labels remain visible over roads, plume zones and water.
- Updated the consolidated-plan legend to use the same badges shown on the map.
- Added a visual mask behind the working map-help control so the passive native information/attribution icon is no longer duplicated.
- No new Python dependencies.
