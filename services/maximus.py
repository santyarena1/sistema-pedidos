from playwright.async_api import async_playwright
from db.queries import obtener_desde_db, guardar_en_db
from utils.format import formatear_precio

async def buscar_maximus(producto):
    cache = obtener_desde_db(producto, "Maximus")
    if cache:
        return [{**fila, "precio": formatear_precio(fila["precio"])} for fila in cache]

    query = producto.replace(" ", "%20")
    url = f"https://www.maximus.com.ar/Productos/maximus.aspx?/CAT=-1/SCAT=-1/M=-1/BUS={query}/OR=1/PAGE=1/"
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

        items = page.locator("div.col-md-prod")
        count = await items.count()

        for i in range(count):
            try:
                nombre = await items.nth(i).locator("span.title-prod").text_content()
                precio = await items.nth(i).locator("div.price").text_content()
                prod_id = await items.nth(i).get_attribute("id")

                if nombre and precio:
                    try:
                        valor = float(precio.replace("$", "").replace(".", "").replace(",", "."))
                        valor *= 0.95  # Ajuste que ya usabas
                    except:
                        valor = 0

                    guardar_en_db(producto, "Maximus", nombre.strip(), valor, f"https://www.maximus.com.ar/Producto/{prod_id}" if prod_id else "")
                    resultados.append({
                        "sitio": "Maximus",
                        "producto": nombre.strip(),
                        "precio": formatear_precio(valor),
                        "precio_num": valor,
                        "link": f"https://www.maximus.com.ar/Producto/{prod_id}" if prod_id else ""
                    })
            except:
                continue

        await browser.close()
    return resultados
