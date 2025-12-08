import pandas as pd
from psycopg2 import sql
from gold_common_functions import connect_to_postgres, create_gold_categories_table, create_gold_products_table

# ============================================================
# CONFIG
# ============================================================
SOURCE_TABLE = "silver_staging.categories"
TARGET_TABLE = "gold.categories"

def main():
    conn = connect_to_postgres()
    if not conn: return

    # 1) Asegurar que la tabla existe
    create_gold_categories_table(conn)
    
    # 2) Movimiento de datos con deduplicación SQL
    # Seleccionamos solo las columnas de reportería
    query_upsert = f"""
        INSERT INTO {TARGET_TABLE} (
            supermarket, 
            category_slug_final, 
            category_final, 
            category_key
        )
        SELECT 
            supermarket, 
            category_slug_final, 
            category_final, 
            category_key
        FROM {SOURCE_TABLE}
        ON CONFLICT (category_key) DO NOTHING;
    """

    try:
        with conn.cursor() as cur:
            print(f"▶ Cargando datos de {SOURCE_TABLE} a {TARGET_TABLE}...")
            cur.execute(query_upsert)
            rows_inserted = cur.rowcount
            print(f"✔ Proceso completado. Filas nuevas/procesadas: {rows_inserted}")
        
        conn.commit()
    except Exception as e:
        print(f"❌ Error en la carga a Gold: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()