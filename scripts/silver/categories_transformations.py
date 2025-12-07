import os
import re
import json
import unicodedata
import pandas as pd
import numpy as np
from io import StringIO
from psycopg2 import sql
from silver_common_functions import connect_to_postgres, create_staging_categories_table


# ============================================================
# CONFIG
# ============================================================

CHUNKSIZE = 250000

SOURCE_QUERY = """
    SELECT *
    FROM silver.categories
"""

TARGET_TABLE = "categories"
TARGET_SCHEMA = "silver_staging"

MAPPINGS_FILE = '/app/scripts/silver/final_category_mappings.json'

# ============================================================
# HELPERS Y NORMALIZADORES
# ============================================================

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


def load_inverse_mappings():
    """
    Lee mapeo JSON y genera inv_maps[sup][categoria_super] = categoria_final
    """
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
        mappings = json.load(f)

    inv_maps = {sup: {} for sup in ["biggie", "casa_rica", "real", "s6", "stock"]}

    for final, mapping in mappings.items():
        for sup, cats in mapping.items():
            if cats is None:
                continue

            if isinstance(cats, str):
                cats = [cats]

            cats_norm = [normalize_text(c) for c in cats]

            for c in cats_norm:
                inv_maps[sup][c] = final

    return inv_maps


INV_MAPS = load_inverse_mappings()


# ============================================================
# TRANSFORMACIONES POR CHUNK
# ============================================================

def transform_chunk(chunk: pd.DataFrame) -> pd.DataFrame:

    # --------------------------------------------
    # 1) SLUG FINAL UNIFICADO
    # --------------------------------------------
    mask_real = chunk["supermarket"] == "real"

    chunk.loc[mask_real, "real_lvl1_clean"] = (
        chunk.loc[mask_real, "category_lvl1_slug"]
            .str.split("/", n=1)
            .str[-1]
    )

    chunk["category_slug_final"] = np.where(
        chunk["supermarket"] == "biggie", chunk["category_lvl1_slug"],
        np.where(
            chunk["supermarket"] == "casa_rica", chunk["category_lvl2_slug"],
            np.where(
                chunk["supermarket"].isin(["stock", "s6"]), chunk["category_lvl3_slug"],
                np.where(
                    chunk["supermarket"] == "real", chunk["real_lvl1_clean"],
                    None
                )
            )
        )
    )

    # --------------------------------------------
    # 2) NORMALIZACIÓN category_clean
    # --------------------------------------------
    chunk["category_clean"] = chunk["category_lvl1_name"].apply(normalize_text)

    # --------------------------------------------
    # 3) MAPEAR category_final
    # --------------------------------------------
    missing = set()

    def map_final(row):
        sup = row["supermarket"]
        clean = row["category_clean"]

        result = INV_MAPS.get(sup, {}).get(clean)

        if result is None:
            missing.add((sup, row["category_lvl1_name"], clean))

        return result

    chunk["category_final"] = chunk.apply(map_final, axis=1)

    # --------------------------------------------
    # 4) CREACIÓN DE KEYS
    # --------------------------------------------
    
    # Aseguramos fecha como string
    chunk["snapshot_date_str"] = chunk["snapshot_date"].astype(str)

    # CATEGORY_KEY (PK): category_slug_final + supermarket + snapshot_date
    # Usamos fillna('') en el slug por seguridad, aunque idealmente no debería ser nulo
    chunk["category_key"] = (
        chunk["category_slug_final"].fillna("unknown").astype(str) + "_" + 
        chunk["supermarket"].astype(str) + "_" + 
        chunk["snapshot_date_str"]
    )

    # --------------------------------------------
    # 5) LIMPIEZA DE DUPLICADOS EN EL CHUNK
    # --------------------------------------------
    # Este paso fue añadido por duplicaciones en la ingesta de categorias de S6 (pagina vieja)
    # Mantenemos solo la primera aparición de la llave
    rows_before = len(chunk)
    chunk = chunk.drop_duplicates(subset=["category_key"], keep="first")
    rows_after = len(chunk)

    if rows_before > rows_after:
        print(f"   ✂ Se eliminaron {rows_before - rows_after} filas duplicadas en este chunk.")

    # --------------------------------------------
    # Logging - Categorias no mapeadas
    # --------------------------------------------
    # Guardamos temporalmente las faltantes (luego lo haremos a un archivo log)
    if len(missing) > 0:
        print("⚠ Categorías no mapeadas encontradas en este chunk:")
        missing_list = sorted(missing)
        for sup, orig, clean in missing_list[:15]:
            print(f"  - {sup}: '{orig}' → '{clean}'")
        if len(missing_list) > 15:
            print(f"  ... y {len(missing_list) - 15} más.")

    return chunk

# ============================================================
# Elimina columnas auxiliares
# ============================================================

AUX_COLS = ["real_lvl1_clean", "category_clean", "snapshot_date_str"]

def drop_auxiliary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina columnas auxiliares antes de insertar en SQL"""
    cols_to_drop = [c for c in AUX_COLS if c in df.columns]
    return df.drop(columns=cols_to_drop, inplace=False)


# ============================================================
# INSERCIÓN COPY A POSTGRES
# ============================================================

def insert_chunk_copy(conn, df: pd.DataFrame):
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    columns = list(df.columns)

    with conn.cursor() as cur:
        cur.copy_expert(
            sql.SQL("""
                COPY {}.{} ({})
                FROM STDIN WITH CSV
            """).format(
                sql.Identifier(TARGET_SCHEMA),
                sql.Identifier(TARGET_TABLE),
                sql.SQL(",").join(map(sql.Identifier, columns))
            ),
            buffer
        )
    conn.commit()


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():

    conn = connect_to_postgres()
    if not conn:
        print("❌ No se pudo conectar a PostgreSQL")
        return

    # Crear tabla y limpiar destino
    create_staging_categories_table(conn)

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE silver_staging.categories;")
    conn.commit()

    print("▶ Tabla categories preparada")

    total_rows = 0
    chunk_num = 0

    print("▶ Leyendo categorías en chunks...")

    for chunk in pd.read_sql(SOURCE_QUERY, conn, chunksize=CHUNKSIZE):
        chunk_num += 1
        print(f"\n🔹 Procesando chunk {chunk_num} ({len(chunk):,} filas)")

        # 1) Transformaciones
        chunk = transform_chunk(chunk)

        # 2) Elimina columnas auxiliares
        chunk = drop_auxiliary_columns(chunk)

        # 3) Insertar
        insert_chunk_copy(conn, chunk)

        total_rows += len(chunk)
        print(f"✔ Chunk {chunk_num} insertado. Total acumulado: {total_rows:,} filas.")

    conn.close()

    print("\n🎉 Proceso finalizado")
    print(f"📦 Total filas procesadas: {total_rows:,}")


if __name__ == "__main__":
    main()