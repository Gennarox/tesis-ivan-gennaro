import os
import re
import json
import pandas as pd
import numpy as np
from io import StringIO
from psycopg2 import sql
from silver_common_functions import connect_to_postgres, create_staging_products_table


# ============================================================
# CONFIG
# ============================================================

CHUNKSIZE = 150000
SOURCE_QUERY = """
    SELECT *
    FROM silver.products
"""
TARGET_TABLE = "products"
TARGET_SCHEMA = "silver_staging"


# ============================================================
# TRANSFORMACIONES BASE
# ============================================================

def clean_price(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[^\d,\.]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

# ============================================================
# FLAGGING DE MARCAS TOM
# ============================================================

def flag_tom_brands(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el nombre del producto y asigna la marca TOM.
    """
    tom_brands = {
        'Pechugón': r'pechugon',
        'Cavallaro': r'cavallaro',
        'Tres Leones': r'tres\s*leones',
        'Lactolanda': r'lactolanda',
        'Kurupí': r'kurupi',
        'Ochsi': r'ochsi',
        'Hellmann\'s': r'hellmann',
        'Trébol': r'trebol',
        'Coca-Cola': r'coca.*cola',
        'Sedal': r'sedal',
        'Pedigree': r'pedigree',
        'Mar': r'\bmar\b', 
        'Nikito': r'nikito',
        'OMO': r'\bomo\b',
        'Guaraní': r'guarani',
        'Mapex': r'mapex',
        'Caricias': r'caricia',
        'Ades': r'\bades\b',
        'Anita': r'\banita\b',
        'Brahma': r'brahma',
        'Red Bull': r'red\s*bull',
        'Nescafé': r'nescafe',
        'Huggies': r'huggies',
        'Incabril': r'incabril',
        'Colgate': r'colgate',
        'Rexona': r'rexona',
        'Nestlé': r'nestle'
    }

    # 1. Normalización del nombre
    df['search_term'] = (
        df['product_name']
        .str.lower()
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )

    # 2. Asignación del flag
    df['tom_brand'] = 'Otros' 

    for brand_label, pattern in tom_brands.items():
        mask = df['search_term'].str.contains(pattern, regex=True, na=False)
        df.loc[mask, 'tom_brand'] = brand_label

    # 3. Limpieza y retorno
    df.drop(columns=['search_term'], inplace=True)
    return df

# ============================================================
# TRANSFORMACIONES
# ============================================================

def transform_chunk(chunk: pd.DataFrame) -> pd.DataFrame:

    # ------------------------------
    # 1) price → limpiar y convertir
    # ------------------------------
    chunk["price"] = clean_price(chunk["price"])

    # ------------------------------
    # 2) promotion_price
    # ------------------------------
    chunk["promotion_price"] = chunk["promotion_price"].replace("0", None)
    chunk["promotion_price"] = clean_price(chunk["promotion_price"])

    # ------------------------------
    # 3) final_price
    # ------------------------------
    chunk["final_price"] = chunk["promotion_price"].fillna(chunk["price"])
    
    # ------------------------------
    # 4) FLAGGING DE MARCAS TOM
    # ------------------------------
    chunk = flag_tom_brands(chunk) 

    # ------------------------------
    # 5) CREACIÓN DE KEYS
    # ------------------------------

    # Pre-procesamiento de tipos para Keys
    chunk["snapshot_date_str"] = chunk["snapshot_date"].astype(str)
    
    # CATEGORY_KEY
    chunk["category_key"] = (
        chunk["category_slug"].astype(str) + "_" + 
        chunk["supermarket"].astype(str)
    )

    chunk["product_key"] = (
        chunk["product_id"].astype(str) + "_" +
        chunk["product_name"].astype(str) + "_" + 
        chunk["supermarket"].astype(str) + "_" + 
        chunk["snapshot_date_str"]
    )

    # Limpieza: Eliminamos la columna auxiliar de fecha string si no la quieres en la tabla final
    chunk.drop(columns=["snapshot_date_str"], inplace=True)

    return chunk


# ============================================================
# ... (El resto del script, insert_chunk_copy y main, se mantiene igual)
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
    create_staging_products_table(conn)
    
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