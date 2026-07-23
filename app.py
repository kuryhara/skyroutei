"""
SkyRoute / 天途 v10 — Interactive SkyTech Emergency Decision Agent
==================================================================
Single-file Streamlit application for a demonstrator of hazardous-material
incident prevention, command, routing, dispatch, population protection,
traffic control, environmental response and executive presentation.

Run on Windows PowerShell
-------------------------
cd "C:\\Users\\leara\\Downloads"
python -m streamlit run skyroute_cco_v4_complete.py

Required packages
-----------------
python -m pip install streamlit pydeck plotly pandas numpy requests networkx

Optional packages
-----------------
python -m pip install osmnx

Optional AMap integration
-------------------------
Create .streamlit/secrets.toml beside the project folder:
AMAP_KEY = "YOUR_WEB_SERVICE_KEY"

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
    page_title="SkyRoute v10 | SkyTech CCO",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

INK = "#040b15"
PANEL = "#08182a"
PANEL_2 = "#061321"
LINE = "#17405f"
CYAN = "#28d7ff"
BLUE = "#3b82f6"
TEAL = "#22e0bd"
AMBER = "#ffb44a"
RED = "#ff5068"
PURPLE = "#bd71ff"
GREEN = "#63e58e"
TEXT = "#ecf8ff"
MUTED = "#91b3c9"

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
html, body, [class*="css"] {{font-family:'Inter',sans-serif;}}
.stApp {{background:radial-gradient(circle at 80% -10%,#123c65 0%,{INK} 34%,#020711 100%);color:{TEXT};}}
#MainMenu, footer, header {{visibility:hidden;}}
.block-container {{padding-top:.75rem;padding-bottom:2rem;max-width:1850px;}}
section[data-testid="stSidebar"] {{background:linear-gradient(180deg,{PANEL_2},#030913);border-right:1px solid {LINE};}}
section[data-testid="stSidebar"] * {{border-radius:8px;}}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown {{color:{MUTED}!important;}}
.sr-top {{border:1px solid #1a557d;background:linear-gradient(135deg,rgba(16,55,91,.96),rgba(4,15,28,.98));box-shadow:0 0 42px rgba(40,215,255,.09);border-radius:15px;padding:14px 18px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;}}
.sr-brand {{display:flex;gap:13px;align-items:center;}}
.sr-logo {{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;color:#00131d;font-family:'Space Grotesk';font-weight:700;background:linear-gradient(135deg,{CYAN},{TEAL});box-shadow:0 0 23px rgba(40,215,255,.38);}}
.sr-name {{font-family:'Space Grotesk';font-size:22px;font-weight:700;}}
.sr-sub {{font:10px 'JetBrains Mono';color:{MUTED};letter-spacing:.08em;text-transform:uppercase;margin-top:2px;}}
.sr-topstats {{display:flex;gap:24px;flex-wrap:wrap;}}
.sr-topstat {{font:9.5px 'JetBrains Mono';color:{MUTED};text-transform:uppercase;}}
.sr-topstat b {{display:block;color:{TEXT};font-size:11.5px;margin-top:4px;text-transform:none;}}
.sr-card {{border:1px solid {LINE};border-radius:12px;padding:12px 14px;background:linear-gradient(180deg,rgba(8,24,42,.98),rgba(4,13,25,.98));box-shadow:inset 0 1px rgba(255,255,255,.025);min-height:86px;}}
.sr-card .k {{font:9px 'JetBrains Mono';color:{MUTED};text-transform:uppercase;letter-spacing:.06em;}}
.sr-card .v {{font-family:'Space Grotesk';font-size:19px;font-weight:700;margin-top:5px;}}
.sr-card .d {{font:9.5px 'JetBrains Mono';color:{MUTED};margin-top:5px;}}
.sr-h2 {{font-family:'Space Grotesk';font-size:14px;font-weight:700;border-left:3px solid {CYAN};padding-left:9px;margin:15px 0 9px;letter-spacing:.025em;}}
.sr-panel {{border:1px solid {LINE};border-radius:12px;background:linear-gradient(180deg,rgba(8,24,42,.96),rgba(5,15,28,.96));padding:14px;margin-bottom:10px;}}
.sr-panel.selected {{border-color:{CYAN};box-shadow:0 0 24px rgba(40,215,255,.12);}}
.sr-title {{font-family:'Space Grotesk';font-weight:700;font-size:14px;}}
.sr-body {{font-size:12px;line-height:1.55;color:#c6dce9;margin-top:6px;}}
.sr-small {{font:10px 'JetBrains Mono';color:{MUTED};line-height:1.5;}}
.sr-badge {{display:inline-block;border:1px solid {LINE};border-radius:18px;padding:3px 8px;margin:8px 4px 0 0;font:9px 'JetBrains Mono';color:{MUTED};}}
.badge-safe {{color:{TEAL};border-color:{TEAL};}} .badge-fast {{color:{CYAN};border-color:{CYAN};}} .badge-warn {{color:{AMBER};border-color:{AMBER};}} .badge-danger {{color:{RED};border-color:{RED};}} .badge-ai {{color:{PURPLE};border-color:{PURPLE};}}
.sr-alert {{border-left:4px solid {AMBER};background:rgba(255,180,74,.06);padding:11px 13px;margin:8px 0;border-radius:0 10px 10px 0;}}
.sr-critical {{border-left-color:{RED};background:rgba(255,80,104,.07);}}
.sr-good {{border-left-color:{TEAL};background:rgba(34,224,189,.06);}}
.sr-step {{border-left:2px solid {LINE};padding-left:11px;margin:7px 0;font-size:11.5px;color:#bdd5e4;}}
.sr-selected-row {{border:1px solid {CYAN};background:rgba(40,215,255,.05);border-radius:10px;padding:10px;}}
.stButton>button {{border:1px solid {CYAN};background:rgba(40,215,255,.035);color:{CYAN};font:10.5px 'JetBrains Mono';border-radius:8px;}}
.stButton>button:hover {{background:{CYAN};color:#00131d;}}
button[kind="primary"] {{background:linear-gradient(135deg,{CYAN},{TEAL})!important;color:#00131d!important;border:none!important;font-weight:700!important;}}
[data-testid="stMetric"] {{border:1px solid {LINE};border-radius:10px;background:rgba(5,17,31,.8);padding:8px 10px;}}
[data-testid="stMetricValue"] {{font-family:'Space Grotesk';font-size:19px;}}
[data-testid="stChatMessage"] {{border:1px solid {LINE};border-radius:12px;background:rgba(6,19,34,.72);}}
.sr-footer {{border-top:1px solid {LINE};padding:15px;text-align:center;color:{MUTED};font:9.5px 'JetBrains Mono';line-height:1.6;margin-top:22px;}}
.sr-weather{{border:1px solid #1e567b;border-radius:14px;padding:14px;background:linear-gradient(135deg,rgba(20,63,101,.88),rgba(5,18,34,.96));box-shadow:0 0 28px rgba(40,215,255,.08);}}
.sr-weather-main{{display:flex;align-items:center;justify-content:space-between;gap:12px;}}
.sr-weather-temp{{font-family:'Space Grotesk';font-size:44px;font-weight:700;line-height:1;}}
.sr-weather-icon{{font-size:42px;filter:drop-shadow(0 0 10px rgba(40,215,255,.4));}}
.sr-weather-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:12px;}}
.sr-weather-cell{{border:1px solid #17405f;border-radius:9px;padding:8px;background:rgba(3,12,23,.55);font:9px 'JetBrains Mono';color:#91b3c9;}}
.sr-weather-cell b{{display:block;color:#ecf8ff;font-size:12px;margin-top:4px;}}
.sr-tabline{{border:1px solid #17405f;border-radius:12px;padding:8px;background:rgba(5,17,31,.82);margin:6px 0 12px;}}
.sr-ai-strip{{border:1px solid #7f5bc9;border-radius:13px;padding:12px 14px;background:linear-gradient(100deg,rgba(86,47,141,.25),rgba(7,22,39,.95));box-shadow:0 0 25px rgba(189,113,255,.09);margin-bottom:10px;}}
.sr-ai-grid{{display:grid;grid-template-columns:1.4fr .7fr .7fr;gap:10px;align-items:center;}}
.sr-ai-label{{font:9px 'JetBrains Mono';color:#c9afff;text-transform:uppercase;letter-spacing:.08em;}}
.sr-ai-value{{font-family:'Space Grotesk';font-weight:700;font-size:15px;margin-top:3px;}}
.sr-resource-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0 12px;}}
.sr-resource-card{{border:1px solid #17405f;border-radius:10px;padding:10px;background:rgba(5,17,31,.82);}}
.sr-resource-card .n{{font-family:'Space Grotesk';font-weight:700;font-size:13px;}}
.sr-resource-card .s{{font:9px 'JetBrains Mono';color:#91b3c9;margin-top:5px;line-height:1.5;}}
.sr-receipt{{border:1px solid #22e0bd;border-radius:13px;padding:14px;background:linear-gradient(120deg,rgba(34,224,189,.12),rgba(4,18,31,.96));box-shadow:0 0 28px rgba(34,224,189,.1);margin:10px 0;}}
.sr-receipt-title{{font-family:'Space Grotesk';font-size:16px;font-weight:700;color:#63e58e;}}
.sr-receipt-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px;}}
.sr-receipt-item{{font:9px 'JetBrains Mono';color:#91b3c9;border-left:2px solid #22e0bd;padding-left:8px;}}
.sr-receipt-item b{{display:block;color:#ecf8ff;font-size:11px;margin-top:4px;}}
div[role="radiogroup"]{{gap:.25rem;flex-wrap:wrap;}}
div[role="radiogroup"] label{{background:rgba(5,17,31,.78);border:1px solid #17405f;border-radius:9px;padding:.34rem .7rem;}}
div[role="radiogroup"] label:has(input:checked){{border-color:#28d7ff;background:rgba(40,215,255,.12);box-shadow:0 0 14px rgba(40,215,255,.08);}}
.sr-incident-board{{border:1px solid #255f86;border-radius:15px;padding:14px;background:linear-gradient(120deg,rgba(11,38,64,.96),rgba(4,14,27,.98));box-shadow:0 0 32px rgba(40,215,255,.08);margin:7px 0 12px;}}
.sr-incident-card{{border:1px solid #17405f;border-radius:12px;padding:11px;background:rgba(4,17,31,.88);min-height:128px;}}
.sr-incident-card.active{{border-color:#ff5068;box-shadow:0 0 20px rgba(255,80,104,.10);}}
.sr-incident-status{{display:inline-block;border-radius:999px;padding:3px 8px;font:9px 'JetBrains Mono';text-transform:uppercase;border:1px solid #17405f;color:#91b3c9;margin-bottom:8px;}}
.sr-incident-status.active{{border-color:#ff5068;color:#ff8293;background:rgba(255,80,104,.08);}}
.sr-incident-status.containment{{border-color:#ffb44a;color:#ffd18c;background:rgba(255,180,74,.08);}}
.sr-incident-status.monitoring{{border-color:#22e0bd;color:#79f2d8;background:rgba(34,224,189,.08);}}
.sr-map-preview{{border:1px solid #28d7ff;border-radius:12px;padding:11px 13px;background:linear-gradient(100deg,rgba(40,215,255,.11),rgba(4,16,29,.96));margin:6px 0 10px;}}
.sr-decision-summary{{border:1px solid #7f5bc9;border-radius:12px;padding:10px 12px;background:rgba(70,43,112,.17);margin:8px 0 12px;}}
.sr-chip{{display:inline-block;padding:5px 9px;border-radius:999px;border:1px solid #28d7ff;background:rgba(40,215,255,.08);color:#c9f6ff;font:9px 'JetBrains Mono';margin:4px 5px 2px 0;}}
.sr-chip.population{{border-color:#3b82f6;background:rgba(59,130,246,.10);}}
.sr-chip.traffic{{border-color:#ffb44a;background:rgba(255,180,74,.10);}}
.sr-chip.environment{{border-color:#63e58e;background:rgba(99,229,142,.10);}}
.sr-plan-count{{font-family:'Space Grotesk';font-size:20px;font-weight:700;color:#c9afff;}}
.sr-present-shell{{background:linear-gradient(145deg,rgba(4,16,13,.99),rgba(2,9,8,.99));border:1px solid rgba(213,242,109,.28);border-radius:18px;padding:18px 20px 14px;box-shadow:0 0 48px rgba(213,242,109,.07);margin:2px 0 12px;}}
.sr-present-kicker{{font:9px 'JetBrains Mono';letter-spacing:.18em;text-transform:uppercase;color:#d5f26d;margin-bottom:8px;}}
.sr-present-title{{font-family:'Space Grotesk';font-size:clamp(26px,3.3vw,50px);font-weight:700;line-height:1.02;letter-spacing:-.035em;max-width:1150px;}}
.sr-present-sub{{font-size:14px;line-height:1.55;color:#a9b9af;max-width:900px;margin-top:10px;}}
.sr-present-quote{{border-left:3px solid #d5f26d;background:linear-gradient(90deg,rgba(213,242,109,.10),rgba(213,242,109,0));padding:13px 16px;margin:12px 0;color:#f4f9ef;font-family:'Space Grotesk';font-size:18px;font-weight:600;}}
.sr-present-card{{border:1px solid rgba(213,242,109,.22);border-radius:13px;padding:12px 14px;background:rgba(5,20,16,.92);min-height:92px;}}
.sr-present-card .eyebrow{{font:8px 'JetBrains Mono';color:#d5f26d;text-transform:uppercase;letter-spacing:.10em;}}
.sr-present-card .big{{font-family:'Space Grotesk';font-size:23px;font-weight:700;margin-top:5px;}}
.sr-present-card .copy{{font-size:11px;line-height:1.45;color:#9fb0a6;margin-top:5px;}}
.sr-risk-row{{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;border-bottom:1px solid rgba(213,242,109,.12);padding:10px 0;}}
.sr-risk-row:last-child{{border-bottom:none;}}
.sr-risk-icon{{width:30px;height:30px;border:1px solid rgba(213,242,109,.32);border-radius:9px;display:grid;place-items:center;color:#d5f26d;font-weight:700;}}
.sr-risk-name{{font-weight:700;font-size:12px;}}
.sr-risk-copy{{font-size:10px;color:#91a298;margin-top:2px;}}
.sr-risk-value{{font:9px 'JetBrains Mono';color:#ff8278;text-align:right;}}
.sr-route-table{{display:grid;grid-template-columns:1.25fr 1fr 1fr;border:1px solid rgba(213,242,109,.23);border-radius:13px;overflow:hidden;margin-top:10px;}}
.sr-route-table>div{{padding:9px 11px;border-bottom:1px solid rgba(213,242,109,.12);font-size:11px;}}
.sr-route-table>div:nth-last-child(-n+3){{border-bottom:none;}}
.sr-route-table .head{{font:8px 'JetBrains Mono';letter-spacing:.08em;text-transform:uppercase;color:#91a298;background:rgba(255,255,255,.02);}}
.sr-route-table .fast{{color:#ff9e76;}}
.sr-route-table .safe{{color:#d5f26d;font-weight:700;}}
.sr-agent-step{{border-left:1px solid rgba(213,242,109,.25);padding:0 0 13px 18px;margin-left:8px;position:relative;font-size:11px;color:#afbeb5;}}
.sr-agent-step:before{{content:'';position:absolute;left:-5px;top:1px;width:9px;height:9px;border-radius:50%;background:#07140f;border:1px solid #d5f26d;}}
.sr-agent-step b{{display:block;color:#f3f8f0;font-size:12px;margin-bottom:2px;}}
.sr-present-note{{font:9px 'JetBrains Mono';color:#71847a;margin-top:8px;}}
.sr-time-chip{{display:inline-block;border:1px solid rgba(213,242,109,.25);border-radius:999px;padding:5px 9px;color:#d5f26d;font:9px 'JetBrains Mono';margin:0 5px 5px 0;}}
.sr-human{{border:1px solid #d5f26d;border-radius:12px;background:rgba(213,242,109,.08);padding:13px 15px;color:#eef7dc;}}
@media(max-width:900px){{.sr-ai-grid,.sr-receipt-grid,.sr-weather-grid,.sr-resource-grid{{grid-template-columns:1fr 1fr;}}}}

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
    "CRITICAL": [255, 80, 104],
    "ELEVATED": [255, 180, 74],
    "MODERATE": [34, 224, 189],
}
STATUS_COLOR = {
    "Available": [34, 224, 189],
    "Requested": [255, 180, 74],
    "En route": [40, 215, 255],
    "On scene": [189, 113, 255],
    "Busy": [255, 80, 104],
}
AGENCY_COLOR = {
    "police": [59, 130, 246],
    "fire": [255, 80, 104],
    "ambulance": [34, 224, 189],
    "hazmat": [189, 113, 255],
    "environment": [99, 229, 142],
    "bus": [255, 180, 74],
    "sensor": [40, 215, 255],
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
    "police": "P",
    "fire": "F",
    "ambulance": "A",
    "hazmat": "H",
    "environment": "E",
    "bus": "B",
    "sensor": "S",
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
    {"id": "POI-H01", "name": "Pukou District Hospital", "lat": 32.1542, "lon": 118.7023, "type": "hospital", "base_pop": 920, "vulnerability": 2.7, "buffer_m": 600},
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

HISTORICAL_CASES = pd.DataFrame([
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
    for water in WATER_ZONES:
        for p in water["polygon"]:
            d = max(50.0, dist_m(lat, lon, p[1], p[0]))
            environment += 600 / (d / 100 + 1)
    if dist_m(lat, lon, active.lat, active.lon) < 900:
        exposure += 60
    return exposure / 40, environment / 25


def traffic_color(congestion: float) -> List[int]:
    if congestion < 0.40:
        return [34, 224, 189, 225]
    if congestion < 0.68:
        return [255, 180, 74, 235]
    return [255, 80, 104, 245]


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
    if not OSMNX_AVAILABLE:
        return None
    try:
        ox.settings.requests_timeout = 60
        graph = ox.graph.graph_from_point((32.160, 118.704), dist=7000, network_type="drive", simplify=True)
        graph = ox.routing.add_edge_speeds(graph, fallback=40)
        graph = ox.routing.add_edge_travel_times(graph)
        return graph
    except Exception:
        return None


def _geometry_polygon_rings(geometry: Any) -> List[List[List[float]]]:
    """Convert Shapely Polygon/MultiPolygon geometry into PyDeck coordinate rings."""
    if geometry is None or getattr(geometry, "is_empty", True):
        return []
    geometry_type = getattr(geometry, "geom_type", "")
    if geometry_type == "Polygon":
        return [[[float(x), float(y)] for x, y, *_ in geometry.exterior.coords]]
    if geometry_type == "MultiPolygon":
        rings: List[List[List[float]]] = []
        for polygon in geometry.geoms:
            if polygon is not None and not polygon.is_empty:
                rings.append([[float(x), float(y)] for x, y, *_ in polygon.exterior.coords])
        return rings
    return []


def _clean_osm_tag(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return "" if text in {"nan", "none", "<na>"} else text


@st.cache_data(ttl=604800, show_spinner=False)
def load_osm_context_features(
    center_lat: float = 32.1628,
    center_lon: float = 118.6906,
    distance_m: int = 2300,
) -> Dict[str, Any]:
    """Load a bounded OSM context snapshot and return lightweight serializable polygons."""
    if not OSMNX_AVAILABLE:
        return {
            "buildings": [],
            "landuse": [],
            "status": "OSMnx is not installed; contextual polygons are unavailable.",
            "source": "OpenStreetMap",
        }
    tags = {
        "building": True,
        "landuse": True,
        "leisure": ["park", "garden", "sports_centre", "pitch"],
        "natural": ["water", "wood", "wetland", "grassland"],
    }
    try:
        if hasattr(ox, "features") and hasattr(ox.features, "features_from_point"):
            features = ox.features.features_from_point(
                (center_lat, center_lon),
                tags=tags,
                dist=distance_m,
            )
        else:  # OSMnx 1.x compatibility
            features = ox.geometries_from_point(
                (center_lat, center_lon),
                tags=tags,
                dist=distance_m,
            )
    except Exception as exc:
        return {
            "buildings": [],
            "landuse": [],
            "status": f"OSM context request unavailable: {type(exc).__name__}.",
            "source": "OpenStreetMap",
        }

    landuse_palette = {
        "residential": [104, 137, 98, 42],
        "industrial": [183, 135, 77, 52],
        "commercial": [203, 99, 91, 48],
        "retail": [203, 99, 91, 48],
        "institutional": [79, 137, 174, 46],
        "education": [79, 137, 174, 46],
        "recreation_ground": [84, 162, 100, 46],
        "park": [84, 162, 100, 46],
        "garden": [84, 162, 100, 46],
        "forest": [59, 121, 74, 46],
        "wood": [59, 121, 74, 46],
        "grass": [105, 153, 90, 38],
        "grassland": [105, 153, 90, 38],
        "farmland": [142, 154, 87, 36],
        "railway": [104, 102, 121, 42],
        "water": [65, 142, 171, 48],
        "wetland": [65, 142, 171, 44],
    }
    buildings: List[Dict[str, Any]] = []
    landuse: List[Dict[str, Any]] = []

    for _, row in features.iterrows():
        rings = _geometry_polygon_rings(row.geometry)
        if not rings:
            continue
        building_tag = _clean_osm_tag(row.get("building"))
        landuse_tag = _clean_osm_tag(row.get("landuse"))
        leisure_tag = _clean_osm_tag(row.get("leisure"))
        natural_tag = _clean_osm_tag(row.get("natural"))
        name = _clean_osm_tag(row.get("name"))
        if building_tag:
            for ring in rings:
                buildings.append({
                    "polygon": ring,
                    "fill_color": [167, 190, 174, 9],
                    "line_color": [171, 204, 181, 92],
                    "title": name.title() if name else "OSM building footprint",
                    "details": f"Building tag: {building_tag}",
                })
        category = landuse_tag or leisure_tag or natural_tag
        if category:
            color = landuse_palette.get(category, [126, 145, 115, 30])
            for ring in rings:
                landuse.append({
                    "polygon": ring,
                    "fill_color": color,
                    "line_color": color[:3] + [92],
                    "category": category,
                    "title": name.title() if name else category.replace("_", " ").title(),
                    "details": f"OSM context category: {category}",
                })

    # A bounded visual sample keeps the single-file Streamlit prototype responsive.
    buildings = buildings[:1600]
    landuse = landuse[:320]
    return {
        "buildings": buildings,
        "landuse": landuse,
        "status": f"Loaded {len(landuse):,} land-use polygons and {len(buildings):,} building footprints.",
        "source": "OpenStreetMap contributors via OSMnx / Overpass",
    }


def osm_context_layers() -> List[pdk.Layer]:
    context = load_osm_context_features()
    layers: List[pdk.Layer] = []
    if st.session_state.get("map_layer_landuse", True) and context["landuse"]:
        layers.append(
            pdk.Layer(
                "PolygonLayer",
                id="osm-landuse-context",
                data=context["landuse"],
                get_polygon="polygon",
                get_fill_color="fill_color",
                get_line_color="line_color",
                stroked=True,
                filled=True,
                extruded=False,
                line_width_min_pixels=0.45,
                pickable=True,
            )
        )
    if st.session_state.get("map_layer_buildings", True) and context["buildings"]:
        layers.append(
            pdk.Layer(
                "PolygonLayer",
                id="osm-building-footprints",
                data=context["buildings"],
                get_polygon="polygon",
                get_fill_color="fill_color",
                get_line_color="line_color",
                stroked=True,
                filled=True,
                extruded=False,
                line_width_min_pixels=0.55,
                pickable=True,
            )
        )
    return layers


# =============================================================================
# SIMULATION, TRAFFIC, ROUTING AND DECISION ENGINE
# =============================================================================
def build_live_pois(hour: int, weekday: bool) -> List[Dict[str, Any]]:
    result = []
    colors = {
        "school": [255, 180, 74],
        "hospital": [255, 80, 104],
        "residential": [59, 130, 246],
        "eldercare": [189, 113, 255],
        "park": [99, 229, 142],
        "fuel": [255, 80, 104],
        "commercial": [40, 215, 255],
    }
    glyphs = {"school": "S", "hospital": "+", "residential": "R", "eldercare": "E", "park": "P", "fuel": "G", "commercial": "C"}
    for poi in POIS:
        pop = current_population(poi, hour, weekday)
        result.append({
            **poi,
            "population_now": pop,
            "color": colors.get(poi["type"], [40, 215, 255]) + [235],
            "buffer_color": colors.get(poi["type"], [40, 215, 255]) + [22],
            "buffer_line_color": colors.get(poi["type"], [40, 215, 255]) + [130],
            "glyph": glyphs.get(poi["type"], "•"),
            "title": poi["name"],
            "details": f"Type: {poi['type']}<br/>Estimated people now: {pop:,}<br/>Vulnerability: {poi['vulnerability']:.1f}",
        })
    return result


def build_demo_traffic(tick: int, traffic_index: float, rain_mm_h: float, road_wetness: float, active: Incident) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for idx, segment in enumerate(BASE_TRAFFIC_SEGMENTS):
        wave = math.sin((tick + idx * 2.2) / 3.0) * 0.08
        incident_effect = 0.26 if segment["id"] == "T-02" and active.id == "NJ-HZ-260717-01" else 0.0
        weather_effect = min(0.18, rain_mm_h / 250 + road_wetness * 0.08)
        global_effect = traffic_index / 10 * 0.22
        congestion = clamp(segment["base_load"] + wave + incident_effect + weather_effect + global_effect - 0.11, 0.05, 0.98)
        speed = max(7.0, segment["free_speed"] * (1 - congestion * 0.78))
        output.append({
            **segment,
            "congestion": congestion,
            "speed": round(speed, 0),
            "color": traffic_color(congestion),
            "status_text": status_text(congestion),
            "source": "Simulated live",
            "title": segment["name"],
            "details": f"{status_text(congestion)}<br/>Average speed: {speed:.0f} km/h<br/>Source: simulated live",
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


def osm_nodes_to_path(graph: Any, nodes: List[Any]) -> List[List[float]]:
    """Convert a route to detailed edge geometry so lines follow road curves."""
    if not nodes:
        return []
    try:
        edges = ox.routing.route_to_gdf(graph, nodes, weight="travel_time")
        path: List[List[float]] = []
        for geometry in edges.geometry:
            coordinates = [[float(x), float(y)] for x, y in geometry.coords]
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
    if graph is None or ox is None:
        return None
    try:
        origin_node = ox.distance.nearest_nodes(graph, origin[1], origin[0])
        destination_node = ox.distance.nearest_nodes(graph, destination[1], destination[0])
        nodes = ox.routing.shortest_path(graph, origin_node, destination_node, weight="travel_time")
        return osm_nodes_to_path(graph, list(nodes)) if nodes else None
    except Exception:
        return None


def build_route_options(resource: Resource, active: Incident, traffic: List[Dict[str, Any]], backend: str, amap_key: str) -> Dict[str, RouteResult]:
    origin = (resource.lat, resource.lon)
    destination = (active.lat, active.lon)

    # AMap is used for the fastest path when available. The two alternative
    # objectives still use the real OSM street graph instead of fake offsets.
    if backend.startswith("AMap") and amap_key:
        amap = fetch_amap_driving_route(amap_key, origin, destination)
        fastest_osm = osm_route(resource, active, "fastest", traffic)
        safest = osm_route(resource, active, "safest", traffic)
        low_traffic = osm_route(resource, active, "low_traffic", traffic)
        if amap:
            fastest = route_result_from_path(
                "fastest", "Fastest AMap route", amap["path"], active, traffic,
                "AMap live route", "AMap turn-by-turn route using current navigation cost.", 1.02,
            )
            fastest.distance_km = amap["distance_km"] or fastest.distance_km
            fastest.eta_min = amap["eta_min"] or fastest.eta_min
        else:
            fastest = fastest_osm
        if fastest and safest and low_traffic:
            options = {"fastest": fastest, "safest": safest, "low_traffic": low_traffic}
            recommended = min(options.values(), key=lambda route: route.composite_score)
            options["recommended"] = RouteResult(**{**asdict(recommended), "id": "recommended", "label": "AI recommended street route"})
            return options

    fastest = osm_route(resource, active, "fastest", traffic)
    safest = osm_route(resource, active, "safest", traffic)
    low_traffic = osm_route(resource, active, "low_traffic", traffic)
    if fastest and safest and low_traffic:
        options = {"fastest": fastest, "safest": safest, "low_traffic": low_traffic}
        recommended = min(options.values(), key=lambda route: route.composite_score)
        options["recommended"] = RouteResult(**{**asdict(recommended), "id": "recommended", "label": "AI recommended street route"})
        return options

    # Explicitly labeled offline fallback. It is kept only so the demonstration
    # remains operable when Overpass/OSM is temporarily unreachable.
    fastest = route_result_from_path(
        "fastest", "Offline approximate route", offset_curve(origin, destination, 0.0018, 26), active, traffic,
        "Offline approximation", "OpenStreetMap routing is unavailable. Reconnect and select OSMnx to obtain street-following routes.", 1.0,
    )
    safest = route_result_from_path(
        "safest", "Offline low-exposure approximation", offset_curve(origin, destination, 0.0065, 28), active, traffic,
        "Offline approximation", "Temporary non-operational fallback. It must not be used for real dispatch.", 0.92,
    )
    low_traffic = route_result_from_path(
        "low_traffic", "Offline low-congestion approximation", offset_curve(origin, destination, -0.0055, 28), active, traffic,
        "Offline approximation", "Temporary non-operational fallback. It must not be used for real dispatch.", 0.96,
    )
    options = {route.id: route for route in [fastest, safest, low_traffic]}
    recommended = min(options.values(), key=lambda route: route.composite_score)
    options["recommended"] = RouteResult(**{**asdict(recommended), "id": "recommended", "label": "AI fallback recommendation"})
    return options


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
        "dispatch_status": {r.id: r.status for r in RESOURCES},
        "dispatch_start_tick": {},
        "road_closures": [],
        "demo_tick": 0,
        "demo_stage": 0,
        "event_log": [],
        "agent_messages": [{"role": "assistant", "content": "SkyRoute AI online. I am monitoring the selected incident, weather, traffic, routes, exposed population and available resources."}],
        "plan_confirmed": False,
        "dispatch_receipts": [],
        "last_dispatch_receipt": None,
        "presentation_mode": False,
        "presentation_step": 0,
        "presentation_hour": 14,
        "presentation_disruption": False,
        "map_layer_landuse": True,
        "map_layer_buildings": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

if st.session_state.presentation_mode:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {display:none !important;}
        .block-container {padding-top:.55rem;max-width:1780px;}
        .stApp {background:radial-gradient(circle at 80% 0%,#172514 0%,#04100d 33%,#010706 100%);}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        get_line_color=[235, 248, 255, 220],
        line_width_min_pixels=1.2,
        pickable=pickable,
        auto_highlight=True,
    )


def text_layer(layer_id: str, data: List[Dict[str, Any]], size: int = 14) -> pdk.Layer:
    return pdk.Layer(
        "TextLayer",
        id=layer_id,
        data=data,
        get_position="[lon, lat]",
        get_text="glyph",
        get_size=size,
        get_color=[255, 255, 255, 255],
        get_alignment_baseline="center",
        pickable=False,
    )


def point_layers(layer_prefix: str, data: List[Dict[str, Any]], radius: Any = 65, size: int = 13) -> List[pdk.Layer]:
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
        "html": "<b>{title}</b><br/>{details}",
        "style": {
            "backgroundColor": "#061321",
            "color": "#ecf8ff",
            "border": "1px solid #28d7ff",
            "borderRadius": "8px",
            "fontSize": "12px",
        },
    }
    north_span = max(0.010, 0.036 * (2 ** (12.0 - zoom)))
    north_layer = pdk.Layer(
        "TextLayer",
        id="map-north-indicator",
        data=[{
            "lon": longitude - north_span * 0.72,
            "lat": latitude + north_span * 0.48,
            "label": "N ↑",
            "angle": -bearing,
        }],
        get_position="[lon, lat]",
        get_text="label",
        get_size=14,
        get_color=[235, 248, 223, 235],
        get_angle="angle",
        get_alignment_baseline="center",
        get_text_anchor="middle",
        billboard=True,
        pickable=False,
    )
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
        layers=osm_context_layers() + list(layers) + [north_layer],
        tooltip=tooltip,
    )


def render_map(
    deck: pdk.Deck,
    key: str,
    height: int = 590,
    selectable: bool = False,
) -> Any:
    try:
        if selectable:
            event = st.pydeck_chart(
                deck,
                use_container_width=True,
                height=height,
                key=key,
                on_select="rerun",
                selection_mode="single-object",
            )
        else:
            st.pydeck_chart(deck, use_container_width=True, height=height, key=key)
            event = None
        map_space, map_info = st.columns([8.7, 1.3])
        with map_info:
            with st.popover("ⓘ Map data"):
                context = load_osm_context_features()
                st.markdown("**Map and scenario provenance**")
                st.caption(
                    "Basemap: CARTO / OpenStreetMap contributors. Operational points, "
                    "population presence, weather, plume geometry, traffic conditions "
                    "and route metrics are simulated for this academic demonstration."
                )
                st.caption(
                    "The scenario is not a live command-center feed. Production use "
                    "requires validated official sources, licenses and human authority."
                )
                st.markdown("**Context polygons**")
                st.caption(context["status"])
                st.caption(
                    "Land-use and building geometries are contextual OSM features. "
                    "Building footprints are flat visual boundaries and do not enter route or risk calculations."
                )
        return event
    except Exception as exc:
        st.error(f"The map could not be rendered: {exc}")
        st.caption("Try disabling the CARTO basemap in the sidebar. The operational overlays will still render.")
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


# =============================================================================
# GLOBAL CONTROLS AND LIVE STATE
# =============================================================================
active = active_incident()
now = datetime.now()

st.sidebar.markdown("## 🛰️ SkyRoute v10")
st.sidebar.caption("SkyTech Layer-2 emergency decision agent")

# Keep the widget state separate from programmatic navigation. The callback
# copies a real user click into nav_page before the script reruns, while the
# pre-widget sync handles map/button navigation into another workspace.
def sync_navigation_from_widget() -> None:
    st.session_state.nav_page = st.session_state.nav_widget


if st.session_state.get("nav_widget") != st.session_state.nav_page:
    st.session_state.nav_widget = st.session_state.nav_page
st.sidebar.radio(
    "Operational workspace",
    NAVIGATION,
    key="nav_widget",
    on_change=sync_navigation_from_widget,
)
page = st.session_state.nav_page

incident_index = next((idx for idx, inc in enumerate(INCIDENTS) if inc.id == active.id), 0)
selected_incident_idx = st.sidebar.selectbox(
    "Selected incident",
    range(len(INCIDENTS)),
    index=incident_index,
    format_func=lambda idx: f"{INCIDENTS[idx].id} · {INCIDENTS[idx].substance}",
)
if INCIDENTS[selected_incident_idx].id != st.session_state.active_incident_id:
    st.session_state.active_incident_id = INCIDENTS[selected_incident_idx].id
    st.session_state.plan_confirmed = False
    st.session_state.nav_page = "Incident Command"
    st.session_state.incident_tab = "Overview"
    log_event(f"Incident selected: {INCIDENTS[selected_incident_idx].id}", "incident")
    st.rerun()
active = active_incident()

st.sidebar.markdown("### Data and routing")
data_mode = st.sidebar.selectbox("Traffic source", ["Simulated live", "AMap live if configured"])
routing_backend = st.sidebar.selectbox(
    "Routing backend",
    ["OSMnx real streets", "AMap live route", "Offline approximation (only if network unavailable)"],
    help="OSMnx is the default because it follows actual streets. The first request can take longer while the road graph is downloaded.",
)
use_basemap = st.sidebar.toggle("CARTO dark basemap", value=True, help="Disable this if the background map is black or blocked; overlays remain visible.")
st.sidebar.markdown("#### Context layers")
st.sidebar.toggle(
    "Land use · OpenStreetMap",
    key="map_layer_landuse",
    help="Semi-transparent OSM land-use, leisure and selected natural-area polygons.",
)
st.sidebar.toggle(
    "Building footprints · OpenStreetMap",
    key="map_layer_buildings",
    help="Flat building outlines only. They do not affect routing or risk scores.",
)

st.sidebar.markdown("### Fact-axis scenario")
wind_speed_kmh = st.sidebar.slider("Wind speed (km/h)", 2, 45, 16)
wind_direction = st.sidebar.slider("Wind direction (degrees)", 0, 359, 115)
rain_mm_h = st.sidebar.slider("Rainfall (mm/h)", 0, 80, 18)
temperature_c = st.sidebar.slider("Temperature (°C)", 5, 45, 34)
road_wetness = st.sidebar.slider("Road wetness", 0.0, 1.0, 0.65, 0.05)
traffic_index = st.sidebar.slider("Traffic index", 0.0, 10.0, 7.4, 0.1)
hazmat_flow = st.sidebar.slider("HazMat trucks per hour", 0, 80, 28)

st.sidebar.markdown("### Decision assumptions")
evacuation_capacity_ppm = st.sidebar.slider("Evacuation capacity (people/min)", 20, 300, 95)
setup_delay_min = st.sidebar.slider("Mobilisation delay (min)", 1, 30, 7)
shelter_quality = st.sidebar.slider("Shelter quality", 0.2, 0.95, 0.68, 0.01)

amap_key = get_amap_key()
if data_mode.startswith("AMap") or routing_backend.startswith("AMap"):
    if amap_key:
        st.sidebar.success("AMap key detected")
    else:
        st.sidebar.warning("AMap key not found; automatic fallback will be used")
if routing_backend.startswith("OSMnx") and not OSMNX_AVAILABLE:
    st.sidebar.warning("OSMnx is not installed; automatic fallback will be used")

hour = now.hour
weekday = now.weekday() < 5
pois_live = build_live_pois(hour, weekday)
traffic_segments, traffic_source_label = combined_traffic_source(
    data_mode,
    amap_key,
    st.session_state.demo_tick,
    traffic_index,
    rain_mm_h,
    road_wetness,
    active,
)
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
if not st.session_state.presentation_mode:
    top_shell, present_action = st.columns([8.7, 1.3])
    with top_shell:
        st.markdown(
            f"""
    <div class="sr-top">
     <div class="sr-brand"><div class="sr-logo">SR</div><div><div class="sr-name">SkyRoute / 天途 v10</div><div class="sr-sub">Interactive prevention, routing and incident command · Nanjing pilot</div></div></div>
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
    with present_action:
        if st.button("▶  Presentation", key="enter_presentation", use_container_width=True):
            st.session_state.presentation_mode = True
            st.session_state.presentation_step = 0
            st.session_state.presentation_disruption = False
            st.rerun()

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
            "color": STATUS_COLOR.get(status, [40, 215, 255]) + [230],
            "glyph": AGENCY_GLYPH.get(resource.kind, "U"),
            "title": resource.name,
            "details": f"{AGENCY_LABEL.get(resource.kind, resource.kind)}<br/>Status: {status}<br/>Capacity: {resource.capacity}",
        })
    return output


def traffic_path_data() -> List[Dict[str, Any]]:
    output = []
    for segment in traffic_segments:
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
    if not resource_id:
        candidates = [r for r in RESOURCES if r.kind == kind and st.session_state.dispatch_status.get(r.id, r.status) != "Busy"]
        if not candidates:
            return None
        resource = min(candidates, key=lambda r: dist_m(r.lat, r.lon, active.lat, active.lon))
        st.session_state.selected_resource_ids[kind] = resource.id
    else:
        resource = next((r for r in RESOURCES if r.id == resource_id), None)
        if resource is None:
            return None
    options = build_route_options(resource, active, traffic_segments, routing_backend, amap_key)
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
            "lon": position[0],
            "lat": position[1],
            "color": AGENCY_COLOR[kind] + [245],
            "glyph": AGENCY_GLYPH[kind],
            "title": f"{AGENCY_LABEL[kind]} · {resource.name}",
            "details": f"Status: {status}<br/>Units selected: {quantity}<br/>Route progress: {progress:.0%}",
        })
    return output


def route_layers_for_plan(alpha_other: int = 170) -> List[pdk.Layer]:
    paths = []
    for kind, quantity in st.session_state.resource_quantities.items():
        if quantity <= 0:
            continue
        route = selected_route_for_kind(kind)
        if route is None:
            continue
        paths.append({
            "path": route.path,
            "color": AGENCY_COLOR[kind] + [alpha_other],
            "width": 7,
            "title": f"{AGENCY_LABEL[kind]} · {route.label}",
            "details": f"ETA {route.eta_min} min · {route.distance_km} km<br/>Backend: {route.backend}",
        })
    return [path_layer("plan-resource-routes", paths, 7)] if paths else []


# =============================================================================
# VISUAL DASHBOARDS AND OPERATIONAL FEEDBACK
# =============================================================================
def transparent_plot_layout(fig: go.Figure, height: int = 270) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=36, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter"),
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
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=temperatures, mode="lines+markers", name="Temperature °C", line=dict(width=3)))
    fig.add_trace(go.Bar(x=hours, y=precipitation, name="Precipitation %", opacity=.42, yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="°C", showgrid=False),
        yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100], showgrid=False),
        title="Next 6 hours · operational forecast",
    )
    st.plotly_chart(transparent_plot_layout(fig, 235), use_container_width=True, config={"displayModeBar": False})


def render_prevention_factor_chart() -> None:
    labels = [name.replace("_", " ").title() for name in prevention_factors]
    values = [round(value * 100) for value in prevention_factors.values()]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", text=[f"{v}%" for v in values], textposition="outside"))
    fig.update_layout(title="AI predictive risk contribution", xaxis=dict(range=[0, 110], title="Contribution", showgrid=False), yaxis=dict(autorange="reversed"))
    st.plotly_chart(transparent_plot_layout(fig, 280), use_container_width=True, config={"displayModeBar": False})


def render_route_comparison(options: Dict[str, RouteResult], selected_key: str) -> None:
    routes = [(key, route) for key, route in options.items() if key != "recommended"]
    categories = ["ETA", "Exposure", "Environment", "Congestion", "Responder risk"]
    fig = go.Figure()
    maxima = [max([route.eta_min for _, route in routes] + [1]), max([route.exposure_score for _, route in routes] + [1]), max([route.environment_score for _, route in routes] + [1]), 10, max([route.responder_risk for _, route in routes] + [1])]
    for key, route in routes:
        raw = [route.eta_min, route.exposure_score, route.environment_score, route.congestion_score, route.responder_risk]
        # Lower is better, so invert for an intuitive larger-is-better radar.
        scores = [round(100 * (1 - min(value / maximum, 1)), 1) for value, maximum in zip(raw, maxima)]
        fig.add_trace(go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]], fill="toself", name=route.label, opacity=0.82 if key == selected_key else 0.35))
    fig.update_layout(title="Route performance · larger area means better", polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)), showlegend=True)
    st.plotly_chart(transparent_plot_layout(fig, 330), use_container_width=True, config={"displayModeBar": False})


def resource_status_counts() -> Dict[str, int]:
    counts = {"Available": 0, "Busy": 0, "En route": 0, "On scene": 0}
    for resource in RESOURCES:
        status = st.session_state.dispatch_status.get(resource.id, resource.status)
        counts[status] = counts.get(status, 0) + resource.units
    return counts


def render_resource_availability() -> None:
    counts = resource_status_counts()
    chart_col, cards_col = st.columns([.72, 1.28])
    with chart_col:
        fig = go.Figure(go.Pie(labels=list(counts), values=list(counts.values()), hole=.66, textinfo="label+value"))
        fig.update_layout(title="Fleet status", showlegend=False)
        st.plotly_chart(transparent_plot_layout(fig, 245), use_container_width=True, config={"displayModeBar": False})
    with cards_col:
        cards = []
        for kind, label in AGENCY_LABEL.items():
            candidates = [resource for resource in RESOURCES if resource.kind == kind]
            available = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) == "Available")
            busy = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) == "Busy")
            moving = sum(resource.units for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) in {"En route", "On scene"})
            cards.append(f'<div class="sr-resource-card"><div class="n">{AGENCY_GLYPH.get(kind,"U")} · {label}</div><div class="s">Available: <b>{available}</b><br/>Busy: <b>{busy}</b><br/>Deployed: <b>{moving}</b></div></div>')
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
        if resource and route:
            status = st.session_state.dispatch_status.get(resource.id, resource.status)
            st.markdown(
                f'<div class="sr-panel"><div class="sr-title">{AGENCY_GLYPH[kind]} · {AGENCY_LABEL[kind]} · {quantity} unit(s)</div><div class="sr-body"><b>Origin:</b> {resource.name}<br/><b>Status:</b> {status}<br/><b>Route:</b> {route.label}<br/><b>ETA:</b> {route.eta_min} min · {route.distance_km} km<br/><b>Backend:</b> {route.backend}</div></div>',
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
    if street_path and len(street_path) >= 2:
        return street_path
    return offset_curve((poi["lat"], poi["lon"]), (shelter["lat"], shelter["lon"]), curve, 18)


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
                layers.append(polygon_layer(f"{layer_key}-shelter", zones, [59, 130, 246, 45 if chosen else 24], [59, 130, 246, strength]))

        if option_id in {"POP-PHASE", "POP-HYBRID", "POP-ASSIST"}:
            routes = []
            selected_pois = exposed[:4]
            if option_id == "POP-ASSIST":
                selected_pois = [poi for poi in exposed if poi.get("type") in {"eldercare", "hospital"}] or exposed[:2]
            for idx, poi in enumerate(selected_pois):
                shelter = min(SHELTERS, key=lambda item: dist_m(poi["lat"], poi["lon"], item["lat"], item["lon"]))
                routes.append({
                    "path": evacuation_path(poi, shelter, 0.0014 * (idx - 1)),
                    "color": [34, 224, 189, strength],
                    "width": 8 if chosen else 5,
                    "title": f"{label} · Evacuation route · {poi['name']}",
                    "details": f"{record.get('title', option_id)}<br/>Destination: {shelter['name']}",
                })
            if routes:
                layers.append(path_layer(f"{layer_key}-evacuation", routes, 6))

        if option_id == "TR-CLOSE":
            layers.append(path_layer(f"{layer_key}-closure", [{
                "path": BASE_TRAFFIC_SEGMENTS[1]["path"], "color": [255, 255, 255, strength], "width": 16 if chosen else 11,
                "title": f"{label} · Road closure", "details": record.get("title", option_id),
            }], 14))
        elif option_id == "TR-CORRIDOR":
            route = selected_route_for_kind("fire")
            if route:
                layers.append(path_layer(f"{layer_key}-corridor", [{
                    "path": route.path, "color": [40, 215, 255, strength], "width": 13 if chosen else 8,
                    "title": f"{label} · Emergency green corridor", "details": f"Fire ETA {route.eta_min} min",
                }], 10))
        elif option_id == "TR-HAZMAT":
            layers.append(path_layer(f"{layer_key}-old", [{
                "path": HAZMAT_CORRIDORS[1]["path"], "color": [255, 80, 104, 150], "width": 6,
                "title": "Restricted HazMat route", "details": record.get("title", option_id),
            }], 6))
            layers.append(path_layer(f"{layer_key}-new", [{
                "path": HAZMAT_CORRIDORS[2]["path"], "color": [34, 224, 189, strength], "width": 11 if chosen else 8,
                "title": f"{label} · HazMat bypass", "details": record.get("title", option_id),
            }], 9))
        elif option_id == "TR-EVAC":
            shelter = SHELTERS[0]
            bus = next(resource for resource in RESOURCES if resource.kind == "bus")
            street_path = real_street_path_between((bus.lat, bus.lon), (shelter["lat"], shelter["lon"]))
            bus_path = street_path or offset_curve((bus.lat, bus.lon), (shelter["lat"], shelter["lon"]), -0.003, 18)
            layers.append(path_layer(f"{layer_key}-bus", [{
                "path": bus_path, "color": [255, 180, 74, strength], "width": 12 if chosen else 8,
                "title": f"{label} · Evacuation bus priority", "details": f"Destination: {shelter['name']}",
            }], 10))

        if option_id == "ENV-DRAIN":
            barriers = [{
                "polygon": make_circle_polygon(drain["lat"], drain["lon"], 110),
                "title": f"{label} · Drain barrier · {drain['name']}", "details": record.get("title", option_id),
            } for drain in DRAINS[:2]]
            layers.append(polygon_layer(f"{layer_key}-drains", barriers, [255, 180, 74, 55 if chosen else 28], [255, 180, 74, strength]))
        elif option_id == "ENV-SENSOR":
            proposals = [
                {"lat": active.lat + 0.010, "lon": active.lon + 0.008, "name": "Downwind mobile air sensor"},
                {"lat": 32.1681, "lon": 118.6822, "name": "School verification sensor"},
                {"lat": 32.1555, "lon": 118.7165, "name": "Retention inlet water sensor"},
            ]
            layers += point_layers(f"{layer_key}-sensors", [{
                **point, "color": [189, 113, 255, strength], "glyph": "S",
                "title": f"{label} · {point['name']}", "details": record.get("title", option_id),
            } for point in proposals], 76 if chosen else 62, 13)
        elif option_id == "ENV-BOOM":
            layers.append(path_layer(f"{layer_key}-boom", [{
                "path": [[118.6908, 32.1620], [118.6960, 32.1586], [118.7020, 32.1554]],
                "color": [255, 180, 74, strength], "width": 12 if chosen else 8,
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

    weather_col, risk_col = st.columns([1.15, 1])
    with weather_col:
        render_weather_dashboard()
    with risk_col:
        st.markdown('<div class="sr-panel"><div class="sr-title">SkyRoute AI · city risk monitor</div><div class="sr-body">The agent continuously combines weather, road wetness, traffic, ordinary crashes and HazMat flow to identify preventable escalation.</div></div>', unsafe_allow_html=True)
        render_prevention_factor_chart()

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
        layers: List[pdk.Layer] = [path_layer("city-traffic", traffic_path_data(), 8)]
        corridor_data = []
        for corridor in HAZMAT_CORRIDORS:
            corridor_data.append({
                **corridor,
                "color": ([40, 215, 255, 110] if corridor["risk"] == "Low" else [255, 180, 74, 130] if corridor["risk"] == "Medium" else [255, 80, 104, 150]),
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
                "color": [255, 180, 74, 235], "glyph": "T",
                "title": f"HazMat truck {truck['id']}",
                "details": f"Cargo: {truck['substance']}<br/>Speed: {truck['speed']} km/h<br/>Corridor: {truck['route']}",
            })
        layers += point_layers("hazmat-trucks", truck_data, 75, 12)
        layers += point_layers("ordinary-accidents", [{
            **acc, "color": [255, 180, 74, 230] if acc["severity"] == "minor" else [255, 80, 104, 235],
            "glyph": "X", "title": acc["title"], "details": f"{acc['road']}<br/>Severity: {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 60, 11)
        layers += point_layers("incidents", incident_map_data(), 145, 16)

        center_lat, center_lon, map_zoom = 32.160, 118.704, 11.35
        if selected_alert:
            proposed_path = preventive_alternative_path(selected_alert)
            layers.append(path_layer("selected-preventive-risk", [{
                "path": selected_alert.path, "color": [255, 80, 104, 235], "width": 17,
                "title": f"Current risk · {selected_alert.title}", "details": selected_alert.reason,
            }], 17))
            layers.append(path_layer("selected-preventive-highlight", [{
                "path": selected_alert.path, "color": [255, 255, 255, 220], "width": 7,
                "title": "Affected segment", "details": selected_alert.recommended_action,
            }], 7))
            if proposed_path:
                layers.append(path_layer("selected-preventive-alternative", [{
                    "path": proposed_path, "color": [40, 215, 255, 245], "width": 12,
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


# =============================================================================
# PAGE 2 — INCIDENT OVERVIEW
# =============================================================================
def page_incident_overview() -> None:
    st.markdown('<div class="sr-h2">Incident understanding and operational picture</div>', unsafe_allow_html=True)
    map_col, info_col = st.columns([1.58, 1])

    with map_col:
        layers: List[pdk.Layer] = []
        water_data = [{
            **zone,
            "title": zone["name"],
            "details": "Sensitive water or ecological receptor",
        } for zone in WATER_ZONES]
        layers.append(polygon_layer("incident-water", water_data, [25, 116, 170, 65], [40, 215, 255, 195]))
        layers.append(path_layer("incident-traffic", traffic_path_data(), 8))

        plume_data = [{
            "polygon": incident_state["plume_polygon"],
            "title": "Downwind protective-action zone",
            "details": f"Length {incident_state['protective_distance']/1000:.1f} km<br/>Wind {wind_label(wind_direction)} {wind_speed_kmh} km/h",
        }]
        layers.append(polygon_layer("incident-plume", plume_data, [255, 80, 104, 68], [255, 80, 104, 235]))
        isolation_data = [{
            "polygon": make_circle_polygon(active.lat, active.lon, incident_state["isolation_distance"]),
            "title": "Initial isolation zone",
            "details": f"Radius {incident_state['isolation_distance']} m",
        }]
        layers.append(polygon_layer("incident-isolation", isolation_data, [255, 180, 74, 35], [255, 180, 74, 240]))

        layers.append(pdk.Layer(
            "ScatterplotLayer",
            id="poi-buffers",
            data=pois_live,
            get_position="[lon, lat]",
            get_radius="buffer_m",
            get_fill_color="buffer_color",
            get_line_color="buffer_line_color",
            stroked=True,
            line_width_min_pixels=1,
            pickable=True,
        ))
        layers += point_layers("incident-pois", pois_live, 60, 12)
        layers += point_layers("incident-resources", resource_map_data(), 54, 11)
        layers += point_layers("incident-marker", [{
            "id": active.id,
            "lon": active.lon,
            "lat": active.lat,
            "color": THREAT_COLOR[active.threat] + [250],
            "glyph": "!",
            "title": f"{active.id} · {active.substance}",
            "details": f"Leak estimate: {incident_state['dynamic_leak']:.0f} kg/min<br/>{active.description}",
        }], 95, 18)

        deck = make_deck(layers, active.lat, active.lon, 13.05, 42, -12, use_basemap)
        render_map(deck, "incident-overview-map", 650)

    with info_col:
        st.markdown(f'<div class="sr-panel"><div class="sr-title">{active.id} · {active.substance}</div><div class="sr-body">{active.description}<br/><br/><b>Road:</b> {active.road}<br/><b>Hazard:</b> {incident_state["substance"]["hazard"]}<br/><b>Detected:</b> {active.detected_at}</div></div>', unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        r1.metric("Plume arrival", f"{incident_state['plume_arrival_min']} min")
        r2.metric("Evacuation clearance", f"{incident_state['evacuation_time_min']} min")
        r3, r4 = st.columns(2)
        r3.metric("Movement margin", f"{incident_state['movement_margin']} min")
        r4.metric("Shelter effectiveness", f"{incident_state['shelter_effectiveness']:.0%}")

        st.markdown(
            f'<div class="sr-alert sr-critical"><div class="sr-title">Agent protective recommendation</div><div class="sr-body"><b>{incident_state["recommendation"]}</b> · confidence {incident_state["confidence"]:.0%}<br/>The recommendation combines plume arrival, evacuation clearance, shelter effectiveness, vulnerable populations and traffic conditions.</div></div>',
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

        st.markdown('<div class="sr-h2">Exposed settings</div>', unsafe_allow_html=True)
        exposed = incident_state["exposed_pois"]
        if exposed:
            sorted_exposed = sorted(exposed, key=lambda item: item["population_now"], reverse=True)
            fig = go.Figure(go.Bar(
                x=[item["population_now"] for item in sorted_exposed],
                y=[item["name"] for item in sorted_exposed],
                orientation="h",
                text=[f"{item['population_now']:,} people · {item['distance_m']} m" for item in sorted_exposed],
                textposition="auto",
            ))
            fig.update_layout(title="Estimated people currently exposed", yaxis=dict(autorange="reversed"), xaxis=dict(showgrid=False))
            st.plotly_chart(transparent_plot_layout(fig, 270), use_container_width=True, config={"displayModeBar": False})
        else:
            st.success("No mapped vulnerable setting intersects the current demonstration zone.")


# =============================================================================
# DECISION CARD RENDERER
# =============================================================================
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
        layers.append(polygon_layer("pop-plume", [{
            "polygon": incident_state["plume_polygon"],
            "title": "Protective-action plume",
            "details": f"Arrival estimate {incident_state['plume_arrival_min']} min",
        }], [255, 80, 104, 60], [255, 80, 104, 225]))
        layers += point_layers("pop-exposed-pois", incident_state["exposed_pois"], 72, 13)
        layers += point_layers("pop-shelters", [{
            **shelter, "color": [34, 224, 189, 235], "glyph": "S", "title": shelter["name"],
            "details": f"Shelter capacity: {shelter['capacity']:,}",
        } for shelter in SHELTERS], 70, 12)
        layers += decision_overlay_layers("population-map", [preview])
        layers += point_layers("population-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": active.description,
        }], 88, 17)
        render_map(make_deck(layers, active.lat, active.lon, 12.45, 34, -8, use_basemap), "population-protection-map", 680)
        st.info(f"Preview: **{preview.title}**. The map also keeps every decision already selected in Population, Traffic and Environment, so overlaps remain visible.")

    with decision_col:
        render_decision_options(options, "preview_population")


# =============================================================================
# PAGE 4 — DISPATCH AND RESOURCES
# =============================================================================
def page_dispatch() -> None:
    st.markdown('<div class="sr-h2">Select units, compare real-street routes and prepare dispatch</div>', unsafe_allow_html=True)
    render_resource_availability()
    render_dispatch_receipt()
    controls, map_col = st.columns([1, 1.55])

    with controls:
        agency = st.selectbox("Agency to configure", list(AGENCY_LABEL.keys()), format_func=lambda key: AGENCY_LABEL[key])
        candidates = [resource for resource in RESOURCES if resource.kind == agency]
        available_candidates = [resource for resource in candidates if st.session_state.dispatch_status.get(resource.id, resource.status) != "Busy"] or candidates
        default_resource_id = st.session_state.selected_resource_ids.get(agency, available_candidates[0].id)
        default_index = next((index for index, resource in enumerate(available_candidates) if resource.id == default_resource_id), 0)
        selected_resource = st.selectbox(
            "Origin unit",
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

        with st.spinner("Calculating road-network alternatives…"):
            options = build_route_options(selected_resource, active, traffic_segments, routing_backend, amap_key)
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
            f'<div class="sr-panel selected"><div class="sr-title">{chosen.label}</div><div class="sr-body">ETA <b>{chosen.eta_min} min</b> · {chosen.distance_km} km<br/>Exposure {chosen.exposure_score} · Environment {chosen.environment_score} · Congestion {chosen.congestion_score}<br/>Composite score <b>{chosen.composite_score}</b><br/><br/>{chosen.explanation}</div><span class="sr-badge badge-ai">{chosen.backend}</span></div>',
            unsafe_allow_html=True,
        )
        if chosen.backend == "Offline approximation":
            st.error("Street data could not be loaded. This approximation can cross buildings and is only a temporary fallback. Keep OSMnx selected and check the internet connection before the demonstration.")
        render_route_comparison(options, selected_route_key)
        if st.button("Add unit and route to plan", type="primary", use_container_width=True):
            if quantity <= 0:
                st.warning("Select at least one unit.")
            else:
                st.session_state.plan_confirmed = False
                log_event(f"{quantity} {AGENCY_LABEL[agency]} unit(s) added from {selected_resource.name} using {chosen.label}", "dispatch")
                st.toast("Resource configuration added to the plan")

    with map_col:
        all_routes = []
        for key, route in options.items():
            if key == "recommended":
                continue
            selected = key == selected_route_key
            all_routes.append({
                "path": route.path,
                "color": (AGENCY_COLOR[agency] + [245]) if selected else [110, 140, 160, 62],
                "width": 11 if selected else 4,
                "title": route.label,
                "details": f"ETA {route.eta_min} min · {route.distance_km} km<br/>Composite score {route.composite_score}<br/>{route.backend}",
            })
        layers: List[pdk.Layer] = [path_layer("dispatch-route-options", all_routes, 6), path_layer("dispatch-traffic", traffic_path_data(), 7)]
        layers += point_layers("dispatch-resources", resource_map_data(), 55, 11)
        layers += point_layers("dispatch-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": active.description,
        }], 90, 17)
        deployed = deployed_vehicle_data()
        if deployed:
            layers += point_layers("dispatch-moving-units", deployed, 76, 13)
        render_map(make_deck(layers, (selected_resource.lat + active.lat) / 2, (selected_resource.lon + active.lon) / 2, 12.35, 38, -8, use_basemap), "dispatch-resources-map", 690)
        st.caption("The highlighted alternative is the route currently selected for dispatch. With OSMnx or AMap, the geometry follows the street network and road curves.")

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


# =============================================================================
# PAGE 5 — TRAFFIC CONTROL
# =============================================================================
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
            **truck, "color": [255, 180, 74, 235], "glyph": "T", "title": f"HazMat truck {truck['id']}",
            "details": f"{truck['substance']} · {truck['speed']} km/h · route {truck['route']}",
        } for truck in HAZMAT_TRUCKS], 72, 12)
        layers += point_layers("traffic-normal-incidents", [{
            **acc, "color": [255, 80, 104, 235], "glyph": "X", "title": acc["title"],
            "details": f"{acc['road']} · {acc['severity']}",
        } for acc in ORDINARY_ACCIDENTS], 58, 11)
        layers += point_layers("traffic-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": active.description,
        }], 92, 17)
        render_map(make_deck(layers, active.lat, active.lon, 12.25, 35, -8, use_basemap), "traffic-control-map", 675)
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
        layers: List[pdk.Layer] = []
        layers.append(polygon_layer("environment-water-zones", [{
            **zone, "title": zone["name"], "details": "Sensitive water and ecological receptor",
        } for zone in WATER_ZONES], [25, 116, 170, 82], [40, 215, 255, 225]))
        layers.append(polygon_layer("environment-plume", [{
            "polygon": incident_state["plume_polygon"], "title": "Air-impact zone",
            "details": f"Wind {wind_label(wind_direction)} · {wind_speed_kmh} km/h",
        }], [255, 80, 104, 45], [255, 80, 104, 190]))
        layers += point_layers("environment-drains", [{
            **drain, "color": [40, 215, 255, 240], "glyph": "D", "title": drain["name"],
            "details": "Stormwater pathway requiring protection",
        } for drain in DRAINS], 56, 11)
        layers += point_layers("environment-fixed-sensors", [{
            **sensor, "color": [34, 224, 189, 240], "glyph": "S", "title": sensor["name"],
            "details": f"Status: {sensor['status']}",
        } for sensor in SENSORS], 58, 11)
        layers += decision_overlay_layers("environment-map", [preview])
        layers += point_layers("environment-active-incident", [{
            "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [245], "glyph": "!",
            "title": active.id, "details": incident_state["substance"]["environment"],
        }], 92, 17)
        render_map(make_deck(layers, active.lat, active.lon, 12.65, 38, -8, use_basemap), "environment-protection-map", 675)
        st.info(f"Preview: **{preview.title}**. Selected population and traffic actions stay visible to reveal overlaps with drains, sensors and containment areas.")

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
    layers: List[pdk.Layer] = []
    layers.append(path_layer("plan-traffic", traffic_path_data(), 7))
    layers.append(polygon_layer("plan-plume", [{
        "polygon": incident_state["plume_polygon"],
        "title": "Current protective-action zone",
        "details": f"Simulation minute {st.session_state.demo_tick}",
    }], [255, 80, 104, 52], [255, 80, 104, 220]))
    layers += decision_overlay_layers("consolidated-plan")
    layers += route_layers_for_plan()
    deployed = deployed_vehicle_data()
    if deployed:
        layers += point_layers("plan-moving-resources", deployed, 78, 13)
    layers += point_layers("plan-shelters", [{
        **shelter, "color": [34, 224, 189, 225], "glyph": "S", "title": shelter["name"],
        "details": f"Capacity {shelter['capacity']:,}",
    } for shelter in SHELTERS], 56, 11)
    layers += point_layers("plan-incident", [{
        "lon": active.lon, "lat": active.lat, "color": THREAT_COLOR[active.threat] + [250], "glyph": "!",
        "title": active.id, "details": active.description,
    }], 95, 18)
    return layers


# =============================================================================
# PAGE 7 — CONSOLIDATED PLAN AND EXECUTIVE DEMONSTRATION
# =============================================================================
def page_plan() -> None:
    render_dispatch_receipt()
    st.markdown('<div class="sr-h2">Consolidated operational plan and presentation mode</div>', unsafe_allow_html=True)
    map_col, plan_col = st.columns([1.56, 1])

    with map_col:
        deck = make_deck(consolidated_map_layers(), active.lat, active.lon, 12.3, 40, -10, use_basemap)
        render_map(deck, "consolidated-plan-map", 690)

        timeline = go.Figure()
        minutes = list(range(0, 31))
        exposure = [max(0, incident_state["exposed_population"] * (1 - (0.018 * m if st.session_state.plan_confirmed else 0.004 * m))) for m in minutes]
        response = [min(100, max(0, (m - 4) * 5.5)) if st.session_state.plan_confirmed else min(45, m * 1.2) for m in minutes]
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
            f'<div class="sr-panel" style="border-top:2px solid {status_color}"><div class="sr-title">Plan readiness</div><div class="sr-body">{"Minimum plan complete" if ready else "Missing: " + ", ".join(missing)}</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sr-h2">Selected decisions</div>', unsafe_allow_html=True)
        for category, label in [("population", "Population"), ("traffic", "Traffic"), ("environment", "Environment")]:
            category_decisions = selected_decisions(category)
            if category_decisions:
                for decision in category_decisions:
                    st.markdown(f'<div class="sr-step"><b>{label}:</b> ✓ {decision["title"]}<br/>{decision["summary"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="sr-step"><b>{label}:</b> not selected</div>', unsafe_allow_html=True)

        st.markdown('<div class="sr-h2">Selected resources</div>', unsafe_allow_html=True)
        any_resource = False
        for kind, quantity in st.session_state.resource_quantities.items():
            if quantity <= 0:
                continue
            any_resource = True
            route = selected_route_for_kind(kind)
            resource_id = st.session_state.selected_resource_ids.get(kind)
            resource = next((r for r in RESOURCES if r.id == resource_id), None)
            if route and resource:
                status = st.session_state.dispatch_status.get(resource.id, resource.status)
                st.markdown(f'<div class="sr-step"><b>{AGENCY_LABEL[kind]}:</b> {quantity} unit(s)<br/>{resource.name} · {route.label} · ETA {route.eta_min} min · {status}</div>', unsafe_allow_html=True)
        if not any_resource:
            st.caption("No resources selected.")

        b1, b2 = st.columns(2)
        if b1.button("Confirm and dispatch", type="primary", use_container_width=True):
            confirm_dispatch()
            st.rerun()
        if b2.button("Edit resources", use_container_width=True):
            st.session_state.incident_tab = "Dispatch"
            st.rerun()

        st.markdown('<div class="sr-h2">Presentation sequence</div>', unsafe_allow_html=True)
        stage = DEMO_STAGES[st.session_state.demo_stage]
        st.progress(st.session_state.demo_stage / (len(DEMO_STAGES) - 1), text=f"Stage {st.session_state.demo_stage + 1}/{len(DEMO_STAGES)} · {stage}")
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
            st.markdown(f'<div class="sr-step"><b>{event["time"]} · {event["category"]}</b><br/>{event["message"]}</div>', unsafe_allow_html=True)

        payload = {
            "incident": asdict(active),
            "state": incident_state,
            "decisions": st.session_state.plan_decisions,
            "resources": st.session_state.resource_quantities,
            "selected_resource_ids": st.session_state.selected_resource_ids,
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


# =============================================================================
# SKYROUTE CONTEXTUAL AGENT
# =============================================================================
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
    if any(word in q for word in ["adicione", "adicionar", "inclua", "coloque", "add"]):
        for token, kind in mappings.items():
            if token in q:
                resource = next((r for r in RESOURCES if r.kind == kind and st.session_state.dispatch_status.get(r.id, r.status) != "Busy"), None)
                if resource:
                    quantity = min(resource.units, max(1, number))
                    st.session_state.resource_quantities[kind] = quantity
                    st.session_state.selected_resource_ids[kind] = resource.id
                    st.session_state.selected_routes.setdefault(kind, "recommended")
                    log_event(f"Agent added {quantity} {AGENCY_LABEL[kind]} unit(s)", "agent")
                    return f"Added {quantity} {AGENCY_LABEL[kind]} unit(s) from {resource.name} using the agent-recommended route. Review and confirm in the Dispatch tab."
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
        options = build_route_options(nearest, active, traffic_segments, routing_backend, amap_key)
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
# PAGE 8 — AGENT
# =============================================================================
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
    d3.metric("AMap key", "Detected" if bool(amap_key) else "Not configured")
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
        st.markdown(f'<div class="sr-panel"><div class="sr-title">{active.id} · {active.substance} · {active.threat}</div><div class="sr-small">{active.road} · detected {active.detected_at} · command workspace</div></div>', unsafe_allow_html=True)
    render_ai_command_strip()
    render_selected_decision_strip()
    if st.session_state.get("incident_tab_widget") != st.session_state.incident_tab:
        st.session_state.incident_tab_widget = st.session_state.incident_tab
    st.radio(
        "Incident command section",
        INCIDENT_TABS,
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
    }
    tab_functions[st.session_state.incident_tab]()


# =============================================================================
# GUIDED PITCH — CONTROLLED CASE STUDY INSIDE THE OPERATIONAL PROTOTYPE
# =============================================================================
PRESENTATION_STEPS = [
    {
        "kicker": "01 · Prevention and incident context",
        "title": "Prevention begins before the emergency.",
        "sub": "Rain, wet pavement and congestion are preventive signals. If an accident occurs, wind and rainfall become operational inputs for exposure and response models.",
    },
    {
        "kicker": "02 · Dynamic vulnerability",
        "title": "Vulnerability moves with the city.",
        "sub": "The priority is based on who is actually present at the time of the incident - not only on static land-use categories.",
    },
    {
        "kicker": "03 · Route comparison",
        "title": "The fastest route is not always the safest.",
        "sub": "Deterministic routing alternatives are compared by time, exposed population, vulnerable groups, traffic reliability and environmental conflict.",
    },
    {
        "kicker": "04 · Continuous replanning",
        "title": "When conditions change, the plan must change.",
        "sub": "A secondary crash and heavier rainfall invalidate the first corridor and trigger a new calculation.",
    },
    {
        "kicker": "05 · Human-in-command AI",
        "title": "An orchestration agent - not a chatbot.",
        "sub": "Specialized models calculate routes and risk. The agent coordinates them, explains the trade-off and waits for human approval.",
    },
]

PRESENTATION_MODULES = {
    "Population": {
        "summary": "Who is present, where, and how vulnerability changes by hour.",
        "functions": [
            "Time-dependent occupancy estimates",
            "Sensitive facilities and vulnerable groups",
            "Potential population exposure by route",
            "Protection-priority ranking",
        ],
    },
    "Dispatch": {
        "summary": "Which resources can respond and which access route is operationally defensible.",
        "functions": [
            "Resource availability and capability",
            "Estimated travel and mobilisation time",
            "Access conflicts and route alternatives",
            "Commander approval before dispatch",
        ],
    },
    "Traffic": {
        "summary": "How congestion, closures and road incidents alter reliability.",
        "functions": [
            "Congestion and wet-road penalties",
            "Secondary crashes and blocked segments",
            "Fastest versus low-conflict routing",
            "Continuous travel-time recalculation",
        ],
    },
    "Environment": {
        "summary": "How the chemical event interacts with weather, water and sensitive areas.",
        "functions": [
            "Wind-informed plume geometry",
            "Rainfall and runoff assumptions",
            "Water bodies, drains and ecological receptors",
            "Containment and monitoring priorities",
        ],
    },
}

PRESENTATION_STEP_MODULES = [
    {"Traffic", "Environment"},
    {"Population"},
    {"Population", "Dispatch", "Traffic"},
    {"Dispatch", "Traffic", "Environment"},
    {"Population", "Dispatch", "Traffic", "Environment"},
]

FASTEST_DEMO_PATH = [
    [118.6730, 32.1790], [118.6795, 32.1740], [118.6830, 32.1680],
    [118.6878, 32.1650], [118.6906, 32.1628],
]
SAFER_DEMO_PATH = [
    [118.6730, 32.1790], [118.6685, 32.1720], [118.6700, 32.1600],
    [118.6790, 32.1530], [118.6870, 32.1560], [118.6906, 32.1628],
]
REPLANNED_DEMO_PATH = [
    [118.6730, 32.1790], [118.6660, 32.1810], [118.6620, 32.1700],
    [118.6660, 32.1570], [118.6790, 32.1510], [118.6870, 32.1560],
    [118.6906, 32.1628],
]


def presentation_route_layers(
    show_fastest: bool = True,
    show_safest: bool = True,
    show_replanned: bool = False,
    fastest_blocked: bool = False,
) -> List[pdk.Layer]:
    route_data: List[Dict[str, Any]] = []
    if show_fastest:
        route_data.append({
            "path": FASTEST_DEMO_PATH,
            "color": [255, 118, 92, 125 if fastest_blocked else 245],
            "width": 8,
            "title": "Fastest route" + (" - invalidated" if fastest_blocked else ""),
            "details": "18 min · 4,850 people near corridor · 1,170 vulnerable people",
        })
    if show_safest:
        route_data.append({
            "path": SAFER_DEMO_PATH,
            "color": [213, 242, 109, 235],
            "width": 9,
            "title": "Safer route",
            "details": "22 min · 1,420 people near corridor · 260 vulnerable people",
        })
    if show_replanned:
        route_data.append({
            "path": REPLANNED_DEMO_PATH,
            "color": [40, 215, 255, 245],
            "width": 9,
            "title": "Replanned safer route",
            "details": "23 min · avoids the secondary crash and high-exposure corridor",
        })
    return [path_layer("presentation-routes", route_data, 8)] if route_data else []


def presentation_context_layers(
    dynamic_hour: Optional[int] = None,
    include_routes: bool = False,
    replanned: bool = False,
) -> List[pdk.Layer]:
    display_pois = build_live_pois(dynamic_hour if dynamic_hour is not None else 14, True)
    plume = [{
        "polygon": incident_state["plume_polygon"],
        "title": "Estimated chlorine exposure zone",
        "details": "Deterministic scenario geometry · changes with wind and release assumptions",
    }]
    isolation = [{
        "polygon": make_circle_polygon(active.lat, active.lon, incident_state["isolation_distance"]),
        "title": "Immediate isolation zone",
        "details": f"{incident_state['isolation_distance']} m scenario radius",
    }]
    accidents = [{
        "lon": item["lon"], "lat": item["lat"],
        "color": [255, 180, 74, 245],
        "title": item["title"],
        "details": f"{item['road']} · {item['severity']} road disruption",
    } for item in ORDINARY_ACCIDENTS]
    incident_point = [{
        "lon": active.lon, "lat": active.lat,
        "color": [255, 80, 104, 250],
        "title": f"{active.id} · {active.substance}",
        "details": active.description,
    }]
    layers: List[pdk.Layer] = [
        polygon_layer("presentation-plume", plume, [255, 80, 104, 52], [255, 80, 104, 205]),
        polygon_layer("presentation-isolation", isolation, [255, 180, 74, 24], [255, 180, 74, 205]),
        path_layer("presentation-traffic", traffic_path_data(), 6),
    ]
    for poi in display_pois:
        poi["radius"] = max(75, min(360, 75 + poi["population_now"] * 0.10))
    layers.append(scatter_layer("presentation-population", display_pois, "radius"))
    layers.append(scatter_layer("presentation-road-events", accidents, 105))
    layers.append(scatter_layer("presentation-main-incident", incident_point, 145))
    if include_routes:
        layers.extend(presentation_route_layers(True, not replanned, replanned, replanned))
    return layers


def render_presentation_map(
    layers: List[pdk.Layer],
    key: str,
    zoom: float = 12.1,
    pitch: float = 38,
    height: int = 570,
) -> None:
    deck = make_deck(
        layers,
        latitude=32.1625,
        longitude=118.6890,
        zoom=zoom,
        pitch=pitch,
        bearing=0,
        use_basemap=use_basemap,
    )
    render_map(deck, key=key, height=height)


def presentation_header(step: int) -> None:
    exit_col, progress_col, prev_col, next_col = st.columns([1.35, 6.3, .75, .75])
    with exit_col:
        if st.button("← Exit", key="exit_presentation", use_container_width=True):
            st.session_state.presentation_mode = False
            st.rerun()
    with progress_col:
        st.caption(f"SKYROUTE CASE STUDY  ·  {step + 1} / {len(PRESENTATION_STEPS)}")
        st.progress((step + 1) / len(PRESENTATION_STEPS))
    with prev_col:
        if st.button("‹", key="presentation_previous", use_container_width=True, disabled=step == 0):
            st.session_state.presentation_step = max(0, step - 1)
            st.rerun()
    with next_col:
        if st.button("›", key="presentation_next", use_container_width=True, disabled=step == len(PRESENTATION_STEPS) - 1):
            st.session_state.presentation_step = min(len(PRESENTATION_STEPS) - 1, step + 1)
            st.rerun()


def presentation_title(step: int) -> None:
    item = PRESENTATION_STEPS[step]
    st.markdown(
        f"""
        <div class="sr-present-shell">
          <div class="sr-present-kicker">{item['kicker']}</div>
          <div class="sr-present-title">{item['title']}</div>
          <div class="sr-present-sub">{item['sub']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_presentation_modules(step: int) -> None:
    active_modules = PRESENTATION_STEP_MODULES[step]
    st.markdown(
        '<div class="sr-present-kicker" style="margin:2px 0 7px">Tools activated in this scene</div>',
        unsafe_allow_html=True,
    )
    module_cols = st.columns(4)
    for col, (module_name, module) in zip(module_cols, PRESENTATION_MODULES.items()):
        with col:
            active_mark = "●" if module_name in active_modules else "○"
            with st.popover(f"{active_mark} {module_name}"):
                status = "Activated in this scene" if module_name in active_modules else "Available to the agent"
                st.caption(status.upper())
                st.markdown(f"**{module['summary']}**")
                for function_name in module["functions"]:
                    st.markdown(f"- {function_name}")
                st.caption(
                    "The agent coordinates this module; deterministic logic and data tools produce its metrics."
                )


def presentation_step_risks() -> None:
    map_col, story_col = st.columns([2.15, 1])
    with map_col:
        render_presentation_map(presentation_context_layers(), "presentation-risk-map")
    with story_col:
        st.markdown(
            """
            <div class="sr-present-card">
              <div class="eyebrow">Preventive monitoring · before an accident</div>
              <div class="sr-risk-row"><div class="sr-risk-icon">R</div><div><div class="sr-risk-name">Heavy-rain signal</div><div class="sr-risk-copy">Wet pavement and lower visibility raise collision risk</div></div><div class="sr-risk-value">34 mm/h</div></div>
              <div class="sr-risk-row"><div class="sr-risk-icon">T</div><div><div class="sr-risk-name">Congestion rising</div><div class="sr-risk-copy">HazMat corridor reliability is deteriorating</div></div><div class="sr-risk-value">82%</div></div>
            </div>
            <br/>
            <div class="sr-present-card">
              <div class="eyebrow">Active-incident context · if an accident occurs</div>
              <div class="sr-risk-row"><div class="sr-risk-icon">W</div><div><div class="sr-risk-name">Wind direction</div><div class="sr-risk-copy">Changes estimated plume direction and protection targets</div></div><div class="sr-risk-value">SE</div></div>
              <div class="sr-risk-row"><div class="sr-risk-icon">R</div><div><div class="sr-risk-name">Rainfall conditions</div><div class="sr-risk-copy">Affect visibility, travel time and chemical runoff assumptions</div></div><div class="sr-risk-value">Active input</div></div>
            </div>
            <div class="sr-present-quote">Only by understanding the risks can we find the right direction.</div>
            <div class="sr-present-note">Simulated pitch scenario · values are illustrative and auditable.</div>
            """,
            unsafe_allow_html=True,
        )


def presentation_step_population() -> None:
    hour_options = [2, 8, 14, 19]
    selected_hour = st.segmented_control(
        "Incident time",
        hour_options,
        default=st.session_state.presentation_hour,
        format_func=lambda value: f"{value:02d}:00",
        key="presentation_hour_control",
    )
    if selected_hour is not None:
        st.session_state.presentation_hour = int(selected_hour)
    hour_now = st.session_state.presentation_hour
    live = build_live_pois(hour_now, True)
    school_pop = sum(item["population_now"] for item in live if item["type"] == "school")
    residential_pop = sum(item["population_now"] for item in live if item["type"] == "residential")
    commercial_pop = sum(item["population_now"] for item in live if item["type"] == "commercial")
    if 7 <= hour_now <= 17:
        priority = "Schools"
        explanation = "Children and staff are present; school sensitivity drives protection priority."
    elif hour_now >= 19 or hour_now < 7:
        priority = "Residential areas"
        explanation = "School occupancy falls while residential presence becomes dominant."
    else:
        priority = "Mixed urban activity"
        explanation = "Commuting and commercial activity redistribute exposure."
    map_col, story_col = st.columns([2.15, 1])
    with map_col:
        render_presentation_map(
            presentation_context_layers(dynamic_hour=hour_now),
            f"presentation-population-map-{hour_now}",
        )
    with story_col:
        cards = st.columns(2)
        values = [
            ("School occupancy", f"{school_pop:,}", "estimated people present"),
            ("Residential", f"{residential_pop:,}", "estimated people present"),
            ("Commercial", f"{commercial_pop:,}", "estimated people present"),
            ("Priority now", priority, f"{hour_now:02d}:00 scenario"),
        ]
        for col, (label, value, detail) in zip(cards + st.columns(2), values):
            with col:
                st.markdown(
                    f'<div class="sr-present-card"><div class="eyebrow">{label}</div><div class="big">{value}</div><div class="copy">{detail}</div></div>',
                    unsafe_allow_html=True,
                )
        st.markdown(
            f'<div class="sr-present-quote">{explanation}</div><div class="sr-present-note">Population presence is a time-dependent scenario estimate, not a live census feed.</div>',
            unsafe_allow_html=True,
        )


def presentation_step_routes() -> None:
    layers = presentation_context_layers(dynamic_hour=14)
    layers.extend(presentation_route_layers())
    map_col, comparison_col = st.columns([1.9, 1.1])
    with map_col:
        render_presentation_map(layers, "presentation-route-comparison", zoom=12.25)
    with comparison_col:
        st.markdown(
            """
            <div class="sr-present-quote">4 additional minutes reduce potential vulnerable exposure by 78%.</div>
            <div class="sr-route-table">
              <div class="head">Metric</div><div class="head fast">Fastest</div><div class="head safe">Safer</div>
              <div>Travel time</div><div class="fast">18 min</div><div class="safe">22 min</div>
              <div>Population near route</div><div class="fast">4,850</div><div class="safe">1,420</div>
              <div>Vulnerable people</div><div class="fast">1,170</div><div class="safe">260</div>
              <div>Schools affected</div><div class="fast">2</div><div class="safe">0</div>
              <div>Traffic reliability</div><div class="fast">Low</div><div class="safe">High</div>
              <div>Agent recommendation</div><div class="fast">Rejected</div><div class="safe">Selected</div>
            </div>
            <div class="sr-present-note">Potential exposure, not predicted casualties. Scenario metrics are shown to make the trade-off explicit.</div>
            """,
            unsafe_allow_html=True,
        )


def presentation_step_replanning() -> None:
    disrupted = st.session_state.presentation_disruption
    event_col, action_col = st.columns([3.1, 1])
    with event_col:
        st.markdown(
            f'<span class="sr-time-chip">14:00 Incident</span><span class="sr-time-chip">14:04 Heavy rain</span><span class="sr-time-chip">14:07 Secondary crash</span><span class="sr-time-chip">{"14:10 Recalculated" if disrupted else "Awaiting update"}</span>',
            unsafe_allow_html=True,
        )
    with action_col:
        if st.button(
            "↻ Trigger live update" if not disrupted else "Reset update",
            key="trigger_presentation_update",
            use_container_width=True,
            type="primary" if not disrupted else "secondary",
        ):
            st.session_state.presentation_disruption = not disrupted
            st.rerun()
    layers = presentation_context_layers(dynamic_hour=14, include_routes=True, replanned=disrupted)
    map_col, story_col = st.columns([2.15, 1])
    with map_col:
        render_presentation_map(
            layers,
            f"presentation-replan-map-{int(disrupted)}",
            zoom=12.15,
        )
    with story_col:
        if disrupted:
            st.markdown(
                """
                <div class="sr-present-card">
                  <div class="eyebrow">New conditions received</div>
                  <div class="big">Plan recalculated</div>
                  <div class="copy">Secondary crash blocks the first corridor. Rainfall increases road risk and travel-time uncertainty.</div>
                </div>
                <div class="sr-present-quote">The former route is invalidated. A new low-conflict corridor is recommended.</div>
                <div class="sr-human"><b>COMMANDER REVIEW REQUIRED</b><br/>No automatic dispatch is issued.</div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="sr-present-card">
                  <div class="eyebrow">Current plan</div>
                  <div class="big">Safer route active</div>
                  <div class="copy">The agent continues checking traffic, rainfall, exposure and resource availability.</div>
                </div>
                <div class="sr-present-quote">A recommendation is valid only while its assumptions remain valid.</div>
                """,
                unsafe_allow_html=True,
            )


def presentation_step_agent() -> None:
    flow_col, outcome_col = st.columns([1.4, 1])
    with flow_col:
        st.markdown(
            """
            <div class="sr-present-card">
              <div class="eyebrow">Auditable agent trace</div>
              <div class="sr-agent-step"><b>Incident report interpreted</b>Incomplete report normalized into operational facts.</div>
              <div class="sr-agent-step"><b>Specialized tools called</b>Chemical risk, weather, population and routing models queried.</div>
              <div class="sr-agent-step"><b>Dynamic presence estimated</b>Population and vulnerable groups adjusted for 14:00.</div>
              <div class="sr-agent-step"><b>Candidate routes calculated</b>Deterministic models return time, exposure and conflict metrics.</div>
              <div class="sr-agent-step"><b>Trade-offs compared</b>Fastest route rejected because of vulnerable exposure.</div>
              <div class="sr-agent-step"><b>Recommendation explained</b>Safer route prepared for commander review.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with outcome_col:
        st.markdown(
            """
            <div class="sr-present-quote">The agent coordinates the decision. It does not replace the decision-maker.</div>
            <div class="sr-present-card">
              <div class="eyebrow">Current recommendation</div>
              <div class="big">Select the safer route</div>
              <div class="copy">+4 minutes · 78% lower potential vulnerable exposure · no schools along the selected corridor.</div>
            </div>
            <br/>
            <div class="sr-human"><b>HUMAN SIGN-OFF</b><br/>A commander approves, modifies or rejects the recommendation before dispatch.</div>
            <div class="sr-present-note">Routes and scores are deterministic scenario outputs. The language layer generates the human-readable explanation.</div>
            """,
            unsafe_allow_html=True,
        )


def page_presentation() -> None:
    step = int(clamp(st.session_state.presentation_step, 0, len(PRESENTATION_STEPS) - 1))
    presentation_header(step)
    presentation_title(step)
    render_presentation_modules(step)
    renderers = [
        presentation_step_risks,
        presentation_step_population,
        presentation_step_routes,
        presentation_step_replanning,
        presentation_step_agent,
    ]
    renderers[step]()


# =============================================================================
# PAGE ROUTER — ONLY THE ACTIVE WORKSPACE IS RENDERED
# =============================================================================
PAGE_FUNCTIONS = {
    "Central & Prevention": page_central,
    "Incident Command": page_incident_command,
    "SkyRoute AI Copilot": page_agent,
    "Cases & Data": page_cases,
}

if st.session_state.presentation_mode:
    page_presentation()
else:
    PAGE_FUNCTIONS.get(page, page_central)()

if not st.session_state.presentation_mode:
    st.markdown(
        """
<div class="sr-footer">
SkyRoute / 天途 v10 · product and academic demonstration.<br/>
Default incidents, positions, traffic, population estimates, plume geometry and response scores are simulated. No real dispatch is performed.<br/>
Production deployment requires validated models, official emergency plans, licensed data, secure SkyTech interfaces and human command authority.
</div>
""",
        unsafe_allow_html=True,
    )
