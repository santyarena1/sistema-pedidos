from flask import Flask, render_template
from flask_cors import CORS
from flask_apscheduler import APScheduler

# --- Importamos todos tus blueprints existentes ---
from routes.carrito import carrito_bp
from routes.presupuesto_routes import presupuesto_bp
from routes.buscar import buscar_bp
from routes.pc_armadas_routes import pc_armadas_bp
from routes.pedidos_routes import pedidos_bp
from routes.stock_routes import stock_bp
from routes.componentes_routes import componentes_bp
from routes.pc_predeterminadas_routes import pc_pred_bp
from routes.configuracion_routes import configuracion_bp

# --- CONFIGURACIÓN DEL PLANIFICADOR ---
class Config:
    SCHEDULER_API_ENABLED = True

# --- CREACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__, static_folder="static")
app.config.from_object(Config())

# Habilitar CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- Filtro personalizado para formato de moneda ---
@app.template_filter('formato_arg')
def formato_arg(value):
    try:
        return f"${float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value

# --- Rutas principales ---
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
app.register_blueprint(configuracion_bp)

# --- TAREA PROGRAMADA MEJORADA ---
def tarea_actualizar_mayoristas():
    with app.app_context():
        print("--- INICIANDO TAREA DE ACTUALIZACIÓN DE MAYORISTAS ---")
        # Se importan las funciones aquí para evitar problemas de importación circular
        from services.newbytes import obtener_lista_completa_newbytes
        from services.buscar_invid import obtener_lista_completa_invid
        from services.air_intra import obtener_lista_completa_air
        from services.polytech import obtener_lista_completa_polytech
        from routes.buscar import guardar_resultados_db

        try:
            # Ejecutamos los scrapers uno por uno para no sobrecargar el servidor
            resultados_invid = obtener_lista_completa_invid()
            guardar_resultados_db(resultados_invid)

            resultados_newbytes = obtener_lista_completa_newbytes()
            guardar_resultados_db(resultados_newbytes)
            
            resultados_air = obtener_lista_completa_air()
            guardar_resultados_db(resultados_air)

            resultados_polytech = obtener_lista_completa_polytech()
            guardar_resultados_db(resultados_polytech)
            
            print(f"--- TAREA DE ACTUALIZACIÓN DE MAYORISTAS FINALIZADA ---")

        except Exception as e:
            print(f"--- ERROR GRAVE EN LA TAREA PROGRAMADA: {e} ---")

# --- INICIALIZACIÓN Y CONFIGURACIÓN DEL PLANIFICADOR ---
scheduler = APScheduler()
scheduler.init_app(app)

# Agregamos la tarea para que se ejecute inmediatamente al arrancar y luego cada 6 horas
if not scheduler.get_job('actualizar_precios_mayoristas'):
    scheduler.add_job(
        id='actualizar_precios_mayoristas',
        func=tarea_actualizar_mayoristas,
        trigger='interval',
        hours=6,
        replace_existing=True,
        misfire_grace_time=900 # Tiempo de gracia si el servidor estaba apagado
    )
    # Ejecutamos la tarea una vez al iniciar para tener datos frescos
    scheduler.run_job('actualizar_precios_mayoristas') 

scheduler.start()

if __name__ == '__main__':
    # Esta configuración es ideal para Render, que usará Gunicorn
    app.run()