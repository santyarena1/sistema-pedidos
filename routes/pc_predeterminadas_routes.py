# routes/pc_predeterminadas_routes.py

from flask import Blueprint, jsonify, request, render_template, send_file
from config import DB_CONFIG
import psycopg2
import psycopg2.extras
from datetime import date
from io import BytesIO
from weasyprint import HTML

pc_pred_bp = Blueprint("pcs_predeterminadas", __name__)

def get_connection():
    """Establece la conexión con la base de datos."""
    return psycopg2.connect(**DB_CONFIG)

def actualizar_fecha_mod(cur, pc_id):
    """Función ayudante para actualizar la fecha de modificación de una PC."""
    cur.execute("UPDATE pcs_predeterminadas SET ultima_modificacion = NOW() WHERE id = %s", (pc_id,))

@pc_pred_bp.route("/pcs_predeterminadas")
def vista_pcs():
    """Sirve la página principal de PCs Predeterminadas."""
    return render_template("pc_predeterminadas.html")

# --- RUTAS DE LA API ---

@pc_pred_bp.route("/api/pcs_predeterminadas")
def obtener_pcs():
    """[COMPLETO] Obtiene las PCs, ordenadas por más recientes y con las nuevas columnas de fecha."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, nombre, ultima_modificacion, ultima_actualizacion_componente FROM pcs_predeterminadas ORDER BY id DESC")
            pcs = cur.fetchall()
            for pc in pcs:
                pc_id = pc['id']
                cur.execute("SELECT etiqueta FROM pcs_predeterminadas_etiquetas WHERE pc_id = %s", (pc_id,))
                pc['etiquetas'] = [row['etiqueta'] for row in cur.fetchall()]
                cur.execute("SELECT programa FROM pcs_predeterminadas_programas WHERE pc_id = %s", (pc_id,))
                pc['programas'] = [row['programa'] for row in cur.fetchall()]
                cur.execute("""
                    SELECT pcc.id AS pc_componente_id, c.codigo, c.producto AS nombre, c.categoria, c.precio_venta
                    FROM pcs_predeterminadas_componentes pcc
                    JOIN componentes_presupuesto c ON pcc.componente_codigo = c.codigo
                    WHERE pcc.pc_id = %s ORDER BY pcc.orden ASC
                """, (pc_id,))
                componentes_detalle = cur.fetchall()
                pc['componentes_detalle'] = componentes_detalle
                pc['total'] = sum(c['precio_venta'] for c in componentes_detalle)
        return jsonify(pcs)
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas", methods=['POST'])
def crear_pc():
    """Crea una nueva PC predeterminada."""
    nombre = request.get_json().get("nombre")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pcs_predeterminadas (nombre) VALUES (%s) RETURNING id", (nombre,))
            pc_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({"id": pc_id, "nombre": nombre}), 201
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>", methods=['DELETE'])
def eliminar_pc(pc_id):
    """Elimina una PC predeterminada y sus asociaciones."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pcs_predeterminadas WHERE id = %s", (pc_id,))
            conn.commit()
        return jsonify({"mensaje": "PC eliminada"}), 200
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/nombre", methods=["PATCH"])
def editar_nombre(pc_id):
    """[COMPLETO] Edita el nombre de una PC y actualiza su fecha de modificación."""
    data = request.get_json()
    nuevo = data.get("nombre")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE pcs_predeterminadas SET nombre = %s WHERE id = %s", (nuevo, pc_id))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Nombre actualizado"}), 200
    finally:
        if conn: conn.close()
# --- Rutas de Gestión de Componentes en una PC ---

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/componentes", methods=["POST"])
def agregar_componente(pc_id):
    """[COMPLETO] Agrega un componente a una PC y actualiza su fecha de modificación."""
    data = request.get_json()
    codigo = data.get("codigo")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pcs_predeterminadas_componentes (pc_id, componente_codigo) VALUES (%s, %s)", (pc_id, codigo))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Componente agregado"}), 201
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/componentes/<codigo>", methods=["DELETE"])
def eliminar_componente(pc_id, codigo):
    """[COMPLETO] Elimina un componente de una PC y actualiza su fecha de modificación."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pcs_predeterminadas_componentes WHERE pc_id = %s AND componente_codigo = %s", (pc_id, codigo))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Componente eliminado"}), 200
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/componentes/orden", methods=["PATCH"])
def reordenar_componentes(pc_id):
    """[COMPLETO] Actualiza el orden de los componentes y la fecha de modificación de la PC."""
    orden_ids = request.get_json().get("orden_ids")
    if not orden_ids:
        return jsonify({"error": "No se proporcionó un orden"}), 400
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            update_data = [(i + 1, int(component_id)) for i, component_id in enumerate(orden_ids)]
            psycopg2.extras.execute_batch(cur, "UPDATE pcs_predeterminadas_componentes SET orden = %s WHERE id = %s", update_data)
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Orden actualizado con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- Rutas de Gestión de Etiquetas y Programas ---

@pc_pred_bp.route("/api/etiquetas_pc_predeterminadas", methods=['GET'])
def get_etiquetas():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT etiqueta FROM etiquetas_pc_predeterminadas ORDER BY etiqueta")
            return jsonify([row[0] for row in cur.fetchall()])
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/programas_pc_predeterminadas", methods=['GET'])
def get_programas():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT nombre FROM programas_pc_predeterminadas ORDER BY nombre")
            return jsonify([row[0] for row in cur.fetchall()])
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/etiquetas", methods=["POST"])
def agregar_etiqueta(pc_id):
    etiqueta = request.get_json().get("etiqueta")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pcs_predeterminadas_etiquetas (pc_id, etiqueta) VALUES (%s, %s) ON CONFLICT DO NOTHING", (pc_id, etiqueta))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Etiqueta agregada"}), 201
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/etiquetas/<string:etiqueta>", methods=["DELETE"])
def quitar_etiqueta(pc_id, etiqueta):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pcs_predeterminadas_etiquetas WHERE pc_id = %s AND etiqueta = %s", (pc_id, etiqueta))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Etiqueta eliminada"}), 200
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/programas", methods=["POST"])
def agregar_programa(pc_id):
    programa = request.get_json().get("programa")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pcs_predeterminadas_programas (pc_id, programa) VALUES (%s, %s) ON CONFLICT DO NOTHING", (pc_id, programa))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Programa agregado"}), 201
    finally:
        if conn: conn.close()

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/programas/<string:programa>", methods=["DELETE"])
def quitar_programa(pc_id, programa):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pcs_predeterminadas_programas WHERE pc_id = %s AND programa = %s", (pc_id, programa))
            actualizar_fecha_mod(cur, pc_id)
            conn.commit()
        return jsonify({"mensaje": "Programa eliminado"}), 200
    finally:
        if conn: conn.close()

# --- Generación de PDF ---
@pc_pred_bp.route("/pcs_predeterminadas/<int:pc_id>/pdf")
def generar_pdf_pc(pc_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT nombre FROM pcs_predeterminadas WHERE id = %s", (pc_id,))
            pc = cur.fetchone()
            if not pc: return "PC no encontrada", 404

            cur.execute("""
                SELECT c.producto, c.precio_venta
                FROM pcs_predeterminadas_componentes pcc
                JOIN componentes_presupuesto c ON pcc.componente_codigo = c.codigo
                WHERE pcc.pc_id = %s ORDER BY pcc.orden ASC
            """, (pc_id,))
            items = cur.fetchall()
            total_final = sum(item["precio_venta"] for item in items)

            html = render_template("plantilla_presupuesto_simple.html",
                id=pc_id,
                cliente="Consumidor Final",
                fecha_emision=date.today().strftime("%d/%m/%Y"),
                items=items,
                total_final=float(total_final)
            )
            pdf_io = BytesIO()
            HTML(string=html).write_pdf(pdf_io)
            pdf_io.seek(0)
            return send_file(pdf_io, download_name=f"PC_{pc_id}.pdf", as_attachment=False, mimetype='application/pdf')
    finally:
        if conn: conn.close()