# %%
"""
Full load: procesa archivos de categorías en bronze y carga en Postgres
"""

import os, json, glob
import pandas as pd
import psycopg2
from psycopg2 import sql
import re
from io import StringIO
import silver.silver_common_functions
from silver.silver_common_functions import connect_to_postgres, create_categories_table, list_supermarkets, find_category_files, extract_date_from_filename, copy_dataframe_to_postgres

# ---------- CONFIG dinámico (usa env vars dentro del contenedor) ----------
BRONZE_ROOT = os.environ.get("BRONZE_PATH", "/app/scripts/bronze/outputs")
MAPPINGS_FILE = os.environ.get("MAPPINGS_FILE", "/app/scripts/silver/categories_columns_mappings.json")
DB_DSN = os.environ.get("DB_DSN", "host=postgres_db port=5432 dbname=myapp user=admin password=secure_password")
# --------------------------------------------------------------------------

# %% [markdown]
# ### Funcion principal

# %%
def full_load_categories(conn):
    """
    Full load de categorías usando categories_columns_mappings.json
    Compatible con todos los supermercados.
    """
    # 1️⃣ Cargar mapping
    with open(MAPPINGS_FILE, "r") as f:
        mappings = json.load(f)

    create_categories_table(conn)
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


