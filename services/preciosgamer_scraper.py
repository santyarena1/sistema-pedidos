# -*- coding: utf-8 -*-
# services/preciosgamer_scraper.py

import requests
import time
import unicodedata
import re
from typing import List, Dict

# Lista blanca según tu proyecto (podés ajustar aquí)
TIENDAS_PERMITIDAS = {
    "Acuario Insumos", "Compra Gamer", "Compugarden", "Full H4rd", "Integrados Argentinos", "Maximus",
    "Megasoft", "Mexx", "Scp Hardstore", "TheGamerShop"
}

def _normalize(s: str) -> str:
    """Normaliza eliminando acentos, espacios, signos y pasando a minúsculas."""
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[\s\W_]+', '', s).lower()

def buscar_en_preciosgamer(producto: str, order: str = "asc_price") -> List[Dict]:
    """
    Scraper robusto para PreciosGamer.
    - Usa endpoint oficial, con cabeceras de navegador + Referer/Origin.
    - Lee la lista desde 'response' (NO 'results').
    - Paginación por offset (30 en 30).
    - Filtra por tiendas permitidas (normalización flexible).
    - Tolerante por ítem: si un registro viene mal, no corta toda la página.

    Retorna: lista de dicts con campos esperados por el backend/JS.
    """
    print(f"-> PreciosGamer: buscando '{producto}' (order={order})...")
    resultados: List[Dict] = []
    offset = 0
    LIMIT = 30

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "application/json",
        "Referer": "https://www.preciosgamer.com/",
        "Origin": "https://www.preciosgamer.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    tiendas_norm = {_normalize(t) for t in TIENDAS_PERMITIDAS}

    while True:
        url = (
            "https://api.preciosgamer.com/v1/items"
            f"?order={order}&search={requests.utils.quote(producto)}&offset={offset}"
        )
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()

            # 🔑 PUNTO CLAVE: la lista viene en 'response'
            pagina = data.get("response") or []
            if not pagina:
                break

            for item in pagina:
                try:
                    tienda_raw = item.get("resellerDescription", "") or ""
                    if _normalize(tienda_raw) not in tiendas_norm:
                        continue  # descartamos tiendas no autorizadas

                    # Campos con conversión segura
                    precio_actual = float(item.get("currentPrice", 0) or 0)
                    precio_anterior = float(item.get("lastPrice", 0) or 0)
                    porcentaje_desc = float(item.get("percentage", 0) or 0)

                    resultados.append({
                        "busqueda": producto.lower(),
                        "sitio": tienda_raw,
                        "producto": (item.get("description") or "").strip(),
                        "precio": precio_actual,
                        "link": item.get("destinyUrl") or "#",
                        "imagen": item.get("defaultImgUrl") or "",
                        "marca": (item.get("brandDescription") or "").strip() or "Sin Marca",
                        "precio_anterior": precio_anterior,
                        "porcentaje_descuento": porcentaje_desc,
                    })
                except (TypeError, ValueError) as e:
                    # Si un ítem viene mal, lo saltamos (tu mejora original)
                    print(f"   - Ítem inválido omitido: {e}")
                    continue

            print(f"   Página {offset//LIMIT + 1}: acumulados {len(resultados)}")
            if len(pagina) < LIMIT:
                break
            offset += LIMIT
            time.sleep(0.3)

        except requests.exceptions.RequestException as e:
            print(f"[PG] ERROR de red: {e}")
            break
        except Exception as e:
            print(f"[PG] ERROR procesando página: {e}")
            break

    print(f"-> PreciosGamer OK: {len(resultados)} productos filtrados.")
    return resultados


# ---- Bloque de prueba directa ----
if __name__ == "__main__":
    import sys
    term = sys.argv[1] if len(sys.argv) > 1 else "5600g"
    items = buscar_en_preciosgamer(term)
    print(f"TOTAL: {len(items)}")
    if items:
        from pprint import pprint
        pprint(items[0])
