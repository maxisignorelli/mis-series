import streamlit as st
import requests
import json
import os

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(
    page_title="StreamTracker",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
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

# --- BÚSQUEDA HÍBRIDA ROBUSTA (TMDB + TVMAZE REST BACKUP) ---
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

def buscar_series_api(query):
    if not query or len(query.strip()) < 2:
        return []
    
    resultados = []
    
    # 1. Intentar con TVMaze (Respuesta garantizada y sin límites)
    try:
        url_tvmaze = f"https://api.tvmaze.com/search/shows?q={query}"
        res_tv = requests.get(url_tvmaze, headers=HEADERS, timeout=5).json()
        for item in res_tv[:5]:
            show = item.get("show", {})
            nombre = show.get("name")
            year = show.get("premiered", "")[:4] if show.get("premiered") else ""
            img_dict = show.get("image") or {}
            poster = img_dict.get("medium") or img_dict.get("original") or ""
            summary = show.get("summary", "").replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "")
            network = show.get("network", {}) or show.get("webChannel", {})
            plat = network.get("name") if network else "Streaming"
            
            resultados.append({
                "label": f"{nombre} ({year})" if year else nombre,
                "nombre": nombre,
                "plataforma": plat,
                "poster_url": poster,
                "sinopsis": summary,
                "tvmaze_id": show.get("id")
            })
    except Exception as e:
        pass
        
    return resultados

def obtener_temporadas_tvmaze(tvmaze_id):
    try:
        url = f"https://api.tvmaze.com/shows/{tvmaze_id}/seasons"
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        return len(res) if isinstance(res, list) and len(res) > 0 else 1
    except:
        return 1

# --- INTERFAZ DE LA APP ---
st.title("🎬 StreamTracker")
st.caption("✨ Tu panel personal e inteligente de series")

st.divider()

# --- BÚSQUEDA Y AUTOCOMPLETADO ---
st.subheader("🔍 Agregar nueva serie")

query = st.text_input("Escribe el nombre de la serie:", placeholder="Ej: Slow Horses, Breaking Bad, The Bear...")

if query and len(query.strip()) >= 2:
    with st.spinner("Buscando en la base de datos..."):
        sugerencias = buscar_series_api(query.strip())
    
    if sugerencias:
        opciones = {s["label"]: s for s in sugerencias}
        seleccion = st.selectbox("🎯 Resultados encontrados:", list(opciones.keys()))
        
        if seleccion:
            serie_sel = opciones[seleccion]
            
            if st.button(f"✨ Cargar '{serie_sel['nombre']}' a mi lista", use_container_width=True, type="primary"):
                with st.spinner("Obteniendo temporadas y portada..."):
                    temp_totales = obtener_temporadas_tvmaze(serie_sel["tvmaze_id"])
                    
                    # Verificar duplicado
                    existe = False
                    for s in st.session_state.series:
                        if s["serie"].lower() == serie_sel["nombre"].lower():
                            s["temp_totales"] = temp_totales
                            s["plataforma"] = serie_sel["plataforma"]
                            if serie_sel["poster_url"]:
                                s["poster_url"] = serie_sel["poster_url"]
                            existe = True
                            break
                    
                    if not existe:
                        st.session_state.series.append({
                            "serie": serie_sel["nombre"],
                            "plataforma": serie_sel["plataforma"],
                            "temp_vista": 0,
                            "temp_totales": temp_totales,
                            "estado": "Viendo",
                            "rating": 5,
                            "poster_url": serie_sel["poster_url"],
                            "notas": serie_sel["sinopsis"][:150] + "..." if serie_sel["sinopsis"] else ""
                        })
                    
                    guardar_datos(st.session_state.series)
                    st.success(f"¡{serie_sel['nombre']} agregada con éxito!")
                    st.rerun()
    else:
        st.info("No se encontraron series con ese nombre. Intenta con otra palabra.")

st.divider()

# --- ALERTAS DE PENDIENTES ---
pendientes = [s for s in st.session_state.series if s.get("temp_totales", 1) > s.get("temp_vista", 0)]

if pendientes:
    st.subheader("🔔 Temporadas Pendientes por Ver")
    for s in pendientes:
        diferencia = s["temp_totales"] - s["temp_vista"]
        with st.container():
            col_a1, col_a2 = st.columns([1, 4])
            with col_a1:
                if s.get("poster_url"):
                    st.image(s["poster_url"], width=70)
            with col_a2:
                st.warning(
                    f"🍿 **{s['serie']}** ({s['plataforma']})\n\n"
                    f"Viste **T{s['temp_vista']}**, pero ya hay **{s['temp_totales']} temporada(s)** disponibles "
                    f"(*{diferencia} pendiente(s)*)."
                )

st.divider()

# --- COLECCIÓN PERSONAL ---
st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        with st.expander(f"🎬 **{s['serie']}** — Vista T{s['temp_vista']} de T{s['temp_totales']}", expanded=False):
            col_img, col_detalles = st.columns([1, 2])
            
            with col_img:
                if s.get("poster_url"):
                    st.image(s["poster_url"], use_container_width=True)
                else:
                    st.write("🖼️ Sin imagen")
                    
            with col_detalles:
                st.markdown(f"**📺 Plataforma:** {s.get('plataforma', 'N/A')}")
                
                temp_vista_nueva = st.number_input(
                    "Temporada que ya viste:",
                    min_value=0,
                    max_value=int(s.get("temp_totales", 50)),
                    value=int(s.get("temp_vista", 0)),
                    key=f"temp_input_{idx}"
                )
                
                estado_nuevo = st.selectbox(
                    "Estado:",
                    ["Viendo", "Pendiente nueva temporada", "Completada", "Abandonada"],
                    index=["Viendo", "Pendiente nueva temporada", "Completada", "Abandonada"].index(s.get("estado", "Viendo")),
                    key=f"estado_input_{idx}"
                )
                
                rating_nuevo = st.slider("Calificación:", 1, 5, int(s.get("rating", 5)), key=f"rate_{idx}")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Guardar cambios", key=f"save_{idx}", use_container_width=True):
                        st.session_state.series[idx]["temp_vista"] = temp_vista_nueva
                        st.session_state.series[idx]["estado"] = estado_nuevo
                        st.session_state.series[idx]["rating"] = rating_nuevo
                        guardar_datos(st.session_state.series)
                        st.success("¡Actualizado!")
                        st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Eliminar", key=f"del_{idx}", use_container_width=True):
                        st.session_state.series.pop(idx)
                        guardar_datos(st.session_state.series)
                        st.rerun()
else:
    st.info("Aún no tienes series en tu lista. ¡Usa el buscador de arriba para agregar la primera!")
