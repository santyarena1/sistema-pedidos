# REEMPLAZA todas las líneas de importación al principio de: routes/stock_routes.py

import time
import os
import io # Para manejar el PDF en memoria
import json # Para el registro de movimientos
from flask import Blueprint, request, jsonify, render_template, send_file
from db.connection import get_db_connection
import psycopg2.extras

# Librerías para generar el PDF de etiquetas
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

# Librerías para generar los códigos de barras
import barcode
from barcode.writer import ImageWriter, SVGWriter # <-- CORRECCIÓN PRINCIPAL AQUÍ
import xlsxwriter
from io import BytesIO



stock_bp = Blueprint("stock", __name__)



# --- FUNCIÓN DE REGISTRO DE MOVIMIENTOS ---
def registrar_movimiento(cur, producto_nombre, accion, detalles, item_id=None):
    """Registra una acción en el historial de movimientos."""
    # Convertimos los detalles a JSON si es un dict, de lo contrario lo usamos como string
    detalles_json = json.dumps(detalles) if isinstance(detalles, dict) else detalles
    cur.execute("""
        INSERT INTO movimientos_stock (item_id, producto_nombre, accion, detalles)
        VALUES (%s, %s, %s, %s)
    """, (item_id, producto_nombre, accion, detalles_json))


# --- RUTA PRINCIPAL DE LA PÁGINA ---
@stock_bp.route("/stock")
def vista_stock():
    """Sirve la página principal de gestión de stock."""
    return render_template("stock.html")


# --- API para TIPOS de Producto (la vista general) ---

# REEMPLAZA tu función obtener_productos_stock en: routes/stock_routes.py

@stock_bp.route("/api/stock/productos", methods=["GET"])
def obtener_productos_stock():
    """
    Devuelve la lista de productos con capacidades avanzadas de
    filtrado, ordenamiento y BÚSQUEDA GENERAL.
    """
    q = request.args.get('q')
    marca = request.args.get('marca')
    categoria = request.args.get('categoria')
    deposito = request.args.get('deposito')
    disponibles = request.args.get('disponibles')
    sort_by = request.args.get('sortBy', 'nombre')
    sort_order = request.args.get('sortOrder', 'asc')

    params = []

    base_query = """
        SELECT
            p.id, p.sku, p.nombre, p.precio_venta_sugerido, p.marca, p.categoria, p.ultima_modificacion,
            COUNT(i.id) FILTER (WHERE i.estado = 'Disponible') as cantidad_disponible
        FROM stock_productos p
        LEFT JOIN stock_items i ON p.id = i.producto_id
    """

    where_clauses = []

    if q:
        search_term = f"%{q}%"
        where_clauses.append("""
            (p.sku ILIKE %s OR
             p.nombre ILIKE %s OR
             p.marca ILIKE %s OR
             p.categoria ILIKE %s OR
             p.id IN (SELECT producto_id FROM stock_items WHERE serial_number ILIKE %s))
        """)
        params.extend([search_term] * 5)

    if marca:
        where_clauses.append("p.marca = %s")
        params.append(marca)
    if categoria:
        where_clauses.append("p.categoria = %s")
        params.append(categoria)
    if deposito:
        where_clauses.append("p.id IN (SELECT producto_id FROM stock_items WHERE deposito = %s)")
        params.append(deposito)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " GROUP BY p.id"

    if disponibles == 'true':
        base_query += " HAVING COUNT(i.id) FILTER (WHERE i.estado = 'Disponible') > 0"

    allowed_sort_columns = ['sku', 'nombre', 'marca', 'categoria', 'cantidad_disponible', 'precio_venta_sugerido', 'ultima_modificacion']
    if sort_by not in allowed_sort_columns: sort_by = 'nombre'
    sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
    base_query += f" ORDER BY {sort_by} {sort_order}, p.nombre ASC"

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(base_query, tuple(params))
            productos = [dict(row) for row in cur.fetchall()]
            return jsonify(productos)
    except Exception as e:
        print(f"Error en la consulta de productos: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

def generar_sku(categoria, marca):
    """
    Genera un SKU único tomando las tres primeras letras de la categoría y las tres primeras de la marca,
    más los cuatro últimos dígitos del timestamp.
    """
    if not categoria or not marca:
        return ""
    prefijo_cat = categoria[:3].upper()
    prefijo_marca = marca[:3].upper()
    timestamp = str(int(time.time()))[-4:]
    return f"{prefijo_cat}-{prefijo_marca}-{timestamp}"



@stock_bp.route("/api/stock/productos", methods=["POST"])
def agregar_producto():
    """Agrega un nuevo TIPO de producto a la base de datos."""
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            nombre = data.get('nombre')
            marca = data.get('marca')
            categoria = data.get('categoria')
            # Generamos el SKU tomando marca y categoría
            sku = generar_sku(categoria, marca)

            cur.execute(
                """
                INSERT INTO stock_productos (sku, nombre, precio_venta_sugerido, marca, categoria)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (sku, nombre, data.get('precio_venta_sugerido'), marca, categoria)
            )
            producto_id = cur.fetchone()[0]
            registrar_movimiento(cur, nombre, "CREADO", f"Producto '{nombre}' creado con éxito. SKU: {sku}")
            conn.commit()
        return jsonify({"mensaje": "Tipo de producto creado con éxito", "id": producto_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()



@stock_bp.route("/api/stock/productos/<int:producto_id>", methods=["PATCH"])
def editar_producto(producto_id):
    """Edita los detalles de un TIPO de producto."""
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stock_productos SET sku=%s, nombre=%s, precio_venta_sugerido=%s, marca=%s, categoria=%s, ultima_modificacion=NOW()
                WHERE id=%s
                """,
                (data.get('sku'), data.get('nombre'), data.get('precio_venta_sugerido'), data.get('marca'), data.get('categoria'), producto_id)
            )
            # REGISTRAR MOVIMIENTO
            registrar_movimiento(cur, data.get('nombre'), "EDITADO", "Detalles del producto actualizados.")
            conn.commit()
        return jsonify({"mensaje": "Producto actualizado con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@stock_bp.route("/api/stock/productos/<int:producto_id>", methods=["DELETE"])
def eliminar_producto(producto_id):
    """Elimina un TIPO de producto y todos sus items asociados."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Primero obtenemos el nombre para el log
            cur.execute("SELECT nombre FROM stock_productos WHERE id = %s", (producto_id,))
            producto = cur.fetchone()
            if not producto:
                return jsonify({"error": "Producto no encontrado"}), 404
            
            # REGISTRAR MOVIMIENTO
            registrar_movimiento(cur, producto['nombre'], "ELIMINADO", f"Producto '{producto['nombre']}' y todos sus items asociados fueron eliminados.")
            
            # Luego eliminamos
            cur.execute("DELETE FROM stock_productos WHERE id = %s", (producto_id,))
            conn.commit()
        return jsonify({"mensaje": "Producto y todos sus items eliminados con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()




@stock_bp.route("/api/stock/sku/<string:sku>", methods=["GET"])
def buscar_producto_por_sku(sku):
    """Busca un tipo de producto por su SKU para el lector."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM stock_productos WHERE sku = %s", (sku,))
            producto = cur.fetchone()
        if producto:
            return jsonify(dict(producto))
        else:
            return jsonify({"error": "No se encontró ningún producto con ese SKU"}), 404
    finally:
        conn.close()


@stock_bp.route("/api/stock/historial")
def historial_stock():
    """
    [REVISADO] Devuelve el historial completo de movimientos de stock.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT fecha, accion, producto_nombre, detalles
                FROM movimientos_stock
                ORDER BY fecha DESC 
                LIMIT 500;
            """)
            movimientos = [dict(row) for row in cur.fetchall()]
        return jsonify(movimientos)
    except Exception as e:
        print(f"Error en historial_stock: {e}")
        return jsonify({"error": "Error interno al obtener el historial"}), 500
    finally:
        if conn:
            conn.close()


@stock_bp.route('/api/config/stock/<string:tipo>', methods=['GET', 'POST'])
def gestionar_config(tipo):
    """
    [MEJORADO] Gestiona (obtiene o crea) Marcas, Categorías y Depósitos.
    Ahora es más robusto contra errores y duplicados.
    """
    # 1. Creamos un diccionario para mapear lo que llega del frontend 
    #    con el nombre EXACTO de tu tabla en la base de datos.
    #    AQUÍ PUEDES CORREGIR EL NOMBRE SI TU TABLA NO SE LLAMA 'depositos'.
    nombres_de_tablas = {
        'marcas': 'marcas',
        'categorias': 'categorias',
        'depositos': 'depositos'  # <-- ¡REVISA ESTE NOMBRE! Cámbialo si tu tabla se llama 'deposito' u otra cosa.
    }

    # 2. Verificamos que el tipo que llega es válido.
    if tipo not in nombres_de_tablas:
        return jsonify({"error": "Tipo de configuración no válido"}), 400

    # 3. Obtenemos el nombre correcto de la tabla.
    nombre_tabla_real = nombres_de_tablas[tipo]

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if request.method == 'GET':
                # Usamos el nombre de tabla verificado
                cur.execute(f"SELECT id, nombre FROM {nombre_tabla_real} ORDER BY nombre")
                items = [dict(row) for row in cur.fetchall()]
                return jsonify(items)
            
            elif request.method == 'POST':
                data = request.get_json()
                if not data or 'nombre' not in data or not data['nombre'].strip():
                    return jsonify({"error": "El campo 'nombre' es obligatorio y no puede estar vacío."}), 400
                
                nombre = data['nombre'].strip()
                
                # Usamos el nombre de tabla verificado
                query = f"INSERT INTO {nombre_tabla_real} (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING RETURNING id, nombre"
                
                cur.execute(query, (nombre,))
                
                nuevo_item = cur.fetchone()
                conn.commit()
                
                if nuevo_item:
                    return jsonify(dict(nuevo_item)), 201
                else:
                    return jsonify({"mensaje": f"El elemento '{nombre}' ya existe."}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en la ruta gestionar_config para '{nombre_tabla_real}': {e}")
        return jsonify({"error": "Ocurrió un error interno en el servidor."}), 500
    finally:
        if conn:
            conn.close()



@stock_bp.route("/api/stock/items/<int:item_id>", methods=["DELETE"])
def eliminar_item(item_id):
    """
    [NUEVO] Elimina un item de stock individual.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Obtenemos los datos para el historial ANTES de borrar
            cur.execute("SELECT p.nombre as producto_nombre, i.serial_number FROM stock_items i JOIN stock_productos p ON i.producto_id = p.id WHERE i.id = %s", (item_id,))
            item_info = cur.fetchone()

            if not item_info:
                return jsonify({"error": "Item no encontrado"}), 404

            # Eliminamos el item
            cur.execute("DELETE FROM stock_items WHERE id = %s", (item_id,))

            # Registramos el movimiento
            detalles = f"Item ID {item_id} (SN: {item_info['serial_number']}) eliminado del stock."
            registrar_movimiento(cur, item_info['producto_nombre'], "ITEM ELIMINADO", detalles, item_id=item_id)

            conn.commit()
        return jsonify({"mensaje": "Item eliminado con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en eliminar_item: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# AGREGAR en: routes/stock_routes.py

# --- [NUEVA RUTA] GENERACIÓN DE PDF PARA ETIQUETAS ---
@stock_bp.route("/api/stock/productos/<int:producto_id>/etiquetas_pdf")
def generar_etiquetas_pdf(producto_id):
    """
    Genera un PDF con etiquetas de 50x25mm para cada item 'Disponible' de un producto.
    Cada etiqueta contiene el código de barras del SKU y del Número de Serie.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # 1. Obtenemos el SKU del producto
            cur.execute("SELECT sku FROM stock_productos WHERE id = %s", (producto_id,))
            producto = cur.fetchone()
            if not producto or not producto['sku']:
                return "Este producto no tiene un SKU para generar etiquetas.", 404
            sku_producto = producto['sku']

            # 2. Obtenemos solo los items DISPONIBLES para imprimir
            cur.execute("SELECT serial_number FROM stock_items WHERE producto_id = %s AND estado = 'Disponible' ORDER BY id", (producto_id,))
            items = cur.fetchall()
            if not items:
                return "No hay items 'Disponibles' de este producto para generar etiquetas.", 404

        # 3. Generamos los códigos de barras en formato SVG
        code128 = barcode.get_barcode_class('code128')
        # Opciones para que el código de barras se ajuste bien a la etiqueta
        options = {"module_height": 7.0, "font_size": 10, "text_distance": 2.0, "quiet_zone": 1.0}

        sku_barcode_svg = code128(sku_producto, writer=_Writer()).render(options)
        
        items_con_barcode = []
        for item in items:
            sn = item['serial_number']
            if sn:
                items_con_barcode.append({
                    'sn': sn,
                    'sn_barcode_svg': code128(sn, writer=_Writer()).render(options)
                })

        # 4. Renderizamos el HTML con los SVGs
        env = Environment(loader=FileSystemLoader("templates/"))
        template = env.get_template("plantilla_etiqueta_termica.html")
        html = template.render(
            sku_barcode_svg=sku_barcode_svg.decode('utf-8'),
            items=items_con_barcode
        )

        # 5. Creamos el PDF con las dimensiones correctas para la impresora térmica
        pdf_bytes = HTML(string=html).write_pdf(stylesheets=[CSS(string='@page { size: 50mm 25mm; margin: 1.5mm; }')])
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False, # Para que se vea en el navegador
            download_name=f"etiquetas_{sku_producto}.pdf"
        )
    except Exception as e:
        print(f"Error generando PDF de etiquetas: {e}")
        return str(e), 500
    finally:
        if conn: conn.close()

@stock_bp.route("/api/stock/productos/<int:producto_id>/imprimir_etiquetas", methods=["GET"])
def imprimir_etiquetas_producto(producto_id):
    """
    [VERSIÓN FINAL CON ALINEACIÓN Y ESPACIADO REFINADOS]
    Genera un PDF con etiquetas de diseño profesional.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT sku, nombre FROM stock_productos WHERE id = %s", (producto_id,))
            producto = cur.fetchone()
            if not producto:
                return "Producto no encontrado", 404
            
            sku = producto['sku']
            nombre_producto = producto['nombre']

            cur.execute("SELECT serial_number FROM stock_items WHERE producto_id = %s AND estado = 'Disponible'", (producto_id,))
            items = cur.fetchall()
            if not items:
                return "No hay items 'Disponibles' para este producto para generar etiquetas.", 404

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(50 * mm, 25 * mm))
        
        writer_options = {"write_text": False, "module_height": 6.0, "module_width": 0.2}
        
        code128_sku = barcode.get('code128', sku, writer=ImageWriter())
        sku_barcode_buffer = BytesIO()
        code128_sku.write(sku_barcode_buffer, options=writer_options)

        for item in items:
            sn = item['serial_number']
            
            code128_sn = barcode.get('code128', sn, writer=ImageWriter())
            sn_barcode_buffer = BytesIO()
            code128_sn.write(sn_barcode_buffer, options=writer_options)
            
            sku_barcode_buffer.seek(0)
            sn_barcode_buffer.seek(0)

            # --- DIBUJO DE LA ETIQUETA (CON NUEVAS COORDENADAS) ---
            
            c.roundRect(0.5 * mm, 0.5 * mm, 49 * mm, 24 * mm, radius=1.5 * mm)

            c.setFont("Helvetica-Bold", 7)
            max_width = 48 * mm
            nombre_corto = nombre_producto
            while stringWidth(nombre_corto, "Helvetica-Bold", 7) > max_width:
                nombre_corto = nombre_corto[:-1]
            c.drawCentredString(25 * mm, 21 * mm, nombre_corto)

            c.line(2 * mm, 20 * mm, 48 * mm, 20 * mm)
            
            # --- Sección SKU ---
            c.setFont("Helvetica-Bold", 6)
            c.drawString(3 * mm, 17.5 * mm, "SKU:")
            c.drawImage(ImageReader(sku_barcode_buffer), 3 * mm, 12 * mm, width=44 * mm, height=5 * mm)
            c.setFont("Helvetica", 7)
            c.drawCentredString(25 * mm, 10 * mm, sku)

            # --- Sección S/N ---
            c.setFont("Helvetica-Bold", 6)
            c.drawString(3 * mm, 7.5 * mm, "S/N:")
            c.drawImage(ImageReader(sn_barcode_buffer), 3 * mm, 2.5 * mm, width=44 * mm, height=5 * mm)
            c.setFont("Helvetica", 7)
            c.drawCentredString(25 * mm, 1 * mm, sn)
            
            c.showPage()

        c.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=False,
            download_name=f'etiquetas_{nombre_producto.replace(" ", "_")}.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ocurrió un error crítico al generar el PDF: {e}", 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/items/<int:item_id>/imprimir_etiqueta", methods=["GET"])
def imprimir_etiqueta_individual(item_id):
    """
    [NUEVO] Genera un PDF con una sola etiqueta para un item (SN) específico.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # 1. Obtenemos toda la info necesaria con un JOIN
            cur.execute("""
                SELECT 
                    i.serial_number,
                    p.sku,
                    p.nombre
                FROM stock_items i
                JOIN stock_productos p ON i.producto_id = p.id
                WHERE i.id = %s
            """, (item_id,))
            
            item_data = cur.fetchone()
            if not item_data:
                return "Item no encontrado", 404
            
            sku = item_data['sku']
            nombre_producto = item_data['nombre']
            sn = item_data['serial_number']

        # 2. La lógica de generación de PDF es casi idéntica a la anterior,
        #    pero sin el bucle 'for', ya que es una sola etiqueta.
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(50 * mm, 25 * mm))
        writer_options = {"write_text": False, "module_height": 7.0, "module_width": 0.2}

        # Generar código de barras para SKU
        code128_sku = barcode.get('code128', sku, writer=ImageWriter())
        sku_barcode_buffer = BytesIO()
        code128_sku.write(sku_barcode_buffer, options=writer_options)

        # Generar código de barras para SN
        code128_sn = barcode.get('code128', sn, writer=ImageWriter())
        sn_barcode_buffer = BytesIO()
        code128_sn.write(sn_barcode_buffer, options=writer_options)

        # Volvemos al inicio de los buffers de imagen
        sku_barcode_buffer.seek(0)
        sn_barcode_buffer.seek(0)

        # --- DIBUJO DE LA ETIQUETA ---
        c.roundRect(0.5 * mm, 0.5 * mm, 49 * mm, 24 * mm, radius=1.5 * mm)
        c.setFont("Helvetica-Bold", 7)
        max_width = 48 * mm
        nombre_corto = nombre_producto
        while stringWidth(nombre_corto, "Helvetica-Bold", 7) > max_width:
            nombre_corto = nombre_corto[:-1]
        c.drawCentredString(25 * mm, 21 * mm, nombre_corto)
        c.line(2 * mm, 20 * mm, 48 * mm, 20 * mm)
        
        c.setFont("Helvetica-Bold", 6)
        c.drawString(3 * mm, 17.5 * mm, "SKU:")
        c.drawImage(ImageReader(sku_barcode_buffer), 3 * mm, 12 * mm, width=44 * mm, height=5 * mm)
        c.setFont("Helvetica", 7)
        c.drawCentredString(25 * mm, 10 * mm, sku)

        c.setFont("Helvetica-Bold", 6)
        c.drawString(3 * mm, 7.5 * mm, "S/N:")
        c.drawImage(ImageReader(sn_barcode_buffer), 3 * mm, 2.5 * mm, width=44 * mm, height=5 * mm)
        c.setFont("Helvetica", 7)
        c.drawCentredString(25 * mm, 1 * mm, sn)
        
        c.showPage()
        c.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=False,
            download_name=f'etiqueta_{sn}.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Ocurrió un error crítico al generar el PDF: {e}", 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/marcas", methods=["GET"])
def get_marcas():
    """Obtiene una lista de todas las marcas únicas para los filtros."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT marca FROM stock_productos WHERE marca IS NOT NULL AND marca <> '' ORDER BY marca")
            marcas = [row[0] for row in cur.fetchall()]
            return jsonify(marcas)
    finally:
        if conn: conn.close()

@stock_bp.route("/api/stock/categorias", methods=["GET"])
def get_categorias():
    """Obtiene una lista de todas las categorías únicas para los filtros."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT categoria FROM stock_productos WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria")
            categorias = [row[0] for row in cur.fetchall()]
            return jsonify(categorias)
    finally:
        if conn: conn.close()

@stock_bp.route("/api/stock/depositos", methods=["GET"])
def get_depositos():
    """Obtiene una lista de todos los depósitos para los filtros."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Tu archivo stock.js usa `poblarSelect('...','depositos',...)`, el nombre de la tabla es 'depositos'
            cur.execute("SELECT nombre FROM depositos ORDER BY nombre")
            depositos = [row[0] for row in cur.fetchall()]
            return jsonify(depositos)
    finally:
        if conn: conn.close()



@stock_bp.route("/api/stock/items", methods=["POST"])
def agregar_items():
    """
    Agrega uno o más items físicos (SNs) a un producto existente.
    """
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            producto_id = data.get('producto_id')
            serial_numbers = data.get('serial_numbers', [])

            # Buscamos el nombre del producto para registrarlo en el historial
            cur.execute("SELECT nombre FROM stock_productos WHERE id = %s", (producto_id,))
            producto_nombre_row = cur.fetchone()
            producto_nombre = producto_nombre_row['nombre'] if producto_nombre_row else "Producto Desconocido"

            items_a_insertar = []
            for sn in serial_numbers:
                if sn: # Nos aseguramos de no insertar strings vacíos
                    items_a_insertar.append((
                        producto_id,
                        sn,
                        data.get('costo'),
                        data.get('deposito')
                    ))

            if not items_a_insertar:
                return jsonify({"error": "No se proporcionaron números de serie válidos."}), 400

            psycopg2.extras.execute_batch(
                cur,
                "INSERT INTO stock_items (producto_id, serial_number, costo, deposito) VALUES (%s, %s, %s, %s)",
                items_a_insertar
            )
            # Después de insertar los ítems y actualizar la fecha de modificación:
            
            registrar_movimiento(
                cur,
                producto_nombre,
                "INGRESO",
                f"{len(items_a_insertar)} items agregados.",
            )
            conn.commit()


            # Actualizamos la fecha de última modificación del producto "padre"
            cur.execute("UPDATE stock_productos SET ultima_modificacion = NOW() WHERE id = %s", (producto_id,))

            conn.commit()

        return jsonify({"mensaje": f"{len(items_a_insertar)} items agregados con éxito"}), 201
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en agregar_items: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@stock_bp.route("/api/stock/items/<int:item_id>", methods=["PATCH"])
def editar_item(item_id):
    """
    Edita los detalles de un item de stock individual (estado y/o depósito).
    """
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("UPDATE stock_items SET estado = %s, deposito = %s, ultima_modificacion = NOW() WHERE id = %s",
                (data.get('estado'), data.get('deposito'), item_id)
            )
            conn.commit()
        return jsonify({"mensaje": "Item actualizado con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en editar_item: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@stock_bp.route("/api/stock/items/salida", methods=["POST"])
def registrar_salida_items():
    """
    Registra la salida (egreso) de uno o varios items mediante sus números de serie.
    Cambia el estado a 'Vendido' y crea un registro en movimientos_stock.
    """
    data = request.get_json() or {}
    serial_numbers = data.get("serial_numbers", [])
    motivo = data.get("motivo", "VENTA")  # Permite personalizar el motivo

    if not serial_numbers:
        return jsonify({"error": "No se proporcionaron números de serie."}), 400

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            procesados = 0
            for sn in serial_numbers:
                # Buscamos el item disponible por su serial_number
                cur.execute(
                    """
                    SELECT i.id, i.producto_id, p.nombre
                    FROM stock_items i
                    JOIN stock_productos p ON i.producto_id = p.id
                    WHERE i.serial_number = %s AND i.estado = 'Disponible'
                    """,
                    (sn,),
                )
                item = cur.fetchone()
                if not item:
                    continue  # Serial no encontrado o no disponible

                # Actualizamos el estado a Vendido (o el que necesites)
                cur.execute(
                    "UPDATE stock_items SET estado = 'Vendido', ultima_modificacion = NOW() WHERE id = %s",
                    (item["id"],),
                )

                # Registramos el movimiento en el historial
                detalles = f"Item SN {sn} egresado. Motivo: {motivo}"
                registrar_movimiento(
                    cur,
                    item["nombre"],
                    "EGRESO",
                    detalles,
                    item_id=item["id"],
                )
                procesados += 1

            conn.commit()
        return jsonify({"mensaje": "Salida registrada", "items": procesados}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/export", methods=["GET"])
def exportar_stock():
    """
    Exporta la lista de productos y su stock disponible. Si xlsxwriter está
    disponible se genera un archivo Excel (.xlsx); de lo contrario, se devuelve
    un archivo CSV que puede abrirse en Excel.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT
                    p.sku, p.nombre, p.marca, p.categoria,
                    COUNT(i.id) FILTER (WHERE i.estado = 'Disponible') AS cantidad_disponible,
                    p.precio_venta_sugerido
                FROM stock_productos p
                LEFT JOIN stock_items i ON p.id = i.producto_id
                GROUP BY p.id
                ORDER BY p.nombre
            """)
            rows = cur.fetchall()

        headers = ["SKU", "Nombre", "Marca", "Categoría", "Cantidad Disponible", "Precio Sugerido"]

        # Si xlsxwriter está instalado, generamos un Excel; de lo contrario, usamos CSV.
        if xlsxwriter:
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {"in_memory": True})
            worksheet = workbook.add_worksheet("Stock")
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
            for row_idx, row in enumerate(rows, start=1):
                worksheet.write_row(row_idx, 0, [
                    row["sku"],
                    row["nombre"],
                    row["marca"],
                    row["categoria"],
                    row["cantidad_disponible"],
                    row["precio_venta_sugerido"],
                ])
            workbook.close()
            output.seek(0)
            return send_file(output, download_name="stock.xlsx", as_attachment=True)
        else:
            # Fallback CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([
                    row["sku"],
                    row["nombre"],
                    row["marca"],
                    row["categoria"],
                    row["cantidad_disponible"],
                    row["precio_venta_sugerido"],
                ])
            output.seek(0)
            return send_file(
                BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/csv",
                download_name="stock.csv",
                as_attachment=True,
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/historial/export", methods=["GET"])
def exportar_historial():
    """
    Exporta el historial de movimientos de stock. Si xlsxwriter está disponible
    genera un .xlsx; si no, devuelve un .csv.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT fecha, accion, producto_nombre, detalles
                FROM movimientos_stock
                ORDER BY fecha DESC
            """)
            rows = cur.fetchall()

        headers = ["Fecha", "Acción", "Producto", "Detalles"]

        if xlsxwriter:
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {"in_memory": True})
            sheet = workbook.add_worksheet("Historial")
            for col, header in enumerate(headers):
                sheet.write(0, col, header)
            for idx, row in enumerate(rows, start=1):
                sheet.write_row(idx, 0, [
                    row["fecha"].strftime("%Y-%m-%d %H:%M:%S"),
                    row["accion"],
                    row["producto_nombre"],
                    row["detalles"],
                ])
            workbook.close()
            output.seek(0)
            return send_file(output, download_name="historial_stock.xlsx", as_attachment=True)
        else:
            # Fallback CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([
                    row["fecha"].strftime("%Y-%m-%d %H:%M:%S"),
                    row["accion"],
                    row["producto_nombre"],
                    row["detalles"],
                ])
            output.seek(0)
            return send_file(
                BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/csv",
                download_name="historial_stock.csv",
                as_attachment=True,
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/import", methods=["POST"])
def importar_stock():
    """
    Importa productos e ítems desde un archivo Excel (.xlsx/.xls) o CSV (.csv).
    Para archivos Excel se requiere pandas instalado; de lo contrario, utilice un CSV.
    """
    archivo = request.files.get("file")
    if not archivo or not archivo.filename:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    filename = archivo.filename.lower()
    # Leemos los datos en una lista de dicts (csv) o un DataFrame (Excel)
    try:
        if filename.endswith((".xlsx", ".xls")):
            if pd is None:
                return jsonify({"error": "Para importar archivos Excel necesitas instalar la librería pandas o convertir el archivo a CSV."}), 400
            df = pd.read_excel(archivo)
        else:
            # CSV: usamos el módulo csv del estándar
            archivo.seek(0)
            contenido = archivo.stream.read().decode("utf-8")
            reader = csv.DictReader(StringIO(contenido))
            df = list(reader)
    except Exception as e:
        return jsonify({"error": f"Archivo inválido: {e}"}), 400

    conn = get_db_connection()
    creados = 0
    actualizados = 0
    errores = 0

    try:
        with conn.cursor() as cur:
            # Iteramos según sea DataFrame o lista de dicts
            registros = df.iterrows() if pd and not isinstance(df, list) else enumerate(df)
            for _, fila in registros:
                # fila puede ser una Series (pandas) o un dict (csv)
                if pd and not isinstance(df, list):
                    fila_dict = fila.to_dict()
                else:
                    fila_dict = fila

                sku = str(fila_dict.get("sku") or "").strip()
                nombre = str(fila_dict.get("nombre") or "").strip()
                if not sku or not nombre:
                    errores += 1
                    continue

                # Verificamos si el producto existe
                cur.execute("SELECT id FROM stock_productos WHERE sku = %s", (sku,))
                prod = cur.fetchone()
                if not prod:
                    # Crear producto
                    cur.execute(
                        """
                        INSERT INTO stock_productos (sku, nombre, precio_venta_sugerido, marca, categoria)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                        """,
                        (
                            sku,
                            nombre,
                            fila_dict.get("precio_venta_sugerido"),
                            fila_dict.get("marca"),
                            fila_dict.get("categoria"),
                        ),
                    )
                    producto_id = cur.fetchone()[0]
                    created = True
                    creados += 1
                else:
                    producto_id = prod[0]
                    created = False
                    actualizados += 1

                # Si viene número de serie, insertamos un item
                serial_number = str(fila_dict.get("serial_number") or "").strip()
                if serial_number:
                    cur.execute(
                        """
                        INSERT INTO stock_items (producto_id, serial_number, costo, deposito)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            producto_id,
                            serial_number,
                            fila_dict.get("costo"),
                            fila_dict.get("deposito"),
                        ),
                    )

                accion = "CREADO" if created else "ACTUALIZADO"
                registrar_movimiento(
                    cur,
                    nombre,
                    accion,
                    f"Importación desde archivo. SKU: {sku}",
                )

            conn.commit()
        return jsonify({"mensaje": f"Productos creados: {creados}, actualizados: {actualizados}, errores: {errores}"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@stock_bp.route("/api/stock/productos/<int:producto_id>/items", methods=["GET"])
def obtener_items_producto(producto_id):
    """
    Devuelve los items individuales de un producto, con datos relevantes.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, serial_number, estado, costo, deposito, ultima_modificacion
                FROM stock_items
                WHERE producto_id = %s
                ORDER BY id
            """, (producto_id,))
            items = [dict(row) for row in cur.fetchall()]
        return jsonify(items)
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@stock_bp.route("/api/stock/items/sn/<string:serial_number>", methods=["GET"])
def buscar_item_por_sn(serial_number):
    """
    Devuelve información básica del item (producto, estado) a partir de su número de serie.
    Sólo devuelve items en estado 'Disponible'.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT i.id, i.serial_number, p.nombre AS producto, i.estado
                FROM stock_items i
                JOIN stock_productos p ON i.producto_id = p.id
                WHERE i.serial_number = %s
            """, (serial_number,))
            item = cur.fetchone()
        if not item:
            return jsonify({"error": "No existe un item con ese número de serie."}), 404
        if item['estado'] != 'Disponible':
            return jsonify({"error": "El item no está disponible (estado actual: %s)." % item['estado']}), 400
        return jsonify(dict(item))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

