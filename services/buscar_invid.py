from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
from io import BytesIO
import requests
from db.connection import conn
from db.queries import guardar_en_db
from db.queries import obtener_desde_db
from utils.format import formatear_precio

def actualizar_lista_invid():
    driver = None
    try:
        # Configurar navegador
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        driver.get("https://www.invidcomputers.com")

        # Ejecutar modal de login
        driver.execute_script("ajaxLogin('GET');")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "usuari"))
        )

        driver.find_element(By.ID, "usuari").send_keys("23223648029")
        driver.find_element(By.ID, "passwd").send_keys("Arena123")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@type="button" and contains(@value, "Login")]'))
        ).click()

        # Hacer clic en "Mi cuenta"
        mi_cuenta_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="home_usuario.php" and contains(@class, "cambiar_cuenta_top")]'))
        )
        driver.execute_script("arguments[0].click();", mi_cuenta_btn)

        # Hacer clic en "Descargar lista de precios"
        descargar_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "genera_excel.php")]'))
        )
        driver.execute_script("arguments[0].click();", descargar_btn)

        time.sleep(3)

        excel_url = descargar_btn.get_attribute("href")
        print("[*] Enlace directo del Excel:", excel_url)

        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        response = session.get(excel_url)
        response.raise_for_status()

        print("[*] Tama\u00f1o del archivo descargado:", len(response.content), "bytes")

        df = pd.read_excel(BytesIO(response.content), skiprows=8, engine="openpyxl")
        df.columns = df.columns.str.strip()

        print("[*] Columnas encontradas:", df.columns.tolist())

        if "Producto" not in df.columns or "Precio en ARS" not in df.columns:
            print("[X] Columnas necesarias no encontradas:", list(df.columns))
            return

        with conn.cursor() as cur:
            cur.execute("DELETE FROM productos WHERE sitio = %s", ("Invid",))
            conn.commit()
            print("[~] Productos anteriores de Invid eliminados")

        print("[*] Comenzando a procesar filas...")

        for index, fila in df.iterrows():
            try:
                nombre = str(fila["Producto"]).strip()
                precio_str = str(fila["Precio en ARS"]).replace("ARS", "").replace(",", ".").strip()


                if not nombre or not precio_str or nombre.lower() == "producto":
                    print(f"[!] Fila ignorada {index}: nombre vac\u00edo o inv\u00e1lido")
                    continue

                precio_base = float(precio_str)
                precio_final = round(precio_base * 1.04)

                guardar_en_db(nombre, "Invid", nombre, precio_final, "https://www.invidcomputers.com/")
                print(f"[+] Guardado: {nombre} - ${precio_final}")
            except Exception as e:
                print(f"[!] Error en fila {index}: {fila.get('Producto', '???')}, error: {e}")

        print("[✔] Lista de precios de Invid actualizada correctamente.")

    except Exception as e:
        print("[X] Error general con Selenium/Invid:", str(e))

    finally:
        if driver:
            driver.quit()

async def buscar_invid(producto):
    resultados = obtener_desde_db(producto, "Invid")
    return [
        {
            **r,
            "precio": formatear_precio(r["precio"]),
        }
        for r in resultados
    ]
