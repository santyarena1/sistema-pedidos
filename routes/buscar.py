# routes/buscar.py
# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional

from flask import Blueprint, request, jsonify, current_app

# ============================================
# Configuración
# ============================================
buscar_bp = Blueprint("buscar", __name__, url_prefix="/buscar")

TZ_UTC = timezone.utc
DIAS_FRESCURA = int(os.getenv("FRESHNESS_DAYS", "3"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

MINORISTAS_ESPERADOS = ["PreciosGamer", "The Gamer Shop"]
MAYORISTAS_ESPERADOS = [
    "Maximus", "FullH4rd Mayorista", "HyperGaming Mayorista", "CompraGamer Mayorista"
]

# ============================================
# Conexión a BD (intenta db.py; si no, psycopg2; si no, sin BD)
# ============================================
_modo_bd = None
_mod_bd = None      # módulo db.py o pool
_psycopg2 = None

def _inicializar_bd_una_vez():
    """Detecta cómo conectarnos a la BD (tu db.py o psycopg2)."""
    global _modo_bd, _mod_bd, _psycopg2
    if _modo_bd is not None:
        return

    # 1) Intentar usar tu módulo db.py (nombres usuales)
    try:
        import db as _mydb
        if hasattr(_mydb, "get_connection"):
            _modo_bd = "mod_get_connection"; _mod_bd = _mydb; return
        if hasattr(_mydb, "get_db"):
            _modo_bd = "mod_get_db"; _mod_bd = _mydb; return
        if hasattr(_mydb, "pool"):
            _modo_bd = "mod_pool"; _mod_bd = _mydb.pool; return
    except Exception:
        pass

    # 2) Fallback psycopg2 con DSN
    if DATABASE_URL:
        try:
            import psycopg2
            import psycopg2.extras
            _psycopg2 = psycopg2
            _modo_bd = "psycopg2_dsn"
            return
        except Exception as e:
            try:
                current_app.logger.error("psycopg2 no disponible (%s). Instalar: pip install psycopg2-binary", e)
            except Exception:
                print("psycopg2 no disponible. Instalar: pip install psycopg2-binary")

    # 3) Sin BD (modo sin cache)
    _modo_bd = "sin_bd"
    try:
        current_app.logger.warning("DATABASE_URL no configurada o sin psycopg2: se ejecuta sin BD (solo live/simulado).")
    except Exception:
        print("ADVERTENCIA: Sin BD. Se ejecuta sin cache.")

def _obtener_conexion():
    """Devuelve una conexión a BD según el modo detectado."""
    _inicializar_bd_una_vez()
    if _modo_bd == "mod_get_connection":
        return _mod_bd.get_connection()
    if _modo_bd == "mod_get_db":
        return _mod_bd.get_db()
    if _modo_bd == "mod_pool":
        return _mod_bd.getconn()
    if _modo_bd == "psycopg2_dsn":
        return _psycopg2.connect(DATABASE_URL)
    return None

def _devolver_conexion(conn):
    """Devuelve conexión al pool si aplica."""
    try:
        if conn is None:
            return
        if _modo_bd == "mod_pool":
            _mod_bd.putconn(conn)
        else:
            conn.close()
    except Exception:
        pass

# ============================================
# Utilidades
# ============================================
def iso_utc(dt: Optional[datetime] = None) -> str:
    if not isinstance(dt, datetime):
        dt = datetime.now(TZ_UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_UTC)
    return dt.astimezone(TZ_UTC).isoformat().replace("+00:00", "Z")

def precio_a_float(precio: Any) -> float:
    if precio is None:
        return 0.0
    if isinstance(precio, (int, float)):
        return float(precio)
    s = str(precio)
    s = s.replace("$", "").replace("USD", "").replace("ARS", "").strip()
    s = s.replace(".", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def normalizar_item(it: Dict[str, Any]) -> Dict[str, Any]:
    sitio = it.get("sitio") or ""
    producto = it.get("producto") or ""
    precio = it.get("precio")
    precio_numeric = it.get("precio_numeric")
    if precio_numeric is None:
        precio_numeric = precio_a_float(precio)
    link = (it.get("link") or "").strip()
    imagen = it.get("imagen")
    sku = it.get("sku")
    origen = it.get("origen") or "live"
    fetched_at = it.get("fetched_at") or iso_utc()
    return {
        "sitio": sitio,
        "producto": producto,
        "precio": precio if precio is not None else (f"$ {int(precio_numeric):,}".replace(",", ".")),
        "precio_numeric": float(precio_numeric),
        "link": link,
        "imagen": imagen if imagen else None,
        "sku": sku,
        "origen": origen,
        "fetched_at": fetched_at
    }

def dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    vistos = set()
    out = []
    for it in items:
        clave = (str(it.get("sitio","")).strip().lower(), str(it.get("link","")).strip())
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append(it)
    return out

def contar_por_tienda(items: List[Dict[str, Any]]) -> Dict[str, int]:
    d = {}
    for it in items:
        s = it.get("sitio") or "?"
        d[s] = d.get(s, 0) + 1
    return d

def round_robin(grupos: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    salida = []
    i = 0
    while True:
        agrego = False
        for g in grupos:
            if i < len(g):
                salida.append(g[i])
                agrego = True
        if not agrego:
            break
        i += 1
    return salida

# ============================================
# BD helpers
# ============================================
def bootstrap_bd():
    _inicializar_bd_una_vez()
    if _modo_bd == "sin_bd":
        return
    sql = """
    CREATE TABLE IF NOT EXISTS precios (
        id BIGSERIAL PRIMARY KEY,
        sitio TEXT NOT NULL,
        producto TEXT,
        precio TEXT,
        precio_numeric DOUBLE PRECISION,
        link TEXT,
        imagen TEXT,
        sku TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_precios_sitio_link
        ON precios (LOWER(sitio), COALESCE(link,''));
    CREATE INDEX IF NOT EXISTS ix_precios_updated_at ON precios (updated_at DESC);
    CREATE INDEX IF NOT EXISTS ix_precios_sitio ON precios (LOWER(sitio));
    """
    conn = _obtener_conexion()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
    finally:
        _devolver_conexion(conn)

def guardar_resultados_db(items: List[Dict[str, Any]]) -> None:
    """
    FUNCIÓN QUE USA TU app.py.
    Guarda/upsertea resultados en la tabla precios.
    """
    if not items or _modo_bd == "sin_bd":
        return
    sql = """
    INSERT INTO precios (sitio, producto, precio, precio_numeric, link, imagen, sku, updated_at)
    VALUES (%(sitio)s, %(producto)s, %(precio)s, %(precio_numeric)s, %(link)s, %(imagen)s, %(sku)s, %(updated_at)s)
    ON CONFLICT (LOWER(sitio), COALESCE(link,'')) DO UPDATE SET
        producto = EXCLUDED.producto,
        precio = EXCLUDED.precio,
        precio_numeric = EXCLUDED.precio_numeric,
        imagen = EXCLUDED.imagen,
        sku = EXCLUDED.sku,
        updated_at = EXCLUDED.updated_at;
    """
    ahora = datetime.now(TZ_UTC)
    payload = []
    for it in items:
        norm = normalizar_item(it)
        payload.append({
            "sitio": norm.get("sitio"),
            "producto": norm.get("producto"),
            "precio": norm.get("precio"),
            "precio_numeric": float(norm.get("precio_numeric") or 0),
            "link": (norm.get("link") or ""),
            "imagen": norm.get("imagen"),
            "sku": norm.get("sku"),
            "updated_at": ahora
        })
    conn = _obtener_conexion()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.executemany(sql, payload)
        conn.commit()
    finally:
        _devolver_conexion(conn)

# Alias de compatibilidad (por si en algún lado quedó el nombre en inglés)
db_upsert_many = guardar_resultados_db

def buscar_en_bd_por_sitio(sitio: str, texto: str, dias_frescura: int = DIAS_FRESCURA) -> List[Dict[str, Any]]:
    """Lee de BD resultados frescos por sitio y texto."""
    if _modo_bd == "sin_bd":
        return []
    fecha_min = datetime.now(TZ_UTC) - timedelta(days=dias_frescura)
    sql = """
    SELECT sitio, producto, precio, precio_numeric, link, imagen, sku, updated_at
    FROM precios
    WHERE LOWER(sitio) = LOWER(%s)
      AND updated_at >= %s
      AND (
            producto ILIKE %s
         OR  sku ILIKE %s
         OR  link ILIKE %s
      )
    ORDER BY updated_at DESC
    LIMIT 200
    """
    conn = _obtener_conexion()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        like = f"%{texto}%"
        cur.execute(sql, (sitio, fecha_min, like, like, like))
        filas = cur.fetchall()
        salida = []
        for (sitio, producto, precio, precio_numeric, link, imagen, sku, updated_at) in filas:
            salida.append(normalizar_item({
                "sitio": sitio,
                "producto": producto,
                "precio": precio,
                "precio_numeric": float(precio_numeric) if precio_numeric is not None else None,
                "link": link,
                "imagen": imagen,
                "sku": sku,
                "origen": "cache",
                "fetched_at": iso_utc(updated_at) if updated_at else iso_utc()
            }))
        return salida
    finally:
        _devolver_conexion(conn)

# ============================================
# Scrapers (placeholder: conectá tus reales acá)
# ============================================
def scrape_preciosgamer(texto: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # TODO: implementar scraping real
    items: List[Dict[str, Any]] = []
    dbg = {"url": f"https://www.preciosgamer.com/?q={texto}", "status": "simulado"}
    return items, dbg

def scrape_tgs(texto: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # TODO: implementar scraping real
    items: List[Dict[str, Any]] = []
    dbg = {"url": f"https://thegamershop.com/?q={texto}", "status": "simulado"}
    return items, dbg

def scrape_mayorista(nombre_sitio: str, texto: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # TODO: implementar scraping real por mayorista
    # Importante: devolver imagen=None para mayoristas (blanco en el front)
    items: List[Dict[str, Any]] = []
    dbg = {"site": nombre_sitio, "status": "simulado"}
    return items, dbg

# ============================================
# Búsquedas por tipo (lógicas principales)
# ============================================
def buscar_minoristas(texto: str, live: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    errores = {}
    dbg_extra = {}
    items: List[Dict[str, Any]] = []

    # Cache BD
    for sitio in MINORISTAS_ESPERADOS:
        cache = buscar_en_bd_por_sitio(sitio, texto)
        items.extend([normalizar_item({**it, "origen": "cache"}) for it in cache])

    # Live
    if live:
        try:
            res, dbg = scrape_preciosgamer(texto)
            dbg_extra["PreciosGamer"] = dbg
            res = [normalizar_item({**it, "sitio":"PreciosGamer", "origen":"live"}) for it in res]
            items.extend(res); guardar_resultados_db(res)
        except Exception as e:
            errores["PreciosGamer"] = str(e)

        try:
            res, dbg = scrape_tgs(texto)
            dbg_extra["The Gamer Shop"] = dbg
            res = [normalizar_item({**it, "sitio":"The Gamer Shop", "origen":"live"}) for it in res]
            items.extend(res); guardar_resultados_db(res)
        except Exception as e:
            errores["The Gamer Shop"] = str(e)

    items = dedup(items)
    return items, {"errores": errores, "scrape_debug": dbg_extra}

def buscar_mayoristas(texto: str, live: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    errores = {}
    dbg_extra = {}
    items: List[Dict[str, Any]] = []

    # Cache BD
    for sitio in MAYORISTAS_ESPERADOS:
        cache = buscar_en_bd_por_sitio(sitio, texto)
        cache = [normalizar_item({**it, "imagen": None, "origen":"cache"}) for it in cache]
        items.extend(cache)

    # Live
    if live:
        for sitio in MAYORISTAS_ESPERADOS:
            try:
                res, dbg = scrape_mayorista(sitio, texto)
                dbg_extra[sitio] = dbg
                res = [normalizar_item({**it, "sitio": sitio, "imagen": None, "origen":"live"}) for it in res]
                items.extend(res); guardar_resultados_db(res)
            except Exception as e:
                errores[sitio] = str(e)

    items = dedup(items)
    return items, {"errores": errores, "scrape_debug": dbg_extra}

def buscar_masiva(texto: str, live: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    min_items, min_dbg = buscar_minoristas(texto, live=live)
    may_items, may_dbg = buscar_mayoristas(texto, live=live)
    items = dedup(min_items + may_items)

    # Intercalado por tienda (para “masiva”)
    grupos: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        grupos.setdefault(it["sitio"], []).append(it)
    intercalado = round_robin(list(grupos.values()))

    dbg_all = {"minoristas": min_dbg, "mayoristas": may_dbg}
    return intercalado, dbg_all

# ============================================
# Helpers de debug y logging
# ============================================
def construir_debug(items: List[Dict[str, Any]], esperados: List[str], extras: Dict[str, Any]):
    presentes = set([it.get("sitio") for it in items])
    faltantes = [s for s in esperados if s not in presentes]
    return {
        "total": len(items),
        "por_tienda": contar_por_tienda(items),
        "faltantes": faltantes,
        **(extras or {})
    }

def registrar_busqueda(producto: str, tipo: str, items: List[Dict[str, Any]], bloque_debug: Dict[str, Any]):
    try:
        payload = {
            "producto": producto,
            "tipo": tipo,
            "total": len(items),
            "por_tienda": contar_por_tienda(items),
            "debug": bloque_debug,
            "items": items
        }
        current_app.logger.info("search_results %s", json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass

# ============================================
# Endpoint HTTP /buscar
# ============================================
@buscar_bp.route("", methods=["GET", "POST"])
def endpoint_buscar():
    """
    Body/Query:
      q: texto (obligatorio)
      tipo: minoristas | mayoristas | masiva (default minoristas)
      live: true/false (default true)
      debug: true/false (default false)
    """
    bootstrap_bd()

    payload = request.get_json(silent=True) or {}
    q = payload.get("q") or request.args.get("q") or ""
    tipo = (payload.get("tipo") or request.args.get("tipo") or "minoristas").strip().lower()
    live = payload.get("live")
    if live is None:
        live = (request.args.get("live", "true").lower() != "false")
    want_debug = payload.get("debug")
    if want_debug is None:
        want_debug = (request.args.get("debug", "false").lower() == "true")

    if not q:
        return jsonify({"ok": False, "error": "Falta parámetro 'q'."}), 400

    try:
        if tipo == "minoristas":
            items, dbg = buscar_minoristas(q, live=live)
            debug_block = construir_debug(items, MINORISTAS_ESPERADOS, dbg)
        elif tipo == "mayoristas":
            items, dbg = buscar_mayoristas(q, live=live)
            debug_block = construir_debug(items, MAYORISTAS_ESPERADOS, dbg)
        elif tipo == "masiva":
            items, dbg = buscar_masiva(q, live=live)
            debug_block = construir_debug(items, MINORISTAS_ESPERADOS + MAYORISTAS_ESPERADOS, dbg)
        else:
            return jsonify({"ok": False, "error": f"Tipo desconocido: {tipo}"}), 400

        registrar_busqueda(q, tipo, items, debug_block)

        resp = {
            "ok": True,
            "tipo": tipo,
            "query": q,
            "total": len(items),
            "resultados": items
        }
        if want_debug:
            resp["debug"] = debug_block

        return jsonify(resp), 200

    except Exception as e:
        current_app.logger.exception("Error en /buscar")
        return jsonify({"ok": False, "error": str(e)}), 500

# ============================================
# Funciones auxiliares para tareas en app.py
# ============================================
def actualizar_mayoristas_y_guardar(texto: str) -> Dict[str, Any]:
    """
    Para usar en tu tarea de app.py.
    Busca mayoristas (live=True), guarda en BD y devuelve un resumen.
    """
    bootstrap_bd()
    items, dbg = buscar_mayoristas(texto, live=True)
    # (Ya se guardan dentro de buscar_mayoristas con guardar_resultados_db)
    resumen = {
        "query": texto,
        "total": len(items),
        "por_tienda": contar_por_tienda(items),
        "faltantes": construir_debug(items, MAYORISTAS_ESPERADOS, dbg).get("faltantes", []),
    }
    return resumen

# Aliases de compatibilidad (si tu app.py esperaba estos nombres)
tarea_actualizar_mayoristas = actualizar_mayoristas_y_guardar
guardar_en_bd = guardar_resultados_db
