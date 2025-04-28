from playwright.async_api import async_playwright
from db.queries import obtener_desde_db, guardar_en_db
from utils.format import formatear_precio

async def buscar_compugamer(producto):
    cache = obtener_desde_db(producto, "CompraGamer")
    if cache:
        return [{**fila, "precio": formatear_precio(fila["precio"])} for fila in cache]

    query = producto.replace(" ", "+")
    url = f"https://compragamer.com/productos?criterio={query}"
    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Crear nueva página
        page = await context.new_page()

        # 🚫 Bloquear recursos innecesarios
        await page.route("**/*", lambda route, request: 
            route.abort() if request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_()
        )

        # 🔎 Ir a la página
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1500)  # breve espera para asegurar carga mínima

        items = page.locator("cgw-product-card")
        count = await items.count()

        for i in range(count):
            nombre = await items.nth(i).locator("h3.product-card__title").text_content()
            precio = await items.nth(i).locator("span.txt_price").text_content()
            link = await items.nth(i).locator("a[href^='/producto/']").first.get_attribute("href")

            if nombre and precio:
                try:
                    valor = float(precio.strip().replace("$", "").replace(".", "").replace(",", ".")) * 1.045
                except:
                    valor = 0

                # Guardar en base de datos
                guardar_en_db(producto, "CompraGamer", nombre.strip(), valor, f"https://compragamer.com{link}" if link else "")

                resultados.append({
                    "sitio": "CompraGamer",
                    "producto": nombre.strip(),
                    "precio": formatear_precio(valor),
                    "precio_num": valor,
                    "link": f"https://compragamer.com{link}" if link else ""
                })

        await browser.close()
    return resultados
