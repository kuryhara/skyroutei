"""
SkyRoute / 天途 v29 — Clear Plan Map Context
============================================
Single-file Streamlit application for a demonstrator of hazardous-material
incident prevention, command, routing, dispatch, population protection,
traffic control, environmental response and executive presentation.

Run on Windows PowerShell
-------------------------
cd "C:\Users\leara\Downloads"
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
    page_title="SkyRoute | Emergency Decision Support",
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

SKYROUTE_LOGO_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxOTggMTIyIiByb2xlPSJpbWciIGFyaWEtbGFiZWw9IlNreVJvdXRlIOWkqemAlCBsb2dvIj4KICA8cmVjdCB3aWR0aD0iMTk4IiBoZWlnaHQ9IjEyMiIgcng9IjAiIGZpbGw9IiNENUYyNkQiLz4KICA8cGF0aCBkPSJNIDEzOCA2NiBMIDEzNCA2NiBMIDEzNCA2NyBMIDEzMiA2OSBMIDEzMCA3MiBMIDEzMCA3MyBMIDEyNCA3OSBMIDEyNSA3OSBMIDEyNyA4MSBMIDEyOCA4MSBMIDEzMyA3NiBMIDEzMyA3NSBMIDEzNyA3MCBMIDEzNyA2OSBMIDEzOCA2OCBaIE0gMTYxIDY2IEwgMTYwIDY3IEwgMTYwIDY4IEwgMTY1IDczIEwgMTY1IDc0IEwgMTY3IDc2IEwgMTY3IDc3IEwgMTY5IDc5IEwgMTY5IDgwIEwgMTcwIDgxIEwgMTcxIDgwIEwgMTcyIDgwIEwgMTczIDc5IEwgMTczIDc4IEwgMTcyIDc3IEwgMTcyIDc2IEwgMTcwIDc0IEwgMTcwIDczIEwgMTY3IDcwIEwgMTY3IDY5IEwgMTYzIDY1IEwgMTY2IDY2IFogTSAxMDUgNTIgTCAxMDUgNTYgTCAxMTQgNTYgTCAxMTUgNTcgTCAxMTUgODIgTCAxMTQgODMgTCAxMTMgODMgTCAxMTEgODUgTCAxMTAgODUgTCAxMDQgOTEgTCAxMDYgOTMgTCAxMDYgOTQgTCAxMDcgOTUgTCAxMTYgODYgTCAxMjAgODYgTCAxMjUgOTAgTCAxMjYgOTAgTCAxMjkgOTIgTCAxMzEgOTIgTCAxMzIgOTMgTCAxMzQgOTMgTCAxMzUgOTQgTCAxNzQgOTQgTCAxNzQgOTMgTCAxNzUgOTIgTCAxNzUgOTAgTCAxNzYgODkgTCAxNzAgODkgTCAxNkkgOTAgTCAxMzYgOTAgTCAxMzUgODkgTCAxMzIgODkgTCAxMzEgODggTCAxMjkgODggTCAxMjcgODYgTCAxMjQgODUgTCAxMjIgODMgTCAxMjEgODMgTCAxMjAgODIgTCAxMjAgNTIgWiBNIDI5IDMwIEwgMjkgMzUgTCA1NiAzNSBMIDU3IDM2IEwgNTcgNTMgTCA1NiA1NCBMIDI2IDU0IEwgMjYgNTkgTCA1NCA1OSBMIDU1IDYwIEwgNTUgNjIgTCA1NCA2MyBMIDU4IDY1IEwgNTMgNjYgTCA1MyA2NyBMIDUyIDY4IEwgNTEgNzEgTCA0OCA3NCBMIDQ4IDc1IEwgNDEgODIgTCA0MCA4MiBMIDM3IDg1IEwgMzYgODUgTCAzNSA4NiBMIDM0IDg2IEwgMzIgODggTCAzMSA4OCBMIDMwIDg5IEwgMjkgODkgTCAyOCA5MCBMIDI1IDkxIEwgMjUgOTIgTCAyOCA5NSBMIDI5IDk1IEwgMzAgOTQgTCAzMSA5NCBMIDMyIDkzIEwgMzMgOTMgTCAzNCA5MiBMIDM3IDkxIEwgMzkgODkgTCA0MCA4OSBMIDQyIDg3IEwgNDMgODcgTCA0OCA4MiBMIDQ5IDgyIEwgNTAgODEgTCA1MCA4MCBMIDU0IDc2IEwgNTQgNzUgTCA1NiA3MyBMIDU2IDcyIEwgNTggNjkgTCA1OCA2NyBMIDYwIDY1IEwgNjEgNjUgTCA2MiA2NiBMIDYyIDY4IEwgNjMgNjkgTCA2MyA3MCBMIDY1IDcyIEwgNjYgNzUgTCA2OSA3OCBMIDY5IDc5IEwgNzggODggTCA3OSA4OCBMIDgxIDkwIEwgODIgOTAgTCA4MyA5MSBMIDg0IDkxIEwgODUgOTIgTCA4NiA5MiBMIDkxIDk1IEwgOTMgOTUgTCA5MyA5NCBMIDk2IDkxIEwgOTUgOTEgTCA5NCA5MCBMIDkyIDkwIEwgOTEgODkgTCA5MCA4OSBMIDg5IDg4IEwgODYgODcgTCA4MSA4MyBMIDgwIDgzIEwgNzEgNzQgTCA3MSA3MyBMIDY3IDY4IEwgNjcgNjcgTCA2NSA2NCBMIDY1IDYyIEwgNjQgNjEgTCA2NCA2MCBMIDY1IDU5IEwgOTQgNTkgTCA5NCA1NCBMIDYzIDU0IEwgNjIgNTMgTCA2MiAzNiBMIDYzIDM1IEwgOTAgMzUgTCA5MSAzNCBMIDkxIDMwIFogTSAxMDggMjkgTCAxMDggMzAgTCAxMDkgMzEgTCAxMTAgMzEgTCAxMTIgMzMgTCAxMTMgMzMgTCAxMTggMzggTCAxMTkgMzggTCAxMjAgMzkgTCAxMjMgMzYgTCAxMTkgMzIgTCAxMTggMzIgTCAxMTYgMzAgTCAxMTUgMzAgTCAxMTMgMjggTCAxMTIgMjggTCAxMTEgMjcgTCAxMTAgMjcgWiBNIDE0OSAyMyBMIDE0OCAyMyBMIDE0OCAyNCBMIDE0NSAyNyBMIDE0NSAyOCBMIDEzOCAzNSBMIDEzNyAzNSBMIDEzNCAzOCBMIDEzMyAzOCBMIDEyOCA0MiBMIDEyNyA0MiBMIDEyNiA0MyBMIDEyNSA0NCBMIDEyMyA0NSBMIDEyNiA0OCBMIDEyNyA0NyBMIDEzMCA0NiBMIDEzMiA0NCBMIDEzNSA0MyBMIDEzNiA0NCBMIDEzNiA0OCBMIDE0NiA0OCBMIDE0NyA0OSBMIDE0NyA1NiBMIDE0NiA1NyBMIDEyNiA1NyBMIDEyNiA2MCBMIDEyNyA2MSBMIDE0NiA2MSBMIDE0NyA2MiBMIDE0NyA4MCBMIDE0NiA4MSBMIDEzOSA4MSBMIDEzOSA4MyBMIDE0MCA4NCBMIDE0MCA4NSBMIDE0ODg1BMIDE1MSA4MyBMIDE1MSA4MiBMIDE1MiA4MSBMIDE1MiA2MiBMIDE1MyA2MSBMIDE3MzA2MSBMIDE3NCA2MCBMIDE3NCA1NyBMIDE1MyA1NyBMIDE1MiA1NiBMIDE1MiA0OSBMIDE1MyA0OCBMIDE2MyA0OCBMIDE2NCA0NyBMIDE2NCA0NCBMIDE2NSA0MyBMIDE2NiA0MyBMIDE2OCA0NSBMIDE2OSA0NSBMIDE3MCA0NiBMIDE3MiA0NiBMIDE3MyA0NyBMIDE3NCA0NiBMIDE3NCA0NSBMIDE3NiA0MyBMIDE3NSA0MgBMIDE3MyA0MiBMIDE3MiA0MSBMIDE3MSA0MSBMIDE3MCA0MCBMIDE2OSA0MCBMIDE2OCAzOSBMIDE2NSA0OCBMIDE2MzAzNiBMIDE2MiAzNiBMIDE2MCAzNCBMIDE1OSAzNCBMIDE1MiAyNyBMIDE1MiAyNSBaIE0gMTM1IDQyIEwgMTM2IDQxIEwgMTM3IDQxIEwgMTQwIDM4IEwgMTQxIDM4IEwgMTQ4IDMxIEwgMTUwIDMxIEwgMTU1IDM2IEwgMTU2IDM2IEwgMTYwIDQwIEwgMTYxIDQwIEwgMTYzIDQyIEwgMTYzIDQzIEwgMTYyIDQ0IEwgMTM2IDQ0IEwgMTM1IDQzIFoiIGZpbGw9IiMwNjExMEUiIGZpbGwtcnVsZT0iZXZlbm9kZCIgY2xpcC1ydWxlPSJldmVub2RkIi8+Cjwvc3ZnPg=="

def skyroute_logo_html(css_class: str = "sr-brand-lockup") -> str:
    return f'<div class="{css_class}"><img src="{SKYROUTE_LOGO_DATA_URI}" class="sr-brand-icon" alt="SkyRoute 天途 logo"/><div class="sr-brand-wordmark">SKYROUTE</div></div>'