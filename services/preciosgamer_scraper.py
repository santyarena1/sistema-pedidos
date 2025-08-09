# services/preciosgamer_scraper.py
import requests
import time
import re

def buscar_en_preciosgamer(producto):
    print(f"-> Buscando en PreciosGamer (con paginación) para '{producto}'...")
    productos_totales = []
    offset = 0
    limite_por_pagina = 30
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'}

    # LISTA BLANCA DE TIENDAS PERMITIDAS
    tiendas_permitidas = {
        "Acuario Insumos", "Compra Gamer", "Compugarden", "Full H4rd",
        "Gaming City", "Integrados Argentinos", "Maximus", "Megasoft",
        "Mexx", "Scp Hardstore", "TheGamerShop"  # Agregamos TheGamerShop
    }

    def normalizar_nombre(nombre):
        return re.sub(r'[\s\W_]+', '', nombre).lower()

    tiendas_permitidas_norm = {normalizar_nombre(t) for t in tiendas_permitidas}

    while True:
        url = f"https://api.preciosgamer.com/v1/items?search={requests.utils.quote(producto)}&offset={offset}"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and 'results' in data and data['results']:
                resultados_pagina = data['results']
                
                for item in resultados_pagina:
                    try:
                        nombre_tienda_norm = normalizar_nombre(item.get('resellerDescription', ''))
                        if nombre_tienda_norm in tiendas_permitidas_norm:
                            productos_totales.append({
                                'busqueda': producto.lower(),
                                'sitio': item.get('resellerDescription', 'N/A'),
                                'producto': item.get('description', 'N/A'),
                                'precio': float(item.get('currentPrice', 0)),
                                'link': item.get('destinyUrl', '#'),
                                'imagen': item.get('defaultImgUrl', ''),
                                'marca': item.get('brandDescription', 'Sin Marca'),
                                'precio_anterior': float(item.get('lastPrice', 0)),
                                'porcentaje_descuento': float(item.get('percentage', 0))
                            })
                    except (ValueError, TypeError) as e:
                        print(f"--- ADVERTENCIA: Omitiendo un producto por datos inválidos: {e} ---")
                        continue

                print(f"-> Página {int(offset/limite_por_pagina) + 1} obtenida. Total acumulado: {len(productos_totales)}")
                if len(resultados_pagina) < limite_por_pagina: break
                offset += limite_por_pagina
                time.sleep(0.5)
            else:
                break
        except requests.exceptions.RequestException as e:
            print(f"-> ERROR de red contactando PreciosGamer: {e}")
            break
        except Exception as e:
            print(f"-> ERROR procesando página de PreciosGamer: {e}")
            break
            
    print(f"-> Búsqueda en PreciosGamer finalizada. Total de {len(productos_totales)} productos encontrados.")
    return productos_totales