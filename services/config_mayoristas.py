# -*- coding: utf-8 -*-
# services/config_mayoristas.py
# Config centralizada de URLs base por mayorista con fallback a ENV.

from __future__ import annotations
import os
from typing import Optional, Dict

# EDITABLE: definí acá los dominios base si NO querés usar variables de entorno.
# IMPORTANTE: sin trailing slash.
MAYORISTAS_BASE_URLS: Dict[str, str] = {
    # Ejemplos (reemplazá por tus dominios reales)
    # "AIR": "https://ar.air-intra.com/index_.htm",
    # "POLYTECH": "https://polytech.com.ar",
    # Si conocés otras:
    # "INVID": "https://www.invidcomputers.com/",
    # "NEWBYTES": "https://nb.com.ar/",
}

def obtener_base_url(mayorista: str) -> Optional[str]:
    """
    Orden de resolución:
      1) ENV: <MAYORISTA>_BASE_URL (p.ej., AIR_BASE_URL, POLYTECH_BASE_URL)
      2) Config interna MAYORISTAS_BASE_URLS
      3) None si no hay
    """
    clave_env = f"{mayorista.upper()}_BASE_URL"
    val_env = os.getenv(clave_env, "").strip()
    if val_env:
        return val_env
    # Config interna
    val_cfg = MAYORISTAS_BASE_URLS.get(mayorista.upper(), "").strip()
    return val_cfg or None
