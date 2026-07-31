import streamlit as st
import requests
import json
import os
from datetime import datetime

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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- BÚSQUEDA Y FILTRADO PRECISO DE TEMPORADAS ---
def buscar_series_api(query):
    if not query or len(query.strip()) < 2:
        return []
    
    resultados = []
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

def obtener_temporadas_emitidas(tvmaze_id):
    try:
        url = f"https://api.tvmaze.com/shows/{tvmaze_id}/seasons"
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        if isinstance(res, list) and len(res) > 0:
            hoy = datetime.now().strftime("%Y-%m-%d")
            # Filtrar solo temporadas oficiales (number > 0) y que ya hayan comenzado a emitirse
            temp_validas = []
            for s in res:
                num = s.get("number", 0)
                premiere = s.get("premiereDate")
                if num > 0:
                    if premiere and premiere <= hoy:
                        temp_validas.append(num)
                    elif not premiere:
                        # Si no hay fecha de premiere pero figura en el listado principal, se contempla si tiene episodios asignados
                        temp_validas.append(num)
            
            return len(temp_validas) if temp_validas else len(res)
    except:
        pass
    return 1

# --- INTERFAZ ---
st.title("🎬 StreamTracker")
st.caption("✨ Tu panel personal e inteligente de series")

st.divider()

# --- BÚSQUEDA ---
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
                with st.spinner("Calculando temporadas disponibles..."):
                    temp_totales = obtener_temporadas_emitidas(serie_sel["tvmaze_id"])
                    
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
                            "temp_vista": 1,
                            "temp_totales": temp_totales,
                            "estado": "Pendiente nueva temporada",
                            "rating": 5,
                            "poster_url": serie_sel["poster_url"],
                            "notas": serie_sel["sinopsis"][:150] + "..." if serie_sel["sinopsis"] else ""
                        })
                    
                    guardar_datos(st.session_state.series)
                    st.success(f"¡{serie_sel['nombre']} agregada con éxito!")
                    st.rerun()
    else:
        st.info("No se encontraron series. Intenta con otra palabra.")

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
                    f"Viste **T{s['temp_vista']}**, pero hay **{s['temp_totales']} temporadas disponibles** "
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
                    st.image(s["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️ Sin imagen")
                    
            with col_detalles:
                st.markdown(f"**📺 Plataforma:** {s.get('plataforma', 'N/A')}")
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    temp_vista_nueva = st.number_input(
                        "Temp. vista:",
                        min_value=0,
                        max_value=50,
                        value=int(s.get("temp_vista", 0)),
                        key=f"temp_input_{idx}"
                    )
                with col_t2:
                    temp_totales_nueva = st.number_input(
                        "Temp. disponibles:",
                        min_value=1,
                        max_value=50,
                        value=int(s.get("temp_totales", 1)),
                        key=f"temp_tot_{idx}"
                    )
                
                estado_nuevo = st.selectbox(
                    "Estado:",
                    ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"],
                    index=["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"].index(s.get("estado", "Pendiente nueva temporada")) if s.get("estado") in ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"] else 0,
                    key=f"estado_input_{idx}"
                )
                
                rating_nuevo = st.slider("Calificación:", 1, 5, int(s.get("rating", 5)), key=f"rate_{idx}")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Guardar cambios", key=f"save_{idx}", use_container_width=True):
                        st.session_state.series[idx]["temp_vista"] = temp_vista_nueva
                        st.session_state.series[idx]["temp_totales"] = temp_totales_nueva
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
