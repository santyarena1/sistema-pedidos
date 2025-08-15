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
        # Opciones clave para que funcione en un servidor Linux como el de Render
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage") # Importante para Render
        options.add_argument("start-maximized")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        # webdriver-manager se encargará de encontrar e instalar el driver correcto
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        driver.set_page_load_timeout(60)
        wait = WebDriverWait(driver, 30)

        print(f"-> {nombre_tienda}: Navegando a la página principal.")
        driver.get("https://www.invidcomputers.com")

        print(f"-> {nombre_tienda}: Ejecutando script de login.")
        driver.execute_script("ajaxLogin('GET');")

        user_input = wait.until(EC.visibility_of_element_located((By.ID, "usuari")))
        user_input.send_keys("23223648029")
        driver.find_element(By.ID, "passwd").send_keys("Arena123")

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="button" and contains(@value, "Login")]')))
        driver.execute_script("arguments[0].click();", login_button)
        print(f"-> {nombre_tienda}: Login enviado.")

        mi_cuenta_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="home_usuario.php" and contains(@class, "cambiar_cuenta_top")]'))
        )
        driver.execute_script("arguments[0].click();", mi_cuenta_btn)
        print(f"-> {nombre_tienda}: Accediendo a 'Mi Cuenta'.")

        descargar_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "genera_excel.php")]'))
        )
        excel_url = descargar_btn.get_attribute("href")
        print(f"-> {nombre_tienda}: URL de Excel obtenida. Descargando...")

        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        response = session.get(excel_url, timeout=60)
        response.raise_for_status()
        print(f"-> {nombre_tienda}: Excel descargado. Procesando...")

        df = pd.read_excel(BytesIO(response.content), skiprows=8, engine="openpyxl")
        df.columns = df.columns.str.strip()

        if "Producto" not in df.columns or "Precio en ARS" not in df.columns:
            raise ValueError("Columnas necesarias no encontradas en el Excel de Invid.")

        for index, fila in df.iterrows():
            try:
                nombre = str(fila.get("Producto", "")).strip()
                precio_str = str(fila.get("Precio en ARS", "")).replace("ARS", "").replace(",", ".").strip()

                if not nombre or not precio_str or nombre.lower() == "producto" or 'nan' in precio_str.lower():
                    continue

                precio_base = float(precio_str)
                precio_final = round(precio_base * 1.018)

                resultados.append({
                    "busqueda": "LISTA_COMPLETA",
                    "sitio": nombre_tienda,
                    "producto": nombre,
                    "precio": precio_final,
                    "link": "https://www.invidcomputers.com/"
                })
            except (ValueError, TypeError):
                continue

    except Exception as e:
        print(f"--- ERROR en el proceso de {nombre_tienda}: {e} ---")
        return []
    finally:
        if driver:
            driver.quit()

    print(f"-> Proceso de {nombre_tienda} finalizado. {len(resultados)} productos obtenidos.")
    return resultados