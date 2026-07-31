import streamlit as st
import requests
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker",
    page_icon="🍿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS (DISEÑO MÁS AMIGABLE Y MODERNO) ---
st.markdown("""
<style>
    /* Fondo y contenedores */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header principal */
    .main-title {
        color: #f8fafc;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    
    /* Módulos y Tarjetas */
    div[data-testid="stExpander"] {
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        background-color: #0f172a !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 0.8rem;
    }
    
    /* Badges de Plataformas */
    .plat-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background-color: #334155;
        color: #f8fafc;
        margin-bottom: 8px;
    }
    
    .plat-apple { background-color: #000000; color: #ffffff; border: 1px solid #475569; }
    .plat-netflix { background-color: #e50914; color: #ffffff; }
    .plat-hbo { background-color: #5822b4; color: #ffffff; }
    .plat-prime { background-color: #00a8e1; color: #ffffff; }
    .plat-disney { background-color: #113ccf; color: #ffffff; }
    
    /* Alertas */
    div[data-testid="stAlert"] {
        border-radius: 10px;
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

# --- BÚSQUEDA Y ANÁLISIS DE SERIES ---
def buscar_series_api(query):
    if not query or len(query.strip()) < 2:
        return []
    
    resultados = []
    try:
        url_tvmaze = f"https://api.tvmaze.com/search/shows?q={query}"
        res_tv = requests.get(url_tvmaze, headers=HEADERS, timeout=5).json()
        for item in res_tv[:6]:
            show = item.get("show", {})
            nombre = show.get("name")
            year = show.get("premiered", "")[:4] if show.get("premiered") else ""
            img_dict = show.get("image") or {}
            poster = img_dict.get("medium") or img_dict.get("original") or ""
            summary = show.get("summary", "").replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "")
            network = show.get("network", {}) or show.get("webChannel", {})
            plat = network.get("name") if network else "Streaming"
            
            resultados.append({
                "label": f"🎬 {nombre} ({year})" if year else f"🎬 {nombre}",
                "nombre": nombre,
                "plataforma": plat,
                "poster_url": poster,
                "sinopsis": summary,
                "tvmaze_id": show.get("id")
            })
    except Exception:
        pass
        
    return resultados

def analizar_temporadas_reales(tvmaze_id):
    disponibles = 0
    confirmadas_futuras = []
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    try:
        url_episodes = f"https://api.tvmaze.com/shows/{tvmaze_id}/episodes"
        res_episodes = requests.get(url_episodes, headers=HEADERS, timeout=5).json()
        
        if isinstance(res_episodes, list):
            temporadas_con_episodios_emitidos = set()
            for ep in res_episodes:
                season_num = ep.get("season", 0)
                airdate = ep.get("airdate", "")
                if season_num > 0 and airdate and airdate <= hoy:
                    temporadas_con_episodios_emitidos.add(season_num)
            
            disponibles = len(temporadas_con_episodios_emitidos) if temporadas_con_episodios_emitidos else 1
            
            url_seasons = f"https://api.tvmaze.com/shows/{tvmaze_id}/seasons"
            res_seasons = requests.get(url_seasons, headers=HEADERS, timeout=5).json()
            if isinstance(res_seasons, list):
                for s in res_seasons:
                    s_num = s.get("number", 0)
                    premiere = s.get("premiereDate")
                    if s_num > disponibles and s_num > 0:
                        txt_estreno = f"Temporada {s_num}"
                        if premiere:
                            txt_estreno += f" (Estreno: {premiere})"
                        else:
                            txt_estreno += " (Confirmada)"
                        confirmadas_futuras.append(txt_estreno)
                        
    except Exception:
        disponibles = 1
        
    return disponibles, confirmadas_futuras

def obtener_clase_plataforma(plataforma):
    p = plataforma.lower()
    if "apple" in p: return "plat-badge plat-apple", " Apple TV+"
    if "netflix" in p: return "plat-badge plat-netflix", "🔴 Netflix"
    if "hbo" in p or "max" in p: return "plat-badge plat-hbo", "🟣 Max / HBO"
    if "prime" in p or "amazon" in p: return "plat-badge plat-prime", "🔵 Prime Video"
    if "disney" in p: return "plat-badge plat-disney", "🔹 Disney+"
    return "plat-badge", f"📺 {plataforma}"

# --- ENCABEZADO PRINCIPAL ---
st.markdown("<h1 class='main-title'>🍿 StreamTracker</h1>", unsafe_allow_html=True)
st.caption("✨ Tu catálogo personal inteligente de series y temporadas")

st.divider()

# --- BÚSQUEDA INSTANTÁNEA (SIN NECESIDAD DE APRETAR ENTER) ---
st.subheader("🔍 Buscar y Agregar Serie")

query = st.text_input(
    "Escribe el nombre de la serie:", 
    placeholder="Empieza a escribir (ej: Slow Horses, The Bear, Succession)...",
    key="search_input"
)

# Sugerencias instantáneas a partir de 2 caracteres
if query and len(query.strip()) >= 2:
    sugerencias = buscar_series_api(query.strip())
    
    if sugerencias:
        opciones_dict = {s["label"]: s for s in sugerencias}
        
        # El selectbox actúa como menú desplegable en tiempo real
        seleccion = st.selectbox(
            "👇 Sugerencias encontradas (selecciona la tuya):", 
            list(opciones_dict.keys()),
            key="select_sugerencia"
        )
        
        if seleccion:
            serie_sel = opciones_dict[seleccion]
            
            # Vista previa rápida antes de guardar
            col_prev_img, col_prev_info = st.columns([1, 3])
            with col_prev_img:
                if serie_sel["poster_url"]:
                    st.image(serie_sel["poster_url"], width=100)
            with col_prev_info:
                st.markdown(f"**{serie_sel['nombre']}**")
                css_class, plat_label = obtener_clase_plataforma(serie_sel['plataforma'])
                st.markdown(f"<span class='{css_class}'>{plat_label}</span>", unsafe_allow_html=True)
                
                if st.button(f"➕ Agregar a mi colección", use_container_width=True, type="primary"):
                    with st.spinner("Analizando temporadas reales disponibles..."):
                        temp_disp, futuras = analizar_temporadas_reales(serie_sel["tvmaze_id"])
                        
                        existe = False
                        for s in st.session_state.series:
                            if s["serie"].lower() == serie_sel["nombre"].lower():
                                s["temp_totales"] = temp_disp
                                s["plataforma"] = serie_sel["plataforma"]
                                s["futuras"] = futuras
                                if serie_sel["poster_url"]:
                                    s["poster_url"] = serie_sel["poster_url"]
                                existe = True
                                break
                        
                        if not existe:
                            st.session_state.series.append({
                                "serie": serie_sel["nombre"],
                                "plataforma": serie_sel["plataforma"],
                                "temp_vista": 1,
                                "temp_totales": temp_disp,
                                "futuras": futuras,
                                "estado": "Pendiente nueva temporada",
                                "rating": 5,
                                "poster_url": serie_sel["poster_url"],
                                "notas": serie_sel["sinopsis"][:120] + "..." if serie_sel["sinopsis"] else ""
                            })
                        
                        guardar_datos(st.session_state.series)
                        st.success(f"¡{serie_sel['nombre']} agregada!")
                        st.rerun()
    else:
        st.info("No se encontraron coincidencias. Prueba con otra palabra.")

st.divider()

# --- SECCIÓN DE ALERTAS DE PENDIENTES ---
pendientes = [s for s in st.session_state.series if s.get("temp_totales", 1) > s.get("temp_vista", 0)]

if pendientes:
    st.subheader("🔔 Temporadas Pendientes por Ver")
    for s in pendientes:
        diferencia = s["temp_totales"] - s["temp_vista"]
        css_class, plat_label = obtener_clase_plataforma(s.get("plataforma", ""))
        
        with st.container():
            col_a1, col_a2 = st.columns([1, 4])
            with col_a1:
                if s.get("poster_url"):
                    st.image(s["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️")
            with col_a2:
                st.markdown(f"### {s['serie']}")
                st.markdown(f"<span class='{css_class}'>{plat_label}</span>", unsafe_allow_html=True)
                st.warning(
                    f"🍿 Viste hasta la **Temporada {s['temp_vista']}**, pero ya salieron **{s['temp_totales']} temporadas** "
                    f"(*¡Tienes {diferencia} temporada(s) nueva(s) esperándote!*)."
                )

st.divider()

# --- COLECCIÓN PRINCIPAL CON DISEÑO DE TARJETAS ---
st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        css_class, plat_label = obtener_clase_plataforma(s.get("plataforma", ""))
        estrellas = "⭐" * int(s.get("rating", 5))
        
        # Estado visual
        estado_icon = "⏳"
        if s.get("estado") == "Completada": estado_icon = "✅"
        elif s.get("estado") == "Viendo": estado_icon = "▶️"
        elif s.get("estado") == "Abandonada": estado_icon = "🛑"
        
        titulo_tarjeta = f"{s['serie']} — Viste T{s['temp_vista']} de T{s['temp_totales']} {estado_icon}"
        
        with st.expander(titulo_tarjeta, expanded=False):
            col_img, col_detalles = st.columns([1.2, 2.8])
            
            with col_img:
                if s.get("poster_url"):
                    st.image(s["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️ Sin imagen")
                    
            with col_detalles:
                st.markdown(f"<span class='{css_class}'>{plat_label}</span>", unsafe_allow_html=True)
                st.markdown(f"**Calificación:** {estrellas}")
                st.markdown(f"**🟢 Temporadas lanzadas:** `{s.get('temp_totales', 1)}`")
                
                if s.get("futuras"):
                    txt_fut = ", ".join(s["futuras"])
                    st.caption(f"📌 **Futuras:** {txt_fut}")
                
                if s.get("notas"):
                    st.caption(f"📝 *{s['notas']}*")
                
                st.divider()
                
                # Edición rápida
                temp_vista_nueva = st.number_input(
                    "Última temporada que viste:",
                    min_value=0,
                    max_value=50,
                    value=int(s.get("temp_vista", 0)),
                    key=f"temp_input_{idx}"
                )
                
                estado_nuevo = st.selectbox(
                    "Estado actual:",
                    ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"],
                    index=["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"].index(s.get("estado", "Pendiente nueva temporada")) if s.get("estado") in ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"] else 0,
                    key=f"estado_input_{idx}"
                )
                
                rating_nuevo = st.slider("Tu puntaje:", 1, 5, int(s.get("rating", 5)), key=f"rate_{idx}")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Guardar", key=f"save_{idx}", use_container_width=True):
                        st.session_state.series[idx]["temp_vista"] = temp_vista_nueva
                        st.session_state.series[idx]["estado"] = estado_nuevo
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
    st.info("Tu colección está vacía. ¡Escribe el nombre de una serie arriba para empezar!")
