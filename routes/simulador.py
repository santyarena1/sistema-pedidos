# -*- coding: utf-8 -*-
# routes/simulador.py

import datetime
import json
from flask import Blueprint, render_template, jsonify, request
import psycopg2
import psycopg2.extras

# IMPORTANTE: adaptar este import a tu helper real
from db.connection import get_db_connection  # asumo que existe en tu proyecto

simulador_bp = Blueprint("simulador", __name__, url_prefix="/")

DEFAULT_CONFIG = [
    # proveedor, plan_codigo, plan_nombre, cuotas, porcentaje
    ("MERCADO_PAGO", "mp_debito",  "Débito",      1, 0.0),
    ("MERCADO_PAGO", "mp_credito", "Crédito",     1, 9.0),
    ("MERCADO_PAGO", "mp_3",       "3 cuotas",    3, 15.0),
    ("MERCADO_PAGO", "mp_6",       "6 cuotas",    6, 28.0),
    ("MERCADO_PAGO", "mp_12",      "12 cuotas",  12, 55.0),

    ("BBVA", "bbva_credito",       "Crédito",     1, 0.0),
    ("BBVA", "bbva_3_sin",         "3 cuotas s/interés", 3, 0.0),
    ("BBVA", "bbva_6_sin",         "6 cuotas s/interés", 6, 0.0),
]

def ensure_table_and_defaults(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS simulador_config (
            id SERIAL PRIMARY KEY,
            proveedor VARCHAR(50) NOT NULL,
            plan_codigo VARCHAR(50) NOT NULL UNIQUE,
            plan_nombre VARCHAR(100) NOT NULL,
            cuotas INTEGER NOT NULL DEFAULT 1,
            porcentaje NUMERIC(8,3) NOT NULL DEFAULT 0,
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        conn.commit()

        # Si no hay filas, insertar defaults
        cur.execute("SELECT COUNT(*) FROM simulador_config;")
        count = cur.fetchone()[0]
        if count == 0:
            for proveedor, codigo, nombre, cuotas, porcentaje in DEFAULT_CONFIG:
                cur.execute("""
                    INSERT INTO simulador_config (proveedor, plan_codigo, plan_nombre, cuotas, porcentaje, activo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (plan_codigo) DO NOTHING;
                """, (proveedor, codigo, nombre, cuotas, porcentaje))
            conn.commit()

@simulador_bp.route("/simulador")
def simulador_view():
    # Renderiza la página
    return render_template("simulador.html")

@simulador_bp.route("/api/simulador/config", methods=["GET"])
def simulador_get_config():
    conn = None
    try:
        conn = get_db_connection()
        ensure_table_and_defaults(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
              SELECT proveedor, plan_codigo, plan_nombre, cuotas, porcentaje, activo
              FROM simulador_config
              ORDER BY proveedor ASC, cuotas ASC, plan_codigo ASC;
            """)
            rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)
    except Exception as e:
        print(f"[simulador_get_config] ERROR: {e}")
        return jsonify({"error": "No se pudo obtener la configuración"}), 500
    finally:
        if conn: conn.close()

@simulador_bp.route("/api/simulador/config", methods=["PUT"])
def simulador_put_config():
    """
    Espera JSON: lista de objetos
    [
      { "proveedor": "MERCADO_PAGO", "plan_codigo": "mp_6", "plan_nombre": "6 cuotas", "cuotas": 6, "porcentaje": 28.0, "activo": true },
      ...
    ]
    """
    conn = None
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list):
            return jsonify({"error": "Formato inválido (se espera lista)"}), 400
        conn = get_db_connection()
        ensure_table_and_defaults(conn)
        with conn.cursor() as cur:
            for item in data:
                proveedor = item.get("proveedor")
                plan_codigo = item.get("plan_codigo")
                plan_nombre = item.get("plan_nombre") or ""
                cuotas = int(item.get("cuotas") or 1)
                porcentaje = float(item.get("porcentaje") or 0.0)
                activo = bool(item.get("activo") if "activo" in item else True)

                cur.execute("""
                  INSERT INTO simulador_config (proveedor, plan_codigo, plan_nombre, cuotas, porcentaje, activo, updated_at)
                  VALUES (%s, %s, %s, %s, %s, %s, NOW())
                  ON CONFLICT (plan_codigo)
                  DO UPDATE SET
                    proveedor = EXCLUDED.proveedor,
                    plan_nombre = EXCLUDED.plan_nombre,
                    cuotas = EXCLUDED.cuotas,
                    porcentaje = EXCLUDED.porcentaje,
                    activo = EXCLUDED.activo,
                    updated_at = NOW();
                """, (proveedor, plan_codigo, plan_nombre, cuotas, porcentaje, activo))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"[simulador_put_config] ERROR: {e}")
        return jsonify({"error": "No se pudo guardar la configuración"}), 500
    finally:
        if conn: conn.close()
