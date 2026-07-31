import streamlit as st
import requests
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker — IMDb Search",
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
    .logo-img {
        height: 24px;
        vertical-align: middle;
        margin-right: 6px;
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
        except:
            return []
    return []

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- BÚSQUEDA DIRECTA EN IMDb ---
def buscar_en_imdb(query):
    if not query or len(query.strip()) < 2:
        return []
    
    resultados = []
    try:
        # Sugerencias públicas en tiempo real de IMDb
        q_clean = query.strip().lower().replace(" ", "_")
        url = f"https://v3.sg.media-imdb.com/suggestion/x/{q_clean}.json"
        res = requests.get(url, headers=HEADERS, timeout=4).json()
        
        items = res.get("d", [])
        for item in items:
            # Filtrar solo películas (movie, feature) y series (tvSeries, tvMiniSeries)
            q_type = item.get("qid", "")
            if q_type in ["movie", "tvSeries", "tvMiniSeries", "tvSpecial"]:
                imdb_id = item.get("id")
                title = item.get("l")
                year = item.get("y", "")
                
                # Imagen de portada IMDb
                i_dict = item.get("i", {})
                poster = i_dict.get("imageUrl", "") if i_dict else ""
                
                # Reparto principal o directores
                stars = item.get("s", "")
                
                # Obtener calificación y detalles vía ID de IMDb
                rating_imdb, total_seasons = obtener_detalles_imdb(imdb_id)
                
                label_type = "📺 Serie" if "tv" in q_type else "🎬 Película"
                imdb_str = f"⭐ {rating_imdb}" if rating_imdb else "N/A"
                
                label = f"{label_type}: {title} ({year}) — IMDb: {imdb_str}"
                
                resultados.append({
                    "label": label,
                    "imdb_id": imdb_id,
                    "nombre": title,
                    "year": year,
                    "tipo": label_type,
                    "poster_url": poster,
                    "rating_imdb": rating_imdb,
                    "total_seasons": total_seasons,
                    "elenco": stars
                })
    except Exception:
        pass
        
    return resultados

def obtener_detalles_imdb(imdb_id):
    rating = None
    seasons = 1
    try:
        # Consulta complementaria a base IMDb para obtener rating y temporadas
        url = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        if res:
            rating = res.get("rating", {}).get("average")
            show_id = res.get("id")
            if show_id:
                url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
                res_s = requests.get(url_seasons, headers=HEADERS, timeout=3).json()
                if isinstance(res_s, list):
                    seasons = len(res_s)
    except Exception:
        pass
    return rating, seasons

# --- ENCABEZADO ---
st.markdown("<h1 class='main-title'>🎬 StreamTracker — IMDb Search</h1>", unsafe_allow_html=True)
st.caption("✨ Búsqueda directa sobre la base de datos de IMDb")

st.divider()

# --- BÚSQUEDA INSTANTÁNEA IMDb ---
st.subheader("🔍 Buscar Contenido en IMDb")

query = st.text_input(
    "Escribe para buscar directamente en IMDb:", 
    placeholder="Empieza a escribir (ej: Harry Potter, Slow Horses, El Encargado, Severance)...",
    key="search_input"
)

if query and len(query.strip()) >= 2:
    sugerencias = buscar_en_imdb(query.strip())
    
    if sugerencias:
        opciones_dict = {s["label"]: s for s in sugerencias}
        
        seleccion = st.selectbox(
            f"👇 Coincidencias en IMDb ({len(sugerencias)} resultados):", 
            list(opciones_dict.keys()),
            key="select_sugerencia"
        )
        
        if seleccion:
            item_sel = opciones_dict[seleccion]
            
            col_prev_img, col_prev_info = st.columns([1, 3])
            with col_prev_img:
                if item_sel["poster_url"]:
                    st.image(item_sel["poster_url"], width=110)
                else:
                    st.write("🖼️ Sin imagen")
            with col_prev_info:
                st.markdown(f"### {item_sel['nombre']} ({item_sel['year']})")
                
                if item_sel.get("rating_imdb"):
                    st.markdown(f"<span class='imdb-badge'>IMDb {item_sel['rating_imdb']} / 10</span>", unsafe_allow_html=True)
                else:
                    st.caption("IMDb Rating: No disponible")
                
                if item_sel.get("elenco"):
                    st.caption(f"👥 **Reparto:** {item_sel['elenco']}")
                
                if st.button("➕ Agregar a mi colección", use_container_width=True, type="primary"):
                    existe = False
                    for s in st.session_state.series:
                        if s.get("imdb_id") == item_sel["imdb_id"] or s["serie"].lower() == item_sel["nombre"].lower():
                            s["rating_imdb"] = item_sel["rating_imdb"]
                            s["poster_url"] = item_sel["poster_url"]
                            existe = True
                            break
                    
                    if not existe:
                        st.session_state.series.append({
                            "serie": item_sel["nombre"],
                            "imdb_id": item_sel["imdb_id"],
                            "temp_vista": 1,
                            "temp_totales": item_sel["total_seasons"],
                            "estado": "Viendo",
                            "rating": 5,
                            "rating_imdb": item_sel["rating_imdb"],
                            "poster_url": item_sel["poster_url"],
                            "notas": f"Elenco: {item_sel['elenco']}" if item_sel.get("elenco") else ""
                        })
                    
                    guardar_datos(st.session_state.series)
                    st.success(f"¡{item_sel['nombre']} guardada correctamente!")
                    st.rerun()
    else:
        st.info("Sin coincidencias en IMDb. Intenta con otra palabra.")

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
    st.info("Tu colección está vacía. ¡Busca cualquier serie o película en IMDb para comenzar!")
