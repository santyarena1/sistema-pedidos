from flask import Blueprint, request, render_template, jsonify, send_file
from db.connection import get_db_connection
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io
import base64
import psycopg2.extras

pedidos_bp = Blueprint("pedidos", __name__)

# --- Rutas HTML ---
@pedidos_bp.route("/pedidos")
def formulario_pedidos():
    return render_template("pedidos.html")

@pedidos_bp.route("/pedidos/lista")
def lista_pedidos():
    return render_template("pedidos_lista.html")

@pedidos_bp.route("/pedidos", methods=["POST"])
def guardar_pedido():
    """
    Guarda un nuevo pedido en la base de datos con todos sus detalles,
    incluyendo productos, pagos, observaciones y el estado de cada producto.
    """
    data = request.get_json()
    if not data or "nombre_cliente" not in data or not data.get("productos"):
        return jsonify({"error": "Faltan datos obligatorios (cliente o productos)."}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT MAX(numero) FROM pedidos")
        ultimo_numero = cur.fetchone()[0]
        nuevo_numero = (ultimo_numero or 0) + 1

        fecha_emision = datetime.strptime(data["fecha_emision"], "%Y-%m-%d").date()
        fecha_entrega = None # Puedes ajustar esta lógica si es necesario

        cur.execute("""
            INSERT INTO pedidos (
                numero, nombre_cliente, dni_cliente, email, telefono,
                direccion, tipo_factura, fecha_emision, fecha_entrega,
                origen_venta, vendedor, forma_envio, costo_envio, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            nuevo_numero, data.get("nombre_cliente"), data.get("dni_cliente"),
            data.get("email"), data.get("telefono"), data.get("direccion"),
            data.get("tipo_factura"), fecha_emision, fecha_entrega,
            data.get("origen_venta"), data.get("vendedor"),
            data.get("forma_envio"), float(data.get("costo_envio") or 0),
            data.get("observaciones")
        ))
        pedido_id = cur.fetchone()[0]

        for item in data.get("productos", []):
            cur.execute("""
                INSERT INTO productos_pedido (
                    pedido_id, producto, cantidad, precio_venta, estado_producto
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                pedido_id, item["producto"], item["cantidad"],
                item["precio_venta"], item.get("estado_producto", "PARA HACER")
            ))

        # 5. Insertar los pagos (si existen)
        for pago in data.get("pagos", []):
            # --- CORRECCIÓN AQUÍ ---
            # Se ajustó el orden de las columnas (metodo, monto) para que coincida con la tabla.
            # Se cambió 'fecha_pago' por 'fecha'.
            cur.execute("""
                INSERT INTO pagos (
                    pedido_id, metodo, monto, tipo_cambio, fecha
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                pedido_id,
                pago["metodo"], # <-- Columna 2: metodo (texto)
                pago["monto"],  # <-- Columna 3: monto (número)
                pago.get("tipo_cambio"),
                datetime.strptime(pago["fecha"], "%Y-%m-%d").date()
            ))

        conn.commit()
        return jsonify({
            "message": f"Pedido N°{nuevo_numero} guardado con éxito.",
            "id": pedido_id,
            "numero": nuevo_numero
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en guardar_pedido: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- Constancia de Seña en PDF ---
@pedidos_bp.route("/pedidos/sena/<int:pedido_id>")
def generar_constancia_sena(pedido_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT numero, nombre_cliente, dni_cliente, email, telefono, direccion,
                       tipo_factura, forma_envio, costo_envio, to_char(fecha_emision, 'DD/MM/YYYY') as fecha_emision
                FROM pedidos WHERE id = %s
            """, (pedido_id,))
            p = cur.fetchone()
            if not p: return "Pedido no encontrado", 404

            pedido_dict = dict(zip([desc[0] for desc in cur.description], p))
            
            cur.execute("SELECT producto, cantidad FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
            pedido_dict["productos"] = [{"producto": r[0], "cantidad": r[1]} for r in cur.fetchall()]

            cur.execute("SELECT monto FROM pagos WHERE pedido_id = %s", (pedido_id,))
            total_abonado = sum([r[0] for r in cur.fetchall()])
            pedido_dict["abonado"] = total_abonado

            cur.execute("SELECT SUM(cantidad * precio_venta) FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
            total_productos = cur.fetchone()[0] or 0
            total = total_productos + (pedido_dict["costo_envio"] or 0)
            pedido_dict["total"] = total
            pedido_dict["restante"] = total - total_abonado

        env = Environment(loader=FileSystemLoader("templates"))
        env.filters["formato_arg"] = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        template = env.get_template("plantilla_sena.html")
        html = template.render(**pedido_dict)
        pdf = HTML(string=html, base_url="static/").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", download_name=f"sena_{pedido_id}.pdf")

    except Exception as e:
        return str(e), 500
    finally:
        if conn: conn.close()

# En pedidos_routes.py

# En: pedidos_routes.py

@pedidos_bp.route("/pedidos/todos")
def obtener_todos_los_pedidos():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT 
                    id, numero, nombre_cliente, dni_cliente, email, telefono, direccion, tipo_factura,
                    to_char(fecha_emision, 'YYYY-MM-DD') as fecha_emision,
                    to_char(fecha_entrega, 'YYYY-MM-DD') as fecha_entrega,
                    origen_venta, vendedor, forma_envio, costo_envio, estado_general, factura_base64,
                    ultima_modificacion,
                    observaciones -- SOLUCIÓN: Se agrega la columna que faltaba.
                FROM pedidos
                ORDER BY numero DESC
            """)
            pedidos = [dict(row) for row in cur.fetchall()]

            for pedido in pedidos:
                cur.execute("SELECT * FROM productos_pedido WHERE pedido_id = %s", (pedido["id"],))
                pedido["productos"] = [dict(row) for row in cur.fetchall()]
                
                cur.execute("""
                    SELECT id, pedido_id, metodo, monto, tipo_cambio, to_char(fecha, 'YYYY-MM-DD') as fecha
                    FROM pagos WHERE pedido_id = %s
                """, (pedido["id"],))
                pagos = [dict(row) for row in cur.fetchall()]
                pedido["pagos"] = pagos

                total_productos = sum((p.get('precio_venta') or 0) * (p.get('cantidad') or 1) for p in pedido['productos'])
                costo_envio = pedido.get('costo_envio') or 0
                pedido['total_venta'] = total_productos + costo_envio
                
                total_abonado_calculado = 0
                for pago in pagos:
                    monto = pago.get('monto') or 0
                    if pago.get('metodo') in ['USD', 'USDT']:
                        tipo_cambio = pago.get('tipo_cambio') or 1
                        total_abonado_calculado += monto * tipo_cambio
                    else:
                        total_abonado_calculado += monto
                pedido['total_abonado'] = total_abonado_calculado

        return jsonify(pedidos)
    except Exception as e:
        print("Error al obtener pedidos:", e)
        return jsonify({"error": "Error interno"}), 500
    finally:
        if conn:
            conn.close()

# --- Actualizar Pedido ---
# routes/pedidos_routes.py

# En: pedidos_routes.py

@pedidos_bp.route("/pedidos/<int:pedido_id>", methods=["PATCH"])
def actualizar_pedido(pedido_id):
    data = request.get_json()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # SOLUCIÓN: Se agrega "observaciones = %s" a la consulta UPDATE
            cur.execute("""
                UPDATE pedidos
                SET nombre_cliente = %s, dni_cliente = %s, email = %s, telefono = %s, direccion = %s,
                    tipo_factura = %s, fecha_emision = %s, origen_venta = %s, vendedor = %s, forma_envio = %s,
                    costo_envio = %s, estado_general = %s, observaciones = %s, ultima_modificacion = NOW()
                WHERE id = %s
            """, (
                data.get("nombre_cliente"), data.get("dni_cliente"), data.get("email"),
                data.get("telefono"), data.get("direccion"), data.get("tipo_factura"),
                data.get("fecha_emision"), data.get("origen_venta"),
                data.get("vendedor"), data.get("forma_envio"),
                float(data.get("costo_envio", 0)), data.get("estado_general"),
                data.get("observaciones"), # SOLUCIÓN: Se pasa el valor de las observaciones
                pedido_id
            ))

            # Se reconstruyen los productos y pagos (esta parte no cambia)
            cur.execute("DELETE FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
            for producto in data.get("productos", []):
                estado_producto = 'ENTREGADO' if data.get("estado_general") == 'ENTREGADO' else producto.get("estado_producto", "PARA HACER")
                cur.execute("""
                    INSERT INTO productos_pedido (pedido_id, proveedor, producto, sku, precio_venta, cantidad, estado_producto, cambio)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    pedido_id, producto.get("proveedor"), producto.get("producto"),
                    producto.get("sku"), float(producto.get("precio_venta", 0)),
                    int(producto.get("cantidad", 1)), estado_producto,
                    producto.get("cambio", False)
                ))

            cur.execute("DELETE FROM pagos WHERE pedido_id = %s", (pedido_id,))
            for pago in data.get("pagos", []):
                cur.execute("""
                    INSERT INTO pagos (pedido_id, metodo, monto, tipo_cambio, fecha)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    pedido_id, pago.get("metodo"), float(pago.get("monto", 0)),
                    pago.get("tipo_cambio"), pago.get("fecha")
                ))
            
            conn.commit()
        return jsonify({"mensaje": "Pedido actualizado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al actualizar pedido: {e}") # Logueo de error mejorado
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- Subir y Descargar Factura (Sin cambios) ---
@pedidos_bp.route("/pedidos/<int:pedido_id>/factura", methods=["POST"])
def subir_factura(pedido_id):
    file = request.files.get("factura")
    if not file: return jsonify({"error": "No se recibió el archivo"}), 400
    contenido = file.read()
    base64_factura = base64.b64encode(contenido).decode()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE pedidos SET factura_base64 = %s, ultima_modificacion = NOW() WHERE id = %s", (base64_factura, pedido_id))
            conn.commit()
        return jsonify({"mensaje": "Factura subida"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@pedidos_bp.route("/pedidos/<int:pedido_id>/factura", methods=["GET"])
def descargar_factura(pedido_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT factura_base64 FROM pedidos WHERE id = %s", (pedido_id,))
            row = cur.fetchone()
            if not row or not row[0]: return "Factura no encontrada", 404
            contenido = base64.b64decode(row[0])
        return send_file(io.BytesIO(contenido), mimetype="application/pdf", as_attachment=True, download_name=f"factura_pedido_{pedido_id}.pdf")
    except Exception as e:
        return str(e), 500
    finally:
        if conn: conn.close()

# En: pedidos_routes.py
@pedidos_bp.route("/pedidos/<int:pedido_id>/constancia_entrega", methods=["GET"])
def generar_constancia_entrega(pedido_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Se obtiene el pedido principal
            cur.execute("SELECT *, to_char(fecha_emision, 'DD/MM/YYYY') as fecha_emision_formateada FROM pedidos WHERE id = %s", (pedido_id,))
            pedido = cur.fetchone()
            if not pedido:
                return "Pedido no encontrado", 404
            
            # Convertir a un diccionario mutable para poder añadirle claves
            pedido = dict(pedido)
            
            # SOLUCIÓN: Se obtienen los productos y se añaden al diccionario del pedido
            cur.execute("SELECT * FROM productos_pedido WHERE pedido_id = %s ORDER BY id", (pedido_id,))
            productos = [dict(row) for row in cur.fetchall()]
            pedido["productos"] = productos

        # El resto de la función para generar el PDF
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("plantilla_constancia_entrega.html")
        html = template.render(pedido=pedido) # La plantilla recibirá el pedido con la lista de productos dentro
        pdf = HTML(string=html, base_url="static/").write_pdf()
        
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", download_name=f"constancia_entrega_{pedido_id}.pdf")

    except Exception as e:
        print(f"Error generando constancia de entrega: {e}")
        return str(e), 500
    finally:
        if conn:
            conn.close()

# routes/pedidos_routes.py

@pedidos_bp.route("/pedidos/<int:pedido_id>", methods=["DELETE"])
def eliminar_pedido(pedido_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pedidos WHERE id = %s RETURNING id", (pedido_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Pedido no encontrado"}), 404
            conn.commit()
            return jsonify({"mensaje": "Pedido eliminado con éxito"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# Agrégalo en pedidos_routes.py

@pedidos_bp.route("/pedidos/producto/<int:producto_id>/estado", methods=["PATCH"])
def actualizar_estado_producto(producto_id):
    data = request.get_json()
    nuevo_estado = data.get("estado")
    if not nuevo_estado:
        return jsonify({"error": "Falta el nuevo estado"}), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE productos_pedido SET estado_producto = %s WHERE id = %s",
                (nuevo_estado, producto_id)
            )
            conn.commit()
        return jsonify({"mensaje": "Estado del producto actualizado"}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error al actualizar estado del producto: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()