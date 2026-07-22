# SkyRoute / 天途

Interactive Streamlit prototype for vulnerability-aware emergency decision support in hazardous-material road incidents.

## Fast setup on Windows

Requirements:

- Python 3.11 or newer
- Docker Desktop with WSL 2
- Git or GitHub Desktop for collaboration

Open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\scripts\start_all.ps1
```

The first setup downloads the Jiangsu OpenStreetMap extract and builds the local routing graph. This can take several minutes. When ready, Streamlit opens at:

```text
http://localhost:8501
```

The local OpenRouteService health endpoint is:

```text
http://localhost:8080/ors/v2/health
```

## Daily use

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_all.ps1
```

To stop the local routing service:

```powershell
.\scripts\stop_all.ps1
```

## Collaboration workflow

1. Pull the newest `main` branch.
2. Create a branch named after the task, for example `feature-map-legend`.
3. Make and test changes locally.
4. Commit with a clear message.
5. Push the branch and open a Pull Request.
6. Merge only after another team member reviews it.

Do not commit the Jiangsu `.osm.pbf`, generated ORS graphs, secrets, virtual environments, or logs. They are already ignored by `.gitignore`.

## Main files

- `app.py` — Streamlit application
- `docker-compose.yml` — local OpenRouteService
- `requirements.txt` — Python packages
- `scripts/` — setup, start, stop and diagnostic commands
- `docs/` — project and collaboration notes

## Important

This is a demonstrator. Simulated data and model outputs are not real emergency orders. Human confirmation remains mandatory.


## Brand assets

The vector SkyRoute 天途 logo is stored in `assets/skyroute_tiantu_vector.svg` and embedded in `app.py` for reliable local and cloud rendering.
