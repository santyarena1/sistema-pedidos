from flask import Blueprint, request, jsonify, render_template
# --- CAMBIO 1: Importamos la nueva función en lugar de la variable 'conn' ---
from db.connection import get_db_connection
import psycopg2.extras

pc_armadas_bp = Blueprint("pc_armadas", __name__)

# Ruta que devuelve el HTML (sin cambios)
@pc_armadas_bp.route("/pc_armadas")
def pc_armadas():
    return render_template("pc_armadas.html")

# Ruta separada para devolver PCs armadas en JSON
@pc_armadas_bp.route("/api/pc_armadas", methods=["GET"])
def api_ver_pc_armadas():
    conn = None
    try:
        # --- CAMBIO 2: Obtenemos una conexión nueva ---
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Tu consulta SQL original se mantiene intacta
            cur.execute("""
                SELECT p.id, p.presupuesto_id, p.creado_en, p.nombre_presupuesto,
                       pr.cliente, pr.total_final,
                       ARRAY_REMOVE(ARRAY_AGG(e.etiqueta), NULL) as etiquetas
                FROM pc_armadas p
                JOIN presupuestos pr ON p.presupuesto_id = pr.id
                LEFT JOIN etiquetas_pc e ON p.id = e.pc_id
                GROUP BY p.id, pr.cliente, pr.total_final
                ORDER BY p.creado_en DESC
            """)
            # Usamos DictCursor para convertir las filas a diccionarios fácilmente
            resultados = [dict(row) for row in cur.fetchall()]
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # --- CAMBIO 3: Cerramos la conexión al terminar ---
        if conn:
            conn.close()

# Ruta para agregar una PC armada
@pc_armadas_bp.route("/pc_armadas", methods=["POST"])
def agregar_pc_armada():
    data = request.get_json()
    presupuesto_id = data.get("presupuesto_id")
    etiquetas = data.get("etiquetas", [])

    if not presupuesto_id:
        return jsonify({"error": "ID de presupuesto faltante"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pc_armadas (presupuesto_id) VALUES (%s) RETURNING id", (presupuesto_id,))
            pc_id = cur.fetchone()[0]

            for etiqueta in etiquetas:
                cur.execute("INSERT INTO etiquetas_pc (pc_id, etiqueta) VALUES (%s, %s)", (pc_id, etiqueta.strip()))

            conn.commit()
        return jsonify({"mensaje": "PC Armada guardada", "id": pc_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para buscar PCs armadas por etiqueta
@pc_armadas_bp.route("/pc_armadas/buscar", methods=["GET"])
def buscar_por_etiqueta():
    query = request.args.get("q", "").lower()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT p.id, p.presupuesto_id, p.creado_en
                FROM pc_armadas p
                JOIN etiquetas_pc e ON p.id = e.pc_id
                WHERE LOWER(e.etiqueta) LIKE %s
                ORDER BY p.creado_en DESC
            """, (f"%{query}%",))
            pcs = [dict(row) for row in cur.fetchall()]
        return jsonify(pcs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para eliminar una PC armada
@pc_armadas_bp.route("/pc_armadas/<int:pc_id>", methods=["DELETE"])
def eliminar_pc_armada(pc_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM etiquetas_pc WHERE pc_id = %s", (pc_id,))
            cur.execute("DELETE FROM pc_armadas WHERE id = %s", (pc_id,))
            conn.commit()
        return jsonify({"mensaje": "PC Armada eliminada"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para editar el nombre del presupuesto dentro de PC Armadas
@pc_armadas_bp.route("/pc_armadas/<int:pc_id>/editar_nombre", methods=["PATCH"])
def editar_nombre_presupuesto(pc_id):
    data = request.get_json()
    nuevo_nombre = data.get("nombre_presupuesto")

    if not nuevo_nombre:
        return jsonify({"error": "Falta el nuevo nombre"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE pc_armadas SET nombre_presupuesto = %s WHERE id = %s", (nuevo_nombre, pc_id))
            conn.commit()
        return jsonify({"mensaje": "Nombre actualizado"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para agregar etiqueta a una PC armada
@pc_armadas_bp.route("/pc_armadas/<int:pc_id>/etiquetas", methods=["POST"])
def agregar_etiqueta(pc_id):
    data = request.get_json()
    etiqueta = data.get("etiqueta", "").strip()

    if not etiqueta:
        return jsonify({"error": "Etiqueta vacía"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO etiquetas_pc (pc_id, etiqueta) VALUES (%s, %s)", (pc_id, etiqueta))
            conn.commit()
        return jsonify({"mensaje": "Etiqueta agregada"}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Ruta para obtener todas las etiquetas existentes
@pc_armadas_bp.route("/pc_armadas/etiquetas", methods=["GET"])
def obtener_todas_etiquetas():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT etiqueta FROM etiquetas_pc ORDER BY etiqueta")
            etiquetas = [r[0] for r in cur.fetchall()]
        return jsonify(etiquetas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()