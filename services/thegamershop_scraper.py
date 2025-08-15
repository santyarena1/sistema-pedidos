# services/thegamershop_scraper.py
# Scraper robusto por HTTP + BeautifulSoup para resultados de búsqueda en TheGamerShop.
# Evita Playwright/Selenium. Intenta múltiples endpoints/selectores comunes.

from __future__ import annotations
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

TZ_BA = ZoneInfo("America/Argentina/Buenos_Aires")

BASE = "https://www.thegamershop.com.ar"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

PRICE_RE = re.compile(r"[\$S\$]?[\s]*([\d\.]+(?:,\d{2})?)")  # capta 12.345,67 | 12345

def _fmt_iso_now_ba() -> str:
    return datetime.now(tz=TZ_BA).isoformat()

def _to_float_ars(s: str) -> float:
    """
    Normaliza precios en ARS con separador de miles punto y decimal coma.
    """
    if not s:
        return 0.0
    # extrae 12.345,67
    m = PRICE_RE.search(s)
    txt = m.group(1) if m else s
    # pasar "12.345,67" -> "12345.67"
    txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except Exception:
        return 0.0

def _abs_url(href: Optional[str]) -> str:
    if not href:
        return "#"
    if href.startswith("http"):
        return href
    return BASE.rstrip("/") + "/" + href.lstrip("/")

def _parse_candidates(soup: BeautifulSoup) -> List[Dict]:
    """
    Intenta múltiples layouts comunes:
      - Magento: div.product-item, a.product-item-link, span.price, img
      - TiendaNube/Shopify-like: a.js-product-card / .grid-product__content
      - Genérico: cualquier 'article' o 'div' con precio y título.
    """
    items = []

    # 1) Magento-like
    for card in soup.select("li.product-item, div.product-item, div.item.product-item"):
        try:
            a = card.select_one("a.product-item-link, a.product.photo.product-item-photo, a")
            name = (a.get_text(strip=True) if a else "") or card.get_text(" ", strip=True)
            url = _abs_url(a.get("href")) if a and a.has_attr("href") else "#"
            # precios
            price_el = card.select_one("span.price, span.price-final_price, .price")
            price_txt = price_el.get_text(strip=True) if price_el else ""
            price = _to_float_ars(price_txt)
            # imagen
            img = card.select_one("img")
            img_url = img.get("data-src") or img.get("src") if img else ""
            items.append((name, url, img_url, price))
        except Exception:
            continue

    # 2) TiendaNube / Shopify-like
    if not items:
        for card in soup.select("a.js-product-card, .grid-product__content, .product-card"):
            try:
                # ancla principal
                a = card if card.name == "a" else card.select_one("a")
                name = (a.get_text(strip=True) if a else "") or card.get_text(" ", strip=True)
                url = _abs_url(a.get("href")) if a and a.has_attr("href") else "#"
                # precio
                price_el = card.select_one(".price, .money, [class*='price']")
                price_txt = price_el.get_text(strip=True) if price_el else ""
                price = _to_float_ars(price_txt)
                # imagen
                img = card.select_one("img")
                img_url = (img.get("srcset") or img.get("data-src") or img.get("src") or "").split(" ")[0]
                items.append((name, url, img_url, price))
            except Exception:
                continue

    # 3) Genérico (fallback)
    if not items:
        for card in soup.select("article, div[class*='product'], li"):
            try:
                txt = card.get_text(" ", strip=True)
                if not txt: 
                    continue
                # nombre: heurístico — primer heading o enlace
                h = card.select_one("h3, h2, h4, a")
                name = h.get_text(strip=True) if h else txt[:120]
                a = card.select_one("a")
                url = _abs_url(a.get("href")) if a and a.has_attr("href") else "#"
                # precio: primer número con formato moneda
                price = 0.0
                price_el = card.find(string=PRICE_RE) or txt
                price = _to_float_ars(str(price_el))
                # imagen
                img = card.select_one("img")
                img_url = img.get("src") if img else ""
                # umbral: descartar tarjetas sin precio
                if price > 0 and name and len(name) > 2:
                    items.append((name, url, img_url, price))
            except Exception:
                continue

    results = []
    for (name, url, img_url, price) in items:
        results.append({
            "busqueda": "",  # lo setea el caller si necesita
            "sitio": "TheGamerShop",
            "nombre": name,
            "precio_numeric": float(price or 0),
            "precio_raw": str(price),
            "moneda": "ARS",
            "url": url,
            "imagen": img_url or "",
            "actualizado_en": _fmt_iso_now_ba(),
            "es_tgs": True
        })
    return results

def buscar_en_tgs(producto: str) -> List[Dict]:
    """
    Intenta varios endpoints/estrategias:
      1) /search?q=term
      2) /buscar?q=term
      3) /catalogsearch/result/?q=term
    Si alguno responde con listado HTML, parsea con selectores robustos.
    """
    term = (producto or "").strip()
    if not term:
        return []

    logging.info(f"-> Buscando en TGS (HTTP) para '{term}' ...")
    endpoints = [
        f"{BASE}/search?q={requests.utils.quote(term)}",
        f"{BASE}/buscar?q={requests.utils.quote(term)}",
        f"{BASE}/catalogsearch/result/?q={requests.utils.quote(term)}",
    ]

    for url in endpoints:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200 or not r.text:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            parsed = _parse_candidates(soup)
            if parsed:
                # poné la búsqueda en cada ítem para track
                for it in parsed:
                    it["busqueda"] = term.lower()
                logging.info(f"-> TGS OK con {url}. {len(parsed)} productos.")
                return parsed
        except requests.exceptions.RequestException as e:
            logging.warning(f"-> TGS endpoint falló {url}: {e}")
            continue
        except Exception as e:
            logging.warning(f"-> TGS parse error en {url}: {e}")
            continue

    logging.info("-> TGS sin resultados (HTTP).")
    return []
