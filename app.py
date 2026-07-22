"""
SkyRoute / 天途 v12 — Live Vulnerability-Aware Emergency Decision Agent
==================================================================
Single-file Streamlit application for a demonstrator of hazardous-material
incident prevention, command, routing, dispatch, population protection,
traffic control, environmental response and executive presentation.

Run on Windows PowerShell
-------------------------
cd "C:\\Users\\leara\\Downloads"
python -m streamlit run skyroute_cco_v4_live_case_brand_ops_v6.py

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
    page_title="SkyRoute v13 | SkyTech CCO",
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
[data-testid="stSidebarCollapsedControl"] {display:none!important;}
.sr-top-controls{border:1px solid rgba(255,255,255,.11);border-radius:14px;padding:10px 12px;background:rgba(5,15,12,.86);margin:4px 0 12px;box-shadow:0 0 22px rgba(0,229,255,.035);}
.sr-control-note{font:9px 'JetBrains Mono';color:#91A87A;margin:-3px 0 8px;}

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
.sr-map-info-control{{position:absolute;right:12px;top:12px;pointer-events:auto;}}
.sr-map-info-control summary{{list-style:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;cursor:pointer;background:rgba(5,15,28,.96);border:1px solid #FFFFFF;color:#FFFFFF;font:700 14px 'Poppins';box-shadow:0 0 13px rgba(255,255,255,.22),0 0 20px rgba(0,229,255,.11);user-select:none;}}
.sr-map-info-control summary::-webkit-details-marker{{display:none;}}
.sr-map-info-control summary:hover{{border-color:#00E5FF;color:#00E5FF;box-shadow:0 0 16px rgba(0,229,255,.42);}}
.sr-map-info-control[open] summary{{border-color:#00E5FF;color:#00E5FF;}}
.sr-map-info-panel{{position:absolute;right:0;top:38px;width:255px;border:1px solid #00E5FF;border-radius:10px;padding:10px 11px;background:rgba(4,13,24,.98);color:#DCE9F2;box-shadow:0 12px 34px rgba(0,0,0,.48),0 0 20px rgba(0,229,255,.12);font:9px 'JetBrains Mono';line-height:1.55;}}
.sr-map-info-panel b{{display:block;color:#FFFFFF;font:700 11px 'Poppins';margin-bottom:5px;}}
.sr-map-legend{{border:1px solid #405334;border-radius:12px;padding:10px 12px;background:rgba(6,17,14,.94);margin:7px 0 12px;}}
.sr-map-legend-title{{font-family:'Poppins';font-size:11px;font-weight:700;color:#D5F26D;margin-bottom:8px;text-transform:uppercase;letter-spacing:.08em;}}
.sr-map-legend-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:7px 12px;}}
.sr-map-legend-item{{display:flex;align-items:center;gap:8px;font-size:10px;color:#D6E2C6;line-height:1.3;}}
.sr-legend-symbol{{width:18px;height:18px;border-radius:5px;display:grid;place-items:center;font-size:13px;font-weight:700;border:1px solid rgba(242,246,232,.45);flex:0 0 18px;}}
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
    "CRITICAL": [255, 59, 48],
    "ELEVATED": [255, 159, 10],
    "MODERATE": [255, 214, 10],
}
STATUS_COLOR = {
    "Available": [0, 255, 133],
    "Requested": [255, 214, 10],
    "En route": [0, 229, 255],
    "On scene": [255, 255, 255],
    "Busy": [255, 59, 48],
}
# Operational map colors intentionally prioritize contrast over brand identity.
AGENCY_COLOR = {
    "police": [0, 229, 255],       # electric cyan
    "fire": [255, 94, 31],         # rescue orange
    "ambulance": [47, 128, 255],   # emergency blue
    "hazmat": [255, 45, 149],      # hazard magenta
    "environment": [0, 255, 133],  # monitoring green
    "bus": [185, 107, 255],        # evacuation violet
    "sensor": [255, 214, 10],      # sensor yellow
}
ROUTE_OBJECTIVE_COLOR = {
    "recommended": [255, 255, 255],
    "fastest": [0, 229, 255],
    "safest": [0, 255, 133],
    "low_traffic": [255, 214, 10],
}
MAP_LINE_COLOR = {
    "road_closure": [255, 255, 255],
    "emergency_corridor": [255, 214, 10],
    "evacuation": [185, 107, 255],
    "hazmat_restricted": [255, 59, 48],
    "hazmat_bypass": [255, 45, 149],
    "environmental_containment": [0, 255, 133],
    "isolation": [255, 214, 10],
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
AGENCY_GLYPH = {
    "police": "🚓",
    "fire": "🚒",
    "ambulance": "🚑",
    "hazmat": "☣",
    "environment": "🌿",
    "bus": "🚌",
    "sensor": "📡",
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
        return [0, 255, 133, 235]
    if congestion < 0.68:
        return [255, 214, 10, 240]
    return [255, 59, 48, 250]


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
        "school": [213, 242, 109],
        "hospital": [82, 161, 190],
        "residential": [82, 161, 190],
        "village": [213, 242, 109],
        "eldercare": [169, 191, 90],
        "park": [169, 191, 90],
        "fuel": [242, 100, 87],
        "commercial": [118, 140, 69],
    }
    glyphs = {
        "school": "🏫",
        "hospital": "🏥",
        "residential": "🏘",
        "village": "🏘",
        "eldercare": "👵",
        "park": "🌳",
        "fuel": "⛽",
        "commercial": "🏬",
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
NAVIGATION = [
    "Central & Prevention",
    "Incident Command",
    "SkyRoute AI Copilot",
    "Cases & Data",
]

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
def scatter_layer(
    layer_id: str,
    data: List[Dict[str, Any]],
    radius: Any = 70,
    color: Any = "color",
    stroked: bool = True,
    pickable: bool = True,
) -> pdk.Layer:
    return pdk.Layer(
        "ScatterplotLayer",
        id=layer_id,
        data=data,
        get_position="[lon, lat]",
        get_radius=radius,
        get_fill_color=color,
        stroked=stroked,
        get_line_color=[242, 246, 232, 220],
        line_width_min_pixels=1.2,
        pickable=pickable,
        auto_highlight=True,
    )



def text_layer(layer_id: str, data: List[Dict[str, Any]], size: int = 18) -> pdk.Layer:
    return pdk.Layer(
        "TextLayer",
        id=layer_id,
        data=data,
        get_position="[lon, lat]",
        get_text="glyph",
        get_size=size,
        get_color=[242, 246, 232, 255],
        get_alignment_baseline="center",
        get_text_anchor="middle",
        font_family="Segoe UI Emoji, Noto Color Emoji, Arial Unicode MS, sans-serif",
        pickable=False,
    )


def point_layers(layer_prefix: str, data: List[Dict[str, Any]], radius: Any = 65, size: int = 18) -> List[pdk.Layer]:
    return [scatter_layer(f"{layer_prefix}-points", data, radius), text_layer(f"{layer_prefix}-labels", data, size)]

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
    )


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
    )


def public_environment_layers(prefix: str) -> List[pdk.Layer]:
    if not PROTECTED_AREAS:
        return []
    return [polygon_layer(
        f"{prefix}-public-eco",
        PROTECTED_AREAS,
        [0, 255, 133, 24],
        [0, 255, 133, 215],
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


def render_map_info() -> None:
    st.markdown(
        """
        <div class="sr-map-info-anchor">
          <details class="sr-map-info-control">
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
    render_map_info()
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
        st.caption("Try disabling the CARTO basemap in Operational controls. The operational overlays will still render.")
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
        rendered.append(
            f'<div class="sr-map-legend-item"><span class="sr-legend-symbol" style="background:{color}">{symbol}</span><span>{label}</span></div>'
        )
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
            fill, line, level = [242, 100, 87, 42], [242, 100, 87, 230], "Critical priority"
        elif ratio >= 0.55:
            fill, line, level = [213, 242, 109, 34], [213, 242, 109, 220], "High priority"
        else:
            fill, line, level = [82, 161, 190, 28], [82, 161, 190, 190], "Monitored priority"
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
                f"Downwind alignment {item['downwind_alignment']:.0%}"
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
        color = [169, 191, 90, 245] if status == "Available" else [118, 140, 69, 245] if status == "Limited" else [242, 100, 87, 245]
        output.append({
            **poi,
            "color": color,
            "glyph": "🏥",
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
        color = [213, 242, 109, 220] if status == "En route" else [169, 191, 90, 220] if status == "On scene" else [118, 140, 69, 220]
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
        color = [242, 100, 87, 190] if priority >= 90 else [213, 242, 109, 185] if priority >= 60 else [82, 161, 190, 175]
        for idx, (dx, dy) in enumerate(offsets):
            share = pop / len(offsets) * (1.12 if idx == 0 else 0.98)
            columns.append({
                "lon": poi["lon"] + dx,
                "lat": poi["lat"] + dy,
                "elevation": min(900, 45 + math.sqrt(share) * 28),
                "radius": 42 if idx else 58,
                "color": color,
                "title": f"{poi['name']} · WorldPop 2020 illustrative 3D",
                "details": f"Illustrative population column<br/>Estimated local presence share: {share:.0f}",
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
        elevation_scale=1,
        radius=48,
        get_fill_color="color",
        disk_resolution=12,
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
                "color": [118, 140, 69, 125] if j else [169, 191, 90, 145],
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
        wireframe=False,
        pickable=True,
        opacity=0.82,
    )


def _nearest_traffic_roadblock_points() -> List[Dict[str, Any]]:
    candidate_segments = [seg for seg in traffic_segments if len(seg.get("path", [])) >= 4]
    if not candidate_segments:
        return [
            {"id": "RB-A", "name": "North access roadblock", "lat": active.lat + 0.006, "lon": active.lon - 0.004, "type": "roadblock", "glyph": "⛔"},
            {"id": "RB-B", "name": "South access roadblock", "lat": active.lat - 0.006, "lon": active.lon + 0.004, "type": "roadblock", "glyph": "⛔"},
        ]
    segment = min(candidate_segments, key=lambda seg: _distance_to_path_m(active.lat, active.lon, seg["path"]))
    path = segment["path"]
    idx = min(range(len(path)), key=lambda i: dist_m(active.lat, active.lon, path[i][1], path[i][0]))
    step = max(2, len(path) // 10)
    a = path[max(0, idx-step)]
    b = path[min(len(path)-1, idx+step)]
    return [
        {"id": "RB-A", "name": f"{segment.get('name','Road')} · upstream roadblock", "lat": a[1], "lon": a[0], "type": "roadblock", "glyph": "⛔"},
        {"id": "RB-B", "name": f"{segment.get('name','Road')} · downstream roadblock", "lat": b[1], "lon": b[0], "type": "roadblock", "glyph": "⛔"},
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
        "glyph": "⚠",
        "details": "Source control and technical containment",
    }
    roadblocks = _nearest_traffic_roadblock_points()
    hospitals = [{
        "id": f"TARGET-{item['id']}",
        "name": item["name"],
        "lat": item["lat"],
        "lon": item["lon"],
        "type": "hospital",
        "glyph": "🏥",
        "details": f"Receiving hospital · {item.get('available_beds', 0)} beds available",
    } for item in hospital_map_data()]
    shelters = [{
        "id": f"TARGET-{item['id']}",
        "name": item["name"],
        "lat": item["lat"],
        "lon": item["lon"],
        "type": "shelter",
        "glyph": "⛺",
        "details": f"Evacuation shelter · capacity {item['capacity']:,}",
    } for item in SHELTERS]
    environmental = []
    if WATER_ZONES:
        lat, lon = _polygon_centroid(WATER_ZONES[0].get("polygon", []))
        environmental.append({"id": "TARGET-WATER", "name": WATER_ZONES[0].get("name", "Water receptor"), "lat": lat, "lon": lon, "type": "environment", "glyph": "💧", "details": "Environmental protection mission"})
    if DRAINS:
        environmental.append({"id": "TARGET-DRAIN", "name": DRAINS[0]["name"], "lat": DRAINS[0]["lat"], "lon": DRAINS[0]["lon"], "type": "environment", "glyph": "🌿", "details": "Drain and runoff protection"})
    plume = incident_state.get("plume_polygon", [])
    if len(plume) >= 3:
        edge_lon = float(np.mean([plume[1][0], plume[2][0]]))
        edge_lat = float(np.mean([plume[1][1], plume[2][1]]))
        environmental.append({"id": "TARGET-PLUME-EDGE", "name": "Downwind plume-edge monitoring point", "lat": edge_lat, "lon": edge_lon, "type": "sensor", "glyph": "📡", "details": "Mobile sensor deployment point"})

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
        return {"id": "TARGET-INCIDENT", "name": "Incident source", "lat": active.lat, "lon": active.lon, "glyph": "⚠", "details": "Incident source"}
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

# Main navigation replaces the former permanent left sidebar.
def sync_navigation_from_widget() -> None:
    st.session_state.nav_page = st.session_state.nav_widget

if st.session_state.get("nav_widget") != st.session_state.nav_page:
    st.session_state.nav_widget = st.session_state.nav_page

nav_col, incident_col = st.columns([2.25, 1])
with nav_col:
    st.radio(
        "Operational workspace",
        NAVIGATION,
        key="nav_widget",
        on_change=sync_navigation_from_widget,
        horizontal=True,
        label_visibility="collapsed",
    )
page = st.session_state.nav_page

incident_index = next((idx for idx, inc in enumerate(INCIDENTS) if inc.id == active.id), 0)
with incident_col:
    selected_incident_idx = st.selectbox(
        "Selected incident",
        range(len(INCIDENTS)),
        index=incident_index,
        format_func=lambda idx: f"{INCIDENTS[idx].id} · {INCIDENTS[idx].substance}",
        label_visibility="collapsed",
    )

if INCIDENTS[selected_incident_idx].id != st.session_state.active_incident_id:
    st.session_state.active_incident_id = INCIDENTS[selected_incident_idx].id
    st.session_state.plan_confirmed = False
    st.session_state.plan_decisions = {}
    st.session_state.resource_quantities = {kind: 0 for kind in AGENCY_LABEL}
    st.session_state.selected_resource_ids = {}
    st.session_state.selected_routes = {}
    st.session_state.selected_mission_target_ids = {}
    st.session_state.dispatch_status = {}
    st.session_state.historical_stage = 0
    st.session_state.nav_page = "Incident Command"
    st.session_state.incident_tab = "Live Case Simulation" if INCIDENTS[selected_incident_idx].id == HISTORICAL_INCIDENT_ID else "Overview"
    log_event(f"Incident selected: {INCIDENTS[selected_incident_idx].id}", "incident")
    st.rerun()
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

with st.expander("Operational controls · data, map layers and scenario", expanded=False):
    data_tab, layers_tab, scenario_tab = st.tabs(["Data & routing", "Map layers", "Scenario assumptions"])
    with data_tab:
        data_col, route_col, base_col = st.columns([1, 1.35, .9])
        with data_col:
            data_mode = st.selectbox("Traffic source", ["Simulated live", "AMap live if configured"])
        with route_col:
            routing_backend = st.selectbox(
                "Routing backend",
                ["OpenRouteService local real streets", "Automatic real streets", "AMap live route", "OSMnx real streets", "OSRM public real streets"],
                help="The local OpenRouteService returns road-network GeoJSON from the Jiangsu graph running in Docker.",
            )
        with base_col:
            use_basemap = st.toggle("CARTO dark basemap", value=True)

        if ors_is_local():
            ors_api_key = ""
            health = fetch_ors_health()
            if health.get("ok"):
                st.success("Local OpenRouteService ready · Jiangsu graph")
            else:
                st.warning(f"Local OpenRouteService: {health.get('status', 'not reachable')}")
        else:
            ors_api_key = st.text_input(
                "OpenRouteService API key",
                key="ors_api_key_input",
                type="password",
                help="Only required when ORS_BASE_URL points to the remote HeiGIT service.",
            )

    with layers_tab:
        l1, l2, l3 = st.columns(3)
        with l1:
            show_population_layer = st.toggle("Vulnerable populations and facilities", value=True)
            show_resources_layer = st.toggle("Emergency bases and active units", value=True)
            show_routes_layer = st.toggle("Mission routes", value=True)
        with l2:
            show_traffic_layer = st.toggle("Traffic and road controls", value=True)
            show_water_layer = st.toggle("Water bodies", value=True)
            show_environment_layer = st.toggle("Environmental protection areas", value=True)
        with l3:
            show_labels_layer = st.toggle("Map symbols and labels", value=True)
            show_3d_buildings = st.toggle("Illustrative 3D urban context", value=False)
            show_worldpop_3d = st.toggle("WorldPop 2020 · illustrative 3D", value=False)

    with scenario_tab:
        st.markdown('<div class="sr-control-note">Simulation inputs and decision assumptions. These controls remain available without occupying a permanent side panel.</div>', unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1:
            wind_speed_kmh = st.slider("Wind speed (km/h)", 2, 45, 16)
            wind_direction = st.slider("Wind direction (degrees)", 0, 359, 115)
            rain_mm_h = st.slider("Rainfall (mm/h)", 0, 80, 18)
        with s2:
            temperature_c = st.slider("Temperature (°C)", 5, 45, 34)
            road_wetness = st.slider("Road wetness", 0.0, 1.0, 0.65, 0.05)
            traffic_index = st.slider("Traffic index", 0.0, 10.0, 7.4, 0.1)
            hazmat_flow = st.slider("HazMat trucks per hour", 0, 80, 28)
        with s3:
            evacuation_capacity_ppm = st.slider("Evacuation capacity (people/min)", 20, 300, 95)
            setup_delay_min = st.slider("Mobilisation delay (min)", 1, 30, 7)
            shelter_quality = st.slider("Shelter quality", 0.2, 0.95, 0.68, 0.01)

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
 <div class="sr-brand">{skyroute_logo_html()}<div><div class="sr-sub">{"Huai’an live chlorine response simulation" if active.id == HISTORICAL_INCIDENT_ID else "Interactive prevention, routing and incident command · Nanjing pilot"}</div></div></div>
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
            "glyph": "!",
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
            "color": STATUS_COLOR.get(status, [213, 242, 109]) + [230],
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
        if route is None or len(route.path) < 2:
            continue
        paths.append({
            "path": route.path,
            "color": AGENCY_COLOR[kind] + [min(245, alpha_other + 35)],
            "width": 8,
            "title": f"{AGENCY_LABEL[kind]} → {target['name']}",
            "details": f"Mission route<br/>ETA {route.eta_min} min · {route.distance_km} km<br/>Backend: {route.backend}",
        })
    return [path_layer("plan-resource-routes", paths, 8)] if paths else []

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
    routes = [(key, route) for key, route in options.items() if key != "recommended"]
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
                **point, "color": [213, 242, 109, strength], "glyph": "S",
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
                "color": [255, 45, 149, 240], "glyph": "T",
                "title": f"HazMat truck {truck['id']}",
                "details": f"Cargo: {truck['substance']}<br/>Speed: {truck['speed']} km/h<br/>Corridor: {truck['route']}",
            })
        layers += point_layers("hazmat-trucks", truck_data, 75, 12)
        layers += point_layers("ordinary-accidents", [{
            **acc, "color": [118, 140, 69, 230] if acc["severity"] == "minor" else [242, 100, 87, 235],
            "glyph": "X", "title": acc["title"], "details": f"{acc['road']}<br/>Severity: {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 60, 11)
        layers += point_layers("incidents", incident_map_data(), 145, 16)

        center_lat, center_lon, map_zoom = 32.160, 118.704, 11.35
        if selected_alert:
            proposed_path = preventive_alternative_path(selected_alert)
            layers.append(path_layer("selected-preventive-risk", [{
                "path": selected_alert.path, "color": [242, 100, 87, 235], "width": 17,
                "title": f"Current risk · {selected_alert.title}", "details": selected_alert.reason,
            }], 17))
            layers.append(path_layer("selected-preventive-highlight", [{
                "path": selected_alert.path, "color": [242, 246, 232, 220], "width": 7,
                "title": "Affected segment", "details": selected_alert.recommended_action,
            }], 7))
            if proposed_path:
                layers.append(path_layer("selected-preventive-alternative", [{
                    "path": proposed_path, "color": [0, 229, 255, 250], "width": 12,
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
            ("⚠", "Hazardous-material incident", "#F26457"),
            ("T", "HazMat vehicle", "#FF2D95"),
            ("X", "Ordinary road incident", "#FF3B30"),
            ("", "Traffic: free / slow / congested", "#FFD60A"),
            ("", "HazMat corridor: low / medium / high risk", "#FF9F0A"),
            ("🌿", "Environmental / protected receptor", "#00FF85"),
        ]
        if selected_alert:
            city_legend += [
                ("", "Selected high-risk road segment", "#FF3B30"),
                ("", "AI preventive alternative", "#00E5FF"),
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
            layers.append(polygon_layer("incident-water", water_data, [82, 161, 190, 58], [82, 161, 190, 205]))
        if show_traffic_layer:
            layers.append(path_layer("incident-traffic", traffic_path_data(), 8))

        plume_data = [{
            "polygon": incident_state["plume_polygon"],
            "title": "Downwind protective-action zone",
            "details": f"Length {incident_state['protective_distance']/1000:.1f} km<br/>Wind {wind_label(wind_direction)} {wind_speed_kmh} km/h",
        }]
        layers.append(polygon_layer("incident-plume", plume_data, [242, 100, 87, 68], [242, 100, 87, 235]))
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

        layers += point_layers("incident-marker", [{
            "id": active.id,
            "lon": active.lon,
            "lat": active.lat,
            "color": THREAT_COLOR[active.threat] + [250],
            "glyph": "⚠",
            "title": f"{active.id} · {active.substance}",
            "details": f"Leak estimate: {incident_state['dynamic_leak']:.0f} kg/min<br/>{active.description}",
        }], 100, 22)

        pitch = 54 if (show_3d_buildings or show_worldpop_3d) else 42
        deck = make_deck(layers, active.lat, active.lon, 13.05, pitch, -12, use_basemap)
        render_map(deck, "incident-overview-map", 650)
        legend = [
            ("⚠", "Accident source", "#F26457"),
            ("", "Toxic plume", "#F26457"),
            ("", "Isolation zone", "#FFD60A"),
        ]
        if show_population_layer:
            legend += [("🏘", "Vulnerable community", "#D5F26D"), ("🏥", "Available hospital", "#00A8FF")]
        if show_resources_layer:
            legend += [("🚒", "Fire base", "#FF5E1F"), ("☣", "HazMat base", "#FF2D95"), ("🚓", "Police base", "#00E5FF"), ("🚑", "EMS base", "#2F80FF")]
        if show_water_layer:
            legend.append(("💧", "Water receptor", "#00A8FF"))
        if show_environment_layer:
            legend.append(("🌿", "Protected / environmental area", "#00FF85"))
        if show_worldpop_3d:
            legend.append(("▥", "WorldPop 2020 · illustrative 3D", "#D5F26D"))
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
        }], [242, 100, 87, 60], [242, 100, 87, 225]))
        layers += vulnerability_buffer_layers("population")
        if show_labels_layer:
            layers += point_layers("pop-exposed-pois", incident_state["exposed_pois"], 74, 20)
            layers += point_layers("pop-shelters", [{
                **shelter, "color": [169, 191, 90, 235], "glyph": "⛺", "title": shelter["name"],
                "details": f"Shelter capacity: {shelter['capacity']:,}",
            } for shelter in SHELTERS], 72, 21)
            layers += point_layers("pop-hospitals", hospital_map_data(), 76, 22)
        layers += decision_overlay_layers("population-map", [preview])
        layers += point_layers("population-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "⚠",
            "title": active.id, "details": active.description,
        }], 92, 22)
        pitch = 52 if (show_3d_buildings or show_worldpop_3d) else 34
        render_map(make_deck(layers, active.lat, active.lon, 12.45, pitch, -8, use_basemap), "population-protection-map", 680)
        render_map_legend([
            ("⚠", "Accident source", "#F26457"),
            ("🏘", "Priority community / village", "#D5F26D"),
            ("🏫", "School", "#D5F26D"),
            ("🏥", "Receiving hospital", "#00A8FF"),
            ("⛺", "Evacuation shelter", "#A9BF5A"),
            ("", "Priority buffer size = population + vulnerability", "#768C45"),
        ], "Population protection legend")
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
                route_rgb = ROUTE_OBJECTIVE_COLOR.get(key, AGENCY_COLOR[agency])
                all_routes.append({
                    "path": route.path,
                    "color": route_rgb + ([250] if selected else [115]),
                    "width": 12 if selected else 5,
                    "title": f"{route.label} · {selected_resource.name} → {selected_target['name']}",
                    "details": f"ETA {route.eta_min} min · {route.distance_km} km<br/>{route.backend}",
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
            layers.append(path_layer("dispatch-route-options", all_routes, 6))

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

        layers += point_layers("dispatch-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "⚠",
            "title": active.id, "details": active.description,
        }], 96, 22)

        deployed = deployed_vehicle_data()
        if deployed:
            layers += resource_halo_layers("dispatch-moving-units", deployed)
            if show_labels_layer:
                layers += point_layers("dispatch-moving-units", deployed, 78, 22)

        center_lat = (selected_resource.lat + selected_target["lat"]) / 2
        center_lon = (selected_resource.lon + selected_target["lon"]) / 2
        render_map(make_deck(layers, center_lat, center_lon, 12.35, 42, -8, use_basemap), "dispatch-resources-map", 690)
        render_map_legend([
            (AGENCY_GLYPH[agency], f"{AGENCY_LABEL[agency]} origin / active unit", "#%02X%02X%02X" % tuple(AGENCY_COLOR[agency])),
            (selected_target.get("glyph","◎"), "Assigned mission destination", "#FFFFFF"),
            ("", "AI recommended route", "#FFFFFF"),
            ("", "Fastest route", "#00E5FF"),
            ("", "Lowest-exposure route", "#00FF85"),
            ("", "Lowest-congestion route", "#FFD60A"),
            ("🏥", "Available receiving hospital", "#00A8FF"),
            ("◯", "Pulsing halo = requested / en route / on scene", "#FFFFFF"),
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
            **truck, "color": [118, 140, 69, 235], "glyph": "T", "title": f"HazMat truck {truck['id']}",
            "details": f"{truck['substance']} · {truck['speed']} km/h · route {truck['route']}",
        } for truck in HAZMAT_TRUCKS], 72, 12)
        layers += point_layers("traffic-normal-incidents", [{
            **acc, "color": [242, 100, 87, 235], "glyph": "X", "title": acc["title"],
            "details": f"{acc['road']} · {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 58, 11)
        layers += point_layers("traffic-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": active.description,
        }], 92, 17)
        render_map(make_deck(layers, active.lat, active.lon, 12.25, 35, -8, use_basemap), "traffic-control-map", 675)
        render_map_legend([
            ("!", "Active incident", "#F26457"),
            ("T", "HazMat vehicle", "#FF2D95"),
            ("X", "Ordinary traffic incident", "#FF3B30"),
            ("", "Traffic: free / slow / congested", "#FFD60A"),
            ("", "Road closure", "#FFFFFF"),
            ("", "Emergency corridor", "#FFD60A"),
            ("", "Evacuation route", "#B96BFF"),
            ("", "HazMat bypass", "#FF2D95"),
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
        } for zone in WATER_ZONES], [25, 116, 170, 82], [213, 242, 109, 225]))
        layers.append(polygon_layer("environment-plume", [{
            "polygon": incident_state["plume_polygon"], "title": "Air-impact zone",
            "details": f"Wind {wind_label(wind_direction)} · {wind_speed_kmh} km/h",
        }], [242, 100, 87, 45], [242, 100, 87, 190]))
        layers += point_layers("environment-drains", [{
            **drain, "color": [213, 242, 109, 240], "glyph": "D", "title": drain["name"],
            "details": "Stormwater pathway requiring protection",
        } for drain in DRAINS], 56, 11)
        layers += point_layers("environment-fixed-sensors", [{
            **sensor, "color": [169, 191, 90, 240], "glyph": "S", "title": sensor["name"],
            "details": f"Status: {sensor['status']}",
        } for sensor in SENSORS], 58, 11)
        layers += decision_overlay_layers("environment-map", [preview])
        layers += point_layers("environment-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": incident_state["substance"]["environment"],
        }], 92, 17)
        render_map(make_deck(layers, active.lat, active.lon, 12.65, 38, -8, use_basemap), "environment-protection-map", 675)
        render_map_legend([
            ("!", "Active incident", "#F26457"),
            ("", "Air-impact / toxic-plume zone", "#F26457"),
            ("💧", "Water or ecological receptor", "#00A8FF"),
            ("D", "Drain / stormwater pathway", "#00E5FF"),
            ("S", "Environmental sensor", "#FFD60A"),
            ("🌿", "Protected / environmental area", "#00FF85"),
            ("", "Environmental containment / monitoring action", "#00FF85"),
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

    building_layer = illustrative_buildings_layer("plan")
    population_3d = worldpop_3d_layer("plan")
    if building_layer:
        layers.append(building_layer)
    if population_3d:
        layers.append(population_3d)

    if show_environment_layer:
        layers.extend(public_environment_layers("plan"))
    if show_water_layer:
        layers.append(
            polygon_layer(
                "plan-water",
                [{**zone, "title": zone["name"], "details": "Water or wetland receptor"} for zone in WATER_ZONES],
                [82, 161, 190, 48],
                [82, 161, 190, 205],
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
            [242, 100, 87, 58],
            [242, 100, 87, 230],
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
                "glyph": "⛺",
                "title": shelter["name"],
                "details": f"Evacuation shelter · capacity {shelter['capacity']:,}",
            } for shelter in SHELTERS],
            58,
            19,
        )

    layers += point_layers(
        "plan-incident",
        [{
            "lon": active.lon,
            "lat": active.lat,
            "color": THREAT_COLOR[active.threat] + [250],
            "glyph": "⚠",
            "title": active.id,
            "details": active.description,
        }],
        102,
        23,
    )
    return layers


def page_plan() -> None:
    render_dispatch_receipt()
    st.markdown('<div class="sr-h2">Consolidated operational plan and presentation mode</div>', unsafe_allow_html=True)
    map_col, plan_col = st.columns([1.62, 1])

    with map_col:
        pitch = 54 if (show_3d_buildings or show_worldpop_3d) else 40
        deck = make_deck(consolidated_map_layers(), active.lat, active.lon, 12.3, pitch, -10, use_basemap)
        render_map(deck, "consolidated-plan-map", 690)
        legend_items: List[Tuple[str, str, str]] = [
            ("⚠", "Incident / leak source", "#F26457"),
            ("", "Toxic plume and protective-action zone", "#F26457"),
        ]
        if show_population_layer:
            legend_items += [
                ("🏘", "Vulnerable destination and dynamic buffer", "#D5F26D"),
                ("🏥", "Receiving hospital and availability", "#00A8FF"),
            ]
        if show_resources_layer:
            legend_items += [
                ("🚒", "Fire / HazMat origin or active unit", "#FF5E1F"),
                ("🚓", "Police origin or active unit", "#00E5FF"),
                ("🚑", "EMS origin or active unit", "#2F80FF"),
                ("◉", "Halo = requested, en route or on scene", "#D5F26D"),
            ]
        if show_routes_layer:
            legend_items += [("", "Police route", "#00E5FF"), ("", "Fire route", "#FF5E1F"), ("", "HazMat route", "#FF2D95"), ("", "EMS route", "#2F80FF"), ("", "Evacuation route", "#B96BFF"), ("", "Environmental route", "#00FF85")]
        if show_environment_layer or show_water_layer:
            legend_items += [
                ("🌿", "Environmental protection receptor", "#00FF85"),
                ("💧", "Water / wetland receptor", "#00A8FF"),
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
            layers.append(polygon_layer("live-case-water", [{**zone, "title": zone["name"], "details": "Environmental receptor"} for zone in WATER_ZONES], [82, 161, 190, 50], [82, 161, 190, 195]))
        if show_traffic_layer:
            layers.append(path_layer("live-case-traffic", traffic_path_data(), 7))
        layers.append(polygon_layer("live-case-plume", [{
            "polygon": live_plume,
            "title": f"{stage['title']} chlorine impact zone",
            "details": f"Live input · wind {wind_label(wind_direction)} {wind_speed_kmh} km/h",
        }], [242, 100, 87, 64], [242, 100, 87, 235]))

        layers += vulnerability_buffer_layers("live-case")
        if show_labels_layer:
            priority_points = [{
                **item,
                "color": [242, 100, 87, 245] if idx == 0 else [213, 242, 109, 230],
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
                "details": f"Origin: {resource.name}<br/>Mission: {target['name']}<br/>ETA {route.eta_min} min · {route.distance_km} km",
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
            layers.append(path_layer("live-case-mission-routes", route_data, 8))
        if show_labels_layer and endpoint_data:
            layers += point_layers("live-case-route-endpoints", endpoint_data, 66, 20)

        resources_data = resource_map_data()
        if show_resources_layer:
            layers += resource_halo_layers("live-case-resources", resources_data)
            if show_labels_layer:
                layers += point_layers("live-case-resources", resources_data, 56, 19)

        layers += point_layers("live-case-incident", [{
            "lon": active.lon, "lat": active.lat, "color": [242, 100, 87, 250], "glyph": "⚠",
            "title": "Accident source", "details": "Jinghu Expressway Huai'an section · liquid chlorine release",
        }], 105, 23)

        pitch = 54 if (show_3d_buildings or show_worldpop_3d) else 40
        deck = make_deck(layers, active.lat, active.lon, 12.4, pitch, -10, use_basemap)
        render_map(deck, "live-case-map", 680)
        render_map_legend([
            ("⚠", "Leak source", "#F26457"),
            ("🏘", "Ranked vulnerable village", "#D5F26D"),
            ("🚓", "Police warning / road-control mission", "#00E5FF"),
            ("🚒", "Fire source-control mission", "#FF5E1F"),
            ("🚑", "EMS mission", "#2F80FF"),
            ("🚌", "Evacuation pickup mission", "#B96BFF"),
            ("🏥", "Receiving hospital", "#00A8FF"),
            ("", "HazMat / specialist mission", "#FF2D95"), ("", "Environmental monitoring mission", "#00FF85"),
        ], "Live response legend")

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
SkyRoute / 天途 v12 · live vulnerability-aware emergency decision demonstrator.<br/>
Default positions, traffic, population estimates, plume geometry, hospital capacity and response scores are simulation inputs. The Huai'an 2005 scenario is presented as a live incident simulation based on a real event; operational map anchors and changing weather inputs remain modeling assumptions. No real dispatch is performed.<br/>
Production deployment requires official emergency plans, validated vulnerability and dispersion models, licensed data, secure platform integration and final human command authority.
</div>
""",
    unsafe_allow_html=True,
)
