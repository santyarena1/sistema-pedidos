import requests
from bs4 import BeautifulSoup

def obtener_lista_completa_thegamershop(limite_max=80):
    """
    Obtiene una lista completa (hasta 'limite_max' productos) de TheGamerShop.
    Extrae los datos de las tarjetas de productos en la página principal.
    """
    nombre_tienda = "TheGamerShop"
    resultados = []
    try:
        url = "https://www.thegamershop.com.ar/"
        resp = requests.get(url, timeout=30)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=30)

        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Cada tarjeta de producto contiene data-nombre, data-precio y data-marca
        for card in soup.find_all("div", class_="prod-cat"):
            nombre = card.get("data-nombre", "").strip()
            precio_raw = card.get("data-precio", "").strip()
            if not nombre or not precio_raw:
                continue
            try:
                precio = float(precio_raw)
            except ValueError:
                continue

            link = ""
            link_tag = card.find("a", href=True)
            if link_tag:
                link = link_tag["href"]

            imagen = ""
            img_tag = card.find("img")
            if img_tag:
                # Algunas imágenes usan data-src para carga diferida
                imagen = img_tag.get("data-src") or img_tag.get("src", "")

            marca = card.get("data-marca", "Sin Marca")

            resultados.append({
                "busqueda": "LISTA_COMPLETA",
                "sitio": nombre_tienda,
                "producto": nombre,
                "precio": precio,
                "link": link,
                "imagen": imagen,
                "marca": marca,
                "precio_anterior": 0,
                "porcentaje_descuento": 0
            })

            if len(resultados) >= limite_max:
                break

        print(f"-> Proceso de {nombre_tienda} finalizado. {len(resultados)} productos obtenidos.")
        return resultados

    except Exception as e:
        print(f"--- ERROR en el scraper de {nombre_tienda}: {e} ---")
        return []
