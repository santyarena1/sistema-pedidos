import os
import psycopg2
import urllib.parse as urlparse

# Leer DATABASE_URL desde las variables de entorno
url = urlparse.urlparse(os.environ['DATABASE_URL'])

DB_CONFIG = {
    'dbname': url.path[1:],
    'user': url.username,
    'password': url.password,
    'host': url.hostname,
    'port': url.port
}

# Conexión directa
conn = psycopg2.connect(**DB_CONFIG)
