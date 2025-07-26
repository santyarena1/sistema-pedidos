import asyncio
from playwright.async_api import async_playwright

# Quitamos 'formatear_precio' ya que el formateo ahora lo hace routes/buscar.py
# from utils.format import formatear_precio

async def buscar_en_maximus(termino_busqueda):
    """
    Busca un producto en Maximus de forma asíncrona, manteniendo
    la lógica original. No interactúa con la base de datos.
    """
    nombre_tienda = "Maximus"
    print(f"-> Buscando en {nombre_tienda}...")

    # Mantenemos tu lógica para construir la URL
    query = termino_busqueda.replace(" ", "%20")
    url = f"https://www.maximus.com.ar/Productos/maximus.aspx?/CAT=-1/SCAT=-1/M=-1/BUS={query}/OR=1/PAGE=1/"
    resultados = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Mantenemos tu lógica para bloquear recursos pesados
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ["image", "stylesheet", "font", "media"]
                else route.continue_(),
            )

            # Mantenemos tu lógica de navegación y espera
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(1500)

            # Mantenemos tu selector de items exacto
            items = page.locator("div.col-md-prod")
            count = await items.count()

            if count == 0:
                print(f"-> No se encontraron productos en {nombre_tienda} para '{termino_busqueda}'.")
                await browser.close()
                return []

            for i in range(count):
                try:
                    # Mantenemos tus selectores para nombre, precio y el ID del producto
                    nombre = await items.nth(i).locator("span.title-prod").text_content()
                    precio = await items.nth(i).locator("div.price").text_content()
                    prod_id = await items.nth(i).get_attribute("id")

                    if nombre and precio:
                        # Mantenemos tu lógica de cálculo de precio, incluyendo el ajuste
                        valor_numerico = float(precio.replace("$", "").replace(".", "").replace(",", "."))
                        valor_numerico *= 0.95  # Mantenemos tu ajuste

                        # Mantenemos tu lógica para construir el link
                        link_producto = f"https://www.maximus.com.ar/Producto/{prod_id}" if prod_id else ""
                        
                        # --- CORRECCIÓN CLAVE AQUÍ ---
                        # Preparamos el diccionario para guardar en la BD.
                        # La clave 'precio' contiene el número puro para que la BD lo acepte.
                        resultados.append({
                            "busqueda": termino_busqueda,
                            "sitio": nombre_tienda,
                            "producto": nombre.strip(),
                            "precio": valor_numerico, # Precio NUMÉRICO para la BD
                            "link": link_producto
                        })
                except Exception as e:
                    # Mantenemos tu manejo de errores para items individuales
                    print(f"-> ADVERTENCIA: Saltando un item en {nombre_tienda}. Error: {e}")

            await browser.close()

    except Exception as e:
        print(f"-> ERROR GRAVE buscando en {nombre_tienda}: {e}")
        return []

    print(f"-> Búsqueda en {nombre_tienda} finalizada. {len(resultados)} productos encontrados.")
    return resultados

# Mantenemos tu bloque de prueba intacto
if __name__ == '__main__':
    async def probar():
        productos = await buscar_en_maximus("Ryzen 5 5600G")
        if productos:
            for p in productos:
                print(p)

    asyncio.run(probar())