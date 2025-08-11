# -*- coding: utf-8 -*-
# services/thegamershop_scraper.py

import re
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def _parse_price(texto: str) -> float:
    """Convierte '$ 123.456,78' a float 123456.78 de forma tolerante."""
    s = re.sub(r"[^\d,\.]+", "", texto or "")
    if not s:
        return 0.0
    # Quitamos separador de miles '.' y usamos ',' como decimal
    return float(s.replace(".", "").replace(",", "."))

def buscar_en_tgs(producto: str) -> List[Dict]:
    """
    Scraper de TheGamerShop con Selenium y selectores flexibles.
    - Intenta primero contenedores con data-attributes.
    - Si no hay, recurre a contenedores 'product' genéricos.
    - Extrae nombre, precio, link e imagen con distintos fallbacks.
    """
    print(f"-> TheGamerShop: buscando '{producto}'...")
    resultados: List[Dict] = []
    driver = None
    try:
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

        query = re.sub(r"\s+", "+", producto.strip())
        url = f"https://www.thegamershop.com.ar/buscar/?q={query}"
        driver.get(url)

        wait = WebDriverWait(driver, 25)

        # Espera flexible: alguno de estos selectores debe aparecer
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-product-name], div[class*='product']")
                )
            )
        except Exception:
            print("   - No aparecieron tarjetas de producto.")
            return []

        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-product-name]")  # preferido
        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "div[class*='product']")  # fallback

        for card in cards:
            try:
                # Nombre
                nombre = card.get_attribute("data-product-name")
                if not nombre:
                    t = card.find_elements(By.CSS_SELECTOR, "h2, h3, a, .title, .product-title")
                    nombre = (t[0].text.strip() if t else card.text.split("\n")[0].strip())

                # Precio
                precio_raw = card.get_attribute("data-product-price")
                if not precio_raw:
                    m = re.search(r"\$[\s]*[\d\.\,]+", card.text)
                    precio_raw = m.group(0) if m else "$0"
                precio = _parse_price(precio_raw)

                # Link
                link = card.get_attribute("data-product-url") or ""
                if not link:
                    for a in card.find_elements(By.TAG_NAME, "a"):
                        href = a.get_attribute("href")
                        if href and "thegamershop.com.ar" in href:
                            link = href
                            break
                if not link:
                    link = "#"

                # Imagen
                imagen = ""
                imgs = card.find_elements(By.TAG_NAME, "img")
                if imgs:
                    imagen = imgs[0].get_attribute("src") or ""

                resultados.append({
                    "busqueda": producto.lower(),
                    "sitio": "The Gamer Shop",
                    "producto": nombre,
                    "precio": precio,
                    "link": link,
                    "imagen": imagen,
                    "marca": "",
                    "precio_anterior": 0,
                    "porcentaje_descuento": 0
                })
            except Exception:
                # Si una tarjeta falla, no abortamos toda la búsqueda
                continue

        print(f"-> TheGamerShop OK: {len(resultados)} productos.")
        return resultados

    except Exception as e:
        print(f"[TGS] ERROR: {e}")
        return []
    finally:
        if driver:
            driver.quit()


# ---- Bloque de prueba directa ----
if __name__ == "__main__":
    import sys
    term = sys.argv[1] if len(sys.argv) > 1 else "5600g"
    items = buscar_en_tgs(term)
    print(f"TOTAL: {len(items)}")
    if items:
        from pprint import pprint
        pprint(items[0])
