from db.queries import obtener_desde_db, guardar_en_db
from utils.format import formatear_precio
from services.dolar import obtener_dolar_oficial
import requests
import pandas as pd
from io import BytesIO

async def buscar_newbytes(producto):
    cache = obtener_desde_db(producto, "NewBytes")
    if cache:
        return [{**fila, "precio": formatear_precio(fila["precio"])} for fila in cache]

    try:
        valor_dolar = await obtener_dolar_oficial()
        url = "https://api.nb.com.ar/v1/priceListExcel/1f31e11177035cdab4cad5e94e50ea"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content), skiprows=2, engine="openpyxl")
        df.columns = df.columns.str.strip()

        if "DETALLE" not in df.columns or "PRECIO FINAL" not in df.columns:
            return []

        producto_normalizado = producto.lower().replace(" ", "")
        df["normalizado"] = df["DETALLE"].astype(str).str.lower().str.replace(" ", "")
        coincidencias = df[df["normalizado"].str.contains(producto_normalizado)]
        resultados = []

        for _, fila in coincidencias.iterrows():
            try:
                precio_usd = float(str(fila["PRECIO FINAL"]).replace(",", "."))
                precio_ars = round(precio_usd * valor_dolar * 1.04)  # Aumento del 4%
            except:
                precio_ars = 0

            guardar_en_db(producto, "NewBytes", fila["DETALLE"], precio_ars, "https://newbytes.com.ar")
            resultados.append({
                "sitio": "NewBytes",
                "producto": fila["DETALLE"],
                "precio": formatear_precio(precio_ars),
                "precio_num": precio_ars,
                "link": "https://newbytes.com.ar"
            })

        return resultados
    except Exception as e:
        print("Error en buscar_newbytes:", e)
        return []
