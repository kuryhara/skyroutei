"""
SkyRoute / 天途 v16 — Live Vulnerability-Aware Emergency Decision Agent
==================================================================
Single-file Streamlit application for a demonstrator of hazardous-material
incident prevention, command, routing, dispatch, population protection,
traffic control, environmental response and executive presentation.

Run on Windows PowerShell
-------------------------
cd "C:\\Users\\leara\\Downloads"
python -m streamlit run app.py

Required packages
-----------------
python -m pip install streamlit pydeck plotly pandas numpy requests networkx

Optional packages
-----------------
python -m pip install osmnx

Optional routing integrations
-----------------------------
The default routing backend is a local OpenRouteService instance at:
http://localhost:8080/ors

No API key or billing account is required for the local backend. Optional remote
connectors can still be configured with ORS_API_KEY or AMAP_KEY.

OpenRouteService returns explicit GeoJSON road geometries that are drawn inside
the existing PyDeck map, so the plume, vulnerable populations, water and
ecological layers remain visible. No Google billing account is required.

Important
---------
The default data, events, population estimates, plume geometry and agency
positions are simulated for product demonstration. The application does not
issue real emergency orders. AMap and OSMnx are optional connectors and must
be validated, licensed and secured before production use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import copy
import json
import math
import os
import re
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:  # pragma: no cover
    ox = None
    OSMNX_AVAILABLE = False


# =============================================================================
# PAGE AND VISUAL SYSTEM
# =============================================================================
st.set_page_config(
    page_title="SkyRoute v16 | SkyTech CCO",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

INK = "#06110E"
PANEL = "#0B1812"
PANEL_2 = "#08130F"
LINE = "#405334"
CYAN = "#D5F26D"
BLUE = "#52A1BE"
TEAL = "#A9BF5A"
AMBER = "#768C45"
RED = "#F26457"
PURPLE = "#D5F26D"
GREEN = "#A9BF5A"
TEXT = "#F2F6E8"
MUTED = "#B7C99D"

SKYROUTE_LOGO_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxOTggMTIyIiByb2xlPSJpbWciIGFyaWEtbGFiZWw9IlNreVJvdXRlIOWkqemAlCBsb2dvIj4KICA8cmVjdCB3aWR0aD0iMTk4IiBoZWlnaHQ9IjEyMiIgcng9IjAiIGZpbGw9IiNENUYyNkQiLz4KICA8cGF0aCBkPSJNIDEzOCA2NiBMIDEzNCA2NiBMIDEzNCA2NyBMIDEzMiA2OSBMIDEzMiA3MCBMIDEzMCA3MiBMIDEzMCA3MyBMIDEyNCA3OSBMIDEyNSA3OSBMIDEyNyA4MSBMIDEyOCA4MSBMIDEzMyA3NiBMIDEzMyA3NSBMIDEzNyA3MCBMIDEzNyA2OSBMIDEzOCA2OCBaIE0gMTYxIDY2IEwgMTYwIDY3IEwgMTYwIDY4IEwgMTY1IDczIEwgMTY1IDc0IEwgMTY3IDc2IEwgMTY3IDc3IEwgMTY5IDc5IEwgMTY5IDgwIEwgMTcwIDgxIEwgMTcxIDgwIEwgMTcyIDgwIEwgMTczIDc5IEwgMTczIDc4IEwgMTcyIDc3IEwgMTcyIDc2IEwgMTcwIDc0IEwgMTcwIDczIEwgMTY3IDcwIEwgMTY3IDY5IEwgMTYzIDY1IEwgMTYyIDY2IFogTSAxMDUgNTIgTCAxMDUgNTYgTCAxMTQgNTYgTCAxMTUgNTcgTCAxMTUgODIgTCAxMTQgODMgTCAxMTMgODMgTCAxMTEgODUgTCAxMTAgODUgTCAxMDQgOTEgTCAxMDYgOTMgTCAxMDYgOTQgTCAxMDcgOTUgTCAxMTYgODYgTCAxMjAgODYgTCAxMjUgOTAgTCAxMjYgOTAgTCAxMjkgOTIgTCAxMzEgOTIgTCAxMzIgOTMgTCAxMzQgOTMgTCAxMzUgOTQgTCAxNzQgOTQgTCAxNzQgOTMgTCAxNzUgOTIgTCAxNzUgOTAgTCAxNzYgODkgTCAxNzAgODkgTCAxNjkgOTAgTCAxMzYgOTAgTCAxMzUgODkgTCAxMzIgODkgTCAxMzEgODggTCAxMjkgODggTCAxMjcgODYgTCAxMjQgODUgTCAxMjIgODMgTCAxMjEgODMgTCAxMjAgODIgTCAxMjAgNTIgWiBNIDI5IDMwIEwgMjkgMzUgTCA1NiAzNSBMIDU3IDM2IEwgNTcgNTMgTCA1NiA1NCBMIDI2IDU0IEwgMjYgNTkgTCA1NCA1OSBMIDU1IDYwIEwgNTUgNjIgTCA1NCA2MyBMIDU0IDY1IEwgNTMgNjYgTCA1MyA2NyBMIDUyIDY4IEwgNTEgNzEgTCA0OCA3NCBMIDQ4IDc1IEwgNDEgODIgTCA0MCA4MiBMIDM3IDg1IEwgMzYgODUgTCAzNSA4NiBMIDM0IDg2IEwgMzIgODggTCAzMSA4OCBMIDMwIDg5IEwgMjkgODkgTCAyOCA5MCBMIDI1IDkxIEwgMjUgOTIgTCAyOCA5NSBMIDI5IDk1IEwgMzAgOTQgTCAzMSA5NCBMIDMyIDkzIEwgMzMgOTMgTCAzNCA5MiBMIDM3IDkxIEwgMzkgODkgTCA0MCA4OSBMIDQyIDg3IEwgNDMgODcgTCA0OCA4MiBMIDQ5IDgyIEwgNTAgODEgTCA1MCA4MCBMIDU0IDc2IEwgNTQgNzUgTCA1NiA3MyBMIDU2IDcyIEwgNTggNjkgTCA1OCA2NyBMIDYwIDY1IEwgNjEgNjUgTCA2MiA2NiBMIDYyIDY4IEwgNjMgNjkgTCA2MyA3MCBMIDY1IDcyIEwgNjYgNzUgTCA2OSA3OCBMIDY5IDc5IEwgNzggODggTCA3OSA4OCBMIDgxIDkwIEwgODIgOTAgTCA4MyA5MSBMIDg0IDkxIEwgODUgOTIgTCA4NiA5MiBMIDkxIDk1IEwgOTMgOTUgTCA5MyA5NCBMIDk2IDkxIEwgOTUgOTEgTCA5NCA5MCBMIDkyIDkwIEwgOTEgODkgTCA5MCA4OSBMIDg5IDg4IEwgODYgODcgTCA4MSA4MyBMIDgwIDgzIEwgNzEgNzQgTCA3MSA3MyBMIDY3IDY4IEwgNjcgNjcgTCA2NSA2NCBMIDY1IDYyIEwgNjQgNjEgTCA2NCA2MCBMIDY1IDU5IEwgOTQgNTkgTCA5NCA1NCBMIDYzIDU0IEwgNjIgNTMgTCA2MiAzNiBMIDYzIDM1IEwgOTAgMzUgTCA5MSAzNCBMIDkxIDMwIFogTSAxMDggMjkgTCAxMDggMzAgTCAxMDkgMzEgTCAxMTAgMzEgTCAxMTIgMzMgTCAxMTMgMzMgTCAxMTggMzggTCAxMTkgMzggTCAxMjAgMzkgTCAxMjMgMzYgTCAxMTkgMzIgTCAxMTggMzIgTCAxMTYgMzAgTCAxMTUgMzAgTCAxMTMgMjggTCAxMTIgMjggTCAxMTEgMjcgTCAxMTAgMjcgWiBNIDE0OSAyMyBMIDE0OCAyMyBMIDE0OCAyNCBMIDE0NSAyNyBMIDE0NSAyOCBMIDEzOCAzNSBMIDEzNyAzNSBMIDEzNCAzOCBMIDEzMyAzOCBMIDEyOCA0MiBMIDEyNyA0MiBMIDEyNiA0MyBMIDEyMyA0NCBMIDEyMyA0NSBMIDEyNiA0OCBMIDEyNyA0NyBMIDEzMCA0NiBMIDEzMiA0NCBMIDEzNSA0MyBMIDEzNiA0NCBMIDEzNiA0OCBMIDE0NiA0OCBMIDE0NyA0OSBMIDE0NyA1NiBMIDE0NiA1NyBMIDEyNiA1NyBMIDEyNiA2MCBMIDEyNyA2MSBMIDE0NiA2MSBMIDE0NyA2MiBMIDE0NyA4MCBMIDE0NiA4MSBMIDEzOSA4MSBMIDEzOSA4MyBMIDE0MCA4NCBMIDE0MCA4NSBMIDE0OCA4NSBMIDE1MSA4MyBMIDE1MSA4MiBMIDE1MiA4MSBMIDE1MiA2MiBMIDE1MyA2MSBMIDE3MyA2MSBMIDE3NCA2MCBMIDE3NCA1NyBMIDE1MyA1NyBMIDE1MiA1NiBMIDE1MiA0OSBMIDE1MyA0OCBMIDE2MyA0OCBMIDE2NCA0NyBMIDE2NCA0NCBMIDE2NSA0MyBMIDE2NiA0MyBMIDE2OCA0NSBMIDE2OSA0NSBMIDE3MCA0NiBMIDE3MiA0NiBMIDE3MyA0NyBMIDE3NCA0NiBMIDE3NCA0NSBMIDE3NiA0MyBMIDE3NSA0MiBMIDE3MyA0MiBMIDE3MiA0MSBMIDE3MSA0MSBMIDE3MCA0MCBMIDE2OSA0MCBMIDE2OCAzOSBMIDE2NSAzOCBMIDE2MyAzNiBMIDE2MiAzNiBMIDE2MCAzNCBMIDE1OSAzNCBMIDE1MiAyNyBMIDE1MiAyNSBaIE0gMTM1IDQyIEwgMTM2IDQxIEwgMTM3IDQxIEwgMTQwIDM4IEwgMTQxIDM4IEwgMTQ4IDMxIEwgMTUwIDMxIEwgMTU1IDM2IEwgMTU2IDM2IEwgMTYwIDQwIEwgMTYxIDQwIEwgMTYzIDQyIEwgMTYzIDQzIEwgMTYyIDQ0IEwgMTM2IDQ0IEwgMTM1IDQzIFoiIGZpbGw9IiMwNjExMEUiIGZpbGwtcnVsZT0iZXZlbm9kZCIgY2xpcC1ydWxlPSJldmVub2RkIi8+Cjwvc3ZnPg=="

def skyroute_logo_html(css_class: str = "sr-brand-lockup") -> str:
    return f'<div class="{css_class}"><img src="{SKYROUTE_LOGO_DATA_URI}" class="sr-brand-icon" alt="SkyRoute 天途 logo"/><div class="sr-brand-wordmark">SKYROUTE</div></div>'


st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{display:none!important;}}
.sr-top-controls{{border:1px solid rgba(255,255,255,.11);border-radius:14px;padding:10px 12px;background:rgba(5,15,12,.86);margin:4px 0 12px;box-shadow:0 0 22px rgba(0,229,255,.035);}}
.sr-control-note{{font:9px 'JetBrains Mono';color:#91A87A;margin:-3px 0 8px;}}

html, body, [class*="css"] {{font-family:'Poppins',sans-serif;}}
.stApp {{background:radial-gradient(circle at 80% -10%,#18271D 0%,{INK} 34%,#030806 100%);color:{TEXT};}}
#MainMenu, footer, header {{visibility:hidden;}}
.block-container {{padding-top:.75rem;padding-bottom:2rem;max-width:1850px;}}
section[data-testid="stSidebar"] {{background:linear-gradient(180deg,{PANEL_2},#030806);border-right:1px solid {LINE};}}
section[data-testid="stSidebar"] * {{border-radius:8px;}}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown {{color:{MUTED}!important;}}
.sr-top {{border:1px solid #768C45;background:linear-gradient(135deg,rgba(24,39,29,.97),rgba(6,17,14,.99));box-shadow:0 0 42px rgba(213,242,109,.09);border-radius:15px;padding:14px 18px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;}}
.sr-brand {{display:flex;gap:13px;align-items:center;}}
.sr-logo {{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;color:#06110E;font-family:'Poppins';font-weight:700;background:linear-gradient(135deg,{CYAN},{TEAL});box-shadow:0 0 23px rgba(213,242,109,.38);}}
.sr-name {{font-family:'Poppins';font-size:22px;font-weight:700;}}
.sr-sub {{font:10px 'JetBrains Mono';color:{MUTED};letter-spacing:.08em;text-transform:uppercase;margin-top:2px;}}
.sr-topstats {{display:flex;gap:24px;flex-wrap:wrap;}}
.sr-topstat {{font:9.5px 'JetBrains Mono';color:{MUTED};text-transform:uppercase;}}
.sr-topstat b {{display:block;color:{TEXT};font-size:11.5px;margin-top:4px;text-transform:none;}}
.sr-card {{border:1px solid {LINE};border-radius:12px;padding:12px 14px;background:linear-gradient(180deg,rgba(8,24,42,.98),rgba(4,13,25,.98));box-shadow:inset 0 1px rgba(255,255,255,.025);min-height:86px;}}
.sr-card .k {{font:9px 'JetBrains Mono';color:{MUTED};text-transform:uppercase;letter-spacing:.06em;}}
.sr-card .v {{font-family:'Poppins';font-size:19px;font-weight:700;margin-top:5px;}}
.sr-card .d {{font:9.5px 'JetBrains Mono';color:{MUTED};margin-top:5px;}}
.sr-h2 {{font-family:'Poppins';font-size:14px;font-weight:700;border-left:3px solid {CYAN};padding-left:9px;margin:15px 0 9px;letter-spacing:.025em;}}
.sr-panel {{border:1px solid {LINE};border-radius:12px;background:linear-gradient(180deg,rgba(8,24,42,.96),rgba(5,15,28,.96));padding:14px;margin-bottom:10px;}}
.sr-panel.selected {{border-color:{CYAN};box-shadow:0 0 24px rgba(213,242,109,.12);}}
.sr-title {{font-family:'Poppins';font-weight:700;font-size:14px;}}
.sr-body {{font-size:12px;line-height:1.55;color:#D6E2C6;margin-top:6px;}}
.sr-small {{font:10px 'JetBrains Mono';color:{MUTED};line-height:1.5;}}
.sr-badge {{display:inline-block;border:1px solid {LINE};border-radius:18px;padding:3px 8px;margin:8px 4px 0 0;font:9px 'JetBrains Mono';color:{MUTED};}}
.badge-safe {{color:{TEAL};border-color:{TEAL};}} .badge-fast {{color:{CYAN};border-color:{CYAN};}} .badge-warn {{color:{AMBER};border-color:{AMBER};}} .badge-danger {{color:{RED};border-color:{RED};}} .badge-ai {{color:{PURPLE};border-color:{PURPLE};}}
.sr-alert {{border-left:4px solid {AMBER};background:rgba(118,140,69,.06);padding:11px 13px;margin:8px 0;border-radius:0 10px 10px 0;}}
.sr-critical {{border-left-color:{RED};background:rgba(242,100,87,.07);}}
.sr-good {{border-left-color:{TEAL};background:rgba(169,191,90,.06);}}
.sr-step {{border-left:2px solid {LINE};padding-left:11px;margin:7px 0;font-size:11.5px;color:#C7D6B4;}}
.sr-selected-row {{border:1px solid {CYAN};background:rgba(213,242,109,.05);border-radius:10px;padding:10px;}}
.stButton>button {{border:1px solid {CYAN};background:rgba(213,242,109,.035);color:{CYAN};font:10.5px 'JetBrains Mono';border-radius:8px;}}
.stButton>button:hover {{background:{CYAN};color:#06110E;}}
button[kind="primary"] {{background:linear-gradient(135deg,{CYAN},{TEAL})!important;color:#06110E!important;border:none!important;font-weight:700!important;}}
[data-testid="stMetric"] {{border:1px solid {LINE};border-radius:10px;background:rgba(5,17,31,.8);padding:8px 10px;min-width:0;overflow:hidden;}}
[data-testid="stMetricLabel"] p {{font:9px 'JetBrains Mono'!important;line-height:1.25!important;color:{MUTED}!important;white-space:normal!important;}}
[data-testid="stMetricValue"] {{font-family:'Poppins';min-width:0;overflow:hidden;}}
[data-testid="stMetricValue"] p {{font-family:'Poppins'!important;font-size:15px!important;line-height:1.15!important;white-space:normal!important;overflow-wrap:anywhere!important;word-break:normal!important;margin:0!important;}}
[data-testid="stMetricDelta"] p {{font-size:9px!important;line-height:1.2!important;white-space:normal!important;}}
[data-testid="stChatMessage"] {{border:1px solid {LINE};border-radius:12px;background:rgba(6,19,34,.72);}}
.sr-footer {{border-top:1px solid {LINE};padding:15px;text-align:center;color:{MUTED};font:9.5px 'JetBrains Mono';line-height:1.6;margin-top:22px;}}
.sr-weather{{border:1px solid #52A1BE;border-radius:14px;padding:14px;background:linear-gradient(135deg,rgba(20,63,101,.88),rgba(5,18,34,.96));box-shadow:0 0 28px rgba(213,242,109,.08);}}
.sr-weather-main{{display:flex;align-items:center;justify-content:space-between;gap:12px;}}
.sr-weather-temp{{font-family:'Poppins';font-size:44px;font-weight:700;line-height:1;}}
.sr-weather-icon{{font-size:42px;filter:drop-shadow(0 0 10px rgba(213,242,109,.4));}}
.sr-weather-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:12px;}}
.sr-weather-cell{{border:1px solid #405334;border-radius:9px;padding:8px;background:rgba(3,12,23,.55);font:9px 'JetBrains Mono';color:#B7C99D;}}
.sr-weather-cell b{{display:block;color:#F2F6E8;font-size:12px;margin-top:4px;}}
.sr-forecast-head{{margin:12px 0 0;padding:12px 14px 8px;border:1px solid rgba(213,242,109,.62);border-bottom:none;border-radius:14px 14px 0 0;background:linear-gradient(110deg,rgba(213,242,109,.11),rgba(6,17,14,.97));box-shadow:0 0 24px rgba(213,242,109,.14),inset 0 0 18px rgba(213,242,109,.035);}}
.sr-forecast-head .title{{font-family:'Poppins';font-size:15px;font-weight:700;color:#D5F26D;letter-spacing:.035em;text-shadow:0 0 7px rgba(213,242,109,.42);}}
.sr-forecast-head .sub{{font:9px 'JetBrains Mono';color:#B7C99D;margin-top:3px;}}
[data-testid="stSidebarHeader"]{{display:none!important;}}
[data-testid="stSidebar"] > div:first-child{{padding-top:.8rem!important;}}
.sr-tabline{{border:1px solid #405334;border-radius:12px;padding:8px;background:rgba(5,17,31,.82);margin:6px 0 12px;}}
.sr-ai-strip{{border:1px solid #768C45;border-radius:13px;padding:12px 14px;background:linear-gradient(100deg,rgba(86,47,141,.25),rgba(7,22,39,.95));box-shadow:0 0 25px rgba(213,242,109,.09);margin-bottom:10px;}}
.sr-ai-grid{{display:grid;grid-template-columns:1.4fr .7fr .7fr;gap:10px;align-items:center;}}
.sr-ai-label{{font:9px 'JetBrains Mono';color:#D5F26D;text-transform:uppercase;letter-spacing:.08em;}}
.sr-ai-value{{font-family:'Poppins';font-weight:700;font-size:15px;margin-top:3px;}}
.sr-resource-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0 12px;}}
.sr-resource-card{{border:1px solid #405334;border-radius:10px;padding:10px;background:rgba(5,17,31,.82);}}
.sr-resource-card .n{{font-family:'Poppins';font-weight:700;font-size:13px;}}
.sr-resource-card .s{{font:9px 'JetBrains Mono';color:#B7C99D;margin-top:5px;line-height:1.5;}}
.sr-receipt{{border:1px solid #A9BF5A;border-radius:13px;padding:14px;background:linear-gradient(120deg,rgba(169,191,90,.12),rgba(4,18,31,.96));box-shadow:0 0 28px rgba(169,191,90,.1);margin:10px 0;}}
.sr-receipt-title{{font-family:'Poppins';font-size:16px;font-weight:700;color:#A9BF5A;}}
.sr-receipt-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px;}}
.sr-receipt-item{{font:9px 'JetBrains Mono';color:#B7C99D;border-left:2px solid #A9BF5A;padding-left:8px;}}
.sr-receipt-item b{{display:block;color:#F2F6E8;font-size:11px;margin-top:4px;}}
div[role="radiogroup"]{{gap:.25rem;flex-wrap:wrap;}}
div[role="radiogroup"] label{{background:rgba(5,17,31,.78);border:1px solid #405334;border-radius:9px;padding:.34rem .7rem;}}
div[role="radiogroup"] label:has(input:checked){{border-color:#D5F26D;background:rgba(213,242,109,.12);box-shadow:0 0 14px rgba(213,242,109,.08);}}
.sr-incident-board{{border:1px solid #768C45;border-radius:15px;padding:14px;background:linear-gradient(120deg,rgba(11,38,64,.96),rgba(4,14,27,.98));box-shadow:0 0 32px rgba(213,242,109,.08);margin:7px 0 12px;}}
.sr-incident-card{{border:1px solid #405334;border-radius:12px;padding:11px;background:rgba(4,17,31,.88);min-height:128px;}}
.sr-incident-card.active{{border-color:#F26457;box-shadow:0 0 20px rgba(242,100,87,.10);}}
.sr-incident-status{{display:inline-block;border-radius:999px;padding:3px 8px;font:9px 'JetBrains Mono';text-transform:uppercase;border:1px solid #405334;color:#B7C99D;margin-bottom:8px;}}
.sr-incident-status.active{{border-color:#F26457;color:#F58B81;background:rgba(242,100,87,.08);}}
.sr-incident-status.containment{{border-color:#768C45;color:#D5F26D;background:rgba(118,140,69,.08);}}
.sr-incident-status.monitoring{{border-color:#A9BF5A;color:#D5F26D;background:rgba(169,191,90,.08);}}
.sr-map-preview{{border:1px solid #D5F26D;border-radius:12px;padding:11px 13px;background:linear-gradient(100deg,rgba(213,242,109,.11),rgba(4,16,29,.96));margin:6px 0 10px;}}
.sr-decision-summary{{border:1px solid #768C45;border-radius:12px;padding:10px 12px;background:rgba(70,43,112,.17);margin:8px 0 12px;}}
.sr-chip{{display:inline-block;padding:5px 9px;border-radius:999px;border:1px solid #D5F26D;background:rgba(213,242,109,.08);color:#F2F6E8;font:9px 'JetBrains Mono';margin:4px 5px 2px 0;}}
.sr-chip.population{{border-color:#52A1BE;background:rgba(82,161,190,.10);}}
.sr-chip.traffic{{border-color:#768C45;background:rgba(118,140,69,.10);}}
.sr-chip.environment{{border-color:#A9BF5A;background:rgba(169,191,90,.10);}}
.sr-plan-count{{font-family:'Poppins';font-size:20px;font-weight:700;color:#D5F26D;}}
@media(max-width:900px){{.sr-ai-grid,.sr-receipt-grid,.sr-weather-grid,.sr-resource-grid{{grid-template-columns:1fr 1fr;}}}}


/* SkyRoute brand identity, legends and decision workflow */
.sr-brand-lockup,.sr-sidebar-brand{{display:flex;align-items:center;gap:14px;max-width:100%;}}
.sr-brand-icon{{height:54px;width:auto;object-fit:contain;flex:0 0 auto;filter:drop-shadow(0 0 10px rgba(213,242,109,.18));}}
.sr-brand-wordmark{{font-family:'Poppins',sans-serif;font-weight:700;letter-spacing:.13em;text-transform:uppercase;color:#D5F26D;font-size:38px;line-height:1;text-shadow:0 0 4px rgba(213,242,109,.48),0 0 10px rgba(213,242,109,.40),0 0 22px rgba(213,242,109,.22);}}
.sr-sidebar-brand{{margin:2px 0 8px;}}
.sr-sidebar-brand .sr-brand-icon{{height:48px;}}
.sr-sidebar-brand .sr-brand-wordmark{{font-size:28px;letter-spacing:.11em;}}
.sr-name{{color:#D5F26D;letter-spacing:.11em;text-transform:uppercase;text-shadow:0 0 8px rgba(213,242,109,.34);}}
.sr-h2{{color:#F2F6E8;}}
.sr-top{{border-color:#768C45;background:linear-gradient(135deg,rgba(24,39,29,.97),rgba(6,17,14,.99));}}
.sr-logo{{display:none;}}
.sr-map-info-anchor{{position:relative;height:0;z-index:999;pointer-events:none;}}
.sr-map-native-info-mask{{position:absolute;right:0;width:48px;height:48px;background:#06110E;border-top-left-radius:12px;pointer-events:none;z-index:1;}}
.sr-map-info-control{{position:absolute;right:12px;pointer-events:auto;z-index:2;}}
.sr-map-info-control summary{{list-style:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;cursor:pointer;background:rgba(5,15,28,.96);border:1px solid #FFFFFF;color:#FFFFFF;font:700 14px 'Poppins';box-shadow:0 0 13px rgba(255,255,255,.22),0 0 20px rgba(0,229,255,.11);user-select:none;}}
.sr-map-info-control summary::-webkit-details-marker{{display:none;}}
.sr-map-info-control summary:hover{{border-color:#00E5FF;color:#00E5FF;box-shadow:0 0 16px rgba(0,229,255,.42);}}
.sr-map-info-control[open] summary{{border-color:#00E5FF;color:#00E5FF;}}
.sr-map-info-panel{{position:absolute;right:0;bottom:38px;width:255px;border:1px solid #00E5FF;border-radius:10px;padding:10px 11px;background:rgba(4,13,24,.98);color:#DCE9F2;box-shadow:0 12px 34px rgba(0,0,0,.48),0 0 20px rgba(0,229,255,.12);font:9px 'JetBrains Mono';line-height:1.55;}}
.sr-map-info-panel b{{display:block;color:#FFFFFF;font:700 11px 'Poppins';margin-bottom:5px;}}
.sr-map-legend{{border:1px solid #405334;border-radius:12px;padding:10px 12px;background:rgba(6,17,14,.94);margin:7px 0 12px;}}
.sr-map-legend-title{{font-family:'Poppins';font-size:11px;font-weight:700;color:#D5F26D;margin-bottom:8px;text-transform:uppercase;letter-spacing:.08em;}}
.sr-map-legend-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:7px 12px;}}
.sr-map-legend-item{{display:flex;align-items:center;gap:8px;font-size:10px;color:#D6E2C6;line-height:1.3;}}
.sr-legend-symbol{{width:18px;height:18px;border-radius:5px;display:grid;place-items:center;font-size:13px;font-weight:700;border:1px solid rgba(242,246,232,.45);flex:0 0 18px;}}
.sr-legend-incident-icon,.sr-legend-map-icon{{width:18px;height:18px;display:block;object-fit:contain;filter:drop-shadow(0 0 5px rgba(213,242,109,.22));flex:0 0 18px;}}
.sr-workflow{{position:sticky;top:.7rem;border:1px solid #405334;border-radius:14px;padding:14px 11px;background:linear-gradient(180deg,rgba(8,19,15,.98),rgba(4,11,8,.98));box-shadow:0 0 28px rgba(213,242,109,.06);}}
.sr-workflow-title{{font:9px 'JetBrains Mono';color:#B7C99D;text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px;}}
.sr-workflow-item{{display:grid;grid-template-columns:32px 1fr;gap:9px;position:relative;min-height:58px;opacity:.42;}}
.sr-workflow-item:after{{content:'';position:absolute;left:15px;top:32px;bottom:-8px;width:1px;background:#405334;}}
.sr-workflow-item:last-child:after{{display:none;}}
.sr-workflow-item.done,.sr-workflow-item.active{{opacity:1;}}
.sr-workflow-dot{{width:26px;height:26px;border-radius:50%;border:1px solid #405334;background:#07110D;display:grid;place-items:center;font:10px 'JetBrains Mono';color:#B7C99D;z-index:2;}}
.sr-workflow-item.done .sr-workflow-dot{{border-color:#A9BF5A;color:#D5F26D;background:rgba(169,191,90,.12);}}
.sr-workflow-item.active .sr-workflow-dot{{border-color:#D5F26D;color:#06110E;background:#D5F26D;box-shadow:0 0 18px rgba(213,242,109,.55);}}
.sr-workflow-name{{font-family:'Poppins';font-size:11px;font-weight:700;color:#F2F6E8;margin-top:1px;}}
.sr-workflow-desc{{font:8px 'JetBrains Mono';color:#91A87A;line-height:1.35;margin-top:3px;}}
.sr-workflow-progress{{margin-top:8px;border-top:1px solid #405334;padding-top:9px;font:8px 'JetBrains Mono';color:#B7C99D;}}
.sr-live-case{{border:1px solid #D5F26D;border-radius:13px;padding:12px 14px;background:linear-gradient(110deg,rgba(213,242,109,.11),rgba(6,17,14,.97));box-shadow:0 0 24px rgba(213,242,109,.08);margin:7px 0 12px;}}
.sr-hospital-card{{border:1px solid #405334;border-radius:10px;padding:9px;background:rgba(8,19,14,.85);margin:6px 0;}}
.sr-hospital-card.available{{border-color:#A9BF5A;}}
.sr-hospital-card.limited{{border-color:#768C45;}}
.sr-hospital-card.full{{border-color:#F26457;}}
.sr-target-chip{{display:inline-flex;align-items:center;gap:6px;border:1px solid #405334;border-radius:999px;padding:4px 8px;font:9px 'JetBrains Mono';color:#D6E2C6;margin:3px 3px 0 0;}}
.sr-global-nav{{border:1px solid rgba(148,163,184,.18);border-radius:13px;padding:8px 10px;background:linear-gradient(180deg,rgba(7,18,27,.88),rgba(4,11,17,.92));margin:0 0 12px;box-shadow:0 10px 28px rgba(0,0,0,.18);}}
.sr-global-nav-label{{font:8px 'JetBrains Mono';color:#94A3B8;text-transform:uppercase;letter-spacing:.11em;margin-bottom:6px;}}
.sr-map-view-bar{{border:1px solid rgba(0,217,255,.18);border-radius:11px;padding:7px 10px;background:rgba(3,13,20,.72);margin:5px 0 11px;}}
.sr-map-view-bar .sr-small{{color:#A8BAC8;}}
.sr-agent-return{{border:1px solid rgba(213,242,109,.28);border-radius:11px;padding:8px 10px;background:rgba(213,242,109,.045);margin-bottom:10px;}}
.sr-map-legend-route{{display:inline-block;width:18px;height:4px;border-radius:999px;box-shadow:0 0 7px currentColor;}}
.sr-map-legend-area{{display:inline-block;width:18px;height:13px;border-radius:3px;border:1px solid rgba(255,255,255,.7);box-shadow:inset 0 0 0 2px rgba(0,0,0,.18);}}
@media(max-width:1000px){{.sr-workflow{{position:relative;top:auto}}.sr-brand-lockup{{gap:10px}}.sr-brand-icon{{height:44px}}.sr-brand-wordmark{{font-size:30px;letter-spacing:.10em}}.sr-sidebar-brand .sr-brand-wordmark{{font-size:24px;}}}}

</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# DOMAIN MODELS
# =============================================================================
@dataclass(frozen=True)
class Incident:
    id: str
    lat: float
    lon: float
    road: str
    substance: str
    threat: str
    quantity_t: float
    leak_rate_kg_min: float
    detected_at: str
    description: str


@dataclass(frozen=True)
class Resource:
    id: str
    name: str
    lat: float
    lon: float
    kind: str
    status: str
    units: int
    capacity: str


@dataclass
class RouteResult:
    id: str
    label: str
    path: List[List[float]]
    distance_km: float
    eta_min: float
    exposure_score: float
    environment_score: float
    congestion_score: float
    responder_risk: float
    composite_score: float
    backend: str
    explanation: str


@dataclass(frozen=True)
class DecisionOption:
    id: str
    category: str
    title: str
    summary: str
    implementation_min: int
    people_protected: int
    resource_need: str
    traffic_impact: str
    residual_risk: str
    confidence: float
    agent_reason: str
    map_effect: str


@dataclass(frozen=True)
class PreventiveAlert:
    id: str
    severity: str
    title: str
    corridor: str
    reason: str
    recommended_action: str
    risk_reduction: int
    delay_min: int
    cost_level: str
    path: List[List[float]]


# =============================================================================
# DEMONSTRATION DATA — NANJING JIANGBEI PILOT
# =============================================================================
THREAT_COLOR = {
    "CRITICAL": [255, 89, 94],
    "ELEVATED": [255, 159, 28],
    "MODERATE": [255, 209, 102],
}
STATUS_COLOR = {
    "Available": [0, 214, 143],
    "Requested": [255, 209, 102],
    "En route": [0, 196, 255],
    "On scene": [255, 255, 255],
    "Busy": [255, 89, 94],
    "Returning": [148, 163, 184],
}
# Operational map colors prioritize perceptual separation on a dark basemap.
# Agency identity is carried by both color and a geometric symbol, while status
# is communicated by the outer halo. This avoids relying on color alone.
AGENCY_COLOR = {
    "police": [0, 196, 255],       # cyan
    "fire": [255, 126, 34],        # orange
    "ambulance": [76, 111, 255],   # blue-violet
    "hazmat": [255, 45, 149],      # magenta
    "environment": [0, 214, 143],  # green
    "bus": [180, 106, 255],        # violet
    "sensor": [255, 209, 102],     # amber
}
ROUTE_OBJECTIVE_COLOR = {
    "recommended": [255, 255, 255],
    "fastest": [0, 217, 255],
    "safest": [0, 230, 160],
    "low_traffic": [255, 209, 102],
}
MAP_LINE_COLOR = {
    "road_closure": [255, 255, 255],
    "emergency_corridor": [255, 209, 102],
    "evacuation": [180, 106, 255],
    "hazmat_restricted": [255, 89, 94],
    "hazmat_bypass": [255, 45, 149],
    "environmental_containment": [0, 214, 143],
    "isolation": [255, 209, 102],
    "water": [0, 168, 255],
}
AGENCY_LABEL = {
    "police": "Traffic Police",
    "fire": "Fire & Rescue",
    "ambulance": "Emergency Medical",
    "hazmat": "HazMat Specialist",
    "environment": "Environmental Team",
    "bus": "Evacuation Bus",
    "sensor": "Mobile Sensor",
}
# Basic Unicode geometry is deliberately used instead of emoji. These symbols
# render consistently in PyDeck TextLayer on local and Streamlit Cloud builds.
# Short Latin badge labels are used on the map instead of emoji or rare
# Unicode glyphs. They render consistently in local PyDeck and Streamlit Cloud.
# The coloured marker identifies the agency; the white badge letter reinforces it.
AGENCY_GLYPH = {
    "police": "P",
    "fire": "F",
    "ambulance": "A",
    "hazmat": "H",
    "environment": "E",
    "bus": "B",
    "sensor": "S",
}
MAP_SYMBOL_GLYPH = {
    "incident": "!",
    "community": "C",
    "school": "K",
    "hospital": "+",
    "shelter": "R",
    "police": "P",
    "fire": "F",
    "ambulance": "A",
    "hazmat": "H",
    "environment": "E",
    "bus": "B",
    "sensor": "S",
    "roadblock": "X",
    "drain": "D",
    "truck": "T",
    "traffic_incident": "X",
    "water": "W",
    "protected": "Z",
    "target": "T",
}

# Compact neon operational markers rendered as self-contained PNG data URIs.
# Raster icons have intrinsic dimensions and are reliable in Streamlit Cloud.
MAP_ICON_DATA_URIS = {
    'incident': 'data:image/png;base64,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',
    'police': 'data:image/png;base64,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',
    'fire': 'data:image/png;base64,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',
    'ambulance': 'data:image/png;base64,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',
    'hospital': 'data:image/png;base64,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',
    'hazmat': 'data:image/png;base64,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',
    'environment': 'data:image/png;base64,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',
    'bus': 'data:image/png;base64,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',
    'sensor': 'data:image/png;base64,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',
    'school': 'data:image/png;base64,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',
    'shelter': 'data:image/png;base64,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',
}
MAP_ICON_MAPPINGS = {
    key: {"url": uri, "width": 64, "height": 64, "anchorX": 32, "anchorY": 32}
    for key, uri in MAP_ICON_DATA_URIS.items()
}
ALERT_ICON_DATA_URI = MAP_ICON_DATA_URIS["incident"]
ALERT_ICON_MAPPING = MAP_ICON_MAPPINGS["incident"]
INCIDENT_LEGEND_TOKEN = "__INCIDENT_ICON__"
GLYPH_TO_ICON_KEY = {
    "P": "police", "F": "fire", "A": "ambulance", "H": "hazmat",
    "+": "hospital", "B": "bus", "E": "environment", "S": "sensor",
    "K": "school", "R": "shelter",
}

INCIDENTS: List[Incident] = [
    Incident(
        "NJ-HZ-260717-01", 32.1628, 118.6906,
        "G2503/G2504 Jiangbei freight corridor", "Chlorine", "CRITICAL",
        18.0, 110.0, "14:32",
        "Tanker collision with continuing toxic gas release and traffic obstruction.",
    ),
    Incident(
        "NJ-HZ-260717-02", 32.1489, 118.7182,
        "Pukou Avenue logistics approach", "Ammonia", "ELEVATED",
        12.0, 65.0, "11:18",
        "Valve damage after low-speed rollover close to a logistics warehouse.",
    ),
    Incident(
        "NJ-HZ-260717-03", 32.1261, 118.7047,
        "Jiangbei industrial connector", "LNG", "ELEVATED",
        20.0, 48.0, "09:46",
        "Cryogenic cargo vehicle stopped after rear impact; vapour cloud suspected.",
    ),
    Incident(
        "NJ-HZ-260717-04", 32.1778, 118.7330,
        "Nanjing Ring Expressway access", "Gasoline", "MODERATE",
        24.0, 35.0, "07:20",
        "Fuel tanker side damage; runoff threat toward a stormwater inlet.",
    ),
    Incident(
        "HIST-2005-0329", 33.7330, 119.0830,
        "Beijing–Shanghai (Jinghu) Expressway · Huai'an section K103+300–K103+525",
        "Chlorine", "CRITICAL", 37.5, 240.0, "18:50",
        "Real-case live simulation of the 29 March 2005 liquid-chlorine tanker rollover and valve failure. Location and surrounding settlement coordinates are approximate for live-response decision-support simulation.",
    ),
]

SUBSTANCES: Dict[str, Dict[str, Any]] = {
    "Chlorine": {
        "hazard": "Toxic dense gas",
        "base_isolation_m": 300,
        "base_protective_m": 2200,
        "shelter_factor": 0.72,
        "environment": "Acidic solution may form in water; protect drains and surface water.",
    },
    "Ammonia": {
        "hazard": "Toxic and flammable gas",
        "base_isolation_m": 200,
        "base_protective_m": 1500,
        "shelter_factor": 0.65,
        "environment": "Highly soluble; runoff and water spray require specialist control.",
    },
    "LNG": {
        "hazard": "Flammable cryogenic gas",
        "base_isolation_m": 250,
        "base_protective_m": 900,
        "shelter_factor": 0.52,
        "environment": "Avoid direct water into spill; monitor vapour and ignition sources.",
    },
    "Gasoline": {
        "hazard": "Flammable liquid and vapour",
        "base_isolation_m": 100,
        "base_protective_m": 400,
        "shelter_factor": 0.45,
        "environment": "Block stormwater pathways and recover contaminated runoff.",
    },
}

POIS: List[Dict[str, Any]] = [
    {"id": "POI-S01", "name": "Jiangbei Experimental School", "lat": 32.1680, "lon": 118.6818, "type": "school", "base_pop": 1350, "vulnerability": 2.4, "buffer_m": 500},
    {"id": "POI-H01", "name": "Pukou District Hospital", "lat": 32.1542, "lon": 118.7023, "type": "hospital", "base_pop": 920, "vulnerability": 2.7, "buffer_m": 600, "bed_capacity": 420, "available_beds": 96, "hospital_status": "Available", "specialty": "Emergency and respiratory care"},
    {"id": "POI-R01", "name": "Jiangbei Residential Cluster A", "lat": 32.1570, "lon": 118.6800, "type": "residential", "base_pop": 4200, "vulnerability": 1.8, "buffer_m": 700},
    {"id": "POI-E01", "name": "Longshan Elder-Care Centre", "lat": 32.1740, "lon": 118.6990, "type": "eldercare", "base_pop": 280, "vulnerability": 3.0, "buffer_m": 500},
    {"id": "POI-P01", "name": "Jiangbei Central Park", "lat": 32.1435, "lon": 118.7115, "type": "park", "base_pop": 600, "vulnerability": 1.0, "buffer_m": 350},
    {"id": "POI-G01", "name": "Shuangta Fuel Station", "lat": 32.1640, "lon": 118.6925, "type": "fuel", "base_pop": 35, "vulnerability": 3.2, "buffer_m": 350},
    {"id": "POI-S02", "name": "Pukou Vocational School", "lat": 32.1450, "lon": 118.7240, "type": "school", "base_pop": 980, "vulnerability": 2.2, "buffer_m": 500},
    {"id": "POI-M01", "name": "Jiangbei Shopping Centre", "lat": 32.1602, "lon": 118.7120, "type": "commercial", "base_pop": 2100, "vulnerability": 1.4, "buffer_m": 500},
]

SHELTERS: List[Dict[str, Any]] = [
    {"id": "SH-01", "name": "Pukou Sports Hall", "lat": 32.1514, "lon": 118.6758, "capacity": 2600},
    {"id": "SH-02", "name": "Jiangbei Civic Centre", "lat": 32.1378, "lon": 118.7192, "capacity": 1900},
    {"id": "SH-03", "name": "Longshan Community Hall", "lat": 32.1842, "lon": 118.7141, "capacity": 1150},
]

RESOURCES: List[Resource] = [
    Resource("F-01", "Jiangbei Fire Station 1", 32.1445, 118.6840, "fire", "Available", 2, "2 engines + foam"),
    Resource("F-02", "Pukou Fire Station 3", 32.1780, 118.7110, "fire", "Busy", 1, "1 engine"),
    Resource("P-01", "Jiangbei Traffic Police Post", 32.1510, 118.7100, "police", "Available", 3, "3 patrol units"),
    Resource("P-02", "G2504 Expressway Police Unit", 32.1810, 118.6830, "police", "Available", 2, "2 patrol units"),
    Resource("A-01", "Pukou EMS Base", 32.1536, 118.7030, "ambulance", "Available", 4, "4 ambulances"),
    Resource("A-02", "Jiangbei Emergency Hospital", 32.1390, 118.7260, "ambulance", "Busy", 2, "2 ambulances"),
    Resource("H-01", "Municipal HazMat Unit 2", 32.1320, 118.6980, "hazmat", "Available", 1, "Level-A PPE + plugging kit"),
    Resource("H-02", "Chemical Park Specialist Team", 32.1930, 118.7420, "hazmat", "Available", 1, "Transfer + crane liaison"),
    Resource("E-01", "Ecology Monitoring Team", 32.1490, 118.7350, "environment", "Available", 1, "Mobile air/water laboratory"),
    Resource("B-01", "Jiangbei Bus Reserve", 32.1360, 118.6760, "bus", "Available", 16, "16 evacuation buses"),
    Resource("S-01", "Mobile Sensor Depot", 32.1830, 118.7240, "sensor", "Available", 4, "4 mobile air sensors"),
]

WATER_ZONES: List[Dict[str, Any]] = [
    {"id": "W-01", "name": "Yangtze tributary protection corridor", "polygon": [[118.671, 32.139], [118.678, 32.138], [118.712, 32.183], [118.704, 32.186], [118.671, 32.139]]},
    {"id": "W-02", "name": "Stormwater retention wetland", "polygon": [[118.715, 32.151], [118.727, 32.151], [118.727, 32.160], [118.715, 32.160], [118.715, 32.151]]},
]

# Dynamically populated from public OpenStreetMap environmental features.
# These are shown as a separate public-data layer and are not presented as the
# legally authoritative ecological-redline dataset.
PROTECTED_AREAS: List[Dict[str, Any]] = []
PROTECTED_AREA_SOURCE = "Public environmental layer not loaded"

DRAINS: List[Dict[str, Any]] = [
    {"id": "D-01", "name": "Storm inlet A", "lat": 32.1634, "lon": 118.6934},
    {"id": "D-02", "name": "Storm inlet B", "lat": 32.1601, "lon": 118.6968},
    {"id": "D-03", "name": "Retention inlet", "lat": 32.1552, "lon": 118.7159},
]

HAZMAT_CORRIDORS: List[Dict[str, Any]] = [
    {"id": "HC-A", "name": "Approved HazMat Corridor A", "path": [[118.661, 32.184], [118.676, 32.176], [118.690, 32.164], [118.707, 32.152], [118.732, 32.145]], "risk": "Medium"},
    {"id": "HC-B", "name": "Restricted urban segment", "path": [[118.680, 32.169], [118.697, 32.162], [118.711, 32.155], [118.724, 32.145]], "risk": "High"},
    {"id": "HC-C", "name": "Northern industrial bypass", "path": [[118.668, 32.190], [118.690, 32.184], [118.716, 32.180], [118.744, 32.176]], "risk": "Low"},
]

BASE_TRAFFIC_SEGMENTS: List[Dict[str, Any]] = [
    {"id": "T-01", "name": "G2504 west approach", "path": [[118.662, 32.183], [118.677, 32.175], [118.690, 32.164]], "free_speed": 80, "base_load": 0.50},
    {"id": "T-02", "name": "G2504 incident segment", "path": [[118.690, 32.164], [118.704, 32.156], [118.720, 32.149]], "free_speed": 80, "base_load": 0.72},
    {"id": "T-03", "name": "Pukou Avenue", "path": [[118.682, 32.149], [118.702, 32.151], [118.724, 32.145]], "free_speed": 60, "base_load": 0.63},
    {"id": "T-04", "name": "Northern industrial bypass", "path": [[118.670, 32.190], [118.693, 32.184], [118.716, 32.180], [118.742, 32.176]], "free_speed": 70, "base_load": 0.35},
    {"id": "T-05", "name": "Jiangbei urban connector", "path": [[118.681, 32.168], [118.691, 32.158], [118.700, 32.146], [118.707, 32.132]], "free_speed": 50, "base_load": 0.66},
]

ORDINARY_ACCIDENTS: List[Dict[str, Any]] = [
    {"id": "TA-17", "title": "Rear-end collision", "lat": 32.1706, "lon": 118.7052, "severity": "minor", "road": "G2504 northbound"},
    {"id": "TA-21", "title": "Disabled vehicle", "lat": 32.1504, "lon": 118.7135, "severity": "moderate", "road": "Pukou Avenue"},
]

HAZMAT_TRUCKS: List[Dict[str, Any]] = [
    {"id": "TR-201", "substance": "Ammonia", "lat": 32.1810, "lon": 118.6680, "route": "HC-A", "speed": 51},
    {"id": "TR-202", "substance": "Gasoline", "lat": 32.1730, "lon": 118.6830, "route": "HC-A", "speed": 47},
    {"id": "TR-203", "substance": "Chlorine", "lat": 32.1590, "lon": 118.7000, "route": "HC-B", "speed": 31},
    {"id": "TR-204", "substance": "LNG", "lat": 32.1830, "lon": 118.7070, "route": "HC-C", "speed": 58},
    {"id": "TR-205", "substance": "Gasoline", "lat": 32.1510, "lon": 118.7170, "route": "HC-B", "speed": 28},
]

SENSORS: List[Dict[str, Any]] = [
    {"id": "SN-01", "name": "Fixed air sensor A", "lat": 32.1660, "lon": 118.6980, "status": "Online"},
    {"id": "SN-02", "name": "School air sensor", "lat": 32.1681, "lon": 118.6822, "status": "Online"},
    {"id": "SN-03", "name": "Wetland water sensor", "lat": 32.1560, "lon": 118.7200, "status": "Online"},
]

# Preserve the original Nanjing demonstration datasets so selecting the
# historical case does not change or remove any existing scenario.
NANJING_CONTEXT = {
    "pois": copy.deepcopy(POIS),
    "shelters": copy.deepcopy(SHELTERS),
    "resources": copy.deepcopy(RESOURCES),
    "water_zones": copy.deepcopy(WATER_ZONES),
    "drains": copy.deepcopy(DRAINS),
    "hazmat_corridors": copy.deepcopy(HAZMAT_CORRIDORS),
    "traffic_segments": copy.deepcopy(BASE_TRAFFIC_SEGMENTS),
    "ordinary_accidents": copy.deepcopy(ORDINARY_ACCIDENTS),
    "hazmat_trucks": copy.deepcopy(HAZMAT_TRUCKS),
    "sensors": copy.deepcopy(SENSORS),
}

HISTORICAL_INCIDENT_ID = "HIST-2005-0329"

# Coordinates below are explicitly treated as reconstruction anchors. The
# accident coordinate follows the case summary; village and agency positions
# are operational map anchors used to test the agent's prioritisation and
# routing workflow, not cadastral or forensic coordinates.
HISTORICAL_POIS: List[Dict[str, Any]] = [
    {"id": "H-POI-GAODANG", "name": "Gaodang Village", "lat": 33.7310, "lon": 119.0795, "type": "village", "base_pop": 550, "vulnerability": 2.8, "buffer_m": 500, "historical_note": "Approximate village-centre anchor; the closest household was reported about 60 m from the leak."},
    {"id": "H-POI-ZHANGXIAOWEI", "name": "Zhangxiaowei Village", "lat": 33.7362, "lon": 119.0900, "type": "village", "base_pop": 720, "vulnerability": 2.1, "buffer_m": 550, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-YUANNAN", "name": "Yuannan Village", "lat": 33.7285, "lon": 119.0935, "type": "village", "base_pop": 680, "vulnerability": 2.1, "buffer_m": 550, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-XIAOCHEN", "name": "Xiaochenzhuang Village", "lat": 33.7410, "lon": 119.0968, "type": "village", "base_pop": 460, "vulnerability": 2.0, "buffer_m": 500, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-YUELAIJI", "name": "Yuelaiji Village", "lat": 33.7460, "lon": 119.1030, "type": "village", "base_pop": 850, "vulnerability": 2.0, "buffer_m": 600, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-ZHANGGUANDANG", "name": "Zhangguandang Village", "lat": 33.7240, "lon": 119.1010, "type": "village", "base_pop": 620, "vulnerability": 2.0, "buffer_m": 550, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-SHIQIAO", "name": "Shiqiao Village", "lat": 33.7185, "lon": 119.1090, "type": "village", "base_pop": 900, "vulnerability": 1.9, "buffer_m": 650, "historical_note": "Named in historical accounts as an affected settlement."},
    {"id": "H-POI-PLA82", "name": "PLA 82 Hospital", "lat": 33.5960, "lon": 119.0170, "type": "hospital", "base_pop": 850, "vulnerability": 2.7, "buffer_m": 600, "bed_capacity": 520, "available_beds": 118, "hospital_status": "Available", "specialty": "Emergency toxic-exposure and respiratory care", "historical_note": "Receiving hospital named in incident accounts."},
    {"id": "H-POI-PEOPLE", "name": "Huai'an People's Hospital", "lat": 33.5880, "lon": 119.0270, "type": "hospital", "base_pop": 1050, "vulnerability": 2.7, "buffer_m": 650, "bed_capacity": 680, "available_beds": 142, "hospital_status": "Available", "specialty": "Emergency medicine and mass-casualty reception", "historical_note": "Receiving hospital named in incident accounts."},
]

HISTORICAL_SHELTERS: List[Dict[str, Any]] = [
    {"id": "H-SH-01", "name": "Wangxing Township assembly area", "lat": 33.7120, "lon": 119.0650, "capacity": 3500},
    {"id": "H-SH-02", "name": "Jiang'an Township reception area", "lat": 33.7510, "lon": 119.1210, "capacity": 4200},
    {"id": "H-SH-03", "name": "Huaiyin urban reception centre", "lat": 33.6650, "lon": 119.0300, "capacity": 6500},
]

HISTORICAL_RESOURCES: List[Resource] = [
    Resource("H-F-01", "Huai'an Fire & Rescue Command Base", 33.6950, 119.0520, "fire", "Available", 29, "29 fire trucks · approximately 150 officers"),
    Resource("H-F-02", "Jiangsu Provincial Fire Reinforcement Base", 33.6150, 119.0300, "fire", "Available", 10, "10 additional fire trucks · approximately 90 officers"),
    Resource("H-P-01", "Jinghu Expressway Traffic Police Post", 33.7200, 119.0750, "police", "Available", 6, "Road closure + village warning units"),
    Resource("H-A-01", "PLA 82 Hospital EMS Base", 33.5960, 119.0170, "ambulance", "Available", 8, "Ambulances + chlorine-exposure triage"),
    Resource("H-H-01", "Jiangsu HazMat Response Base", 33.6400, 119.0550, "hazmat", "Available", 2, "Level-A suits + leak plugging"),
    Resource("H-E-01", "Huai'an Environmental Monitoring Station", 33.6700, 119.0700, "environment", "Available", 2, "Mobile air and agricultural-impact monitoring"),
    Resource("H-B-01", "Huaiyin Bus Mobilisation Depot", 33.7000, 119.0600, "bus", "Available", 24, "Evacuation buses"),
    Resource("H-S-01", "Mobile Chlorine Sensor Depot", 33.7120, 119.0780, "sensor", "Available", 6, "Portable chlorine sensors"),
]

HISTORICAL_WATER_ZONES: List[Dict[str, Any]] = [
    {"id": "H-W-01", "name": "Rural drainage and irrigation receptor", "polygon": [[119.087, 33.719], [119.097, 33.719], [119.103, 33.748], [119.094, 33.751], [119.087, 33.719]]},
    {"id": "H-W-02", "name": "Agricultural runoff receptor", "polygon": [[119.071, 33.724], [119.081, 33.721], [119.086, 33.739], [119.077, 33.742], [119.071, 33.724]]},
]

HISTORICAL_DRAINS: List[Dict[str, Any]] = [
    {"id": "H-D-01", "name": "Expressway drainage point", "lat": 33.7334, "lon": 119.0840},
    {"id": "H-D-02", "name": "Agricultural ditch receptor", "lat": 33.7280, "lon": 119.0910},
]

HISTORICAL_HAZMAT_CORRIDORS: List[Dict[str, Any]] = [
    {"id": "H-HC-A", "name": "Jinghu Expressway southbound approach", "path": [[119.030, 33.780], [119.055, 33.760], [119.083, 33.733], [119.110, 33.705]], "risk": "High"},
    {"id": "H-HC-B", "name": "Emergency access from Huaiyin", "path": [[119.035, 33.675], [119.055, 33.700], [119.083, 33.733]], "risk": "Medium"},
    {"id": "H-HC-C", "name": "Northern diversion corridor", "path": [[119.020, 33.790], [119.070, 33.775], [119.125, 33.750]], "risk": "Low"},
]

HISTORICAL_TRAFFIC_SEGMENTS: List[Dict[str, Any]] = [
    {"id": "H-T-01", "name": "Jinghu north approach", "path": [[119.030, 33.780], [119.058, 33.758], [119.083, 33.733]], "free_speed": 90, "base_load": 0.62},
    {"id": "H-T-02", "name": "Accident and closure segment", "path": [[119.070, 33.746], [119.083, 33.733], [119.100, 33.718]], "free_speed": 90, "base_load": 0.92},
    {"id": "H-T-03", "name": "Huaiyin emergency access", "path": [[119.035, 33.675], [119.055, 33.700], [119.083, 33.733]], "free_speed": 60, "base_load": 0.55},
    {"id": "H-T-04", "name": "Northern regional detour", "path": [[119.020, 33.790], [119.070, 33.775], [119.125, 33.750]], "free_speed": 70, "base_load": 0.38},
    {"id": "H-T-05", "name": "Village warning and evacuation access", "path": [[119.064, 33.710], [119.082, 33.732], [119.104, 33.746]], "free_speed": 45, "base_load": 0.58},
]

HISTORICAL_ORDINARY_ACCIDENTS: List[Dict[str, Any]] = [
    {"id": "H-TA-01", "title": "Expressway obstruction", "lat": 33.7330, "lon": 119.0830, "severity": "critical", "road": "Jinghu Expressway"},
]

HISTORICAL_HAZMAT_TRUCKS: List[Dict[str, Any]] = [
    {"id": "H-TR-01", "substance": "Chlorine", "lat": 33.7330, "lon": 119.0830, "route": "H-HC-A", "speed": 0},
]

HISTORICAL_SENSORS: List[Dict[str, Any]] = [
    {"id": "H-SN-01", "name": "Upwind mobile sensor · recommended", "lat": 33.7290, "lon": 119.0760, "status": "Proposed"},
    {"id": "H-SN-02", "name": "Gaodang warning sensor · recommended", "lat": 33.7327, "lon": 119.0823, "status": "Proposed"},
    {"id": "H-SN-03", "name": "Downwind mobile sensor · recommended", "lat": 33.7410, "lon": 119.0968, "status": "Proposed"},
]

HISTORICAL_ECO_AREAS: List[Dict[str, Any]] = [
    {"id": "H-ECO-01", "name": "Agricultural crop-impact zone", "polygon": [[119.080, 33.715], [119.113, 33.713], [119.119, 33.750], [119.092, 33.754], [119.080, 33.715]], "category": "Agricultural environmental receptor", "source": "Real-case live simulation", "planning_reference": True, "risk_weight": 0.0, "title": "Agricultural crop-impact zone", "details": "Illustrative environmental receptor based on reported crop and livestock impacts; not a legal boundary."},
]

HISTORICAL_CONTEXT = {
    "pois": HISTORICAL_POIS,
    "shelters": HISTORICAL_SHELTERS,
    "resources": HISTORICAL_RESOURCES,
    "water_zones": HISTORICAL_WATER_ZONES,
    "drains": HISTORICAL_DRAINS,
    "hazmat_corridors": HISTORICAL_HAZMAT_CORRIDORS,
    "traffic_segments": HISTORICAL_TRAFFIC_SEGMENTS,
    "ordinary_accidents": HISTORICAL_ORDINARY_ACCIDENTS,
    "hazmat_trucks": HISTORICAL_HAZMAT_TRUCKS,
    "sensors": HISTORICAL_SENSORS,
}

HISTORICAL_RECONSTRUCTION_STAGES: List[Dict[str, Any]] = [
    {
        "time": "18:50",
        "title": "T0 · Initial incomplete report",
        "known": "Tanker rollover and expressway obstruction reported. Cargo identity and leak magnitude are not yet confirmed.",
        "agent": "Geofence the incident, identify nearby settlements, request cargo verification, stage sensors and issue a precautionary community alert.",
        "historical": "The accident scene dominated the first response picture; historical accounts describe delayed and uneven warning to nearby villages.",
        "confidence": 0.34,
        "plume_length_m": 650,
        "plume_width_m": 320,
        "knowledge_factor": 0.32,
    },
    {
        "time": "19:00",
        "title": "T1 · Liquid chlorine confirmed",
        "known": "The cargo is confirmed as liquid chlorine and a large uncontrolled release is visible. Rural settlements are located immediately around the expressway.",
        "agent": "Rank Gaodang and the downwind villages as explicit protection destinations while HazMat teams continue to the tanker.",
        "historical": "Fire and police resources mobilised, but the nearby population did not receive a uniformly early, targeted warning.",
        "confidence": 0.71,
        "plume_length_m": 1500,
        "plume_width_m": 700,
        "knowledge_factor": 0.72,
    },
    {
        "time": "19:15",
        "title": "T2 · Toxic exposure reports",
        "known": "Residents report acrid odour, eye irritation and a visible green gas cloud. The affected direction can now be corrected with field observations.",
        "agent": "Recalculate destination priorities, send police and warning teams to the highest-ranked villages, position ambulances and buses outside the plume, and deploy cross-wind sensors.",
        "historical": "Evacuation expanded across multiple villages as poisoning became evident and the scale of the release was understood.",
        "confidence": 0.88,
        "plume_length_m": 2600,
        "plume_width_m": 1250,
        "knowledge_factor": 1.00,
    },
    {
        "time": "19:40",
        "title": "T3 · Regional escalation and road closure",
        "known": "The expressway segment is closed, casualty transport is increasing and the operation requires separate access for leak control, evacuation and medical transport.",
        "agent": "Continuously re-route each resource class: HazMat to the tanker, police and buses to villages, ambulances to receiving hospitals and monitoring teams across the plume edge.",
        "historical": "The response grew into a major multi-agency operation, with a long expressway closure and extensive evacuation.",
        "confidence": 0.93,
        "plume_length_m": 3800,
        "plume_width_m": 1800,
        "knowledge_factor": 1.10,
    },
]


def incident_context_bundle(incident: Incident) -> Dict[str, Any]:
    source = HISTORICAL_CONTEXT if incident.id == HISTORICAL_INCIDENT_ID else NANJING_CONTEXT
    return {key: copy.deepcopy(value) for key, value in source.items()}

HISTORICAL_CASES = pd.DataFrame([
    {"Case": "Jinghu Expressway Huai'an liquid-chlorine leak", "Place": "Jiangsu, China", "Year": 2005, "Hazard": "Overloaded liquid-chlorine tanker rollover and valve failure", "Lesson": "Destination prioritisation and targeted warning must begin before routing every resource toward the accident source."},
    {"Case": "Tianjin Port explosions", "Place": "China", "Year": 2015, "Hazard": "Mixed hazardous storage", "Lesson": "Inventory knowledge, separation and responder protection must be available before escalation."},
    {"Case": "Jilin chemical plant / Songhua River", "Place": "China", "Year": 2005, "Hazard": "Benzene river pollution", "Lesson": "Water protection and downstream communication must be command decisions, not afterthoughts."},
    {"Case": "Bhopal gas disaster", "Place": "India", "Year": 1984, "Hazard": "Methyl isocyanate", "Lesson": "Early warning, maintenance, public communication and protective-action readiness are decisive."},
    {"Case": "Graniteville chlorine release", "Place": "United States", "Year": 2005, "Hazard": "Chlorine rail release", "Lesson": "Rapid isolation, shelter instructions and responder PPE reduce exposure during the initial phase."},
])


# =============================================================================
# GENERIC GEOSPATIAL AND SCORING HELPERS
# =============================================================================
def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def dist_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6_371_000 * math.sqrt(x * x + y * y)


def path_distance_km(path: Sequence[Sequence[float]]) -> float:
    total = 0.0
    for a, b in zip(path[:-1], path[1:]):
        total += dist_m(a[1], a[0], b[1], b[0])
    return total / 1000


def current_population(poi: Dict[str, Any], hour: int, weekday: bool = True) -> int:
    kind = poi["type"]
    if kind == "school":
        multiplier = 1.0 if weekday and 7 <= hour <= 17 else 0.08
    elif kind == "hospital":
        multiplier = 1.05
    elif kind == "residential":
        multiplier = 1.30 if hour < 7 or hour >= 19 else 0.62
    elif kind == "village":
        multiplier = 1.0
    elif kind == "eldercare":
        multiplier = 0.95
    elif kind == "park":
        multiplier = 1.25 if 17 <= hour <= 21 else 0.45
    elif kind == "commercial":
        multiplier = 1.12 if 10 <= hour <= 21 else 0.15
    else:
        multiplier = 0.65
    return int(round(poi["base_pop"] * multiplier))


def make_circle_polygon(lat: float, lon: float, radius_m: float, points: int = 72) -> List[List[float]]:
    m_per_lat = 111_000
    m_per_lon = 111_000 * math.cos(math.radians(lat))
    polygon: List[List[float]] = []
    for i in range(points + 1):
        theta = 2 * math.pi * i / points
        polygon.append([lon + math.cos(theta) * radius_m / m_per_lon, lat + math.sin(theta) * radius_m / m_per_lat])
    return polygon


def make_plume_polygon(lat: float, lon: float, wind_dir_deg: float, length_m: float, width_m: float) -> List[List[float]]:
    theta = math.radians(90 - wind_dir_deg)
    dx = math.cos(theta) * length_m
    dy = math.sin(theta) * length_m
    px = -math.sin(theta) * width_m / 2
    py = math.cos(theta) * width_m / 2
    m_per_lon = 111_000 * math.cos(math.radians(lat))
    m_per_lat = 111_000

    def ll(x: float, y: float) -> List[float]:
        return [lon + x / m_per_lon, lat + y / m_per_lat]

    return [
        ll(-px * 0.15, -py * 0.15),
        ll(dx + px, dy + py),
        ll(dx - px, dy - py),
        ll(px * 0.15, py * 0.15),
        ll(-px * 0.15, -py * 0.15),
    ]


def wind_label(degrees: float) -> str:
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return labels[int((degrees % 360) / 45 + 0.5) % 8]


def interpolate_position(path: Sequence[Sequence[float]], progress: float) -> List[float]:
    if not path:
        return [118.6906, 32.1628]
    progress = clamp(progress, 0.0, 1.0)
    if progress >= 1:
        return list(path[-1])
    scaled = progress * (len(path) - 1)
    idx = int(math.floor(scaled))
    fraction = scaled - idx
    a = path[idx]
    b = path[min(idx + 1, len(path) - 1)]
    return [a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction]


def offset_curve(origin: Tuple[float, float], destination: Tuple[float, float], offset: float, points: int = 18) -> List[List[float]]:
    """Create a smooth demonstration route with visible turns instead of a straight line."""
    olat, olon = origin
    dlat, dlon = destination
    vx = dlon - olon
    vy = dlat - olat
    length = math.sqrt(vx * vx + vy * vy) or 1.0
    px = -vy / length
    py = vx / length
    result: List[List[float]] = []
    for i in range(points):
        t = i / (points - 1)
        wave = math.sin(math.pi * t) * offset + math.sin(3 * math.pi * t) * offset * 0.20
        stair = round(t * 5) / 5
        base_lon = olon + vx * stair
        base_lat = olat + vy * t
        result.append([base_lon + px * wave, base_lat + py * wave])
    result[0] = [olon, olat]
    result[-1] = [dlon, dlat]
    return result


def point_risk(lat: float, lon: float, active: Incident, plume_polygon: List[List[float]]) -> Tuple[float, float]:
    exposure = 0.0
    environment = 0.0
    for poi in POIS:
        d = max(80.0, dist_m(lat, lon, poi["lat"], poi["lon"]))
        exposure += poi["vulnerability"] * poi["base_pop"] / (d / 100 + 1)
    for water in [*WATER_ZONES, *PROTECTED_AREAS]:
        risk_weight = float(water.get("risk_weight", 1.0))
        if risk_weight <= 0:
            continue
        for p in water.get("polygon", []):
            d = max(50.0, dist_m(lat, lon, p[1], p[0]))
            # Official/simulated water receptors retain the strongest penalty;
            # public protected/wetland polygons add a meaningful avoidance cost.
            receptor_weight = 600 if water.get("source") != "OpenStreetMap public data" else 420
            environment += risk_weight * receptor_weight / (d / 100 + 1)
    if dist_m(lat, lon, active.lat, active.lon) < 900:
        exposure += 60
    return exposure / 40, environment / 25


def traffic_color(congestion: float) -> List[int]:
    if congestion < 0.40:
        return [0, 214, 143, 235]
    if congestion < 0.68:
        return [255, 209, 102, 240]
    return [255, 89, 94, 250]


def status_text(congestion: float) -> str:
    if congestion < 0.40:
        return "Free flow"
    if congestion < 0.68:
        return "Slow"
    return "Congested"


# =============================================================================
# COORDINATE CONVERSION AND OPTIONAL REAL DATA CONNECTORS
# =============================================================================
PI = math.pi
A = 6378245.0
EE = 0.00669342162296594323


def _out_of_china(lon: float, lat: float) -> bool:
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(x: float, y: float) -> float:
    result = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    result += (20 * math.sin(6 * x * PI) + 20 * math.sin(2 * x * PI)) * 2 / 3
    result += (20 * math.sin(y * PI) + 40 * math.sin(y / 3 * PI)) * 2 / 3
    result += (160 * math.sin(y / 12 * PI) + 320 * math.sin(y * PI / 30)) * 2 / 3
    return result


def _transform_lon(x: float, y: float) -> float:
    result = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    result += (20 * math.sin(6 * x * PI) + 20 * math.sin(2 * x * PI)) * 2 / 3
    result += (20 * math.sin(x * PI) + 40 * math.sin(x / 3 * PI)) * 2 / 3
    result += (150 * math.sin(x / 12 * PI) + 300 * math.sin(x / 30 * PI)) * 2 / 3
    return result


def wgs84_to_gcj02(lon: float, lat: float) -> Tuple[float, float]:
    if _out_of_china(lon, lat):
        return lon, lat
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlon = (dlon * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return lon + dlon, lat + dlat


def gcj02_to_wgs84(lon: float, lat: float) -> Tuple[float, float]:
    glon, glat = wgs84_to_gcj02(lon, lat)
    return lon * 2 - glon, lat * 2 - glat


def get_amap_key() -> str:
    try:
        return str(st.secrets.get("AMAP_KEY", "")) or os.getenv("AMAP_KEY", "")
    except Exception:
        return os.getenv("AMAP_KEY", "")


def get_ors_key() -> str:
    """Read the server-side OpenRouteService key without exposing it in HTML."""
    try:
        return (
            str(st.secrets.get("ORS_API_KEY", ""))
            or str(st.secrets.get("OPENROUTESERVICE_KEY", ""))
            or os.getenv("ORS_API_KEY", "")
            or os.getenv("OPENROUTESERVICE_KEY", "")
        )
    except Exception:
        return os.getenv("ORS_API_KEY", "") or os.getenv("OPENROUTESERVICE_KEY", "")


ORS_BASE_URL = os.getenv("ORS_BASE_URL", "http://localhost:8080/ors").rstrip("/")


def ors_is_local() -> bool:
    return ORS_BASE_URL.startswith("http://localhost") or ORS_BASE_URL.startswith("http://127.0.0.1")


@st.cache_data(ttl=10, show_spinner=False)
def fetch_ors_health() -> Dict[str, Any]:
    if requests is None:
        return {"ok": False, "status": "requests missing"}
    try:
        response = requests.get(f"{ORS_BASE_URL}/v2/health", timeout=4)
        payload = response.json() if response.content else {}
        return {"ok": response.ok and payload.get("status") == "ready", "status": payload.get("status", f"HTTP {response.status_code}")}
    except Exception as exc:
        return {"ok": False, "status": str(exc)}


def _normalise_ors_path(raw_coordinates: Any) -> List[List[float]]:
    path: List[List[float]] = []
    if not isinstance(raw_coordinates, list):
        return path
    for point in raw_coordinates:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            lon, lat = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            continue
        current = [lon, lat]
        if not path or current != path[-1]:
            path.append(current)
    return path


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ors_directions(
    key: str,
    coordinates: Tuple[Tuple[float, float], ...],
    profile: str = "driving-car",
    alternatives: int = 1,
    preference: str = "fastest",
    avoid_polygons_json: str = "",
    hazmat: bool = False,
) -> Dict[str, Any]:
    """Request full GeoJSON road geometry from OpenRouteService.

    ``coordinates`` are provided as ``(lon, lat)`` pairs. The public API returns
    a GeoJSON FeatureCollection whose LineString coordinates can be drawn by
    PyDeck without any interpolation or straight-line approximation.
    """
    if requests is None or len(coordinates) < 2:
        return {"ok": False, "error": "requests library unavailable or insufficient coordinates", "routes": []}
    if not key and not ors_is_local():
        return {"ok": False, "error": "Remote OpenRouteService requires an API key", "routes": []}

    safe_profile = profile if profile in {"driving-car", "driving-hgv"} else "driving-car"
    body: Dict[str, Any] = {
        "coordinates": [[float(lon), float(lat)] for lon, lat in coordinates],
        "instructions": False,
        "geometry_simplify": False,
        "preference": preference if preference in {"fastest", "shortest", "recommended"} else "fastest",
        "units": "m",
        "attributes": ["avgspeed", "detourfactor", "percentage"],
    }

    target_count = max(1, min(int(alternatives), 3))
    if target_count > 1 and len(coordinates) == 2:
        body["alternative_routes"] = {
            "target_count": target_count,
            "share_factor": 0.60,
            "weight_factor": 1.40,
        }

    options: Dict[str, Any] = {}
    if safe_profile == "driving-hgv":
        options = {
            "vehicle_type": "hgv",
            "profile_params": {
                "restrictions": {
                    "length": 12.0,
                    "width": 2.6,
                    "height": 4.0,
                    "axleload": 10.0,
                    "weight": 26.0,
                    "hazmat": bool(hazmat),
                }
            },
        }
    if avoid_polygons_json:
        try:
            options["avoid_polygons"] = json.loads(avoid_polygons_json)
        except Exception:
            pass
    if options:
        body["options"] = options

    headers = {
        "Accept": "application/geo+json, application/json",
        "Content-Type": "application/json",
    }
    if key:
        headers["Authorization"] = key
    url = f"{ORS_BASE_URL}/v2/directions/{safe_profile}/geojson"
    try:
        response = requests.post(url, json=body, headers=headers, timeout=60 if ors_is_local() else 22)
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if response.status_code >= 400:
            error = ""
            if isinstance(payload, dict):
                err_obj = payload.get("error")
                if isinstance(err_obj, dict):
                    error = str(err_obj.get("message") or err_obj.get("code") or "")
                elif err_obj:
                    error = str(err_obj)
            return {"ok": False, "error": error or f"OpenRouteService HTTP {response.status_code}", "routes": []}

        parsed: List[Dict[str, Any]] = []
        for index, feature in enumerate((payload or {}).get("features", []) or []):
            geometry = feature.get("geometry") or {}
            path = _normalise_ors_path(geometry.get("coordinates"))
            if len(path) < 2:
                continue
            properties = feature.get("properties") or {}
            summary = properties.get("summary") or {}
            parsed.append({
                "id": f"ORS-{index}",
                "path": path,
                "distance_km": round(float(summary.get("distance", 0) or 0) / 1000, 2),
                "eta_min": round(float(summary.get("duration", 0) or 0) / 60, 1),
                "profile": safe_profile,
                "attribution": ((payload or {}).get("metadata") or {}).get("attribution", "openrouteservice / OpenStreetMap"),
            })
        if not parsed:
            return {"ok": False, "error": "OpenRouteService returned no usable GeoJSON LineString", "routes": []}
        return {"ok": True, "error": "", "routes": parsed}
    except Exception as exc:  # pragma: no cover - external API
        return {"ok": False, "error": str(exc), "routes": []}


@st.cache_data(ttl=1800, show_spinner=False)
def ors_street_path_through_control_points(
    key: str,
    control_points: Tuple[Tuple[float, float], ...],
    profile: str = "driving-car",
    hazmat: bool = False,
) -> List[List[float]]:
    """Snap a sequence of lon/lat control points to the ORS road network."""
    if (not key and not ors_is_local()) or len(control_points) < 2:
        return []
    result = fetch_ors_directions(
        key,
        control_points,
        profile=profile,
        alternatives=1,
        preference="fastest",
        hazmat=hazmat,
    )
    if not result.get("ok") and profile == "driving-hgv":
        result = fetch_ors_directions(
            key,
            control_points,
            profile="driving-car",
            alternatives=1,
            preference="fastest",
            hazmat=False,
        )
    routes = result.get("routes", []) if result.get("ok") else []
    return routes[0]["path"] if routes else []


def _ring_bbox(ring: Sequence[Sequence[float]]) -> Optional[Tuple[float, float, float, float]]:
    points = [(float(p[0]), float(p[1])) for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
    if len(points) < 4:
        return None
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return min(lons), min(lats), max(lons), max(lats)


def _bbox_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def ors_environment_avoid_geometry(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
) -> str:
    """Build a compact GeoJSON MultiPolygon from mapped protected areas.

    Planning-reference polygons are deliberately excluded because they are
    schematic, not legal boundaries. Only public mapped polygons near the
    route corridor are sent to ORS.
    """
    olat, olon = origin
    dlat, dlon = destination
    route_bbox = (
        min(olon, dlon) - 0.025,
        min(olat, dlat) - 0.025,
        max(olon, dlon) + 0.025,
        max(olat, dlat) + 0.025,
    )
    polygons: List[List[List[List[float]]]] = []
    for area in PROTECTED_AREAS:
        if area.get("planning_reference"):
            continue
        ring = area.get("polygon") or []
        bbox = _ring_bbox(ring)
        if bbox is None or not _bbox_overlap(route_bbox, bbox):
            continue
        # Keep requests compact while preserving polygon shape.
        step = max(1, len(ring) // 70)
        simplified = [[float(p[0]), float(p[1])] for p in ring[::step] if len(p) >= 2]
        if len(simplified) < 4:
            continue
        if simplified[0] != simplified[-1]:
            simplified.append(simplified[0])
        polygons.append([simplified])
        if len(polygons) >= 12:
            break
    if not polygons:
        return ""
    return json.dumps({"type": "MultiPolygon", "coordinates": polygons}, separators=(",", ":"))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_amap_circle_traffic(key: str, lon: float, lat: float, radius: int = 4500) -> Dict[str, Any]:
    if not key or requests is None:
        return {"ok": False, "error": "AMap key or requests library unavailable", "roads": []}
    glon, glat = wgs84_to_gcj02(lon, lat)
    url = "https://restapi.amap.com/v3/traffic/status/circle"
    params = {
        "key": key,
        "location": f"{glon:.6f},{glat:.6f}",
        "radius": min(radius, 4999),
        "level": 5,
        "extensions": "all",
        "output": "JSON",
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        payload = response.json()
        if str(payload.get("status")) != "1":
            return {"ok": False, "error": payload.get("info", "AMap request failed"), "roads": []}
        trafficinfo = payload.get("trafficinfo", {})
        roads_out: List[Dict[str, Any]] = []
        for idx, road in enumerate(trafficinfo.get("roads", []) or []):
            raw = road.get("polyline", "")
            path: List[List[float]] = []
            for pair in raw.split(";"):
                if "," not in pair:
                    continue
                x, y = pair.split(",", 1)
                wlon, wlat = gcj02_to_wgs84(float(x), float(y))
                path.append([wlon, wlat])
            if len(path) < 2:
                continue
            amap_status = int(road.get("status", 0) or 0)
            congestion = {0: 0.50, 1: 0.25, 2: 0.58, 3: 0.88}.get(amap_status, 0.50)
            roads_out.append({
                "id": f"AMAP-{idx}",
                "name": road.get("name") or "AMap road segment",
                "path": path,
                "speed": float(road.get("speed", 0) or 0),
                "congestion": congestion,
                "status_text": {0: "Unknown", 1: "Free flow", 2: "Slow", 3: "Congested"}.get(amap_status, "Unknown"),
                "source": "AMap live",
            })
        return {
            "ok": True,
            "description": trafficinfo.get("description", ""),
            "evaluation": trafficinfo.get("evaluation", {}),
            "roads": roads_out,
        }
    except Exception as exc:  # pragma: no cover - external API
        return {"ok": False, "error": str(exc), "roads": []}


@st.cache_data(ttl=180, show_spinner=False)
def fetch_amap_driving_route(key: str, origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[Dict[str, Any]]:
    if not key or requests is None:
        return None
    olat, olon = origin
    dlat, dlon = destination
    oglon, oglat = wgs84_to_gcj02(olon, olat)
    dglon, dglat = wgs84_to_gcj02(dlon, dlat)
    url = "https://restapi.amap.com/v5/direction/driving"
    params = {
        "key": key,
        "origin": f"{oglon:.6f},{oglat:.6f}",
        "destination": f"{dglon:.6f},{dglat:.6f}",
        "show_fields": "cost,polyline,tmcs",
        "strategy": 32,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        payload = response.json()
        route = payload.get("route") or {}
        paths = route.get("paths") or []
        if not paths:
            return None
        selected = paths[0]
        path_out: List[List[float]] = []
        for step in selected.get("steps", []) or []:
            for pair in str(step.get("polyline", "")).split(";"):
                if "," not in pair:
                    continue
                x, y = pair.split(",", 1)
                wlon, wlat = gcj02_to_wgs84(float(x), float(y))
                point = [wlon, wlat]
                if not path_out or point != path_out[-1]:
                    path_out.append(point)
        if len(path_out) < 2:
            return None
        cost = selected.get("cost", {}) or {}
        duration_s = float(cost.get("duration", 0) or selected.get("duration", 0) or 0)
        distance_m = float(selected.get("distance", 0) or 0)
        return {
            "path": path_out,
            "distance_km": round(distance_m / 1000, 2),
            "eta_min": round(duration_s / 60, 1),
        }
    except Exception:  # pragma: no cover - external API
        return None


@st.cache_resource(show_spinner=False)
def load_osm_graph() -> Any:
    """Load one connected drivable network for the whole pilot area.

    A connected ``drive`` graph is intentional here. The previous
    ``drive_service`` + ``retain_all=True`` graph could snap two points to
    different disconnected service-road components, causing the real route to
    fail and leaving only the synthetic overview lines visible.
    """
    if not OSMNX_AVAILABLE:
        return None
    try:
        ox.settings.requests_timeout = 120
        ox.settings.use_cache = True
        all_lats = [item.lat for item in INCIDENTS] + [item.lat for item in RESOURCES]
        all_lons = [item.lon for item in INCIDENTS] + [item.lon for item in RESOURCES]
        margin = 0.040
        bbox = (min(all_lons) - margin, min(all_lats) - margin, max(all_lons) + margin, max(all_lats) + margin)
        try:
            graph = ox.graph.graph_from_bbox(
                bbox=bbox,
                network_type="drive",
                simplify=True,
                retain_all=False,
                truncate_by_edge=True,
            )
        except TypeError:  # OSMnx 1.x compatibility
            west, south, east, north = bbox
            graph = ox.graph_from_bbox(
                north,
                south,
                east,
                west,
                network_type="drive",
                simplify=True,
                retain_all=False,
                truncate_by_edge=True,
            )
        try:
            graph = ox.routing.add_edge_speeds(graph, fallback=40)
            graph = ox.routing.add_edge_travel_times(graph)
        except AttributeError:  # OSMnx 1.x compatibility
            graph = ox.add_edge_speeds(graph, fallback=40)
            graph = ox.add_edge_travel_times(graph)
        return graph
    except Exception:
        return None


OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_osrm_driving_routes(
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    alternatives: int = 3,
) -> List[Dict[str, Any]]:
    """Return full-resolution routes snapped to the public OSM road network."""
    if requests is None:
        return []
    olat, olon = origin
    dlat, dlon = destination
    url = f"{OSRM_BASE_URL}/route/v1/driving/{olon:.6f},{olat:.6f};{dlon:.6f},{dlat:.6f}"
    params = {
        "alternatives": max(1, min(int(alternatives), 3)),
        "steps": "false",
        "geometries": "geojson",
        "overview": "full",
        "continue_straight": "default",
    }
    try:
        response = requests.get(url, params=params, timeout=18)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok":
            return []
        output: List[Dict[str, Any]] = []
        for route in payload.get("routes", []) or []:
            geometry = (route.get("geometry") or {}).get("coordinates") or []
            path = [[float(point[0]), float(point[1])] for point in geometry if len(point) >= 2]
            if len(path) < 2:
                continue
            output.append({
                "path": path,
                "distance_km": round(float(route.get("distance", 0) or 0) / 1000, 2),
                "eta_min": round(float(route.get("duration", 0) or 0) / 60, 1),
            })
        return output
    except Exception:
        return []


def planning_reference_ecological_areas() -> List[Dict[str, Any]]:
    """Coarse visual references digitised from the public Pukou 2021-2035 plan.

    These are explicitly schematic references, not statutory parcel boundaries.
    They keep the environmental layer visible if the live OSM/Overpass request
    is unavailable during a presentation.
    """
    source = "Pukou Territorial Spatial Master Plan 2021-2035 - schematic reference, not a legal boundary"
    return [
        {
            "id": "PLAN-ECO-LAOSHAN",
            "name": "Laoshan ecological core - planning reference",
            "polygon": [
                [118.626, 32.145], [118.645, 32.128], [118.677, 32.126],
                [118.704, 32.145], [118.705, 32.170], [118.683, 32.193],
                [118.650, 32.198], [118.628, 32.178], [118.626, 32.145],
            ],
            "category": "Ecological core planning reference",
            "source": source,
            "planning_reference": True,
            "risk_weight": 0.0,
            "title": "Laoshan ecological core - planning reference",
            "details": f"Schematic ecological protection reference<br/>Source: {source}",
        },
        {
            "id": "PLAN-ECO-YANGTZE",
            "name": "Yangtze green ecological belt - planning reference",
            "polygon": [
                [118.729, 32.112], [118.746, 32.111], [118.760, 32.142],
                [118.760, 32.188], [118.748, 32.202], [118.739, 32.174],
                [118.734, 32.140], [118.729, 32.112],
            ],
            "category": "Green ecological belt planning reference",
            "source": source,
            "planning_reference": True,
            "risk_weight": 0.0,
            "title": "Yangtze green ecological belt - planning reference",
            "details": f"Schematic riverfront ecological corridor<br/>Source: {source}",
        },
    ]


def _geometry_polygons(geometry: Any) -> List[List[List[float]]]:
    """Convert Shapely Polygon/MultiPolygon geometry to pydeck rings."""
    if geometry is None or getattr(geometry, "is_empty", True):
        return []
    try:
        geometry = geometry.simplify(0.000025, preserve_topology=True)
    except Exception:
        pass
    kind = getattr(geometry, "geom_type", "")
    polygons = [geometry] if kind == "Polygon" else list(getattr(geometry, "geoms", [])) if kind == "MultiPolygon" else []
    result: List[List[List[float]]] = []
    for polygon in polygons:
        try:
            ring = [[float(x), float(y)] for x, y in polygon.exterior.coords]
        except Exception:
            continue
        if len(ring) >= 4:
            result.append(ring)
    return result


@st.cache_data(ttl=86_400, show_spinner=False)
def load_public_protected_areas(center_lat: float = 32.160, center_lon: float = 118.704, include_plan_references: bool = True) -> Tuple[List[Dict[str, Any]], str]:
    """Load designated protected areas and wetlands from public OSM data.

    This layer complements the simulated water receptors. It deliberately does
    not label OSM polygons as the authoritative statutory ecological redline.
    """
    if not OSMNX_AVAILABLE or ox is None:
        references = planning_reference_ecological_areas() if include_plan_references else []
        return references, "Public planning references shown; install OSMnx for live OSM protected-area polygons"
    tags = {
        "boundary": "protected_area",
        "leisure": "nature_reserve",
        "natural": "wetland",
        "landuse": "conservation",
    }
    try:
        if hasattr(ox, "features_from_point"):
            gdf = ox.features_from_point((center_lat, center_lon), tags=tags, dist=18_000)
        else:
            gdf = ox.features.features_from_point((center_lat, center_lon), tags=tags, dist=18_000)
    except Exception:
        references = planning_reference_ecological_areas() if include_plan_references else []
        return references, "Public planning references shown; live OSM environmental query unavailable"

    areas: List[Dict[str, Any]] = []
    seen: set = set()
    for index, row in gdf.iterrows():
        geometry = row.get("geometry")
        rings = _geometry_polygons(geometry)
        if not rings:
            continue
        name = row.get("name:en") or row.get("name") or row.get("protection_title") or "Mapped ecological protection area"
        if row.get("boundary") == "protected_area":
            category = "Protected area"
        elif row.get("leisure") == "nature_reserve":
            category = "Nature reserve"
        elif row.get("natural") == "wetland":
            category = "Wetland"
        else:
            category = "Conservation land"
        protect_class = row.get("protect_class")
        for ring_index, ring in enumerate(rings):
            key = (str(index), ring_index)
            if key in seen:
                continue
            seen.add(key)
            details = f"{category}<br/>Source: OpenStreetMap public data"
            if protect_class and str(protect_class) != "nan":
                details += f"<br/>Protection class: {protect_class}"
            areas.append({
                "id": f"OSM-ECO-{len(areas)+1}",
                "name": str(name),
                "polygon": ring,
                "category": category,
                "source": "OpenStreetMap public data",
                "title": str(name),
                "details": details,
            })
            if len(areas) >= 120:
                break
        if len(areas) >= 120:
            break
    references = planning_reference_ecological_areas() if include_plan_references else []
    areas.extend(references)
    label = f"OpenStreetMap public data · {len(areas) - len(references)} protected/wetland polygon(s) + {len(references)} public-plan reference zone(s)"
    return areas, label


# =============================================================================
# SIMULATION, TRAFFIC, ROUTING AND DECISION ENGINE
# =============================================================================

def build_live_pois(hour: int, weekday: bool) -> List[Dict[str, Any]]:
    result = []
    colors = {
        "school": [255, 209, 102],
        "hospital": [0, 168, 255],
        "residential": [255, 159, 28],
        "village": [255, 159, 28],
        "eldercare": [180, 106, 255],
        "park": [0, 214, 143],
        "fuel": [255, 89, 94],
        "commercial": [148, 163, 184],
    }
    glyphs = {
        "school": MAP_SYMBOL_GLYPH["school"],
        "hospital": MAP_SYMBOL_GLYPH["hospital"],
        "residential": MAP_SYMBOL_GLYPH["community"],
        "village": MAP_SYMBOL_GLYPH["community"],
        "eldercare": MAP_SYMBOL_GLYPH["community"],
        "park": MAP_SYMBOL_GLYPH["environment"],
        "fuel": MAP_SYMBOL_GLYPH["hazmat"],
        "commercial": MAP_SYMBOL_GLYPH["target"],
    }
    for poi in POIS:
        pop = current_population(poi, hour, weekday)
        hospital_extra = ""
        if poi.get("type") == "hospital":
            hospital_extra = (
                f"<br/>Beds available: {int(poi.get('available_beds', 0))}"
                f"<br/>Status: {poi.get('hospital_status', 'Available')}"
                f"<br/>{poi.get('specialty', 'Emergency care')}"
            )
        result.append({
            **poi,
            "population_now": pop,
            "color": colors.get(poi["type"], [213, 242, 109]) + [235],
            "buffer_color": colors.get(poi["type"], [213, 242, 109]) + [22],
            "buffer_line_color": colors.get(poi["type"], [213, 242, 109]) + [150],
            "glyph": glyphs.get(poi["type"], "●"),
            "title": poi["name"],
            "details": (
                f"Type: {poi['type']}<br/>Estimated people now: {pop:,}"
                f"<br/>Vulnerability: {poi['vulnerability']:.1f}"
                + hospital_extra
                + (f"<br/>{poi.get('historical_note')}" if poi.get('historical_note') else "")
            ),
        })
    return result

def build_demo_traffic(tick: int, traffic_index: float, rain_mm_h: float, road_wetness: float, active: Incident) -> List[Dict[str, Any]]:
    """Apply simulated traffic values only to real street geometries.

    The control points in ``BASE_TRAFFIC_SEGMENTS`` define the intended road
    corridor, but are never drawn directly. Each corridor is first routed
    through the OSM/OSRM street network. If street geometry is unavailable, the
    segment is omitted instead of drawing a line through blocks.
    """
    output: List[Dict[str, Any]] = []
    for idx, segment in enumerate(BASE_TRAFFIC_SEGMENTS):
        road_path = segment.get("path", []) if segment.get("street_snapped") else street_path_through_control_points(segment.get("path", []))
        if len(road_path) < 2:
            continue
        wave = math.sin((tick + idx * 2.2) / 3.0) * 0.08
        incident_effect = 0.26 if segment["id"] == "T-02" and active.id == "NJ-HZ-260717-01" else 0.0
        weather_effect = min(0.18, rain_mm_h / 250 + road_wetness * 0.08)
        global_effect = traffic_index / 10 * 0.22
        congestion = clamp(segment["base_load"] + wave + incident_effect + weather_effect + global_effect - 0.11, 0.05, 0.98)
        speed = max(7.0, segment["free_speed"] * (1 - congestion * 0.78))
        output.append({
            **segment,
            "control_path": segment["path"],
            "path": road_path,
            "congestion": congestion,
            "speed": round(speed, 0),
            "color": traffic_color(congestion),
            "status_text": status_text(congestion),
            "source": f"Simulated values on {segment.get('geometry_backend', 'real street')} geometry",
            "title": segment["name"],
            "details": f"{status_text(congestion)}<br/>Average speed: {speed:.0f} km/h<br/>Geometry: {segment.get('geometry_backend', 'real street network')}",
        })
    return output


def combined_traffic_source(
    data_mode: str,
    amap_key: str,
    tick: int,
    traffic_index: float,
    rain_mm_h: float,
    road_wetness: float,
    active: Incident,
) -> Tuple[List[Dict[str, Any]], str]:
    if data_mode.startswith("AMap") and amap_key:
        live = fetch_amap_circle_traffic(amap_key, active.lon, active.lat)
        if live.get("ok") and live.get("roads"):
            roads = live["roads"]
            for road in roads:
                road["color"] = traffic_color(road["congestion"])
                road["title"] = road["name"]
                road["details"] = f"{road['status_text']}<br/>Average speed: {road['speed']:.0f} km/h<br/>Source: AMap live"
            return roads, f"AMap live · {live.get('description', 'traffic query') or 'traffic query'}"
        demo = build_demo_traffic(tick, traffic_index, rain_mm_h, road_wetness, active)
        return demo, f"AMap unavailable, fallback to simulation: {live.get('error', 'no detailed roads returned')}"
    return build_demo_traffic(tick, traffic_index, rain_mm_h, road_wetness, active), "Simulated live data"


def _distance_to_path_m(lat: float, lon: float, path: List[List[float]]) -> float:
    if not path:
        return 99_999.0
    step = max(1, len(path) // 20)
    return min(dist_m(lat, lon, point[1], point[0]) for point in path[::step])


def route_risk_metrics(path: List[List[float]], active: Incident, traffic: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    exposure_values: List[float] = []
    environment_values: List[float] = []
    congestion_values: List[float] = []
    sample_step = max(1, len(path) // 18)
    for lon, lat in path[::sample_step]:
        exposure, environment = point_risk(lat, lon, active, [])
        exposure_values.append(exposure)
        environment_values.append(environment)
        if traffic:
            weighted: List[Tuple[float, float]] = []
            for segment in traffic:
                distance = _distance_to_path_m(lat, lon, segment.get("path", []))
                weight = math.exp(-distance / 850.0)
                weighted.append((float(segment.get("congestion", 0.45)), weight))
            denominator = sum(weight for _, weight in weighted) or 1.0
            congestion_values.append(sum(value * weight for value, weight in weighted) / denominator)
    exposure_score = float(np.mean(exposure_values)) if exposure_values else 0.0
    environment_score = float(np.mean(environment_values)) if environment_values else 0.0
    congestion_score = (float(np.mean(congestion_values)) if congestion_values else 0.40) * 10
    responder_risk = exposure_score * 0.34 + congestion_score * 0.55
    return exposure_score, environment_score, congestion_score, responder_risk


def route_result_from_path(
    route_id: str,
    label: str,
    path: List[List[float]],
    active: Incident,
    traffic: List[Dict[str, Any]],
    backend: str,
    explanation: str,
    speed_factor: float = 1.0,
) -> RouteResult:
    distance_km = max(0.3, path_distance_km(path))
    exposure, environment, congestion, responder = route_risk_metrics(path, active, traffic)
    congestion_ratio = clamp(congestion / 10, 0.0, 0.95)
    avg_speed = max(13, 56 * speed_factor * (1 - congestion_ratio * 0.42))
    eta_min = distance_km / avg_speed * 60 + 1.8
    composite = eta_min * 0.33 + exposure * 0.30 + environment * 0.18 + congestion * 0.10 + responder * 0.09
    return RouteResult(
        id=route_id,
        label=label,
        path=path,
        distance_km=round(distance_km, 2),
        eta_min=round(eta_min, 1),
        exposure_score=round(exposure, 1),
        environment_score=round(environment, 1),
        congestion_score=round(congestion, 1),
        responder_risk=round(responder, 1),
        composite_score=round(composite, 1),
        backend=backend,
        explanation=explanation,
    )


def _line_geometry_coordinates(geometry: Any) -> List[List[float]]:
    """Flatten LineString/MultiLineString edge geometry into lon/lat points."""
    if geometry is None:
        return []
    kind = getattr(geometry, "geom_type", "")
    if kind == "LineString":
        return [[float(x), float(y)] for x, y in geometry.coords]
    if kind == "MultiLineString":
        output: List[List[float]] = []
        for part in geometry.geoms:
            coordinates = [[float(x), float(y)] for x, y in part.coords]
            if output and coordinates and output[-1] == coordinates[0]:
                coordinates = coordinates[1:]
            output.extend(coordinates)
        return output
    return []


def osm_nodes_to_path(graph: Any, nodes: List[Any]) -> List[List[float]]:
    """Convert a route to full edge geometry so the line follows road curves."""
    if not nodes:
        return []
    try:
        edges = ox.routing.route_to_gdf(graph, nodes, weight="travel_time")
        path: List[List[float]] = []
        for geometry in edges.geometry:
            coordinates = _line_geometry_coordinates(geometry)
            if path and coordinates:
                d_start = dist_m(path[-1][1], path[-1][0], coordinates[0][1], coordinates[0][0])
                d_end = dist_m(path[-1][1], path[-1][0], coordinates[-1][1], coordinates[-1][0])
                if d_end < d_start:
                    coordinates.reverse()
            if path and coordinates and path[-1] == coordinates[0]:
                coordinates = coordinates[1:]
            path.extend(coordinates)
        if len(path) >= 2:
            return path
    except Exception:
        pass
    return [[float(graph.nodes[node]["x"]), float(graph.nodes[node]["y"])] for node in nodes]


def _edge_payload(edge_data: Dict[str, Any]) -> Dict[str, Any]:
    if not edge_data:
        return {}
    if 0 in edge_data and isinstance(edge_data[0], dict):
        return edge_data[0]
    first = next(iter(edge_data.values()), {})
    return first if isinstance(first, dict) else edge_data


def _traffic_penalty_for_node(graph: Any, node_id: Any, traffic: List[Dict[str, Any]]) -> float:
    node = graph.nodes[node_id]
    lat, lon = float(node.get("y", 0)), float(node.get("x", 0))
    scores = []
    for segment in traffic:
        distance = _distance_to_path_m(lat, lon, segment.get("path", []))
        scores.append(float(segment.get("congestion", 0.45)) * math.exp(-distance / 900.0))
    return max(scores, default=0.35)


def osm_route(resource: Resource, active: Incident, objective: str, traffic: List[Dict[str, Any]]) -> Optional[RouteResult]:
    graph = load_osm_graph()
    if graph is None or nx is None or ox is None:
        return None
    try:
        origin_node = ox.distance.nearest_nodes(graph, resource.lon, resource.lat)
        destination_node = ox.distance.nearest_nodes(graph, active.lon, active.lat)

        if objective == "fastest":
            nodes = ox.routing.shortest_path(graph, origin_node, destination_node, weight="travel_time")
            label = "Fastest street route"
            explanation = "Actual OpenStreetMap road geometry, minimizing estimated travel time."
            factor = 1.02
        elif objective == "safest":
            def safe_weight(u: Any, v: Any, edge_data: Dict[str, Any]) -> float:
                edge = _edge_payload(edge_data)
                base = float(edge.get("travel_time", 30) or 30)
                node = graph.nodes[v]
                exp, env = point_risk(float(node.get("y", active.lat)), float(node.get("x", active.lon)), active, [])
                return base * (1 + exp * 0.020 + env * 0.016)
            nodes = nx.shortest_path(graph, origin_node, destination_node, weight=safe_weight)
            label = "Lowest exposure street route"
            explanation = "Actual streets with penalties near vulnerable settings, the plume and environmental receptors."
            factor = 0.95
        else:
            def traffic_weight(u: Any, v: Any, edge_data: Dict[str, Any]) -> float:
                edge = _edge_payload(edge_data)
                base = float(edge.get("travel_time", 30) or 30)
                congestion = _traffic_penalty_for_node(graph, v, traffic)
                return base * (1 + congestion * 2.1)
            nodes = nx.shortest_path(graph, origin_node, destination_node, weight=traffic_weight)
            label = "Lowest congestion street route"
            explanation = "Actual streets weighted against currently congested segments in the active traffic layer."
            factor = 0.98

        if not nodes:
            return None
        path = osm_nodes_to_path(graph, list(nodes))
        if len(path) < 2:
            return None
        return route_result_from_path(objective, label, path, active, traffic, "OSMnx real streets", explanation, factor)
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def real_street_path_between(origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[List[List[float]]]:
    graph = load_osm_graph()
    if graph is not None and ox is not None:
        try:
            origin_node = ox.distance.nearest_nodes(graph, origin[1], origin[0])
            destination_node = ox.distance.nearest_nodes(graph, destination[1], destination[0])
            nodes = ox.routing.shortest_path(graph, origin_node, destination_node, weight="travel_time")
            path = osm_nodes_to_path(graph, list(nodes)) if nodes else None
            if path and len(path) >= 2:
                return path
        except Exception:
            pass
    osrm = fetch_osrm_driving_routes(origin, destination, 1)
    return osrm[0]["path"] if osrm else None


def _merge_street_parts(parts: Sequence[Sequence[Sequence[float]]]) -> List[List[float]]:
    merged: List[List[float]] = []
    for part in parts:
        points = [[float(point[0]), float(point[1])] for point in part if len(point) >= 2]
        if not points:
            continue
        if merged and merged[-1] == points[0]:
            points = points[1:]
        merged.extend(points)
    return merged


@st.cache_data(ttl=86_400, show_spinner=False)
def _street_path_through_control_points_cached(control_points: Tuple[Tuple[float, float], ...]) -> List[List[float]]:
    """Route through a sequence of lon/lat control points using real streets."""
    if len(control_points) < 2:
        return []
    parts: List[List[List[float]]] = []
    for start, end in zip(control_points[:-1], control_points[1:]):
        segment = real_street_path_between((start[1], start[0]), (end[1], end[0]))
        if not segment or len(segment) < 2:
            return []
        parts.append(segment)
    return _merge_street_parts(parts)


def street_path_through_control_points(control_path: Sequence[Sequence[float]]) -> List[List[float]]:
    key = tuple((round(float(point[0]), 6), round(float(point[1]), 6)) for point in control_path if len(point) >= 2)
    return _street_path_through_control_points_cached(key)


def streetify_path_collection(
    items: Sequence[Dict[str, Any]],
    ors_key: str = "",
    profile: str = "driving-car",
    hazmat: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    """Replace schematic lines with real road-network geometry.

    OpenRouteService is attempted first. OSMnx/OSRM remains a key-free fallback.
    If every service fails, the original cross-block line is hidden rather than
    displayed as if it were a real street route.
    """
    output: List[Dict[str, Any]] = []
    missing = 0
    ors_count = 0
    fallback_count = 0
    for item in items:
        control_path = item.get("control_path") or item.get("path", [])
        key = tuple(
            (round(float(point[0]), 6), round(float(point[1]), 6))
            for point in control_path
            if isinstance(point, (list, tuple)) and len(point) >= 2
        )
        road_path: List[List[float]] = []
        geometry_backend = ""
        if (ors_key or ors_is_local()) and len(key) >= 2:
            road_path = ors_street_path_through_control_points(
                ors_key,
                key,
                profile=profile,
                hazmat=hazmat,
            )
            if len(road_path) >= 2:
                geometry_backend = "OpenRouteService GeoJSON real streets"
                ors_count += 1
        if len(road_path) < 2:
            road_path = street_path_through_control_points(control_path)
            if len(road_path) >= 2:
                geometry_backend = "OSMnx/OSRM real streets"
                fallback_count += 1
        if len(road_path) < 2:
            missing += 1
            output.append({
                **item,
                "control_path": list(control_path),
                "path": [],
                "street_snapped": False,
                "geometry_backend": "Unavailable - hidden",
            })
        else:
            output.append({
                **item,
                "control_path": list(control_path),
                "path": road_path,
                "street_snapped": True,
                "geometry_backend": geometry_backend,
            })
    available = len(output) - missing
    return output, (
        f"{available}/{len(output)} real-street geometries "
        f"({ors_count} ORS, {fallback_count} OSM/OSRM, {missing} hidden)"
    )


def osrm_route_options(resource: Resource, active: Incident, traffic: List[Dict[str, Any]]) -> Optional[Dict[str, RouteResult]]:
    raw_routes = fetch_osrm_driving_routes((resource.lat, resource.lon), (active.lat, active.lon), 3)
    if not raw_routes:
        return None
    candidates: List[RouteResult] = []
    for idx, raw in enumerate(raw_routes):
        candidate = route_result_from_path(
            f"osrm-{idx}",
            f"OSRM street alternative {idx + 1}",
            raw["path"],
            active,
            traffic,
            "OSRM public real streets",
            "Full-resolution route geometry snapped to the OpenStreetMap driving network.",
            1.0,
        )
        if raw.get("distance_km"):
            candidate.distance_km = raw["distance_km"]
        if raw.get("eta_min"):
            candidate.eta_min = raw["eta_min"]
            candidate.composite_score = round(
                candidate.eta_min * 0.33
                + candidate.exposure_score * 0.30
                + candidate.environment_score * 0.18
                + candidate.congestion_score * 0.10
                + candidate.responder_risk * 0.09,
                1,
            )
        candidates.append(candidate)

    fastest_base = min(candidates, key=lambda item: (item.eta_min, item.distance_km))
    safest_base = min(candidates, key=lambda item: item.exposure_score * 0.64 + item.environment_score * 0.36)
    low_traffic_base = min(candidates, key=lambda item: (item.congestion_score, item.eta_min))
    recommended_base = min(candidates, key=lambda item: item.composite_score)

    def clone(base: RouteResult, route_id: str, label: str, explanation: str) -> RouteResult:
        return RouteResult(**{
            **asdict(base),
            "id": route_id,
            "label": label,
            "explanation": explanation,
        })

    return {
        "fastest": clone(fastest_base, "fastest", "Fastest real-street route", "Public OSRM route with the lowest estimated travel time."),
        "safest": clone(safest_base, "safest", "Lowest exposure real-street route", "Public OSRM street alternative with the lowest combined human and environmental exposure."),
        "low_traffic": clone(low_traffic_base, "low_traffic", "Lowest congestion real-street route", "Public OSRM street alternative with the lowest modeled congestion along the route."),
        "recommended": clone(recommended_base, "recommended", "AI recommended real-street route", "Best available street-following alternative after balancing ETA, exposure, environmental sensitivity, congestion and responder risk."),
    }




def ors_route_options(
    resource: Resource,
    active: Incident,
    traffic: List[Dict[str, Any]],
    ors_key: str,
) -> Optional[Dict[str, RouteResult]]:
    """Build real-street alternatives from OpenRouteService GeoJSON routes."""
    if not ors_key and not ors_is_local():
        return None

    profile = "driving-hgv" if resource.kind in {"fire", "hazmat", "bus"} else "driving-car"
    coordinates = ((resource.lon, resource.lat), (active.lon, active.lat))

    baseline = fetch_ors_directions(
        ors_key,
        coordinates,
        profile=profile,
        alternatives=3,
        preference="fastest",
        hazmat=False,
    )
    if not baseline.get("ok"):
        # Some regions/profiles may not support alternative routes. Retry a
        # single route before falling back to another service.
        baseline = fetch_ors_directions(
            ors_key,
            coordinates,
            profile=profile,
            alternatives=1,
            preference="fastest",
            hazmat=False,
        )
    if not baseline.get("ok") and profile == "driving-hgv":
        baseline = fetch_ors_directions(
            ors_key,
            coordinates,
            profile="driving-car",
            alternatives=3,
            preference="fastest",
            hazmat=False,
        )
    if not baseline.get("ok"):
        return None

    candidates: List[RouteResult] = []
    for idx, raw in enumerate(baseline.get("routes", []) or []):
        candidate = route_result_from_path(
            f"ors-{idx}",
            f"OpenRouteService street alternative {idx + 1}",
            raw["path"],
            active,
            traffic,
            f"OpenRouteService {raw.get('profile', profile)}",
            "Full GeoJSON LineString returned by OpenRouteService and drawn directly on the road network.",
            1.0,
        )
        if raw.get("distance_km"):
            candidate.distance_km = raw["distance_km"]
        if raw.get("eta_min"):
            candidate.eta_min = raw["eta_min"]
            candidate.composite_score = round(
                candidate.eta_min * 0.33
                + candidate.exposure_score * 0.30
                + candidate.environment_score * 0.18
                + candidate.congestion_score * 0.10
                + candidate.responder_risk * 0.09,
                1,
            )
        candidates.append(candidate)

    # Explicit environmental alternative. ORS avoids mapped protected polygons;
    # for emergency vehicles the hazmat restriction itself remains disabled.
    avoid_geometry = ors_environment_avoid_geometry(
        (resource.lat, resource.lon),
        (active.lat, active.lon),
    )
    if avoid_geometry:
        safer = fetch_ors_directions(
            ors_key,
            coordinates,
            profile=profile,
            alternatives=1,
            preference="recommended",
            avoid_polygons_json=avoid_geometry,
            hazmat=False,
        )
        if safer.get("ok"):
            raw = safer["routes"][0]
            safe_candidate = route_result_from_path(
                "ors-environment",
                "OpenRouteService protected-area avoidance route",
                raw["path"],
                active,
                traffic,
                f"OpenRouteService {raw.get('profile', profile)}",
                "Road-following route calculated with mapped protected-area polygons supplied as avoid areas.",
                0.98,
            )
            if raw.get("distance_km"):
                safe_candidate.distance_km = raw["distance_km"]
            if raw.get("eta_min"):
                safe_candidate.eta_min = raw["eta_min"]
            safe_candidate.composite_score = round(
                safe_candidate.eta_min * 0.33
                + safe_candidate.exposure_score * 0.30
                + safe_candidate.environment_score * 0.18
                + safe_candidate.congestion_score * 0.10
                + safe_candidate.responder_risk * 0.09,
                1,
            )
            candidates.append(safe_candidate)

    if not candidates:
        return None

    fastest_base = min(candidates, key=lambda item: (item.eta_min, item.distance_km))
    safest_base = min(candidates, key=lambda item: item.exposure_score * 0.58 + item.environment_score * 0.42)
    low_traffic_base = min(candidates, key=lambda item: (item.congestion_score, item.eta_min))
    recommended_base = min(candidates, key=lambda item: item.composite_score)

    def clone(base: RouteResult, route_id: str, label: str, explanation: str) -> RouteResult:
        return RouteResult(**{
            **asdict(base),
            "id": route_id,
            "label": label,
            "explanation": explanation,
        })

    return {
        "fastest": clone(
            fastest_base,
            "fastest",
            "Fastest OpenRouteService street route",
            "OpenRouteService road geometry with the lowest estimated travel time.",
        ),
        "safest": clone(
            safest_base,
            "safest",
            "Lowest exposure OpenRouteService route",
            "Real-street alternative with the lowest combined human and environmental exposure; mapped protected polygons are avoided when available.",
        ),
        "low_traffic": clone(
            low_traffic_base,
            "low_traffic",
            "Lowest modeled congestion street route",
            "OpenRouteService street alternative evaluated against the SkyRoute traffic layer. OpenRouteService itself is not providing live traffic here.",
        ),
        "recommended": clone(
            recommended_base,
            "recommended",
            "AI recommended OpenRouteService route",
            "Best road-following alternative after balancing ETA, population exposure, environmental sensitivity, modeled congestion and responder risk.",
        ),
    }


def unavailable_route_options(resource: Resource, active: Incident) -> Dict[str, RouteResult]:
    explanation = "No real-street routing service responded. Check the internet connection, configure ORS_API_KEY or AMap, install OSMnx, or set OSRM_BASE_URL to a reachable OSRM server. No approximate cross-block route is drawn."
    def item(route_id: str, label: str) -> RouteResult:
        return RouteResult(route_id, label, [], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 999.0, "Street routing unavailable", explanation)
    return {
        "fastest": item("fastest", "Fastest route unavailable"),
        "safest": item("safest", "Lowest exposure route unavailable"),
        "low_traffic": item("low_traffic", "Lowest congestion route unavailable"),
        "recommended": item("recommended", "AI route unavailable"),
    }


def build_route_options(
    resource: Resource,
    active: Incident,
    traffic: List[Dict[str, Any]],
    backend: str,
    amap_key: str,
    ors_key: str,
) -> Dict[str, RouteResult]:
    origin = (resource.lat, resource.lon)
    destination = (active.lat, active.lon)

    def osm_options() -> Optional[Dict[str, RouteResult]]:
        fastest = osm_route(resource, active, "fastest", traffic)
        safest = osm_route(resource, active, "safest", traffic)
        low_traffic = osm_route(resource, active, "low_traffic", traffic)
        if fastest and safest and low_traffic:
            options = {"fastest": fastest, "safest": safest, "low_traffic": low_traffic}
            recommended = min(options.values(), key=lambda route: route.composite_score)
            options["recommended"] = RouteResult(**{
                **asdict(recommended),
                "id": "recommended",
                "label": "AI recommended real-street route",
            })
            return options
        return None

    def ors_options() -> Optional[Dict[str, RouteResult]]:
        return ors_route_options(resource, active, traffic, ors_key) if (ors_key or ors_is_local()) else None

    if backend.startswith("OpenRouteService"):
        return ors_options() or osm_options() or osrm_route_options(resource, active, traffic) or unavailable_route_options(resource, active)

    if backend.startswith("AMap") and amap_key:
        amap = fetch_amap_driving_route(amap_key, origin, destination)
        alternatives = ors_options() or osm_options() or osrm_route_options(resource, active, traffic)
        if amap and alternatives:
            fastest = route_result_from_path(
                "fastest", "Fastest AMap route", amap["path"], active, traffic,
                "AMap live route", "AMap turn-by-turn geometry snapped to the Chinese road network.", 1.02,
            )
            fastest.distance_km = amap["distance_km"] or fastest.distance_km
            fastest.eta_min = amap["eta_min"] or fastest.eta_min
            alternatives["fastest"] = fastest
            recommended = min(
                [alternatives["fastest"], alternatives["safest"], alternatives["low_traffic"]],
                key=lambda route: route.composite_score,
            )
            alternatives["recommended"] = RouteResult(**{
                **asdict(recommended),
                "id": "recommended",
                "label": "AI recommended real-street route",
            })
            return alternatives
        if amap:
            fastest = route_result_from_path(
                "fastest", "Fastest AMap route", amap["path"], active, traffic,
                "AMap live route", "AMap turn-by-turn geometry snapped to the Chinese road network.", 1.02,
            )
            fastest.distance_km = amap["distance_km"] or fastest.distance_km
            fastest.eta_min = amap["eta_min"] or fastest.eta_min
            return {
                key: RouteResult(**{**asdict(fastest), "id": key, "label": label})
                for key, label in {
                    "fastest": "Fastest AMap route",
                    "safest": "AMap real-street route (single alternative)",
                    "low_traffic": "AMap real-street route (single alternative)",
                    "recommended": "AI recommended AMap route",
                }.items()
            }

    if backend.startswith("OSRM"):
        return osrm_route_options(resource, active, traffic) or ors_options() or osm_options() or unavailable_route_options(resource, active)

    if backend.startswith("OSMnx"):
        return osm_options() or ors_options() or osrm_route_options(resource, active, traffic) or unavailable_route_options(resource, active)

    # Automatic mode now prioritizes OpenRouteService because it returns an
    # explicit GeoJSON LineString and supports protected-area avoidance.
    return ors_options() or osm_options() or osrm_route_options(resource, active, traffic) or unavailable_route_options(resource, active)


def compute_incident_state(
    active: Incident,
    wind_speed_kmh: float,
    wind_direction: float,
    rain_mm_h: float,
    temperature_c: float,
    traffic_index: float,
    evacuation_capacity_ppm: int,
    setup_delay_min: int,
    shelter_quality: float,
    tick: int,
    pois_live: List[Dict[str, Any]],
) -> Dict[str, Any]:
    substance = SUBSTANCES[active.substance]
    dynamic_leak = active.leak_rate_kg_min * (1 + min(0.20, tick * 0.006))
    protective_distance = int(
        substance["base_protective_m"]
        * (0.82 + math.sqrt(max(2, wind_speed_kmh) / 12) * 0.38)
        * (1 + dynamic_leak / 500)
        * (1 + min(0.12, tick * 0.004))
    )
    isolation_distance = int(substance["base_isolation_m"] * (1 + dynamic_leak / 350))
    plume_width = int(protective_distance * (0.40 + min(0.28, rain_mm_h / 230)))
    plume_polygon = make_plume_polygon(active.lat, active.lon, wind_direction, protective_distance, plume_width)
    plume_arrival_min = round((protective_distance / max(0.6, wind_speed_kmh / 3.6)) / 60, 1)

    exposed = []
    for poi in pois_live:
        distance = dist_m(active.lat, active.lon, poi["lat"], poi["lon"])
        if distance <= protective_distance + poi["buffer_m"]:
            exposed.append({**poi, "distance_m": int(distance)})
    exposed_population = sum(p["population_now"] for p in exposed)
    evacuation_time = setup_delay_min + exposed_population / max(1, evacuation_capacity_ppm)
    shelter_effectiveness = clamp(shelter_quality * substance["shelter_factor"] * (1 - rain_mm_h / 500), 0.15, 0.92)
    movement_margin = plume_arrival_min - evacuation_time

    if movement_margin > 9 and traffic_index < 7.2:
        recommendation = "Phased evacuation"
        confidence = 0.78
    elif shelter_effectiveness >= 0.48 and movement_margin < 3:
        recommendation = "Shelter-in-place first"
        confidence = 0.84
    else:
        recommendation = "Hybrid protection"
        confidence = 0.88

    return {
        "substance": substance,
        "dynamic_leak": dynamic_leak,
        "protective_distance": protective_distance,
        "isolation_distance": isolation_distance,
        "plume_width": plume_width,
        "plume_polygon": plume_polygon,
        "plume_arrival_min": plume_arrival_min,
        "exposed_pois": exposed,
        "exposed_population": exposed_population,
        "evacuation_time_min": round(evacuation_time, 1),
        "shelter_effectiveness": shelter_effectiveness,
        "movement_margin": round(movement_margin, 1),
        "recommendation": recommendation,
        "confidence": confidence,
    }


def prevention_score(rain: float, temperature: float, wetness: float, traffic: float, hazmat_flow: int, ordinary_accidents: int) -> Tuple[int, str, Dict[str, float]]:
    factors = {
        "Rain": clamp(rain / 55, 0, 1),
        "Heat": clamp((temperature - 25) / 17, 0, 1),
        "Wet pavement": clamp(wetness, 0, 1),
        "Traffic": clamp(traffic / 10, 0, 1),
        "HazMat flow": clamp(hazmat_flow / 60, 0, 1),
        "Secondary incidents": clamp(ordinary_accidents / 5, 0, 1),
    }
    weighted = (
        factors["Rain"] * 0.17
        + factors["Heat"] * 0.12
        + factors["Wet pavement"] * 0.18
        + factors["Traffic"] * 0.21
        + factors["HazMat flow"] * 0.22
        + factors["Secondary incidents"] * 0.10
    )
    score = int(round(weighted * 100))
    level = "LOW" if score < 35 else "ELEVATED" if score < 65 else "HIGH" if score < 82 else "CRITICAL"
    return score, level, factors


def build_preventive_alerts(
    rain: float,
    temperature: float,
    wetness: float,
    traffic: float,
    hazmat_flow: int,
    score: int,
) -> List[PreventiveAlert]:
    alerts: List[PreventiveAlert] = []
    if rain >= 25 or wetness >= 0.65:
        alerts.append(PreventiveAlert(
            "PA-WET", "HIGH" if rain >= 40 else "ELEVATED",
            "Loss-of-control risk for heavy tankers",
            "G2504 incident approach",
            f"Rain {rain:.0f} mm/h and wet-pavement index {wetness:.0%} reduce braking stability.",
            "Reduce HazMat speed, activate warning signs and stage a traffic-police support unit.",
            24, 4, "Low", BASE_TRAFFIC_SEGMENTS[1]["path"],
        ))
    if traffic >= 7.0 and hazmat_flow >= 22:
        alerts.append(PreventiveAlert(
            "PA-FLOW", "HIGH",
            "HazMat concentration during congestion peak",
            "Restricted urban segment",
            f"Traffic index {traffic:.1f}/10 overlaps with {hazmat_flow} dangerous-goods vehicles per hour.",
            "Apply a timed HazMat restriction and divert vehicles to the northern industrial bypass.",
            31, 8, "Medium", HAZMAT_CORRIDORS[1]["path"],
        ))
    if temperature >= 36:
        alerts.append(PreventiveAlert(
            "PA-HEAT", "ELEVATED",
            "Thermal stress on pressurised cargo",
            "Chemical logistics corridor",
            f"Ambient temperature {temperature:.0f}°C increases equipment and vapour-pressure stress.",
            "Require thermal and pressure inspection before corridor entry and reduce waiting time in queues.",
            18, 6, "Low", HAZMAT_CORRIDORS[0]["path"],
        ))
    if score < 35:
        alerts.append(PreventiveAlert(
            "PA-MON", "LOW",
            "Conditions within monitored tolerance",
            "Citywide network",
            "No predictive threshold currently requires restrictive action.",
            "Maintain sensor, traffic and dangerous-goods flow monitoring.",
            5, 0, "Low", HAZMAT_CORRIDORS[2]["path"],
        ))
    return alerts


def population_decisions(state: Dict[str, Any]) -> List[DecisionOption]:
    people = state["exposed_population"]
    return [
        DecisionOption(
            "POP-HYBRID", "population", "Hybrid protection",
            "Evacuate the nearest school and outdoor population while ordering shelter-in-place in more distant sectors.",
            9, int(people * 0.94), "8 buses, 4 police units, public alert", "Medium", "Low–medium", 0.88,
            "Balances limited plume-arrival time with the high vulnerability of schools and outdoor populations.",
            "Displays evacuation sectors, shelter sectors, bus routes and priority pickup points.",
        ),
        DecisionOption(
            "POP-SHELTER", "population", "Shelter-in-place first",
            "Immediate indoor protection, HVAC shutdown and public instructions while field sensors confirm the plume.",
            4, int(people * 0.86), "Cell broadcast, building managers, sensor verification", "Low", "Medium", 0.83,
            "Fastest protective action when evacuation clearance exceeds the estimated plume-arrival time.",
            "Marks shelter sectors, communication zones and sensor-confirmation points.",
        ),
        DecisionOption(
            "POP-PHASE", "population", "Phased evacuation",
            "Move the closest and most vulnerable sectors first, then release downstream zones if routes remain open.",
            13, int(people * 0.91), "14 buses, 6 police units, 3 shelters", "High", "Low", 0.76,
            "Reduces congestion compared with simultaneous evacuation and prioritises vulnerable facilities.",
            "Shows phased zones, staging areas, shelters and directional evacuation routes.",
        ),
        DecisionOption(
            "POP-ASSIST", "population", "Assisted vulnerable evacuation",
            "Evacuate the elder-care centre, hospital-dependent patients and mobility-limited residents only.",
            11, int(people * 0.46), "4 ambulances, 6 accessible buses, medical coordination", "Medium", "Medium", 0.74,
            "Targets groups least able to maintain effective shelter or self-evacuate.",
            "Highlights assisted pickup points, ambulance routes and receiving facilities.",
        ),
    ]


def environmental_decisions(active: Incident) -> List[DecisionOption]:
    return [
        DecisionOption(
            "ENV-DRAIN", "environment", "Block stormwater inlets",
            "Install drain covers and absorbent barriers before contaminated water reaches the retention wetland.",
            7, 0, "Environmental team + fire crew", "Low", "Low", 0.91,
            "The nearest inlets provide a rapid pathway from the roadway to surface-water receptors.",
            "Highlights drains, barrier locations and the protected downstream pathway.",
        ),
        DecisionOption(
            "ENV-SENSOR", "environment", "Deploy air and water sensors",
            "Place one air sensor downwind, one near the school and one water sensor at the retention inlet.",
            10, 0, "3 mobile sensors", "Low", "Low", 0.89,
            "Field observations reduce uncertainty and allow protective zones to contract or expand safely.",
            "Displays proposed sensor locations and their coverage areas.",
        ),
        DecisionOption(
            "ENV-BOOM", "environment", "Install containment line",
            "Create a temporary containment and recovery line between the roadway and drainage corridor.",
            16, 0, "HazMat + environmental team + absorbent material", "Medium", "Low", 0.78,
            "Useful for liquid runoff and contaminated suppression water when the source cannot be stopped immediately.",
            "Shows the containment line, clean/dirty zones and vehicle access.",
        ),
        DecisionOption(
            "ENV-MONITOR", "environment", "Monitor only",
            "Maintain observation while prioritising life safety; escalate if water or air thresholds are exceeded.",
            3, 0, "Existing fixed sensors", "Low", "Medium–high", 0.58,
            "Preserves resources but leaves greater uncertainty and potential delayed environmental response.",
            "Displays current fixed sensors and threshold watch areas only.",
        ),
    ]


def traffic_control_options() -> List[DecisionOption]:
    return [
        DecisionOption(
            "TR-CORRIDOR", "traffic", "Emergency green corridor",
            "Reserve one approach for responders and coordinate junction priority.",
            5, 0, "Traffic police + signal control", "Medium", "Low", 0.90,
            "Reduces responder ETA and separates emergency flow from evacuation traffic.",
            "Highlights the protected emergency corridor and conflicting movements.",
        ),
        DecisionOption(
            "TR-CLOSE", "traffic", "Close the incident segment",
            "Block both directions through the isolation zone and activate signed detours.",
            4, 0, "4 police units + variable-message signs", "High", "Low", 0.93,
            "Prevents public entry into the isolation zone and protects responder workspace.",
            "Marks closures, barricades and diverted civilian traffic.",
        ),
        DecisionOption(
            "TR-HAZMAT", "traffic", "Divert other HazMat vehicles",
            "Send dangerous-goods traffic to the northern industrial bypass until the operation is closed.",
            8, 0, "Digital notice + logistics coordination", "Medium", "Low", 0.87,
            "Avoids secondary dangerous-goods exposure near the active incident and congestion queue.",
            "Shows affected trucks, old route and proposed bypass.",
        ),
        DecisionOption(
            "TR-EVAC", "traffic", "Evacuation bus priority",
            "Reserve a separate lane and pickup sequence for evacuation buses.",
            7, 0, "Bus control + 3 police units", "High", "Low–medium", 0.82,
            "Prevents evacuation buses from competing with private vehicles and response resources.",
            "Displays the bus corridor, pickup points and shelter destinations.",
        ),
    ]


def choose_recommended_decision(options: List[DecisionOption], preferred_title: str = "") -> DecisionOption:
    if preferred_title:
        for option in options:
            if preferred_title.lower() in option.title.lower():
                return option
    return max(options, key=lambda x: x.confidence)


# =============================================================================
# SESSION STATE
# =============================================================================
INCIDENT_TABS = [
    "Overview",
    "Population",
    "Dispatch",
    "Traffic",
    "Environment",
    "Plan",
    "AI Copilot",
]


def init_state() -> None:
    defaults: Dict[str, Any] = {
        "nav_page": "Central & Prevention",
        "agent_return_page": "Central & Prevention",
        "agent_return_incident_tab": "Overview",
        "show_3d_buildings": False,
        "show_worldpop_3d": False,
        "active_incident_id": INCIDENTS[0].id,
        "selected_alert_id": None,
        "incident_tab": "Overview",
        "prevention_actions": [],
        "preview_population": None,
        "preview_traffic": None,
        "preview_environment": None,
        "plan_decisions": {},
        "resource_quantities": {kind: 0 for kind in AGENCY_LABEL},
        "selected_resource_ids": {},
        "selected_routes": {},
        "selected_mission_target_ids": {},
        "dispatch_status": {r.id: r.status for r in RESOURCES},
        "dispatch_start_tick": {},
        "road_closures": [],
        "demo_tick": 0,
        "demo_stage": 0,
        "historical_stage": 0,
        "event_log": [],
        "agent_messages": [{"role": "assistant", "content": "SkyRoute AI online. I am monitoring the selected incident, weather, traffic, routes, exposed population and available resources."}],
        "plan_confirmed": False,
        "dispatch_receipts": [],
        "last_dispatch_receipt": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def navigate_to(page_name: str, incident_tab: Optional[str] = None) -> None:
    """Navigate without the removed workspace radio and preserve incident context."""
    st.session_state.nav_page = page_name
    if incident_tab is not None:
        st.session_state.incident_tab = incident_tab
    st.rerun()


def open_agent() -> None:
    """Open the AI agent from any page and remember the exact return context."""
    current_page = st.session_state.get("nav_page", "Central & Prevention")
    if current_page != "SkyRoute AI Copilot":
        st.session_state.agent_return_page = current_page
        st.session_state.agent_return_incident_tab = st.session_state.get("incident_tab", "Overview")
    st.session_state.nav_page = "SkyRoute AI Copilot"
    st.rerun()


def return_from_agent() -> None:
    return_page = st.session_state.get("agent_return_page", "Central & Prevention")
    st.session_state.nav_page = return_page
    if return_page == "Incident Command":
        st.session_state.incident_tab = st.session_state.get("agent_return_incident_tab", "Overview")
    st.rerun()


def active_incident() -> Incident:
    return next((i for i in INCIDENTS if i.id == st.session_state.active_incident_id), INCIDENTS[0])


def log_event(message: str, category: str = "system") -> None:
    st.session_state.event_log.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "tick": st.session_state.demo_tick,
        "category": category,
        "message": message,
    })
    st.session_state.event_log = st.session_state.event_log[:80]


def normalize_plan_decisions() -> None:
    """Migrate older category-keyed plans to an accumulating ID-keyed structure."""
    raw = st.session_state.get("plan_decisions", {})
    if not isinstance(raw, dict):
        st.session_state.plan_decisions = {}
        return
    migrated: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        option_id = str(value.get("id") or key)
        migrated[option_id] = value
    st.session_state.plan_decisions = migrated


def selected_decisions(category: Optional[str] = None) -> List[Dict[str, Any]]:
    values = list(st.session_state.get("plan_decisions", {}).values())
    if category is not None:
        values = [item for item in values if item.get("category") == category]
    return values


def is_decision_selected(option_id: str) -> bool:
    return option_id in st.session_state.get("plan_decisions", {})


def add_decision_to_plan(option: DecisionOption) -> None:
    st.session_state.plan_decisions[option.id] = asdict(option)
    st.session_state.plan_confirmed = False
    log_event(f"Decision added: {option.title}", option.category)
    st.toast(f"Added to plan: {option.title}")


def remove_decision_from_plan(option: DecisionOption) -> None:
    st.session_state.plan_decisions.pop(option.id, None)
    st.session_state.plan_confirmed = False
    log_event(f"Decision removed: {option.title}", option.category)
    st.toast(f"Removed from plan: {option.title}")


normalize_plan_decisions()


def add_prevention_action(alert: PreventiveAlert) -> None:
    if alert.id not in st.session_state.prevention_actions:
        st.session_state.prevention_actions.append(alert.id)
        log_event(f"Preventive action accepted: {alert.recommended_action}", "prevention")
        st.toast("Preventive action added")


# =============================================================================
# MAP LAYER HELPERS — ALL LAYERS HAVE IDs AND COMMON TOOLTIP FIELDS
# =============================================================================
def _symbol_key_for_item(item: Dict[str, Any]) -> str:
    kind = str(item.get("kind", "")).lower()
    if kind in AGENCY_GLYPH:
        return kind
    item_type = str(item.get("type", "")).lower()
    if item_type in {"village", "residential", "population", "eldercare", "commercial"}:
        return "community"
    if item_type in MAP_SYMBOL_GLYPH:
        return item_type
    title = str(item.get("title", item.get("name", ""))).lower()
    if "hospital" in title:
        return "hospital"
    if "school" in title:
        return "school"
    if "hazmat truck" in title or "vehicle" in title:
        return "truck"
    if "incident" in title or "leak" in title or "accident source" in title:
        return "incident"
    if "drain" in title:
        return "drain"
    if "sensor" in title:
        return "sensor"
    return "target"


def _prepare_point_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for raw in data:
        item = dict(raw)
        symbol_key = _symbol_key_for_item(item)
        item["symbol_key"] = symbol_key
        item["glyph"] = str(MAP_SYMBOL_GLYPH.get(symbol_key, "O") or "O")[:2]
        item.setdefault("title", item.get("name", "Map object"))
        item.setdefault("details", item.get("description", "Operational map object"))
        item.setdefault("outline_color", STATUS_COLOR.get(str(item.get("status", "")), [5, 10, 16]) + [245])
        item.setdefault("text_color", [255, 255, 255, 255])
        prepared.append(item)
    return prepared


def scatter_layer(
    layer_id: str,
    data: List[Dict[str, Any]],
    radius: Any = 70,
    color: Any = "color",
    stroked: bool = True,
    pickable: bool = True,
) -> pdk.Layer:
    prepared = _prepare_point_data(data)
    return pdk.Layer(
        "ScatterplotLayer",
        id=layer_id,
        data=prepared,
        get_position="[lon, lat]",
        get_radius=radius,
        get_fill_color=color,
        stroked=stroked,
        get_line_color="outline_color",
        line_width_min_pixels=2,
        pickable=pickable,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 105],
    )


def text_layer(
    layer_id: str,
    data: List[Dict[str, Any]],
    size: int = 18,
    shadow: bool = False,
) -> pdk.Layer:
    prepared = _prepare_point_data(data)
    return pdk.Layer(
        "TextLayer",
        id=layer_id,
        data=prepared,
        get_position="[lon, lat]",
        get_text="glyph",
        get_size=size,
        size_units="pixels",
        size_min_pixels=max(12, size - 4),
        size_max_pixels=size + 6,
        get_color=[3, 8, 14, 245] if shadow else "text_color",
        get_pixel_offset=[1, 1] if shadow else [0, 0],
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        font_family="Arial",
        character_set=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+!OX-"),
        billboard=True,
        pickable=False,
    )


def point_layers(layer_prefix: str, data: List[Dict[str, Any]], radius: Any = 65, size: int = 18) -> List[pdk.Layer]:
    """Render operational points with compact neon icons when available.

    The ScatterplotLayer remains the pickable/status halo. Supported agencies
    and facilities receive a reliable embedded PNG IconLayer; all other map
    objects retain the lightweight ASCII badge fallback.
    """
    prepared = _prepare_point_data(data)
    icon_items: List[Dict[str, Any]] = []
    text_items: List[Dict[str, Any]] = []
    icon_pixels = int(clamp(size + 7, 23, 30))
    for raw in prepared:
        item = dict(raw)
        icon_key = str(item.get("symbol_key", ""))
        if icon_key in MAP_ICON_MAPPINGS:
            item["icon_data"] = dict(MAP_ICON_MAPPINGS[icon_key])
            item["icon_size_px"] = icon_pixels
            item["fallback_glyph"] = str(item.get("glyph", "O"))[:1]
            icon_items.append(item)
        else:
            text_items.append(item)

    layers: List[pdk.Layer] = [scatter_layer(f"{layer_prefix}-points", prepared, radius)]
    if icon_items:
        # ASCII fallback is placed under the PNG and remains visible if a
        # browser ever fails to decode the texture.
        layers.append(pdk.Layer(
            "TextLayer",
            id=f"{layer_prefix}-icon-fallback",
            data=icon_items,
            get_position="[lon, lat]",
            get_text="fallback_glyph",
            get_size=12,
            size_units="pixels",
            size_min_pixels=10,
            size_max_pixels=14,
            get_color=[255, 255, 255, 255],
            get_alignment_baseline="'center'",
            get_text_anchor="'middle'",
            font_family="Arial",
            character_set=list("PFAHEBSKR+"),
            billboard=True,
            pickable=False,
        ))
        layers.append(pdk.Layer(
            "IconLayer",
            id=f"{layer_prefix}-icons",
            data=icon_items,
            icon_mapping=None,
            get_icon="icon_data",
            get_position="[lon, lat]",
            get_size="icon_size_px",
            size_units="pixels",
            size_min_pixels=22,
            size_max_pixels=31,
            billboard=True,
            pickable=True,
            auto_highlight=True,
            highlight_color=[255, 255, 255, 95],
        ))
    if text_items:
        layers.extend([
            text_layer(f"{layer_prefix}-label-shadow", text_items, size + 2, shadow=True),
            text_layer(f"{layer_prefix}-labels", text_items, size),
        ])
    return layers


def incident_icon_layers(
    layer_prefix: str,
    data: List[Dict[str, Any]],
    get_size: int = 4,
    size_scale: int = 13,
) -> List[pdk.Layer]:
    """Render a compact neon incident badge with an ASCII fallback."""
    incidents_with_icon: List[Dict[str, Any]] = []
    for raw in data:
        item = dict(raw)
        item["icon_data"] = dict(ALERT_ICON_MAPPING)
        item["icon_size_px"] = 29
        item["fallback_glyph"] = "!"
        item.setdefault("title", item.get("name", "Incident"))
        item.setdefault("details", item.get("description", "Active incident"))
        incidents_with_icon.append(item)

    fallback_layer = pdk.Layer(
        "TextLayer",
        id=f"{layer_prefix}-fallback",
        data=incidents_with_icon,
        get_position="[lon, lat]",
        get_text="fallback_glyph",
        get_size=13,
        size_units="pixels",
        size_min_pixels=11,
        size_max_pixels=15,
        get_color=[255, 255, 255, 255],
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        font_family="Arial",
        character_set=list("!"),
        billboard=True,
        pickable=False,
    )
    icon_layer = pdk.Layer(
        "IconLayer",
        id=f"{layer_prefix}-points",
        data=incidents_with_icon,
        icon_mapping=None,
        get_icon="icon_data",
        get_position="[lon, lat]",
        get_size="icon_size_px",
        size_units="pixels",
        size_min_pixels=26,
        size_max_pixels=32,
        billboard=True,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 95],
    )
    return [fallback_layer, icon_layer]


def path_layer(layer_id: str, data: List[Dict[str, Any]], width: int = 7, color: Any = "color", pickable: bool = True) -> pdk.Layer:
    return pdk.Layer(
        "PathLayer",
        id=layer_id,
        data=data,
        get_path="path",
        get_color=color,
        get_width="width" if data and "width" in data[0] else width,
        width_min_pixels=max(2, width // 2),
        pickable=pickable,
        cap_rounded=True,
        joint_rounded=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 120],
    )


def path_layers_with_halo(
    layer_id: str,
    data: List[Dict[str, Any]],
    width: int = 7,
    halo_extra: int = 5,
) -> List[pdk.Layer]:
    """Render dark underlays beneath routes so overlapping colors remain legible."""
    if not data:
        return []
    halo_data: List[Dict[str, Any]] = []
    for raw in data:
        item = dict(raw)
        core_width = int(item.get("width", width))
        item["color"] = [1, 5, 9, 235]
        item["width"] = core_width + halo_extra
        halo_data.append(item)
    return [
        path_layer(f"{layer_id}-halo", halo_data, width + halo_extra, pickable=False),
        path_layer(layer_id, data, width, pickable=True),
    ]


def polygon_layer(layer_id: str, data: List[Dict[str, Any]], fill: Any, line: Any, pickable: bool = True) -> pdk.Layer:
    return pdk.Layer(
        "PolygonLayer",
        id=layer_id,
        data=data,
        get_polygon="polygon",
        get_fill_color=fill,
        get_line_color=line,
        stroked=True,
        line_width_min_pixels=2,
        pickable=pickable,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 70],
    )


def public_environment_layers(prefix: str) -> List[pdk.Layer]:
    if not PROTECTED_AREAS:
        return []
    return [polygon_layer(
        f"{prefix}-public-eco",
        PROTECTED_AREAS,
        [0, 214, 143, 24],
        [0, 214, 143, 215],
    )]


def make_deck(
    layers: List[pdk.Layer],
    latitude: float,
    longitude: float,
    zoom: float,
    pitch: float = 36,
    bearing: float = 0,
    use_basemap: bool = True,
) -> pdk.Deck:
    tooltip = {
        "html": "<div style=\"font-size:13px;font-weight:700;margin-bottom:4px\">{title}</div><div style=\"line-height:1.45\">{details}</div>",
        "style": {
            "backgroundColor": "#08130F",
            "color": "#F2F6E8",
            "border": "1px solid #D5F26D",
            "borderRadius": "8px",
            "fontSize": "12px",
        },
    }
    return pdk.Deck(
        map_provider="carto",
        map_style="dark" if use_basemap else None,
        initial_view_state=pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            pitch=pitch,
            bearing=bearing,
            controller=True,
        ),
        layers=layers,
        tooltip=tooltip,
    )


def render_map_info(height: int) -> None:
    # The anchor is rendered immediately before the PyDeck canvas. Positioning
    # the control by the chart height keeps it inside the map's lower-right
    # corner and away from the native zoom/navigation controls.
    top_offset = max(18, int(height) - 46)
    mask_offset = max(18, int(height) - 48)
    st.markdown(
        f"""
        <div class="sr-map-info-anchor">
          <div class="sr-map-native-info-mask" style="top:{mask_offset}px"></div>
          <details class="sr-map-info-control" style="top:{top_offset}px">
            <summary title="Map help — hover for object details or click to open instructions">i</summary>
            <div class="sr-map-info-panel">
              <b>Map interaction</b>
              Hover over routes, facilities, targets and operational zones to see their name and details.<br/><br/>
              Drag to pan · scroll to zoom · hold Ctrl while scrolling when the page captures the wheel.<br/><br/>
              On selectable maps, click a highlighted object to open its decision preview.
            </div>
          </details>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map(
    deck: pdk.Deck,
    key: str,
    height: int = 590,
    selectable: bool = False,
) -> Any:
    render_map_info(height)
    try:
        if selectable:
            return st.pydeck_chart(
                deck,
                use_container_width=True,
                height=height,
                key=key,
                on_select="rerun",
                selection_mode="single-object",
            )
        st.pydeck_chart(deck, use_container_width=True, height=height, key=key)
        return None
    except Exception as exc:
        st.error(f"The map could not be rendered: {exc}")
        st.caption("The operational overlays can still render even when the basemap service is unavailable.")
        return None


def selected_objects(event: Any, layer_id: str) -> List[Dict[str, Any]]:
    if event is None:
        return []
    try:
        selection = event.selection
        objects = selection.get("objects", {})
        return objects.get(layer_id, []) or []
    except Exception:
        try:
            return event.get("selection", {}).get("objects", {}).get(layer_id, []) or []
        except Exception:
            return []



def render_map_legend(items: List[Tuple[str, str, str]], title: str = "Map legend") -> None:
    """Render a compact dynamic legend below a PyDeck map."""
    if not items:
        return
    rendered = []
    for symbol, label, color in items:
        if symbol == INCIDENT_LEGEND_TOKEN:
            swatch = f'<img class="sr-legend-incident-icon" src="{ALERT_ICON_DATA_URI}" alt="Incident"/>'
        elif symbol in GLYPH_TO_ICON_KEY:
            icon_key = GLYPH_TO_ICON_KEY[symbol]
            swatch = f'<img class="sr-legend-map-icon" src="{MAP_ICON_DATA_URIS[icon_key]}" alt="{icon_key}"/>'
        elif symbol == "━":
            swatch = f'<span class="sr-map-legend-route" style="background:{color};color:{color}"></span>'
        elif symbol == "▰":
            swatch = f'<span class="sr-map-legend-area" style="background:{color}"></span>'
        else:
            swatch = f'<span class="sr-legend-symbol" style="background:{color}">{symbol}</span>'
        rendered.append(f'<div class="sr-map-legend-item">{swatch}<span>{label}</span></div>')
    st.markdown(
        f'<div class="sr-map-legend"><div class="sr-map-legend-title">{title}</div><div class="sr-map-legend-grid">{"".join(rendered)}</div></div>',
        unsafe_allow_html=True,
    )


def _polygon_centroid(polygon: Sequence[Sequence[float]]) -> Tuple[float, float]:
    if not polygon:
        return active.lat, active.lon
    return (
        float(np.mean([point[1] for point in polygon])),
        float(np.mean([point[0] for point in polygon])),
    )


def current_priority_ranking() -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    protective_distance = max(900.0, float(incident_state.get("protective_distance", 1800)))
    for poi in pois_live:
        if poi.get("type") == "hospital":
            continue
        distance = max(60.0, dist_m(active.lat, active.lon, poi["lat"], poi["lon"]))
        bearing = _bearing_deg(active.lat, active.lon, poi["lat"], poi["lon"])
        alignment = max(0.0, 1 - _angle_difference(bearing, wind_direction) / 105.0)
        proximity = max(0.0, 1 - distance / (protective_distance * 1.35))
        population_factor = math.log1p(max(1, poi["population_now"])) / math.log(5001)
        score = population_factor * 32 + float(poi["vulnerability"]) * 12 + proximity * 40 + alignment * 34
        if poi.get("id") == "H-POI-GAODANG":
            score += 34
        candidates.append({
            **poi,
            "distance_m": int(distance),
            "bearing": bearing,
            "downwind_alignment": alignment,
            "priority_score": round(score, 1),
        })
    return sorted(candidates, key=lambda item: item["priority_score"], reverse=True)


def vulnerability_buffer_data() -> List[Dict[str, Any]]:
    ranking = current_priority_ranking()
    if not ranking:
        return []
    max_score = max(item["priority_score"] for item in ranking) or 1.0
    output: List[Dict[str, Any]] = []
    for item in ranking:
        ratio = item["priority_score"] / max_score
        if ratio >= 0.78:
            fill, line, level = [255, 89, 94, 42], [255, 89, 94, 230], "Critical priority"
        elif ratio >= 0.55:
            fill, line, level = [255, 209, 102, 34], [255, 209, 102, 220], "High priority"
        else:
            fill, line, level = [0, 196, 255, 28], [0, 196, 255, 190], "Monitored priority"
        radius = int(clamp(
            160 + math.sqrt(max(1, item["population_now"])) * 16 + item["vulnerability"] * 55,
            180,
            1250,
        ))
        output.append({
            **item,
            "priority_radius_m": radius,
            "priority_fill": fill,
            "priority_line": line,
            "priority_level": level,
            "title": f"{item['name']} · {level}",
            "details": (
                f"Dynamic priority {item['priority_score']:.1f}<br/>"
                f"Estimated people {item['population_now']:,}<br/>"
                f"Distance {item['distance_m']} m<br/>"
                f"Downwind alignment {item['downwind_alignment']:.0%}<br/>"
                f"Estimated plume arrival: {incident_state.get('plume_arrival_min', '—')} min"
            ),
        })
    return output


def vulnerability_buffer_layers(prefix: str) -> List[pdk.Layer]:
    data = vulnerability_buffer_data()
    if not data or not show_population_layer:
        return []
    pulse = 1.0 + 0.05 * math.sin(float(st.session_state.get("demo_tick", 0)))
    for item in data:
        item["pulse_radius_m"] = item["priority_radius_m"] * pulse
    return [
        pdk.Layer(
            "ScatterplotLayer",
            id=f"{prefix}-vulnerability-halos",
            data=data,
            get_position="[lon, lat]",
            get_radius="pulse_radius_m",
            get_fill_color="priority_fill",
            get_line_color="priority_line",
            stroked=True,
            line_width_min_pixels=2,
            pickable=True,
            auto_highlight=True,
        )
    ]


def hospital_map_data() -> List[Dict[str, Any]]:
    output = []
    for poi in pois_live:
        if poi.get("type") != "hospital":
            continue
        available = int(poi.get("available_beds", max(20, int(poi.get("base_pop", 100) * 0.1))))
        status = str(poi.get("hospital_status", "Available"))
        outline = STATUS_COLOR.get("Available" if status == "Available" else "Requested" if status == "Limited" else "Busy", [148, 163, 184]) + [250]
        output.append({
            **poi,
            "color": [0, 168, 255, 245],
            "outline_color": outline,
            "glyph": MAP_SYMBOL_GLYPH["hospital"],
            "title": poi["name"],
            "details": (
                f"Hospital status: {status}<br/>Available beds: {available}<br/>"
                f"{poi.get('specialty', 'Emergency care')}<br/>"
                f"Estimated people on site: {poi.get('population_now', 0):,}"
            ),
        })
    return output


def resource_halo_layers(prefix: str, data: List[Dict[str, Any]]) -> List[pdk.Layer]:
    active_data = []
    pulse = 1.0 + 0.12 * math.sin(float(st.session_state.get("demo_tick", 0)) * 1.4)
    for item in data:
        status = item.get("status", "Available")
        if status not in {"Requested", "En route", "On scene"}:
            continue
        color = STATUS_COLOR.get(status, [148, 163, 184]) + [220]
        active_data.append({
            **item,
            "halo_radius": (125 if status == "On scene" else 105) * pulse,
            "halo_fill": color[:3] + [24],
            "halo_line": color,
        })
    if not active_data:
        return []
    return [
        pdk.Layer(
            "ScatterplotLayer",
            id=f"{prefix}-status-halo",
            data=active_data,
            get_position="[lon, lat]",
            get_radius="halo_radius",
            get_fill_color="halo_fill",
            get_line_color="halo_line",
            stroked=True,
            line_width_min_pixels=3,
            pickable=False,
        )
    ]


def worldpop_3d_data() -> List[Dict[str, Any]]:
    columns: List[Dict[str, Any]] = []
    offsets = [(0, 0), (0.00055, 0), (-0.00055, 0), (0, 0.00045), (0, -0.00045), (0.00042, 0.00034), (-0.00042, -0.00034)]
    ranking = {item["id"]: item for item in current_priority_ranking()}
    for poi in pois_live:
        if poi.get("type") == "hospital":
            continue
        pop = max(1, int(poi.get("population_now", 1)))
        priority = ranking.get(poi.get("id"), {}).get("priority_score", poi.get("vulnerability", 1) * 10)
        color = [255, 89, 94, 205] if priority >= 90 else [255, 209, 102, 195] if priority >= 60 else [0, 196, 255, 180]
        for idx, (dx, dy) in enumerate(offsets):
            share = pop / len(offsets) * (1.12 if idx == 0 else 0.98)
            columns.append({
                "lon": poi["lon"] + dx,
                "lat": poi["lat"] + dy,
                "elevation": min(1150, 70 + math.sqrt(share) * 36),
                "radius": 38 if idx else 54,
                "color": color,
                "title": f"{poi['name']} · population volume",
                "details": (
                    f"Illustrative 3D population volume<br/>Estimated local presence share: {share:.0f}<br/>"
                    f"Vulnerability index: {poi.get('vulnerability', 0)}<br/>Priority score: {priority:.1f}"
                ),
            })
    return columns


def worldpop_3d_layer(prefix: str) -> Optional[pdk.Layer]:
    if not show_worldpop_3d:
        return None
    data = worldpop_3d_data()
    if not data:
        return None
    return pdk.Layer(
        "ColumnLayer",
        id=f"{prefix}-worldpop-3d",
        data=data,
        get_position="[lon, lat]",
        get_elevation="elevation",
        elevation_scale=1.15,
        radius=48,
        get_fill_color="color",
        disk_resolution=24,
        coverage=0.88,
        opacity=0.82,
        pickable=True,
        auto_highlight=True,
    )


def illustrative_building_data() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    source_points = [*pois_live, *resource_map_data()]
    for idx, item in enumerate(source_points):
        if idx > 34:
            break
        base_lon, base_lat = float(item["lon"]), float(item["lat"])
        base_h = 24 if item.get("type") in {"village", "residential"} else 38 if item.get("type") == "hospital" else 18
        for j, (dx, dy, scale) in enumerate([
            (-0.00022, -0.00016, 1.0),
            (0.00020, -0.00008, .72),
            (-0.00005, 0.00021, .84),
        ]):
            w = 0.00012 * scale
            h = 0.00009 * scale
            lon, lat = base_lon + dx, base_lat + dy
            poly = [[lon-w, lat-h], [lon+w, lat-h], [lon+w, lat+h], [lon-w, lat+h], [lon-w, lat-h]]
            items.append({
                "polygon": poly,
                "height": base_h * (1 + (j % 2) * 0.35),
                "color": [102, 126, 148, 92] if j else [137, 159, 178, 112],
                "title": "Illustrative 3D urban context",
                "details": "Context massing for spatial orientation; not surveyed building height.",
            })
    return items


def illustrative_buildings_layer(prefix: str) -> Optional[pdk.Layer]:
    if not show_3d_buildings:
        return None
    data = illustrative_building_data()
    if not data:
        return None
    return pdk.Layer(
        "PolygonLayer",
        id=f"{prefix}-buildings-3d",
        data=data,
        get_polygon="polygon",
        get_fill_color="color",
        get_elevation="height",
        extruded=True,
        wireframe=True,
        get_line_color=[183, 202, 216, 90],
        line_width_min_pixels=1,
        pickable=True,
        opacity=0.62,
    )


def _nearest_traffic_roadblock_points() -> List[Dict[str, Any]]:
    candidate_segments = [seg for seg in traffic_segments if len(seg.get("path", [])) >= 4]
    if not candidate_segments:
        return [
            {"id": "RB-A", "name": "North access roadblock", "lat": active.lat + 0.006, "lon": active.lon - 0.004, "type": "roadblock", "glyph": MAP_SYMBOL_GLYPH["roadblock"]},
            {"id": "RB-B", "name": "South access roadblock", "lat": active.lat - 0.006, "lon": active.lon + 0.004, "type": "roadblock", "glyph": MAP_SYMBOL_GLYPH["roadblock"]},
        ]
    segment = min(candidate_segments, key=lambda seg: _distance_to_path_m(active.lat, active.lon, seg["path"]))
    path = segment["path"]
    idx = min(range(len(path)), key=lambda i: dist_m(active.lat, active.lon, path[i][1], path[i][0]))
    step = max(2, len(path) // 10)
    a = path[max(0, idx-step)]
    b = path[min(len(path)-1, idx+step)]
    return [
        {"id": "RB-A", "name": f"{segment.get('name','Road')} · upstream roadblock", "lat": a[1], "lon": a[0], "type": "roadblock", "glyph": MAP_SYMBOL_GLYPH["roadblock"]},
        {"id": "RB-B", "name": f"{segment.get('name','Road')} · downstream roadblock", "lat": b[1], "lon": b[0], "type": "roadblock", "glyph": MAP_SYMBOL_GLYPH["roadblock"]},
    ]


def mission_targets_for_kind(kind: str) -> List[Dict[str, Any]]:
    ranking = current_priority_ranking()
    vulnerable_targets = [{
        "id": f"TARGET-{item['id']}",
        "name": item["name"],
        "lat": item["lat"],
        "lon": item["lon"],
        "type": "population",
        "glyph": item.get("glyph", "🏘"),
        "details": f"Population protection priority · score {item['priority_score']:.1f}",
    } for item in ranking[:4]]
    incident_target = {
        "id": "TARGET-INCIDENT",
        "name": "Leak source / containment point",
        "lat": active.lat,
        "lon": active.lon,
        "type": "incident",
        "glyph": MAP_SYMBOL_GLYPH["incident"],
        "details": "Source control and technical containment",
    }
    roadblocks = _nearest_traffic_roadblock_points()
    hospitals = [{
        "id": f"TARGET-{item['id']}",
        "name": item["name"],
        "lat": item["lat"],
        "lon": item["lon"],
        "type": "hospital",
        "glyph": MAP_SYMBOL_GLYPH["hospital"],
        "details": f"Receiving hospital · {item.get('available_beds', 0)} beds available",
    } for item in hospital_map_data()]
    shelters = [{
        "id": f"TARGET-{item['id']}",
        "name": item["name"],
        "lat": item["lat"],
        "lon": item["lon"],
        "type": "shelter",
        "glyph": MAP_SYMBOL_GLYPH["shelter"],
        "details": f"Evacuation shelter · capacity {item['capacity']:,}",
    } for item in SHELTERS]
    environmental = []
    if WATER_ZONES:
        lat, lon = _polygon_centroid(WATER_ZONES[0].get("polygon", []))
        environmental.append({"id": "TARGET-WATER", "name": WATER_ZONES[0].get("name", "Water receptor"), "lat": lat, "lon": lon, "type": "environment", "glyph": MAP_SYMBOL_GLYPH["water"], "details": "Environmental protection mission"})
    if DRAINS:
        environmental.append({"id": "TARGET-DRAIN", "name": DRAINS[0]["name"], "lat": DRAINS[0]["lat"], "lon": DRAINS[0]["lon"], "type": "environment", "glyph": MAP_SYMBOL_GLYPH["environment"], "details": "Drain and runoff protection"})
    plume = incident_state.get("plume_polygon", [])
    if len(plume) >= 3:
        edge_lon = float(np.mean([plume[1][0], plume[2][0]]))
        edge_lat = float(np.mean([plume[1][1], plume[2][1]]))
        environmental.append({"id": "TARGET-PLUME-EDGE", "name": "Downwind plume-edge monitoring point", "lat": edge_lat, "lon": edge_lon, "type": "sensor", "glyph": MAP_SYMBOL_GLYPH["sensor"], "details": "Mobile sensor deployment point"})

    if kind in {"fire", "hazmat"}:
        return [incident_target] + roadblocks
    if kind == "police":
        return vulnerable_targets[:2] + roadblocks + [incident_target]
    if kind == "ambulance":
        return vulnerable_targets[:3] + hospitals
    if kind == "bus":
        return vulnerable_targets[:3] + shelters
    if kind == "environment":
        return environmental + [incident_target]
    if kind == "sensor":
        return [item for item in environmental if item.get("type") == "sensor"] + vulnerable_targets[:2] + environmental
    return [incident_target]


def selected_mission_target(kind: str) -> Dict[str, Any]:
    targets = mission_targets_for_kind(kind)
    if not targets:
        return {"id": "TARGET-INCIDENT", "name": "Incident source", "lat": active.lat, "lon": active.lon, "glyph": MAP_SYMBOL_GLYPH["incident"], "details": "Incident source"}
    selected_id = st.session_state.get("selected_mission_target_ids", {}).get(kind)
    selected = next((item for item in targets if item["id"] == selected_id), None)
    if selected is None:
        selected = targets[0]
        st.session_state.selected_mission_target_ids[kind] = selected["id"]
    return selected


def build_mission_route_options(
    resource: Resource,
    target: Dict[str, Any],
    traffic: List[Dict[str, Any]],
    backend: str,
    amap_key: str,
    ors_key: str,
) -> Dict[str, RouteResult]:
    """Route a resource from its real base to a mission-specific destination."""
    profile = "driving-hgv" if resource.kind in {"fire", "hazmat", "bus"} else "driving-car"
    coordinates = ((resource.lon, resource.lat), (target["lon"], target["lat"]))
    candidates: List[RouteResult] = []

    if ors_key or ors_is_local():
        result = fetch_ors_directions(
            ors_key,
            coordinates,
            profile=profile,
            alternatives=3,
            preference="fastest",
            hazmat=False,
        )
        if not result.get("ok"):
            result = fetch_ors_directions(
                ors_key,
                coordinates,
                profile="driving-car",
                alternatives=1,
                preference="fastest",
                hazmat=False,
            )
        if result.get("ok"):
            for idx, raw in enumerate(result.get("routes", []) or []):
                candidate = route_result_from_path(
                    f"mission-ors-{idx}",
                    f"Street alternative {idx + 1} to {target['name']}",
                    raw["path"],
                    active,
                    traffic,
                    f"Local OpenRouteService {raw.get('profile', profile)}",
                    f"Real-street route from {resource.name} to the assigned mission destination: {target['name']}.",
                    1.0,
                )
                if raw.get("distance_km"):
                    candidate.distance_km = raw["distance_km"]
                if raw.get("eta_min"):
                    candidate.eta_min = raw["eta_min"]
                candidate.composite_score = round(
                    candidate.eta_min * 0.33
                    + candidate.exposure_score * 0.30
                    + candidate.environment_score * 0.18
                    + candidate.congestion_score * 0.10
                    + candidate.responder_risk * 0.09,
                    1,
                )
                candidates.append(candidate)

    if not candidates:
        raw_routes = fetch_osrm_driving_routes(
            (resource.lat, resource.lon),
            (target["lat"], target["lon"]),
            3,
        )
        for idx, raw in enumerate(raw_routes or []):
            candidate = route_result_from_path(
                f"mission-osrm-{idx}",
                f"Street alternative {idx + 1} to {target['name']}",
                raw["path"],
                active,
                traffic,
                "OSRM real streets",
                f"Road-network route from {resource.name} to {target['name']}.",
                1.0,
            )
            candidate.distance_km = raw.get("distance_km") or candidate.distance_km
            candidate.eta_min = raw.get("eta_min") or candidate.eta_min
            candidates.append(candidate)

    if not candidates:
        path = real_street_path_between(
            (resource.lat, resource.lon),
            (target["lat"], target["lon"]),
        )
        if path and len(path) >= 2:
            candidates.append(route_result_from_path(
                "mission-local",
                f"Street route to {target['name']}",
                path,
                active,
                traffic,
                "Local real-street fallback",
                f"Road-network route from {resource.name} to {target['name']}.",
                1.0,
            ))

    if not candidates:
        return unavailable_route_options(resource, active)

    fastest_base = min(candidates, key=lambda item: (item.eta_min, item.distance_km))
    safest_base = min(candidates, key=lambda item: item.exposure_score * 0.58 + item.environment_score * 0.42)
    low_traffic_base = min(candidates, key=lambda item: (item.congestion_score, item.eta_min))
    recommended_base = min(candidates, key=lambda item: item.composite_score)

    def clone(base: RouteResult, route_id: str, label: str, reason: str) -> RouteResult:
        return RouteResult(**{
            **asdict(base),
            "id": route_id,
            "label": label,
            "explanation": f"{reason} Mission destination: {target['name']}.",
        })

    return {
        "fastest": clone(fastest_base, "fastest", f"Fastest route to {target['name']}", "Lowest estimated travel time."),
        "safest": clone(safest_base, "safest", f"Lowest-exposure route to {target['name']}", "Lowest combined human and environmental exposure."),
        "low_traffic": clone(low_traffic_base, "low_traffic", f"Lowest-congestion route to {target['name']}", "Lowest modeled congestion."),
        "recommended": clone(recommended_base, "recommended", f"AI recommended route to {target['name']}", "Best balance of ETA, exposure, environmental sensitivity and congestion."),
    }


def workflow_stage_state() -> List[Dict[str, str]]:
    resource_kinds = [kind for kind, qty in st.session_state.resource_quantities.items() if qty > 0]
    routes_ready = False
    if resource_kinds:
        routes_ready = True
        for kind in resource_kinds:
            route = selected_route_for_kind(kind)
            if route is None or len(route.path) < 2:
                routes_ready = False
                break
    conflicts_ready = bool(selected_decisions("traffic") or selected_decisions("environment"))
    recommend_ready = minimum_plan_ready()[0]
    human_done = bool(st.session_state.plan_confirmed)
    flags = [
        True,
        bool(current_priority_ranking()),
        routes_ready,
        conflicts_ready,
        recommend_ready,
        human_done,
    ]
    current_index = next((idx for idx, flag in enumerate(flags) if not flag), len(flags)-1)
    definitions = [
        ("Observe", "Incident · wind · closures"),
        ("Rank targets", "Sensitivity · hazard · population"),
        ("Generate routes", "Responder · evacuation · access"),
        ("Check conflicts", "Plume · traffic · environment"),
        ("Recommend", "Target · resource · access"),
        ("Await human", "No automatic dispatch"),
    ]
    result = []
    for idx, (name, desc) in enumerate(definitions):
        status = "done" if flags[idx] else "active" if idx == current_index else "waiting"
        result.append({"name": name, "desc": desc, "status": status, "number": str(idx+1)})
    return result


def render_agent_workflow_tracker() -> None:
    stages = workflow_stage_state()
    completed = sum(1 for item in stages if item["status"] == "done")
    items = []
    for item in stages:
        symbol = "✓" if item["status"] == "done" else item["number"]
        items.append(
            f'<div class="sr-workflow-item {item["status"]}"><div class="sr-workflow-dot">{symbol}</div>'
            f'<div><div class="sr-workflow-name">{item["name"]}</div><div class="sr-workflow-desc">{item["desc"]}</div></div></div>'
        )
    st.markdown(
        f'<div class="sr-workflow"><div class="sr-workflow-title">Agent workflow</div>{"".join(items)}'
        f'<div class="sr-workflow-progress">{completed} of 6 stages completed</div></div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# GLOBAL CONTROLS AND LIVE STATE
# =============================================================================
active = active_incident()
now = datetime.now()

# The former “Operational workspace” radio was removed from rendering and
# state synchronization. Navigation now uses explicit buttons and session state.
page = st.session_state.get("nav_page", "Central & Prevention")
active = active_incident()

_context = incident_context_bundle(active)
POIS = _context["pois"]
SHELTERS = _context["shelters"]
RESOURCES = _context["resources"]
WATER_ZONES = _context["water_zones"]
DRAINS = _context["drains"]
HAZMAT_CORRIDORS = _context["hazmat_corridors"]
BASE_TRAFFIC_SEGMENTS = _context["traffic_segments"]
ORDINARY_ACCIDENTS = _context["ordinary_accidents"]
HAZMAT_TRUCKS = _context["hazmat_trucks"]
SENSORS = _context["sensors"]
for resource in RESOURCES:
    st.session_state.dispatch_status.setdefault(resource.id, resource.status)

if "ors_api_key_input" not in st.session_state:
    st.session_state.ors_api_key_input = get_ors_key()

# Fixed operational configuration. The former “Operational controls” expander
# and its low-value duplicate inputs were removed from the public interface.
data_mode = "Simulated live"
routing_backend = "Automatic real streets"
use_basemap = True
ors_api_key = "" if ors_is_local() else get_ors_key()

show_population_layer = True
show_resources_layer = True
show_routes_layer = True
show_traffic_layer = True
show_water_layer = True
show_environment_layer = True
show_labels_layer = True
show_3d_buildings = False
show_worldpop_3d = False

# Stable scenario inputs used by the prevention and live-incident models.
wind_speed_kmh = 16
wind_direction = 115
rain_mm_h = 18
temperature_c = 34
road_wetness = 0.65
traffic_index = 7.4
hazmat_flow = 28
evacuation_capacity_ppm = 95
setup_delay_min = 7
shelter_quality = 0.68

amap_key = get_amap_key()
if data_mode.startswith("AMap") or routing_backend.startswith("AMap"):
    if not amap_key:
        st.warning("AMap key not found; automatic fallback will be used")
if (routing_backend.startswith("OpenRouteService") or routing_backend.startswith("Automatic")) and not ors_is_local() and not ors_api_key:
    st.warning("Remote OpenRouteService requires an API key")
if routing_backend.startswith("OSMnx") and not OSMNX_AVAILABLE:
    st.warning("OSMnx is not installed; automatic fallback will be used")

hour = 19 if active.id == HISTORICAL_INCIDENT_ID else now.hour
weekday = True if active.id == HISTORICAL_INCIDENT_ID else now.weekday() < 5
pois_live = build_live_pois(hour, weekday)
PROTECTED_AREAS, PROTECTED_AREA_SOURCE = load_public_protected_areas(
    active.lat, active.lon, include_plan_references=active.id != HISTORICAL_INCIDENT_ID
)
if active.id == HISTORICAL_INCIDENT_ID:
    PROTECTED_AREAS.extend(copy.deepcopy(HISTORICAL_ECO_AREAS))
    PROTECTED_AREA_SOURCE += " · reported agricultural-impact area added"
BASE_TRAFFIC_SEGMENTS, BASE_TRAFFIC_GEOMETRY_SOURCE = streetify_path_collection(
    BASE_TRAFFIC_SEGMENTS, ors_api_key, profile="driving-car", hazmat=False
)
HAZMAT_CORRIDORS, HAZMAT_CORRIDOR_SOURCE = streetify_path_collection(
    HAZMAT_CORRIDORS, ors_api_key, profile="driving-hgv", hazmat=True
)
traffic_segments, traffic_source_label = combined_traffic_source(
    data_mode,
    amap_key,
    st.session_state.demo_tick,
    traffic_index,
    rain_mm_h,
    road_wetness,
    active,
)
if data_mode.startswith("Simulated") and not traffic_segments:
    traffic_source_label = "Street geometry unavailable - schematic traffic lines hidden"
incident_state = compute_incident_state(
    active,
    wind_speed_kmh,
    wind_direction,
    rain_mm_h,
    temperature_c,
    traffic_index,
    evacuation_capacity_ppm,
    setup_delay_min,
    shelter_quality,
    st.session_state.demo_tick,
    pois_live,
)
prevention_value, prevention_level, prevention_factors = prevention_score(
    rain_mm_h,
    temperature_c,
    road_wetness,
    traffic_index,
    hazmat_flow,
    len(ORDINARY_ACCIDENTS),
)
preventive_alerts = build_preventive_alerts(
    rain_mm_h,
    temperature_c,
    road_wetness,
    traffic_index,
    hazmat_flow,
    prevention_value,
)


# =============================================================================
# TOP BAR AND METRICS
# =============================================================================
st.markdown(
    f"""
<div class="sr-top">
 <div class="sr-brand">{skyroute_logo_html()}<div><div class="sr-sub">{"Huai’an live chlorine response simulation" if active.id == HISTORICAL_INCIDENT_ID else "Global emergency prevention, routing and incident command"}</div></div></div>
 <div class="sr-topstats">
  <div class="sr-topstat">Workspace<b>{page}</b></div>
  <div class="sr-topstat">Incident<b>{active.id}</b></div>
  <div class="sr-topstat">Traffic<b>{traffic_source_label[:42]}</b></div>
  <div class="sr-topstat">Authority<b>Human confirmation required</b></div>
 </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="sr-global-nav"><div class="sr-global-nav-label">Primary navigation</div></div>', unsafe_allow_html=True)
nav_city, nav_incident, nav_cases, nav_ai = st.columns([1.05, 1.18, 1.0, 1.32])
with nav_city:
    if st.button("City command", key="global-nav-city", use_container_width=True, disabled=page == "Central & Prevention"):
        navigate_to("Central & Prevention")
with nav_incident:
    if st.button("Incident command", key="global-nav-incident", use_container_width=True, disabled=page == "Incident Command"):
        navigate_to("Incident Command", st.session_state.get("incident_tab", "Overview"))
with nav_cases:
    if st.button("Cases & data", key="global-nav-cases", use_container_width=True, disabled=page == "Cases & Data"):
        navigate_to("Cases & Data")
with nav_ai:
    if st.button("✦ Ask SkyRoute AI", key="global-nav-agent", type="primary", use_container_width=True, disabled=page == "SkyRoute AI Copilot"):
        open_agent()

metric_items = [
    ("Threat", active.threat, f"{active.substance} · {active.quantity_t:.0f} t", RED),
    ("Protective zone", f"{incident_state['protective_distance']/1000:.1f} km", f"isolation {incident_state['isolation_distance']} m", AMBER),
    ("People exposed", f"{incident_state['exposed_population']:,}", f"{len(incident_state['exposed_pois'])} mapped settings", PURPLE),
    ("Agent action", incident_state["recommendation"], f"confidence {incident_state['confidence']:.0%} · {len(selected_decisions())} decisions", CYAN),
    ("Prevention risk", f"{prevention_value}/100", prevention_level, TEAL if prevention_value < 35 else AMBER if prevention_value < 70 else RED),
]
metric_cols = st.columns(5)
for col, (key, value, detail, color) in zip(metric_cols, metric_items):
    with col:
        st.markdown(
            f'<div class="sr-card" style="border-top:2px solid {color}"><div class="k">{key}</div><div class="v">{value}</div><div class="d">{detail}</div></div>',
            unsafe_allow_html=True,
        )


# =============================================================================
# SHARED MAP DATA BUILDERS
# =============================================================================
def incident_map_data() -> List[Dict[str, Any]]:
    return [
        {
            **asdict(inc),
            "color": THREAT_COLOR[inc.threat] + [235],
            "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": f"{inc.id} · {inc.substance}",
            "details": f"{inc.threat}<br/>{inc.road}<br/>{inc.description}",
        }
        for inc in INCIDENTS
    ]



def resource_map_data() -> List[Dict[str, Any]]:
    output = []
    for resource in RESOURCES:
        status = st.session_state.dispatch_status.get(resource.id, resource.status)
        output.append({
            **asdict(resource),
            "status": status,
            "color": AGENCY_COLOR.get(resource.kind, [255, 255, 255]) + [235],
            "outline_color": STATUS_COLOR.get(status, [148, 163, 184]) + [250],
            "glyph": AGENCY_GLYPH.get(resource.kind, "●"),
            "title": resource.name,
            "details": (
                f"{AGENCY_LABEL.get(resource.kind, resource.kind)} base / unit<br/>"
                f"Status: {status}<br/>Capacity: {resource.capacity}"
            ),
        })
    return output

def traffic_path_data() -> List[Dict[str, Any]]:
    output = []
    for segment in traffic_segments:
        if len(segment.get("path", [])) < 2:
            continue
        output.append({
            **segment,
            "color": segment.get("color", traffic_color(segment.get("congestion", 0.5))),
            "width": 8,
            "title": segment.get("title", segment.get("name", "Traffic segment")),
            "details": segment.get("details", f"Speed: {segment.get('speed', 0)} km/h"),
        })
    return output



def selected_route_for_kind(kind: str) -> Optional[RouteResult]:
    resource_id = st.session_state.selected_resource_ids.get(kind)
    target = selected_mission_target(kind)
    if not resource_id:
        candidates = [
            r for r in RESOURCES
            if r.kind == kind and st.session_state.dispatch_status.get(r.id, r.status) != "Busy"
        ]
        if not candidates:
            return None
        resource = min(candidates, key=lambda r: dist_m(r.lat, r.lon, target["lat"], target["lon"]))
        st.session_state.selected_resource_ids[kind] = resource.id
    else:
        resource = next((r for r in RESOURCES if r.id == resource_id), None)
        if resource is None:
            return None
    options = build_mission_route_options(resource, target, traffic_segments, routing_backend, amap_key, ors_api_key)
    route_key = st.session_state.selected_routes.get(kind, "recommended")
    return options.get(route_key) or options["recommended"]


def deployed_vehicle_data() -> List[Dict[str, Any]]:
    output = []
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        resource_id = st.session_state.selected_resource_ids.get(kind)
        resource = next((r for r in RESOURCES if r.id == resource_id), None)
        route = selected_route_for_kind(kind)
        target = selected_mission_target(kind)
        if resource is None or route is None:
            continue
        status = st.session_state.dispatch_status.get(resource.id, resource.status)
        if status not in {"En route", "On scene"}:
            position = [resource.lon, resource.lat]
            progress = 0.0
        else:
            start_tick = st.session_state.dispatch_start_tick.get(resource.id, st.session_state.demo_tick)
            elapsed = max(0, st.session_state.demo_tick - start_tick)
            progress = clamp(elapsed / max(1, route.eta_min), 0, 1)
            position = interpolate_position(route.path, progress)
            if progress >= 1 and status != "On scene":
                st.session_state.dispatch_status[resource.id] = "On scene"
                status = "On scene"
        output.append({
            "id": resource.id,
            "kind": kind,
            "status": status,
            "lon": position[0],
            "lat": position[1],
            "color": AGENCY_COLOR[kind] + [245],
            "glyph": AGENCY_GLYPH[kind],
            "title": f"{AGENCY_LABEL[kind]} · {resource.name}",
            "details": (
                f"Status: {status}<br/>Units selected: {quantity}<br/>"
                f"Mission: {target['name']}<br/>Route progress: {progress:.0%}"
            ),
        })
    return output


def route_layers_for_plan(alpha_other: int = 185) -> List[pdk.Layer]:
    if not show_routes_layer:
        return []
    paths = []
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        route = selected_route_for_kind(kind)
        target = selected_mission_target(kind)
        resource_id = st.session_state.selected_resource_ids.get(kind)
        resource = next((item for item in RESOURCES if item.id == resource_id), None)
        if route is None or len(route.path) < 2:
            continue
        status = st.session_state.dispatch_status.get(resource.id, resource.status) if resource else "Planned"
        paths.append({
            "path": route.path,
            "color": AGENCY_COLOR[kind] + [min(245, alpha_other + 35)],
            "width": 8,
            "title": f"{AGENCY_LABEL[kind]} → {target['name']}",
            "details": (
                f"Origin: {resource.name if resource else 'Selected agency base'}<br/>"
                f"Destination: {target['name']}<br/>Mission: {AGENCY_LABEL[kind]} deployment<br/>"
                f"Status: {status}<br/>ETA {route.eta_min} min · {route.distance_km} km<br/>"
                f"Backend: {route.backend}"
            ),
        })
    return path_layers_with_halo("plan-resource-routes", paths, 8, halo_extra=5) if paths else []

def transparent_plot_layout(fig: go.Figure, height: int = 270) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=36, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Poppins"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def render_weather_dashboard() -> None:
    humidity = int(clamp(82 - (temperature_c - 24) * 1.25 + rain_mm_h * 0.42, 32, 98))
    feels_like = round(temperature_c + humidity / 100 * 3.5 - wind_speed_kmh * 0.035, 1)
    max_temp = round(temperature_c + 3.2, 1)
    min_temp = round(temperature_c - 5.4, 1)
    precip_probability = int(clamp(rain_mm_h * 2.2 + road_wetness * 35, 5, 100))
    condition = "Heavy rain" if rain_mm_h >= 25 else "Rain" if rain_mm_h > 2 else "Hot and cloudy" if temperature_c >= 32 else "Cloudy"
    icon = "⛈️" if rain_mm_h >= 25 else "🌧️" if rain_mm_h > 2 else "🌤️"
    st.markdown(
        f"""<div class="sr-weather"><div class="sr-weather-main"><div><div class="sr-small">NANJING · OPERATIONAL WEATHER</div><div class="sr-weather-temp">{temperature_c}°</div><div class="sr-body">{condition} · feels like {feels_like}°C</div></div><div class="sr-weather-icon">{icon}</div></div><div class="sr-weather-grid"><div class="sr-weather-cell">Humidity<b>{humidity}%</b></div><div class="sr-weather-cell">Maximum<b>{max_temp}°C</b></div><div class="sr-weather-cell">Minimum<b>{min_temp}°C</b></div><div class="sr-weather-cell">Precipitation<b>{precip_probability}%</b></div><div class="sr-weather-cell">Rain rate<b>{rain_mm_h} mm/h</b></div><div class="sr-weather-cell">Wind<b>{wind_label(wind_direction)} {wind_speed_kmh} km/h</b></div><div class="sr-weather-cell">Road surface<b>{road_wetness:.0%} wet</b></div><div class="sr-weather-cell">Visibility<b>{max(1.8, 12-rain_mm_h*.18):.1f} km</b></div></div></div>""",
        unsafe_allow_html=True,
    )
    hours = [f"+{hour}h" for hour in range(0, 7)]
    temperatures = [round(temperature_c + math.sin((hour + 1) / 2.2) * 1.8 - hour * .28, 1) for hour in range(7)]
    precipitation = [int(clamp(precip_probability + math.sin(hour * 1.2) * 18 - hour * 3, 0, 100)) for hour in range(7)]
    st.markdown(
        '<div class="sr-forecast-head"><div class="title">Next 6 hours · operational forecast</div>'
        '<div class="sub">Temperature trend, precipitation probability and road-operability outlook</div></div>',
        unsafe_allow_html=True,
    )
    fig = go.Figure()
    # Low-opacity underlays create a restrained neon glow without reducing legibility.
    fig.add_trace(go.Scatter(x=hours, y=temperatures, mode="lines", showlegend=False, hoverinfo="skip", line=dict(width=15, color="rgba(213,242,109,.07)")))
    fig.add_trace(go.Scatter(x=hours, y=temperatures, mode="lines", showlegend=False, hoverinfo="skip", line=dict(width=8, color="rgba(213,242,109,.14)")))
    fig.add_trace(go.Scatter(
        x=hours, y=temperatures, mode="lines+markers", name="Temperature °C",
        line=dict(width=3, color="#D5F26D"),
        marker=dict(size=8, color="#D5F26D", line=dict(width=1, color="#F2F6E8")),
    ))
    fig.add_trace(go.Bar(
        x=hours, y=precipitation, name="Precipitation %", yaxis="y2",
        marker=dict(color="rgba(82,161,190,.48)", line=dict(color="#52A1BE", width=1)),
    ))
    fig.update_layout(
        height=255,
        margin=dict(l=12, r=12, t=56, b=18),
        paper_bgcolor="rgba(6,17,14,.97)",
        plot_bgcolor="rgba(6,17,14,.74)",
        font=dict(color=TEXT, family="Poppins"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0,
            bgcolor="rgba(6,17,14,.78)", bordercolor="rgba(213,242,109,.30)", borderwidth=1,
            font=dict(size=10),
        ),
        xaxis=dict(showgrid=False, zeroline=False, color=MUTED),
        yaxis=dict(title="°C", showgrid=True, gridcolor="rgba(213,242,109,.08)", zeroline=False, color=MUTED),
        yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100], showgrid=False, zeroline=False, color=BLUE),
        bargap=.42,
        shapes=[dict(type="rect", xref="paper", yref="paper", x0=0, y0=0, x1=1, y1=1, line=dict(color="rgba(213,242,109,.62)", width=1), fillcolor="rgba(0,0,0,0)")],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_prevention_factor_chart() -> None:
    labels = [name.replace("_", " ").title() for name in prevention_factors]
    values = [round(value * 100) for value in prevention_factors.values()]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", text=[f"{v}%" for v in values], textposition="outside"))
    fig.update_layout(title="AI predictive risk contribution", xaxis=dict(range=[0, 110], title="Contribution", showgrid=False), yaxis=dict(autorange="reversed"))
    st.plotly_chart(transparent_plot_layout(fig, 280), use_container_width=True, config={"displayModeBar": False})


def render_route_comparison(options: Dict[str, RouteResult], selected_key: str) -> None:
    routes = list(options.items())
    categories = ["ETA", "Exposure", "Environment", "Congestion", "Responder safety"]
    fig = go.Figure()
    maxima = [
        max([route.eta_min for _, route in routes] + [1]),
        max([route.exposure_score for _, route in routes] + [1]),
        max([route.environment_score for _, route in routes] + [1]),
        10,
        max([route.responder_risk for _, route in routes] + [1]),
    ]
    for key, route in routes:
        raw = [route.eta_min, route.exposure_score, route.environment_score, route.congestion_score, route.responder_risk]
        # Lower is better, so invert for an intuitive larger-is-better radar.
        scores = [round(100 * (1 - min(value / maximum, 1)), 1) for value, maximum in zip(raw, maxima)]
        rgb = ROUTE_OBJECTIVE_COLOR.get(key, [255, 255, 255])
        selected = key == selected_key
        line_color = f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
        fill_alpha = .24 if selected else .055
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{fill_alpha})",
            line=dict(color=line_color, width=3.6 if selected else 1.6),
            marker=dict(color=line_color, size=5 if selected else 3),
            name=route.label,
            opacity=1 if selected else .58,
            hovertemplate=(
                f"<b>{route.label}</b><br>ETA: {route.eta_min} min<br>Distance: {route.distance_km} km"
                "<br>%{theta}: %{r:.0f}/100<extra></extra>"
            ),
        ))
    fig.update_layout(
        title=dict(text="Route objectives · higher score is operationally better", x=.02, font=dict(size=13, color="#FFFFFF")),
        polar=dict(
            bgcolor="rgba(3,11,20,.72)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(255,255,255,.13)", linecolor="rgba(255,255,255,.16)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,.13)", linecolor="rgba(255,255,255,.16)", tickfont=dict(size=10, color="#DCE9F2")),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-.08, xanchor="left", x=0, font=dict(size=9)),
        margin=dict(l=24, r=24, t=48, b=60),
    )
    st.plotly_chart(transparent_plot_layout(fig, 365), use_container_width=True, config={"displayModeBar": False})


def resource_status_counts() -> Dict[str, int]:
    counts = {"Available": 0, "Busy": 0, "En route": 0, "On scene": 0}
    for resource in RESOURCES:
        status = st.session_state.dispatch_status.get(resource.id, resource.status)
        counts[status] = counts.get(status, 0) + resource.units
    return counts


def render_resource_availability() -> None:
    counts = resource_status_counts()
    chart_col, cards_col = st.columns([.78, 1.22])
    with chart_col:
        order = ["Available", "Requested", "En route", "On scene", "Busy"]
        labels = [status for status in order if counts.get(status, 0) > 0]
        values = [counts[status] for status in labels]
        status_hex = {
            "Available": "#00FF85",
            "Requested": "#FFD60A",
            "En route": "#00E5FF",
            "On scene": "#FFFFFF",
            "Busy": "#FF3B30",
        }
        total_units = sum(values)
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=.69,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[status_hex[label] for label in labels], line=dict(color="#06101A", width=3)),
            textinfo="value",
            textposition="inside",
            textfont=dict(size=11, color="#06101A"),
            hovertemplate="<b>%{label}</b><br>%{value} units · %{percent}<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Fleet readiness", x=.03, font=dict(size=13, color="#FFFFFF")),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-.08, xanchor="left", x=0, font=dict(size=8.5)),
            annotations=[dict(
                text=f"<b>{total_units}</b><br><span style='font-size:9px'>TOTAL UNITS</span>",
                x=.5, y=.5, showarrow=False, font=dict(size=18, color="#FFFFFF"),
            )],
            margin=dict(l=8, r=8, t=44, b=54),
        )
        st.plotly_chart(transparent_plot_layout(fig, 285), use_container_width=True, config={"displayModeBar": False})
    with cards_col:
        cards = []
        for kind, label in AGENCY_LABEL.items():
            candidates = [resource for resource in RESOURCES if resource.kind == kind]
            available = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) == "Available")
            busy = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) == "Busy")
            moving = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) in {"En route", "On scene"})
            color = "#%02X%02X%02X" % tuple(AGENCY_COLOR.get(kind, [255, 255, 255]))
            cards.append(
                f'<div class="sr-resource-card" style="border-color:{color};box-shadow:inset 3px 0 0 {color},0 0 14px {color}18">'
                f'<div class="n" style="color:{color}">{AGENCY_GLYPH.get(kind,"U")} · {label}</div>'
                f'<div class="s">Available: <b>{available}</b><br/>Busy: <b>{busy}</b><br/>Deployed: <b>{moving}</b></div></div>'
            )
        st.markdown('<div class="sr-resource-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)



def render_resource_plan_cards() -> None:
    configured = False
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        configured = True
        resource_id = st.session_state.selected_resource_ids.get(kind)
        resource = next((item for item in RESOURCES if item.id == resource_id), None)
        route = selected_route_for_kind(kind)
        target = selected_mission_target(kind)
        if resource and route:
            status = st.session_state.dispatch_status.get(resource.id, resource.status)
            st.markdown(
                f'<div class="sr-panel"><div class="sr-title">{AGENCY_GLYPH[kind]} · {AGENCY_LABEL[kind]} · {quantity} unit(s)</div>'
                f'<div class="sr-body"><b>Origin base:</b> {resource.name}<br/><b>Mission destination:</b> {target["name"]}<br/>'
                f'<b>Status:</b> {status}<br/><b>Route:</b> {route.label}<br/><b>ETA:</b> {route.eta_min} min · {route.distance_km} km<br/>'
                f'<b>Backend:</b> {route.backend}</div></div>',
                unsafe_allow_html=True,
            )
    if not configured:
        st.info("No resources have been added to the operational plan yet.")

def render_dispatch_receipt() -> None:
    receipt = st.session_state.get("last_dispatch_receipt")
    if not receipt:
        return
    units_text = " · ".join(receipt["units"]) or "No units"
    st.markdown(
        f"""<div class="sr-receipt"><div class="sr-receipt-title">✓ Dispatch request registered · {receipt['request_id']}</div><div class="sr-body">{units_text}</div><div class="sr-receipt-grid"><div class="sr-receipt-item">Requested at<b>{receipt['requested_at']}</b></div><div class="sr-receipt-item">Mobilisation<b>{receipt['mobilisation_min']} min</b></div><div class="sr-receipt-item">First arrival<b>{receipt['first_arrival_min']} min</b></div><div class="sr-receipt-item">Estimated execution<b>{receipt['execution_min']} min</b></div></div></div>""",
        unsafe_allow_html=True,
    )


def render_ai_command_strip() -> None:
    next_action = "Complete the minimum plan" if not minimum_plan_ready()[0] else "Review and confirm dispatch"
    st.markdown(
        f"""<div class="sr-ai-strip"><div class="sr-ai-grid"><div><div class="sr-ai-label">SkyRoute AI recommendation</div><div class="sr-ai-value">{incident_state['recommendation']}</div><div class="sr-small">Reasoning: plume {incident_state['plume_arrival_min']} min · evacuation {incident_state['evacuation_time_min']} min · traffic {traffic_index}/10</div></div><div><div class="sr-ai-label">Confidence</div><div class="sr-ai-value">{incident_state['confidence']:.0%}</div></div><div><div class="sr-ai-label">Next action</div><div class="sr-ai-value">{next_action}</div></div></div></div>""",
        unsafe_allow_html=True,
    )



def incident_operational_status(incident: Incident) -> str:
    if incident.id == active.id and st.session_state.demo_stage >= 6:
        return "Containment"
    fixed = {
        "NJ-HZ-260717-01": "Active",
        "NJ-HZ-260717-02": "Active",
        "NJ-HZ-260717-03": "Containment",
        "NJ-HZ-260717-04": "Monitoring",
    }
    return fixed.get(incident.id, "Active")


def path_view(path: List[List[float]]) -> Tuple[float, float, float]:
    if not path:
        return 32.160, 118.704, 11.35
    lons = [point[0] for point in path]
    lats = [point[1] for point in path]
    span = max(max(lons) - min(lons), max(lats) - min(lats), 0.001)
    zoom = 13.8 if span < 0.012 else 12.9 if span < 0.026 else 11.9
    return float(np.mean(lats)), float(np.mean(lons)), zoom


def preventive_alternative_path(alert: PreventiveAlert) -> List[List[float]]:
    if alert.id == "PA-FLOW":
        return HAZMAT_CORRIDORS[2]["path"]
    if alert.id == "PA-WET":
        return HAZMAT_CORRIDORS[0]["path"]
    if alert.id == "PA-HEAT":
        return HAZMAT_CORRIDORS[2]["path"]
    return alert.path


def decision_records(extra_options: Optional[List[DecisionOption]] = None) -> List[Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {item["id"]: item for item in selected_decisions() if item.get("id")}
    for option in extra_options or []:
        records.setdefault(option.id, asdict(option))
    return list(records.values())


def evacuation_path(poi: Dict[str, Any], shelter: Dict[str, Any], curve: float = 0.0) -> List[List[float]]:
    street_path = real_street_path_between((poi["lat"], poi["lon"]), (shelter["lat"], shelter["lon"]))
    return street_path if street_path and len(street_path) >= 2 else []


def decision_overlay_layers(prefix: str, extra_options: Optional[List[DecisionOption]] = None) -> List[pdk.Layer]:
    """Render every selected action together, plus the current uncommitted preview."""
    layers: List[pdk.Layer] = []
    selected_ids = set(st.session_state.get("plan_decisions", {}).keys())
    exposed = incident_state["exposed_pois"]

    for record in decision_records(extra_options):
        option_id = record.get("id", "")
        chosen = option_id in selected_ids
        strength = 245 if chosen else 165
        label = "SELECTED" if chosen else "PREVIEW"
        layer_key = re.sub(r"[^a-zA-Z0-9_-]", "-", f"{prefix}-{option_id}")

        if option_id in {"POP-SHELTER", "POP-HYBRID"}:
            zones = []
            for poi in exposed:
                if option_id == "POP-SHELTER" or poi["distance_m"] > incident_state["protective_distance"] * 0.45:
                    zones.append({
                        "polygon": make_circle_polygon(poi["lat"], poi["lon"], poi["buffer_m"] * 0.70),
                        "title": f"{label} · Shelter sector · {poi['name']}",
                        "details": record.get("title", option_id),
                    })
            if zones:
                layers.append(polygon_layer(f"{layer_key}-shelter", zones, [82, 161, 190, 45 if chosen else 24], [82, 161, 190, strength]))

        if option_id in {"POP-PHASE", "POP-HYBRID", "POP-ASSIST"}:
            routes = []
            selected_pois = exposed[:4]
            if option_id == "POP-ASSIST":
                selected_pois = [poi for poi in exposed if poi.get("type") in {"eldercare", "hospital"}] or exposed[:2]
            for idx, poi in enumerate(selected_pois):
                shelter = min(SHELTERS, key=lambda item: dist_m(poi["lat"], poi["lon"], item["lat"], item["lon"]))
                routes.append({
                    "path": evacuation_path(poi, shelter, 0.0014 * (idx - 1)),
                    "color": MAP_LINE_COLOR["evacuation"] + [strength],
                    "width": 8 if chosen else 5,
                    "title": f"{label} · Evacuation route · {poi['name']}",
                    "details": f"{record.get('title', option_id)}<br/>Destination: {shelter['name']}",
                })
            if routes:
                layers.append(path_layer(f"{layer_key}-evacuation", routes, 6))

        if option_id == "TR-CLOSE":
            layers.append(path_layer(f"{layer_key}-closure", [{
                "path": BASE_TRAFFIC_SEGMENTS[1]["path"], "color": MAP_LINE_COLOR["road_closure"] + [strength], "width": 16 if chosen else 11,
                "title": f"{label} · Road closure", "details": record.get("title", option_id),
            }], 14))
        elif option_id == "TR-CORRIDOR":
            route = selected_route_for_kind("fire")
            if route:
                layers.append(path_layer(f"{layer_key}-corridor", [{
                    "path": route.path, "color": MAP_LINE_COLOR["emergency_corridor"] + [strength], "width": 13 if chosen else 8,
                    "title": f"{label} · Emergency green corridor", "details": f"Fire ETA {route.eta_min} min",
                }], 10))
        elif option_id == "TR-HAZMAT":
            layers.append(path_layer(f"{layer_key}-old", [{
                "path": HAZMAT_CORRIDORS[1]["path"], "color": MAP_LINE_COLOR["hazmat_restricted"] + [150], "width": 6,
                "title": "Restricted HazMat route", "details": record.get("title", option_id),
            }], 6))
            layers.append(path_layer(f"{layer_key}-new", [{
                "path": HAZMAT_CORRIDORS[2]["path"], "color": MAP_LINE_COLOR["hazmat_bypass"] + [strength], "width": 11 if chosen else 8,
                "title": f"{label} · HazMat bypass", "details": record.get("title", option_id),
            }], 9))
        elif option_id == "TR-EVAC":
            shelter = SHELTERS[0]
            bus = next(resource for resource in RESOURCES if resource.kind == "bus")
            street_path = real_street_path_between((bus.lat, bus.lon), (shelter["lat"], shelter["lon"]))
            bus_path = street_path or []
            layers.append(path_layer(f"{layer_key}-bus", [{
                "path": bus_path, "color": MAP_LINE_COLOR["evacuation"] + [strength], "width": 12 if chosen else 8,
                "title": f"{label} · Evacuation bus priority", "details": f"Destination: {shelter['name']}",
            }], 10))

        if option_id == "ENV-DRAIN":
            barriers = [{
                "polygon": make_circle_polygon(drain["lat"], drain["lon"], 110),
                "title": f"{label} · Drain barrier · {drain['name']}", "details": record.get("title", option_id),
            } for drain in DRAINS[:2]]
            layers.append(polygon_layer(f"{layer_key}-drains", barriers, [118, 140, 69, 55 if chosen else 28], [118, 140, 69, strength]))
        elif option_id == "ENV-SENSOR":
            proposals = [
                {"lat": active.lat + 0.010, "lon": active.lon + 0.008, "name": "Downwind mobile air sensor"},
                {"lat": 32.1681, "lon": 118.6822, "name": "School verification sensor"},
                {"lat": 32.1555, "lon": 118.7165, "name": "Retention inlet water sensor"},
            ]
            layers += point_layers(f"{layer_key}-sensors", [{
                **point, "type": "sensor", "color": [255, 209, 102, strength], "glyph": MAP_SYMBOL_GLYPH["sensor"],
                "title": f"{label} · {point['name']}", "details": record.get("title", option_id),
            } for point in proposals], 76 if chosen else 62, 13)
        elif option_id == "ENV-BOOM":
            layers.append(path_layer(f"{layer_key}-boom", [{
                "path": [[118.6908, 32.1620], [118.6960, 32.1586], [118.7020, 32.1554]],
                "color": MAP_LINE_COLOR["environmental_containment"] + [strength], "width": 12 if chosen else 8,
                "title": f"{label} · Containment line", "details": record.get("title", option_id),
            }], 10))
    return layers


def render_selected_decision_strip() -> None:
    decisions = selected_decisions()
    if not decisions:
        st.markdown('<div class="sr-decision-summary"><div class="sr-small">No operational decisions selected yet. Preview an action on a functional map, then add it to the shared plan.</div></div>', unsafe_allow_html=True)
        return
    chips = ''.join(
        f'<span class="sr-chip {item.get("category", "")}">✓ {item.get("title", item.get("id", "Decision"))}</span>'
        for item in decisions
    )
    col_summary, col_clear = st.columns([5.2, 1])
    with col_summary:
        st.markdown(
            f'<div class="sr-decision-summary"><span class="sr-plan-count">{len(decisions)}</span> selected decision(s)<br/>{chips}</div>',
            unsafe_allow_html=True,
        )
    with col_clear:
        if st.button("Clear decisions", use_container_width=True):
            st.session_state.plan_decisions = {}
            st.session_state.plan_confirmed = False
            log_event("All operational decisions cleared", "command")
            st.rerun()


# =============================================================================
# PAGE 1 — CENTRAL AND PREVENTION
# =============================================================================
def page_central() -> None:
    st.markdown('<div class="sr-h2">Active incidents and citywide preventive command</div>', unsafe_allow_html=True)

    statuses = {incident.id: incident_operational_status(incident) for incident in INCIDENTS}
    active_count = sum(status == "Active" for status in statuses.values())
    containment_count = sum(status == "Containment" for status in statuses.values())
    monitoring_count = sum(status == "Monitoring" for status in statuses.values())
    c1, c2, c3, c4 = st.columns(4)
    for column, title, value, detail, color in [
        (c1, "Incidents in system", len(INCIDENTS), "all hazardous-material events", CYAN),
        (c2, "Active response", active_count, "requiring immediate command", RED),
        (c3, "In containment", containment_count, "resources already acting", AMBER),
        (c4, "Monitoring", monitoring_count, "stable but under observation", TEAL),
    ]:
        with column:
            st.markdown(f'<div class="sr-card" style="border-top:2px solid {color}"><div class="k">{title}</div><div class="v">{value}</div><div class="d">{detail}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sr-incident-board"><div class="sr-title">Incident command queue</div><div class="sr-small">Open an event directly here or click its marker on the city map.</div></div>', unsafe_allow_html=True)
    incident_cols = st.columns(len(INCIDENTS))
    for column, incident in zip(incident_cols, INCIDENTS):
        status = statuses[incident.id]
        status_class = status.lower()
        with column:
            st.markdown(
                f'<div class="sr-incident-card {"active" if incident.id == active.id else ""}"><span class="sr-incident-status {status_class}">{status}</span><div class="sr-title">{incident.substance} · {incident.threat}</div><div class="sr-small">{incident.id}<br/>{incident.road}<br/>Detected {incident.detected_at}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open command", key=f"hero-open-{incident.id}", type="primary" if incident.id == active.id else "secondary", use_container_width=True):
                st.session_state.active_incident_id = incident.id
                st.session_state.nav_page = "Incident Command"
                st.session_state.incident_tab = "Overview"
                st.session_state.plan_confirmed = False
                log_event(f"Incident opened from command queue: {incident.id}", "incident")
                st.rerun()

    selected_alert = next((item for item in preventive_alerts if item.id == st.session_state.selected_alert_id), None)
    if selected_alert:
        p1, p2 = st.columns([5.2, 1])
        with p1:
            st.markdown(
                f'<div class="sr-map-preview"><div class="sr-title">Map preview · {selected_alert.title}</div><div class="sr-body"><b>Risk segment:</b> red/white · <b>proposed preventive route:</b> cyan<br/>{selected_alert.recommended_action}</div></div>',
                unsafe_allow_html=True,
            )
        with p2:
            if st.button("Clear preview", use_container_width=True):
                st.session_state.selected_alert_id = None
                st.rerun()

    map_col, alert_col = st.columns([1.62, 1])
    with map_col:
        layers: List[pdk.Layer] = public_environment_layers("city")
        layers.append(path_layer("city-traffic", traffic_path_data(), 8))
        corridor_data = []
        for corridor in HAZMAT_CORRIDORS:
            corridor_data.append({
                **corridor,
                "color": ([0, 229, 255, 145] if corridor["risk"] == "Low" else [255, 159, 10, 175] if corridor["risk"] == "Medium" else [255, 45, 149, 210]),
                "width": 4,
                "title": corridor["name"],
                "details": f"HazMat corridor risk: {corridor['risk']}",
            })
        layers.append(path_layer("hazmat-corridors", corridor_data, 4))
        truck_data = []
        for idx, truck in enumerate(HAZMAT_TRUCKS):
            drift = math.sin((st.session_state.demo_tick + idx) / 3) * 0.0012
            truck_data.append({
                **truck, "lon": truck["lon"] + drift, "lat": truck["lat"] + drift * 0.4,
                "type": "truck", "color": [255, 45, 149, 240], "glyph": MAP_SYMBOL_GLYPH["truck"],
                "title": f"HazMat truck {truck['id']}",
                "details": f"Cargo: {truck['substance']}<br/>Speed: {truck['speed']} km/h<br/>Corridor: {truck['route']}",
            })
        layers += point_layers("hazmat-trucks", truck_data, 75, 12)
        layers += point_layers("ordinary-accidents", [{
            **acc, "type": "traffic_incident", "color": [255, 209, 102, 230] if acc["severity"] == "minor" else [255, 89, 94, 235],
            "glyph": MAP_SYMBOL_GLYPH["traffic_incident"], "title": acc["title"], "details": f"{acc['road']}<br/>Severity: {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 60, 11)
        layers += incident_icon_layers("incidents", incident_map_data(), get_size=4, size_scale=13)

        center_lat, center_lon, map_zoom = 32.160, 118.704, 11.35
        if selected_alert:
            proposed_path = preventive_alternative_path(selected_alert)
            layers.append(path_layer("selected-preventive-risk", [{
                "path": selected_alert.path, "color": [255, 89, 94, 235], "width": 17,
                "title": f"Current risk · {selected_alert.title}", "details": selected_alert.reason,
            }], 17))
            layers.append(path_layer("selected-preventive-highlight", [{
                "path": selected_alert.path, "color": [242, 246, 232, 220], "width": 7,
                "title": "Affected segment", "details": selected_alert.recommended_action,
            }], 7))
            if proposed_path:
                layers.append(path_layer("selected-preventive-alternative", [{
                    "path": proposed_path, "color": [0, 217, 255, 250], "width": 12,
                    "title": "AI proposed preventive route", "details": f"Expected risk reduction: {selected_alert.risk_reduction}%",
                }], 12))
            center_lat, center_lon, map_zoom = path_view(selected_alert.path + proposed_path)

        event = render_map(make_deck(layers, center_lat, center_lon, map_zoom, 31, -8, use_basemap), "city-prevention-map", 630, selectable=True)
        selected = selected_objects(event, "incidents-points")
        if selected:
            chosen_id = selected[0].get("id")
            if chosen_id:
                st.session_state.active_incident_id = chosen_id
                st.session_state.nav_page = "Incident Command"
                st.session_state.incident_tab = "Overview"
                st.session_state.plan_confirmed = False
                log_event(f"Incident opened from city map: {chosen_id}", "incident")
                st.rerun()
        city_legend: List[Tuple[str, str, str]] = [
            (INCIDENT_LEGEND_TOKEN, "Hazardous-material incident", "#FF595E"),
            (MAP_SYMBOL_GLYPH["truck"], "HazMat vehicle", "#FF2D95"),
            (MAP_SYMBOL_GLYPH["traffic_incident"], "Ordinary road incident", "#FF595E"),
            ("━", "Traffic: free / slow / congested", "#FFD166"),
            ("━", "HazMat corridor: low / medium / high risk", "#FF9F1C"),
            ("▰", "Environmental / protected receptor", "#00D68F"),
        ]
        if selected_alert:
            city_legend += [
                ("━", "Selected high-risk road segment", "#FF595E"),
                ("━", "AI preventive alternative", "#00D9FF"),
            ]
        render_map_legend(city_legend, "Citywide operational map legend")
        st.caption("Click an incident marker to open its command workspace. Preventive previews visibly highlight the affected segment and the AI alternative.")

    with alert_col:
        st.markdown('<div class="sr-h2">AI preventive alerts</div>', unsafe_allow_html=True)
        st.progress(prevention_value / 100, text=f"Predictive road-incident risk: {prevention_value}/100 · {prevention_level}")
        for alert in preventive_alerts:
            is_preview = st.session_state.selected_alert_id == alert.id
            is_applied = alert.id in st.session_state.prevention_actions
            css = "sr-critical" if alert.severity in {"HIGH", "CRITICAL"} else "sr-good" if alert.severity == "LOW" else ""
            selected_class = " selected" if is_preview else ""
            st.markdown(
                f'<div class="sr-panel{selected_class}"><div class="sr-alert {css}"><div class="sr-title">{alert.severity} · {alert.title}</div><div class="sr-body"><b>{alert.corridor}</b><br/>{alert.reason}<br/><br/><b>AI option:</b> {alert.recommended_action}</div><span class="sr-badge badge-ai">risk -{alert.risk_reduction}%</span><span class="sr-badge">delay +{alert.delay_min} min</span><span class="sr-badge">cost {alert.cost_level}</span>{"<span class=\"sr-badge badge-safe\">✓ applied</span>" if is_applied else ""}</div></div>',
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns(2)
            if b1.button("Showing on map" if is_preview else "Visualise", key=f"view-alert-{alert.id}", disabled=is_preview, use_container_width=True):
                st.session_state.selected_alert_id = alert.id
                log_event(f"Preventive alert visualised: {alert.title}", "prevention")
                st.rerun()
            if b2.button("✓ Applied" if is_applied else "Apply prevention", key=f"apply-alert-{alert.id}", disabled=is_applied, type="primary" if not is_applied else "secondary", use_container_width=True):
                add_prevention_action(alert)
                st.rerun()

    st.markdown('<div class="sr-h2">Operational weather and predictive contribution</div>', unsafe_allow_html=True)
    weather_col, risk_col = st.columns([1.15, 1])
    with weather_col:
        render_weather_dashboard()
    with risk_col:
        st.markdown('<div class="sr-panel"><div class="sr-title">SkyRoute AI · city risk monitor</div><div class="sr-body">The agent continuously combines weather, road wetness, traffic, ordinary crashes and HazMat flow to identify preventable escalation.</div></div>', unsafe_allow_html=True)
        render_prevention_factor_chart()


# =============================================================================
# PAGE 2 — INCIDENT OVERVIEW
# =============================================================================

def page_incident_overview() -> None:
    if active.id == HISTORICAL_INCIDENT_ID:
        st.markdown(
            "<div class='sr-live-case'><div class='sr-title'>Real incident live simulation · Huai'an “3·29” liquid-chlorine leak</div>"
            "<div class='sr-body'>The command center is receiving information progressively. SkyRoute ranks protection targets, assigns different agencies to different missions and continuously recalculates road-network access.</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown('<div class="sr-h2">Incident understanding and operational picture</div>', unsafe_allow_html=True)
    map_col, info_col = st.columns([1.58, 1])

    with map_col:
        layers: List[pdk.Layer] = []
        building_layer = illustrative_buildings_layer("incident")
        pop3d_layer = worldpop_3d_layer("incident")
        if building_layer:
            layers.append(building_layer)
        if pop3d_layer:
            layers.append(pop3d_layer)
        if show_environment_layer:
            layers.extend(public_environment_layers("incident"))
        if show_water_layer:
            water_data = [{**zone, "title": zone["name"], "details": "Sensitive water or ecological receptor"} for zone in WATER_ZONES]
            layers.append(polygon_layer("incident-water", water_data, [0, 168, 255, 58], [0, 168, 255, 215]))
        if show_traffic_layer:
            layers.append(path_layer("incident-traffic", traffic_path_data(), 8))

        plume_data = [{
            "polygon": incident_state["plume_polygon"],
            "title": "Downwind protective-action zone",
            "details": f"Length {incident_state['protective_distance']/1000:.1f} km<br/>Wind {wind_label(wind_direction)} {wind_speed_kmh} km/h",
        }]
        layers.append(polygon_layer("incident-plume", plume_data, [255, 89, 94, 68], [255, 89, 94, 235]))
        isolation_data = [{
            "polygon": make_circle_polygon(active.lat, active.lon, incident_state["isolation_distance"]),
            "title": "Initial isolation zone",
            "details": f"Radius {incident_state['isolation_distance']} m",
        }]
        layers.append(polygon_layer("incident-isolation", isolation_data, [255, 214, 10, 28], MAP_LINE_COLOR["isolation"] + [240]))

        if show_population_layer:
            layers += vulnerability_buffer_layers("incident")
            if show_labels_layer:
                layers += point_layers("incident-pois", pois_live, 62, 20)
        hospitals = hospital_map_data()
        if hospitals and show_population_layer and show_labels_layer:
            layers += point_layers("incident-hospitals", hospitals, 78, 22)

        resources_data = resource_map_data()
        if show_resources_layer:
            layers += resource_halo_layers("incident-resources", resources_data)
            if show_labels_layer:
                layers += point_layers("incident-resources", resources_data, 58, 20)

        layers += incident_icon_layers("incident-marker", [{
            "id": active.id,
            "lon": active.lon,
            "lat": active.lat,
            "color": THREAT_COLOR[active.threat] + [250],
            "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": f"{active.id} · {active.substance}",
            "details": f"Leak estimate: {incident_state['dynamic_leak']:.0f} kg/min<br/>{active.description}",
        }], get_size=4, size_scale=13)

        pitch = 42
        deck = make_deck(layers, active.lat, active.lon, 13.05, pitch, -12, use_basemap)
        render_map(deck, "incident-overview-map", 650)
        legend = [
            (INCIDENT_LEGEND_TOKEN, "Accident source", "#FF595E"),
            ("▰", "Toxic plume", "#FF595E"),
            ("▰", "Isolation zone", "#FFD166"),
        ]
        if show_population_layer:
            legend += [(MAP_SYMBOL_GLYPH["community"], "Community / village", "#FF9F1C")]
            present_types = {str(item.get("type", "")) for item in pois_live}
            if "school" in present_types:
                legend.append((MAP_SYMBOL_GLYPH["school"], "School", "#FFD166"))
            if "eldercare" in present_types:
                legend.append((MAP_SYMBOL_GLYPH["community"], "Elder-care facility", "#B46AFF"))
            legend.append((MAP_SYMBOL_GLYPH["hospital"], "Available hospital", "#00A8FF"))
        if show_resources_layer:
            legend += [(MAP_SYMBOL_GLYPH["fire"], "Fire base", "#FF7E22"), (MAP_SYMBOL_GLYPH["hazmat"], "HazMat base", "#FF2D95"), (MAP_SYMBOL_GLYPH["police"], "Police base", "#00C4FF"), (MAP_SYMBOL_GLYPH["ambulance"], "EMS base", "#4C6FFF")]
        if show_water_layer:
            legend.append(("▰", "Water receptor", "#00A8FF"))
        if show_environment_layer:
            legend.append(("▰", "Protected / environmental area", "#00D68F"))
        render_map_legend(legend, "Operational map legend")

    with info_col:
        st.markdown(f'<div class="sr-panel"><div class="sr-title">{active.id} · {active.substance}</div><div class="sr-body">{active.description}<br/><br/><b>Road:</b> {active.road}<br/><b>Hazard:</b> {incident_state["substance"]["hazard"]}<br/><b>Detected:</b> {active.detected_at}</div></div>', unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        r1.metric("Plume arrival", f"{incident_state['plume_arrival_min']} min")
        r2.metric("Evacuation clearance", f"{incident_state['evacuation_time_min']} min")
        r3, r4 = st.columns(2)
        r3.metric("Movement margin", f"{incident_state['movement_margin']} min")
        r4.metric("Shelter effectiveness", f"{incident_state['shelter_effectiveness']:.0%}")

        ranking = current_priority_ranking()
        top = ranking[0] if ranking else None
        st.markdown(
            f'<div class="sr-alert sr-critical"><div class="sr-title">Agent protective recommendation</div><div class="sr-body">'
            f'<b>{incident_state["recommendation"]}</b> · confidence {incident_state["confidence"]:.0%}<br/>'
            f'Immediate target: <b>{top["name"] if top else "incident assessment"}</b>. The recommendation combines plume arrival, evacuation clearance, vulnerability, population presence and traffic.</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sr-h2">Next operational decision</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Protect population", type="primary", use_container_width=True):
            st.session_state.incident_tab = "Population"
            st.rerun()
        if c2.button("Select resources", use_container_width=True):
            st.session_state.incident_tab = "Dispatch"
            st.rerun()
        c3, c4 = st.columns(2)
        if c3.button("Control traffic", use_container_width=True):
            st.session_state.incident_tab = "Traffic"
            st.rerun()
        if c4.button("Protect environment", use_container_width=True):
            st.session_state.incident_tab = "Environment"
            st.rerun()

        st.markdown('<div class="sr-h2">Receiving hospitals</div>', unsafe_allow_html=True)
        hospitals = hospital_map_data()
        if hospitals:
            for hospital in hospitals:
                status_cls = str(hospital.get("hospital_status", "Available")).lower()
                st.markdown(
                    f'<div class="sr-hospital-card {status_cls}"><div class="sr-title">🏥 {hospital["name"]}</div>'
                    f'<div class="sr-small">{hospital.get("hospital_status","Available")} · {hospital.get("available_beds",0)} beds available<br/>'
                    f'{hospital.get("specialty","Emergency care")}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No receiving hospital is mapped in the current context.")

        st.markdown('<div class="sr-h2">Priority targets</div>', unsafe_allow_html=True)
        for idx, item in enumerate(ranking[:4]):
            css = "sr-selected-row" if idx == 0 else "sr-step"
            st.markdown(
                f'<div class="{css}"><b>{idx+1}. {item["name"]}</b><br/>'
                f'Priority {item["priority_score"]:.1f} · {item["population_now"]:,} people · {item["distance_m"]} m</div>',
                unsafe_allow_html=True,
            )

def render_decision_options(options: List[DecisionOption], preview_key: str) -> None:
    current_preview = st.session_state.get(preview_key)
    for option in options:
        selected = is_decision_selected(option.id)
        previewing = current_preview == option.id
        css = " selected" if selected else ""
        selected_badge = '<span class="sr-badge badge-safe">✓ selected in shared plan</span>' if selected else ""
        preview_badge = '<span class="sr-badge badge-ai">visible on map</span>' if previewing else ""
        st.markdown(
            f'<div class="sr-panel{css}"><div class="sr-title">{option.title}</div><div class="sr-body">{option.summary}</div><span class="sr-badge badge-ai">confidence {option.confidence:.0%}</span><span class="sr-badge">implementation {option.implementation_min} min</span><span class="sr-badge badge-safe">residual {option.residual_risk}</span>{selected_badge}{preview_badge}</div>',
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("People protected", f"{option.people_protected:,}" if option.people_protected else "—")
        m2.metric("Traffic impact", option.traffic_impact)
        m3.metric("Resources", option.resource_need[:28] + ("…" if len(option.resource_need) > 28 else ""))
        with st.expander("Why, requirements and map consequence"):
            st.write(f"**Agent reason:** {option.agent_reason}")
            st.write(f"**Resources:** {option.resource_need}")
            st.write(f"**Map consequence:** {option.map_effect}")
        b1, b2 = st.columns(2)
        if b1.button("Showing on map" if previewing else "Visualise on map", key=f"preview-{option.id}", disabled=previewing, use_container_width=True):
            st.session_state[preview_key] = option.id
            log_event(f"Decision previewed: {option.title}", option.category)
            st.rerun()
        action_label = "✓ Selected · remove" if selected else "Add to operational plan"
        if b2.button(action_label, key=f"plan-{option.id}", type="secondary" if selected else "primary", use_container_width=True):
            if selected:
                remove_decision_from_plan(option)
            else:
                add_decision_to_plan(option)
            st.session_state[preview_key] = option.id
            st.rerun()


# =============================================================================
# PAGE 3 — POPULATION PROTECTION
# =============================================================================

def page_population() -> None:
    options = population_decisions(incident_state)
    preview_id = st.session_state.preview_population or choose_recommended_decision(options, incident_state["recommendation"]).id
    preview = next((option for option in options if option.id == preview_id), options[0])

    st.markdown('<div class="sr-h2">Interactive population-protection decision</div>', unsafe_allow_html=True)
    map_col, decision_col = st.columns([1.48, 1])

    with map_col:
        layers: List[pdk.Layer] = []
        building_layer = illustrative_buildings_layer("population")
        pop3d_layer = worldpop_3d_layer("population")
        if building_layer:
            layers.append(building_layer)
        if pop3d_layer:
            layers.append(pop3d_layer)
        layers.append(polygon_layer("pop-plume", [{
            "polygon": incident_state["plume_polygon"],
            "title": "Protective-action plume",
            "details": f"Arrival estimate {incident_state['plume_arrival_min']} min",
        }], [255, 89, 94, 60], [255, 89, 94, 225]))
        layers += vulnerability_buffer_layers("population")
        if show_labels_layer:
            layers += point_layers("pop-exposed-pois", incident_state["exposed_pois"], 74, 20)
            layers += point_layers("pop-shelters", [{
                **shelter, "color": [169, 191, 90, 235], "glyph": MAP_SYMBOL_GLYPH["shelter"], "title": shelter["name"],
                "details": f"Shelter capacity: {shelter['capacity']:,}",
            } for shelter in SHELTERS], 72, 21)
            layers += point_layers("pop-hospitals", hospital_map_data(), 76, 22)
        layers += decision_overlay_layers("population-map", [preview])
        layers += incident_icon_layers("population-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": active.id, "details": active.description,
        }], get_size=4, size_scale=13)
        pitch = 34
        render_map(make_deck(layers, active.lat, active.lon, 12.45, pitch, -8, use_basemap), "population-protection-map", 680)
        population_legend: List[Tuple[str, str, str]] = [
            (INCIDENT_LEGEND_TOKEN, "Accident source", "#FF595E"),
            (MAP_SYMBOL_GLYPH["community"], "Priority community / village", "#FF9F1C"),
            (MAP_SYMBOL_GLYPH["school"], "School", "#FFD166"),
            (MAP_SYMBOL_GLYPH["community"], "Elder-care facility", "#B46AFF"),
            (MAP_SYMBOL_GLYPH["hospital"], "Receiving hospital", "#00A8FF"),
            (MAP_SYMBOL_GLYPH["shelter"], "Evacuation shelter", "#00D68F"),
            ("▰", "Priority buffer: red / amber / cyan", "#FFD166"),
        ]
        render_map_legend(population_legend, "Population protection legend")
        st.info(f"Preview: **{preview.title}**. Buffer size reflects population and vulnerability; color reflects dynamic operational priority.")

    with decision_col:
        render_decision_options(options, "preview_population")


def page_dispatch() -> None:
    st.markdown('<div class="sr-h2">Select a real origin base, assign a mission destination and prepare dispatch</div>', unsafe_allow_html=True)
    render_resource_availability()
    render_dispatch_receipt()
    controls, map_col = st.columns([1, 1.55])

    with controls:
        agency = st.selectbox("Agency to configure", list(AGENCY_LABEL.keys()), format_func=lambda key: AGENCY_LABEL[key])
        targets = mission_targets_for_kind(agency)
        target_ids = [item["id"] for item in targets]
        current_target_id = st.session_state.selected_mission_target_ids.get(agency, target_ids[0] if target_ids else "TARGET-INCIDENT")
        target_index = target_ids.index(current_target_id) if current_target_id in target_ids else 0
        selected_target = st.selectbox(
            "Mission destination",
            targets,
            index=target_index,
            format_func=lambda item: f"{item.get('glyph','●')} {item['name']} · {item.get('details','')}",
        )
        st.session_state.selected_mission_target_ids[agency] = selected_target["id"]

        candidates = [resource for resource in RESOURCES if resource.kind == agency]
        available_candidates = [resource for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) != "Busy"] or candidates
        default_resource_id = st.session_state.selected_resource_ids.get(agency)
        if default_resource_id not in [item.id for item in available_candidates]:
            default_resource_id = min(
                available_candidates,
                key=lambda item: dist_m(item.lat, item.lon, selected_target["lat"], selected_target["lon"]),
            ).id
        default_index = next((index for index, resource in enumerate(available_candidates) if resource.id == default_resource_id), 0)
        selected_resource = st.selectbox(
            "Origin station / base",
            available_candidates,
            index=default_index,
            format_func=lambda resource: f"{resource.name} · {st.session_state.dispatch_status.get(resource.id, resource.status)} · {resource.capacity}",
        )
        st.session_state.selected_resource_ids[agency] = selected_resource.id

        max_units = max(1, selected_resource.units)
        quantity = st.number_input(
            "Units to include", min_value=0, max_value=max_units,
            value=min(st.session_state.resource_quantities.get(agency, 0), max_units), step=1,
            key=f"qty-{agency}-{selected_resource.id}",
        )
        st.session_state.resource_quantities[agency] = int(quantity)

        with st.spinner("Calculating mission-specific road alternatives…"):
            options = build_mission_route_options(selected_resource, selected_target, traffic_segments, routing_backend, amap_key, ors_api_key)
        route_keys = ["recommended", "fastest", "safest", "low_traffic"]
        current_route = st.session_state.selected_routes.get(agency, "recommended")
        if current_route not in route_keys:
            current_route = "recommended"
        selected_route_key = st.radio(
            "Route objective", route_keys, index=route_keys.index(current_route),
            format_func=lambda key: options[key].label,
        )
        st.session_state.selected_routes[agency] = selected_route_key
        chosen = options[selected_route_key]

        st.markdown(
            f'<div class="sr-panel selected"><div class="sr-title">{AGENCY_GLYPH[agency]} {selected_resource.name} → {selected_target["name"]}</div>'
            f'<div class="sr-body"><b>{chosen.label}</b><br/>ETA <b>{chosen.eta_min} min</b> · {chosen.distance_km} km<br/>'
            f'Exposure {chosen.exposure_score} · Environment {chosen.environment_score} · Congestion {chosen.congestion_score}<br/>'
            f'Composite score <b>{chosen.composite_score}</b><br/><br/>{chosen.explanation}</div>'
            f'<span class="sr-badge badge-ai">{chosen.backend}</span></div>',
            unsafe_allow_html=True,
        )
        if not chosen.path:
            st.error("No real-street route is available. SkyRoute did not draw an approximate line.")
        render_route_comparison(options, selected_route_key)

        if st.button("Add mission and route to plan", type="primary", use_container_width=True):
            if not chosen.path:
                st.warning("A real street route must be available before this unit can be added.")
            elif quantity <= 0:
                st.warning("Select at least one unit.")
            else:
                st.session_state.plan_confirmed = False
                st.session_state.dispatch_status[selected_resource.id] = "Requested"
                log_event(
                    f"{quantity} {AGENCY_LABEL[agency]} unit(s): {selected_resource.name} → {selected_target['name']} via {chosen.label}",
                    "dispatch",
                )
                st.toast("Mission configuration added to the plan")

    with map_col:
        all_routes = []
        if show_routes_layer:
            for key, route in options.items():
                if len(route.path) < 2:
                    continue
                selected = key == selected_route_key
                recommended = key == "recommended"
                route_rgb = ROUTE_OBJECTIVE_COLOR.get(key, AGENCY_COLOR[agency])
                opacity = 255 if recommended else 235 if selected else 105
                width = 13 if recommended else 9 if selected else 4
                all_routes.append({
                    "path": route.path,
                    "color": route_rgb + [opacity],
                    "width": width,
                    "title": f"{route.label} · {selected_resource.name} → {selected_target['name']}",
                    "details": (
                        f"Objective: {'AI recommended' if recommended else key.replace('_', ' ').title()}<br/>"
                        f"Mission: {AGENCY_LABEL[agency]} deployment<br/>"
                        f"Status: {st.session_state.dispatch_status.get(selected_resource.id, selected_resource.status)}<br/>"
                        f"ETA {route.eta_min} min · {route.distance_km} km<br/>"
                        f"Exposure {route.exposure_score} · Environment {route.environment_score} · Congestion {route.congestion_score}<br/>"
                        f"Backend: {route.backend}"
                    ),
                })

        layers: List[pdk.Layer] = []
        building_layer = illustrative_buildings_layer("dispatch")
        if building_layer:
            layers.append(building_layer)
        if show_environment_layer:
            layers.extend(public_environment_layers("dispatch"))
        if show_traffic_layer:
            layers.append(path_layer("dispatch-traffic", traffic_path_data(), 7))
        if all_routes:
            layers += path_layers_with_halo("dispatch-route-options", all_routes, 6, halo_extra=5)

        resources_data = resource_map_data()
        if show_resources_layer:
            layers += resource_halo_layers("dispatch-resources", resources_data)
            if show_labels_layer:
                layers += point_layers("dispatch-resources", resources_data, 60, 20)

        target_marker = [{
            **selected_target,
            "color": AGENCY_COLOR[agency] + [245],
            "glyph": selected_target.get("glyph", "◎"),
            "title": f"Mission destination · {selected_target['name']}",
            "details": selected_target.get("details", "Assigned destination"),
        }]
        if show_labels_layer:
            layers += point_layers("dispatch-target", target_marker, 92, 23)
            layers += point_layers("dispatch-hospitals", hospital_map_data(), 76, 22)

        layers += incident_icon_layers("dispatch-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": active.id, "details": active.description,
        }], get_size=4, size_scale=13)

        deployed = deployed_vehicle_data()
        if deployed:
            layers += resource_halo_layers("dispatch-moving-units", deployed)
            if show_labels_layer:
                layers += point_layers("dispatch-moving-units", deployed, 78, 22)

        center_lat = (selected_resource.lat + selected_target["lat"]) / 2
        center_lon = (selected_resource.lon + selected_target["lon"]) / 2
        dispatch_pitch = 38
        render_map(make_deck(layers, center_lat, center_lon, 12.35, dispatch_pitch, -8, use_basemap), "dispatch-resources-map", 690)
        render_map_legend([
            (INCIDENT_LEGEND_TOKEN, "Incident / leak source", "#E2543D"),
            (AGENCY_GLYPH[agency], f"{AGENCY_LABEL[agency]} origin / active unit", "#%02X%02X%02X" % tuple(AGENCY_COLOR[agency])),
            (MAP_SYMBOL_GLYPH.get(_symbol_key_for_item(selected_target), "◎"), "Assigned mission destination", "#FFFFFF"),
            ("━", "AI recommended route", "#FFFFFF"),
            ("━", "Fastest route", "#00D9FF"),
            ("━", "Lowest-exposure route", "#00E6A0"),
            ("━", "Lowest-congestion route", "#FFD166"),
            (MAP_SYMBOL_GLYPH["hospital"], "Available receiving hospital", "#00A8FF"),
            ("◉", "Requested halo", "#FFD166"),
            ("◉", "En-route halo", "#00C4FF"),
            ("◉", "On-scene halo", "#FFFFFF"),
        ], "Dispatch legend")

    st.markdown('<div class="sr-h2">Receiving hospital availability</div>', unsafe_allow_html=True)
    hospitals = hospital_map_data()
    if hospitals:
        hospital_cols = st.columns(max(1, min(3, len(hospitals))))
        for idx, hospital in enumerate(hospitals):
            with hospital_cols[idx % len(hospital_cols)]:
                status_cls = str(hospital.get("hospital_status", "Available")).lower()
                st.markdown(
                    f'<div class="sr-hospital-card {status_cls}"><div class="sr-title">🏥 {hospital["name"]}</div>'
                    f'<div class="sr-small">{hospital.get("hospital_status","Available")} · {hospital.get("available_beds",0)} beds available<br/>'
                    f'{hospital.get("specialty","Emergency care")}</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No receiving hospitals are mapped in this scenario.")

    st.markdown('<div class="sr-h2">Current resource plan</div>', unsafe_allow_html=True)
    render_resource_plan_cards()
    if any(quantity > 0 for quantity in st.session_state.resource_quantities.values()):
        c1, c2 = st.columns(2)
        if c1.button("Review consolidated plan", use_container_width=True):
            st.session_state.incident_tab = "Plan"
            st.rerun()
        if c2.button("Confirm and dispatch selected units", type="primary", use_container_width=True):
            confirm_dispatch()
            st.rerun()

def page_traffic() -> None:
    options = traffic_control_options()
    preview_id = st.session_state.preview_traffic or "TR-CLOSE"
    preview = next((option for option in options if option.id == preview_id), options[0])

    st.markdown('<div class="sr-h2">Traffic, closures, dangerous-goods diversion and emergency priority</div>', unsafe_allow_html=True)
    map_col, control_col = st.columns([1.52, 1])

    with map_col:
        layers: List[pdk.Layer] = [path_layer("traffic-live-segments", traffic_path_data(), 10)]
        layers += decision_overlay_layers("traffic-map", [preview])
        layers += point_layers("traffic-hazmat-trucks", [{
            **truck, "type": "truck", "color": [255, 45, 149, 235], "glyph": MAP_SYMBOL_GLYPH["truck"], "title": f"HazMat truck {truck['id']}",
            "details": f"{truck['substance']} · {truck['speed']} km/h · route {truck['route']}",
        } for truck in HAZMAT_TRUCKS], 72, 12)
        layers += point_layers("traffic-normal-incidents", [{
            **acc, "type": "traffic_incident", "color": [255, 89, 94, 235], "glyph": MAP_SYMBOL_GLYPH["traffic_incident"], "title": acc["title"],
            "details": f"{acc['road']} · {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 58, 11)
        layers += incident_icon_layers("traffic-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": active.id, "details": active.description,
        }], get_size=4, size_scale=13)
        render_map(make_deck(layers, active.lat, active.lon, 12.25, 35, -8, use_basemap), "traffic-control-map", 675)
        render_map_legend([
            (INCIDENT_LEGEND_TOKEN, "Active incident", "#FF595E"),
            (MAP_SYMBOL_GLYPH["truck"], "HazMat vehicle", "#FF2D95"),
            (MAP_SYMBOL_GLYPH["traffic_incident"], "Ordinary traffic incident", "#FF595E"),
            ("━", "Traffic: free / slow / congested", "#FFD166"),
            ("━", "Road closure", "#FFFFFF"),
            ("━", "Emergency corridor", "#FFD166"),
            ("━", "Evacuation route", "#B46AFF"),
            ("━", "HazMat bypass", "#FF2D95"),
        ], "Traffic-control map legend")
        st.info(f"Preview: **{preview.title}**. All previously selected population and environmental measures remain overlaid for conflict checking.")

    with control_col:
        render_decision_options(options, "preview_traffic")

    st.markdown('<div class="sr-h2">Live traffic performance</div>', unsafe_allow_html=True)
    road_names = [segment.get("name", "Road") for segment in traffic_segments]
    speeds = [segment.get("speed", 0) for segment in traffic_segments]
    congestion_values = [round(segment.get("congestion", 0) * 100) for segment in traffic_segments]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=road_names, y=speeds, name="Average speed km/h"))
    fig.add_trace(go.Scatter(x=road_names, y=congestion_values, mode="lines+markers", name="Congestion %", yaxis="y2"))
    fig.update_layout(yaxis=dict(title="km/h", showgrid=False), yaxis2=dict(title="%", overlaying="y", side="right", range=[0,100], showgrid=False), title=f"Traffic state · {traffic_source_label}")
    st.plotly_chart(transparent_plot_layout(fig, 320), use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# PAGE 6 — ENVIRONMENTAL PROTECTION
# =============================================================================
def page_environment() -> None:
    options = environmental_decisions(active)
    preview_id = st.session_state.preview_environment or "ENV-DRAIN"
    preview = next((option for option in options if option.id == preview_id), options[0])

    st.markdown('<div class="sr-h2">Environmental receptors, drains, sensors and containment actions</div>', unsafe_allow_html=True)
    map_col, decision_col = st.columns([1.5, 1])

    with map_col:
        layers: List[pdk.Layer] = public_environment_layers("environment")
        layers.append(polygon_layer("environment-water-zones", [{
            **zone, "title": zone["name"], "details": "Sensitive water and ecological receptor",
        } for zone in WATER_ZONES], [0, 168, 255, 70], [0, 168, 255, 225]))
        layers.append(polygon_layer("environment-plume", [{
            "polygon": incident_state["plume_polygon"], "title": "Air-impact zone",
            "details": f"Wind {wind_label(wind_direction)} · {wind_speed_kmh} km/h",
        }], [255, 89, 94, 45], [255, 89, 94, 190]))
        layers += point_layers("environment-drains", [{
            **drain, "type": "drain", "color": [0, 217, 255, 240], "glyph": MAP_SYMBOL_GLYPH["drain"], "title": drain["name"],
            "details": "Stormwater pathway requiring protection",
        } for drain in DRAINS], 56, 11)
        layers += point_layers("environment-fixed-sensors", [{
            **sensor, "type": "sensor", "color": [255, 209, 102, 240], "glyph": MAP_SYMBOL_GLYPH["sensor"], "title": sensor["name"],
            "details": f"Status: {sensor['status']}",
        } for sensor in SENSORS], 58, 11)
        layers += decision_overlay_layers("environment-map", [preview])
        layers += incident_icon_layers("environment-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": active.id, "details": incident_state["substance"]["environment"],
        }], get_size=4, size_scale=13)
        render_map(make_deck(layers, active.lat, active.lon, 12.65, 38, -8, use_basemap), "environment-protection-map", 675)
        render_map_legend([
            (INCIDENT_LEGEND_TOKEN, "Active incident", "#FF595E"),
            ("▰", "Air-impact / toxic-plume zone", "#FF595E"),
            ("▰", "Water or ecological receptor", "#00A8FF"),
            (MAP_SYMBOL_GLYPH["drain"], "Drain / stormwater pathway", "#00D9FF"),
            (MAP_SYMBOL_GLYPH["sensor"], "Environmental sensor", "#FFD166"),
            ("▰", "Protected / environmental area", "#00D68F"),
            ("━", "Environmental containment / monitoring action", "#00D68F"),
        ], "Environmental-protection map legend")
        st.info(f"Preview: **{preview.title}**. Selected population and traffic actions stay visible to reveal overlaps with drains, sensors and containment areas.")
        st.caption(f"Public environmental polygons: {PROTECTED_AREA_SOURCE}. These complement the statutory planning references but are not represented as official ecological-redline boundaries.")

    with decision_col:
        render_decision_options(options, "preview_environment")


# =============================================================================
# PLAN ENGINE AND DEMONSTRATION SEQUENCE
# =============================================================================
DEMO_STAGES = [
    "Incident detected",
    "Impact zone calculated",
    "Protective action recommended",
    "Traffic controls proposed",
    "Resources selected",
    "Plan confirmed",
    "Units moving",
    "Sensors updating",
    "Source controlled",
    "Incident stabilised",
]


def minimum_plan_ready() -> Tuple[bool, List[str]]:
    missing = []
    for category, label in [("population", "population protection"), ("traffic", "traffic control"), ("environment", "environmental protection")]:
        if not selected_decisions(category):
            missing.append(label)
    if not any(qty > 0 for qty in st.session_state.resource_quantities.values()):
        missing.append("at least one response resource")
    return len(missing) == 0, missing


def confirm_dispatch() -> None:
    ready, missing = minimum_plan_ready()
    if not ready:
        st.error("The plan is incomplete: " + ", ".join(missing))
        return
    units: List[str] = []
    etas: List[float] = []
    requested_at = datetime.now()
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        resource_id = st.session_state.selected_resource_ids.get(kind)
        resource = next((item for item in RESOURCES if item.id == resource_id), None)
        route = selected_route_for_kind(kind)
        if resource_id and resource and route:
            st.session_state.dispatch_status[resource_id] = "En route"
            st.session_state.dispatch_start_tick[resource_id] = st.session_state.demo_tick
            units.append(f"{quantity} {AGENCY_LABEL[kind]} from {resource.name}")
            etas.append(float(route.eta_min))
    first_arrival = round(min(etas), 1) if etas else 0.0
    execution = round(max(etas) + setup_delay_min, 1) if etas else float(setup_delay_min)
    receipt = {
        "request_id": f"SR-{active.id}-{requested_at.strftime('%H%M%S')}",
        "requested_at": requested_at.strftime("%H:%M:%S"),
        "requested_iso": requested_at.isoformat(timespec="seconds"),
        "mobilisation_min": setup_delay_min,
        "first_arrival_min": first_arrival,
        "execution_min": execution,
        "estimated_complete": (requested_at + timedelta(minutes=execution)).strftime("%H:%M:%S"),
        "units": units,
    }
    st.session_state.last_dispatch_receipt = receipt
    st.session_state.dispatch_receipts.insert(0, receipt)
    st.session_state.dispatch_receipts = st.session_state.dispatch_receipts[:20]
    st.session_state.plan_confirmed = True
    st.session_state.demo_stage = max(st.session_state.demo_stage, 5)
    log_event(f"Dispatch {receipt['request_id']} requested at {receipt['requested_at']}; execution estimate {execution} min", "command")
    st.toast(f"Dispatch requested at {receipt['requested_at']} · estimated execution {execution} min")


def advance_demo(minutes: int = 1) -> None:
    st.session_state.demo_tick += minutes
    if st.session_state.plan_confirmed:
        st.session_state.demo_stage = min(len(DEMO_STAGES) - 1, max(6, st.session_state.demo_stage + 1))
    else:
        st.session_state.demo_stage = min(4, st.session_state.demo_stage + 1)
    log_event(f"Simulation advanced by {minutes} minute(s)", "simulation")


def reset_demo() -> None:
    st.session_state.demo_tick = 0
    st.session_state.demo_stage = 0
    st.session_state.plan_confirmed = False
    st.session_state.dispatch_status = {r.id: r.status for r in RESOURCES}
    st.session_state.dispatch_start_tick = {}
    st.session_state.last_dispatch_receipt = None
    log_event("Demonstration reset", "simulation")



def consolidated_map_layers() -> List[pdk.Layer]:
    """Build the complete operational map without hiding existing decision layers."""
    layers: List[pdk.Layer] = []

    if show_environment_layer:
        layers.extend(public_environment_layers("plan"))
    if show_water_layer:
        layers.append(
            polygon_layer(
                "plan-water",
                [{**zone, "title": zone["name"], "details": "Water or wetland receptor"} for zone in WATER_ZONES],
                [0, 168, 255, 48],
                [0, 168, 255, 215],
            )
        )
    if show_traffic_layer:
        layers.append(path_layer("plan-traffic", traffic_path_data(), 7))

    layers.append(
        polygon_layer(
            "plan-plume",
            [{
                "polygon": incident_state["plume_polygon"],
                "title": "Current chlorine protective-action zone",
                "details": (
                    f"Simulation minute {st.session_state.demo_tick}<br/>"
                    f"Wind {wind_label(wind_direction)} {wind_speed_kmh} km/h"
                ),
            }],
            [255, 89, 94, 58],
            [255, 89, 94, 230],
        )
    )

    layers += vulnerability_buffer_layers("plan")
    layers += decision_overlay_layers("consolidated-plan")
    layers += route_layers_for_plan()

    mission_targets: List[Dict[str, Any]] = []
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        target = selected_mission_target(kind)
        mission_targets.append({
            **target,
            "color": AGENCY_COLOR.get(kind, [213, 242, 109]) + [245],
            "glyph": target.get("glyph", "◎"),
            "title": f"{AGENCY_LABEL.get(kind, kind)} mission · {target['name']}",
            "details": target.get("details", "Assigned mission destination"),
        })

    deployed = deployed_vehicle_data()
    bases = resource_map_data()
    if show_resources_layer:
        layers += resource_halo_layers("plan-active", deployed + bases)
        if show_labels_layer:
            layers += point_layers("plan-bases", bases, 54, 19)
            if deployed:
                layers += point_layers("plan-moving-resources", deployed, 76, 21)

    if show_labels_layer:
        if mission_targets:
            layers += point_layers("plan-mission-targets", mission_targets, 72, 21)
        layers += point_layers("plan-hospitals", hospital_map_data(), 78, 22)
        layers += point_layers(
            "plan-shelters",
            [{
                **shelter,
                "color": [169, 191, 90, 235],
                "glyph": MAP_SYMBOL_GLYPH["shelter"],
                "title": shelter["name"],
                "details": f"Evacuation shelter · capacity {shelter['capacity']:,}",
            } for shelter in SHELTERS],
            58,
            19,
        )

    layers += incident_icon_layers(
        "plan-incident",
        [{
            "lon": active.lon,
            "lat": active.lat,
            "color": THREAT_COLOR[active.threat] + [250],
            "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": active.id,
            "details": active.description,
        }],
        get_size=4,
        size_scale=13,
    )
    return layers


def page_plan() -> None:
    render_dispatch_receipt()
    st.markdown('<div class="sr-h2">Consolidated operational plan and presentation mode</div>', unsafe_allow_html=True)
    map_col, plan_col = st.columns([1.62, 1])

    with map_col:
        pitch = 40
        deck = make_deck(consolidated_map_layers(), active.lat, active.lon, 12.3, pitch, -10, use_basemap)
        render_map(deck, "consolidated-plan-map", 690)
        legend_items: List[Tuple[str, str, str]] = [
            (INCIDENT_LEGEND_TOKEN, "Incident / leak source", "#FF595E"),
            ("▰", "Toxic plume and protective-action zone", "#FF595E"),
        ]
        if show_population_layer:
            legend_items += [
                (MAP_SYMBOL_GLYPH["community"], "Vulnerable destination and dynamic buffer", "#FFD166"),
                (MAP_SYMBOL_GLYPH["hospital"], "Hospital badge (+) · receiving capacity", "#00A8FF"),
            ]
        if show_resources_layer:
            legend_items += [
                (MAP_SYMBOL_GLYPH["fire"], "Fire badge (F) · base or active unit", "#FF7E22"),
                (MAP_SYMBOL_GLYPH["hazmat"], "HazMat badge (H) · base or active unit", "#FF2D95"),
                (MAP_SYMBOL_GLYPH["police"], "Police badge (P) · base or active unit", "#00C4FF"),
                (MAP_SYMBOL_GLYPH["ambulance"], "EMS badge (A) · base or active unit", "#4C6FFF"),
                ("◉", "Requested / en route / on scene halo", "#FFD166"),
            ]
        if show_routes_layer:
            legend_items += [("━", "Police route", "#00C4FF"), ("━", "Fire route", "#FF7E22"), ("━", "HazMat route", "#FF2D95"), ("━", "EMS route", "#4C6FFF"), ("━", "Evacuation route", "#B46AFF"), ("━", "Environmental route", "#00D68F")]
        if show_environment_layer or show_water_layer:
            legend_items += [
                ("▰", "Environmental protection receptor", "#00D68F"),
                ("▰", "Water / wetland receptor", "#00A8FF"),
            ]
        render_map_legend(legend_items, "Consolidated plan legend")

        timeline = go.Figure()
        minutes = list(range(0, 31))
        exposure = [
            max(
                0,
                incident_state["exposed_population"]
                * (1 - (0.018 * minute if st.session_state.plan_confirmed else 0.004 * minute)),
            )
            for minute in minutes
        ]
        response = [
            min(100, max(0, (minute - 4) * 5.5))
            if st.session_state.plan_confirmed
            else min(45, minute * 1.2)
            for minute in minutes
        ]
        timeline.add_trace(go.Scatter(x=minutes, y=exposure, name="People remaining exposed", mode="lines", yaxis="y"))
        timeline.add_trace(go.Scatter(x=minutes, y=response, name="Response completion %", mode="lines", yaxis="y2"))
        timeline.add_vline(x=st.session_state.demo_tick, line_dash="dash", annotation_text="Current simulation")
        timeline.update_layout(
            template="plotly_dark",
            paper_bgcolor=PANEL,
            plot_bgcolor=PANEL,
            height=300,
            margin=dict(t=35, b=25, l=45, r=45),
            xaxis_title="Minutes after command",
            yaxis=dict(title="People"),
            yaxis2=dict(title="Completion %", overlaying="y", side="right", range=[0, 100]),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(timeline, use_container_width=True)

    with plan_col:
        ready, missing = minimum_plan_ready()
        status_color = TEAL if ready else AMBER
        st.markdown(
            f'<div class="sr-panel" style="border-top:2px solid {status_color}">'
            f'<div class="sr-title">Plan readiness</div>'
            f'<div class="sr-body">{"Minimum plan complete" if ready else "Missing: " + ", ".join(missing)}</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sr-h2">Selected decisions</div>', unsafe_allow_html=True)
        for category, label in [("population", "Population"), ("traffic", "Traffic"), ("environment", "Environment")]:
            category_decisions = selected_decisions(category)
            if category_decisions:
                for decision in category_decisions:
                    st.markdown(
                        f'<div class="sr-step"><b>{label}:</b> ✓ {decision["title"]}<br/>{decision["summary"]}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(f'<div class="sr-step"><b>{label}:</b> not selected</div>', unsafe_allow_html=True)

        st.markdown('<div class="sr-h2">Assigned missions</div>', unsafe_allow_html=True)
        any_resource = False
        mission_payload: Dict[str, Any] = {}
        for kind, quantity in st.session_state.resource_quantities.items():
            if quantity <= 0:
                continue
            any_resource = True
            route = selected_route_for_kind(kind)
            target = selected_mission_target(kind)
            resource_id = st.session_state.selected_resource_ids.get(kind)
            resource = next((item for item in RESOURCES if item.id == resource_id), None)
            if route and resource:
                status = st.session_state.dispatch_status.get(resource.id, resource.status)
                mission_payload[kind] = {
                    "agency": AGENCY_LABEL[kind],
                    "origin": resource.name,
                    "destination": target["name"],
                    "quantity": quantity,
                    "status": status,
                    "eta_min": route.eta_min,
                    "distance_km": route.distance_km,
                    "backend": route.backend,
                }
                st.markdown(
                    f'<div class="sr-panel"><div class="sr-title">{AGENCY_GLYPH[kind]} {AGENCY_LABEL[kind]} · {status}</div>'
                    f'<div class="sr-body"><b>Origin:</b> {resource.name}<br/>'
                    f'<b>Mission:</b> {target["name"]}<br/>'
                    f'<b>Units:</b> {quantity} · <b>ETA:</b> {route.eta_min} min · {route.distance_km} km<br/>'
                    f'<b>Route:</b> {route.label}</div></div>',
                    unsafe_allow_html=True,
                )
        if not any_resource:
            st.caption("No resources selected. Configure missions in Dispatch.")

        b1, b2 = st.columns(2)
        if b1.button("Confirm and dispatch", type="primary", use_container_width=True):
            confirm_dispatch()
            st.rerun()
        if b2.button("Edit missions", use_container_width=True):
            st.session_state.incident_tab = "Dispatch"
            st.rerun()

        st.markdown('<div class="sr-h2">Presentation sequence</div>', unsafe_allow_html=True)
        stage = DEMO_STAGES[st.session_state.demo_stage]
        st.progress(
            st.session_state.demo_stage / (len(DEMO_STAGES) - 1),
            text=f"Stage {st.session_state.demo_stage + 1}/{len(DEMO_STAGES)} · {stage}",
        )
        s1, s2, s3 = st.columns(3)
        if s1.button("Next stage", use_container_width=True):
            advance_demo(1)
            st.rerun()
        if s2.button("+ 3 minutes", use_container_width=True):
            advance_demo(3)
            st.rerun()
        if s3.button("Reset demo", use_container_width=True):
            reset_demo()
            st.rerun()

        if st.button("Auto-play executive sequence", use_container_width=True):
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            for _ in range(8):
                advance_demo(1)
                stage_now = DEMO_STAGES[st.session_state.demo_stage]
                status_placeholder.info(f"Running presentation: {stage_now}")
                progress_placeholder.progress(st.session_state.demo_stage / (len(DEMO_STAGES) - 1))
                time.sleep(0.45)
            st.rerun()

        st.markdown('<div class="sr-h2">Recent command log</div>', unsafe_allow_html=True)
        for event in st.session_state.event_log[:8]:
            st.markdown(
                f'<div class="sr-step"><b>{event["time"]} · {event["category"]}</b><br/>{event["message"]}</div>',
                unsafe_allow_html=True,
            )

        payload = {
            "incident": asdict(active),
            "state": incident_state,
            "decisions": st.session_state.plan_decisions,
            "resources": st.session_state.resource_quantities,
            "selected_resource_ids": st.session_state.selected_resource_ids,
            "selected_mission_target_ids": st.session_state.selected_mission_target_ids,
            "missions": mission_payload,
            "routes": st.session_state.selected_routes,
            "confirmed": st.session_state.plan_confirmed,
            "simulation_tick": st.session_state.demo_tick,
        }
        st.download_button(
            "Download command payload JSON",
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            file_name=f"{active.id}_skyroute_plan.json",
            mime="application/json",
            use_container_width=True,
        )

def agent_context_summary() -> str:
    selected_decisions = ", ".join(v["title"] for v in st.session_state.plan_decisions.values()) or "none"
    selected_resources = ", ".join(f"{qty} {AGENCY_LABEL[kind]}" for kind, qty in st.session_state.resource_quantities.items() if qty > 0) or "none"
    return (
        f"Incident {active.id}, {active.substance}, threat {active.threat}. "
        f"Protective zone {incident_state['protective_distance']/1000:.1f} km, exposed population {incident_state['exposed_population']}. "
        f"Plume arrival {incident_state['plume_arrival_min']} min, evacuation clearance {incident_state['evacuation_time_min']} min. "
        f"Agent recommends {incident_state['recommendation']}. Traffic {traffic_index}/10. "
        f"Selected decisions: {selected_decisions}. Selected resources: {selected_resources}."
    )



def apply_agent_command(question: str) -> Optional[str]:
    q = question.lower()
    number_match = re.search(r"\b(\d+)\b", q)
    number = int(number_match.group(1)) if number_match else 1
    mappings = {
        "ambul": "ambulance",
        "polic": "police",
        "bombe": "fire",
        "fire": "fire",
        "hazmat": "hazmat",
        "ambient": "environment",
        "sensor": "sensor",
        "ônibus": "bus",
        "onibus": "bus",
        "bus": "bus",
    }
    if any(word in q for word in ["adicione", "adicionar", "inclua", "coloque", "add", "dispatch", "envie"]):
        for token, kind in mappings.items():
            if token not in q:
                continue
            target = selected_mission_target(kind)
            candidates = [
                resource for resource in RESOURCES
                if resource.kind == kind
                and st.session_state.dispatch_status.get(resource.id, resource.status) != "Busy"
            ]
            if not candidates:
                return f"No available {AGENCY_LABEL[kind]} unit was found."
            resource = min(
                candidates,
                key=lambda item: dist_m(item.lat, item.lon, target["lat"], target["lon"]),
            )
            quantity = min(resource.units, max(1, number))
            st.session_state.resource_quantities[kind] = quantity
            st.session_state.selected_resource_ids[kind] = resource.id
            st.session_state.selected_routes.setdefault(kind, "recommended")
            st.session_state.dispatch_status[resource.id] = "Requested"
            log_event(
                f"Agent assigned {quantity} {AGENCY_LABEL[kind]} unit(s): {resource.name} → {target['name']}",
                "agent",
            )
            return (
                f"Assigned {quantity} {AGENCY_LABEL[kind]} unit(s) from {resource.name} "
                f"to {target['name']}. The route is generated from the real origin base and remains "
                f"pending human confirmation in Dispatch."
            )
    return None

def agent_answer(question: str) -> str:
    command_result = apply_agent_command(question)
    if command_result:
        return command_result

    q = question.lower()
    if "por que" in q or "porque" in q or "why" in q:
        if "shelter" in q or "evac" in q or "prote" in q:
            return (
                f"The protective recommendation is **{incident_state['recommendation']}** because the plume-arrival estimate is "
                f"{incident_state['plume_arrival_min']} min while evacuation clearance is {incident_state['evacuation_time_min']} min. "
                f"Shelter effectiveness is estimated at {incident_state['shelter_effectiveness']:.0%}, traffic is {traffic_index}/10, "
                f"and {incident_state['exposed_population']:,} people are mapped inside the demonstration influence zone."
            )
    if "escola" in q or "school" in q:
        schools = [p for p in incident_state["exposed_pois"] if p["type"] == "school"]
        if schools:
            first = min(schools, key=lambda p: p["distance_m"])
            return f"The first mapped school priority is **{first['name']}**, approximately {first['distance_m']} m from the incident, with about {first['population_now']:,} people currently estimated."
        return "No mapped school currently intersects the demonstration protective zone."
    if "rota" in q or "route" in q:
        configured = []
        for kind, qty in st.session_state.resource_quantities.items():
            if qty > 0:
                route = selected_route_for_kind(kind)
                if route:
                    configured.append(f"{AGENCY_LABEL[kind]}: {route.label}, ETA {route.eta_min} min, composite {route.composite_score}")
        if configured:
            return "Current selected routes:\n\n" + "\n\n".join(configured)
        nearest = next(r for r in RESOURCES if r.kind == "fire" and r.status != "Busy")
        options = build_route_options(nearest, active, traffic_segments, routing_backend, amap_key, ors_api_key)
        best = options["recommended"]
        return f"No resource route has been confirmed. For the nearest fire unit, the agent currently recommends **{best.label}**, ETA {best.eta_min} min and composite score {best.composite_score}."
    if "trânsito" in q or "transito" in q or "traffic" in q:
        worst = max(traffic_segments, key=lambda t: t.get("congestion", 0))
        return f"The most constrained segment is **{worst.get('name', 'road segment')}**, at approximately {worst.get('speed', 0):.0f} km/h and {worst.get('congestion', 0):.0%} congestion. Data source: {traffic_source_label}."
    if "preven" in q or "chuva" in q or "temperatura" in q or "pista" in q:
        top = preventive_alerts[0]
        return f"Preventive risk is **{prevention_value}/100 ({prevention_level})**. The leading alert is **{top.title}** because {top.reason.lower()} Recommended action: {top.recommended_action}"
    if "ambient" in q or "água" in q or "agua" in q or "drain" in q:
        return f"Environmental priority: {incident_state['substance']['environment']} The nearest stormwater inlets are mapped in the Environment tab, where drain barriers, sensors or containment can be added to the plan."
    if "plano" in q or "plan" in q:
        ready, missing = minimum_plan_ready()
        if ready:
            return "The minimum operational plan is complete. Review the consolidated map and press **Confirm and dispatch** when the commander accepts the decisions and resources."
        return "The plan is not complete. Missing: " + ", ".join(missing) + "."
    if "status" in q or "resumo" in q or "summary" in q:
        return agent_context_summary()
    return (
        "I can explain the protective recommendation, identify exposed schools, compare routes, describe traffic and prevention alerts, "
        "add resources to the draft plan, review environmental priorities and check whether the plan is ready."
    )


# =============================================================================
# LIVE CASE SIMULATION — HUAI'AN 3·29 EVENT
# =============================================================================
def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _angle_difference(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def historical_priority_ranking(stage_index: int) -> List[Dict[str, Any]]:
    stage = HISTORICAL_RECONSTRUCTION_STAGES[stage_index]
    candidates: List[Dict[str, Any]] = []
    for poi in pois_live:
        if poi.get("type") == "hospital":
            continue
        distance = max(60.0, dist_m(active.lat, active.lon, poi["lat"], poi["lon"]))
        bearing = _bearing_deg(active.lat, active.lon, poi["lat"], poi["lon"])
        alignment = max(0.0, 1 - _angle_difference(bearing, wind_direction) / 105.0)
        proximity = max(0.0, 1 - distance / max(900.0, stage["plume_length_m"] * 1.35))
        population_factor = math.log1p(max(1, poi["population_now"])) / math.log(1001)
        score = (
            population_factor * 27
            + float(poi["vulnerability"]) * 10
            + proximity * 36
            + alignment * 42 * stage["knowledge_factor"]
        )
        if poi["id"] == "H-POI-GAODANG":
            score += 30 + stage_index * 7
        candidates.append({
            **poi,
            "distance_m": int(distance),
            "bearing": bearing,
            "downwind_alignment": alignment,
            "priority_score": round(score, 1),
        })
    return sorted(candidates, key=lambda item: item["priority_score"], reverse=True)


def historical_ors_route(origin: Tuple[float, float], destination: Tuple[float, float], profile: str = "driving-car") -> Optional[Dict[str, Any]]:
    result = fetch_ors_directions(
        ors_api_key,
        ((origin[1], origin[0]), (destination[1], destination[0])),
        profile=profile,
        alternatives=1,
        preference="fastest",
        hazmat=False,
    )
    routes = result.get("routes", []) if result.get("ok") else []
    return routes[0] if routes else None


def historical_route_map_data(ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not ranking:
        return []
    top = ranking[0]
    route_data: List[Dict[str, Any]] = []
    assignments = [
        (next((r for r in RESOURCES if r.kind == "hazmat"), None), (active.lat, active.lon), "HazMat to leak source", AGENCY_COLOR["hazmat"] + [245], "driving-car"),
        (next((r for r in RESOURCES if r.kind == "police"), None), (top["lat"], top["lon"]), f"Warning team to {top['name']}", AGENCY_COLOR["police"] + [245], "driving-car"),
        (next((r for r in RESOURCES if r.kind == "bus"), None), (top["lat"], top["lon"]), f"Evacuation buses to {top['name']}", AGENCY_COLOR["bus"] + [245], "driving-car"),
    ]
    for resource, destination, title, color, profile in assignments:
        if resource is None:
            continue
        raw = historical_ors_route((resource.lat, resource.lon), destination, profile)
        if not raw:
            continue
        route_data.append({
            "path": raw["path"],
            "color": color,
            "width": 8,
            "title": title,
            "details": f"{resource.name}<br/>Distance {raw.get('distance_km', 0):.1f} km · ETA {raw.get('eta_min', 0):.1f} min<br/>Local OpenRouteService / Jiangsu road graph",
        })
    return route_data



def page_historical_study() -> None:
    if active.id != HISTORICAL_INCIDENT_ID:
        st.info("Select HIST-2005-0329 to open the real-case live simulation.")
        return

    stage_index = int(st.session_state.get("historical_stage", 0))
    stage = HISTORICAL_RECONSTRUCTION_STAGES[stage_index]
    ranking = current_priority_ranking()
    top = ranking[0] if ranking else None

    st.markdown(
        '<div class="sr-ai-strip"><div class="sr-ai-grid"><div><div class="sr-ai-label">Live incident simulation · real 2005 event</div>'
        '<div class="sr-ai-value">Jinghu Expressway Huai\'an “3·29” liquid-chlorine leak</div></div>'
        '<div><div class="sr-ai-label">Agent question</div><div class="sr-ai-value">Who needs protection first?</div></div>'
        '<div><div class="sr-ai-label">Authority</div><div class="sr-ai-value">Human commander retains final decision</div></div></div></div>',
        unsafe_allow_html=True,
    )

    controls = st.columns([1, 1, 1.4])
    if controls[0].button("← Previous update", disabled=stage_index == 0, use_container_width=True):
        st.session_state.historical_stage = max(0, stage_index - 1)
        log_event("Live case returned to the previous information update", "case")
        st.rerun()
    if controls[1].button("Receive next update →", type="primary", disabled=stage_index == len(HISTORICAL_RECONSTRUCTION_STAGES) - 1, use_container_width=True):
        next_index = min(len(HISTORICAL_RECONSTRUCTION_STAGES) - 1, stage_index + 1)
        st.session_state.historical_stage = next_index
        log_event(f"New live incident update: {HISTORICAL_RECONSTRUCTION_STAGES[next_index]['title']}", "case")
        st.rerun()
    controls[2].progress(stage_index / (len(HISTORICAL_RECONSTRUCTION_STAGES) - 1), text=f"{stage['time']} · {stage['title']}")

    map_col, insight_col = st.columns([1.55, 1])
    with map_col:
        live_plume = make_plume_polygon(
            active.lat,
            active.lon,
            wind_direction,
            stage["plume_length_m"],
            stage["plume_width_m"],
        )
        layers: List[pdk.Layer] = []
        building_layer = illustrative_buildings_layer("live-case")
        pop3d_layer = worldpop_3d_layer("live-case")
        if building_layer:
            layers.append(building_layer)
        if pop3d_layer:
            layers.append(pop3d_layer)
        if show_environment_layer:
            layers.extend(public_environment_layers("live-case"))
        if show_water_layer:
            layers.append(polygon_layer("live-case-water", [{**zone, "title": zone["name"], "details": "Environmental receptor"} for zone in WATER_ZONES], [0, 168, 255, 50], [0, 168, 255, 210]))
        if show_traffic_layer:
            layers.append(path_layer("live-case-traffic", traffic_path_data(), 7))
        layers.append(polygon_layer("live-case-plume", [{
            "polygon": live_plume,
            "title": f"{stage['title']} chlorine impact zone",
            "details": f"Live input · wind {wind_label(wind_direction)} {wind_speed_kmh} km/h",
        }], [255, 89, 94, 64], [255, 89, 94, 235]))

        layers += vulnerability_buffer_layers("live-case")
        if show_labels_layer:
            priority_points = [{
                **item,
                "color": [255, 89, 94, 245] if idx == 0 else [213, 242, 109, 230],
                "glyph": item.get("glyph", "🏘"),
                "title": f"Priority {idx + 1} · {item['name']}",
                "details": f"Dynamic priority {item['priority_score']:.1f}<br/>Population {item['population_now']:,}<br/>Distance {item['distance_m']} m",
            } for idx, item in enumerate(ranking[:7])]
            layers += point_layers("live-case-priorities", priority_points, 76, 21)
            layers += point_layers("live-case-hospitals", hospital_map_data(), 78, 22)

        route_data = []
        endpoint_data = []
        agency_order = ["hazmat", "fire", "police", "bus", "ambulance", "environment", "sensor"]
        for kind in agency_order:
            resources = [r for r in RESOURCES if r.kind == kind and st.session_state.dispatch_status.get(r.id, r.status) != "Busy"]
            if not resources:
                continue
            target = mission_targets_for_kind(kind)[0]
            resource = min(resources, key=lambda r: dist_m(r.lat, r.lon, target["lat"], target["lon"]))
            route_options = build_mission_route_options(resource, target, traffic_segments, routing_backend, amap_key, ors_api_key)
            route = route_options["recommended"]
            if not route.path:
                continue
            route_data.append({
                "path": route.path,
                "color": AGENCY_COLOR[kind] + [235],
                "width": 8,
                "title": f"{AGENCY_LABEL[kind]} → {target['name']}",
                "details": (
                    f"Origin: {resource.name}<br/>Destination: {target['name']}<br/>"
                    f"Mission: {AGENCY_LABEL[kind]} deployment<br/>Status: recommended · awaiting human dispatch<br/>"
                    f"ETA {route.eta_min} min · {route.distance_km} km<br/>Backend: {route.backend}"
                ),
            })
            endpoint_data.extend([
                {
                    "lon": resource.lon, "lat": resource.lat, "color": AGENCY_COLOR[kind] + [245],
                    "glyph": AGENCY_GLYPH[kind], "title": resource.name,
                    "details": f"{AGENCY_LABEL[kind]} origin base",
                },
                {
                    "lon": target["lon"], "lat": target["lat"], "color": AGENCY_COLOR[kind] + [245],
                    "glyph": target.get("glyph", "◎"), "title": target["name"],
                    "details": f"{AGENCY_LABEL[kind]} mission destination",
                },
            ])
        if show_routes_layer and route_data:
            layers += path_layers_with_halo("live-case-mission-routes", route_data, 8, halo_extra=5)
        if show_labels_layer and endpoint_data:
            layers += point_layers("live-case-route-endpoints", endpoint_data, 66, 20)

        resources_data = resource_map_data()
        if show_resources_layer:
            layers += resource_halo_layers("live-case-resources", resources_data)
            if show_labels_layer:
                layers += point_layers("live-case-resources", resources_data, 56, 19)

        layers += incident_icon_layers("live-case-incident", [{
            "lon": active.lon, "lat": active.lat, "color": [255, 89, 94, 250], "glyph": MAP_SYMBOL_GLYPH["incident"],
            "title": "Accident source", "details": "Jinghu Expressway Huai'an section · liquid chlorine release",
        }], get_size=4, size_scale=13)

        pitch = 40
        deck = make_deck(layers, active.lat, active.lon, 12.4, pitch, -10, use_basemap)
        render_map(deck, "live-case-map", 680)
        live_legend: List[Tuple[str, str, str]] = [
            (INCIDENT_LEGEND_TOKEN, "Leak source", "#FF595E"),
            ("▰", "Current toxic-plume zone", "#FF595E"),
            (MAP_SYMBOL_GLYPH["community"], "Ranked vulnerable village", "#FF9F1C"),
            (MAP_SYMBOL_GLYPH["police"], "Police warning / road-control mission", "#00C4FF"),
            (MAP_SYMBOL_GLYPH["fire"], "Fire source-control mission", "#FF7E22"),
            (MAP_SYMBOL_GLYPH["ambulance"], "EMS mission", "#4C6FFF"),
            (MAP_SYMBOL_GLYPH["bus"], "Evacuation pickup mission", "#B46AFF"),
            (MAP_SYMBOL_GLYPH["hospital"], "Receiving hospital", "#00A8FF"),
            ("━", "HazMat / specialist mission", "#FF2D95"),
            ("━", "Environmental monitoring mission", "#00D68F"),
        ]
        render_map_legend(live_legend, "Live response legend")

    with insight_col:
        st.markdown(
            f'<div class="sr-panel selected"><div class="sr-title">{stage["time"]} · {stage["title"]}</div><div class="sr-body">'
            f'<b>Information available now:</b><br/>{stage["known"]}<br/><br/><b>SkyRoute action:</b><br/>{stage["agent"]}</div>'
            f'<span class="sr-badge badge-ai">confidence {stage["confidence"]:.0%}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sr-h2">Dynamic destination ranking</div>', unsafe_allow_html=True)
        for idx, item in enumerate(ranking[:5]):
            css = "sr-selected-row" if idx == 0 else "sr-step"
            st.markdown(
                f'<div class="{css}"><b>{idx + 1}. {item["name"]}</b><br/>'
                f'Score {item["priority_score"]:.1f} · {item["population_now"]:,} people · {item["distance_m"]} m · '
                f'downwind alignment {item["downwind_alignment"]:.0%}</div>',
                unsafe_allow_html=True,
            )

        if top:
            st.markdown(
                f'<div class="sr-alert sr-critical"><div class="sr-title">Immediate operational priority</div>'
                f'<div class="sr-body"><b>{top["name"]}</b><br/>Protection and warning resources are assigned to this target while fire and HazMat units continue to the leak source.</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sr-h2">Agency missions now</div>', unsafe_allow_html=True)
        mission_lines = [
            ("🚒 Fire / HazMat", "Leak source and valve control"),
            ("🚓 Police", f"Warning and access control at {top['name'] if top else 'priority community'}"),
            ("🚑 EMS", f"Casualty collection near {top['name'] if top else 'priority community'}"),
            ("🚌 Evacuation", f"Pickup at {top['name'] if top else 'priority community'}"),
            ("🌿 Environment", "Water, drainage and agricultural receptors"),
            ("📡 Sensors", "Downwind plume edge and community verification"),
        ]
        for label, mission in mission_lines:
            st.markdown(f'<div class="sr-step"><b>{label}</b><br/>{mission}</div>', unsafe_allow_html=True)

        n1, n2 = st.columns(2)
        if n1.button("Open population action", use_container_width=True):
            st.session_state.incident_tab = "Population"
            st.rerun()
        if n2.button("Open resource dispatch", use_container_width=True):
            st.session_state.incident_tab = "Dispatch"
            st.rerun()

    st.markdown('<div class="sr-h2">Recorded outcome benchmark and SkyRoute response simulation</div>', unsafe_allow_html=True)
    h_col, s_col = st.columns(2)
    with h_col:
        st.markdown(
            '<div class="sr-panel"><div class="sr-title">Recorded outcome · reported ranges</div><div class="sr-body">'
            '<b>Deaths:</b> 27–28<br/><b>Hospitalised:</b> approximately 285–350<br/>'
            '<b>Evacuated:</b> approximately 10,000–15,000 people<br/>'
            '<b>Expressway closure:</b> about 110 km for roughly 20 hours<br/>'
            '<b>Leak containment and clearance:</b> approximately 65 hours<br/>'
            '<b>Environmental impact:</b> livestock, poultry and crop damage'
            '</div></div>',
            unsafe_allow_html=True,
        )
    with s_col:
        st.markdown(
            '<div class="sr-panel selected"><div class="sr-title">SkyRoute live-response benchmark</div><div class="sr-body">'
            '<b>Destination ranking:</b> villages become explicit protection targets immediately<br/>'
            '<b>Parallel allocation:</b> each agency receives a different operational destination<br/>'
            '<b>Continuous re-planning:</b> priorities and road routes update with each new report<br/>'
            '<b>Transparent reasoning:</b> population, proximity, plume alignment and confidence remain visible<br/>'
            '<b>Evaluation:</b> modeled warning and exposure reduction, not a claim about specific lives saved'
            '</div></div>',
            unsafe_allow_html=True,
        )

def page_agent() -> None:
    if st.session_state.get("nav_page") == "SkyRoute AI Copilot":
        return_label = st.session_state.get("agent_return_page", "Central & Prevention")
        st.markdown(
            f'<div class="sr-agent-return"><div class="sr-small">AI AGENT · return destination</div>'
            f'<div class="sr-title">{return_label}</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("← Back to previous workspace", key="agent-return-button", use_container_width=False):
            return_from_agent()
    st.markdown('<div class="sr-h2">SkyRoute AI Copilot · operational intelligence core</div>', unsafe_allow_html=True)
    chat_col, context_col = st.columns([1.32, 1])

    with chat_col:
        prompt_cols = st.columns(3)
        quick_prompts = [
            "Why is this protective action recommended?",
            "Which school is at risk first?",
            "What is the current traffic problem?",
        ]
        for col, prompt_text in zip(prompt_cols, quick_prompts):
            if col.button(prompt_text, key=f"quick-{prompt_text}", use_container_width=True):
                st.session_state.agent_messages.append({"role": "user", "content": prompt_text})
                st.session_state.agent_messages.append({"role": "assistant", "content": agent_answer(prompt_text)})
                st.rerun()

        for message in st.session_state.agent_messages[-14:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        question = st.chat_input("Ask the AI to explain, compare or add decisions and resources")
        if question:
            st.session_state.agent_messages.append({"role": "user", "content": question})
            answer = agent_answer(question)
            st.session_state.agent_messages.append({"role": "assistant", "content": answer})
            st.rerun()

    with context_col:
        st.markdown('<div class="sr-h2">Agent live context</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sr-panel"><div class="sr-title">Operational memory</div><div class="sr-body">{agent_context_summary()}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="sr-h2">Agent actions</div>', unsafe_allow_html=True)
        if st.button("Add recommended population decision", use_container_width=True):
            option = choose_recommended_decision(population_decisions(incident_state), incident_state["recommendation"])
            add_decision_to_plan(option)
            st.rerun()
        if st.button("Add road closure", use_container_width=True):
            option = next(o for o in traffic_control_options() if o.id == "TR-CLOSE")
            add_decision_to_plan(option)
            st.rerun()
        if st.button("Add drain protection", use_container_width=True):
            option = next(o for o in environmental_decisions(active) if o.id == "ENV-DRAIN")
            add_decision_to_plan(option)
            st.rerun()
        if st.button("Open consolidated plan", type="primary", use_container_width=True):
            st.session_state.nav_page = "Incident Command"
            st.session_state.incident_tab = "Plan"
            st.rerun()

        st.markdown('<div class="sr-h2">SkyTech agent bridge</div>', unsafe_allow_html=True)
        st.markdown('<div class="sr-panel"><div class="sr-title">Inputs consumed</div><div class="sr-body">Accident Recognition · Material Assessment · Impact Range · Sensitive Target Collision · Plan & Resource</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sr-panel"><div class="sr-title">Outputs generated</div><div class="sr-body">Ranked protective actions · resource selection · real-street routes · traffic controls · environmental controls · command-review payload</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="sr-alert sr-good"><div class="sr-title">Human command authority</div><div class="sr-body">The AI can recommend and prepare actions, but dispatch remains blocked until the commander confirms the plan.</div></div>', unsafe_allow_html=True)


# =============================================================================
# PAGE 9 — CASES AND DATA
# =============================================================================
def page_cases() -> None:
    st.markdown('<div class="sr-h2">Comparable cases and production-data roadmap</div>', unsafe_allow_html=True)
    selected_case = st.selectbox("Inspect comparable lesson", HISTORICAL_CASES["Case"].tolist())
    row = HISTORICAL_CASES[HISTORICAL_CASES["Case"] == selected_case].iloc[0]
    st.markdown(
        f'<div class="sr-panel"><div class="sr-title">{row.Case} · {row.Place}, {row.Year}</div><div class="sr-body"><b>Hazard:</b> {row.Hazard}<br/><b>Operational lesson:</b> {row.Lesson}</div></div>',
        unsafe_allow_html=True,
    )
    case_fig = go.Figure(go.Bar(
        x=HISTORICAL_CASES["Year"].tolist(),
        y=list(range(1, len(HISTORICAL_CASES) + 1)),
        text=HISTORICAL_CASES["Case"].tolist(),
        textposition="auto",
    ))
    case_fig.update_layout(title="Comparable incident timeline", yaxis=dict(visible=False), xaxis=dict(title="Year", showgrid=False))
    st.plotly_chart(transparent_plot_layout(case_fig, 270), use_container_width=True, config={"displayModeBar": False})

    roadmap = [
        ("Traffic state", "AMap traffic-status API", "Live connector + simulation fallback"),
        ("Road routing", "OSMnx / AMap", "Real-street geometry enabled"),
        ("Plume", "Validated local model", "Demonstration geometry to replace"),
        ("Population", "Census + occupancy + mobility", "Routine-activity estimate"),
        ("Resources", "SkyTech / municipal systems", "Simulated secure-interface payload"),
        ("Weather", "CMA + field sensors", "Visual scenario dashboard"),
    ]
    st.markdown('<div class="sr-h2">Production integration roadmap</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for index, (capability, source, status) in enumerate(roadmap):
        with cols[index % 3]:
            st.markdown(f'<div class="sr-panel"><div class="sr-title">{capability}</div><div class="sr-body"><b>Preferred source:</b> {source}<br/><b>Prototype:</b> {status}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sr-h2">Technical diagnostics</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Streamlit", st.__version__)
    d2.metric("OSMnx", "Installed" if OSMNX_AVAILABLE else "Missing")
    d3.metric("Local ORS", fetch_ors_health().get("status", "unknown") if ors_is_local() else "Remote")
    d4.metric("Maps/page", "1 maximum")
    st.caption(f"Traffic mode: {data_mode} · Routing backend: {routing_backend} · Basemap: {'enabled' if use_basemap else 'disabled'}")


# =============================================================================
# INCIDENT COMMAND WORKSPACE — TAB-LIKE CONDITIONAL RENDERING
# =============================================================================
def sync_incident_tab_from_widget() -> None:
    st.session_state.incident_tab = st.session_state.incident_tab_widget



def page_incident_command() -> None:
    top_left, top_right = st.columns([1, 4.2])
    with top_left:
        if st.button("← Back to city command", use_container_width=True):
            st.session_state.nav_page = "Central & Prevention"
            st.rerun()
    with top_right:
        st.markdown(
            f'<div class="sr-panel"><div class="sr-title">{active.id} · {active.substance} · {active.threat}</div>'
            f'<div class="sr-small">{active.road} · detected {active.detected_at} · live command workspace</div></div>',
            unsafe_allow_html=True,
        )

    if active.id == HISTORICAL_INCIDENT_ID:
        current_stage = HISTORICAL_RECONSTRUCTION_STAGES[int(st.session_state.get("historical_stage", 0))]
        st.markdown(
            f'<div class="sr-live-case"><div class="sr-title">LIVE INCIDENT SIMULATION · Huai’an “3·29” chlorine leak</div>'
            f'<div class="sr-body"><b>{current_stage["time"]} · {current_stage["title"]}</b><br/>'
            f'The event is unfolding now. SkyRoute receives only the information available at this stage and updates priorities, missions and routes in real time.</div></div>',
            unsafe_allow_html=True,
        )

    workflow_col, workspace_col = st.columns([0.84, 4.2], gap="medium")
    with workflow_col:
        render_agent_workflow_tracker()
        if active.id == HISTORICAL_INCIDENT_ID:
            stage_index = int(st.session_state.get("historical_stage", 0))
            stage = HISTORICAL_RECONSTRUCTION_STAGES[stage_index]
            st.markdown(
                f'<div class="sr-panel"><div class="sr-small">LIVE UPDATE</div>'
                f'<div class="sr-title">{stage["time"]}</div><div class="sr-body">{stage["title"]}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="sr-small" style="margin-top:9px">Completed steps remain lit. The final dispatch is never automatic.</div>',
            unsafe_allow_html=True,
        )

    with workspace_col:
        render_ai_command_strip()
        render_selected_decision_strip()
        available_tabs = INCIDENT_TABS + (["Live Case Simulation"] if active.id == HISTORICAL_INCIDENT_ID else [])
        if st.session_state.incident_tab not in available_tabs:
            st.session_state.incident_tab = "Live Case Simulation" if active.id == HISTORICAL_INCIDENT_ID else "Overview"
        if st.session_state.get("incident_tab_widget") != st.session_state.incident_tab:
            st.session_state.incident_tab_widget = st.session_state.incident_tab
        st.radio(
            "Incident command section",
            available_tabs,
            key="incident_tab_widget",
            horizontal=True,
            label_visibility="collapsed",
            on_change=sync_incident_tab_from_widget,
        )
        tab_functions = {
            "Overview": page_incident_overview,
            "Population": page_population,
            "Dispatch": page_dispatch,
            "Traffic": page_traffic,
            "Environment": page_environment,
            "Plan": page_plan,
            "AI Copilot": page_agent,
            "Live Case Simulation": page_historical_study,
        }
        tab_functions[st.session_state.incident_tab]()


# =============================================================================
# PAGE ROUTER — ONLY THE ACTIVE WORKSPACE IS RENDERED
# =============================================================================
PAGE_FUNCTIONS = {
    "Central & Prevention": page_central,
    "Incident Command": page_incident_command,
    "SkyRoute AI Copilot": page_agent,
    "Cases & Data": page_cases,
}

PAGE_FUNCTIONS.get(page, page_central)()

st.markdown(
    """
<div class="sr-footer">
SkyRoute / 天途 v14 · live vulnerability-aware emergency decision demonstrator.<br/>
Default positions, traffic, population estimates, plume geometry, hospital capacity and response scores are simulation inputs. The Huai'an 2005 scenario is presented as a live incident simulation based on a real event; operational map anchors and changing weather inputs remain modeling assumptions. No real dispatch is performed.<br/>
Production deployment requires official emergency plans, validated vulnerability and dispersion models, licensed data, secure platform integration and final human command authority.
</div>
""",
    unsafe_allow_html=True,
)
