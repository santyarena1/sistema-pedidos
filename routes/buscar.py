from flask import Blueprint, request, jsonify, render_template
import asyncio
from services.compra_gamer import buscar_compugamer
from services.fullh4rd import buscar_fullh4rd
from services.maximus import buscar_maximus
from services.newbytes import buscar_newbytes
from services.buscar_invid import actualizar_lista_invid
from services.buscar_invid import buscar_invid
from services.air_intra import actualizar_lista_air
from services.polytech import actualizar_lista_polytech
from db.connection import conn






buscar_bp = Blueprint("buscar", __name__)



@buscar_bp.route("/actualizar-polytech", methods=["GET"])
def actualizar_polytech_manual():
    try:
        actualizar_lista_polytech()
        return jsonify({"mensaje": "Polytech actualizado correctamente ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@buscar_bp.route("/actualizar-air", methods=["GET"])
def actualizar_air_manual():
    try:
        actualizar_lista_air()
        return jsonify({"mensaje": "AIR actualizado correctamente ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    tipo = request.args.get("tipo", "mayorista")  # Por defecto "minorista"

    if not producto:
        return jsonify({"error": "Falta el parámetro 'producto'"}), 400

    try:
        resultados = []

        if tipo == "mayorista":
            print(f"🔍 Buscando solo en mayoristas: NewBytes, Invid, AIR")
            resultados += asyncio.run(buscar_newbytes(producto))
            resultados += asyncio.run(buscar_invid(producto))
            resultados += cargar_resultados_bd(producto, "AIR")
            resultados += cargar_resultados_bd(producto, "POLYTECH")


            
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
    
def cargar_resultados_bd(producto, sitio):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT producto, precio, link
            FROM productos
            WHERE sitio = %s AND LOWER(producto) LIKE %s
            ORDER BY actualizado DESC
            LIMIT 30
        """, (sitio, f"%{producto.lower()}%"))
        filas = cur.fetchall()

    resultados = []
    for fila in filas:
        resultados.append({
            "sitio": sitio,
            "producto": fila[0],
            "precio": f"${fila[1]:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "link": fila[2],
            "precio_num": fila[1]
        })
    return resultados
