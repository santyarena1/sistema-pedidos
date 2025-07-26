import asyncio
from playwright.async_api import async_playwright

# Quitamos 'formatear_precio' ya que el formateo ahora lo hace routes/buscar.py
# from utils.format import formatear_precio

async def buscar_en_compragamer(termino_busqueda):
    """
    Busca un producto en CompraGamer de forma asíncrona, manteniendo
    la lógica original. No interactúa con la base de datos.
    """
    nombre_tienda = "CompraGamer"
    print(f"-> Buscando en {nombre_tienda}...")
    
    # Mantenemos tu URL y lógica de búsqueda originales
    url = f"https://compragamer.com/productos?criterio={termino_busqueda.replace(' ', '+')}"
    resultados = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Mantenemos tu lógica para bloquear recursos
            await page.route(
                "**/*", 
                lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_()
            )

            # Mantenemos tu lógica de navegación y espera
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(1500)

            # Mantenemos tus selectores exactos
            items = page.locator("cgw-product-card")
            count = await items.count()
            
            if count == 0:
                print(f"-> No se encontraron productos en {nombre_tienda} para '{termino_busqueda}'.")
                await browser.close()
                return []

            for i in range(count):
                try:
                    nombre = await items.nth(i).locator("h3.product-card__title").text_content()
                    precio = await items.nth(i).locator("span.txt_price").text_content()
                    link = await items.nth(i).locator("a[href^='/producto/']").first.get_attribute("href")

                    if nombre and precio:
                        # Mantenemos tu cálculo de precio exacto, incluyendo el ajuste de 1.018
                        valor_numerico = float(precio.strip().replace("$", "").replace(".", "").replace(",", ".")) * 1.018
                        
                        # --- CORRECCIÓN CLAVE AQUÍ ---
                        # Preparamos el diccionario para guardar en la BD.
                        # La clave 'precio' contiene el número puro para que la BD lo acepte.
                        # Eliminamos 'precio_numeric' y el precio formateado.
                        resultados.append({
                            "busqueda": termino_busqueda,
                            "sitio": nombre_tienda,
                            "producto": nombre.strip(),
                            "precio": valor_numerico,  # Precio NUMÉRICO para la BD
                            "link": f"https://compragamer.com{link}" if link else ""
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
        productos = await buscar_en_compragamer("Ryzen 5 5600G")
        if productos:
            for p in productos:
                print(p)
    
    asyncio.run(probar())