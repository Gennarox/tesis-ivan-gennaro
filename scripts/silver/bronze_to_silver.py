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

# %% [markdown]
# ### Funciones secundarias

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
    
def list_supermarkets(base_path):
    """Lista los supermercados disponibles en outputs/"""
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

def find_category_files(sup_dir):
    """Encuentra todos los CSV de categorías dentro del supermercado"""
    return glob.glob(os.path.join(sup_dir, "categorias", "*.csv"))

def extract_date_from_filename(filename):
    """Extrae fecha del nombre del archivo (ej: casaRica_categorias_2025-08-01.csv)"""
    import re
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None

def copy_dataframe_to_postgres(df, conn, table_name):
    """Inserta DataFrame en Postgres con COPY (rápido)"""
    from io import StringIO
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    cur = conn.cursor()
    cur.copy_expert(sql.SQL(f"COPY {table_name} FROM STDIN WITH CSV"), buffer)
    cur.close()

# %% [markdown]
# ### Funcion principal

# %%
def full_load_categories(conn):
    """
    Full load de categorías usando categories_mapping.json
    Compatible con todos los supermercados.
    """
    # 1️⃣ Cargar mapping
    with open(MAPPINGS_FILE, "r") as f:
        mappings = json.load(f)

    create_schema_and_tables(conn)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE silver.categories;")
    conn.commit()

    for sup, conf in mappings.items():
        sup_dir = os.path.join(BRONZE_ROOT, conf["path"])
        print(f"\n📦 Procesando supermercado: {sup} desde {sup_dir}")

        # Buscar archivos CSV/JSON
        files = glob.glob(os.path.join(sup_dir, "*.csv")) + glob.glob(os.path.join(sup_dir, "*.json"))
        if not files:
            print(f"⚠️ No se encontraron archivos para {sup}")
            continue

        for fpath in files:
            print(f"  ↳ Leyendo {fpath}")

            # 2️⃣ Leer archivo según tipo
            if conf["type"] == "csv":
                df = pd.read_csv(fpath)
            else:
                df = pd.read_json(fpath)

            # 3️⃣ Aplicar mapping básico (renombrar columnas que existen)
            simple_cols = {k: v for k, v in conf["columns"].items() if "[]" not in k}
            df = df.rename(columns=simple_cols)

            # 4️⃣ Procesar subcategorías JSON (si existen)
            for k, v in conf["columns"].items():
                if "[]" in k and k.split("[].")[0] in df.columns:
                    parent_col, sub_key = k.split("[].")
                    df_expanded = pd.json_normalize(df[parent_col].apply(lambda x: x if isinstance(x, list) else []))
                    if sub_key in df_expanded.columns:
                        df_expanded = df_expanded.rename(columns={sub_key: v})
                        df = pd.concat([df.drop(columns=[parent_col]), df_expanded], axis=1)

            # 5️⃣ Columnas comunes
            df["supermarket"] = sup
            df["snapshot_date"] = extract_date_from_filename(fpath)
            df["created_at"] = pd.Timestamp.now()

            # 6️⃣ Asegurar columnas del esquema
            cols_keep = [
                "snapshot_date", "supermarket",
                "category_lvl1_name", "category_lvl2_name", "category_lvl3_name",
                "category_lvl1_id", "category_lvl2_id", "category_lvl3_id",
                "category_lvl1_slug", "category_lvl2_slug", "category_lvl3_slug",
                "created_at"
            ]
            for col in cols_keep:
                if col not in df.columns:
                    df[col] = None
            df = df[cols_keep]

            # 7️⃣ Insertar en PostgreSQL
            copy_dataframe_to_postgres(df, conn, "silver.categories")
            conn.commit()

    cur.close()
    print("\n✅ Full load completado para todos los supermercados.")


# %% [markdown]
# ### Ejecucion

# %%
if __name__ == "__main__":
    conn = connect_to_postgres()
    if conn:
        full_load_categories(conn)
        conn.close()


