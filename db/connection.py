# db/connection.py
import psycopg2
from config import DATABASE_URL # Importamos la variable directamente

def get_db_connection():
    """
    Crea y devuelve una nueva conexión a la base de datos
    usando la URL completa.
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn