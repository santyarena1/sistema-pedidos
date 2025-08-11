from flask import Flask, render_template
from flask_cors import CORS
from flask_apscheduler import APScheduler
from threading import Thread 
import time 

# --- Importamos todos tus blueprints existentes ---
from routes.carrito import carrito_bp
from routes.presupuesto_routes import presupuesto_bp
from routes.buscar import buscar_bp
from routes.pc_armadas_routes import pc_armadas_bp
from routes.pedidos_routes import pedidos_bp
from routes.stock_routes import stock_bp
from routes.componentes_routes import componentes_bp
from routes.pc_predeterminadas_routes import pc_pred_bp
# --- CAMBIO 1: Importamos el nuevo blueprint de configuración ---
from routes.configuracion_routes import configuracion_bp


# --- CONFIGURACIÓN DEL PLANIFICADOR ---
class Config:
    SCHEDULER_API_ENABLED = True

# --- CREACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__, static_folder="static")
app.config.from_object(Config())

# Habilitar CORS (sin cambios)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- Filtro personalizado (sin cambios) ---
@app.template_filter('formato_arg')
def formato_arg(value):
    try:
        return f"${float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

# --- Rutas principales (sin cambios) ---
@app.route("/")
def home():
    return render_template("presupuesto_rediseñado.html")

@app.route("/presupuesto_rediseñado")
def mostrar_presupuesto():
    return render_template("presupuesto_rediseñado.html")

# --- Registro de todos tus blueprints ---
app.register_blueprint(carrito_bp)
app.register_blueprint(presupuesto_bp)
app.register_blueprint(buscar_bp)
app.register_blueprint(pc_armadas_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(componentes_bp)
app.register_blueprint(pc_pred_bp)
# --- CAMBIO 2: Registramos el nuevo blueprint de configuración ---
app.register_blueprint(configuracion_bp)


def tarea_actualizar_mayoristas():
    with app.app_context():
        print("--- INICIANDO TAREA DE ACTUALIZACIÓN DE MAYORISTAS ---")
        from services.newbytes import obtener_lista_completa_newbytes
        from services.buscar_invid import obtener_lista_completa_invid
        from services.air_intra import obtener_lista_completa_air
        from services.polytech import obtener_lista_completa_polytech
        from routes.buscar import guardar_resultados_db

        try:
            resultados_invid = obtener_lista_completa_invid()
            resultados_newbytes = obtener_lista_completa_newbytes()
            resultados_air = obtener_lista_completa_air()
            resultados_polytech = obtener_lista_completa_polytech()
            

            # Guardamos cada mayorista por separado para limpiar su propio sitio
            if resultados_invid:
                guardar_resultados_db(resultados_invid)
            if resultados_newbytes:
                guardar_resultados_db(resultados_newbytes)
            if resultados_air:
                guardar_resultados_db(resultados_air)
            if resultados_polytech:
                guardar_resultados_db(resultados_polytech)


            total = sum(len(lst) for lst in [resultados_invid, resultados_newbytes, resultados_air, resultados_polytech,])
            print(f"-> Tarea finalizada. Total de {total} productos procesados.")
        except Exception as e:
            print(f"--- ERROR EN LA TAREA DE ACTUALIZACIÓN: {e} ---")



# --- INICIALIZACIÓN Y CONFIGURACIÓN DEL PLANIFICADOR (sin cambios) ---
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

if not scheduler.get_job('actualizar_precios_mayoristas'):
    scheduler.add_job(
        id='actualizar_precios_mayoristas',
        func=tarea_actualizar_mayoristas,
        trigger='interval',
        hours=6,
        replace_existing=True
    )

# --- EJECUCIÓN INICIAL AL ARRANCAR LA APP (sin cambios) ---
def ejecutar_actualizacion_inicial():
    print("-> Esperando 5 segundos para la actualización inicial...")
    time.sleep(5)
    tarea_actualizar_mayoristas()

hilo_inicial = Thread(target=ejecutar_actualizacion_inicial)
hilo_inicial.start()

if __name__ == '__main__':
    # El truco es usar el reloader de Flask para evitar la doble inicialización.
    # El argumento use_reloader=False le dice a Flask que no inicie el monitor,
    # lo que previene que el scheduler se ejecute dos veces.
    # Esto es ideal para el desarrollo. En producción, usarías un servidor como Gunicorn.
    
    # Comprobamos que el scheduler no esté ya corriendo para ser extra seguros.
    if not scheduler.running:
        scheduler.start()
        print("-> Planificador de tareas APScheduler iniciado.")

    app.run(debug=True, port=5000, use_reloader=False)