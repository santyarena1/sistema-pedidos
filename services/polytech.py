import os
import pandas as pd
import tempfile
from playwright.sync_api import sync_playwright
import time

def obtener_lista_completa_polytech():
    """
    Obtiene la lista de precios de Polytech, con un sistema de reintentos
    para manejar la lentitud en la descarga del archivo.
    """
    nombre_tienda = "POLYTECH"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")
    
    with sync_playwright() as p:
        # Dejamos el navegador visible para asegurar compatibilidad
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            # 1. Login
            print("-> Haciendo login en Polytech...")
            page.goto("https://www.gestionresellers.com.ar/login", timeout=60000)
            page.fill("#user_name", "AAP0525")
            page.fill("#password", "HGGJSMQ3")
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle", timeout=60000)

            # 2. Obtenemos el dólar de la página
            print("-> Obteniendo valor del dólar desde la página...")
            dolar_element = page.wait_for_selector("#cotizacion_moneda", timeout=10000)
            dolar_text = dolar_element.text_content()
            valor_dolar_str = dolar_text.split("$")[1].strip().replace(",", "")
            valor_dolar = float(valor_dolar_str)
            print(f"-> Valor del Dólar obtenido y guardado: {valor_dolar}")
            
            # 3. Descargar Excel con lógica de reintentos
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"-> Intento de descarga #{attempt + 1}/{max_retries}...")
                    # Aumentamos el timeout de la descarga a 3 minutos (180000 ms)
                    with page.expect_download(timeout=180000) as download_info:
                        # Hacemos clic en el enlace para descargar
                        page.click("a[href='/extranet/exportar/excel?lbv=']")
                    
                    download = download_info.value
                    print("-> Descarga completada con éxito.")
                    
                    # Si la descarga fue exitosa, salimos del bucle de reintentos
                    break
                
                except Exception as e:
                    print(f"-> El intento #{attempt + 1} falló: {e}")
                    if attempt < max_retries - 1:
                        print("-> La página parece trabada. Refrescando y reintentando en 10 segundos...")
                        page.reload() # Refrescamos la página
                        page.wait_for_load_state("networkidle", timeout=60000) # Esperamos a que recargue
                        time.sleep(10)
                    else:
                        print("-> Se alcanzaron los máximos reintentos. Abortando.")
                        raise # Lanzamos el último error para que falle el script

            # 4. Procesamos el archivo descargado
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, download.suggested_filename)
                download.save_as(filepath)
                browser.close()

                print("-> Procesando el archivo descargado...")
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
            print(f"-> ERROR GRAVE en el proceso de {nombre_tienda}: {e}")
            if 'browser' in locals() and browser.is_connected():
                browser.close()
            return []

# Bloque de prueba
if __name__ == '__main__':
    def probar():
        print("Probando la obtención de la lista completa de Polytech...")
        lista_productos = obtener_lista_completa_polytech()
        if lista_productos:
            print(f"Se obtuvieron {len(lista_productos)} productos.")
        else:
            print("No se pudieron obtener productos.")

    probar()