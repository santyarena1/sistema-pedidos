import requests
import pandas as pd
from io import BytesIO

def obtener_lista_completa_newbytes():
    """
    Obtiene la lista de precios completa de NewBytes.
    Devuelve un diccionario con una única clave 'precio' que contiene el número puro.
    """
    nombre_tienda = "NewBytes"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")
    try:
        # Usamos 'value_sell' para la cotización del dólar, que suele ser más precisa para la venta.
        valor_dolar = requests.get("https://api.bluelytics.com.ar/v2/latest").json()["blue"]["value_sell"]
        url_lista = "https://api.nb.com.ar/v1/priceListExcel/1f31e11177035cdab4cad5e94e50ea"
        excel_response = requests.get(url_lista, timeout=30)
        excel_response.raise_for_status()

        df = pd.read_excel(BytesIO(excel_response.content), skiprows=2, engine="openpyxl")
        df.columns = df.columns.str.strip()

        if "DETALLE" not in df.columns or "PRECIO FINAL" not in df.columns:
            raise ValueError("Columnas 'DETALLE' o 'PRECIO FINAL' no encontradas en el Excel.")

        resultados = []
        for _, fila in df.iterrows():
            try:
                detalle = str(fila.get("DETALLE", "")).strip()
                precio_str = str(fila.get("PRECIO FINAL", "")).replace(",", ".").strip()

                if not detalle or detalle.upper() == "DETALLE" or "PRECIO FINAL" in detalle or not precio_str or precio_str.lower() == 'nan':
                    continue

                precio_usd = float(precio_str)
                # Mantenemos tu cálculo de precio
                precio_ars = round(precio_usd * valor_dolar * 1.04)

                # --- CORRECCIÓN FINAL AQUÍ ---
                # El diccionario ahora solo contiene la clave 'precio' con el número puro.
                resultados.append({
                    "busqueda": "LISTA_COMPLETA",
                    "sitio": nombre_tienda,
                    "producto": detalle,
                    "precio": precio_ars, # NÚMERO PURO
                    "link": "https://newbytes.com.ar"
                })
            except (ValueError, TypeError):
                continue
        
        print(f"-> Lista de {nombre_tienda} procesada. {len(resultados)} productos encontrados.")
        return resultados

    except requests.RequestException as e:
        print(f"-> ERROR GRAVE de red obteniendo lista de {nombre_tienda}: {e}")
        return []
    except Exception as e:
        print(f"-> ERROR GRAVE procesando lista de {nombre_tienda}: {e}")
        return []

# Mantenemos tu bloque de prueba intacto
if __name__ == '__main__':
    def probar():
        print("Probando la obtención de la lista completa de NewBytes...")
        lista_productos = obtener_lista_completa_newbytes()
        if lista_productos:
            print(f"Se obtuvieron {len(lista_productos)} productos.")
            print("Mostrando los primeros 5:")
            for p in lista_productos[:5]:
                print(p)
        else:
            print("No se pudieron obtener productos.")
    
    probar()