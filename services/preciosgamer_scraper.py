import requests
import time

def buscar_en_preciosgamer(producto):
    print(f"-> Buscando en PreciosGamer (con paginación) para '{producto}'...")
    productos_totales = []
    offset = 0
    limite_por_pagina = 30
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'} # Tu header

    while True:
        url = f"https://api.preciosgamer.com/v1/items?search={requests.utils.quote(producto)}&offset={offset}"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and 'response' in data and data['response']:
                resultados_pagina = data['response']
                
                for item in resultados_pagina:
                    # --- INICIO DE LA MEJORA ---
                    # Usamos un bloque try/except para cada producto individualmente.
                    # Si uno falla, el bucle continúa con el siguiente.
                    try:
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
                        continue # Salta al siguiente producto
                    # --- FIN DE LA MEJORA ---

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