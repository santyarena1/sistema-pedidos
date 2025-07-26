from flask import Blueprint, request, jsonify, render_template
from db.connection import get_db_connection
import psycopg2.extras

configuracion_bp = Blueprint("configuracion", __name__)

# --- Ruta para renderizar la página HTML de configuración ---
# Aunque usaremos un modal, esta ruta es útil tenerla por si en el futuro
# quieres mover la configuración a su propia página.
@configuracion_bp.route("/configuracion")
def vista_configuracion():
    # Asumimos que la configuración se manejará en un modal dentro de otra página,
    # pero si quisieras una página dedicada, aquí la renderizarías.
    # Por ahora, podemos redirigir o simplemente mostrar un mensaje.
    return "Página de configuración en desarrollo."

# --- API para Categorías de Venta ---

@configuracion_bp.route("/api/configuracion/categorias", methods=["GET"])
def obtener_categorias_venta():
    """
    Obtiene todas las categorías de venta junto con su margen de ganancia actual.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Usamos un LEFT JOIN para asegurarnos de obtener todas las categorías,
            # incluso si aún no tienen un margen definido.
            cur.execute("""
                SELECT c.id, c.nombre, COALESCE(m.margen_porcentaje, 0.0) as margen
                FROM categorias_venta c
                LEFT JOIN margenes_categoria m ON c.id = m.categoria_id
                ORDER BY c.nombre;
            """)
            categorias = [dict(row) for row in cur.fetchall()]
        return jsonify(categorias)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@configuracion_bp.route("/api/configuracion/categorias", methods=["POST"])
def agregar_categoria_venta():
    """
    Agrega una nueva categoría de venta a la base de datos.
    """
    data = request.get_json()
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return jsonify({"error": "El nombre no puede estar vacío"}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Intentamos insertar la nueva categoría.
            # ON CONFLICT (nombre) DO NOTHING evita errores si la categoría ya existe.
            cur.execute("INSERT INTO categorias_venta (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING RETURNING id", (nombre,))
            categoria_id_row = cur.fetchone()
            
            # Si la categoría se creó (es decir, no existía), le asignamos un margen inicial de 0.
            if categoria_id_row:
                categoria_id = categoria_id_row[0]
                cur.execute("INSERT INTO margenes_categoria (categoria_id, margen_porcentaje) VALUES (%s, 0.0)", (categoria_id,))
                mensaje = "Categoría agregada con éxito"
            else:
                mensaje = "La categoría ya existe"

            conn.commit()
        return jsonify({"mensaje": mensaje}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- API para Márgenes de Ganancia ---

@configuracion_bp.route("/api/configuracion/margenes", methods=["PUT"])
def actualizar_margenes():
    """
    Recibe una lista de categorías con sus nuevos márgenes y los actualiza en la BD.
    """
    # Espera una lista de objetos, ej: [{"id": 1, "margen": 30.5}, ...]
    lista_margenes = request.get_json()
    if not isinstance(lista_margenes, list):
        return jsonify({"error": "El formato de datos debe ser una lista"}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for item in lista_margenes:
                categoria_id = item.get("id")
                margen = item.get("margen")
                
                # Usamos un "UPSERT": si ya existe un margen para esa categoría, lo actualiza.
                # Si no existe, lo inserta.
                cur.execute("""
                    INSERT INTO margenes_categoria (categoria_id, margen_porcentaje)
                    VALUES (%s, %s)
                    ON CONFLICT (categoria_id) 
                    DO UPDATE SET margen_porcentaje = EXCLUDED.margen_porcentaje;
                """, (categoria_id, margen))
            conn.commit()
        return jsonify({"mensaje": "Márgenes actualizados con éxito"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()