# pcs_predeterminadas_routes.py
from flask import Blueprint, jsonify, request, render_template
from config import DB_CONFIG
import psycopg2.extras
from flask import send_file
from datetime import date
from weasyprint import HTML
from io import BytesIO
from decimal import Decimal

pc_pred_bp = Blueprint("pcs_predeterminadas", __name__)




def get_connection():
    return psycopg2.connect(**DB_CONFIG)

@pc_pred_bp.route("/pcs_predeterminadas")
def vista_pcs():
    return render_template("pc_predeterminadas.html")

# --- API: Obtener todas las PCs con etiquetas, programas y componentes ---
@pc_pred_bp.route("/api/pcs_predeterminadas")
def obtener_pcs():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM pcs_predeterminadas ORDER BY id")
    pcs = cur.fetchall()
    for pc in pcs:
        pc_id = pc['id']

        cur.execute("SELECT etiqueta FROM pcs_predeterminadas_etiquetas WHERE pc_id = %s", (pc_id,))
        pc['etiquetas'] = [row['etiqueta'] for row in cur.fetchall()]

        cur.execute("SELECT programa FROM pcs_predeterminadas_programas WHERE pc_id = %s", (pc_id,))
        pc['programas'] = [row['programa'] for row in cur.fetchall()]

        cur.execute("SELECT componente_codigo FROM pcs_predeterminadas_componentes WHERE pc_id = %s", (pc_id,))
        codigos = [row['componente_codigo'] for row in cur.fetchall()]
        pc['componentes'] = codigos

        componentes_detalle = []
        total = 0
        for cod in codigos:
            cur.execute("""
                SELECT codigo, producto AS nombre, categoria, precio_costo, precio_venta
                FROM componentes_presupuesto
                WHERE codigo = %s
            """, (cod,))
            row = cur.fetchone()
            if row:
                componentes_detalle.append(dict(row))
                total += float(row['precio_venta'])


        pc['componentes_detalle'] = componentes_detalle
        pc['total'] = total

    conn.close()
    return jsonify(pcs)


@pc_pred_bp.route("/api/componentes_presupuesto")
def buscar_componentes():
    q = request.args.get("q", "").lower()
    if not q:
        return jsonify([])

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT codigo, producto, categoria, precio_costo, precio_venta
        FROM componentes_presupuesto
        WHERE LOWER(codigo) LIKE %s OR LOWER(producto) LIKE %s

    """, (f"%{q}%", f"%{q}%"))
    resultados = cur.fetchall()
    conn.close()
    return jsonify(resultados)

# --- Crear nueva PC ---
@pc_pred_bp.route("/api/pcs_predeterminadas", methods=["POST"])
def crear_pc():
    data = request.get_json()
    nombre = data.get("nombre")
    if not nombre:
        return jsonify({"error": "Falta nombre"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO pcs_predeterminadas (nombre) VALUES (%s) RETURNING id", (nombre,))
    pc_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"id": pc_id, "nombre": nombre})

# --- Eliminar PC ---
@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>", methods=["DELETE"])
def eliminar_pc(pc_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pcs_predeterminadas WHERE id = %s", (pc_id,))
    conn.commit()
    conn.close()
    return "", 204

# --- Editar nombre ---
@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/nombre", methods=["PATCH"])
def editar_nombre(pc_id):
    data = request.get_json()
    nuevo = data.get("nombre")
    if not nuevo:
        return jsonify({"error": "Falta nuevo nombre"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE pcs_predeterminadas SET nombre = %s WHERE id = %s", (nuevo, pc_id))
    conn.commit()
    conn.close()
    return "", 204

# --- Etiquetas disponibles ---
@pc_pred_bp.route("/api/etiquetas_pc_predeterminadas")
def get_etiquetas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT etiqueta FROM etiquetas_pc_predeterminadas ORDER BY etiqueta")
    etiquetas = [r[0] for r in cur.fetchall()]
    conn.close()
    return jsonify(etiquetas)

# --- Crear nueva etiqueta ---
@pc_pred_bp.route("/api/etiquetas_pc_predeterminadas", methods=["POST"])
def nueva_etiqueta():
    data = request.get_json()
    etiqueta = data.get("etiqueta")
    if not etiqueta:
        return jsonify({"error": "Falta etiqueta"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO etiquetas_pc_predeterminadas (etiqueta) VALUES (%s) ON CONFLICT DO NOTHING", (etiqueta,))
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
    return "", 204

# --- Programas disponibles ---
@pc_pred_bp.route("/api/programas_pc_predeterminadas")
def get_programas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM programas_pc_predeterminadas ORDER BY nombre")
    nombres = [r[0] for r in cur.fetchall()]
    conn.close()
    return jsonify(nombres)


@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/etiquetas", methods=["POST"])
def agregar_etiqueta(pc_id):
    data = request.get_json()
    etiqueta = data.get("etiqueta")
    if not etiqueta:
        return jsonify({"error": "Falta etiqueta"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pcs_predeterminadas_etiquetas (pc_id, etiqueta)
        VALUES (%s, %s) ON CONFLICT DO NOTHING
    """, (pc_id, etiqueta))
    conn.commit()
    conn.close()
    return "", 204

@pc_pred_bp.route("/pcs_predeterminadas/<int:pc_id>/pdf")
def generar_pdf_pc(pc_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT nombre FROM pcs_predeterminadas WHERE id = %s", (pc_id,))
    pc = cur.fetchone()
    if not pc:
        return "PC no encontrada", 404

    cur.execute("""
        SELECT c.codigo, c.precio_venta, c.producto
        FROM pcs_predeterminadas_componentes pc_comp
        JOIN componentes_presupuesto c ON pc_comp.componente_codigo = c.codigo
        LEFT JOIN componentes_presupuesto cp ON c.codigo = cp.codigo
        WHERE pc_comp.pc_id = %s
    """, (pc_id,))
    items = cur.fetchall()
    total_final = sum(item["precio_venta"] * 1 for item in items)  # 1 unidad por componente

    html = render_template("plantilla_presupuesto_simple.html", 
        id=pc_id,
        cliente = "Consumidor Final",
        fecha_emision=date.today().strftime("%d/%m/%Y"),
        fecha_validez=(date.today().replace(day=28)).strftime("%d/%m/%Y"),
        items=[{
            "producto": item.get("producto") or item.get("nombre") or "Sin nombre",
            "cantidad": 1,
            "precio_venta": item["precio_venta"],
            "iva": int(item.get("iva", 0)),
        } for item in items],
        total_final = float(total_final)
    )

    pdf_io = BytesIO()
    HTML(string=html).write_pdf(pdf_io)
    pdf_io.seek(0)

    return send_file(pdf_io, download_name=f"PC_{pc_id}.pdf", as_attachment=False)

@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/programas", methods=["POST"])
def agregar_programa(pc_id):
    data = request.get_json()
    programa = data.get("programa")
    if not programa:
        return jsonify({"error": "Falta programa"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pcs_predeterminadas_programas (pc_id, programa)
        VALUES (%s, %s) ON CONFLICT DO NOTHING
    """, (pc_id, programa))
    conn.commit()
    conn.close()
    return "", 204

# --- Crear nuevo programa ---
@pc_pred_bp.route("/api/programas_pc_predeterminadas", methods=["POST"])
def nuevo_programa():
    data = request.get_json()
    nombre = data.get("nombre")
    if not nombre:
        return jsonify({"error": "Falta nombre"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO programas_pc_predeterminadas (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (nombre,))
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
    return "", 204

# --- Agregar componente a PC ---
@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/componentes", methods=["POST"])
def agregar_componente(pc_id):
    data = request.get_json()
    codigo = data.get("codigo")
    if not codigo:
        return jsonify({"error": "Falta código"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pcs_predeterminadas_componentes (pc_id, componente_codigo)
        VALUES (%s, %s)
    """, (pc_id, codigo))
    conn.commit()
    conn.close()
    return "", 204

# --- Eliminar componente de PC ---
@pc_pred_bp.route("/api/pcs_predeterminadas/<int:pc_id>/componentes/<codigo>", methods=["DELETE"])
def eliminar_componente(pc_id, codigo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM pcs_predeterminadas_componentes
        WHERE pc_id = %s AND componente_codigo = %s
    """, (pc_id, codigo))
    conn.commit()
    conn.close()
    return "", 204
