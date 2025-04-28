from playwright.async_api import async_playwright
from db.queries import obtener_desde_db, guardar_en_db
from utils.format import formatear_precio

async def buscar_fullh4rd(producto):
    cache = obtener_desde_db(producto, "FullH4rd")
    if cache:
        return [{**fila, "precio": formatear_precio(fila["precio"])} for fila in cache]

    query = producto.replace(" ", "%20")
    url = f"https://www.fullh4rd.com.ar/cat/search/{query}"
    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # ⚡ Bloquear recursos pesados
        await page.route("**/*", lambda route, request:
            route.abort() if request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_()
        )

        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        items = page.locator("div.item.product-list")
        count = await items.count()

        for i in range(count):
            nombre = await items.nth(i).locator("div.info h3").text_content()
            precio = await items.nth(i).locator("div.price").text_content()
            link = await items.nth(i).locator("a").get_attribute("href")

            if nombre and precio:
                try:
                    precio_limpio = precio.strip().split(" ")[0]
                    valor = float(precio_limpio.replace("$", "").replace(".", "").replace(",", "."))
                except:
                    valor = 0

                guardar_en_db(producto, "FullH4rd", nombre.strip(), valor, f"https://www.fullh4rd.com.ar{link}" if link else "")
                resultados.append({
                    "sitio": "FullH4rd",
                    "producto": nombre.strip(),
                    "precio": formatear_precio(valor),
                    "precio_num": valor,
                    "link": f"https://www.fullh4rd.com.ar{link}" if link else ""
                })

        await browser.close()
    return resultados
