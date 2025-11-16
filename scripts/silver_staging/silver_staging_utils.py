import os
import glob
import re
import json
import pandas as pd
import psycopg2
from psycopg2 import sql
from io import StringIO


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

# =============================================================================
# 💾 LECTURA DE TABLAS DE SQL CON PANDAS                                                        A DEPRECAR
# =============================================================================

def read_table(query, conn):
    """Lee una tabla o query y devuelve un DataFrame"""
    return pd.read_sql(query, conn)

# =============================================================================
# 🧱 CREACIÓN DE ESQUEMA Y TABLAS                                                               repetido de silver, a unificar
# =============================================================================

def create_products_table(conn):
    """
    Crea la tabla `silver_staging.products` si no existe.

    Esta tabla almacena los productos procesados desde Silver, ya con estructura
    unificada. Si la tabla ya existe, no realiza cambios destructivos.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS silver_staging;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS silver_staging.products (
            snapshot_date DATE NOT NULL,
            supermarket TEXT NOT NULL,
            product_id TEXT NULL,
            product_name TEXT NULL,
            brand TEXT NULL,
            price TEXT NULL,
            unit_of_measure TEXT NULL,
            is_on_promotion BOOLEAN NULL,
            promotion_price TEXT NULL,
            category_slug TEXT NULL,
            ingestion_time TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            final_price TEXT NULL
        );
    """)

    conn.commit()
    cur.close()
