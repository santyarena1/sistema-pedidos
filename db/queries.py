from db.connection import conn

def guardar_en_db(busqueda, sitio, producto, precio, link):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO productos (busqueda, sitio, producto, precio, link)
                VALUES (%s, %s, %s, %s, %s)
            """, (busqueda, sitio, producto, precio, link))
            conn.commit()
    except Exception as e:
        print(f"❌ Error al guardar en DB ({sitio}): {e}")
        conn.rollback()

def obtener_desde_db(producto, sitio):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT producto, precio, link FROM productos
                WHERE LOWER(producto) LIKE %s AND sitio = %s
                ORDER BY actualizado DESC
                LIMIT 20
            """, (f"%{producto.lower()}%", sitio))
            rows = cursor.fetchall()
            return [
                {
                    "sitio": sitio,
                    "producto": row[0],
                    "precio": row[1],
                    "link": row[2]
                } for row in rows
            ]
    except Exception as e:
        print(f"❌ Error al consultar DB ({sitio}):", e)
        conn.rollback()
        return []