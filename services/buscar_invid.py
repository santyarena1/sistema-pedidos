import time
import pandas as pd
from io import BytesIO
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def obtener_lista_completa_invid():
    nombre_tienda = "Invid"
    print(f"-> Obteniendo lista completa de {nombre_tienda}...")
    driver = None
    resultados = []

    try:
        options = Options()
        # El navegador ahora se ejecuta en modo invisible (headless)
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("start-maximized")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        driver.get("https://www.invidcomputers.com")

        driver.execute_script("ajaxLogin('GET');")

        wait = WebDriverWait(driver, 20)
        user_input = wait.until(EC.visibility_of_element_located((By.ID, "usuari")))

        user_input.send_keys("23223648029")
        driver.find_element(By.ID, "passwd").send_keys("Arena123")

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="button" and contains(@value, "Login")]')))
        driver.execute_script("arguments[0].click();", login_button)

        # Pequeña espera para asegurar que el login se procese
        time.sleep(3)

        mi_cuenta_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="home_usuario.php" and contains(@class, "cambiar_cuenta_top")]'))
        )
        driver.execute_script("arguments[0].click();", mi_cuenta_btn)

        descargar_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "genera_excel.php")]'))
        )
        excel_url = descargar_btn.get_attribute("href")

        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        response = session.get(excel_url)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content), skiprows=8, engine="openpyxl")
        df.columns = df.columns.str.strip()

        if "Producto" not in df.columns or "Precio en ARS" not in df.columns:
            raise ValueError("Columnas necesarias no encontradas en el Excel de Invid.")

        for index, fila in df.iterrows():
            try:
                nombre = str(fila["Producto"]).strip()
                precio_str = str(fila["Precio en ARS"]).replace("ARS", "").replace(",", ".").strip()

                if not nombre or not precio_str or nombre.lower() == "producto" or precio_str.lower() == 'nan':
                    continue

                precio_base = float(precio_str)
                precio_final = round(precio_base * 1.018)

                resultados.append({
                    "busqueda": "LISTA_COMPLETA",
                    "sitio": nombre_tienda,
                    "producto": nombre,
                    "precio": precio_final,  # Precio NUMÉRICO para la BD
                    "link": "https://www.invidcomputers.com/"
                })
            except (ValueError, TypeError):
                # Ignoramos filas con precios no válidos
                continue

    except Exception as e:
        print(f"--- ERROR en el proceso de {nombre_tienda}: {e} ---")
        return []
    finally:
        if driver:
            driver.quit()

    print(f"-> Proceso de {nombre_tienda} finalizado. {len(resultados)} productos obtenidos.")
    return resultados

# Este bloque te permite probar el archivo por separado si lo necesitas
if __name__ == '__main__':
    def probar():
        print("Probando la obtención de la lista completa de Invid...")
        lista_productos = obtener_lista_completa_invid()
        if lista_productos:
            print(f"Se obtuvieron {len(lista_productos)} productos.")
            print("Mostrando los primeros 5:")
            for p in lista_productos[:5]:
                print(p)
        else:
            print("No se pudieron obtener productos.")

    probar()