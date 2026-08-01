import streamlit as st
import requests
import json
import os
from datetime import datetime
from streamlit_searchbox import st_searchbox
from google import genai

# --- OBTENER API KEY DESDE LOS SECRETS DE STREAMLIT ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="StreamTracker — Estilo JustWatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stApp {
        background: #0b0e14;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .header-container {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .header-title {
        color: #f8fafc;
        font-weight: 900;
        font-size: 2.2rem;
        margin: 0;
        letter-spacing: -0.03em;
    }
    
    .imdb-badge {
        background-color: #f5c518;
        color: #000000;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    
    .genre-tag {
        background-color: #1e293b;
        color: #cbd5e1;
        border: 1px solid #334155;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        margin-right: 4px;
        display: inline-block;
    }

    .status-tag {
        background-color: #0284c7;
        color: white;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-badge-viewing {
        background-color: #10b981;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-badge-completed {
        background-color: #3b82f6;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    div[data-testid="stExpander"] {
        background-color: #151c28 !important;
        border: 1px solid #232d3f !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "series_data.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamTrackerApp/1.0"}

# --- OBTENER DETALLES COMPLETOS DE TVMAZE ---
def obtener_detalles_completos(imdb_id):
    info = {
        "rating_imdb": None,
        "temp_totales": 1,
        "generos": [],
        "estado_serie": "Desconocido",
        "primer_episodio": "N/A",
        "ultimo_episodio": "N/A",
        "actores": [],
        "desglose_temporadas": []
    }
    
    if not imdb_id:
        return info

    try:
        url = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=4).json()
        
        if res:
            info["rating_imdb"] = res.get("rating", {}).get("average")
            info["generos"] = res.get("genres", [])
            
            status_raw = res.get("status", "")
            if status_raw == "Ended":
                info["estado_serie"] = "Finalizada 🏁"
            elif status_raw == "Running":
                info["estado_serie"] = "En Emisión 📺"
            elif status_raw == "To Be Determined":
                info["estado_serie"] = "En Pausa / Pendiente ⏳"
            else:
                info["estado_serie"] = status_raw or "En Emisión"

            show_id = res.get("id")
            
            if show_id:
                url_cast = f"https://api.tvmaze.com/shows/{show_id}/cast"
                res_cast = requests.get(url_cast, headers=HEADERS, timeout=4).json()
                if isinstance(res_cast, list):
                    info["actores"] = [c["person"]["name"] for c in res_cast[:5] if "person" in c]
                
                url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
                res_s = requests.get(url_seasons, headers=HEADERS, timeout=4).json()
                
                url_episodes = f"https://api.tvmaze.com/shows/{show_id}/episodes"
                res_ep = requests.get(url_episodes, headers=HEADERS, timeout=4).json()
                
                hoy = datetime.now().date()
                
                if isinstance(res_ep, list) and len(res_ep) > 0:
                    eps_emitidos = []
                    for ep in res_ep:
                        a_date = ep.get("airdate")
                        if a_date:
                            try:
                                f_ep = datetime.strptime(a_date, "%Y-%m-%d").date()
                                if f_ep <= hoy:
                                    eps_emitidos.append(ep)
                            except ValueError:
                                pass
                    
                    if eps_emitidos:
                        info["primer_episodio"] = eps_emitidos[0].get("airdate", "N/A")
                        info["ultimo_episodio"] = eps_emitidos[-1].get("airdate", "N/A")
                
                if isinstance(res_s, list):
                    temp_emitidas_count = 0
                    desglose = []
                    
                    for season in res_s:
                        p_date = season.get("premiereDate")
                        es_emitida = False
                        if p_date:
                            try:
                                f_prem = datetime.strptime(p_date, "%Y-%m-%d").date()
                                if f_prem <= hoy:
                                    es_emitida = True
                            except ValueError:
                                pass
                        
                        if es_emitida:
                            temp_emitidas_count += 1
                            num_temp = season.get("number", temp_emitidas_count)
                            eps_temp = [e for e in res_ep if e.get("season") == num_temp and e.get("airdate") and datetime.strptime(e.get("airdate"), "%Y-%m-%d").date() <= hoy] if isinstance(res_ep, list) else []
                            
                            desglose.append({
                                "temporada": f"Temporada {num_temp}",
                                "episodios": len(eps_temp) if eps_temp else (season.get("episodeOrder") or "N/A"),
                                "rating": season.get("rating", {}).get("average") or info["rating_imdb"] or "N/A"
                            })
                    
                    info["temp_totales"] = max(temp_emitidas_count, 1)
                    info["desglose_temporadas"] = desglose
    except Exception:
        pass
        
    return info

# --- CARGAR / GUARDAR DATOS ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
                modificado = False
                for s in datos:
                    if "estado_serie" not in s or s.get("primer_episodio") in [None, "N/A"]:
                        detalles = obtener_detalles_completos(s.get("imdb_id"))
                        s.update(detalles)
                        modificado = True
                if modificado:
                    guardar_datos(datos)
                return datos
        except Exception:
            return []
    return []

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

if "series" not in st.session_state:
    st.session_state.series = cargar_datos()

if "recomendaciones" not in st.session_state:
    st.session_state.recomendaciones = []

# --- BÚSQUEDA IMDB LIVE ---
def buscar_imdb_live(search_term: str):
    if not search_term or len(search_term.strip()) < 2:
        return []
    
    opciones = []
    try:
        q_clean = search_term.strip().lower().replace(" ", "_")
        url = f"https://v3.sg.media-imdb.com/suggestion/x/{q_clean}.json"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        
        items = res.get("d", [])
        for item in items:
            q_type = item.get("qid", "")
            if q_type in ["movie", "tvSeries", "tvMiniSeries", "tvSpecial"]:
                title = item.get("l")
                year = item.get("y", "")
                imdb_id = item.get("id")
                
                i_dict = item.get("i", {})
                poster = i_dict.get("imageUrl", "") if i_dict else ""
                stars = item.get("s", "")
                
                label_type = "📺" if "tv" in q_type else "🎬"
                reparto_txt = f" — {stars[:30]}" if stars else ""
                txt_mostrar = f"{label_type} {title} ({year}){reparto_txt}"
                
                opciones.append((txt_mostrar, {
                    "imdb_id": imdb_id,
                    "nombre": title,
                    "year": year,
                    "tipo": label_type,
                    "poster_url": poster,
                    "elenco": stars
                }))
    except Exception:
        pass
        
    return opciones

# --- FUNCIÓN DE IA RECOMENDADORA (GENERA JSON) ---
def obtener_recomendaciones_ia(api_key, coleccion):
    try:
        client = genai.Client(api_key=api_key)
        
        resumen = []
        for s in coleccion:
            resumen.append(
                f"- {s['serie']} (Géneros: {', '.join(s.get('generos', []))}, Calificación personal: {s.get('rating', 8)}/10)"
            )
        
        prompt = f"""
        Actúa como un experto curador de cine y televisión.
        Analiza el historial de este usuario:

        {chr(10).join(resumen)}

        Basándote en sus valoraciones más altas y géneros preferidos, recomienda exactamente 4 series o películas que NO estén en su lista.
        
        Responde ÚNICAMENTE en formato JSON válido (sin texto antes ni después) con la siguiente estructura de lista:
        [
            {{
                "titulo": "Título de la serie o película",
                "motivo": "Explicación breve de por qué le gustará basándote en lo que ya vio.",
                "plataforma": "Netflix / Max / Prime Video / etc."
            }}
        ]
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        texto_clean = response.text.strip()
        if texto_clean.startswith("```json"):
            texto_clean = texto_clean.replace("
