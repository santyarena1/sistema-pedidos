from flask import Blueprint, request, jsonify, render_template
from db.connection import conn

carrito_bp = Blueprint("carrito", __name__)

@carrito_bp.route("/carrito")
def carrito():
    return render_template("carrito_rediseñado.html")


@carrito_bp.route("/carrito", methods=["POST"])
def agregar_al_carrito():
    data = request.get_json()
    sitio = data.get("sitio")
    producto = data.get("producto")
    precio = data.get("precio")
    link = data.get("link")

    if not all([sitio, producto, precio]):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO carrito (sitio, producto, precio, link)
                VALUES (%s, %s, %s, %s)
            """, (sitio, producto, precio, link))
            conn.commit()
        return jsonify({"mensaje": "Producto agregado al carrito"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@carrito_bp.route("/carrito", methods=["GET"])
def ver_carrito():
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, sitio, producto, precio, link, timestamp FROM carrito ORDER BY timestamp DESC")
            filas = cur.fetchall()
            carrito = []
            for fila in filas:
                carrito.append({
                    "id": fila[0],
                    "sitio": fila[1],
                    "producto": fila[2],
                    "precio": float(fila[3]),
                    "link": fila[4],
                    "timestamp": fila[5].isoformat() if fila[5] else ""
                })
        return jsonify(carrito)
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@carrito_bp.route("/carrito/<int:carrito_id>", methods=["DELETE"])
def eliminar_producto_carrito(carrito_id):
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM carrito WHERE id = %s", (carrito_id,))
            conn.commit()
        return jsonify({"mensaje": f"Producto con ID {carrito_id} eliminado"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@carrito_bp.route("/carrito", methods=["DELETE"])
def vaciar_carrito():
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM carrito")
            conn.commit()
        return jsonify({"mensaje": "Carrito vaciado"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
