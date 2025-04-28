import os
import urllib.parse

# Si existe DATABASE_URL (entorno de producción como Render), usamos eso
if "DATABASE_URL" in os.environ:
    urllib.parse.uses_netloc.append("postgres")
    url = urllib.parse.urlparse(os.environ["DATABASE_URL"])

    DB_CONFIG = {
        "dbname": url.path[1:],
        "user": url.username,
        "password": url.password,
        "host": url.hostname,
        "port": url.port
    }
else:
    # Local (tu PC)
    DB_CONFIG = {
        "dbname": "preciosdb",
        "user": "postgres",
        "password": "admin123",
        "host": "localhost",
        "port": "5432"
    }
