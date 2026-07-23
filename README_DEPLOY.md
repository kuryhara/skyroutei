# SkyRoute — current static site

This folder contains the current SkyRoute React production build shown in the
existing prototype, plus the requested presentation, map-source and
flat-building improvements.

## GitHub upload

Use the existing `main` branch. Upload every file and folder in this directory
to the repository root while preserving the `assets/` and `data/` folders.

The former `skyroute_cco_v4_complete.py` and `requirements.txt` files are not
used by this site. They may be deleted after the static files are uploaded.

Then enable GitHub Pages:

1. Open **Settings**.
2. Open **Pages**.
3. Choose **Deploy from a branch**.
4. Select `main` and `/ (root)`.
5. Save.

This is a static GitHub Pages site. It does not run through Streamlit and does
not use `requirements.txt` or the former Python application.

## Requested changes included

- `Data` and `Presentation` controls in the upper-right corner.
- Guided presentation with Population, Dispatch, Traffic and Environment
  function explanations.
- Existing land-use data retained.
- Building outlines rendered as flat footprints, without 3D extrusion.
- Small north indicator on the map.
- Map attribution kept inside MapLibre's compact information control.

## Included data

- OpenStreetMap vector context, land use and flat building footprints.
- WorldPop-derived scenario cells.
- Compact two-dimensional fallback map.
- Deterministic demonstration routes, exposure and incident states.

The package is an academic decision-support demonstration, not a live emergency
command system.
