import os
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from db.connection import conn

def actualizar_lista_polytech():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Navegador visible
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1. Login
        page.goto("https://www.gestionresellers.com.ar/login")
        page.fill("#user_name", "AAP0525")
        page.fill("#password", "HGGJSMQ3")

        page.click("input[type='submit']")
        page.wait_for_timeout(3000)

        # 2. Descargar Excel desde botón "Exportar lista completa"
        
        with page.expect_download(timeout=60000) as download_info:
            page.click("a[href='/extranet/exportar/excel?lbv=']")
        download = download_info.value
        filename = download.suggested_filename
        filepath = f"/tmp/{filename}"
        download.save_as(filepath)
        browser.close()

        # 3. Obtener valor del dólar blue
        valor_dolar = requests.get("https://api.bluelytics.com.ar/v2/latest").json()["blue"]["value_avg"]
        print(f"💵 Dólar blue: {valor_dolar}")

        # 4. Leer el archivo descargado
        df = pd.read_csv(filepath, sep='\t', encoding='latin1').fillna("")
        print(df.columns.tolist())


        registros = []

        for _, row in df.iterrows():
            try:
                descripcion = str(row.get("Descripción", "")).strip()
                precio_usd = row.get("Precio c/IVA (DOLAR (U$S))", 0) 
                iva = 21.0  # Asumido por ahora

                if not descripcion or not precio_usd:
                    continue

                precio_final = round(float(precio_usd) * (1 + iva / 100) * valor_dolar, 2)

                registros.append((
                    descripcion,
                    descripcion,
                    "POLYTECH",
                    precio_final,
                    "https://www.gestionresellers.com.ar",
                    datetime.now()
                ))
            except Exception as e:
                print(f"❌ Error en fila: {row}\n{e}")

        # 5. Guardar en base de datos
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM productos WHERE sitio = 'POLYTECH'")
                cur.executemany("""
                    INSERT INTO productos (producto, busqueda, sitio, precio, link, actualizado)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, registros)
                conn.commit()
                print(f"✅ Se cargaron {len(registros)} productos de POLYTECH")
        except Exception as e:
            conn.rollback()
            print("❌ Error al guardar en la base:", e)
