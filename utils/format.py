def formatear_precio(valor):
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")