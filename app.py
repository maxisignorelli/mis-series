import streamlit as st
import requests
import json
import os
from datetime import datetime
from streamlit_searchbox import st_searchbox

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker — Estilo JustWatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stApp {
        background: #0b0e14;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
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
    
    .imdb-badge {
        background-color: #f5c518;
        color: #000000;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    
    .genre-tag {
        background-color: #1e293b;
        color: #cbd5e1;
        border: 1px solid #334155;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        margin-right: 4px;
        display: inline-block;
    }

    .status-tag {
        background-color: #0284c7;
        color: white;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
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
    
    div[data-testid="stExpander"] {
        background-color: #151c28 !important;
        border: 1px solid #232d3f !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "series_data.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- OBTENER DETALLES COMPLETOS ---
def obtener_detalles_completos(imdb_id):
    info = {
        "rating_imdb": None,
        "temp_totales": 1,
        "generos": [],
        "estado_serie": "Desconocido",
        "primer_episodio": "N/A",
        "ultimo_episodio": "N/A",
        "actores": [],
        "desglose_temporadas": []
    }
    
    if not imdb_id:
        return info

    try:
        url = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=4).json()
        
        if res:
            info["rating_imdb"] = res.get("rating", {}).get("average")
            info["generos"] = res.get("genres", [])
            
            status_raw = res.get("status", "")
            if status_raw == "Ended":
                info["estado_serie"] = "Finalizada 🏁"
            elif status_raw == "Running":
                info["estado_serie"] = "En Emisión 📺"
            elif status_raw == "To Be Determined":
                info["estado_serie"] = "En Pausa / Pendiente ⏳"
            else:
                info["estado_serie"] = status_raw or "En Emisión"

            show_id = res.get("id")
            
            if show_id:
                # Cast
                url_cast = f"https://api.tvmaze.com/shows/{show_id}/cast"
                res_cast = requests.get(url_cast, headers=HEADERS, timeout=4).json()
                if isinstance(res_cast, list):
                    info["actores"] = [c["person"]["name"] for c in res_cast[:5] if "person" in c]
                
                # Temporadas y Episodios
                url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
                res_s = requests.get(url_seasons, headers=HEADERS, timeout=4).json()
                
                url_episodes = f"https://api.tvmaze.com/shows/{show_id}/episodes"
                res_ep = requests.get(url_episodes, headers=HEADERS, timeout=4).json()
                
                hoy = datetime.now().date()
                
                if isinstance(res_ep, list) and len(res_ep) > 0:
                    eps_emitidos = []
                    for ep in res_ep:
                        a_date = ep.get("airdate")
                        if a_date:
                            try:
                                f_ep = datetime.strptime(a_date, "%Y-%m-%d").date()
                                if f_ep <= hoy:
                                    eps_emitidos.append(ep)
                            except ValueError:
                                pass
                    
                    if eps_emitidos:
                        info["primer_episodio"] = eps_emitidos[0].get("airdate", "N/A")
                        info["ultimo_episodio"] = eps_emitidos[-1].get("airdate", "N/A")
                
                if isinstance(res_s, list):
                    temp_emitidas_count = 0
                    desglose = []
                    
                    for season in res_s:
                        p_date = season.get("premiereDate")
                        es_emitida = False
                        if p_date:
                            try:
                                f_prem = datetime.strptime(p_date, "%Y-%m-%d").date()
                                if f_prem <= hoy:
                                    es_emitida = True
                            except ValueError:
                                pass
                        
                        if es_emitida:
                            temp_emitidas_count += 1
                            num_temp = season.get("number", temp_emitidas_count)
                            eps_temp = [e for e in res_ep if e.get("season") == num_temp and e.get("airdate") and datetime.strptime(e.get("airdate"), "%Y-%m-%d").date() <= hoy] if isinstance(res_ep, list) else []
                            
                            desglose.append({
                                "temporada": f"Temporada {num_temp}",
                                "episodios": len(eps_temp) if eps_temp else (season.get("episodeOrder") or "N/A"),
                                "rating": season.get("rating", {}).get("average") or info["rating_imdb"] or "N/A"
                            })
                    
                    info["temp_totales"] = max(temp_emitidas_count, 1)
                    info["desglose_temporadas"] = desglose
    except Exception:
        pass
        
    return info

# --- CARGAR/AUTO-COMPLETAR DATOS LOCALES ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
                modificado = False
                for s in datos:
                    if "estado_serie" not in s or s.get("primer_episodio") in [None, "N/A"]:
                        detalles = obtener_detalles_completos(s.get("imdb_id"))
                        s.update(detalles)
                        modificado = True
                if modificado:
                    guardar_datos(datos)
                return datos
        except Exception:
            return []
    return []

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

# --- BÚSQUEDA IMDB LIVE ---
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

# --- HEADER PRINCIPAL ---
st.markdown("""
<div class="header-container">
    <div class="header-title">🎬 StreamTracker</div>
    <div style="color: #94a3b8; font-size: 0.95rem; margin-top: 4px;">
        Tu catálogo personal interactivo
    </div>
</div>
""", unsafe_allow_html=True)

col_lateral, col_principal = st.columns([1, 2.8], gap="large")

# ==========================================
# COLUMNA IZQUIERDA: BÚSQUEDA
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
            
        if st.button("➕ Agregar a mi colección", use_container_width=True, type="primary"):
            with st.spinner("Cargando información completa..."):
                detalles = obtener_detalles_completos(seleccion["imdb_id"])
                
                existe = False
                for s in st.session_state.series:
                    if s.get("imdb_id") == seleccion["imdb_id"] or s["serie"].lower() == seleccion["nombre"].lower():
                        s.update(detalles)
                        s["poster_url"] = seleccion["poster_url"]
                        existe = True
                        break
                
                if not existe:
                    nueva_serie = {
                        "serie": seleccion["nombre"],
                        "imdb_id": seleccion["imdb_id"],
                        "temp_vista": 1,
                        "rating": 8,
                        "poster_url": seleccion["poster_url"],
                    }
                    nueva_serie.update(detalles)
                    st.session_state.series.append(nueva_serie)
                
                guardar_datos(st.session_state.series)
                st.success(f"¡{seleccion['nombre']} agregada!")
                st.rerun()

    st.markdown("---")
    st.metric("Total en Colección", len(st.session_state.series))

# ==========================================
# COLUMNA DERECHA: TARJETAS EN COLECCIÓN
# ==========================================
with col_principal:
    st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")
    
    if st.session_state.series:
        grid_cols = st.columns(2, gap="medium")
        
        for idx, s in enumerate(st.session_state.series):
            col_target = grid_cols[idx % 2]
            
            with col_target:
                temp_v = int(s.get("temp_vista", 1))
                temp_t = int(s.get("temp_totales", 1))
                progreso = min(temp_v / temp_t, 1.0) if temp_t > 0 else 1.0
                es_completa = temp_v >= temp_t
                
                badge_html = f"<span class='status-badge-completed'>Completada</span>" if es_completa else f"<span class='status-badge-viewing'>Viendo</span>"
                rating_imdb_html = f"<span class='imdb-badge'>IMDb {s['rating_imdb']}</span>" if s.get("rating_imdb") else ""
                mi_nota = int(s.get("rating", 8))
                
                with st.container():
                    c_img, c_info = st.columns([1, 1.5])
                    
                    with c_img:
                        if s.get("poster_url"):
                            st.image(s["poster_url"], use_container_width=True)
                        else:
                            st.write("🖼️ Sin Imagen")
                            
                    with c_info:
                        st.markdown(f"### {s['serie']}")
                        st.markdown(f"{badge_html} {rating_imdb_html}", unsafe_allow_html=True)
                        
                        if s.get("generos"):
                            generos_html = "".join([f"<span class='genre-tag'>{g}</span>" for g in s["generos"]])
                            st.markdown(f"<div style='margin-top: 6px;'>{generos_html}</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"**Progreso:** Temp. {temp_v} de {temp_t}")
                        st.progress(progreso)
                        st.markdown(f"**Tu Nota:** ⭐ **{mi_nota}/10**")

                    # Expander con detalles
                    with st.expander("ℹ️ Ver Detalle y Administrar"):
                        st.markdown(f"**Estado:** <span class='status-tag'>{s.get('estado_serie', 'N/A')}</span>", unsafe_allow_html=True)
                        st.markdown(f"📅 **Primer Episodio:** `{s.get('primer_episodio', 'N/A')}`")
                        st.markdown(f"📅 **Último Episodio:** `{s.get('ultimo_episodio', 'N/A')}`")
                        
                        if s.get("actores"):
                            st.markdown(f"🎭 **Actores Principales:** {', '.join(s['actores'])}")
                        
                        st.divider()
                        
                        # Desglose de Temporadas
                        st.markdown("##### 📚 Desglose por Temporada")
                        desglose = s.get("desglose_temporadas", [])
                        if desglose:
                            st.dataframe(
                                desglose,
                                column_config={
                                    "temporada": "Temporada",
                                    "episodios": "Capítulos",
                                    "rating": "Nota IMDb"
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.caption("Sin desglose disponible.")
                            
                        st.divider()
                        
                        # CALIFICACIÓN EN ESTRELLAS (1 a 10)
                        st.markdown("##### ⭐ Tu Calificación Personal")
                        
                        idx_defecto = max(0, min(mi_nota - 1, 9))
                        calificacion_seleccionada = st.selectbox(
                            "Puntuación (1 al 10):",
                            options=list(range(1, 11)),
                            format_func=lambda x: f"{'⭐' * x} ({x}/10)",
                            index=idx_defecto,
                            key=f"select_rating_{idx}"
                        )
                        
                        nueva_temp = st.number_input(
                            "Última Temporada Vista:",
                            min_value=0,
                            max_value=50,
                            value=temp_v,
                            key=f"input_temp_{idx}"
                        )
                        
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("💾 Guardar Cambios", key=f"btn_save_{idx}", use_container_width=True):
                                st.session_state.series[idx]["temp_vista"] = nueva_temp
                                st.session_state.series[idx]["rating"] = calificacion_seleccionada
                                guardar_datos(st.session_state.series)
                                st.success("¡Guardado!")
                                st.rerun()
                        with b_col2:
                            if st.button("🗑️ Eliminar Serie", key=f"btn_del_{idx}", use_container_width=True):
                                st.session_state.series.pop(idx)
                                guardar_datos(st.session_state.series)
                                st.rerun()
                                
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Tu colección está vacía.")
