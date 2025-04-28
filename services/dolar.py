from playwright.async_api import async_playwright

async def obtener_dolar_oficial():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://dolarhoy.com/cotizaciondolaroficial", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        valor_div = await page.locator("div.cotizacion_moneda .tile.cotizacion_value div:has-text('Venta')").locator("..").locator(".value").nth(1).text_content()
        valor = valor_div.replace("$", "").replace(".", "").replace(",", ".").strip()
        return float(valor)