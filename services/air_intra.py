import os
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from db.connection import conn
import requests


def actualizar_lista_air():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1. Login
        page.goto("https://ar.air-intra.com/index_.htm")
        page.fill("#urbid", "B5763")
        page.fill("#urbpass", "30707589449")
        page.click("#urblogin")
        time.sleep(3)

        # 2. Ir al menú de descargas
        page.goto("https://ar.air-intra.com/2022/")
        page.click("text=+ Productos")
        time.sleep(1)
        page.click("text=+ Descargas")
        time.sleep(1)
        with page.expect_download() as download_info:
            page.click("text=Listas (CSV)")
        download = download_info.value
        path = download.path()
        filename = download.suggested_filename

        # Guardar archivo descargado
        download.save_as(f"/tmp/{filename}")
        browser.close()

        # 3. Leer y procesar el CSV
        df = pd.read_csv(f"/tmp/{filename}", sep=",", encoding="latin1").fillna("")




        registros = []
    valor_dolar = requests.get("https://api.bluelytics.com.ar/v2/latest").json()["blue"]["value_avg"]
    print(f"💸 Dólar blue actual: {valor_dolar}")

    for _, row in df.iterrows():
        try:
            descripcion = row.get("Descripcion", "").strip()
            precio_base = row.get("lista1")
            iva = row.get("IVA")

            if isinstance(precio_base, str):
                precio_base = float(precio_base.replace(",", "."))
            if isinstance(iva, str):
                iva = float(iva.replace(",", "."))

            precio_final = round(precio_base * (1 + iva / 100) * valor_dolar, 2)



            registros.append((
                descripcion,      # producto
                descripcion,      # busqueda
                "AIR",            # sitio ✅ CORRECTO
                precio_final,     # precio
                "https://ar.air-intra.com",  # link fijo
                datetime.now()
            ))

        except Exception as e:
            print(f"❌ Error con fila: {row}\n{e}")



        
        # 4. Insertar en base de datos
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM productos WHERE sitio = 'AIR'")
                cur.executemany("""
                    INSERT INTO productos (producto, busqueda, sitio, precio, link, actualizado)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, registros)
                conn.commit()
                print(f"✅ Se cargaron {len(registros)} productos de AIR")
        except Exception as e:
            conn.rollback()
            print("❌ Error al guardar en la base:", e)

