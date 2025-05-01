import os
import psycopg2
import urllib.parse as urlparse

url = os.environ.get('DATABASE_URL') or "postgresql://postgres:admin123@localhost:5432/preciosdb"
url = urlparse.urlparse(url)

DB_CONFIG = {
    "dbname": url.path[1:],
    "user": url.username,
    "password": url.password,
    "host": url.hostname,
    "port": url.port
}


