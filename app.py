# app.py
# -*- coding: utf-8 -*-
import os
import time
from threading import Thread

from flask import Flask, render_template, make_response
from flask_cors import CORS
from flask_apscheduler import APScheduler

# --- Blueprints de tu app (sin cambios) ---
from routes.carrito import carrito_bp
from routes.presupuesto_routes import presupuesto_bp
from routes.pc_armadas_routes import pc_armadas_bp
from routes.pedidos_routes import pedidos_bp
from routes.stock_routes import stock_bp
from routes.componentes_routes import componentes_bp
from routes.pc_predeterminadas_routes import pc_pred_bp
from routes.configuracion_routes import configuracion_bp

# --- Buscar: blueprint + helpers de BD ---
# Intentamos importar también 'reemplazar_resultados_de_sitio'.
# Si tu versión de routes/buscar.py no lo tiene, usamos un fallback que NO borra datos (solo upsert).
try:
    from routes.buscar import buscar_bp, guardar_resultados_db, reemplazar_resultados_de_sitio
except ImportError:
    from routes.buscar import buscar_bp, guardar_resultados_db
    def reemplazar_resultados_de_sitio(sitio: str, items: list):
        """Fallback seguro: si no existe la función, hacemos upsert manteniendo históricos."""
        normalizados = [{**it, "sitio": sitio} for it in (items or [])]
        guardar_resultados_db(normalizados)


# =========================
# Configuración de la app
# =========================
class Config:
    SCHEDULER_API_ENABLED = True


app = Flask(__name__, static_folder="static")
app.config.from_object(Config())

# CORS abierto (como tenías)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# =========================
# Filtros / Utilidades
# =========================
@app.template_filter('formato_arg')
def formato_arg(value):
    try:
        return f"${float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return value

# Evitar ruido por /favicon.ico en consola
@app.route("/favicon.ico")
def favicon():
    return make_response(("", 204))


# =========================
# Rutas principales (como tenías)
# =========================
@app.route("/")
def home():
    return render_template("presupuesto_rediseñado.html")

@app.route("/presupuesto_rediseñado")
def mostrar_presupuesto():
    return render_template("presupuesto_rediseñado.html")


# =========================
# Registro de blueprints
# =========================
app.register_blueprint(carrito_bp)
app.register_blueprint(presupuesto_bp)
app.register_blueprint(buscar_bp)              # <--- /buscar
app.register_blueprint(pc_armadas_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(componentes_bp)
app.register_blueprint(pc_pred_bp)
app.register_blueprint(configuracion_bp)


# =========================
# Tarea: actualizar mayoristas
# =========================
def tarea_actualizar_mayoristas():
    """
    Carga catálogos completos de mayoristas/minoristas que vos ya scrapeás
    y los guarda en BD. Si está disponible 'reemplazar_resultados_de_sitio',
    primero borra el sitio y luego inserta (catálogo limpio).
    Si no está disponible, hace upsert (no borra).
    """
    with app.app_context():
        print("--- INICIANDO TAREA DE ACTUALIZACIÓN DE MAYORISTAS ---")

        # Importes locales para evitar ciclos y acelerar arranque
        try:
            from services.newbytes import obtener_lista_completa_newbytes
            from services.buscar_invid import obtener_lista_completa_invid
            from services.air_intra import obtener_lista_completa_air
            from services.polytech import obtener_lista_completa_polytech
            from services.thegamershop_scraper import obtener_lista_completa_thegamershop
        except Exception as e:
            print(f"--- ERROR IMPORTANDO SERVICIOS: {e} ---")
            return

        # Nombres de sitio tal como querés verlos en el front/BD
        SITES = [
            ("Invid",                 "obtener_lista_completa_invid"),
            ("Newbytes",              "obtener_lista_completa_newbytes"),
            ("Air Computers",         "obtener_lista_completa_air"),
            ("Polytech",              "obtener_lista_completa_polytech"),
            ("The Gamer Shop",        "obtener_lista_completa_thegamershop"),  # si es catálogo completo
        ]

        total = 0
        errores = []

        for nombre_sitio, funcion in SITES:
            try:
                # Resolvemos la función desde los módulos importados arriba
                if funcion == "obtener_lista_completa_invid":
                    lista = obtener_lista_completa_invid()
                elif funcion == "obtener_lista_completa_newbytes":
                    lista = obtener_lista_completa_newbytes()
                elif funcion == "obtener_lista_completa_air":
                    lista = obtener_lista_completa_air()
                elif funcion == "obtener_lista_completa_polytech":
                    lista = obtener_lista_completa_polytech()
                elif funcion == "obtener_lista_completa_thegamershop":
                    lista = obtener_lista_completa_thegamershop()
                else:
                    lista = []

                lista = lista or []

                # Si tenemos reemplazo por sitio, usamos eso (mantiene BD limpia y evita viejos)
                try:
                    reemplazar_resultados_de_sitio(nombre_sitio, lista)
                except Exception as e:
                    # Si por alguna razón falla el reemplazo, no perdemos data: hacemos upsert
                    print(f"[{nombre_sitio}] Falla en reemplazar_resultados_de_sitio: {e} -> upsert")
                    normalizados = [{**it, "sitio": nombre_sitio} for it in lista]
                    guardar_resultados_db(normalizados)

                cant = len(lista)
                total += cant
                print(f"-> {nombre_sitio}: {cant} productos procesados.")

            except Exception as e:
                errores.append(f"{nombre_sitio}: {e}")
                print(f"--- ERROR EN {nombre_sitio}: {e} ---")

        print(f"-> Tarea finalizada. Total de {total} productos procesados.")
        if errores:
            print("-> Errores durante la tarea:", "; ".join(errores))


# =========================
# Scheduler (APScheduler)
# =========================
class AppScheduler(APScheduler):
    """Evita dobles inicios y nos da un lugar para hooks si hiciera falta."""
    pass

scheduler = AppScheduler()
scheduler.init_app(app)
scheduler.start()

# Job recurrente cada 6 horas
if not scheduler.get_job('actualizar_precios_mayoristas'):
    scheduler.add_job(
        id='actualizar_precios_mayoristas',
        func=tarea_actualizar_mayoristas,
        trigger='interval',
        hours=6,
        replace_existing=True
    )

# Actualización inicial (a los 5s de arrancar)
def ejecutar_actualizacion_inicial():
    try:
        print("-> Esperando 5 segundos para la actualización inicial...")
        time.sleep(5)
        tarea_actualizar_mayoristas()
    except Exception as e:
        print(f"--- ERROR EN ACTUALIZACIÓN INICIAL: {e} ---")

Thread(target=ejecutar_actualizacion_inicial, daemon=True).start()


# =========================
# Main
# =========================
if __name__ == '__main__':
    # Evitamos doble arranque del scheduler con el reloader
    if not scheduler.running:
        scheduler.start()
        print("-> Planificador de tareas APScheduler iniciado.")

    port = int(os.getenv("PORT", "5050"))
    app.run(debug=True, port=port, use_reloader=False, host="0.0.0.0")
