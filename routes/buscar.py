from flask import Blueprint, request, jsonify, render_template
import psycopg2.extras
from threading import Thread
import re

# --- IMPORTACIONES ---
# Usamos PreciosGamer como fuente principal para minoristas.
# Tus scrapers de mayoristas como newbytes, invid, etc., se ejecutan por separado
# con el planificador APScheduler, por lo que no se importan aquí.
from services.preciosgamer_scraper import buscar_en_preciosgamer
from db.connection import get_db_connection

buscar_bp = Blueprint("buscar", __name__)

# Lock para evitar búsquedas duplicadas
ACTUALIZACIONES_EN_CURSO = set()

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
            tiendas_permitidas = {
                "Acuario Insumos", "Compra Gamer", "Compugarden", "Full H4rd",
                "Gaming City", "Integrados Argentinos", "Maximus", "Megasoft",
                "Mexx", "Scp Hardstore"
            }
            def normalizar_nombre(nombre):
                return re.sub(r'[\s\W_]+', '', nombre).lower()
            tiendas_permitidas_norm = {normalizar_nombre(t) for t in tiendas_permitidas}
            
            resultados_brutos = buscar_en_preciosgamer(producto)
            
            resultados_filtrados = []
            for res in resultados_brutos:
                nombre_tienda_norm = normalizar_nombre(res.get('sitio', ''))
                if nombre_tienda_norm in tiendas_permitidas_norm:
                    res.setdefault('imagen', ''); res.setdefault('marca', 'Sin Marca');
                    res.setdefault('precio_anterior', 0); res.setdefault('porcentaje_descuento', 0);
                    resultados_filtrados.append(res)

            print(f"-> Encontrados {len(resultados_brutos)} resultados brutos. Después de filtrar, quedan {len(resultados_filtrados)}.")

            if resultados_filtrados:
                guardar_resultados_db(resultados_filtrados)
            
            print(f"-> Actualización en 2do plano para '{producto}' finalizada.")
        finally:
            if producto in ACTUALIZACIONES_EN_CURSO:
                ACTUALIZACIONES_EN_CURSO.remove(producto)
                print(f"-> Lock liberado para '{producto}'.")

    thread = Thread(target=correr_busqueda_unica)
    thread.start()


# --- RUTA DE BÚSQUEDA PRINCIPAL (CON TODA LA LÓGICA RESTAURADA) ---
@buscar_bp.route("/comparar", methods=["GET"])
def comparar_productos():
    producto = request.args.get("producto", "").lower().strip()
    tipo = request.args.get("tipo", "minorista")

    if not producto:
        return jsonify({"error": "Falta el parámetro 'producto'"}), 400
    
    # Comprobamos el lock solo para búsquedas que usan el segundo plano
    if tipo in ["minorista", "masiva"] and producto in ACTUALIZACIONES_EN_CURSO:
        return jsonify({"estado": "actualizando", "mensaje": "Ya hay una actualización en curso..."})
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            filtro_tiempo = "AND actualizado > NOW() - INTERVAL '11 hours'"
            
            # --- LÓGICA RESTAURADA ---
            if tipo == "mayorista":
                sitios = ('NewBytes', 'Invid', 'AIR', 'POLYTECH')
                # La búsqueda en mayoristas es siempre en vivo desde la BD, no usa el segundo plano.
                query = f"SELECT * FROM productos WHERE sitio IN %s AND LOWER(producto) ILIKE %s ORDER BY precio ASC LIMIT 200"
                cur.execute(query, (sitios, f"%{producto}%"))
                resultados_actuales = [dict(row) for row in cur.fetchall()]

            else: # Lógica para minorista y masiva
                # Para masiva, no filtramos por la lista de tiendas permitidas en la consulta SQL, 
                # sino que traemos todo lo que coincida con el nombre del producto.
                # El scraper ya se encarga de filtrar por las tiendas que nos interesan.
                query = f"SELECT * FROM productos WHERE busqueda = %s {filtro_tiempo} ORDER BY precio ASC"
                cur.execute(query, (producto,))
                resultados_actuales = [dict(row) for row in cur.fetchall()]

                # Si no hay resultados recientes para minorista/masiva, lanzamos la actualización
                if not resultados_actuales:
                    ACTUALIZACIONES_EN_CURSO.add(producto)
                    print(f"-> Lock establecido para '{producto}'. Iniciando búsqueda en 2do plano.")
                    ejecutar_busqueda_en_segundo_plano(producto)
                    return jsonify({"estado": "actualizando", "mensaje": "Buscando este producto por primera vez..."})
        
            # Formateo de precios (común a todos los tipos de búsqueda)
            for r in resultados_actuales:
                if 'precio' in r and r['precio'] is not None:
                    valor = float(r['precio'])
                    r['precio'] = f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            return jsonify(resultados_actuales)
            
    except Exception as e:
        print(f"-> Error en /comparar: {e}")
        return jsonify({"error": "Ocurrió un error en el servidor", "detalle": str(e)}), 500
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