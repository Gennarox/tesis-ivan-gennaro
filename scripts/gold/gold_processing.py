import pandas as pd
from psycopg2 import sql
# Asegúrate de que estas funciones existan en tu gold_common_functions.py
from gold_common_functions import connect_to_postgres, create_gold_categories_table, create_gold_products_table 

# ============================================================
# CONFIG
# ============================================================
SOURCE_CATEGORY_TABLE = "silver_staging.categories"
TARGET_CATEGORY_TABLE = "gold.categories"

SOURCE_PRODUCT_TABLE = "silver_staging.products"
TARGET_PRODUCT_TABLE = "gold.products"

# ============================================================
# FUNCIONES DE CARGA
# ============================================================

def load_categories(conn):
    """Carga y deduplica la dimensión de categorías (usa category_key)."""
    
    # 1) Asegurar que la tabla existe (y tiene la PK 'category_key')
    create_gold_categories_table(conn)
    
    # 2) Definición de columnas a insertar
    columns_list = [
        "supermarket", 
        "category_slug_final", 
        "category_final", 
        "category_key"
    ]
    columns_sql = ", ".join(columns_list)
    
    # 3) Consulta de UPSERT (INSERT ON CONFLICT)
    query_upsert = f"""
        INSERT INTO {TARGET_CATEGORY_TABLE} ({columns_sql})
        SELECT {columns_sql}
        FROM {SOURCE_CATEGORY_TABLE}
        ON CONFLICT (category_key) DO NOTHING; 
    """

    with conn.cursor() as cur:
        print(f"\n▶ [Categories] Cargando de {SOURCE_CATEGORY_TABLE} a {TARGET_CATEGORY_TABLE} (Deduplicación)...")
        cur.execute(query_upsert)
        rows_inserted = cur.rowcount
        print(f"✔ [Categories] Proceso completado. Filas nuevas insertadas: {rows_inserted}")


def load_products(conn):
    """Carga y enforza unicidad para la tabla de hechos de productos (usa product_key)."""
    
    # 1) Asegurar que la tabla existe (y tiene la PK 'product_key')
    create_gold_products_table(conn)
    
    # 2) Definición de columnas a insertar
    columns_list = [
        "snapshot_date", 
        "supermarket", 
        "product_id", 
        "product_name", 
        "brand", 
        "price", 
        "unit_of_measure", 
        "is_on_promotion", 
        "promotion_price", 
        "category_slug", 
        "ingestion_time", 
        "created_at", 
        "final_price",
        "tom_brand",
        "category_key", 
        "product_key"
    ]
    columns_sql = ", ".join(columns_list)
    
    # 3) Consulta de UPSERT (INSERT ON CONFLICT)
    query_upsert = f"""
        INSERT INTO {TARGET_PRODUCT_TABLE} ({columns_sql})
        SELECT {columns_sql}
        FROM {SOURCE_PRODUCT_TABLE}
        ON CONFLICT (product_key) DO NOTHING; 
    """

    with conn.cursor() as cur:
        print(f"\n▶ [Products] Cargando de {SOURCE_PRODUCT_TABLE} a {TARGET_PRODUCT_TABLE} (Histórico/Deduplicación)...")
        cur.execute(query_upsert)
        rows_inserted = cur.rowcount
        print(f"✔ [Products] Proceso completado. Filas nuevas insertadas: {rows_inserted}")


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():
    """
    Función principal que orquesta la carga de datos desde Silver Staging a Gold,
    asegurando la unicidad de las dimensiones y los hechos.
    """
    conn = connect_to_postgres()
    if not conn: return

    try:
        # 1. Cargar la Dimensión de Categorías (Tabla pequeña, deduplicada por category_key)
        load_categories(conn)
        
        # 2. Cargar la Tabla de Hechos de Productos (Tabla grande, deduplicada por product_key)
        load_products(conn)
        
        conn.commit()
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN LA CARGA A GOLD: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n🎉 Proceso Gold completado.")

if __name__ == "__main__":
    main()