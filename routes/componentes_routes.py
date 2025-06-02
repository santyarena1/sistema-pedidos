from flask import Blueprint, request, jsonify
from db.connection import conn

componentes_bp = Blueprint("componentes", __name__)

from flask import render_template  # asegurate de tener este import

@componentes_bp.route("/componentes-presupuesto")
def vista_componentes():
    return render_template("componentes_presupuesto.html")

@componentes_bp.route("/api/etiquetas", methods=["POST"])
def agregar_etiqueta():
    data = request.get_json()
    nombre = data.get("nombre")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO etiquetas_compatibilidad (nombre)
                VALUES (%s)
                ON CONFLICT DO NOTHING
            """, (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Etiqueta agregada"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500



# Guardar nueva categoría en BD real
@componentes_bp.route("/api/categorias", methods=["POST"])
def agregar_categoria():
    data = request.get_json()
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "Nombre vacío"}), 400
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categorias_componentes (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Categoría guardada"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Obtener todas las categorías desde BD
@componentes_bp.route("/api/categorias", methods=["GET"])
def obtener_categorias():
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM categorias_componentes ORDER BY nombre")
            categorias = [r[0] for r in cur.fetchall()]
        return jsonify(categorias)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar categoría desde BD
@componentes_bp.route("/api/categorias", methods=["DELETE"])
def eliminar_categoria():
    data = request.get_json()
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "Nombre vacío"}), 400
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categorias_componentes WHERE nombre = %s", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Categoría eliminada"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Eliminar etiqueta desde BD real
@componentes_bp.route("/api/etiquetas", methods=["DELETE"])
def eliminar_etiqueta():
    data = request.get_json()
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "Nombre vacío"}), 400
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM etiquetas_compatibilidad WHERE nombre = %s", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Etiqueta eliminada"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Obtener todos los componentes con sus etiquetas
@componentes_bp.route("/api/componentes", methods=["GET"])
def obtener_componentes():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.codigo, c.categoria, c.producto, c.precio_costo, c.mark_up, c.precio_venta,
                       ARRAY_REMOVE(ARRAY_AGG(e.nombre), NULL) AS etiquetas
                FROM componentes_presupuesto c
                LEFT JOIN componentes_etiquetas ce ON c.id = ce.componente_id
                LEFT JOIN etiquetas_compatibilidad e ON ce.etiqueta_id = e.id
                GROUP BY c.id
                ORDER BY c.id DESC
            """)
            columnas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(columnas, row)) for row in cur.fetchall()]
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear componente nuevo
@componentes_bp.route("/api/componentes", methods=["POST"])
def crear_componente():
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO componentes_presupuesto (codigo, categoria, producto, precio_costo, mark_up, precio_venta)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (data['codigo'], data['categoria'], data['producto'], data['precio_costo'], data['mark_up'], data['precio_venta']))
            componente_id = cur.fetchone()[0]

            for etiqueta in data.get("etiquetas", []):
                cur.execute("SELECT id FROM etiquetas_compatibilidad WHERE nombre = %s", (etiqueta,))
                fila = cur.fetchone()
                if fila:
                    etiqueta_id = fila[0]
                else:
                    cur.execute("INSERT INTO etiquetas_compatibilidad (nombre) VALUES (%s) RETURNING id", (etiqueta,))
                    etiqueta_id = cur.fetchone()[0]
                cur.execute("INSERT INTO componentes_etiquetas (componente_id, etiqueta_id) VALUES (%s, %s)", (componente_id, etiqueta_id))

            conn.commit()
        return jsonify({"mensaje": "Componente creado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Editar componente
@componentes_bp.route("/api/componentes/<int:id>", methods=["PUT"])
def actualizar_componente(id):
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE componentes_presupuesto
                SET codigo=%s, categoria=%s, producto=%s,
                    precio_costo=%s, mark_up=%s, precio_venta=%s
                WHERE id=%s
            """, (data['codigo'], data['categoria'], data['producto'], data['precio_costo'],
                  data['mark_up'], data['precio_venta'], id))
            conn.commit()
        return jsonify({"mensaje": "Componente actualizado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Eliminar componente
@componentes_bp.route("/api/componentes/<int:id>", methods=["DELETE"])
def eliminar_componente(id):
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM componentes_etiquetas WHERE componente_id = %s", (id,))
            cur.execute("DELETE FROM componentes_presupuesto WHERE id = %s", (id,))
            conn.commit()
        return jsonify({"mensaje": "Componente eliminado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Obtener todas las etiquetas
@componentes_bp.route("/api/etiquetas", methods=["GET"])
def obtener_etiquetas():
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM etiquetas_compatibilidad ORDER BY nombre")
            etiquetas = [r[0] for r in cur.fetchall()]
        return jsonify(etiquetas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500