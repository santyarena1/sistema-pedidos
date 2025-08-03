# routes/presupuesto_routes.py

from flask import Blueprint, request, jsonify, render_template, send_file
from db.connection import get_db_connection
import psycopg2.extras
from datetime import date
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io

presupuesto_bp = Blueprint("presupuestos", __name__)

# --- Filtro Jinja para formateo de moneda ---
# REEMPLAZAR EN: routes/presupuesto_routes.py

def formato_arg(valor):
    """
    Filtro Jinja para formatear un número al estilo argentino.
    Versión corregida y simplificada: Asume que el valor de entrada es un número
    y lo formatea correctamente, evitando errores de cálculo.
    """
    try:
        # Convierte el valor a un número flotante para asegurar que sea un número.
        num = float(valor)

        return f"${num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        # Si por alguna razón el valor no es un número, lo devuelve tal cual.
        return valor
# --- Ruta principal para renderizar la página HTML ---
@presupuesto_bp.route("/presupuestos")
def vista_presupuestos():
    """Sirve la página principal modernizada de Gestión de Presupuestos."""
    return render_template("presupuesto_rediseñado.html")

# --- API RESTful para la gestión de Presupuestos ---

# REEMPLAZAR EN: routes/presupuesto_routes.py

@presupuesto_bp.route("/api/presupuestos", methods=["GET"])
def obtener_presupuestos():
    """
    Obtiene una lista de presupuestos.
    Si recibe el parámetro 'componente', filtra los presupuestos que contengan ese ítem.
    """
    componente_query = request.args.get("componente", None)
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if componente_query:
                # Si hay un término de búsqueda, se ejecuta esta consulta con JOIN.
                # Usamos DISTINCT para no repetir presupuestos si un componente aparece varias veces.
                sql = """
                    SELECT DISTINCT p.id, p.cliente, p.fecha_emision, p.total_final, p.descuento
                    FROM presupuestos p
                    JOIN items_presupuesto ip ON p.id = ip.presupuesto_id
                    WHERE LOWER(ip.producto) LIKE %s
                    ORDER BY p.id DESC;
                """
                cur.execute(sql, (f"%{componente_query.lower()}%",))
            else:
                # Si no hay búsqueda, se ejecuta la consulta original que trae todos los presupuestos.
                sql = "SELECT id, cliente, fecha_emision, total_final, descuento FROM presupuestos ORDER BY id DESC"
                cur.execute(sql)

            presupuestos = [dict(row) for row in cur.fetchall()]
        return jsonify(presupuestos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@presupuesto_bp.route("/api/presupuestos/<int:presupuesto_id>", methods=["GET"])
def obtener_presupuesto_detalle(presupuesto_id):
    """Obtiene los detalles completos de un presupuesto, incluyendo sus ítems."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM presupuestos WHERE id = %s", (presupuesto_id,))
            presupuesto = cur.fetchone()
            if not presupuesto:
                return jsonify({"error": "Presupuesto no encontrado"}), 404
            
            presupuesto = dict(presupuesto)
            
            # --- CORRECCIÓN CLAVE ---
            # Se formatea explícitamente la fecha a un string 'YYYY-MM-DD'.
            # Esto evita problemas de zona horaria o formato en el frontend.
            if presupuesto.get('fecha_emision'):
                presupuesto['fecha_emision'] = presupuesto['fecha_emision'].isoformat()
            if presupuesto.get('fecha_validez'):
                presupuesto['fecha_validez'] = presupuesto['fecha_validez'].isoformat()
            
            cur.execute("SELECT * FROM items_presupuesto WHERE presupuesto_id = %s ORDER BY id ASC", (presupuesto_id,))
            presupuesto['items'] = [dict(row) for row in cur.fetchall()]
        return jsonify(presupuesto)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# REEMPLAZAR EN: routes/presupuesto_routes.py

@presupuesto_bp.route("/api/presupuestos", methods=["POST"])
def crear_presupuesto():
    """Crea un nuevo presupuesto y sus ítems."""
    data = request.get_json()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO presupuestos (cliente, fecha_emision, fecha_validez, total_final, descuento)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (
                data.get('cliente'), data.get('fecha_emision'), data.get('fecha_validez'),
                data.get('total_final', 0), data.get('descuento', 0)
            ))
            presupuesto_id = cur.fetchone()[0]

            items_a_insertar = []
            for item in data.get("items", []):
                # ▼▼▼ CORRECCIÓN CLAVE ▼▼▼
                # Se convierte el nombre del producto a mayúsculas.
                producto_mayusculas = item.get('producto', '').upper()
                
                items_a_insertar.append((
                    presupuesto_id, producto_mayusculas,
                    item.get('cantidad', 1), item.get('precio', 0),
                    item.get('precio_venta', 0), item.get('iva', 21)
                ))
            
            psycopg2.extras.execute_batch(cur, """
                INSERT INTO items_presupuesto (presupuesto_id, producto, cantidad, precio, precio_venta, iva)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, items_a_insertar)
            
            conn.commit()
        return jsonify({"mensaje": "Presupuesto creado con éxito", "id": presupuesto_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# REEMPLAZAR EN: routes/presupuesto_routes.py

@presupuesto_bp.route("/api/presupuestos/<int:presupuesto_id>", methods=["PUT"])
def actualizar_presupuesto(presupuesto_id):
    """Actualiza un presupuesto existente y sus ítems."""
    data = request.get_json()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE presupuestos SET cliente=%s, fecha_emision=%s, fecha_validez=%s,
                total_final=%s, descuento=%s, ultima_modificacion=NOW() WHERE id=%s
            """, (
                data.get('cliente'), data.get('fecha_emision'), data.get('fecha_validez'),
                data.get('total_final', 0), data.get('descuento', 0), presupuesto_id
            ))
            
            cur.execute("DELETE FROM items_presupuesto WHERE presupuesto_id=%s", (presupuesto_id,))
            items_a_insertar = []
            for item in data.get("items", []):
                # ▼▼▼ CORRECCIÓN CLAVE ▼▼▼
                # Se convierte el nombre del producto a mayúsculas.
                producto_mayusculas = item.get('producto', '').upper()

                items_a_insertar.append((
                    presupuesto_id, producto_mayusculas,
                    item.get('cantidad', 1), item.get('precio', 0),
                    item.get('precio_venta', 0), item.get('iva', 21)
                ))

            if items_a_insertar:
                 psycopg2.extras.execute_batch(cur, """
                    INSERT INTO items_presupuesto (presupuesto_id, producto, cantidad, precio, precio_venta, iva)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, items_a_insertar)

            conn.commit()
        return jsonify({"mensaje": "Presupuesto actualizado con éxito"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@presupuesto_bp.route("/api/presupuestos/<int:presupuesto_id>", methods=["DELETE"])
def eliminar_presupuesto(presupuesto_id):
    """Elimina un presupuesto y sus ítems asociados."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM presupuestos WHERE id = %s", (presupuesto_id,))
            conn.commit()
        return jsonify({"mensaje": "Presupuesto eliminado"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@presupuesto_bp.route("/presupuestos/pdf/<int:presupuesto_id>")
def generar_pdf_estilizado(presupuesto_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM presupuestos WHERE id = %s", (presupuesto_id,))
            presupuesto = cur.fetchone()
            if not presupuesto: return "Presupuesto no encontrado", 404
            
            cur.execute("SELECT * FROM items_presupuesto WHERE presupuesto_id = %s", (presupuesto_id,))
            items = cur.fetchall()

        env = Environment(loader=FileSystemLoader("templates/"))
        env.filters['formato_arg'] = formato_arg
        template = env.get_template("plantilla_presupuesto.html")
        
        # CORRECCIÓN: Se convierte 'total_final' a float antes de pasarlo a la plantilla.
        # Esto asegura que la multiplicación (ej. total_final * 1.136) funcione correctamente.
        html = template.render(
            id=presupuesto['id'],
            cliente=presupuesto['cliente'],
            fecha_emision=presupuesto['fecha_emision'].strftime('%d/%m/%Y'),
            fecha_validez=presupuesto['fecha_validez'].strftime('%d/%m/%Y'),
            items=items,
            total_final=float(presupuesto['total_final'])
        )
        pdf = HTML(string=html, base_url="static/").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=False,
                         download_name=f"presupuesto_{presupuesto_id}.pdf")
    except Exception as e:
        return str(e), 500
    finally:
        if conn: conn.close()

@presupuesto_bp.route("/presupuestos/pdf_simple/<int:presupuesto_id>")
def generar_pdf_simple(presupuesto_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM presupuestos WHERE id = %s", (presupuesto_id,))
            presupuesto = cur.fetchone()
            if not presupuesto: return "Presupuesto no encontrado", 404
            
            cur.execute("SELECT producto, cantidad FROM items_presupuesto WHERE presupuesto_id = %s", (presupuesto_id,))
            items = cur.fetchall()

        env = Environment(loader=FileSystemLoader("templates/"))
        env.filters['formato_arg'] = formato_arg
        template = env.get_template("plantilla_presupuesto_simple.html")

        # CORRECCIÓN: También se convierte 'total_final' a float aquí.
        html = template.render(
            id=presupuesto['id'],
            cliente=presupuesto['cliente'],
            fecha_emision=presupuesto['fecha_emision'].strftime('%d/%m/%Y'),
            fecha_validez=presupuesto['fecha_validez'].strftime('%d/%m/%Y'),
            items=items,
            total_final=float(presupuesto['total_final'])
        )
        pdf = HTML(string=html, base_url="static/").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=False,
                         download_name=f"presupuesto_simple_{presupuesto_id}.pdf")
    except Exception as e:
        return str(e), 500
    finally:
        if conn: conn.close()