import streamlit as st
import requests
import json
import os
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker Live",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS ---
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
    .result-card {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        border: 1px solid #334155;
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

TMDB_KEY = "15d2ea6d0dc1d476efb2532d8b1b513e"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def ejecutar_busqueda_tmdb(query_text: str):
    if not query_text or len(query_text.strip()) < 2:
        return []
    
    opciones = []
    try:
        q_clean = urllib.parse.quote(query_text.strip())
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={q_clean}&language=es-AR&region=AR&page=1&include_adult=false"
        
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            for item in results[:6]:
                media_type = item.get("media_type")
                if media_type in ["tv", "movie"]:
                    title_display = item.get("title") or item.get("name") or item.get("original_title") or item.get("original_name")
                    original_title = item.get("original_title") or item.get("original_name") or title_display
                    
                    release_date = item.get("release_date") or item.get("first_air_date") or ""
                    year = release_date.split("-")[0] if release_date else ""
                    
                    poster_path = item.get("poster_path")
                    poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
                    
                    tmdb_id = item.get("id")
                    label_type = "📺 Serie" if media_type == "tv" else "🎬 Película"
                    
                    opciones.append({
                        "tmdb_id": tmdb_id,
                        "media_type": media_type,
                        "nombre": title_display,
                        "original_title": original_title,
                        "year": year,
                        "tipo": label_type,
                        "poster_url": poster
                    })
    except Exception:
        pass
        
    return opciones

def obtener_detalles_imdb(tmdb_id, media_type):
    imdb_id = None
    rating = None
    seasons = 1
    
    try:
        url_ext = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_KEY}"
        res_ext = requests.get(url_ext, headers=HEADERS, timeout=4).json()
        imdb_id = res_ext.get("imdb_id")
        
        if media_type == "tv":
            url_detail = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_KEY}"
            res_det = requests.get(url_detail, headers=HEADERS, timeout=4).json()
            seasons = res_det.get("number_of_seasons", 1)
            
        if imdb_id:
            url_maze = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
            res_maze = requests.get(url_maze, headers=HEADERS, timeout=4).json()
            if res_maze and "rating" in res_maze:
                rating = res_maze.get("rating", {}).get("average")
    except Exception:
        pass
        
    return imdb_id, rating, seasons

# --- ENCABEZADO ---
st.markdown("<h1 class='main-title'>🎬 StreamTracker Live</h1>", unsafe_allow_html=True)
st.caption("✨ Títulos comercializados en Argentina + Notas oficiales IMDb")

st.divider()

# --- INTERFAZ DE BÚSQUEDA NATIVA ---
st.subheader("🔍 Buscar Contenido")

query_input = st.text_input("Escribe el nombre del título (ej: The Bear, Slow Horses, Harry Potter):", key="search_query_input")

if query_input:
    resultados = ejecutar_busqueda_tmdb(query_input)
    
    if resultados:
        st.write(f"**Resultados para:** *{query_input}*")
        
        for idx, item in enumerate(resultados):
            with st.container():
                col_p, col_i, col_b = st.columns([1, 2.5, 1.5])
                
                with col_p:
                    if item["poster_url"]:
                        st.image(item["poster_url"], width=75)
                    else:
                        st.write("🖼️ Sin imagen")
                        
                with col_i:
                    year_str = f" ({item['year']})" if item['year'] else ""
                    st.markdown(f"**{item['nombre']}**{year_str}")
                    st.caption(f"{item['tipo']}")
                    if item['original_title'] != item['nombre']:
                        st.caption(f"Original: *{item['original_title']}*")
                        
                with col_b:
                    if st.button("➕ Agregar", key=f"btn_add_{item['tmdb_id']}_{idx}", type="primary"):
                        with st.spinner("Obteniendo calificación..."):
                            imdb_id, rating_imdb, total_seasons = obtener_detalles_imdb(
                                item["tmdb_id"], 
                                item["media_type"]
                            )
                            
                            existe = False
                            for s in st.session_state.series:
                                if (imdb_id and s.get("imdb_id") == imdb_id) or s["serie"].lower() == item["nombre"].lower():
                                    s["rating_imdb"] = rating_imdb
                                    s["poster_url"] = item["poster_url"]
                                    existe = True
                                    break
                            
                            if not existe:
                                st.session_state.series.append({
                                    "serie": item["nombre"],
                                    "imdb_id": imdb_id,
                                    "temp_vista": 1,
                                    "temp_totales": total_seasons,
                                    "estado": "Viendo",
                                    "rating": 5,
                                    "rating_imdb": rating_imdb,
                                    "poster_url": item["poster_url"],
                                    "notas": f"Original: {item['original_title']}" if item.get("original_title") != item["nombre"] else ""
                                })
                            
                            guardar_datos(st.session_state.series)
                            st.success(f"¡Agregada!")
                            st.rerun()
                st.divider()
    else:
        st.warning("No se encontraron resultados para esta búsqueda.")

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
    st.info("Tu colección está vacía. Escribe arriba en la búsqueda para añadir títulos.")
