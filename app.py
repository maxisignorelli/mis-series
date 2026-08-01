import streamlit as st
import requests
import json
import os
from datetime import datetime
from streamlit_searchbox import st_searchbox

# --- CONFIGURACIÓN DE PÁGINA (WIDE LAYOUT) ---
st.set_page_config(
    page_title="StreamTracker — Estilo JustWatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (JUSTWATCH THEME) ---
st.markdown("""
<style>
    /* Fondo principal estilo streaming */
    .stApp {
        background: #0b0e14;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header superior */
    .header-container {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .header-title {
        color: #f8fafc;
        font-weight: 900;
        font-size: 2.2rem;
        margin: 0;
        letter-spacing: -0.03em;
    }
    
    /* Tarjetas de Colección (Card Grid) */
    .movie-card {
        background-color: #151c28;
        border: 1px solid #232d3f;
        border-radius: 12px;
        padding: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    .movie-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
    }
    
    /* Insignias */
    .imdb-badge {
        background-color: #f5c518;
        color: #000000;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .status-badge-viewing {
        background-color: #10b981;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-completed {
        background-color: #3b82f6;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* Estilizado de inputs */
    div[data-testid="stExpander"] {
        background-color: #151c28 !important;
        border: 1px solid #232d3f !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS LOCAL ---
DB_FILE = "series_data.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- FUNCIÓN DE BÚSQUEDA EN TIEMPO REAL (IMDb) ---
def buscar_imdb_live(search_term: str):
    if not search_term or len(search_term.strip()) < 2:
        return []
    
    opciones = []
    try:
        q_clean = search_term.strip().lower().replace(" ", "_")
        url = f"https://v3.sg.media-imdb.com/suggestion/x/{q_clean}.json"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        
        items = res.get("d", [])
        for item in items:
            q_type = item.get("qid", "")
            if q_type in ["movie", "tvSeries", "tvMiniSeries", "tvSpecial"]:
                title = item.get("l")
                year = item.get("y", "")
                imdb_id = item.get("id")
                
                i_dict = item.get("i", {})
                poster = i_dict.get("imageUrl", "") if i_dict else ""
                stars = item.get("s", "")
                
                label_type = "📺" if "tv" in q_type else "🎬"
                reparto_txt = f" — {stars[:30]}" if stars else ""
                txt_mostrar = f"{label_type} {title} ({year}){reparto_txt}"
                
                opciones.append((txt_mostrar, {
                    "imdb_id": imdb_id,
                    "nombre": title,
                    "year": year,
                    "tipo": label_type,
                    "poster_url": poster,
                    "elenco": stars
                }))
    except Exception:
        pass
        
    return opciones

# --- FILTRADO ESTRICTO DE TEMPORADAS LANZADAS ---
def obtener_detalles_extra(imdb_id):
    rating = None
    seasons = 1
    try:
        url = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        if res:
            rating = res.get("rating", {}).get("average")
            show_id = res.get("id")
            if show_id:
                url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
                res_s = requests.get(url_seasons, headers=HEADERS, timeout=3).json()
                
                if isinstance(res_s, list):
                    hoy = datetime.now().date()
                    temporadas_emitidas = 0
                    
                    for season in res_s:
                        premier_date_str = season.get("premiereDate")
                        if premier_date_str:
                            try:
                                fecha_estreno = datetime.strptime(premier_date_str, "%Y-%m-%d").date()
                                if fecha_estreno <= hoy:
                                    temporadas_emitidas += 1
                            except ValueError:
                                pass
                    
                    if temporadas_emitidas > 0:
                        seasons = temporadas_emitidas
    except Exception:
        pass
    return rating, seasons

# --- HEADER PRINCIPAL ---
st.markdown("""
<div class="header-container">
    <div class="header-title">🎬 StreamTracker</div>
    <div style="color: #94a3b8; font-size: 0.95rem; margin-top: 4px;">
        Tu catálogo personal de series y películas con seguimiento en tiempo real
    </div>
</div>
""", unsafe_allow_html=True)

# --- DISTRIBUCIÓN PRINCIPAL DE LA PÁGINA (ANCHO COMPLETO) ---
col_lateral, col_principal = st.columns([1, 2.8], gap="large")

# ==========================================
# COLUMNA IZQUIERDA: CONTROLES Y BÚSQUEDA
# ==========================================
with col_lateral:
    st.subheader("🔍 Añadir Contenido")
    
    seleccion = st_searchbox(
        buscar_imdb_live,
        key="imdb_searchbox",
        placeholder="Buscar serie o película..."
    )

    if seleccion:
        st.markdown("---")
        st.markdown(f"#### {seleccion['nombre']} ({seleccion['year']})")
        
        if seleccion.get("poster_url"):
            st.image(seleccion["poster_url"], use_container_width=True)
            
        if seleccion.get("elenco"):
            st.caption(f"👥 **Reparto:** {seleccion['elenco']}")
            
        if st.button("➕ Agregar a mi colección", use_container_width=True, type="primary"):
            with st.spinner("Calculando temporadas emitidas..."):
                rating_imdb, total_seasons = obtener_detalles_extra(seleccion["imdb_id"])
                
                existe = False
                for s in st.session_state.series:
                    if s.get("imdb_id") == seleccion["imdb_id"] or s["serie"].lower() == seleccion["nombre"].lower():
                        s["rating_imdb"] = rating_imdb
                        s["poster_url"] = seleccion["poster_url"]
                        s["temp_totales"] = total_seasons
                        existe = True
                        break
                
                if not existe:
                    st.session_state.series.append({
                        "serie": seleccion["nombre"],
                        "imdb_id": seleccion["imdb_id"],
                        "temp_vista": 1,
                        "temp_totales": total_seasons,
                        "estado": "Viendo",
                        "rating": 5,
                        "rating_imdb": rating_imdb,
                        "poster_url": seleccion["poster_url"],
                        "notas": f"Elenco: {seleccion['elenco']}" if seleccion.get("elenco") else ""
                    })
                
                guardar_datos(st.session_state.series)
                st.success(f"¡{seleccion['nombre']} agregada!")
                st.rerun()

    # Métrica rápida de la colección
    st.markdown("---")
    st.markdown("### 📊 Estadísticas")
    total_titulos = len(st.session_state.series)
    completadas = sum(1 for s in st.session_state.series if s.get("temp_vista", 0) >= s.get("temp_totales", 1))
    
    st.metric("Total en Colección", total_titulos)
    st.metric("Temporadas al día", completadas)

# ==========================================
# COLUMNA DERECHA: GRILLA DE CONTENIDOS (JUSTWATCH STYLE)
# ==========================================
with col_principal:
    st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")
    
    if st.session_state.series:
        # Mostrar las tarjetas en una cuadrícula de 2 columnas
        grid_cols = st.columns(2, gap="medium")
        
        for idx, s in enumerate(st.session_state.series):
            # Asignar a la columna izquierda o derecha según la posición
            col_target = grid_cols[idx % 2]
            
            with col_target:
                # Calculo de progreso de temporadas
                temp_v = int(s.get("temp_vista", 1))
                temp_t = int(s.get("temp_totales", 1))
                progreso = min(temp_v / temp_t, 1.0) if temp_t > 0 else 1.0
                es_completa = temp_v >= temp_t
                
                badge_html = f"<span class='status-badge-completed'>Completada</span>" if es_completa else f"<span class='status-badge-viewing'>Viendo</span>"
                rating_imdb_html = f"<span class='imdb-badge'>IMDb {s['rating_imdb']}</span>" if s.get("rating_imdb") else ""
                
                with st.container():
                    # Formato de tarjeta limpia estilo JustWatch
                    c_img, c_info = st.columns([1, 1.6])
                    
                    with c_img:
                        if s.get("poster_url"):
                            st.image(s["poster_url"], use_container_width=True)
                        else:
                            st.write("🖼️ Sin Imagen")
                            
                    with c_info:
                        st.markdown(f"### {s['serie']}")
                        st.markdown(f"{badge_html} {rating_imdb_html}", unsafe_allow_html=True)
                        st.markdown(f"**Progreso:** Temp. {temp_v} de {temp_t}")
                        st.progress(progreso)
                        st.markdown(f"**Tu Nota:** {'⭐' * int(s.get('rating', 5))}")

                    # Expander para editar información detallada
                    with st.expander("⚙️ Administrar / Editar"):
                        nueva_temp = st.number_input(
                            "Temporada vista:",
                            min_value=0,
                            max_value=50,
                            value=temp_v,
                            key=f"input_temp_{idx}"
                        )
                        nuevo_rating = st.slider("Tu Nota:", 1, 5, int(s.get("rating", 5)), key=f"input_rate_{idx}")
                        
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("💾 Guardar", key=f"btn_save_{idx}", use_container_width=True):
                                st.session_state.series[idx]["temp_vista"] = nueva_temp
                                st.session_state.series[idx]["rating"] = nuevo_rating
                                guardar_datos(st.session_state.series)
                                st.rerun()
                        with b_col2:
                            if st.button("🗑️ Borrar", key=f"btn_del_{idx}", use_container_width=True):
                                st.session_state.series.pop(idx)
                                guardar_datos(st.session_state.series)
                                st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Tu colección está vacía. Utiliza el buscador del panel izquierdo para agregar tu primera serie o película.")
