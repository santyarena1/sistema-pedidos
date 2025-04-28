from flask import Blueprint, request, jsonify, render_template
import asyncio
from services.compra_gamer import buscar_compugamer
from services.fullh4rd import buscar_fullh4rd
from services.maximus import buscar_maximus
from services.newbytes import buscar_newbytes

buscar_bp = Blueprint("buscar", __name__)

# Renderiza el HTML del comparador
@buscar_bp.route("/buscar")
def mostrar_comparador():
    return render_template("buscador_rediseñado.html")

# Devuelve resultados en JSON
@buscar_bp.route("/comparar", methods=["GET"])
def comparar_productos():
    producto = request.args.get("producto")
    if not producto:
        return jsonify({"error": "Falta el parámetro 'producto'"}), 400

    try:
        resultados = []
        for funcion in [buscar_compugamer, buscar_fullh4rd, buscar_maximus, buscar_newbytes]:
            resultados += asyncio.run(funcion(producto))

        resultados_ordenados = sorted(resultados, key=lambda x: x.get("precio_num", float('inf')))
        for r in resultados_ordenados:
            r.pop("precio_num", None)

        return jsonify(resultados_ordenados)

    except Exception as e:
        print("Error en /comparar:", e)
        return jsonify({"error": "Ocurrió un error al comparar precios"}), 500
