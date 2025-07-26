# routes/componentes_routes.py

from flask import Blueprint, request, jsonify, render_template
from config import DB_CONFIG
import psycopg2
import psycopg2.extras

componentes_bp = Blueprint("componentes", __name__)

def get_db_connection():
    """Establece la conexión con la base de datos."""
    return psycopg2.connect(**DB_CONFIG)

@componentes_bp.route("/componentes-presupuesto")
def vista_componentes():
    """Sirve la página principal de Gestión de Componentes."""
    return render_template("componentes_presupuesto.html")

# --- RUTAS DE LA API PARA COMPONENTES ---

@componentes_bp.route("/api/componentes", methods=["GET"])
def obtener_componentes():
    """
    Obtiene la lista de componentes. Si recibe un parámetro 'q', filtra los resultados.
    """
    query_param = request.args.get("q", "").lower().strip()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if query_param:
                sql = """
                    SELECT c.id, c.codigo, c.producto, c.categoria, c.precio_venta
                    FROM componentes_presupuesto c
                    WHERE LOWER(c.producto) LIKE %s OR LOWER(c.codigo) LIKE %s
                    LIMIT 10;
                """
                cur.execute(sql, (f"%{query_param}%", f"%{query_param}%"))
            else:
                # [CORREGIDO] Se arregló el error de tipeo "etaqueta_id" por "etiqueta_id"
                sql = """
                    SELECT c.id, c.codigo, c.categoria, c.producto, c.precio_costo, c.mark_up, c.precio_venta, c.ultima_modificacion,
                        ARRAY_REMOVE(ARRAY_AGG(e.nombre ORDER BY e.nombre), NULL) AS etiquetas
                    FROM componentes_presupuesto c
                    LEFT JOIN componentes_etiquetas ce ON c.id = ce.componente_id
                    LEFT JOIN etiquetas_compatibilidad e ON ce.etiqueta_id = e.id
                    GROUP BY c.id ORDER BY c.id DESC;
                """
                cur.execute(sql)
            
            resultados = [dict(row) for row in cur.fetchall()]
        return jsonify(resultados)
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/componentes", methods=["POST"])
def crear_componente():
    """
    [CORREGIDO Y ROBUSTO] Crea un nuevo componente y asocia sus etiquetas.
    Maneja correctamente los datos que puedan faltar para evitar errores 500.
    """
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Usamos .get() para todos los campos para evitar que el programa se rompa
            codigo = data.get('codigo', '')
            categoria = data.get('categoria')
            producto = data.get('producto', '').upper() # Convertimos a mayúsculas
            precio_costo = data.get('precio_costo', 0)
            mark_up = data.get('mark_up', 1.3)
            precio_venta = data.get('precio_venta', 0)

            # Validamos que los campos esenciales no estén vacíos
            if not categoria or not producto:
                return jsonify({"error": "La categoría y el nombre del producto son obligatorios."}), 400

            cur.execute("""
                INSERT INTO componentes_presupuesto (codigo, categoria, producto, precio_costo, mark_up, precio_venta)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (codigo, categoria, producto, precio_costo, mark_up, precio_venta))
            componente_id = cur.fetchone()[0]

            for etiqueta_nombre in data.get("etiquetas", []):
                cur.execute("SELECT id FROM etiquetas_compatibilidad WHERE nombre = %s", (etiqueta_nombre,))
                etiqueta_id_row = cur.fetchone()
                if etiqueta_id_row:
                    etiqueta_id = etiqueta_id_row[0]
                    cur.execute("INSERT INTO componentes_etiquetas (componente_id, etiqueta_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (componente_id, etiqueta_id))
            
            conn.commit()
        return jsonify({"mensaje": "Componente creado con éxito"}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

        
@componentes_bp.route("/api/componentes/<int:id>", methods=["PUT"])
def actualizar_componente(id):
    """
    [COMPLETO] Actualiza un componente, sus etiquetas, y la fecha
    'ultima_actualizacion_componente' en las PCs que lo usan.
    """
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Primero, obtenemos el código original del componente antes de cualquier cambio
            cur.execute("SELECT codigo FROM componentes_presupuesto WHERE id = %s", (id,))
            componente = cur.fetchone()
            if not componente:
                return jsonify({"error": "Componente no encontrado"}), 404
            
            codigo_componente_original = componente[0]
            producto_mayusculas = data.get('producto', '').upper()

            # Actualizamos el componente, incluyendo la fecha de su propia modificación
            cur.execute("""
                UPDATE componentes_presupuesto
                SET codigo=%s, categoria=%s, producto=%s, precio_costo=%s, mark_up=%s, precio_venta=%s, ultima_modificacion=NOW()
                WHERE id=%s
            """, (data['codigo'], data['categoria'], producto_mayusculas, data['precio_costo'], data['mark_up'], data['precio_venta'], id))
            
            # Ahora, actualizamos la fecha en todas las PCs que usan este componente
            cur.execute("""
                UPDATE pcs_predeterminadas
                SET ultima_actualizacion_componente = NOW()
                WHERE id IN (SELECT pc_id FROM pcs_predeterminadas_componentes WHERE componente_codigo = %s)
            """, (codigo_componente_original,))

            # Finalmente, actualizamos las etiquetas de compatibilidad (borrar y re-insertar)
            cur.execute("DELETE FROM componentes_etiquetas WHERE componente_id = %s", (id,))
            for etiqueta_nombre in data.get("etiquetas", []):
                cur.execute("SELECT id FROM etiquetas_compatibilidad WHERE nombre = %s", (etiqueta_nombre,))
                etiqueta_id_row = cur.fetchone()
                if etiqueta_id_row:
                    etiqueta_id = etiqueta_id_row[0]
                    cur.execute("INSERT INTO componentes_etiquetas (componente_id, etiqueta_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (id, etiqueta_id))

            conn.commit()
        return jsonify({"mensaje": "Componente y PCs referenciadas actualizadas con éxito"})
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en actualizar_componente: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

        
@componentes_bp.route("/api/componentes/<int:id>", methods=["DELETE"])
def eliminar_componente(id):
    """Elimina un componente de la base de datos."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM componentes_etiquetas WHERE componente_id = %s", (id,))
            cur.execute("DELETE FROM componentes_presupuesto WHERE id = %s", (id,))
            conn.commit()
        return jsonify({"mensaje": "Componente eliminado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- RUTAS PARA CATEGORÍAS Y ETIQUETAS ---

@componentes_bp.route("/api/categorias", methods=["GET"])
def obtener_categorias():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM categorias_componentes ORDER BY nombre")
            return jsonify([row[0] for row in cur.fetchall()])
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/categorias", methods=["POST"])
def agregar_categoria():
    nombre = request.get_json().get("nombre", "").strip()
    if not nombre: return jsonify({"error": "Nombre vacío"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categorias_componentes (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Categoría guardada"}), 201
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/categorias", methods=["DELETE"])
def eliminar_categoria():
    nombre = request.get_json().get("nombre", "").strip()
    if not nombre: return jsonify({"error": "Nombre vacío"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM componentes_presupuesto WHERE categoria = %s LIMIT 1", (nombre,))
            if cur.fetchone():
                return jsonify({"error": "No se puede eliminar la categoría porque está en uso."}), 409
            cur.execute("DELETE FROM categorias_componentes WHERE nombre = %s", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Categoría eliminada"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/etiquetas", methods=["GET"])
def obtener_etiquetas():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM etiquetas_compatibilidad ORDER BY nombre")
            return jsonify([row[0] for row in cur.fetchall()])
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/etiquetas", methods=["POST"])
def agregar_etiqueta():
    nombre = request.get_json().get("nombre")
    if not nombre: return jsonify({"error": "Nombre vacío"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO etiquetas_compatibilidad (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Etiqueta agregada"}), 201
    finally:
        if conn: conn.close()

@componentes_bp.route("/api/etiquetas", methods=["DELETE"])
def eliminar_etiqueta():
    nombre = request.get_json().get("nombre", "").strip()
    if not nombre: return jsonify({"error": "Nombre vacío"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM etiquetas_compatibilidad WHERE nombre = %s", (nombre,))
            conn.commit()
        return jsonify({"mensaje": "Etiqueta eliminada"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()