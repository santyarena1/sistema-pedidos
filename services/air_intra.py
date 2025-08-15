# -*- coding: utf-8 -*-
# services/air_scraper.py
# Scraper de AIR sin Playwright: HTTP + BeautifulSoup + JSON-LD.
# Recolecta "lista completa" descubriendo URLs desde sitemap o listados.
# Compatible con Render (sin binarios de navegador).

from __future__ import annotations
import os
import re
import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

try:
    from zoneinfo import ZoneInfo
    TZ_BA = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    TZ_BA = None

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0 Safari/537.36"),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PRICE_RE = re.compile(r"([\$S]?\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)")
NUM_RE = re.compile(r"(\d+(?:[.,]\d{2})?)")

def _ts_ba_iso() -> str:
    try:
        now = datetime.now(tz=TZ_BA) if TZ_BA else datetime.now()
        return now.isoformat()
    except Exception:
        return datetime.utcnow().isoformat() + "Z"

def _to_float_ars(txt: str) -> float:
    if not txt:
        return 0.0
    # "12.345,67" -> 12345.67
    s = txt.strip()
    m = PRICE_RE.search(s)
    if m:
        s = m.group(1)
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def _abs(base: str, href: Optional[str]) -> str:
    if not href:
        return "#"
    return href if href.startswith("http") else urljoin(base.rstrip("/") + "/", href.lstrip("/"))

def _get(url: str, timeout: int = 30) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r
    except requests.RequestException as e:
        logging.warning(f"[AIR] GET fallo {url}: {e}")
    return None

def _parse_jsonld_product(soup: BeautifulSoup) -> Dict[str, str]:
    # Busca scripts con Product y extrae lo esencial
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
            if isinstance(data, list):
                # algunos sitios ponen lista
                for entry in data:
                    res = _from_ld_entry(entry)
                    if res:
                        return res
            else:
                res = _from_ld_entry(data)
                if res:
                    return res
        except Exception:
            continue
    return {}

def _from_ld_entry(entry: dict) -> Optional[Dict[str, str]]:
    t = entry.get("@type") or entry.get("@type".lower())
    if isinstance(t, list):
        t = [str(x).lower() for x in t]
        is_prod = any("product" in x for x in t)
    else:
        is_prod = str(t).lower() == "product"
    if not is_prod:
        return None
    name = entry.get("name") or ""
    image = entry.get("image") or ""
    # offers puede ser dict o lista
    price = ""
    currency = "ARS"
    offers = entry.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price") or ""
        currency = offers.get("priceCurrency") or "ARS"
    elif isinstance(offers, list) and offers:
        o0 = offers[0] or {}
        price = o0.get("price") or ""
        currency = o0.get("priceCurrency") or "ARS"
    return {"name": name, "image": image, "price": str(price), "currency": currency}

def _parse_price_fallback(soup: BeautifulSoup) -> str:
    # Busca precios en elementos comunes
    candidates = [
        ".price .amount", ".price .money", "span.money", "span.price", ".product-price",
        "[data-price]", "[class*='price']"
    ]
    for sel in candidates:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    # prueba texto suelto
    txt = soup.get_text(" ", strip=True)
    m = PRICE_RE.search(txt)
    return m.group(1) if m else ""

def _parse_name_fallback(soup: BeautifulSoup) -> str:
    for sel in ["h1.product-title", "h1", "h2.product-title", "h2", "title"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return ""

def _parse_image_fallback(soup: BeautifulSoup) -> str:
    # Intenta og:image
    og = soup.select_one("meta[property='og:image']")
    if og and og.get("content"):
        return og.get("content")
    # o la primera imagen "grande"
    img = soup.select_one("img[src*='product'], img[src*='large'], img[src]")
    if img and img.get("src"):
        return img.get("src")
    return ""

def _discover_product_urls(base: str) -> List[str]:
    urls: List[str] = []
    # 1) sitemap principal
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-products.xml", "/sitemap_products_1.xml"]:
        r = _get(urljoin(base, path))
        if not r:
            continue
        soup = BeautifulSoup(r.text, "xml")
        for loc in soup.find_all("loc"):
            u = (loc.get_text() or "").strip()
            if not u:
                continue
            if any(k in u.lower() for k in ["product", "producto", "item", "catalog", "producto"]):
                urls.append(u)
        if urls:
            return list(dict.fromkeys(urls))  # único y temprano
    # 2) fallback: páginas de listados “conocidas”
    listados = [
        "/collections/all",
        "/productos",
        "/catalogsearch/result/?q=a",   # letra “a” para forzar listado
        "/search?q=a",
    ]
    seen = set()
    for path in listados:
        r = _get(urljoin(base, path))
        if not r:
            continue
        soup = BeautifulSoup(r.text, "lxml")
        # vínculos a productos
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            u = _abs(base, href)
            if u in seen:
                continue
            # heurística simple de URL de producto
            if any(k in u.lower() for k in ["product", "producto", "item", "catalog"]):
                urls.append(u)
                seen.add(u)
        # no saturar
        time.sleep(0.2)
    return list(dict.fromkeys(urls))

def _parse_product_page(base: str, url: str) -> Optional[Dict]:
    r = _get(url)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")

    ld = _parse_jsonld_product(soup)
    name = ld.get("name") or _parse_name_fallback(soup)
    image = ld.get("image") or _parse_image_fallback(soup)
    price_raw = ld.get("price") or _parse_price_fallback(soup)
    currency = ld.get("currency") or "ARS"

    price = _to_float_ars(str(price_raw))
    if not name or price <= 0:
        # descarta páginas sin precio claro
        return None

    return {
        "busqueda": "",  # en “lista completa” no hay query; tu capa superior lo ignora
        "sitio": "AIR",
        "sku": None,
        "nombre": name,
        "precio_numeric": price,
        "precio_raw": str(price_raw),
        "moneda": currency or "ARS",
        "url": url,
        "imagen": image,
        "actualizado_en": _ts_ba_iso(),
        "es_tgs": False
    }

def obtener_lista_completa_air() -> List[Dict]:
    base = os.getenv("AIR_BASE_URL", "").strip()
    if not base:
        raise ValueError("Definí la variable de entorno AIR_BASE_URL con la URL base del mayorista AIR (ej: https://air-mayorista.com).")
    if not base.startswith("http"):
        base = "https://" + base

    logging.info("-> Obteniendo lista completa de AIR (HTTP sin Playwright)...")
    urls = _discover_product_urls(base)
    logging.info(f"-> AIR: descubiertas {len(urls)} URLs candidatas de producto.")
    out: List[Dict] = []
    for i, url in enumerate(urls, start=1):
        data = _parse_product_page(base, url)
        if data:
            out.append(data)
        if i % 50 == 0:
            logging.info(f"   Progreso AIR: {i}/{len(urls)}")
        time.sleep(0.15)  # throttle sutil para no agredir
    logging.info(f"-> AIR finalizado. Productos válidos: {len(out)}")
    return out

# Opcional: búsqueda ad-hoc filtrando por nombre una vez recolectada la lista
def buscar_en_air(termino: str) -> List[Dict]:
    termino = (termino or "").strip().lower()
    if not termino:
        return []
    full = obtener_lista_completa_air()
    return [p for p in full if termino in (p.get("nombre","").lower())]
