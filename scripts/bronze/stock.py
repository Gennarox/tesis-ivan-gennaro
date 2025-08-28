# %%
# Librerías
import requests
import selectolax
from selectolax.parser import HTMLParser
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

# Funciones del proyecto
import scrapping_functions
from scrapping_functions import get_json_from_url, save_json, parse_json_to_model
import html_utils
from html_utils import esperar, obtener_max_page_retail, extraer_productos_retail, save_df_as_csv

# %% [markdown]
# ##### Categorias

# %%
response = requests.get("https://www.stock.com.py/default.aspx")
html = response.text
tree = HTMLParser(html)

# %%
data = []

# Buscar todos los nodos de nivel 1
for lvl1_li in tree.css("li.level1"):
    lvl1_a = lvl1_li.css_first("a")
    if not lvl1_a:
        continue
    lvl1_name = lvl1_a.text(strip=True)

    # Dentro de este <li>, buscar los hijos de nivel 2
    for lvl2_li in lvl1_li.css("ul > li.level2"):
        lvl2_a = lvl2_li.css_first("a")
        if not lvl2_a:
            continue
        lvl2_name = lvl2_a.text(strip=True)

        # Dentro del lvl2, buscar los hijos de nivel 3 (con enlaces)
        for lvl3_li in lvl2_li.css("ul > li.level3"):
            lvl3_a = lvl3_li.css_first("a[href]")
            if not lvl3_a:
                continue
            lvl3_name = lvl3_a.text(strip=True)
            lvl3_url = lvl3_a.attributes.get("href")

            data.append({
                "categoria_nivel_1": lvl1_name,
                "categoria_nivel_2": lvl2_name,
                "categoria_nivel_3": lvl3_name,
                "url": lvl3_url,
                "category_slug": f"{lvl1_name}/{lvl2_name}/{lvl3_name}".replace(" ", "_")
            })

# %%
df_categorias = pd.DataFrame(data)
df_categorias.nunique()

# %%
df_categorias.head()

# %%
save_df_as_csv(
    dataframe = df_categorias,
    name = 'stock_categorias',
    subfolder = 'stock/categorias'
)

# %% [markdown]
# # Productos

# %%
INGESTION_TIME = datetime.now(ZoneInfo("America/Asuncion"))
SUPERMERCADO = "Stock"
productos_final = []
selectors = {
    "producto": "div.producto",
    "titulo": "h2.product-title",
    "marca": "div.product-brand",
    "precio": "span.price-label",
    "unidad_medida": "span.unidad-medida",
    }

# 🔁 Iterar sobre cada categoría (nivel 3) con contexto
for _, row in df_categorias.iterrows():
    categoria_url = row["url"]
    category_slug = row["category_slug"]

    print(f"\n🔎 Scrapeando categoría: {category_slug}")
    esperar()
    
    response = requests.get(categoria_url)
    tree = HTMLParser(response.text)
    max_page = obtener_max_page_retail(tree)
    print(f"📄 Total de páginas: {max_page}")

    for page in range(1, max_page + 1):
        page_url = f"{categoria_url}?pageindex={page}"
        print(f"➡️ Página {page}: {page_url}")
        esperar()

        resp = requests.get(page_url)
        html_tree = HTMLParser(resp.text)

        contexto = {
            "category_slug": category_slug,
            "ingestion_time": INGESTION_TIME,
            "supermercado": SUPERMERCADO
        }

        productos_pagina = extraer_productos_retail(html_tree, contexto, selectors=selectors)
        productos_final.extend(productos_pagina)

# %%
df = pd.DataFrame(productos_final)
df.head(10)

# %%
save_df_as_csv(
    dataframe = df,
    name = 'stock_productos',
    subfolder = 'stock/productos'
)


