# -*- coding: utf-8 -*-
"""
Runner de scrapers que funciona como:
  python -m services.probar_scrapers --site invid --q "5600g"
o también directamente (si el cwd es el root del repo):
  python services/probar_scrapers.py --site invid --q "5600g"

Permite probar: preciosgamer, tgs, invid, newbytes, air, polytech
"""

from __future__ import annotations
import argparse
import importlib
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# --- Habilitar import absolut/relativo según cómo se ejecute ---
# Si se ejecuta como script suelto, aseguramos que el root del repo esté en sys.path
CURRENT_FILE = os.path.abspath(__file__)
SERVICES_DIR = os.path.dirname(CURRENT_FILE)
REPO_ROOT = os.path.dirname(SERVICES_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Zona horaria Buenos Aires para timestamps legibles en logs
try:
    from zoneinfo import ZoneInfo
    TZ_BA = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    TZ_BA = None

def ts_ba() -> str:
    try:
        dt = datetime.now(tz=TZ_BA) if TZ_BA else datetime.now()
        return dt.strftime("%Y-%m-%d %H:%M:%S%z")
    except Exception:
        return datetime.now().isoformat()

# Mapa de módulos esperados -> función a invocar
SCRAPERS_INDEX = {
    "preciosgamer": ("services.preciosgamer_scraper", "buscar_en_preciosgamer"),
    "tgs":          ("services.thegamershop_scraper", "buscar_en_tgs"),
    "invid":        ("services.invid_scraper", "buscar_en_invid"),
    "newbytes":     ("services.newbytes_scraper", "buscar_en_newbytes"),
    "air":          ("services.air_scraper", "buscar_en_air"),
    "polytech":     ("services.polytech_scraper", "buscar_en_polytech"),
}

def load_scraper(site: str) -> Callable[[str], List[Dict[str, Any]]]:
    if site not in SCRAPERS_INDEX:
        raise ValueError(f"Site desconocido '{site}'. Opciones: {', '.join(SCRAPERS_INDEX.keys())}")
    module_name, fn_name = SCRAPERS_INDEX[site]
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"No pude importar el módulo '{module_name}'. "
            f"Verificá el nombre del archivo en services/ y el __init__.py"
        ) from e
    if not hasattr(mod, fn_name):
        raise AttributeError(f"El módulo '{module_name}' no tiene la función '{fn_name}'")
    return getattr(mod, fn_name)

def main():
    parser = argparse.ArgumentParser(description="Runner de scrapers (mayoristas/minoristas)")
    parser.add_argument("--site", required=True, help="preciosgamer | tgs | invid | newbytes | air | polytech")
    parser.add_argument("--q", required=True, help="término a buscar (producto)")
    parser.add_argument("--limit", type=int, default=5, help="mostrar primeros N resultados")
    args = parser.parse_args()

    # Logging sencillo en consola
    logging.basicConfig(
        level=logging.INFO,
        format=f"[%(levelname)s] {ts_ba()} - %(message)s"
    )

    try:
        fn = load_scraper(args.site)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar scraper '{args.site}': {e}")
        sys.exit(1)

    print(f"\n== Ejecutando scraper '{args.site}' para consulta: '{args.q}' ==\n")
    try:
        data = fn(args.q)
        print(f"Total resultados: {len(data)}\n")
        for i, item in enumerate(data[: args.limit], start=1):
            print(f"--- #{i} ---")
            print(json.dumps(item, ensure_ascii=False, indent=2))
        if not data:
            print("** Sin resultados. Revisar selectores, endpoint o filtros del sitio. **")
    except Exception as e:
        print(f"\n[ERROR] Falló la ejecución del scraper '{args.site}': {e}\n")
        raise

if __name__ == "__main__":
    main()
