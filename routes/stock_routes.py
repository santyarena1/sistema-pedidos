from flask import Blueprint, request, jsonify, render_template
from db.connection import conn
from datetime import datetime

stock_bp = Blueprint("stock", __name__)

@stock_bp.route("/stock")
def vista_stock():
    return render_template("stock.html")

@stock_bp.route("/api/stock", methods=["GET"])
def obtener_stock():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, producto, codigo, deposito, cantidad, precio_venta, ultima_modificacion
                FROM stock
                ORDER BY producto ASC
            """)
            filas = cur.fetchall()
            resultados = [
                {
                    "id": f[0],
                    "producto": f[1],
                    "codigo": f[2],
                    "deposito": f[3],
                    "cantidad": f[4],
                    "precio_venta": float(f[5]) if f[5] else 0,
                    "ultima_modificacion": f[6].isoformat() if f[6] else None
                }
                for f in filas
            ]
            return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@stock_bp.route("/api/stock", methods=["POST"])
def agregar_stock():
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stock (producto, codigo, deposito, cantidad, precio_venta)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data.get("producto"),
                data.get("codigo"),
                data.get("deposito"),
                data.get("cantidad", 0),
                data.get("precio_venta", 0.0)
            ))
            stock_id = cur.fetchone()[0]
            registrar_movimiento(stock_id, "crear", None, None, None)
            conn.commit()
            return jsonify({"mensaje": "Producto agregado", "id": stock_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@stock_bp.route("/api/stock/<int:stock_id>", methods=["PATCH"])
def editar_stock(stock_id):
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT producto, codigo, deposito, cantidad, precio_venta FROM stock WHERE id = %s", (stock_id,))
            anterior = cur.fetchone()

            cur.execute("""
                UPDATE stock
                SET producto=%s, codigo=%s, deposito=%s, cantidad=%s, precio_venta=%s, ultima_modificacion=NOW()
                WHERE id=%s
            """, (
                data.get("producto"),
                data.get("codigo"),
                data.get("deposito"),
                data.get("cantidad"),
                data.get("precio_venta"),
                stock_id
            ))

            campos = ["producto", "codigo", "deposito", "cantidad", "precio_venta"]
            for i, campo in enumerate(campos):
                nuevo = data.get(campo)
                viejo = anterior[i]
                if str(nuevo) != str(viejo):
                    registrar_movimiento(stock_id, "editar", campo, viejo, nuevo)

            conn.commit()
            return jsonify({"mensaje": "Producto actualizado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@stock_bp.route("/api/stock", methods=["DELETE"])
def eliminar_stock():
    codigo = request.args.get("codigo")
    if not codigo:
        return jsonify({"error": "Falta el código"}), 400

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM stock WHERE codigo = %s", (codigo,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Producto no encontrado"}), 404
            stock_id = row[0]
            registrar_movimiento(stock_id, "eliminar", None, None, None)
            cur.execute("DELETE FROM stock WHERE id = %s", (stock_id,))
            conn.commit()
            return jsonify({"mensaje": "Producto eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@stock_bp.route("/api/stock/historial")
def historial_stock():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.fecha, m.accion, s.producto, s.codigo, m.campo, m.valor_anterior, m.valor_nuevo
                FROM movimientos_stock m
                JOIN stock s ON m.producto_id = s.id
                ORDER BY m.fecha DESC
            """)
            filas = cur.fetchall()
            movimientos = [
                {
                    "fecha": f[0].isoformat() if f[0] else None,
                    "accion": f[1],
                    "producto": f[2],
                    "codigo": f[3],
                    "campo": f[4],
                    "valor_anterior": f[5],
                    "valor_nuevo": f[6]
                }
                for f in filas
            ]
            return jsonify(movimientos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def registrar_movimiento(producto_id, accion, campo, valor_anterior, valor_nuevo):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO movimientos_stock (producto_id, accion, campo, valor_anterior, valor_nuevo)
            VALUES (%s, %s, %s, %s, %s)
        """, (producto_id, accion, campo, str(valor_anterior), str(valor_nuevo)))