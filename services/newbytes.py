from db.queries import obtener_desde_db, guardar_en_db
from utils.format import formatear_precio
from services.dolar import obtener_dolar_oficial
import requests
import pandas as pd
from io import BytesIO
from db.connection import conn


async def buscar_newbytes(producto):
    cache = obtener_desde_db(producto, "NewBytes")
    return [
        {**fila, "precio": formatear_precio(fila["precio"])}
        for fila in cache
    ] if cache else []


def actualizar_lista_newbytes():
    try:
        valor_dolar = requests.get("https://api.bluelytics.com.ar/v2/latest").json()["blue"]["value_avg"]
        url = "https://api.nb.com.ar/v1/priceListExcel/1f31e11177035cdab4cad5e94e50ea"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content), skiprows=2, engine="openpyxl")
        df.columns = df.columns.str.strip()

        if "DETALLE" not in df.columns or "PRECIO FINAL" not in df.columns:
            print("❌ Columnas faltantes en el Excel de NewBytes")
            return

        # 🔥 LIMPIAR ANTES DE CARGAR
        with conn.cursor() as cur:
            cur.execute("DELETE FROM productos WHERE sitio = %s", ("NewBytes",))
            conn.commit()
            print("🧹 Productos anteriores de NewBytes eliminados")

        for _, fila in df.iterrows():
            try:
                detalle = str(fila["DETALLE"]).strip()
                precio_str = str(fila["PRECIO FINAL"]).replace(",", ".").strip()

                if not detalle or detalle.upper() == "DETALLE" or "PRECIO FINAL" in detalle:
                    continue
                if not precio_str or precio_str.lower() == "nan":
                    continue

                precio_usd = float(precio_str)
                precio_ars = round(precio_usd * valor_dolar * 1.04)

                guardar_en_db(detalle, "NewBytes", detalle, precio_ars, "https://newbytes.com.ar")
            except Exception as e:
                print(f"⚠️ Error en fila: {fila.get('DETALLE', 'SIN DETALLE')}, error: {e}")

        print("✅ Lista de precios de NewBytes actualizada correctamente")

    except Exception as e:
        print("❌ Error al actualizar lista de NewBytes:", e)


