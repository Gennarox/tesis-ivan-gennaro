# %%
import pandas as pd
from silver_staging_utils import connect_to_postgres, read_table
import numpy as np
import json
import re
import unicodedata

MAPPINGS_FILE = '/workspaces/tesis-ivan-gennaro/scripts/silver_staging/final_category_mappings.json'

# %% [markdown]
# # Productos

# %%
query = '''
SELECT
    *
FROM silver.products
WHERE
    snapshot_date IN (
        SELECT DISTINCT snapshot_date FROM silver.products ORDER BY snapshot_date DESC LIMIT 10   
    )
'''
print(query)

conn = connect_to_postgres()
if conn:
    df = read_table(query, conn)
    conn.close()

# %%
df.info()

# %%
df['snapshot_date'].unique()

# %%
df['supermarket'].unique()

# %% [markdown]
# ## Final Price creation

# %% [markdown]
# ##### Price problem with Casa Rica

# %%
df["price"] = (
    df["price"]
    .astype(str)
    .str.replace(r"[^\d,\.]", "", regex=True)
    .str.replace(".", "", regex=False) 
    .str.replace(",", ".", regex=False)
    .pipe(pd.to_numeric, errors="coerce")
)

# %% [markdown]
# ##### Coalesce to build final price

# %%
df.loc[df['promotion_price'] == '0', 'promotion_price'] = None

# %%
df["final_price"] = (
    df["promotion_price"]
        .combine_first(df['price'])
)

# %% [markdown]
# # Categoria

# %%
query = '''
SELECT
    *
FROM silver.categories
WHERE
    snapshot_date IN (
        SELECT MAX(snapshot_date) FROM silver.categories  
    )
'''
print(query)

conn = connect_to_postgres()
if conn:
    df = read_table(query, conn)
    conn.close()

# %%
df.info()

# %%
df['snapshot_date'].unique()

# %%
df['supermarket'].unique()

# %% [markdown]
# ### category_final_slug
# Creacion de un slug homogeneo para todos los supermercados, a utilizar para la surrogate key

# %%
mask_real = df['supermarket'] == 'real'

df.loc[mask_real, 'real_lvl1_clean'] = (
    df.loc[mask_real, 'category_lvl1_slug']
        .str.split('/', n=1)
        .str[-1]
)


# %%
df['category_slug_final'] = (
    np.where(df['supermarket'] == 'biggie', df['category_lvl1_slug'],
    np.where(df['supermarket'] == 'casa rica', df['category_lvl2_slug'],
    np.where(df['supermarket'].isin(['stock', 'super seis']), df['category_lvl3_slug'],
    np.where(df['supermarket'] == 'real', df['real_lvl1_clean'],
             None))))
)

# %%
df.head(1000)

# %% [markdown]
# ### category_final_name

# %% [markdown]
# Análisis

# %%
query = '''
SELECT
    supermarket,
	category_lvl1_name
FROM silver.categories
'''
print(query)

conn = connect_to_postgres()
if conn:
    df = read_table(query, conn)
    conn.close()

# %%
df.head()

# %%
pivot = (
    df
    .assign(value=True)          # Marcamos presencia
    .pivot_table(
        index='category_lvl1_name',
        columns='supermarket',
        values='value',
        aggfunc='any',           # Si existe al menos 1 → True
        fill_value=False
    )
)

pivot_int = pivot.astype(int)


# %%
# pivot_int.to_csv("/workspaces/tesis-ivan-gennaro/scripts/silver_staging/category_final_name_analisis.csv")

# %% [markdown]
# Aplicacion

# %%
def normalize_text(s):
    """
    Normaliza una cadena para matching:
      - pasa a minúsculas
      - quita acentos
      - reemplaza caracteres no alfanuméricos por espacio
      - reduce espacios múltiples a uno
      - strip()
    """
    if s is None:
        return None
    s = str(s).strip().lower()
    # quitar acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # deja solo letras, números y espacios
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    # colapsar espacios
    s = re.sub(r"\s+", " ", s).strip()
    return s


# %%
df['category_clean'] = df['category_lvl1_name'].apply(normalize_text)


# %%
# Leer mappings desde JSON
with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
    mappings = json.load(f)

inv_maps = {sup: {} for sup in ["biggie", "casa_rica", "real", "s6", "stock"]}

for final, mapping in mappings.items():
    for sup, cats in mapping.items():
        if cats is None:
            continue
        
        # Normalizar: convertir string -> lista de strings
        if isinstance(cats, str):
            cats = [cats]

        # Normalizar cada valor
        cats_norm = [normalize_text(c) for c in cats]

        # Guardar mapping categoria_super → categoria_final
        for c in cats_norm:
            inv_maps[sup][c] = final   # final NO normalizado, mejor para presentación


# %%
# 3) Mapear la categoría final
df['category_final'] = df.apply(
    lambda row: inv_maps[row['supermarket']].get(row['category_clean']),
    axis=1
)

# %%
df.drop_duplicates().to_csv("/workspaces/tesis-ivan-gennaro/scripts/silver_staging/category_final_name.csv")

# %%
df[df["category_final"].isna()][["supermarket", "category_lvl1_name", "category_clean"]].drop_duplicates()

# %%
df["category_final"].drop_duplicates()

# %%



