# %%
"""
bronze_to_silver.py
Full load: procesa archivos de categorías en bronze y carga en Postgres
"""

import os, json, glob
import pandas as pd
import psycopg2
from psycopg2 import sql

# ---------- CONFIG dinámico (usa env vars dentro del contenedor) ----------
BRONZE_ROOT = os.environ.get("BRONZE_PATH", "/app/scripts/bronze/outputs")
MAPPINGS_FILE = os.environ.get("MAPPINGS_FILE", "/app/scripts/silver/categories_mapping.json")
DB_DSN = os.environ.get("DB_DSN", "host=postgres_db port=5432 dbname=myapp user=admin password=secure_password")
# --------------------------------------------------------------------------

# %%
def connect_to_postgres():
    """Conecta a PostgreSQL y retorna la conexión"""
    try:
        conn = psycopg2.connect(DB_DSN)
        print("✅ Conectado a PostgreSQL")
        return conn
    except Exception as e:
        print("❌ Error conectando a PostgreSQL:", e)
        return None

# %%
def create_schema_and_tables(conn):
    """Crea el esquema y la tabla si no existen"""
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS silver.categories(
            snapshot_date DATE NOT NULL,
            supermarket TEXT NOT NULL,
            category_lvl1_name TEXT,
            category_lvl2_name TEXT,
            category_lvl3_name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (snapshot_date, supermarket, category_lvl1_name, category_lvl2_name, category_lvl3_name)
        );
    """)
    conn.commit()
    cur.close()

# %%
def list_supermarkets(base_path):
    """Lista los supermercados disponibles en outputs/"""
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

# %%
def find_category_files(sup_dir):
    """Encuentra todos los CSV de categorías dentro del supermercado"""
    return glob.glob(os.path.join(sup_dir, "categorias", "*.csv"))


# %%
def full_load_categories(conn):
    """Hace un full load de categorías en la base de datos"""
    create_schema_and_tables(conn)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE silver.categories;")
    conn.commit()

    supermarkets = list_supermarkets(BRONZE_ROOT)
    for sup in supermarkets:
        print(f"📦 Procesando supermercado: {sup}")
        sup_dir = os.path.join(BRONZE_ROOT, sup)
        files = find_category_files(sup_dir)

        for fpath in files:
            print(f"  ↳ Leyendo {fpath}")
            df = pd.read_csv(fpath)
            df["supermarket"] = sup
            df["snapshot_date"] = extract_date_from_filename(fpath)

            # Insertar en PostgreSQL
            copy_dataframe_to_postgres(df, conn, "silver.categories")

    conn.commit()
    cur.close()
    print("✅ Full load completado.")


# %%
def extract_date_from_filename(filename):
    """Extrae fecha del nombre del archivo (ej: casaRica_categorias_2025-08-01.csv)"""
    import re
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None

# %%
def copy_dataframe_to_postgres(df, conn, table_name):
    """Inserta DataFrame en Postgres con COPY (rápido)"""
    from io import StringIO
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    cur = conn.cursor()
    cur.copy_expert(sql.SQL(f"COPY {table_name} FROM STDIN WITH CSV"), buffer)
    cur.close()

# %%
# ---------- MAIN ----------
if __name__ == "__main__":
    conn = connect_to_postgres()
    if conn:
        full_load_categories(conn)
        conn.close()



