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
    tipo = request.args.get("tipo", "minorista")  # Por defecto "minorista"

    if not producto:
        return jsonify({"error": "Falta el parámetro 'producto'"}), 400

    try:
        resultados = []

        if tipo == "mayorista":
            print(f"🔍 Buscando solo en mayoristas: NewBytes")
            resultados += asyncio.run(buscar_newbytes(producto))
        else:
            print(f"🔍 Buscando solo en minoristas: CompraGamer, FullH4rd, Maximus")
            for funcion in [buscar_compugamer, buscar_fullh4rd, buscar_maximus]:
                resultados += asyncio.run(funcion(producto))

        # Ordenar por precio
        resultados_ordenados = sorted(resultados, key=lambda x: x.get("precio_num", float('inf')))
        for r in resultados_ordenados:
            r.pop("precio_num", None)

        return jsonify(resultados_ordenados)

    except Exception as e:
        print("❌ Error en /comparar:", str(e))
        return jsonify({"error": str(e)}), 500

