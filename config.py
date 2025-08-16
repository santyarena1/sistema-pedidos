# config.py
import os

# Carga la URL de la base de datos desde las variables de entorno.
# El fallback a localhost es útil solo para desarrollo local.
DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://postgres:postgres@localhost:5432/preciosdb")

# Si DATABASE_URL no está definida en producción, es mejor que falle para detectar el error.
if 'RENDER' in os.environ and not DATABASE_URL.startswith('postgresql://postgressanty'):
    raise ValueError("DATABASE_URL no está configurada correctamente en el entorno de producción.")