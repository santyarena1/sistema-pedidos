# -*- coding: utf-8 -*-
"""
Atajo para ejecutar scrapers desde la raíz del repo sin -m:
  python scrapers_runner.py --site invid --q "5600g"
"""
import os
import sys

if __name__ == "__main__":
    ROOT = os.path.dirname(os.path.abspath(__file__))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from services.probar_scrapers import main
    main()
