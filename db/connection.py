# db/connection.py

import psycopg2
from config import DB_CONFIG

def get_db_connection():
    """
    Crea y devuelve una nueva conexión a la base de datos.
    Esta es la forma recomendada para asegurar que cada operación
    tenga una conexión limpia y estable, especialmente con hilos.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    return conn