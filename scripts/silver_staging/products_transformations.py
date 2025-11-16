import os
import re
import json
import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import sql
from io import StringIO
from silver_staging_utils import connect_to_postgres, create_products_table


# ============================================================
# CONFIG
# ============================================================

CHUNKSIZE = 10000
SOURCE_QUERY = """
    SELECT *
    FROM silver.products
    ORDER BY snapshot_date
"""
TARGET_TABLE = "products"
TARGET_SCHEMA = "silver_staging"


# ============================================================
# TRANSFORMACIONES
# ============================================================

def clean_price(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[^\d,\.]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )


def transform_chunk(chunk: pd.DataFrame) -> pd.DataFrame:

    # Limpieza básica de price
    chunk["price"] = clean_price(chunk["price"])

    # promotion_price: convertir "0" a NULL
    chunk.loc[chunk["promotion_price"] == "0", "promotion_price"] = None

    # final_price
    chunk["final_price"] = (
        chunk["promotion_price"].combine_first(chunk["price"])
    )

    return chunk


# ============================================================
# INSERCIÓN RÁPIDA A POSTGRES (COPY FROM)
# ============================================================

def insert_chunk_copy(conn, df: pd.DataFrame):

    # Convertir DataFrame → CSV en memoria
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

    # Crear tabla si no existe y limpiar la tabla destino=
    create_products_table(conn)
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE silver_staging.products;")
    conn.commit()

    print("▶ Table en SQL preparada correctamente")

    total_rows = 0
    chunk_num = 0

    print("▶ Leyendo en chunks...")

    for chunk in pd.read_sql(SOURCE_QUERY, conn, chunksize=CHUNKSIZE):

        chunk_num += 1
        print(f"🔹 Procesando chunk {chunk_num} ({len(chunk):,} filas)")

        # 1) Transformaciones
        chunk = transform_chunk(chunk)

        # 2) Inserción eficiente con COPY
        insert_chunk_copy(conn, chunk)

        total_rows += len(chunk)
        print(f"✔ Chunk {chunk_num} insertado. Total acumulado: {total_rows:,} filas.")

    conn.close()
    print("🎉 Proceso finalizado")
    print(f"📦 Total filas procesadas: {total_rows:,}")


if __name__ == "__main__":
    main()