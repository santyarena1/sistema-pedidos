import requests
import json

def probar_api_preciosgamer(producto):
    """
    Realiza una única petición a la API de PreciosGamer usando la URL correcta.
    """
    
    # === LA URL CORRECTA QUE TÚ ENCONTRASTE ===
    url = f"https://api.preciosgamer.com/v1/items?search={requests.utils.quote(producto)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"--- Realizando test para el producto: '{producto}' ---")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("\n-> ¡ÉXITO! Conexión con la API establecida (Código 200).")
            data = response.json()
            
            # El formato de esta API es un diccionario que contiene la lista
            if isinstance(data, dict) and 'results' in data and isinstance(data['results'], list):
                resultados = data['results']
                print(f"-> ¡CORRECTO! La API devolvió {len(resultados)} productos.")
                
                if resultados:
                    print("\n--- EJEMPLO DEL PRIMER PRODUCTO ENCONTRADO ---")
                    # Imprimimos el primer producto de forma legible
                    print(json.dumps(resultados[0], indent=4, ensure_ascii=False))
            else:
                print("\n-> ERROR: La respuesta de la API no tiene el formato esperado (no se encontró 'results').")
                print("Respuesta recibida:", data)

        else:
            print(f"\n-> ERROR: La API respondió con un código de estado inesperado: {response.status_code}")
            print("Respuesta:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n-> ERROR CRÍTICO: No se pudo conectar con el servidor. {e}")

# --- Ejecutamos el test ---
if __name__ == "__main__":
    termino_de_busqueda = "5600g" # Puedes cambiar esto para probar
    probar_api_preciosgamer(termino_de_busqueda)