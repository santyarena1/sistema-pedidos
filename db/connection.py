import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)