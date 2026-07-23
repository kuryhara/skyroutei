"""
SkyRoute / 天途 v21 — Compact Layer Toolbar and Flat Map Icons
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


/* Compact map-layer pill bar */
[class*="st-key-layer_toolbar_"]{{border:1px solid rgba(0,229,255,.16);border-radius:10px;background:rgba(4,13,20,.78);padding:4px 6px;margin:5px 0 9px;box-shadow:0 8px 22px rgba(0,0,0,.14);}}
[class*="st-key-layer_toolbar_"] [data-testid="stHorizontalBlock"]{{gap:.34rem!important;align-items:center;}}
[class*="st-key-layer_toolbar_"] [data-testid="column"]{{padding:0!important;}}
.sr-layer-inline-label{{height:28px;display:flex;align-items:center;gap:6px;padding:0 5px;color:#BFD2DF;font:700 9px 'Poppins';white-space:nowrap;}}
.sr-layer-inline-label svg{{width:14px;height:14px;stroke:#00E5FF;filter:drop-shadow(0 0 5px rgba(0,229,255,.4));}}
[class*="st-key-layer_toolbar_"] [data-testid="stButton"]{{margin:0!important;}}
[class*="st-key-layer_toolbar_"] [data-testid="stButton"] button{{min-height:28px!important;height:28px!important;padding:0 9px!important;border-radius:7px!important;font:700 8.5px 'JetBrains Mono'!important;text-transform:lowercase!important;line-height:1!important;box-shadow:none!important;white-space:nowrap!important;}}
[class*="st-key-layer_toolbar_"] [data-testid="stBaseButton-secondary"]{{background:transparent!important;border:1px solid rgba(148,163,184,.18)!important;color:#91A87A!important;}}
[class*="st-key-layer_toolbar_"] [data-testid="stBaseButton-secondary"]:hover{{border-color:rgba(0,229,255,.42)!important;color:#D6EAF2!important;background:rgba(0,229,255,.04)!important;}}
[class*="st-key-layer_toolbar_"] [data-testid="stBaseButton-primary"]{{background:rgba(0,229,255,.11)!important;border:1px solid rgba(0,229,255,.62)!important;color:#E9FCFF!important;box-shadow:inset 0 0 0 1px rgba(0,229,255,.04),0 0 10px rgba(0,229,255,.08)!important;}}
[class*="st-key-layer_toolbar_"] [data-testid="stBaseButton-primary"]:hover{{background:rgba(0,229,255,.17)!important;border-color:#00E5FF!important;}}
@media(max-width:900px){{[class*="st-key-layer_toolbar_"] [data-testid="stHorizontalBlock"]{{gap:.2rem!important;}}[class*="st-key-layer_toolbar_"] [data-testid="stButton"] button{{padding:0 6px!important;font-size:7.8px!important;}}.sr-layer-inline-label{{font-size:8px;gap:4px;}}}}
.sr-data-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px;margin:7px 0 12px;}}
.sr-data-card{{border:1px solid #405334;border-radius:11px;background:linear-gradient(180deg,rgba(8,24,42,.92),rgba(5,15,28,.95));padding:12px;min-height:112px;}}
.sr-data-card .eyebrow{{font:8px 'JetBrains Mono';letter-spacing:.08em;text-transform:uppercase;color:#91A87A;}}
.sr-data-card .name{{font:700 12px 'Poppins';color:#F2F6E8;margin-top:5px;}}
.sr-data-card .source{{font:9.5px 'JetBrains Mono';color:#D6E2C6;line-height:1.5;margin-top:7px;}}
.sr-data-status{{display:inline-block;margin-top:8px;padding:3px 7px;border-radius:999px;border:1px solid #768C45;color:#D5F26D;font:8px 'JetBrains Mono';}}
.sr-data-status.visual{{border-color:#00E5FF;color:#00E5FF;}}
.sr-data-status.sim{{border-color:#FFB703;color:#FFD166;}}
.sr-case-strip{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:8px 0 13px;}}
.sr-case-node{{position:relative;border:1px solid #405334;border-radius:11px;padding:11px;background:rgba(6,18,29,.9);min-height:104px;}}
.sr-case-node:before{{content:'';position:absolute;left:12px;top:0;width:32px;height:2px;background:#00E5FF;box-shadow:0 0 10px rgba(0,229,255,.45);}}
.sr-case-year{{font:700 16px 'Poppins';color:#D5F26D;}}
.sr-case-name{{font:600 9.5px 'Poppins';color:#F2F6E8;line-height:1.35;margin-top:4px;}}
.sr-case-place{{font:8px 'JetBrains Mono';color:#91A87A;margin-top:7px;}}
.sr-data-table{{border:1px solid #405334;border-radius:12px;overflow:hidden;margin-top:8px;}}
.sr-data-row{{display:grid;grid-template-columns:1fr 1.25fr 1.35fr;gap:12px;padding:10px 12px;border-bottom:1px solid rgba(118,140,69,.28);background:rgba(5,15,28,.82);align-items:start;}}
.sr-data-row:last-child{{border-bottom:none;}}
.sr-data-row.header{{background:rgba(213,242,109,.07);font:8px 'JetBrains Mono';text-transform:uppercase;letter-spacing:.08em;color:#91A87A;}}
.sr-data-cell{{font-size:10.5px;line-height:1.45;color:#D6E2C6;}}
.sr-data-cell b{{font-family:'Poppins';color:#F2F6E8;}}
.sr-data-note{{border-left:3px solid #00E5FF;border-radius:0 9px 9px 0;background:rgba(0,229,255,.045);padding:10px 12px;font:9px 'JetBrains Mono';line-height:1.55;color:#B7C99D;margin:8px 0 12px;}}
@media (max-width:1100px){{.sr-data-grid{{grid-template-columns:repeat(2,minmax(0,1fr));}}.sr-case-strip{{grid-template-columns:repeat(2,minmax(0,1fr));}}.sr-data-row{{grid-template-columns:1fr;gap:4px;}}.sr-data-row.header{{display:none;}}}}

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
# ASCII glyphs remain only as a resilient fallback. The primary operational
# markers are compact embedded PNG icons with universally recognizable symbols
# (medical cross, emergency siren, flame, ambulance, hazard diamond, etc.).
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
    'hazmat': 'data:image/png;base64,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',
    'hospital': 'data:image/png;base64,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',
    'bus': 'data:image/png;base64,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',
    'environment': 'data:image/png;base64,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',
    'sensor': 'data:image/png;base64,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',
    'school': 'data:image/png;base64,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',
    'shelter': 'data:image/png;base64,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',
    'community': 'data:image/png;base64,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',
    'truck': 'data:image/png;base64,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',
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
    "K": "school", "R": "shelter", "C": "community", "T": "truck",
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
        "layer_population": True,
        "layer_environment": True,
        "layer_resources": True,
        "layer_traffic_routes": True,
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
        get_position="[lon, lat, 7]",
        get_text="glyph",
        get_size=size,
        size_units="pixels",
        size_min_pixels=max(12, size - 4),
        size_max_pixels=size + 6,
        get_color=[3, 8, 14, 245] if shadow else "text_color",
        get_pixel_offset=[1, -3] if shadow else [0, -4],
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        font_family="Arial",
        character_set=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+!OX-"),
        billboard=True,
        parameters={"depthTest": False},
        pickable=False,
    )


def point_layers(layer_prefix: str, data: List[Dict[str, Any]], radius: Any = 65, size: int = 18) -> List[pdk.Layer]:
    """Render compact operational markers slightly above the map surface.

    The status halo remains attached to the geographic point. PNG symbols are
    billboarded toward the camera, lifted a few metres above the map and bottom-
    anchored so they remain legible at an angled view without looking detached.
    """
    prepared = _prepare_point_data(data)
    icon_items: List[Dict[str, Any]] = []
    text_items: List[Dict[str, Any]] = []
    icon_pixels = int(clamp(size, 17, 21))
    for raw in prepared:
        item = dict(raw)
        icon_key = str(item.get("symbol_key", ""))
        if icon_key in MAP_ICON_MAPPINGS:
            item["icon_data"] = dict(MAP_ICON_MAPPINGS[icon_key])
            # Anchor the lower part of the badge to the location and lift it just
            # enough to prevent the pitched basemap from visually clipping it.
            item["icon_data"]["anchorY"] = 54
            item["icon_size_px"] = icon_pixels
            item["icon_elevation_m"] = 8
            item["fallback_glyph"] = str(item.get("glyph", "O"))[:1]
            icon_items.append(item)
        else:
            text_items.append(item)

    layers: List[pdk.Layer] = [scatter_layer(f"{layer_prefix}-points", prepared, radius)]
    if icon_items:
        layers.append(pdk.Layer(
            "IconLayer",
            id=f"{layer_prefix}-icons",
            data=icon_items,
            icon_mapping=None,
            get_icon="icon_data",
            get_position="[lon, lat, icon_elevation_m]",
            get_size="icon_size_px",
            size_units="pixels",
            size_min_pixels=16,
            size_max_pixels=22,
            get_pixel_offset=[0, -2],
            billboard=True,
            parameters={"depthTest": False},
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
    """Render the incident badge upright and slightly above the map surface."""
    incidents_with_icon: List[Dict[str, Any]] = []
    for raw in data:
        item = dict(raw)
        item["icon_data"] = dict(ALERT_ICON_MAPPING)
        item["icon_data"]["anchorY"] = 55
        item["icon_size_px"] = 21
        item["icon_elevation_m"] = 10
        item["fallback_glyph"] = "!"
        item.setdefault("title", item.get("name", "Incident"))
        item.setdefault("details", item.get("description", "Active incident"))
        incidents_with_icon.append(item)
    icon_layer = pdk.Layer(
        "IconLayer",
        id=f"{layer_prefix}-points",
        data=incidents_with_icon,
        icon_mapping=None,
        get_icon="icon_data",
        get_position="[lon, lat, icon_elevation_m]",
        get_size="icon_size_px",
        size_units="pixels",
        size_min_pixels=19,
        size_max_pixels=23,
        get_pixel_offset=[0, -3],
        billboard=True,
        parameters={"depthTest": False},
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 95],
    )
    return [icon_layer]


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
              Left-drag to pan · right-drag to rotate and change pitch · scroll to zoom.<br/><br/>
              Hold Ctrl while scrolling when the page captures the wheel. On selectable maps, click a highlighted object to open its decision preview.
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
    """Generate restrained, deterministic urban massing for orientation only."""
    items: List[Dict[str, Any]] = []
    source_points = [*pois_live, *resource_map_data()]
    layouts = [
        (-0.00024, -0.00018, 1.00, 0.72),
        (0.00021, -0.00012, 0.72, 0.92),
        (-0.00008, 0.00023, 0.86, 0.70),
        (0.00028, 0.00019, 0.62, 0.66),
    ]
    for idx, item in enumerate(source_points[:38]):
        base_lon, base_lat = float(item["lon"]), float(item["lat"])
        kind = item.get("type")
        base_h = 22 if kind in {"village", "residential"} else 30 if kind == "hospital" else 15
        for j, (dx, dy, sx, sy) in enumerate(layouts):
            factor = 0.78 + ((idx * 7 + j * 5) % 8) * 0.055
            half_w = 0.000105 * sx
            half_h = 0.000082 * sy
            lon, lat = base_lon + dx, base_lat + dy
            poly = [
                [lon-half_w, lat-half_h], [lon+half_w, lat-half_h],
                [lon+half_w, lat+half_h], [lon-half_w, lat+half_h],
                [lon-half_w, lat-half_h],
            ]
            items.append({
                "polygon": poly,
                "height": max(8, min(34, base_h * factor)),
                "color": [65, 91, 111, 102] if j else [86, 116, 134, 120],
                "title": "Illustrative 3D building context",
                "details": "Deterministic visual massing for orientation only; not surveyed building geometry or height.",
            })
    return items


def illustrative_buildings_layer(prefix: str) -> Optional[pdk.Layer]:
    """3D building massing was removed from the operational map."""
    return None


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

show_population_layer = bool(st.session_state.get("layer_population", True))
show_resources_layer = bool(st.session_state.get("layer_resources", True))
show_routes_layer = bool(st.session_state.get("layer_traffic_routes", True))
show_traffic_layer = bool(st.session_state.get("layer_traffic_routes", True))
show_water_layer = bool(st.session_state.get("layer_environment", True))
show_environment_layer = bool(st.session_state.get("layer_environment", True))
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


def render_map_layer_controls(scope: str) -> None:
    """Render a small pill-style map-layer toolbar."""
    global show_population_layer, show_environment_layer, show_water_layer
    global show_resources_layer, show_routes_layer, show_traffic_layer
    global show_3d_buildings

    layer_specs = [
        ("population", "layer_population", "Vulnerable population targets and exposure buffers"),
        ("environment", "layer_environment", "Water, protected areas and environmental receptors"),
        ("resources", "layer_resources", "Police, fire, HazMat, EMS and support resources"),
        ("routes", "layer_traffic_routes", "Traffic state, corridors and operational routes"),
    ]

    with st.container(key=f"layer_toolbar_{scope}"):
        columns = st.columns([0.78, 1.12, 1.22, 1.03, 0.96], gap="small", vertical_alignment="center")
        with columns[0]:
            st.markdown(
                '<div class="sr-layer-inline-label" title="Map layers">'
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"></path>'
                '<path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"></path>'
                '<path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"></path>'
                '</svg><span>Layers</span></div>',
                unsafe_allow_html=True,
            )

        for column, (label, state_key, help_text) in zip(columns[1:], layer_specs):
            is_active = bool(st.session_state.get(state_key, True))
            with column:
                if st.button(
                    label,
                    key=f"{scope}_{state_key}_pill",
                    type="primary" if is_active else "secondary",
                    help=help_text,
                    use_container_width=True,
                ):
                    st.session_state[state_key] = not is_active
                    st.rerun()

    show_population_layer = bool(st.session_state.get("layer_population", True))
    show_environment_layer = bool(st.session_state.get("layer_environment", True))
    show_water_layer = show_environment_layer
    show_resources_layer = bool(st.session_state.get("layer_resources", True))
    show_routes_layer = bool(st.session_state.get("layer_traffic_routes", True))
    show_traffic_layer = show_routes_layer
    show_3d_buildings = False


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

    render_map_layer_controls("city")

    map_col, alert_col = st.columns([1.62, 1])
    with map_col:
        layers: List[pdk.Layer] = []
        building_layer = illustrative_buildings_layer("city")
        if building_layer:
            layers.append(building_layer)
        if show_environment_layer:
            layers.extend(public_environment_layers("city"))
        if show_population_layer:
            layers += vulnerability_buffer_layers("city-population")
        if show_traffic_layer:
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
        if show_routes_layer:
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
        if show_resources_layer:
            layers += point_layers("hazmat-trucks", truck_data, 75, 12)
        if show_traffic_layer:
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

        event = render_map(make_deck(layers, center_lat, center_lon, map_zoom, 47, -18, use_basemap), "city-prevention-map", 630, selectable=True)
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
    render_map_layer_controls("incident")
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

        pitch = 46
        deck = make_deck(layers, active.lat, active.lon, 13.05, pitch, -22, use_basemap)
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
                (MAP_SYMBOL_GLYPH["hospital"], "Hospital · receiving capacity", "#00A8FF"),
            ]
        if show_resources_layer:
            legend_items += [
                (MAP_SYMBOL_GLYPH["fire"], "Fire & rescue · base or active unit", "#FF7E22"),
                (MAP_SYMBOL_GLYPH["hazmat"], "HazMat · base or active unit", "#FF2D95"),
                (MAP_SYMBOL_GLYPH["police"], "Police · base or active unit", "#00C4FF"),
                (MAP_SYMBOL_GLYPH["ambulance"], "Ambulance / EMS · base or active unit", "#4C6FFF"),
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
    st.markdown('<div class="sr-h2">Cases & data</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sr-data-note"><b>Read the prototype by data status:</b> '
        'connected street geometry and dynamic operational estimates. '
        'Each layer is identified by source and operational status.</div>',
        unsafe_allow_html=True,
    )

    data_layers = [
        ("Road network & routing", "OpenStreetMap street geometry with OpenRouteService routing and automatic fallback.", "Connected", ""),
        ("Traffic", "Time-stamped operational simulation; production connector designed for authorized traffic feeds.", "Simulated live", "sim"),
        ("Population", "Routine-activity and sensitive-target estimates recalculated for the active incident time.", "Dynamic estimate", "sim"),
        ("Environment", "Water receptors, protected areas and incident-specific environmental protection targets.", "Public + scenario", ""),
        ("Weather", "Operational scenario values structured for replacement by CMA, sensors or customer feeds.", "Simulated live", "sim"),
    ]
    cards = []
    for name, source, status, css in data_layers:
        cards.append(
            f'<div class="sr-data-card"><div class="eyebrow">Data layer</div>'
            f'<div class="name">{name}</div><div class="source">{source}</div>'
            f'<span class="sr-data-status {css}">{status}</span></div>'
        )
    st.markdown(f'<div class="sr-data-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sr-h2">Comparable incident lessons</div>', unsafe_allow_html=True)
    ordered_cases = HISTORICAL_CASES.sort_values(["Year", "Case"])
    nodes = []
    for _, case in ordered_cases.iterrows():
        nodes.append(
            f'<div class="sr-case-node"><div class="sr-case-year">{int(case.Year)}</div>'
            f'<div class="sr-case-name">{case.Case}</div><div class="sr-case-place">{case.Place}</div></div>'
        )
    st.markdown(f'<div class="sr-case-strip">{"".join(nodes)}</div>', unsafe_allow_html=True)

    selected_case = st.selectbox(
        "Inspect one operational lesson",
        HISTORICAL_CASES["Case"].tolist(),
        label_visibility="collapsed",
    )
    row = HISTORICAL_CASES[HISTORICAL_CASES["Case"] == selected_case].iloc[0]
    a, b, c = st.columns([0.55, 1, 1.45])
    with a:
        st.markdown(f'<div class="sr-card"><div class="k">Year</div><div class="v">{int(row.Year)}</div><div class="d">comparable incident</div></div>', unsafe_allow_html=True)
    with b:
        st.markdown(f'<div class="sr-card"><div class="k">Place</div><div class="v" style="font-size:15px">{row.Place}</div><div class="d">historical reference</div></div>', unsafe_allow_html=True)
    with c:
        st.markdown(f'<div class="sr-card"><div class="k">Hazard</div><div class="v" style="font-size:13px">{row.Hazard}</div><div class="d">incident mechanism</div></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sr-panel selected"><div class="sr-title">Operational lesson</div>'
        f'<div class="sr-body">{row.Lesson}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sr-h2">Production integration roadmap</div>', unsafe_allow_html=True)
    roadmap = [
        ("Traffic state", "Authorized municipal / AMap traffic feed", "Replace the time-stamped simulation while keeping the same congestion-aware logic."),
        ("Road routing", "OpenRouteService, OSM or customer routing service", "Keep deterministic route calculation separate from the AI explanation layer."),
        ("Plume", "Validated local dispersion model and field sensors", "Replace demonstration geometry with calibrated protective-action zones."),
        ("Population", "Census, occupancy, mobility and facility feeds", "Update exposure and vulnerability priorities continuously."),
        ("Resources", "SkyTech, CAD, AVL or municipal systems", "Use authenticated unit status, capability and location data."),
        ("Weather", "CMA, station and incident-sensor feeds", "Continuously trigger recalculation when conditions change."),
    ]
    rows = ['<div class="sr-data-row header"><div>Capability</div><div>Production source</div><div>What changes</div></div>']
    for capability, source, change in roadmap:
        rows.append(
            f'<div class="sr-data-row"><div class="sr-data-cell"><b>{capability}</b></div>'
            f'<div class="sr-data-cell">{source}</div><div class="sr-data-cell">{change}</div></div>'
        )
    st.markdown(f'<div class="sr-data-table">{"".join(rows)}</div>', unsafe_allow_html=True)

    with st.expander("Technical diagnostics"):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Streamlit", st.__version__)
        d2.metric("OSMnx", "Installed" if OSMNX_AVAILABLE else "Missing")
        d3.metric("Routing", fetch_ors_health().get("status", "unknown") if ors_is_local() else "Remote ORS")
        d4.metric("Map rendering", "PyDeck / WebGL")
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
