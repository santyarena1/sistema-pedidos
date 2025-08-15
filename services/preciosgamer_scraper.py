# services/preciosgamer_scraper.py
# Scraper estable vía API oficial de PreciosGamer (HTTP puro, sin navegador).
# Comentarios en castellano y campos normalizados para integrarse sin tocar el resto.

from __future__ import annotations
import time
import math
import logging
from typing import List, Dict
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_BA = ZoneInfo("America/Argentina/Buenos_Aires")

API_URL = "https://api.preciosgamer.com/v1/items"
PAGE_SIZE = 30
DEFAULT_HEADERS = {
    # User-Agent “realista” para evitar rate limit tonto
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

def _fmt_iso_now_ba() -> str:
    return datetime.now(tz=TZ_BA).isoformat()

def _safe_float(val, default=0.0) -> float:
    try:
        if val is None: return float(default)
        return float(str(val).replace(",", "."))
    except Exception:
        return float(default)

def buscar_en_preciosgamer(producto: str) -> List[Dict]:
    """
    Busca en PreciosGamer usando la API paginada.
    Devuelve lista de dicts con campos normalizados.
    """
    term = (producto or "").strip()
    if not term:
        return []

    resultados: List[Dict] = []
    offset = 0

    logging.info(f"-> Buscando en PreciosGamer para '{term}' (API) ...")
    while True:
        params = {
            "search": term,
            "offset": offset,
            "order": "asc_price",  # ordenar por precio asc para consistencia
        }
        try:
            resp = requests.get(API_URL, headers=DEFAULT_HEADERS, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            items = []
            if isinstance(data, dict) and data.get("response"):
                items = data["response"]

            # Si no hay items, cortamos
            if not items:
                break

            for item in items:
                try:
                    nombre = item.get("description") or "N/A"
                    precio_actual = _safe_float(item.get("currentPrice"), 0)
                    precio_anterior = _safe_float(item.get("lastPrice"), 0)
                    moneda = "ARS"
                    url = item.get("destinyUrl") or "#"
                    imagen = item.get("defaultImgUrl") or ""
                    reseller = item.get("resellerDescription") or "PreciosGamer"

                    resultados.append({
                        "busqueda": term.lower(),
                        "sitio": reseller,  # el reseller/tienda dentro de PreciosGamer
                        "nombre": nombre,
                        "precio_numeric": precio_actual,
                        "precio_raw": str(item.get("currentPrice")),
                        "moneda": moneda,
                        "url": url,
                        "imagen": imagen,
                        "actualizado_en": _fmt_iso_now_ba(),
                        "es_tgs": False
                    })
                except Exception as e:
                    logging.warning(f"--- ADVERTENCIA: ítem inválido en PreciosGamer: {e}")
                    continue

            logging.info(f"-> Página {math.floor(offset / PAGE_SIZE) + 1} OK. Total acumulado: {len(resultados)}")

            # si vino menos que PAGE_SIZE, ya no hay más
            if len(items) < PAGE_SIZE:
                break

            offset += PAGE_SIZE
            time.sleep(0.4)  # leve throttle
        except requests.exceptions.RequestException as e:
            logging.error(f"-> ERROR HTTP PreciosGamer: {e}")
            break
        except Exception as e:
            logging.error(f"-> ERROR procesando PreciosGamer: {e}")
            break

    logging.info(f"-> PreciosGamer finalizado. Total {len(resultados)} productos.")
    return resultados
