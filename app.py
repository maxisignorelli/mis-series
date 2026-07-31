import streamlit as st
import json
import os

DB_FILE = "series_data.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return [
        {
            "serie": "Slow Horses",
            "plataforma": "Apple TV+",
            "temp_vista": 1,
            "temp_totales": 4,
            "estado": "Pendiente nueva temporada",
            "rating": 5,
            "fecha_estreno": "",
            "poster_url": "https://m.media-amazon.com/images/M/MV5BOTE3N2M3OTItNzUyNS00MDcxLTg1NzAtYTE5OTlmZDM4M2VkXkEyXkFqcGc@._V1_.jpg",
            "notas": "Excelente serie de espionaje. Pendiente arrancar la T2."
        }
    ]

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="Mi Tracker de Series Pro", page_icon="🎬", layout="centered")

st.title("🎬 Mi Tracker de Series")
st.caption("Gestiona tus series, temporadas pendientes, fechas de estreno y notas.")

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

# --- FORMULARIO PARA AGREGAR O EDITAR ---
with st.expander("➕ Agregar / Actualizar Serie", expanded=False):
    with st.form("form_serie"):
        nombre = st.text_input("Nombre de la Serie *")
        plataforma = st.text_input("Plataforma (ej. Apple TV+, Netflix, HBO)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            temp_vista = st.number_input("Última temp. vista", min_value=0, value=1, step=1)
        with col_t2:
            temp_totales = st.number_input("Temp. disponibles/totales", min_value=1, value=1, step=1)
            
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            estado = st.selectbox(
                "Estado", 
                ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"]
            )
        with col_e2:
            rating = st.slider("Calificación (Estrellas)", min_value=1, max_value=5, value=5)
            
        fecha_estreno = st.text_input("Próximo estreno (Opcional, ej: 15 de Noviembre)")
        poster_url = st.text_input("URL del Póster/Imagen (Opcional link de imagen)")
        notas = st.text_area("Notas personales (ej: 'Quedé en episodio 3', 'Ver con...')")
        
        submitted = st.form_submit_button("💾 Guardar Serie")
        
        if submitted and nombre:
            # Buscar si ya existe para actualizar
            existe = False
            for s in st.session_state.series:
                if s["serie"].lower() == nombre.lower():
                    s["plataforma"] = plataforma
                    s["temp_vista"] = temp_vista
                    s["temp_totales"] = temp_totales
                    s["estado"] = estado
                    s["rating"] = rating
                    s["fecha_estreno"] = fecha_estreno
                    s["poster_url"] = poster_url
                    s["notas"] = notas
                    existe = True
                    break
            
            if not existe:
                st.session_state.series.append({
                    "serie": nombre,
                    "plataforma": plataforma,
                    "temp_vista": temp_vista,
                    "temp_totales": temp_totales,
                    "estado": estado,
                    "rating": rating,
                    "fecha_estreno": fecha_estreno,
                    "poster_url": poster_url,
                    "notas": notas
                })
            
            guardar_datos(st.session_state.series)
            st.success(f"¡{nombre} guardada con éxito!")
            st.rerun()

st.divider()

# --- ALERTAS Y PENDIENTES ---
pendientes = [s for s in st.session_state.series if s.get("temp_totales", 1) > s.get("temp_vista", 0)]

st.subheader("🔔 Temporadas Pendientes por Ver")
if pendientes:
    for s in pendientes:
        diferencia = s["temp_totales"] - s["temp_vista"]
        estreno_txt = f" | 📅 **Estreno registrado:** {s['fecha_estreno']}" if s.get("fecha_estreno") else ""
        st.warning(
            f"🍿 **{s['serie']}** ({s['plataforma']})\n\n"
            f"Viste hasta la **T{s['temp_vista']}**, pero ya hay **T{s['temp_totales']} disponibles** "
            f"({diferencia} temporada(s) pendiente(s)).{estreno_txt}"
        )
else:
    st.info("🎉 ¡Estás al día con todas tus series!")

st.divider()

# --- FILTROS DE BÚSQUEDA ---
st.subheader("🔍 Filtros y Búsqueda")
col_f1, col_f2 = st.columns(2)

with col_f1:
    filtro_estado = st.selectbox("Filtrar por Estado", ["Todos", "Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"])
with col_f2:
    plataformas_unicas = ["Todas"] + list(set([s.get("plataforma", "") for s in st.session_state.series if s.get("plataforma")]))
    filtro_plat = st.selectbox("Filtrar por Plataforma", plataformas_unicas)

# Filtrar lista
series_filtradas = st.session_state.series
if filtro_estado != "Todos":
    series_filtradas = [s for s in series_filtradas if s.get("estado") == filtro_estado]
if filtro_plat != "Todas":
    series_filtradas = [s for s in series_filtradas if s.get("plataforma") == filtro_plat]

st.divider()

# --- LISTADO DE SERIES ---
st.subheader(f"📺 Tu Lista ({len(series_filtradas)} series)")

if series_filtradas:
    for idx, s in enumerate(series_filtradas):
        with st.container():
            col_img, col_info, col_del = st.columns([1.5, 3.5, 0.8])
            
            with col_img:
                if s.get("poster_url"):
                    try:
                        st.image(s["poster_url"], use_column_width=True)
                    except:
                        st.caption("📷 Imagen no disponible")
                else:
                    st.caption("📺 Sin póster")

            with col_info:
                estrellas = "⭐" * int(s.get("rating", 5))
                st.markdown(f"### {s['serie']} {estrellas}")
                st.caption(f"**Plataforma:** {s.get('plataforma', 'N/A')} | **Estado:** {s.get('estado', 'N/A')}")
                st.write(f"📊 Vista: **T{s.get('temp_vista', 0)}** / Disponible: **T{s.get('temp_totales', 1)}**")
                
                if s.get("fecha_estreno"):
                    st.write(f"📅 **Próximo estreno:** {s['fecha_estreno']}")
                if s.get("notas"):
                    st.info(f"📝 **Notas:** {s['notas']}")

            with col_del:
                # Encontrar el índice real en la lista completa para borrar
                idx_real = st.session_state.series.index(s)
                if st.button("🗑️", key=f"del_{idx_real}", help="Eliminar serie"):
                    st.session_state.series.pop(idx_real)
                    guardar_datos(st.session_state.series)
                    st.rerun()
            
            st.divider()
else:
    st.write("No hay series que coincidan con los filtros seleccionados.")
