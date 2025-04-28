from flask import Blueprint, request, render_template, jsonify, send_file
from db.connection import conn
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io
import base64
from datetime import timedelta


pedidos_bp = Blueprint("pedidos", __name__)

# HTML
@pedidos_bp.route("/pedidos")
def formulario_pedidos():
    return render_template("pedidos.html")

@pedidos_bp.route("/pedidos/lista")
def lista_pedidos():
    return render_template("pedidos_lista.html")

# Guardar Pedido
@pedidos_bp.route("/pedidos", methods=["POST"])
def guardar_pedido():
    data = request.get_json()
    try:
        with conn.cursor() as cur:
            # Generar número de pedido
            cur.execute("SELECT COALESCE(MAX(numero), 999) + 1 FROM pedidos")
            numero = cur.fetchone()[0]

            # Insertar pedido
            fecha_emision = datetime.strptime(data.get("fecha_emision"), "%Y-%m-%d").date()
            fecha_entrega = fecha_emision + timedelta(days=7)  # aprox. 5 hábiles

            cur.execute("""
                INSERT INTO pedidos (
                    numero, nombre_cliente, dni_cliente, email, telefono,
                    direccion, tipo_factura, fecha_emision, fecha_entrega,
                    origen_venta, vendedor, forma_envio, costo_envio
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                numero,
                data.get("nombre_cliente"),
                data.get("dni_cliente"),
                data.get("email"),
                data.get("telefono"),
                data.get("direccion"),
                data.get("tipo_factura"),
                fecha_emision,
                fecha_entrega,
                data.get("origen_venta"),
                data.get("vendedor"),
                data.get("forma_envio"),
                float(data.get("costo_envio", 0))
            ))
            pedido_id = cur.fetchone()[0]

            # Productos
            for item in data.get("productos", []):
                cur.execute("""
                    INSERT INTO productos_pedido (pedido_id, producto, cantidad, precio_venta)
                    VALUES (%s, %s, %s, %s)
                """, (pedido_id, item["producto"], item["cantidad"], item["precio_venta"]))

            # Pagos
            for pago in data.get("pagos", []):
                cur.execute("""
                    INSERT INTO pagos (pedido_id, metodo, monto, tipo_cambio)
                    VALUES (%s, %s, %s, %s)
                """, (
                    pedido_id,
                    pago["metodo"],
                    pago["monto"],
                    pago.get("tipo_cambio")
                ))


            conn.commit()
        return jsonify({"mensaje": "Pedido guardado", "id": pedido_id, "numero": numero}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Constancia de Seña en PDF
@pedidos_bp.route("/pedidos/sena/<int:pedido_id>")
def generar_constancia_sena(pedido_id):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT numero, nombre_cliente, dni_cliente, email, telefono, direccion,
                       tipo_factura, forma_envio, costo_envio, fecha_emision
                FROM pedidos WHERE id = %s
            """, (pedido_id,))
            p = cur.fetchone()
            if not p:
                return "Pedido no encontrado", 404

            pedido_dict = {
                "numero": f"N{p[0]}",
                "cliente": p[1],
                "dni": p[2],
                "email": p[3],
                "telefono": p[4],
                "direccion": p[5],
                "tipo_factura": p[6],
                "forma_envio": p[7],
                "costo_envio": p[8],
                "fecha_emision": p[9].strftime("%d/%m/%Y")
            }

            # Productos
            cur.execute("SELECT producto, cantidad FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
            pedido_dict["productos"] = [{"producto": r[0], "cantidad": r[1]} for r in cur.fetchall()]

            # Pagos
            cur.execute("SELECT monto FROM pagos WHERE pedido_id = %s", (pedido_id,))
            pagos = [r[0] for r in cur.fetchall()]
            total_abonado = sum(pagos)
            pedido_dict["abonado"] = total_abonado

            # Total estimado (precio_venta x cantidad)
            cur.execute("SELECT SUM(cantidad * precio_venta) FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
            total_productos = cur.fetchone()[0] or 0
            total = total_productos + (pedido_dict["costo_envio"] or 0)
            pedido_dict["total"] = total
            pedido_dict["restante"] = total - total_abonado

        # Render PDF
        env = Environment(loader=FileSystemLoader("templates"))
        env.filters["formato_arg"] = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        template = env.get_template("plantilla_sena.html")
        html = template.render(**pedido_dict)
        pdf = HTML(string=html, base_url=".").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", download_name=f"sena_{pedido_id}.pdf")

    except Exception as e:
        return str(e), 500




# --- Rutas NUEVAS a agregar debajo de lo que ya tenés ---

@pedidos_bp.route("/pedidos/todos")
def obtener_todos_los_pedidos():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    p.id, p.numero, p.nombre_cliente, p.telefono, p.dni_cliente, p.direccion, 
                    p.email, p.vendedor, p.fecha_emision, p.fecha_entrega,
                    p.origen_venta, p.forma_envio, p.costo_envio, p.tipo_factura,
                    p.estado_general, p.ultima_modificacion
                FROM pedidos p
                ORDER BY p.numero DESC
            """)
            pedidos = []
            for row in cur.fetchall():
                pedido = {
                    "id": row[0],
                    "numero": row[1],
                    "nombre_cliente": row[2],
                    "telefono": row[3],
                    "dni_cliente": row[4],  # <- agregado
                    "direccion": row[5],
                    "email": row[6],
                    "vendedor": row[7],
                    "fecha_emision": row[8].isoformat() if row[8] else None,
                    "fecha_entrega": row[9].isoformat() if row[9] else None,
                    "origen_venta": row[10],
                    "forma_envio": row[11],
                    "costo_envio": float(row[12]),
                    "tipo_factura": row[13],
                    "estado_general": row[14],
                    "ultima_modificacion": row[15].isoformat() if row[15] else None,
                    "productos": [],
                    "pagos": []
                }

                # Productos
                cur.execute("""
                    SELECT proveedor, producto, sku, precio_venta, cantidad, estado_producto, cambio
                    FROM productos_pedido
                    WHERE pedido_id = %s
                """, (pedido["id"],))
                pedido["productos"] = [{
                    "proveedor": r[0],
                    "producto": r[1],
                    "sku": r[2],
                    "precio_venta": float(r[3]),
                    "cantidad": r[4],
                    "estado_producto": r[5],
                    "cambio": r[6]
                } for r in cur.fetchall()]

                # Pagos
                cur.execute("""
                    SELECT metodo, monto, tipo_cambio, fecha
                    FROM pagos
                    WHERE pedido_id = %s
                """, (pedido["id"],))
                pedido["pagos"] = [{
                    "metodo": r[0],
                    "monto": float(r[1]),
                    "tipo_cambio": float(r[2]) if r[2] else None,
                    "fecha": r[3].isoformat() if r[3] else None
                } for r in cur.fetchall()]

                pedidos.append(pedido)

        return jsonify(pedidos)
    except Exception as e:
        print("❌ Error al obtener pedidos:", e)
        return jsonify({"error": "Error interno"}), 500




@pedidos_bp.route("/pedidos/<int:pedido_id>", methods=["PATCH"])
def actualizar_pedido(pedido_id):
    data = request.get_json()
    print("📦 Datos recibidos:", data)  # Para debug

    try:
        with conn.cursor() as cur:
            # Actualizar pedido (con valores seguros por defecto)
            cur.execute("""
                UPDATE pedidos
                SET nombre_cliente = %s, dni_cliente = %s, email = %s, telefono = %s, direccion = %s,
                    tipo_factura = %s, fecha_emision = %s, origen_venta = %s, vendedor = %s, forma_envio = %s,
                    costo_envio = %s, estado_general = %s, ultima_modificacion = NOW()
                WHERE id = %s
            """, (
                data.get("nombre_cliente", ""),
                data.get("dni_cliente", ""),
                data.get("email", ""),
                data.get("telefono", ""),
                data.get("direccion", ""),
                data.get("tipo_factura", ""),
                data.get("fecha_emision", "2000-01-01"),
                data.get("origen_venta", ""),
                data.get("vendedor", ""),
                data.get("forma_envio", ""),
                float(data.get("costo_envio", 0)),
                data.get("estado_general", ""),
                pedido_id
            ))

            # Borrar e insertar productos si existen
            if "productos" in data:
                cur.execute("DELETE FROM productos_pedido WHERE pedido_id = %s", (pedido_id,))
                for producto in data["productos"]:
                    cur.execute("""
                        INSERT INTO productos_pedido (pedido_id, proveedor, producto, sku, precio_venta, cantidad, estado_producto, cambio)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        pedido_id,
                        producto.get("proveedor", ""),
                        producto.get("producto", ""),
                        producto.get("sku", ""),
                        float(producto.get("precio_venta", 0)),
                        int(producto.get("cantidad", 1)),
                        producto.get("estado_producto", ""),
                        bool(producto.get("cambio", False))
                    ))

            # Borrar e insertar pagos si existen
            if "pagos" in data:
                cur.execute("DELETE FROM pagos WHERE pedido_id = %s", (pedido_id,))
                for pago in data["pagos"]:
                    cur.execute("""
                        INSERT INTO pagos (pedido_id, metodo, monto, tipo_cambio, fecha)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        pedido_id,
                        pago.get("metodo", ""),
                        float(pago.get("monto", 0)),
                        pago.get("tipo_cambio"),
                        pago.get("fecha", "2000-01-01")
                    ))

            conn.commit()
        return jsonify({"mensaje": "Pedido actualizado"}), 200

    except Exception as e:
        conn.rollback()
        print("❌ Error actualizando pedido:", e)
        return jsonify({"error": str(e)}), 500




@pedidos_bp.route("/pedidos/<int:pedido_id>/factura", methods=["POST"])
def subir_factura(pedido_id):
    file = request.files.get("factura")
    if not file:
        return jsonify({"error": "No se recibió el archivo"}), 400

    contenido = file.read()
    base64_factura = base64.b64encode(contenido).decode()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pedidos
                SET factura_base64 = %s, ultima_modificacion = NOW()
                WHERE id = %s
            """, (base64_factura, pedido_id))
            conn.commit()
        return jsonify({"mensaje": "Factura subida"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@pedidos_bp.route("/pedidos/<int:pedido_id>/factura", methods=["GET"])
def descargar_factura(pedido_id):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT factura_base64 FROM pedidos WHERE id = %s", (pedido_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                return "Factura no encontrada", 404

            contenido = base64.b64decode(row[0])
            return send_file(
                io.BytesIO(contenido),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"factura_pedido_{pedido_id}.pdf"
            )
    except Exception as e:
        return str(e), 500


@pedidos_bp.route("/pedidos/<int:pedido_id>/constancia_entrega", methods=["GET"])
def generar_constancia_entrega(pedido_id):
    try:
        with conn.cursor() as cur:
            # Obtener datos del pedido
            cur.execute("""
                SELECT numero, nombre_cliente, dni_cliente, telefono, email, direccion, tipo_factura, forma_envio, fecha_emision
                FROM pedidos
                WHERE id = %s
            """, (pedido_id,))
            p = cur.fetchone()

            if not p:
                return "Pedido no encontrado", 404

            pedido = {
                "numero": p[0],
                "cliente": p[1],
                "dni": p[2],
                "telefono": p[3],
                "email": p[4],
                "direccion": p[5],
                "tipo_factura": p[6],
                "forma_envio": p[7],
                "fecha_emision": p[8].strftime("%d/%m/%Y") if p[8] else "-",
                "productos": []
            }

            # Obtener productos
            cur.execute("""
                SELECT sku, cantidad, producto
                FROM productos_pedido
                WHERE pedido_id = %s
            """, (pedido_id,))
            for row in cur.fetchall():
                pedido["productos"].append({
                    "sku": row[0],
                    "cantidad": row[1],
                    "producto": row[2]
                })

        # Renderizar plantilla
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("plantilla_constancia_entrega.html")
        html = template.render(**pedido)
        pdf = HTML(string=html, base_url=".").write_pdf()
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", download_name=f"constancia_entrega_{pedido_id}.pdf")
    except Exception as e:
        print(f"❌ Error generando constancia de entrega: {e}")
        return str(e), 500

