from datetime import datetime

def obtener_detalles_extra(imdb_id):
    rating = None
    seasons = 1
    try:
        url = f"https://api.tvmaze.com/lookup/shows?imdb={imdb_id}"
        res = requests.get(url, headers=HEADERS, timeout=3).json()
        if res:
            rating = res.get("rating", {}).get("average")
            show_id = res.get("id")
            if show_id:
                url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
                res_s = requests.get(url_seasons, headers=HEADERS, timeout=3).json()
                
                if isinstance(res_s, list):
                    hoy = datetime.now().date()
                    temporadas_emitidas = 0
                    
                    for season in res_s:
                        premier_date_str = season.get("premiereDate")
                        
                        if premier_date_str:
                            try:
                                fecha_estreno = datetime.strptime(premier_date_str, "%Y-%m-%d").date()
                                # Solo suma la temporada si la fecha de estreno es hoy o en el pasado
                                if fecha_estreno <= hoy:
                                    temporadas_emitidas += 1
                            except ValueError:
                                pass
                        elif season.get("number"):
                            # Si no hay fecha registrada pero ya hay número de temporada asignado
                            temporadas_emitidas += 1
                    
                    if temporadas_emitidas > 0:
                        seasons = temporadas_emitidas
    except Exception:
        pass
    return rating, seasons
