from flask import Blueprint, request, jsonify, render_template
# --- CAMBIO 1: Importamos la nueva función en lugar de la variable 'conn' ---
from db.connection import get_db_connection
import psycopg2.extras

carrito_bp = Blueprint("carrito", __name__)

# Ruta para renderizar la página HTML del carrito (sin cambios)
@carrito_bp.route("/carrito")
def carrito():
    return render_template("carrito_rediseñado.html")

# Ruta para AGREGAR un producto al carrito
@carrito_bp.route("/carrito", methods=["POST"])
def agregar_al_carrito():
    data = request.get_json()
    sitio = data.get("sitio")
    producto = data.get("producto")
    precio = data.get("precio")
    link = data.get("link")

    if not all([sitio, producto, precio]):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    conn = None
    try:
        # --- CAMBIO 2: Obtenemos una conexión nueva ---
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO carrito (sitio, producto, precio, link)
                VALUES (%s, %s, %s, %s)
            """, (sitio, producto, precio, link))
            conn.commit()
        return jsonify({"mensaje": "Producto agregado al carrito"}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        # --- CAMBIO 3: Cerramos la conexión al terminar ---
        if conn:
            conn.close()

# Ruta para OBTENER todos los productos del carrito
@carrito_bp.route("/carrito/items", methods=["GET"])
def ver_carrito():
    conn = None
    try:
        # Obtenemos una conexión nueva
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM carrito ORDER BY id ASC")
            # Usamos DictCursor para convertir las filas a diccionarios fácilmente
            items = [dict(row) for row in cur.fetchall()]
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para ELIMINAR UN producto específico del carrito
@carrito_bp.route("/carrito/<int:carrito_id>", methods=["DELETE"])
def eliminar_producto_carrito(carrito_id):
    conn = None
    try:
        # Obtenemos una conexión nueva
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM carrito WHERE id = %s", (carrito_id,))
            conn.commit()
        return jsonify({"mensaje": f"Producto con ID {carrito_id} eliminado"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para VACIAR completamente el carrito
@carrito_bp.route("/carrito/vaciar", methods=["DELETE"])
def vaciar_carrito():
    conn = None
    try:
        # Obtenemos una conexión nueva
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM carrito")
            conn.commit()
        return jsonify({"mensaje": "Carrito vaciado"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()