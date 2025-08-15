import os
import pandas as pd
import tempfile
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

def obtener_lista_completa_polytech():
    nombre_tienda = "POLYTECH"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True) # FORZAMOS MODO HEADLESS
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(60000)

            print(f"-> {nombre_tienda}: Haciendo login...")
            page.goto("https://www.gestionresellers.com.ar/login")
            page.fill("#user_name", "AAP0525")
            page.fill("#password", "HGGJSMQ3")
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            print(f"-> {nombre_tienda}: Obteniendo valor del dólar...")
            dolar_element = page.wait_for_selector("#cotizacion_moneda")
            dolar_text = dolar_element.text_content()
            valor_dolar_str = dolar_text.split("$")[1].strip().replace(",", "")
            valor_dolar = float(valor_dolar_str)
            print(f"-> {nombre_tienda}: Valor del Dólar obtenido: {valor_dolar}")
            
            print(f"-> {nombre_tienda}: Iniciando descarga Excel...")
            with page.expect_download(timeout=180000) as download_info: # Timeout largo para la descarga
                page.click("a[href='/extranet/exportar/excel?lbv=']")
            download = download_info.value
            print(f"-> {nombre_tienda}: Descarga completada.")

            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, download.suggested_filename)
                download.save_as(filepath)
                browser.close()

                print("-> Procesando el archivo Excel descargado...")
                df = pd.read_csv(filepath, sep='\t', encoding='latin1').fillna("")

                resultados = []
                for _, row in df.iterrows():
                    try:
                        descripcion = str(row.get("Descripción", "")).strip()
                        precio_usd_str = str(row.get("Precio c/IVA (DOLAR (U$S))", "0.0")).replace(",", ".")
                        if not descripcion or not precio_usd_str or float(precio_usd_str) == 0:
                            continue
                        
                        precio_usd = float(precio_usd_str)
                        precio_final = round(precio_usd * valor_dolar, 2)
                        
                        resultados.append({
                            "busqueda": "LISTA_COMPLETA",
                            "sitio": nombre_tienda,
                            "producto": descripcion,
                            "precio": precio_final,
                            "link": "https://www.gestionresellers.com.ar"
                        })
                    except (ValueError, TypeError, AttributeError):
                        continue

            print(f"-> Lista de {nombre_tienda} procesada. {len(resultados)} productos encontrados.")
            return resultados

        except Exception as e:
            print(f"--- ERROR GRAVE en el proceso de {nombre_tienda}: {e} ---")
            if browser and browser.is_connected():
                browser.close()
            return []