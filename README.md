# SkyRoute / 天途

Streamlit demonstrator for vulnerability-aware emergency prevention, incident
command, road routing, resource dispatch and environmental protection.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Replace the current GitHub version

Upload the contents of this folder to the repository root and choose
**Commit changes**. The main application file must be named `app.py`.

Required repository structure:

```text
app.py
requirements.txt
.gitignore
README.md
.github/workflows/python-check.yml
assets/
```

The map icons are also embedded in `app.py`, so the application remains
self-contained if Streamlit cannot resolve an asset path. The files in
`assets/` are retained as editable design sources.

## Map context

The essential operational context remains visible without a separate Layers
control. When OSMnx and an internet connection are available, land use and flat
building footprints request OpenStreetMap context. The offline
fallback is identified as illustrative context. Building footprints are flat
visual boundaries only; no height, occupancy or structural condition is
inferred, and they do not affect the routing or risk models.

The small map bar keeps north orientation on the upper-left and exposes source,
interaction and modeling notes only through the `i` control.

Moving units display their identity, status and remaining ETA without requiring
hover. The header keeps only the **Data** action on the far right.

Production use requires authorized operational feeds, validated models,
licensed integrations and final human command authority.
