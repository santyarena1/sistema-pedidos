import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import tempfile
import os
import time

def obtener_lista_completa_air():
    nombre_tienda = "AIR"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True) # FORZAMOS MODO HEADLESS
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(60000) # Timeout de 60 segundos para todo

            print(f"-> {nombre_tienda}: Haciendo login...")
            page.goto("https://ar.air-intra.com/index_.htm")
            page.fill("#urbid", "B5763")
            page.fill("#urbpass", "30707589449")
            page.click("#urblogin")
            page.wait_for_load_state("networkidle")

            print(f"-> {nombre_tienda}: Obteniendo valor del dólar...")
            dolar_element = page.wait_for_selector("#labeldolar")
            dolar_text = dolar_element.text_content()
            
            valor_dolar_str = dolar_text.split(":")[1].strip().replace(",", "")
            valor_dolar = float(valor_dolar_str)
            print(f"-> {nombre_tienda}: Valor del Dólar obtenido: {valor_dolar}")
            
            print(f"-> {nombre_tienda}: Navegando a descargas...")
            page.goto("https://ar.air-intra.com/2022/")
            page.click("text=+ Productos")
            page.click("text=+ Descargas")

            print(f"-> {nombre_tienda}: Iniciando descarga CSV...")
            with page.expect_download() as download_info:
                page.click("text=Listas (CSV)")
            download = download_info.value
            print(f"-> {nombre_tienda}: Descarga completada.")

            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, download.suggested_filename)
                download.save_as(filepath)
                browser.close()

                print("-> Procesando el archivo CSV...")
                df = pd.read_csv(filepath, sep=",", encoding="latin1").fillna("")

                resultados = []
                for _, row in df.iterrows():
                    try:
                        descripcion = row.get("Descripcion", "").strip()
                        precio_base_str = str(row.get("lista3", "0")).replace(",", ".")
                        iva_str = str(row.get("IVA", "0")).replace(",", ".")

                        if not descripcion or not precio_base_str or precio_base_str == "0":
                            continue
                        
                        precio_base = float(precio_base_str)
                        iva = float(iva_str)
                        precio_final = round(precio_base * (1 + iva / 100) * valor_dolar, 2)
                        
                        resultados.append({
                            "busqueda": "LISTA_COMPLETA",
                            "sitio": nombre_tienda,
                            "producto": descripcion,
                            "precio": precio_final,
                            "link": "https://ar.air-intra.com"
                        })
                    except (ValueError, TypeError):
                        continue

            print(f"-> Lista de {nombre_tienda} procesada. {len(resultados)} productos encontrados.")
            return resultados

        except Exception as e:
            print(f"--- ERROR GRAVE en el proceso de {nombre_tienda}: {e} ---")
            if 'browser' in locals() and browser.is_connected():
                browser.close()
            return []