# services/probar_scrapers.py
# -*- coding: utf-8 -*-

from .preciosgamer_scraper import buscar_en_preciosgamer
from .thegamershop_scraper import buscar_en_tgs

def probar_scrapers(termino):
    print("\n========= PreciosGamer =========")
    pg = buscar_en_preciosgamer(termino)
    print(f"Productos de PreciosGamer: {len(pg)}")
    if pg:
        print("Ejemplo:", pg[0])

    print("\n========= TheGamerShop =========")
    tgs = buscar_en_tgs(termino)
    print(f"Productos de TheGamerShop: {len(tgs)}")
    if tgs:
        print("Ejemplo:", tgs[0])

if __name__ == "__main__":
    import sys
    termino = sys.argv[1] if len(sys.argv) > 1 else "Ryzen 5600G"
    probar_scrapers(termino)
