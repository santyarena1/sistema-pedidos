import pandas as pd
from playwright.sync_api import sync_playwright
import tempfile
import os
import time

def obtener_lista_completa_air():
    """
    Obtiene la lista de precios de AIR Computers, usando la cotización
    del dólar de la página y leyendo las columnas de datos correctas.
    """
    nombre_tienda = "AIR"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")

    with sync_playwright() as p:
        # Dejamos el navegador visible para asegurar que no haya bloqueos
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            # 1. Login
            print("-> Haciendo login en AIR...")
            page.goto("https://ar.air-intra.com/index_.htm", timeout=60000)
            page.fill("#urbid", "B5763")
            page.fill("#urbpass", "30707589449")
            page.click("#urblogin")
            page.wait_for_load_state("networkidle", timeout=30000)

            # 2. Obtenemos el dólar de la página
            print("-> Obteniendo valor del dólar desde la página...")
            dolar_element = page.wait_for_selector("#labeldolar", timeout=10000)
            dolar_text = dolar_element.text_content()
            
            valor_dolar_str = dolar_text.split(":")[1].strip().replace(",", "")
            valor_dolar = float(valor_dolar_str)
            print(f"-> Valor del Dólar obtenido y guardado: {valor_dolar}")
            
            # 3. Descargamos el archivo CSV
            print("-> Navegando a la sección de descargas...")
            page.goto("https://ar.air-intra.com/2022/", timeout=60000)
            page.click("text=+ Productos")
            page.click("text=+ Descargas")

            print("-> Iniciando descarga del archivo CSV...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("text=Listas (CSV)")
            download = download_info.value

            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, download.suggested_filename)
                download.save_as(filepath)
                browser.close()

                # 4. Procesamos el archivo con la columna de precio correcta
                print("-> Procesando el archivo CSV...")
                df = pd.read_csv(filepath, sep=",", encoding="latin1").fillna("")

                resultados = []
                for _, row in df.iterrows():
                    try:
                        descripcion = row.get("Descripcion", "").strip()
                        # --- CORRECCIÓN FINAL AQUÍ ---
                        # Leemos de la columna 'lista3' en lugar de 'lista1'
                        precio_base_str = str(row.get("lista3", "0")).replace(",", ".")
                        # -----------------------------
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
            print(f"-> ERROR GRAVE en el proceso de {nombre_tienda}: {e}")
            if 'browser' in locals() and browser.is_connected():
                browser.close()
            return []

# Bloque de prueba
if __name__ == '__main__':
    def probar():
        print("Probando la obtención de la lista completa de AIR...")
        lista_productos = obtener_lista_completa_air()
        if lista_productos:
            print(f"Se obtuvieron {len(lista_productos)} productos.")
            print("Mostrando los primeros 5:")
            for p in lista_productos[:5]:
                print(p)
        else:
            print("No se pudieron obtener productos.")

    probar()