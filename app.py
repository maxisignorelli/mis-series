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
            "estado": "Pendiente nueva temporada"
        }
    ]

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="Mi Tracker de Series", page_icon="🎬", layout="centered")

st.title("🎬 Mi Rastreador de Series")
st.caption("Organiza lo que viste y mantente al día con las nuevas temporadas.")

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

# --- FORMULARIO PARA AGREGAR / EDITAR ---
with st.expander("➕ Agregar o actualizar una serie", expanded=False):
    with st.form("form_serie"):
        nombre = st.text_input("Nombre de la Serie")
        plataforma = st.text_input("Plataforma (ej. Apple TV+, Netflix, HBO)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            temp_vista = st.number_input("Última temporada vista", min_value=0, value=1, step=1)
        with col_t2:
            temp_totales = st.number_input("Temporadas disponibles/totales", min_value=1, value=1, step=1)
            
        estado = st.selectbox(
            "Estado", 
            ["Pendiente nueva temporada", "Viendo", "Completada", "Abandonada"]
        )
        
        submitted = st.form_submit_button("Guardar Serie")
        
        if submitted and nombre:
            # Reemplaza si ya existe, o agrega nueva
            existe = False
            for s in st.session_state.series:
                if s["serie"].lower() == nombre.lower():
                    s["plataforma"] = plataforma
                    s["temp_vista"] = temp_vista
                    s["temp_totales"] = temp_totales
                    s["estado"] = estado
                    existe = True
                    break
            
            if not existe:
                st.session_state.series.append({
                    "serie": nombre,
                    "plataforma": plataforma,
                    "temp_vista": temp_vista,
                    "temp_totales": temp_totales,
                    "estado": estado
                })
            
            guardar_datos(st.session_state.series)
            st.success(f"¡{nombre} guardada con éxito!")
            st.rerun()

st.divider()

# --- PANEL DE ALERTAS ---
pendientes = [s for s in st.session_state.series if s["temp_totales"] > s["temp_vista"]]

st.subheader("🔔 Temporadas Pendientes por Ver")
if pendientes:
    for s in pendientes:
        diferencia = s["temp_totales"] - s["temp_vista"]
        st.warning(
            f"🍿 **{s['serie']}** ({s['plataforma']})\n\n"
            f"Viste hasta la **Temporada {s['temp_vista']}**, pero ya hay **{s['temp_totales']} disponibles** "
            f"({diferencia} temporada(s) pendiente(s))."
        )
else:
    st.info("🎉 ¡Estás al día con todas tus series!")

st.divider()

# --- LISTA COMPLETA ---
st.subheader("📺 Tu Lista de Series")

if st.session_state.series:
    for idx, s in enumerate(st.session_state.series):
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{s['serie']}**")
                st.caption(f"Plataforma: {s['plataforma']} | Estado: {s['estado']}")
            with col2:
                st.write(f"Vista: **T{s['temp_vista']}** / Disponible: **T{s['temp_totales']}**")
            with col3:
                if st.button("🗑️", key=f"del_{idx}", help="Eliminar serie"):
                    st.session_state.series.pop(idx)
                    guardar_datos(st.session_state.series)
                    st.rerun()
            st.divider()
else:
    st.write("Aún no has agregado series a tu lista.")
