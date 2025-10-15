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
DB_DSN = os.environ.get("DB_DSN", "host=postgres_db port=5432 dbname=myapp user=admin password=secure_password")
# --------------------------------------------------------------------------

# %% [markdown]
# ### Funcion principal

# %%


# %% [markdown]
# ### Ejecucion

# %%
if __name__ == "__main__":
    conn = connect_to_postgres()
    if conn:
        create_products_table(conn)
        conn.close()


