import streamlit as st
import requests
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker Argentina",
    page_icon="🍿",
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
    .logo-img {
        height: 26px;
        vertical-align: middle;
        margin-right: 8px;
        border-radius: 4px;
    }
    .imdb-badge {
        background-color: #f5c518;
        color: #000000;
        font-weight: bold;
        padding: 2px 8px;
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
        except:
            return []
    return []

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- LOGOS DE STREAMING (ARGENTINA) ---
LOGOS_STREAMING = {
    "netflix": "https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg",
    "disney": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Disney%2B_logo.svg",
    "max": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Max_logo.svg",
    "hbo": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Max_logo.svg",
    "prime": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Prime_Video.png",
    "apple": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Apple_TV_Plus_Logo.svg",
    "paramount": "https://upload.wikimedia.org/wikipedia/commons/a/a5/Paramount_Plus.svg",
    "flow": "https://upload.wikimedia.org/wikipedia/commons/2/29/Flow_logo.png",
    "mercado": "https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png"
}

def obtener_logo_plataforma(plataforma):
    p = plataforma.lower()
    for key, url in LOGOS_STREAMING.items():
        if key in p:
            return f'<img src="{url}" class="logo-img" title="{plataforma}">'
    return f"📺 **{plataforma}**"

def formatear_fecha(fecha_str):
    if not fecha_str or len(fecha_str) < 10:
        return fecha_str
    try:
        dt = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except:
        return fecha_str

# --- BÚSQUEDA Y DATOS DESDE TVMAZE (CON BÚSQUEDA LOCALIZADA ARGENTINA) ---
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
            
            # Nombre traducido si está disponible
            year = show.get("premiered", "")[:4] if show.get("premiered") else ""
            img_dict = show.get("image") or {}
            poster = img_dict.get("medium") or img_dict.get("original") or ""
            summary = show.get("summary", "").replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "")
            
            # Plataforma ajustada
            network = show.get("network", {}) or show.get("webChannel", {})
            plat = network.get("name") if network else "Streaming"
            
            # Mapeo de plataformas de EE.UU. a plataformas disponibles en Argentina
            plat_lower = plat.lower()
            if "hulu" in plat_lower or "fx" in plat_lower:
                plat = "Disney+"
            elif "hbo" in plat_lower or "max" in plat_lower:
                plat = "Max"
            elif "peacock" in plat_lower:
                plat = "Universal+ / Prime Video"

            # Rating IMDb
            rating_imdb = show.get("rating", {}).get("average")
            imdb_str = f"⭐ {rating_imdb}" if rating_imdb else "N/A"

            resultados.append({
                "label": f"🎬 {nombre} ({year}) — IMDb: {imdb_str}",
                "nombre": nombre,
                "plataforma": plat,
                "poster_url": poster,
                "sinopsis": summary,
                "tvmaze_id": show.get("id"),
                "rating_imdb": rating_imdb
            })
    except Exception:
        pass
        
    return resultados

def analizar_temporadas_y_capitulos(tvmaze_id):
    disponibles = 0
    confirmadas_futuras = []
    capitulos_por_temporada = {}
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Obtener episodios
        url_episodes = f"https://api.tvmaze.com/shows/{tvmaze_id}/episodes"
        res_episodes = requests.get(url_episodes, headers=HEADERS, timeout=5).json()
        
        if isinstance(res_episodes, list):
            temporadas_emitidas = set()
            for ep in res_episodes:
                season_num = ep.get("season", 0)
                airdate = ep.get("airdate", "")
                
                if season_num > 0:
                    if season_num not in capitulos_por_temporada:
                        capitulos_por_temporada[season_num] = 0
                    
                    if airdate and airdate <= hoy:
                        capitulos_por_temporada[season_num] += 1
                        temporadas_emitidas.add(season_num)

            disponibles = len(temporadas_emitidas) if temporadas_emitidas else 1
            
            # Obtener temporadas futuras
            url_seasons = f"https://api.tvmaze.com/shows/{tvmaze_id}/seasons"
            res_seasons = requests.get(url_seasons, headers=HEADERS, timeout=5).json()
            if isinstance(res_seasons, list):
                for s in res_seasons:
                    s_num = s.get("number", 0)
                    premiere = s.get("premiereDate")
                    if s_num > disponibles and s_num > 0:
                        fecha_fmt = formatear_fecha(premiere) if premiere else "Confirmada"
                        confirmadas_futuras.append(f"Temporada {s_num} (Estreno: {fecha_fmt})")
                        
    except Exception:
        disponibles = 1
        
    return disponibles, confirmadas_futuras, capitulos_por_temporada

# --- ENCABEZADO ---
st.markdown("<h1 class='main-title'>🍿 StreamTracker Argentina</h1>", unsafe_allow_html=True)
st.caption("✨ Tu catálogo de series y películas adaptado al streaming local")

st.divider()

# --- BÚSQUEDA INSTANTÁNEA ---
st.subheader("🔍 Buscar Serie o Película")

query = st.text_input(
    "Escribe el nombre:", 
    placeholder="Empieza a escribir (ej: Harry Potter, Slow Horses, El Encargado)...",
    key="search_input"
)

if query and len(query.strip()) >= 2:
    sugerencias = buscar_series_api(query.strip())
    
    if sugerencias:
        opciones_dict = {s["label"]: s for s in sugerencias}
        
        seleccion = st.selectbox(
            "👇 Sugerencias encontradas:", 
            list(opciones_dict.keys()),
            key="select_sugerencia"
        )
        
        if seleccion:
            serie_sel = opciones_dict[seleccion]
            
            col_prev_img, col_prev_info = st.columns([1, 3])
            with col_prev_img:
                if serie_sel["poster_url"]:
                    st.image(serie_sel["poster_url"], width=100)
            with col_prev_info:
                st.markdown(f"**{serie_sel['nombre']}**")
                logo_html = obtener_logo_plataforma(serie_sel['plataforma'])
                st.markdown(f"Disponible en: {logo_html}", unsafe_allow_html=True)
                
                if serie_sel.get("rating_imdb"):
                    st.markdown(f"<span class='imdb-badge'>IMDb {serie_sel['rating_imdb']} / 10</span>", unsafe_allow_html=True)
                
                if st.button("➕ Agregar a mi colección", use_container_width=True, type="primary"):
                    with st.spinner("Obteniendo episodios y temporadas..."):
                        temp_disp, futuras, caps_por_temp = analizar_temporadas_y_capitulos(serie_sel["tvmaze_id"])
                        
                        existe = False
                        for s in st.session_state.series:
                            if s["serie"].lower() == serie_sel["nombre"].lower():
                                s["temp_totales"] = temp_disp
                                s["plataforma"] = serie_sel["plataforma"]
                                s["futuras"] = futuras
                                s["capitulos_detalle"] = caps_por_temp
                                s["rating_imdb"] = serie_sel.get("rating_imdb")
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
                                "capitulos_detalle": caps_por_temp,
                                "estado": "Pendiente nueva temporada",
                                "rating": 5,
                                "rating_imdb": serie_sel.get("rating_imdb"),
                                "poster_url": serie_sel["poster_url"],
                                "notas": serie_sel["sinopsis"][:120] + "..." if serie_sel["sinopsis"] else ""
                            })
                        
                        guardar_datos(st.session_state.series)
                        st.success(f"¡{serie_sel['nombre']} agregada!")
                        st.rerun()
    else:
        st.info("No se encontraron coincidencias.")

st.divider()

# --- COLECCIÓN CON DESGLOSE DE CAPÍTULOS Y RATING ---
st.subheader(f"📺 Tu Colección ({len(st.session_state.series)})")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        logo_html = obtener_logo_plataforma(s.get("plataforma", ""))
        
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
                    st.write("🖼️ Sin portada")
                    
            with col_detalles:
                st.markdown(f"Plataforma: {logo_html}", unsafe_allow_html=True)
                
                # Calificaciones
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    if s.get("rating_imdb"):
                        st.markdown(f"<span class='imdb-badge'>IMDb {s['rating_imdb']} / 10</span>", unsafe_allow_html=True)
                    else:
                        st.caption("IMDb: N/A")
                with col_r2:
                    st.markdown(f"**Tu Nota:** {'⭐' * int(s.get('rating', 5))}")

                st.divider()

                # Desglose de capítulos por temporada
                st.markdown("**📂 Detalle de Capítulos por Temporada:**")
                caps_dict = s.get("capitulos_detalle", {})
                if caps_dict:
                    txt_caps = []
                    for temp_n, cap_cnt in sorted(caps_dict.items()):
                        txt_caps.append(f"• **Temp {temp_n}:** {cap_cnt} episodios")
                    st.markdown("\n".join(txt_caps))
                else:
                    st.caption("Información de episodios no disponible.")

                if s.get("futuras"):
                    st.caption("📌 **Próximos estrenos:** " + ", ".join(s["futuras"]))

                st.divider()
                
                # Edición rápida
                temp_vista_nueva = st.number_input(
                    "Última temporada vista:",
                    min_value=0,
                    max_value=50,
                    value=int(s.get("temp_vista", 0)),
                    key=f"temp_input_{idx}"
                )
                
                rating_nuevo = st.slider("Cambiar tu calificación:", 1, 5, int(s.get("rating", 5)), key=f"rate_{idx}")
                
                estado_nuevo = st.selectbox(
                    "Estado:",
                    ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"],
                    index=["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"].index(s.get("estado", "Pendiente nueva temporada")) if s.get("estado") in ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"] else 0,
                    key=f"estado_input_{idx}"
                )
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Guardar cambios", key=f"save_{idx}", use_container_width=True):
                        st.session_state.series[idx]["temp_vista"] = temp_vista_nueva
                        st.session_state.series[idx]["rating"] = rating_nuevo
                        st.session_state.series[idx]["estado"] = estado_nuevo
                        guardar_datos(st.session_state.series)
                        st.success("¡Guardado!")
                        st.rerun()
                
                with col_b2:
                    if st.button("🗑️ Eliminar", key=f"del_{idx}", use_container_width=True):
                        st.session_state.series.pop(idx)
                        guardar_datos(st.session_state.series)
                        st.rerun()
else:
    st.info("Tu colección está vacía. ¡Busca una serie o película para comenzar!")
