import time
import os
from flask import Blueprint, request, jsonify, render_template, send_file
from db.connection import get_db_connection
import psycopg2.extras
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth  # <-- ¡ESTA ES LA IMPORTACIÓN QUE FALTABA!
import barcode
from barcode.writer import ImageWriter

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

@stock_bp.route("/api/stock/productos", methods=["GET"])
def obtener_productos_stock():
    """
    [MODIFICADO] Devuelve la lista de productos con capacidades avanzadas de 
    filtrado, ordenamiento y BÚSQUEDA GENERAL.
    """
    # Recoger parámetros de la URL
    q = request.args.get('q')  # <-- Parámetro para la búsqueda general
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
    
    # --- Lógica de Búsqueda General ---
    if q:
        search_term = f"%{q}%"
        # Buscamos en los campos del producto O si existe un item con ese SN
        where_clauses.append("""
            (p.sku ILIKE %s OR 
             p.nombre ILIKE %s OR 
             p.marca ILIKE %s OR 
             p.categoria ILIKE %s OR
             p.id IN (SELECT producto_id FROM stock_items WHERE serial_number ILIKE %s))
        """)
        params.extend([search_term] * 5) # Añadimos el término 5 veces, una por cada '?'
    
    # --- Lógica de Filtros Específicos ---
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

    # Lógica de ordenamiento
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

# REEMPLAZAR en: routes/stock_routes.py
def generar_sku(nombre, categoria):
    """Genera un SKU único a partir del nombre y la categoría del producto."""
    if not nombre or not categoria:
        return ""
    # Tomamos las 3 primeras letras de la categoría y las 3 primeras del nombre
    prefijo_cat = categoria[:3].upper()
    prefijo_prod = nombre[:3].upper()
    # Usamos los últimos 4 dígitos del timestamp para asegurar que sea único
    timestamp = str(int(time.time()))[-4:]
    return f"{prefijo_cat}-{prefijo_prod}-{timestamp}"

@stock_bp.route("/api/stock/productos", methods=["POST"])
def agregar_producto():
    """Agrega un nuevo TIPO de producto a la base de datos."""
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Generamos el SKU automáticamente ignorando lo que venga del front
            nombre = data.get('nombre')
            categoria = data.get('categoria')
            sku = generar_sku(nombre, categoria)

            cur.execute(
                """
                INSERT INTO stock_productos (sku, nombre, precio_venta_sugerido, marca, categoria)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (sku, nombre, data.get('precio_venta_sugerido'), data.get('marca'), categoria)
            )
            producto_id = cur.fetchone()[0]
            registrar_movimiento(cur, data.get('nombre'), "CREADO", f"Producto '{data.get('nombre')}' creado con éxito. SKU: {sku}")
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





# --- API para ITEMS Individuales (con Número de Serie) ---

@stock_bp.route("/api/stock/productos/<int:producto_id>/items", methods=["GET"])
def obtener_items_de_producto(producto_id):
    """
    Devuelve todos los items individuales (con sus SNs) de un producto específico.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, serial_number, estado, costo, deposito, ultima_modificacion 
                FROM stock_items 
                WHERE producto_id = %s 
                ORDER BY id ASC
            """, (producto_id,))
            items = [dict(row) for row in cur.fetchall()]
        return jsonify(items)
    except Exception as e:
        print(f"Error en obtener_items_de_producto: {e}")
        return jsonify({"error": "Error interno del servidor al obtener items"}), 500
    finally:
        if conn:
            conn.close()


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
            
            # Actualizamos la fecha de última modificación del producto "padre"
            cur.execute("UPDATE stock_productos SET ultima_modificacion = NOW() WHERE id = %s", (producto_id,))
            
            # Aquí podrías volver a agregar la llamada al historial si la tienes definida
            # registrar_movimiento(cur, producto_nombre, "INGRESO", f"{len(items_a_insertar)} items agregados.")
            
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
    [MEJORADO] Edita los detalles de un item de stock individual (estado y/o depósito).
    """
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Obtenemos los datos actuales para el historial
            cur.execute("SELECT p.nombre as producto_nombre FROM stock_items i JOIN stock_productos p ON i.producto_id = p.id WHERE i.id = %s", (item_id,))
            item_info = cur.fetchone()

            if not item_info:
                return jsonify({"error": "Item no encontrado"}), 404

            # Actualizamos el item con los nuevos datos
            # Nota: El costo ya no se actualiza desde aquí.
            cur.execute(
                "UPDATE stock_items SET estado = %s, deposito = %s, ultima_modificacion = NOW() WHERE id = %s",
                (data.get('estado'), data.get('deposito'), item_id)
            )

            # Registramos el movimiento en el historial
            detalles = f"Item ID {item_id} actualizado. Nuevo estado: {data.get('estado')}, Nuevo depósito: {data.get('deposito')}."
            registrar_movimiento(cur, item_info['producto_nombre'], "ITEM EDITADO", detalles, item_id=item_id)

            conn.commit()
        return jsonify({"mensaje": "Item actualizado con éxito"}), 200
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en editar_item: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


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

        sku_barcode_svg = code128(sku_producto, writer=SVGWriter()).render(options)
        
        items_con_barcode = []
        for item in items:
            sn = item['serial_number']
            if sn:
                items_con_barcode.append({
                    'sn': sn,
                    'sn_barcode_svg': code128(sn, writer=SVGWriter()).render(options)
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