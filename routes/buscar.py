from flask import Blueprint, request, jsonify, render_template
import psycopg2.extras
from threading import Thread
import re
import datetime
import json
import time
from datetime import timedelta




# --- IMPORTACIONES ---
# Usamos PreciosGamer como fuente principal para minoristas.
# Tus scrapers de mayoristas como newbytes, invid, etc., se ejecutan por separado
# con el planificador APScheduler, por lo que no se importan aquí.
from services.preciosgamer_scraper import buscar_en_preciosgamer
from db.connection import get_db_connection

buscar_bp = Blueprint("buscar", __name__)
# Registrar la última vez que se intentó actualizar sin resultados
ULTIMOS_SIN_RESULTADO = {}


# Lock para evitar búsquedas duplicadas
ACTUALIZACIONES_EN_CURSO = set()

def reemplazar_resultados_de_sitio(sitio: str, items: list):
    """
    Reemplaza todos los productos de un sitio por una nueva lista.
    Registra una auditoría con la cantidad de productos insertados, los errores y la duración.
    """
    if not sitio:
        return
    inicio = time.time()
    errores = []
    inserted = 0

    # Aseguramos que todos los ítems tengan las claves opcionales requeridas por la tabla
    for it in (items or []):
        # Campos opcionales que podrían faltar según el scraper
        it.setdefault('imagen', '')
        it.setdefault('marca', 'Sin Marca')
        it.setdefault('precio_anterior', 0)
        it.setdefault('porcentaje_descuento', 0)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Eliminamos productos del sitio
            cur.execute("DELETE FROM productos WHERE sitio = %s", (sitio,))
            # Insertamos los nuevos
            if items:
                psycopg2.extras.execute_batch(cur, """
                    INSERT INTO productos (
                        busqueda, sitio, producto, precio, link, imagen,
                        marca, precio_anterior, porcentaje_descuento, actualizado
                    ) VALUES (
                        %(busqueda)s, %(sitio)s, %(producto)s, %(precio)s, %(link)s, %(imagen)s,
                        %(marca)s, %(precio_anterior)s, %(porcentaje_descuento)s, NOW()
                    )
                """, items)
                inserted = len(items)
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        errores.append(str(e))
    finally:
        if conn:
            conn.close()

    # Guardamos la auditoría con las métricas recolectadas
    duracion_ms = int((time.time() - inicio) * 1000)
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO auditoria_mayoristas (
                    sitio, ultima_actualizacion, cantidad_productos,
                    cantidad_errores, detalle_errores, duracion_ms
                ) VALUES (%s, NOW(), %s, %s, %s, %s)
            """, (
                sitio,
                inserted,
                len(errores),
                json.dumps(errores) if errores else None,
                duracion_ms
            ))
            conn.commit()
    except Exception as e:
        print(f"-> ERROR guardando auditoría de {sitio}: {e}")
    finally:
        if conn:
            conn.close()


# Endpoint stub para IA (fase 2)
@buscar_bp.route("/ia/categoria-sugerida", methods=["POST"])
def categoria_sugerida():
    """
    Stub que, dado un título de producto, devuelve una categoría sugerida con score.
    Esta implementación no usa un modelo real y devuelve siempre None.
    """
    data = request.get_json() or {}
    titulo = data.get('titulo_producto') or ''
    # TODO: integrar modelo real en una fase posterior
    return jsonify({"titulo": titulo, "categoria": None, "score": 0.0})


# --- FUNCIÓN DE GUARDADO (SIN CAMBIOS) ---
def guardar_resultados_db(lista_de_resultados):
    if not lista_de_resultados:
        return
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Determinamos si es una actualización de mayoristas o una búsqueda de minoristas
            busqueda_termino = lista_de_resultados[0]['busqueda']
            if busqueda_termino == "LISTA_COMPLETA":
                # Si es una lista completa, borramos todos los productos de ese sitio
                sitio = lista_de_resultados[0]['sitio']
                print(f"-> Limpiando lista completa para el mayorista: '{sitio}'")
                cur.execute("DELETE FROM productos WHERE sitio = %s", (sitio,))
            else:
                # Si es una búsqueda normal, borramos solo los resultados de esa búsqueda
                print(f"-> Limpiando resultados antiguos para la búsqueda: '{busqueda_termino}'")
                cur.execute("DELETE FROM productos WHERE busqueda = %s", (busqueda_termino,))

            psycopg2.extras.execute_batch(cur, """
                INSERT INTO productos (
                    busqueda, sitio, producto, precio, link, imagen, 
                    marca, precio_anterior, porcentaje_descuento, actualizado
                ) VALUES (
                    %(busqueda)s, %(sitio)s, %(producto)s, %(precio)s, %(link)s, %(imagen)s,
                    %(marca)s, %(precio_anterior)s, %(porcentaje_descuento)s, NOW()
                )
            """, lista_de_resultados)
            conn.commit()
            print(f"-> ¡Éxito! {len(lista_de_resultados)} productos guardados/actualizados en la BD.")
    except Exception as e:
        print(f"-> ERROR GRAVE al guardar en la base de datos: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

# --- BÚSQUEDA EN SEGUNDO PLANO (PARA MINORISTAS Y MASIVA) ---
def ejecutar_busqueda_en_segundo_plano(producto):
    def correr_busqueda_unica():
        try:
            # Lista de tiendas permitidas (sin TheGamerShop porque se incluye siempre)
            tiendas_permitidas = {
                "Acuario Insumos", "Compra Gamer", "Compugarden", "Full H4rd",
                "Gaming City", "Integrados Argentinos", "Maximus", "Megasoft",
                "Mexx", "Scp Hardstore"
            }
            def normalizar_nombre(nombre):
                return re.sub(r'[\s\W_]+', '', nombre).lower()
            tiendas_permitidas_norm = {normalizar_nombre(t) for t in tiendas_permitidas}

            # Ejecutamos ambos scrapers
            resultados_pg = buscar_en_preciosgamer(producto) or []
            

            resultados_comb = []

            # Filtramos resultados de PreciosGamer por tiendas permitidas
            for res in resultados_pg:
                nombre_tienda_norm = normalizar_nombre(res.get('sitio', ''))
                if nombre_tienda_norm in tiendas_permitidas_norm:
                    res.setdefault('imagen', '')
                    res.setdefault('marca', 'Sin Marca')
                    res.setdefault('precio_anterior', 0)
                    res.setdefault('porcentaje_descuento', 0)
                    resultados_comb.append(res)

            # Agregamos todos los resultados de TheGamerShop (siempre se permiten)
            

            
            print(f"-> Después de filtrar, quedan {len(resultados_comb)} resultados combinados.")

            if resultados_comb:
                guardar_resultados_db(resultados_comb)

            print(f"-> Actualización en 2do plano para '{producto}' finalizada.")
        finally:
            if producto in ACTUALIZACIONES_EN_CURSO:
                ACTUALIZACIONES_EN_CURSO.remove(producto)
                print(f"-> Lock liberado para '{producto}'.")

    thread = Thread(target=correr_busqueda_unica)
    thread.start()





@buscar_bp.route("/comparar", methods=["GET"])
def comparar_productos():
    """
    Permite buscar un producto en tres modos:
      - 'minorista': retorna los resultados de productos busqueda=producto; si no hay datos frescos, ejecuta scraping y devuelve estado 'actualizando'.
      - 'mayorista': retorna solo mayoristas (Invid, NewBytes, AIR, POLYTECH y TheGamerShop) por coincidencia parcial.
      - 'masiva': combina ambos conjuntos, y si no hay minoristas, ejecuta scraping y devuelve estado 'actualizando'.
    """
    producto = request.args.get("producto", "").lower().strip()
    tipo = request.args.get("tipo", "minorista").lower()

    if not producto:
        return jsonify({"error": "Falta el parámetro 'producto'"}), 400

    # Evitamos lanzar múltiples scrapers para el mismo término (solo minorista/masiva)
    if tipo in ["minorista", "masiva"] and producto in ACTUALIZACIONES_EN_CURSO:
        return jsonify({
            "estado": "actualizando",
            "mensaje": "Ya hay una actualización en curso para este producto."
        })

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            intervalo_minorista = "NOW() - INTERVAL '11 hours'"

            # -------- Búsqueda en mayoristas --------
            if tipo == "mayorista":
                sitios = ('NewBytes', 'Invid', 'AIR', 'POLYTECH', )
                cur.execute("""
                    SELECT * FROM productos
                    WHERE sitio IN %s AND LOWER(producto) ILIKE %s
                    ORDER BY precio ASC
                    LIMIT 200
                """, (sitios, f"%{producto}%"))
                resultados_actuales = [dict(row) for row in cur.fetchall()]

            # -------- Búsqueda masiva --------
            elif tipo == "masiva":
                sitios_mayoristas = ('NewBytes', 'Invid', 'AIR', 'POLYTECH', )
                cur.execute(f"""
                    SELECT * FROM productos
                    WHERE (busqueda = %s AND actualizado > {intervalo_minorista})
                       OR (sitio IN %s AND LOWER(producto) ILIKE %s)
                    ORDER BY precio ASC
                """, (producto, sitios_mayoristas, f"%{producto}%"))
                resultados_actuales = [dict(row) for row in cur.fetchall()]

                # Contamos si hay minoristas frescos
                cur.execute(f"""
                    SELECT COUNT(*) FROM productos
                    WHERE busqueda = %s AND actualizado > {intervalo_minorista}
                """, (producto,))
                minorista_count = cur.fetchone()[0]

                if minorista_count == 0:
                    ahora = datetime.datetime.utcnow()
                    ultimo_intento = ULTIMOS_SIN_RESULTADO.get(producto)
                    # solo intentamos si ha pasado más de 1 hora desde el último intento fallido
                    if not ultimo_intento or (ahora - ultimo_intento).total_seconds() >= 3600:
                        ULTIMOS_SIN_RESULTADO[producto] = ahora
                        ACTUALIZACIONES_EN_CURSO.add(producto)
                        ejecutar_busqueda_en_segundo_plano(producto)

                    # Formateamos precios de mayoristas antes de responder
                    for r in resultados_actuales:
                        if r.get('precio') is not None:
                            valor = float(r['precio'])
                            r['precio'] = f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                    return jsonify({
                        "estado": "actualizando",
                        "mensaje": "Buscando minoristas por primera vez...",
                        "resultados": resultados_actuales
                    })

            # -------- Búsqueda minorista --------
            else:  # tipo == "minorista"
                cur.execute(f"""
                    SELECT * FROM productos
                    WHERE busqueda = %s AND actualizado > {intervalo_minorista}
                    ORDER BY precio ASC
                """, (producto,))
                resultados_actuales = [dict(row) for row in cur.fetchall()]

                if not resultados_actuales:
                    ahora = datetime.datetime.utcnow()
                    ultimo_intento = ULTIMOS_SIN_RESULTADO.get(producto)
                    # evitamos repetir la búsqueda si ya se intentó hace menos de 1 hora
                    if ultimo_intento and (ahora - ultimo_intento).total_seconds() < 3600:
                        return jsonify([])

                    ULTIMOS_SIN_RESULTADO[producto] = ahora
                    ACTUALIZACIONES_EN_CURSO.add(producto)
                    ejecutar_busqueda_en_segundo_plano(producto)
                    return jsonify({
                        "estado": "actualizando",
                        "mensaje": "Buscando este producto por primera vez..."
                    })

            # Formateo final de precios para cualquier tipo de búsqueda con datos listos
            for r in resultados_actuales:
                if r.get('precio') is not None:
                    valor = float(r['precio'])
                    r['precio'] = f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            return jsonify(resultados_actuales)

    except Exception as e:
        print(f"-> Error en /comparar: {e}")
        return jsonify({"error": "Error interno en el servidor."}), 500
    finally:
        if conn: conn.close()




# --- El resto de tus rutas se mantienen igual ---
@buscar_bp.route("/buscar")
def mostrar_comparador():
    return render_template("buscador_rediseñado.html")

@buscar_bp.route("/api/tiendas", methods=["GET"])
def obtener_tiendas():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT sitio FROM productos ORDER BY sitio")
            tiendas = [row[0] for row in cur.fetchall()]
        return jsonify(tiendas)
    except Exception as e:
        print(f"Error al obtener tiendas: {e}")
        return jsonify([]), 500
    finally:
        if conn: conn.close()

# Al inicio de routes/buscar.py (tras otras importaciones) añade:
import psycopg2.extras

@buscar_bp.route('/api/mayoristas/estado', methods=['GET'])
def estado_mayoristas():
    """
    Devuelve el último estado de cada mayorista con la hora ajustada a UTC-3 (Buenos Aires).
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (sitio) sitio, ultima_actualizacion, cantidad_productos, cantidad_errores
                FROM auditoria_mayoristas
                ORDER BY sitio, ultima_actualizacion DESC
            """)
            resultados = []
            for row in cur.fetchall():
                # Ajustamos la hora (UTC -3) suponiendo que la base guarda UTC
                ts = row['ultima_actualizacion']
                if ts:
                    ts_local = ts - timedelta(hours=3)
                    row = dict(row)
                    row['ultima_actualizacion'] = ts_local.isoformat()
                resultados.append(dict(row))
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@buscar_bp.route('/api/mayoristas/<sitio>/actualizar', methods=['POST'])
def actualizar_mayorista(sitio):
    """
    Fuerza la actualización de un solo mayorista.
    Ejecuta el scraper correspondiente y reemplaza sus registros en la base de datos.
    """
    nombre = sitio.strip()
    try:
        # Importamos aquí para evitar ciclos y acelerar arranque
        from services.newbytes import obtener_lista_completa_newbytes
        from services.buscar_invid import obtener_lista_completa_invid
        from services.air_intra import obtener_lista_completa_air
        from services.polytech import obtener_lista_completa_polytech


        mapping = {
            'Invid': obtener_lista_completa_invid,
            'Newbytes': obtener_lista_completa_newbytes,
            'AIR': obtener_lista_completa_air,
            'POLYTECH': obtener_lista_completa_polytech,
          
        }
        if nombre not in mapping:
            return jsonify({"error": "Sitio no reconocido"}), 400

        lista = mapping[nombre]() or []
        # Aseguramos campos opcionales
        for it in lista:
            it.setdefault('imagen', '')
            it.setdefault('marca', 'Sin Marca')
            it.setdefault('precio_anterior', 0)
            it.setdefault('porcentaje_descuento', 0)

        reemplazar_resultados_de_sitio(nombre, lista)
        return jsonify({
            "mensaje": f"{nombre} actualizado con éxito",
            "cantidad_productos": len(lista)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@buscar_bp.route('/api/mayoristas/<sitio>/productos', methods=['GET'])
def productos_mayorista(sitio):
    """
    Devuelve una lista de productos de un mayorista específico para visualización en el modal.
    Se limita a los 500 más recientes (ordenados por fecha de actualización).
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT producto, precio, actualizado
                FROM productos
                WHERE sitio = %s
                ORDER BY actualizado DESC
                LIMIT 500
            """, (sitio,))
            productos = []
            for row in cur.fetchall():
                # Ajuste horario para la columna actualizado
                ts = row['actualizado']
                if ts:
                    ts_local = ts - timedelta(hours=3)
                    actualizado = ts_local.isoformat()
                else:
                    actualizado = None
                productos.append({
                    "producto": row['producto'],
                    "precio": row['precio'],
                    "actualizado": actualizado
                })
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()