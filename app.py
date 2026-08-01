import streamlit as st
import requests
import json
import os
from datetime import datetime
from streamlit_searchbox import st_searchbox

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker — IMDb Live",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .main-title {
        color: #f8fafc;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        background-color: #0f172a !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 0.8rem;
    }
    .imdb-badge {
        background-color: #f5c518;
        color: #000000;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        display: inline-block;
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

# --- OBTENCIÓN DE DETALLES Y FILTRADO DE TEMPORADAS DISPONIBLES ---
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
                                # Solo contabiliza si la fecha de estreno ya pasó o es hoy
                                if fecha_estreno <= hoy:
                                    temporadas_emitidas += 1
                            except ValueError:
                                pass
                        elif season.get("number"):
                            # Resguardo si no tiene fecha estipulada pero la temporada ya está emitida/numerada
                            temporadas_emitidas += 1
                    
                    if temporadas_emitidas > 0:
                        seasons = temporadas_emitidas
    except Exception:
        pass
    return rating, seasons

# --- ENCABEZADO ---
st.markdown("<h1 class='main-title'>🎬 StreamTracker Live</h1>", unsafe_allow_html=True)
st.caption("✨ Búsqueda directa en vivo sobre la base de datos de IMDb")

st.divider()

# --- BÚSQUEDA INSTANTÁNEA EN VIVO (LETRA POR LETRA) ---
st.subheader("🔍 Buscar Contenido")

seleccion = st_searchbox(
    buscar_imdb_live,
    key="imdb_searchbox",
    placeholder="Escribe el nombre de la serie o película..."
)

if seleccion:
    col_prev_img, col_prev_info = st.columns([1, 3])
    with col_prev_img:
        if seleccion.get("poster_url"):
            st.image(seleccion["poster_url"], width=110)
        else:
            st.write("🖼️ Sin imagen")
            
    with col_prev_info:
        st.markdown(f"### {seleccion['nombre']} ({seleccion['year']})")
        
        if seleccion.get("elenco"):
            st.caption(f"👥 **Reparto:** {seleccion['elenco']}")
        
        if st.button("➕ Agregar a mi colección", use_container_width=True, type="primary"):
            with st.spinner("Obteniendo detalles de IMDb y calculando temporadas disponibles..."):
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
                st.success(f"¡{seleccion['nombre']} agregada a tu colección!")
                st.rerun()

st.divider()

# --- COLECCIÓN PRINCIPAL ---
st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        estado_icon = "✅" if s.get("estado") == "Completada" else ("▶️" if s.get("estado") == "Viendo" else "⏳")
        titulo_tarjeta = f"{s['serie']} — T{s.get('temp_vista', 1)} de T{s.get('temp_totales', 1)} {estado_icon}"
        
        with st.expander(titulo_tarjeta, expanded=False):
            col_img, col_detalles = st.columns([1.2, 2.8])
            
            with col_img:
                if s.get("poster_url"):
                    st.image(s["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️ Sin portada")
                    
            with col_detalles:
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    if s.get("rating_imdb"):
                        st.markdown(f"<span class='imdb-badge'>IMDb {s['rating_imdb']} / 10</span>", unsafe_allow_html=True)
                    else:
                        st.caption("IMDb: N/A")
                with col_r2:
                    st.markdown(f"**Tu Nota:** {'⭐' * int(s.get('rating', 5))}")

                if s.get("notas"):
                    st.caption(f"📝 *{s['notas']}*")

                st.divider()
                
                temp_vista_nueva = st.number_input(
                    "Última temporada vista:",
                    min_value=0,
                    max_value=50,
                    value=int(s.get("temp_vista", 1)),
                    key=f"temp_input_{idx}"
                )
                
                rating_nuevo = st.slider("Tu calificación personal:", 1, 5, int(s.get("rating", 5)), key=f"rate_{idx}")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Guardar", key=f"save_{idx}", use_container_width=True):
                        st.session_state.series[idx]["temp_vista"] = temp_vista_nueva
                        st.session_state.series[idx]["rating"] = rating_nuevo
                        guardar_datos(st.session_state.series)
                        st.success("¡Guardado!")
                        st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Eliminar", key=f"del_{idx}", use_container_width=True):
                        st.session_state.series.pop(idx)
                        guardar_datos(st.session_state.series)
                        st.rerun()
else:
    st.info("Tu colección está vacía. ¡Empieza a escribir en el buscador de arriba para agregar contenido!")
