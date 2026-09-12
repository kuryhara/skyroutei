import streamlit as st
import pandas as pd
import pydeck as pdk
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA & ESTILOS CSS
# =============================================================================

st.set_page_config(
    page_title="SkyRoute - Centro de Controle de Emergências",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .reportview-container { background: #0e1117; color: #fafafa; }
    .sr-top { display: flex; justify-content: space-between; align-items: center; padding: 1rem 0; border-bottom: 1px solid #333; margin-bottom: 1.5rem; }
    .sr-brand { font-weight: 700; font-size: 1.25rem; letter-spacing: 0.05em; color: #00c4ff; }
    .sr-top-right a { color: #888; text-decoration: none; font-size: 0.9rem; }
    .sr-top-right a:hover { color: #fff; }
    .sr-h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #e2e8f0; }
    .sr-workflow-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 0.75rem; }
    .sr-workflow { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 2rem; }
    .sr-workflow-item { display: flex; gap: 0.75rem; align-items: flex-start; opacity: 0.5; }
    .sr-workflow-item.active { opacity: 1; }
    .sr-workflow-item.done { opacity: 0.8; }
    .sr-workflow-dot { width: 24px; height: 24px; border-radius: 50%; background: #334155; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: bold; color: #fff; flex-shrink: 0; }
    .sr-workflow-item.active .sr-workflow-dot { background: #00c4ff; }
    .sr-workflow-item.done .sr-workflow-dot { background: #10b981; }
    .sr-workflow-name { font-weight: 600; font-size: 0.9rem; color: #f8fafc; }
    .sr-workflow-desc { font-size: 0.8rem; color: #94a3b8; }
    .sr-incident-board { display: flex; flex-direction: column; gap: 0.75rem; }
    .sr-incident-card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; position: relative; }
    .sr-incident-card.active { border-color: #ef4444; }
    .sr-incident-status { position: absolute; top: 1rem; right: 1rem; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
    .sr-incident-status.active { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .sr-title { font-weight: 600; font-size: 1rem; color: #f8fafc; margin-bottom: 0.25rem; }
    .sr-body { font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.5rem; }
    .sr-small { font-size: 0.75rem; color: #94a3b8; }
    .sr-map-preview { border-radius: 8px; overflow: hidden; border: 1px solid #334155; }
    .metric-card { background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155; text-align: center; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# MODELOS DE DADOS & CONSTANTES
# =============================================================================

@dataclass
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

@dataclass
class Resource:
    id: str
    name: str
    lat: float
    lon: float
    kind: str
    status: str
    units: int
    capacity: str

THREAT_COLOR: Dict[str, List[int]] = {
    "CRITICAL": [239, 68, 68, 220],
    "HIGH": [249, 115, 22, 220],
    "MODERATE": [234, 179, 8, 220]
}

def skyroute_logo_html(className: str = "") -> str:
    return f"""
    <div class="{className}">
        <div style="font-size: 1.1rem; font-weight: 800; color: #00c4ff; letter-spacing: 0.1em;">SKYROUTE</div>
        <div style="font-size: 0.7rem; color: #64748b; letter-spacing: 0.05em;">GEOPROCESSAMENTO URBANO</div>
    </div>
    """

# =============================================================================
# MAPAS E COMPONENTES ESPACIAIS
# =============================================================================

def generate_map_layers(incidents: List[Incident], resources: List[Resource], radius_km: float) -> pdk.Deck:
    """
    Constrói as camadas de dados espaciais incluindo zonas de impacto e isolamento.
    """
    incident_data = [asdict(i) for i in incidents]
    
    # Camada de raio de dispersão (Círculo de impacto estimado)
    impact_layer = pdk.Layer(
        "ScatterplotLayer",
        data=incident_data,
        get_position="[lon, lat]",
        get_fill_color=[239, 68, 68, 50],
        get_radius=radius_km * 1000, # Converter km para metros
        pickable=False,
    )

    incident_layer = pdk.Layer(
        "ScatterplotLayer",
        data=incident_data,
        get_position="[lon, lat]",
        get_fill_color=[239, 68, 68, 220],
        get_radius=150,
        pickable=True,
        opacity=0.8,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=2,
    )

    resource_data = [asdict(r) for r in resources]
    resource_layer = pdk.Layer(
        "ScatterplotLayer",
        data=resource_data,
        get_position="[lon, lat]",
        get_fill_color=[0, 196, 255, 220],
        get_radius=80,
        pickable=True,
        opacity=0.9,
    )

    view_state = pdk.ViewState(
        latitude=32.0603,
        longitude=118.7969,
        zoom=13,
        pitch=45,
        bearing=0
    )

    return pdk.Deck(
        layers=[impact_layer, incident_layer, resource_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10",
        tooltip={"text": "{name}\nStatus: {status}\nSubstância: {substance}"}
    )

def render_sidebar() -> Dict[str, Any]:
    """Painel lateral avançado com controles de simulação e geoprocessamento."""
    st.sidebar.markdown(skyroute_logo_html("sr-sidebar-brand"), unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sr-workflow-title'>Fluxo de Operação</div>", unsafe_allow_html=True)
    
    st.sidebar.markdown("""
    <div class="sr-workflow">
        <div class="sr-workflow-item done">
            <div class="sr-workflow-dot">1</div>
            <div>
                <div class="sr-workflow-name">Detecção e Isolamento</div>
                <div class="sr-workflow-desc">Perímetro estabelecido.</div>
            </div>
        </div>
        <div class="sr-workflow-item active">
            <div class="sr-workflow-dot">2</div>
            <div>
                <div class="sr-workflow-name">Despacho de Rotas</div>
                <div class="sr-workflow-desc">Calculando rotas de fuga.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("### Parâmetros de Simulação")
    dispersion_radius = st.sidebar.slider("Raio de Isolamento Crítico (km)", 0.5, 5.0, 1.5, 0.1)
    wind_speed = st.sidebar.slider("Velocidade do Vento (km/h)", 0.0, 40.0, 12.5)
    evacuation_mode = st.sidebar.selectbox("Estratégia de Evacuação", ["Anel Concêntrico", "Setorizado por Vento", "Corredores Livres"])
    
    return {
        "dispersion_radius": dispersion_radius,
        "wind_speed": wind_speed,
        "evacuation_mode": evacuation_mode
    }

def main():
    params = render_sidebar()
    
    st.markdown("""
    <div class="sr-top">
        <div class="sr-brand">
            <div class="sr-name">CENTRO DE CONTROLE DE EMERGÊNCIAS - MÓDULO ESPACIAL</div>
        </div>
        <div class="sr-top-right">
            <a href="#" class="sr-top-link">Sincronizado com QGIS Server</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Base de Dados Expandida de Incidentes e Recursos
    incidents = [
        Incident(
            id="INC-001", lat=32.0603, lon=118.7969, road="Jiangbei Expressway",
            substance="Cloro Gasoso", threat="CRITICAL", quantity_t=4.5,
            leak_rate_kg_min=12.0, detected_at="13:14", description="Vazamento em transporte rodoviário"
        ),
        Incident(
            id="INC-002", lat=32.0680, lon=118.8050, road="Nanjing Ring Rd",
            substance="Ácido Sulfúrico", threat="HIGH", quantity_t=8.0,
            leak_rate_kg_min=5.5, detected_at="13:28", description="Rompimento de válvula lateral"
        )
    ]
    
    resources = [
        Resource(id="RES-99", name="Unidade HazMat Alpha", lat=32.0550, lon=118.7900, kind="hazmat", status="En route", units=2, capacity="Alta"),
        Resource(id="RES-102", name="Bombeiros Setor Norte", lat=32.0720, lon=118.7910, kind="fire", status="Dispatched", units=4, capacity="Média"),
        Resource(id="RES-105", name="Defesa Civil Móvel", lat=32.0500, lon=118.8100, kind="civil", status="Standby", units=1, capacity="Alta")
    ]

    # Métricas Globais Superiores
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(f"<div class='metric-card'><h4>Incidentes Ativos</h4><h2>{len(incidents)}</h2></div>", unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"<div class='metric-card'><h4>Recursos Alocados</h4><h2>{len(resources)}</h2></div>", unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"<div class='metric-card'><h4>Estratégia</h4><p style='margin:0; font-weight:600; color:#00c4ff'>{params['evacuation_mode']}</p></div>", unsafe_allow_html=True)
    with col_m4:
        st.markdown(f"<div class='metric-card'><h4>Vento</h4><p style='margin:0; font-weight:600; color:#00c4ff'>{params['wind_speed']} km/h</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("<div class='sr-map-preview'>", unsafe_allow_html=True)
        deck = generate_map_layers(incidents, resources, params["dispersion_radius"])
        st.pydeck_chart(deck, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='sr-h2'>Painel de Incidentes e Contenção</div>", unsafe_allow_html=True)
        
        tab_inc, tab_res = st.tabs(["Incidentes", "Recursos"])
        
        with tab_inc:
            st.markdown("<div class='sr-incident-board'>", unsafe_allow_html=True)
            for inc in incidents:
                st.markdown(f"""
                <div class="sr-incident-card active">
                    <span class="sr-incident-status active">{inc.threat}</span>
                    <div class="sr-title">{inc.id} - {inc.substance}</div>
                    <div class="sr-body">{inc.description}</div>
                    <div class="sr-small">Via: {inc.road} | Vazamento: {inc.leak_rate_kg_min} kg/min</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with tab_res:
            for res in resources:
                st.markdown(f"""
                <div class="sr-incident-card" style="border-color: #00c4ff;">
                    <span class="sr-incident-status" style="background: rgba(0, 196, 255, 0.2); color: #00c4ff;">{res.status}</span>
                    <div class="sr-title">{res.name}</div>
                    <div class="sr-body">Capacidade: {res.capacity} | Unidades: {res.units}</div>
                    <div class="sr-small">Coordenadas: {res.lat}, {res.lon}</div>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()