# %%
"""
Full load: procesa archivos de productos en bronze y carga en Postgres
"""

import os, json, glob
import pandas as pd
import psycopg2
from psycopg2 import sql
import re
from io import StringIO
import silver_common_functions
from silver_common_functions import connect_to_postgres, create_products_table, list_supermarkets, find_category_files, extract_date_from_filename, copy_dataframe_to_postgres

# ---------- CONFIG dinámico (usa env vars dentro del contenedor) ----------
BRONZE_ROOT = os.environ.get("BRONZE_PATH", "/app/scripts/bronze/outputs")
MAPPINGS_FILE = os.environ.get("MAPPINGS_FILE", "/app/scripts/silver/products_columns_mappings.json")
# --------------------------------------------------------------------------

# %% [markdown]
# ### Funcion principal

# %%
def full_load_products(conn):
    """
    Carga completa de productos desde la capa Bronze hacia Silver.
    Lee archivos CSV/JSON de distintos supermercados, aplica el mapeo definido en
    products_columns_mappings.json, y los inserta en PostgreSQL.
    Maneja estructuras anidadas (por ejemplo: promotion.price).
    """

    # 1️⃣ Cargar mapeos
    with open(MAPPINGS_FILE, "r") as f:
        mappings = json.load(f)

    # 2️⃣ Crear tabla si no existe y limpiar la tabla destino
    create_products_table(conn)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE silver.products;")
    conn.commit()

    # 3️⃣ Iterar por supermercado
    for sup, conf in mappings.items():
        sup_dir = os.path.join(BRONZE_ROOT, conf["path"])
        print(f"\n📦 Procesando supermercado: {sup} desde {sup_dir}")

        files = glob.glob(os.path.join(sup_dir, "*.csv")) + glob.glob(os.path.join(sup_dir, "*.json"))
        if not files:
            print(f"⚠️ No se encontraron archivos para {sup}")
            continue

        for fpath in files:
            print(f"  ↳ Leyendo {fpath}")
            try:
                if os.path.getsize(fpath) == 0:
                    print(f"    ⚠️ Archivo vacío, se omite: {os.path.basename(fpath)}")
                    continue

                # Leer el archivo
                if conf["type"] == "csv":
                    df = pd.read_csv(fpath, sep=',', thousands='.', decimal=',')
                else:
                    df = pd.read_json(fpath)

                if df.empty:
                    print(f"    ⚠️ DataFrame vacío, se omite: {os.path.basename(fpath)}")
                    continue

            except Exception as e:
                print(f"    ❌ Error leyendo {os.path.basename(fpath)}: {e}")
                continue

            # 4️⃣ Procesar mapeo: columnas simples y anidadas
            simple_cols = {}
            nested_cols = {}
            list_cols = {}

            for k, v in conf["columns"].items():
                if "[]" in k:  # Ejemplo: promotion.conditions[].price
                    list_cols[k] = v
                elif "." in k:  # Ejemplo: promotion.price
                    nested_cols[k] = v
                else:
                    simple_cols[k] = v

            # Renombrar columnas simples directamente
            df.rename(columns=simple_cols, inplace=True)

            # Expandir columnas anidadas simples
            for nested_col, new_col in nested_cols.items():
                parent_col, sub_key = nested_col.split(".", 1)
                if parent_col in df.columns:
                    expanded = pd.json_normalize(df[parent_col]).add_prefix(f"{parent_col}.")
                    if f"{parent_col}.{sub_key}" in expanded.columns:
                        df[new_col] = expanded[f"{parent_col}.{sub_key}"]
                    df.drop(columns=[parent_col], inplace=True, errors="ignore")

            # Expandir columnas con listas (ej: promotion.conditions[].price)
            for list_col, new_col in list_cols.items():
                parent_path, sub_key = list_col.split("[].")
                parent_root = parent_path.split(".")[0]
                if parent_root in df.columns:
                    # Convertir cada fila en lista válida
                    df_expanded = df[parent_root].apply(lambda x: x if isinstance(x, dict) else x)
                    df_expanded = pd.json_normalize(df_expanded)
                    # Buscar la columna expandida (p. ej. "promotion.conditions.price")
                    target_col = f"{parent_path}.{sub_key}"
                    if target_col in df_expanded.columns:
                        df[new_col] = df_expanded[target_col]
                    df.drop(columns=[parent_root], inplace=True, errors="ignore")

            # 5️⃣ Agregar metadatos comunes
            df["supermarket"] = sup
            df["snapshot_date"] = extract_date_from_filename(fpath)
            df["created_at"] = pd.Timestamp.now()

            # 6️⃣ Normalizar columnas según el esquema de la tabla
            cols_keep = [
                "snapshot_date", "supermarket",
                "product_id", "product_name", "brand",
                "price", "unit_of_measure",
                "is_on_promotion", "promotion_price",
                "category_slug", "ingestion_time", "created_at"
            ]
            df = df.reindex(columns=cols_keep, fill_value=None)

            """
            # 7️⃣ Tipos y limpieza básica
            bool_cols = ["is_on_promotion"]
            for col in bool_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes", "si"])

            num_cols = ["price", "discount_percent", "promotion_price"]
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            """

            # 8️⃣ Insertar en PostgreSQL
            try:
                copy_dataframe_to_postgres(df, conn, "silver.products")
                conn.commit()
            except Exception as e:
                print(f"    ❌ Error insertando {os.path.basename(fpath)}: {e}")
                conn.rollback()

    print("\n✅ Full load completado para todos los supermercados.")

# %% [markdown]
# ### Ejecucion

# %%
if __name__ == "__main__":
    conn = connect_to_postgres()
    if conn:
        full_load_products(conn)
        conn.close()


