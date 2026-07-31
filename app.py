import streamlit as st
import requests
import json
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS CUSTOM (INTERFAZ MÁS LINDA Y FRIENDLY) ---
st.markdown("""
<style>
    /* Estilo general y tipografía */
    .stApp {
        background-color: #0e1117;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Estilo para las tarjetas de series */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div[data-testid="stVerticalBlock"] {
        border-radius: 12px;
    }
    
    /* Badges de estado */
    .badge-pend {
        background-color: #ff9800;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-ok {
        background-color: #4caf50;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    /* Botones más llamativos */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# --- MANEJO DE DATOS LOCALES ---
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

# --- CONEXIÓN A TMDB API (Sugerencias y Datos Automáticos) ---
TMDB_API_KEY = "1b88e1518171966d51065757a2f58ec0"  # Clave pública de consulta

def buscar_series_tmdb(query):
    if not query or len(query) < 2:
        return []
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={query}&language=es-ES"
    try:
        res = requests.get(url).json()
        return res.get("results", [])[:5]  # Devolver las primeras 5 sugerencias
    except:
        return []

def obtener_detalle_serie(tmdb_id):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=es-ES&append_to_response=watch/providers"
    try:
        res = requests.get(url).json()
        
        # Extraer plataformas (ej. Netflix, Apple TV+, etc.)
        providers = res.get("watch/providers", {}).get("results", {}).get("AR", {}).get("flatrate", [])
        plataformas = [p["provider_name"] for p in providers] if providers else ["No especificada"]
        
        poster_path = res.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        
        return {
            "nombre": res.get("name"),
            "temp_totales": res.get("number_of_seasons", 1),
            "plataforma": ", ".join(plataformas),
            "poster_url": poster_url,
            "sinopsis": res.get("overview", "")
        }
    except:
        return None

# --- ENCABEZADO Y HEADER ---
st.title("🎬 StreamTracker")
st.caption("✨ Tu panel personal inteligente de series y temporadas")

st.divider()

# --- BUSCADOR Y AUTOCOMPLETADO INTELIGENTE ---
st.subheader("🔍 Agregar nueva serie")

query = st.text_input("Comienza a escribir el nombre de la serie...", placeholder="Ej: Slow Horses, Breaking Bad, The Bear...")

if query:
    sugerencias = buscar_series_tmdb(query)
    
    if sugerencias:
        opciones = {f"{s['name']} ({s.get('first_air_date', 'N/A')[:4]})": s for s in sugerencias}
        seleccion = st.selectbox("🎯 Coincidencias encontradas (selecciona una):", list(opciones.keys()))
        
        if seleccion:
            serie_tmdb = opciones[seleccion]
            
            if st.button(f"✨ Cargar información de '{serie_tmdb['name']}'", use_container_width=True, type="primary"):
                with st.spinner("Buscando datos, temporadas y plataformas..."):
                    detalles = obtener_detalle_serie(serie_tmdb["id"])
                    
                    if detalles:
                        # Guardar o actualizar
                        existe = False
                        for s in st.session_state.series:
                            if s["serie"].lower() == detalles["nombre"].lower():
                                s["temp_totales"] = detalles["temp_totales"]
                                s["plataforma"] = detalles["plataforma"]
                                s["poster_url"] = detalles["poster_url"]
                                existe = True
                                break
                        
                        if not existe:
                            st.session_state.series.append({
                                "serie": detalles["nombre"],
                                "plataforma": detalles["plataforma"],
                                "temp_vista": 0, # Empieza en 0 para configurar
                                "temp_totales": detalles["temp_totales"],
                                "estado": "Viendo",
                                "rating": 5,
                                "poster_url": detalles["poster_url"],
                                "notas": detalles["sinopsis"][:120] + "..." if detalles["sinopsis"] else ""
                            })
                        
                        guardar_datos(st.session_state.series)
                        st.success(f"¡{detalles['nombre']} agregada automáticamente!")
                        st.rerun()

st.divider()

# --- ALERTAS DE TEMPORADAS PENDIENTES ---
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
                    f"Viste **T{s['temp_vista']}**, pero ya salieron **{s['temp_totales']} temporadas** "
                    f"(*{diferencia} pendiente(s)*)."
                )

st.divider()

# --- MI COLECCIÓN ---
st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        with st.expander(f"🎬 **{s['serie']}** — T{s['temp_vista']}/{s['temp_totales']}", expanded=False):
            col_img, col_detalles = st.columns([1, 2])
            
            with col_img:
                if s.get("poster_url"):
                    st.image(s["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️ Sin imagen")
                    
            with col_detalles:
                st.markdown(f"**📺 Plataforma:** {s.get('plataforma', 'N/A')}")
                
                # Control rápido para actualizar temporada vista
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
