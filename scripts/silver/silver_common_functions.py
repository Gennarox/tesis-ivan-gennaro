"""
silver_common_functions.py
==========================

Funciones comunes utilizadas por los scripts de la capa Silver del pipeline ETL.
Estas funciones manejan conexión a PostgreSQL, creación de tablas, detección de
archivos en la capa Bronze, limpieza de nombres y carga eficiente de datos.

Este módulo está diseñado para ser reutilizado tanto en:

* SIlver schema
- bronze_to_silver_categories.py
- bronze_to_silver_products.py

* Silver_staging schema
- products_transformations.py
- categories_transformations.py
"""

import os
import glob
import re
import json
import pandas as pd
import psycopg2
from psycopg2 import sql
from io import StringIO

# ===================================================================================================================
# ===================================================================================================================
#                                             SILVER & SILVER STAGING SCHEMA
# ===================================================================================================================
# ===================================================================================================================

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
    

# ===================================================================================================================
# ===================================================================================================================
#                                             SILVER SCHEMA
# ===================================================================================================================
# ===================================================================================================================


# =============================================================================
# 🧱 CREACIÓN DE ESQUEMA Y TABLAS
# =============================================================================

def create_categories_table(conn):
    """
    Crea el esquema `silver` y la tabla `silver.categories` si no existen.

    Esta tabla se usa para almacenar las categorías procesadas desde Bronze.
    En caso de que ya existan, la función no realiza ningún cambio destructivo.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS silver.categories (
            snapshot_date DATE NOT NULL,
            supermarket TEXT NOT NULL,
            category_lvl1_name TEXT NULL,
            category_lvl2_name TEXT NULL,
            category_lvl3_name TEXT NULL,
            category_lvl1_id TEXT NULL,
            category_lvl2_id TEXT NULL,
            category_lvl3_id TEXT NULL,
            category_lvl1_slug TEXT NULL,
            category_lvl2_slug TEXT NULL,
            category_lvl3_slug TEXT NULL,
            created_at TIMESTAMP DEFAULT NOW()
            --PRIMARY KEY (snapshot_date, supermarket, category_lvl1_name, category_lvl2_name, category_lvl3_name)
        );
    """)

    conn.commit()
    cur.close()

def create_products_table(conn):
    """
    Crea la tabla `silver.products` si no existe.

    Esta tabla almacena los productos procesados desde Bronze, ya con estructura
    unificada. Si la tabla ya existe, no realiza cambios destructivos.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS silver.products (
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
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()



# =============================================================================
# 🗂️ UTILIDADES DE ARCHIVOS Y DIRECTORIOS
# =============================================================================

def list_supermarkets(base_path):
    """
    Lista los supermercados encontrados en el directorio base de outputs Bronze.

    Args:
        base_path (str): Ruta base, normalmente `/app/scripts/bronze/outputs`.

    Returns:
        list[str]: Lista de nombres de subdirectorios correspondientes a supermercados.
    """
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]


def find_category_files(sup_dir):
    """
    Busca archivos de categorías dentro del directorio de un supermercado.

    Args:
        sup_dir (str): Ruta al directorio del supermercado (ej: `/bronze/outputs/real`).

    Returns:
        list[str]: Lista de rutas a archivos CSV o JSON encontrados.
    """
    csvs = glob.glob(os.path.join(sup_dir, "categorias", "*.csv"))
    jsons = glob.glob(os.path.join(sup_dir, "categorias", "*.json"))
    return csvs + jsons


def extract_date_from_filename(filename):
    """
    Extrae la fecha del nombre del archivo usando una expresión regular.

    Se espera un formato tipo: `biggie_categorias_2025-08-01_12-00-00.json`.

    Args:
        filename (str): Nombre o ruta completa del archivo.

    Returns:
        str | None: Fecha en formato 'YYYY-MM-DD', o None si no se encontró.
    """
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None


# =============================================================================
# 🚀 CARGA DE DATAFRAME A POSTGRESQL
# =============================================================================

def copy_dataframe_to_postgres(df, conn, table_name):
    """
    Inserta un DataFrame en PostgreSQL usando el comando COPY (modo rápido y eficiente).

    El DataFrame debe tener exactamente las columnas que existen en la tabla destino.
    Internamente convierte el DataFrame a un buffer en formato TSV y lo copia vía STDIN.

    Args:
        df (pd.DataFrame): DataFrame a insertar.
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
        table_name (str): Nombre completo de la tabla destino (ej: 'silver.categories').

    Raises:
        psycopg2.Error: Si ocurre un error durante la carga en la base de datos.
    """

    # Convertir DataFrame en buffer TSV (maneja correctamente nulos y comas)
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)

    cur = conn.cursor()

    # Permitir esquema opcional
    if "." in table_name:
        schema, table = table_name.split(".")
        table_sql = sql.Identifier(schema, table)
    else:
        table_sql = sql.Identifier(table_name)

    # COPY usando formato CSV con delimitador de tabulaciones
    copy_sql = sql.SQL("""
        COPY {} FROM STDIN WITH (
            FORMAT CSV,
            DELIMITER E'\t',
            NULL '\\N'
        )
    """).format(table_sql)

    try:
        cur.copy_expert(copy_sql, buffer)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al copiar datos en {table_name}: {e}")
        raise
    finally:
        cur.close()

# ===================================================================================================================
# ===================================================================================================================
#                                             SILVER STAGING SCHEMA
# ===================================================================================================================
# ===================================================================================================================

def normalize_text(s):
    """
    Normaliza texto para matching:
    - minúsculas
    - quitar acentos
    - dejar solo letras/números
    - reducir espacios
    """
    if s is None:
        return None
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\\s]+", " ", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s

def create_staging_products_table(conn):
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
            final_price TEXT NULL,
            category_key TEXT NOT NULL
        );
    """)

    conn.commit()
    cur.close()

def create_staging_categories_table(conn):
    """
    Crea el esquema `silver_staging` y la tabla `silver_staging.categories` si no existen.

    Esta tabla se usa para almacenar las categorías procesadas desde Bronze.
    En caso de que ya existan, la función no realiza ningún cambio destructivo.

    Args:
        conn (psycopg2.connection): Conexión activa a PostgreSQL.
    """
    cur = conn.cursor()

    cur.execute("CREATE SCHEMA IF NOT EXISTS silver_staging;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS silver_staging.categories (
            snapshot_date DATE NOT NULL,
            supermarket TEXT NOT NULL,
            category_lvl1_name TEXT NULL,
            category_lvl2_name TEXT NULL,
            category_lvl3_name TEXT NULL,
            category_lvl1_id TEXT NULL,
            category_lvl2_id TEXT NULL,
            category_lvl3_id TEXT NULL,
            category_lvl1_slug TEXT NULL,
            category_lvl2_slug TEXT NULL,
            category_lvl3_slug TEXT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            category_slug_final TEXT NULL,
            category_final TEXT NULL,
            category_key TEXT NOT NULL PRIMARY KEY
        );
    """)

