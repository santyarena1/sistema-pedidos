from flask import Flask
from flask_cors import CORS
from routes.carrito import carrito_bp
from routes.presupuesto_routes import presupuesto_bp
from routes.buscar import buscar_bp
from flask import Flask, render_template
from routes.pc_armadas_routes import pc_armadas_bp
from routes.pedidos_routes import pedidos_bp
from routes.stock_routes import stock_bp 


app = Flask(__name__, static_folder="static")

from apscheduler.schedulers.background import BackgroundScheduler
from services.newbytes import actualizar_lista_newbytes


@app.route("/")
def home():
    return render_template("presupuesto_rediseñado.html")


@app.route("/presupuesto_rediseñado")
def mostrar_presupuesto():
    return render_template("presupuesto_rediseñado.html")

# Habilitar CORS para todos los orígenes y métodos
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Blueprints

app.register_blueprint(carrito_bp)
app.register_blueprint(presupuesto_bp)
app.register_blueprint(buscar_bp)
app.register_blueprint(pc_armadas_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(stock_bp)

scheduler = BackgroundScheduler()
scheduler.add_job(actualizar_lista_newbytes, "cron", hour=10, minute=0)
scheduler.add_job(actualizar_lista_newbytes, "cron", hour=15, minute=0)
scheduler.start()


if __name__ == "__main__":
    app.run(debug=True)
