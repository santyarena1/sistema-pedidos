from flask import Blueprint, request, jsonify, send_file, render_template
from db.connection import conn
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import date, timedelta
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os

presupuesto_bp = Blueprint("presupuestos", __name__)

@presupuesto_bp.route("/presupuestos")
def presupuestos():
    return render_template("presupuesto_rediseñado.html")


def formato_arg(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@presupuesto_bp.route("/presupuestos/pdf/<int:presupuesto_id>", methods=["GET"])
def generar_pdf_estilizado(presupuesto_id):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cliente, fecha_emision, fecha_validez, total_final FROM presupuestos WHERE id = %s", (presupuesto_id,))
            p = cur.fetchone()
            if not p:
                return "Presupuesto no encontrado", 404

            cur.execute("SELECT producto, cantidad, precio_venta, iva FROM items_presupuesto WHERE presupuesto_id = %s", (presupuesto_id,))
            items = cur.fetchall()

        env = Environment(loader=FileSystemLoader("templates"))
        env.filters['formato_arg'] = formato_arg
        template = env.get_template("plantilla_presupuesto.html")

        rendered_html = template.render(
            cliente=p[0],
            fecha_emision=p[1],
            fecha_validez=p[2],
            total_final=p[3],
            id=presupuesto_id,
            dias_validez=7,
            items=[
                {"producto": i[0], "cantidad": i[1], "precio_venta": i[2], "iva": i[3]} for i in items
            ]
        )

        pdf = HTML(string=rendered_html, base_url=".").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=False,
                         download_name=f"presupuesto_{presupuesto_id}.pdf")

    except Exception as e:
        return str(e), 500

@presupuesto_bp.route("/presupuestos", methods=["POST"])
def guardar_presupuesto():
    data = request.get_json()
    cliente = data.get("cliente")
    fecha_emision = data.get("fecha_emision") or date.today().isoformat()
    fecha_validez = data.get("fecha_validez") or (date.today() + timedelta(days=7)).isoformat()
    coef_venta = data.get("coef_venta", 1.3)
    descuento = data.get("descuento", 0)
    total_final = data.get("total_final", 0)
    items = data.get("items", [])

    if not all([cliente, fecha_emision, fecha_validez, items]):
        return jsonify({"error": "Faltan datos"}), 400

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO presupuestos (cliente, fecha_emision, fecha_validez, coef_venta, descuento, total_final)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (cliente, fecha_emision, fecha_validez, coef_venta, descuento, total_final))
            presupuesto_id = cur.fetchone()[0]

            for item in items:
                cur.execute("""
                    INSERT INTO items_presupuesto (presupuesto_id, producto, cantidad, precio, descuento, iva, precio_venta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    presupuesto_id,
                    item.get("producto"),
                    item.get("cantidad", 1),
                    item.get("precio", 0),
                    item.get("descuento", 0),
                    item.get("iva", 0),
                    item.get("precio_venta", 0)
                ))
            conn.commit()
        return jsonify({"mensaje": "Presupuesto guardado", "id": presupuesto_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@presupuesto_bp.route("/presupuestos", methods=["GET"])
def ver_presupuestos():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, cliente, fecha_emision, fecha_validez, coef_venta, descuento, total_final, creado_en
                FROM presupuestos ORDER BY creado_en DESC
            """)
            presupuestos = []
            for row in cur.fetchall():
                presupuestos.append({
                    "id": row[0],
                    "cliente": row[1],
                    "fecha_emision": row[2].isoformat(),
                    "fecha_validez": row[3].isoformat(),
                    "coef_venta": row[4],
                    "descuento": row[5],
                    "total_final": row[6],
                    "creado_en": row[7].isoformat() if row[7] else ""
                })
        return jsonify(presupuestos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@presupuesto_bp.route("/presupuestos/<int:presupuesto_id>", methods=["GET"])
def obtener_presupuesto(presupuesto_id):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cliente, fecha_emision, fecha_validez, coef_venta, descuento, total_final
                FROM presupuestos WHERE id = %s
            """, (presupuesto_id,))
            p = cur.fetchone()
            if not p:
                return jsonify({"error": "No existe"}), 404
            presupuesto = {
                "cliente": p[0],
                "fecha_emision": p[1].isoformat(),
                "fecha_validez": p[2].isoformat(),
                "coef_venta": p[3],
                "descuento": p[4],
                "total_final": p[5],
                "items": []
            }
            cur.execute("""
                SELECT producto, cantidad, precio, descuento, iva, precio_venta
                FROM items_presupuesto WHERE presupuesto_id = %s
            """, (presupuesto_id,))
            for row in cur.fetchall():
                presupuesto["items"].append({
                    "producto": row[0],
                    "cantidad": row[1],
                    "precio": row[2],
                    "descuento": row[3],
                    "iva": row[4],
                    "precio_venta": row[5]
                })
            return jsonify(presupuesto)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@presupuesto_bp.route("/presupuestos/<int:presupuesto_id>", methods=["PUT"])
def actualizar_presupuesto(presupuesto_id):
    data = request.get_json()
    cliente = data.get("cliente")
    fecha_emision = data.get("fecha_emision")
    fecha_validez = data.get("fecha_validez")
    coef_venta = data.get("coef_venta", 1.3)
    descuento = data.get("descuento", 0)
    total_final = data.get("total_final", 0)
    items = data.get("items", [])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE presupuestos SET cliente=%s, fecha_emision=%s, fecha_validez=%s,
                coef_venta=%s, descuento=%s, total_final=%s WHERE id=%s
            """, (cliente, fecha_emision, fecha_validez, coef_venta, descuento, total_final, presupuesto_id))

            cur.execute("DELETE FROM items_presupuesto WHERE presupuesto_id=%s", (presupuesto_id,))

            for item in items:
                cur.execute("""
                    INSERT INTO items_presupuesto (presupuesto_id, producto, cantidad, precio, descuento, iva, precio_venta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    presupuesto_id,
                    item.get("producto"),
                    item.get("cantidad", 1),
                    item.get("precio", 0),
                    item.get("descuento", 0),
                    item.get("iva", 0),
                    item.get("precio_venta", 0)
                ))
            conn.commit()
        return jsonify({"mensaje": "Presupuesto actualizado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@presupuesto_bp.route("/presupuestos/<int:presupuesto_id>", methods=["DELETE"])
def eliminar_presupuesto(presupuesto_id):
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items_presupuesto WHERE presupuesto_id = %s", (presupuesto_id,))
            cur.execute("DELETE FROM presupuestos WHERE id = %s", (presupuesto_id,))
            conn.commit()
        return jsonify({"mensaje": "Presupuesto eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@presupuesto_bp.route("/presupuestos/pdf_simple/<int:presupuesto_id>")
def generar_pdf_simple(presupuesto_id):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cliente, fecha_emision, fecha_validez, total_final FROM presupuestos WHERE id = %s", (presupuesto_id,))
            p = cur.fetchone()
            if not p:
                return "Presupuesto no encontrado", 404

            cur.execute("SELECT producto, cantidad FROM items_presupuesto WHERE presupuesto_id = %s", (presupuesto_id,))
            items = cur.fetchall()

        env = Environment(loader=FileSystemLoader("templates"))
        env.filters['formato_arg'] = formato_arg

        template = env.get_template("plantilla_presupuesto_simple.html")

        rendered_html = template.render(
            cliente=p[0],
            fecha_emision=p[1],
            fecha_validez=p[2],
            total_final=p[3],
            id=presupuesto_id,
            dias_validez=7,
            items=[{"producto": i[0], "cantidad": i[1]} for i in items]
        )

        pdf = HTML(string=rendered_html, base_url=".").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=False,
                         download_name=f"presupuesto_simple_{presupuesto_id}.pdf")

    except Exception as e:
        return str(e), 500
    
@presupuesto_bp.route("/presupuestos/todos", methods=["GET"])
def ver_presupuestos_json():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, cliente, fecha_emision, total_final
                FROM presupuestos
                ORDER BY id DESC
            """)
            rows = cur.fetchall()
            columnas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(columnas, row)) for row in rows]
            return jsonify(resultados)
    except Exception as e:
        print("Error al obtener historial:", e)
        return jsonify({"error": "Error interno"}), 500


