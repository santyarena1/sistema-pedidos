from flask import Blueprint, request, jsonify, render_template
from db.connection import get_db_connection
import psycopg2.extras
import json # Importamos json para registrar detalles en el historial

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
    """Devuelve la lista de todos los TIPOS de producto y su cantidad disponible."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT
                    p.id, p.sku, p.nombre, p.precio_venta_sugerido, p.marca, p.categoria, p.ultima_modificacion,
                    COUNT(i.id) FILTER (WHERE i.estado = 'Disponible') as cantidad_disponible
                FROM stock_productos p
                LEFT JOIN stock_items i ON p.id = i.producto_id
                GROUP BY p.id
                ORDER BY p.nombre;
            """)
            productos = [dict(row) for row in cur.fetchall()]
        return jsonify(productos)
    finally:
        conn.close()

@stock_bp.route("/api/stock/productos", methods=["POST"])
def agregar_producto():
    """Agrega un nuevo TIPO de producto a la base de datos."""
    data = request.get_json()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stock_productos (sku, nombre, precio_venta_sugerido, marca, categoria) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (data.get('sku'), data.get('nombre'), data.get('precio_venta_sugerido'), data.get('marca'), data.get('categoria'))
            )
            producto_id = cur.fetchone()[0]
            # REGISTRAR MOVIMIENTO
            registrar_movimiento(cur, data.get('nombre'), "CREADO", f"Producto '{data.get('nombre')}' creado con éxito.")
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

