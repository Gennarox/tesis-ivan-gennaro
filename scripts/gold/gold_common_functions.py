import os
import psycopg2
from psycopg2 import sql

# =============================================================================
# 💾 CONEXIÓN A BASE DE DATOS
# =============================================================================

def connect_to_postgres():
    """
    Establece una conexión con la base de datos PostgreSQL.

    Usa la variable de entorno `DB_DSN`, que debe contener el string de conexión
    completo en formato psycopg2 (ejemplo: "host=postgres_db dbname=myapp user=admin password=secret").

    Returns:
        psycopg2.connection | None: Objeto de conexión si se logra conectar, o None si falla.
    """
    DB_DSN = os.environ.get("DB_DSN")
    if not DB_DSN:
        print("⚠️ Variable de entorno DB_DSN no definida.")
        return None

    try:
        conn = psycopg2.connect(DB_DSN, connect_timeout=30)
        print("✅ Conectado a PostgreSQL")
        return conn
    except Exception as e:
        print("❌ Error conectando a PostgreSQL:", e)
        return None

def create_gold_products_table(conn):
    """
    Crea la tabla `gold.products` si no existe.

    Esta tabla almacena los productos procesados desde Silver, ya con estructura
    lista para reporteria. Si la tabla ya existe, no realiza cambios destructivos.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold.products (
            snapshot_date DATE NOT NULL,
            supermarket TEXT NOT NULL,
            product_id TEXT NULL,
            product_name TEXT NULL,
            brand TEXT NULL,
            price NUMERIC NULL,
            unit_of_measure TEXT NULL,
            is_on_promotion BOOLEAN NULL,
            promotion_price NUMERIC NULL,
            category_slug TEXT NULL,
            ingestion_time TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            final_price NUMERIC NULL,
            tom_brand TEXT NOT NULL,
            category_key TEXT NOT NULL,
            product_key TEXT NOT NULL PRIMARY KEY
        );
    """)

    conn.commit()
    cur.close()

def create_gold_categories_table(conn):
    """
    Crea el esquema `gold` y la tabla `gold.categories` si no existen.

    Esta tabla se usa para almacenar las categorías procesadas desde Bronze.
    En caso de que ya existan, la función no realiza ningún cambio destructivo.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold.categories (
            supermarket TEXT NOT NULL,
            category_slug_final TEXT NULL,
            category_final TEXT NULL,
            category_key TEXT NOT NULL PRIMARY KEY
        );
    """)
