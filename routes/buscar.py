from flask import Blueprint, request, jsonify, render_template
import asyncio
from services.compra_gamer import buscar_compugamer
from services.fullh4rd import buscar_fullh4rd
from services.maximus import buscar_maximus
from services.newbytes import buscar_newbytes
from services.buscar_invid import actualizar_lista_invid
from services.buscar_invid import buscar_invid





buscar_bp = Blueprint("buscar", __name__)

@buscar_bp.route("/actualizar-invid", methods=["GET"])
def actualizar_invid_manual():
    try:
        actualizar_lista_invid()
        return jsonify({"mensaje": "Invid actualizado correctamente ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            print(f"🔍 Buscando solo en mayoristas: NewBytes, Invid")
            resultados += asyncio.run(buscar_newbytes(producto))
            resultados += asyncio.run(buscar_invid(producto))
            
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

@buscar_bp.route("/actualizar-newbytes", methods=["GET"])
def actualizar_newbytes_manual():
    try:
        from services.newbytes import actualizar_lista_newbytes
        actualizar_lista_newbytes()
        return jsonify({"mensaje": "Actualización manual completada ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
