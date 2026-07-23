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

## Presentation mode

Use **▶ Presentation** in the upper-right corner. The guided case study covers:

1. preventive intelligence;
2. dynamic population by time of day;
3. fastest route versus safer route;
4. continuous replanning;
5. agent orchestration and human approval.

The pitch metrics are explicitly identified as scenario estimates. The
application does not claim predicted lives saved or perform real dispatch.

## Map context

When OSMnx and an internet connection are available, the **land use** and
**buildings** switches request OpenStreetMap context. Building footprints are
flat visual boundaries only; no height, occupancy or structural condition is
inferred, and they do not affect the routing or risk models.

Production use requires authorized operational feeds, validated models,
licensed integrations and final human command authority.
