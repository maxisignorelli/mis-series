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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- BÚSQUEDA MULTI-FUENTE A PRUEBA DE BLOQUEOS ---
def ejecutar_busqueda_sin_bloqueo(query_text: str):
    if not query_text or len(query_text.strip()) < 2:
        return []
    
    opciones = []
    q_clean = query_text.strip()
    
    # Intento 1: API Directa de TVMaze / IMDb (Libre y rápida)
    try:
        url_tv = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(q_clean)}"
        res_tv = requests.get(url_tv, headers=HEADERS, timeout=4)
        
        if res_tv.status_code == 200:
            shows = res_tv.json()
            for item in shows[:6]:
                show = item.get("show", {})
                nombre = show.get("name")
                imdb_id = show.get("externals", {}).get("imdb")
                rating = show.get("rating", {}).get("average")
                
                premiered = show.get("premiered", "")
                year = premiered.split("-")[0] if premiered else ""
                
                image_dict = show.get("image") or {}
                poster = image_dict.get("medium") or image_dict.get("original") or ""
                
                if nombre:
                    opciones.append({
                        "nombre": nombre,
                        "imdb_id": imdb_id,
                        "year": year,
                        "tipo": "📺 Serie",
                        "poster_url": poster,
                        "rating_imdb": rating,
                        "temp_totales": 1
                    })
    except Exception:
        pass

    # Intento 2: API Abierta OMDb pública de respaldo para Películas si no encontró suficientes
    if len(opciones) < 3:
        try:
            url_omdb = f"https://www.omdbapi.com/?apikey=trilogy&s={urllib.parse.quote(q_clean)}"
            res_omdb = requests.get(url_omdb, headers=HEADERS, timeout=4)
            if res_omdb.status_code == 200:
                data = res_omdb.json()
                if data.get("Response") == "True":
                    for item in data.get("Search", [])[:5]:
                        imdb_id = item.get("imdbID")
                        nombre = item.get("Title")
                        year = item.get("Year", "")
                        type_str = "🎬 Película" if item.get("Type") == "movie" else "📺 Serie"
                        poster = item.get("Poster")
                        if poster == "N/A":
                            poster = ""
                        
                        # Evitar duplicados
                        if not any(o.get("imdb_id") == imdb_id for o in opciones):
                            opciones.append({
                                "nombre": nombre,
                                "imdb_id": imdb_id,
                                "year": year,
                                "tipo": type_str,
                                "poster_url": poster,
                                "rating_imdb": None,
                                "temp_totales": 1
                            })
        except Exception:
            pass

    return opciones

def obtener_rating_imdb_faltante(imdb_id):
    if not imdb_id:
        return None
    try:
        url = f"https://www.omdbapi.com/?apikey=trilogy&i={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        if res.get("Response") == "True":
            return res.get("imdbRating")
    except Exception:
        pass
    return None

# --- ENCABEZADO ---
st.markdown("<h1 class='main-title'>🎬 StreamTracker Live</h1>", unsafe_allow_html=True)
st.caption("✨ Catálogo universal con puntuaciones reales de IMDb")

st.divider()

# --- INTERFAZ DE BÚSQUEDA ---
st.subheader("🔍 Buscar Contenido")

query_input = st.text_input("Escribe el nombre del título (ej: Harry Potter, The Bear, Slow Horses):", key="search_query_input")

if query_input:
    resultados = ejecutar_busqueda_sin_bloqueo(query_input)
    
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
                    if item.get("rating_imdb"):
                        st.markdown(f"<span class='imdb-badge'>IMDb {item['rating_imdb']}</span>", unsafe_allow_html=True)
                        
                with col_b:
                    if st.button("➕ Agregar", key=f"btn_add_{idx}", type="primary"):
                        with st.spinner("Guardando en tu colección..."):
                            rating_final = item.get("rating_imdb")
                            if not rating_final and item.get("imdb_id"):
                                rating_final = obtener_rating_imdb_faltante(item["imdb_id"])
                            
                            existe = False
                            for s in st.session_state.series:
                                if (item["imdb_id"] and s.get("imdb_id") == item["imdb_id"]) or s["serie"].lower() == item["nombre"].lower():
                                    s["rating_imdb"] = rating_final
                                    s["poster_url"] = item["poster_url"]
                                    existe = True
                                    break
                            
                            if not existe:
                                st.session_state.series.append({
                                    "serie": item["nombre"],
                                    "imdb_id": item["imdb_id"],
                                    "temp_vista": 1,
                                    "temp_totales": item.get("temp_totales", 1),
                                    "estado": "Viendo",
                                    "rating": 5,
                                    "rating_imdb": rating_final,
                                    "poster_url": item["poster_url"],
                                    "notas": ""
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
