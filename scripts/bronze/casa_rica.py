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
import html_utils
from html_utils import esperar, obtener_max_page_casa_rica, extraer_productos_casa_rica, save_df_as_csv

# %% [markdown]
# ##### Categorias

# %%
response = requests.get("https://casarica.com.py/")
html = response.text
tree = HTMLParser(html)

# %%
data = [] 
for lvl1 in tree.css("a.dropdown-toggle"):
    lvl1_name = lvl1.text(strip=True)
    lvl1_url = lvl1.attributes.get("href", "")

    parent_li = lvl1.parent
    submenu = parent_li.css_first("ul.dropdown-menu")

    if not submenu: 
        data.append({
            "categoria_nivel_1": lvl1_name,
            "categoria_nivel_2": None,
            "url": lvl1_url,
            "category_slug": lvl1_name.replace(" ", "_")
        })
        continue

    for lvl2_li in submenu.css("li.menu-item"):
        lvl2_a = lvl2_li.css_first("a[href]")
        if not lvl2_a:
            continue

        lvl2_name = lvl2_a.text(strip=True)
        lvl2_url = lvl2_a.attributes.get("href")

        if "Ver todos" in lvl2_name:
            continue

        data.append({
            "categoria_nivel_1": lvl1_name,
            "categoria_nivel_2": lvl2_name,
            "url": lvl2_url,
            "category_slug": f"{lvl1_name}/{lvl2_name}".replace(" ", "_")
        })

# %%
df_categorias = pd.DataFrame(data)
df_categorias.nunique()

# %%
df_categorias.head()

# %%
save_df_as_csv(
    dataframe = df_categorias,
    name = 'casa_rica_categorias',
    subfolder = 'casa_rica/categorias'
)

# %% [markdown]
# # Productos

# %%
INGESTION_TIME = datetime.now(ZoneInfo("America/Asuncion"))
SUPERMERCADO = "Casa Rica"
productos_final = []
selectors = {
    "producto": "a.ecommercepro-LoopProduct-link",
    "titulo": "h2.ecommercepro-loop-product__title",
    "precio": "span.price span.amount"
}

for _, row in df_categorias.iterrows():
    categoria_url = row["url"]
    category_slug = row["category_slug"]

    print(f"\n🔎 Scrapeando categoría: {category_slug}")
    esperar()
    response = requests.get(f'https://casarica.com.py/catalogo/{categoria_url}')
    tree = HTMLParser(response.text)
    max_page = obtener_max_page_casa_rica(tree)
    print(f"📄 Total de páginas: {max_page}")

    for page in range(1, max_page + 1):
        page_url = f'https://casarica.com.py/catalogo/{categoria_url}' if page == 1 else f"https://casarica.com.py/catalogo/{categoria_url}.{page}"
        print(f"➡️ Página {page}: {page_url}")
        esperar()

        resp = requests.get(page_url)
        html_tree = HTMLParser(resp.text)

        contexto = {
            "category_slug": category_slug,
            "ingestion_time": INGESTION_TIME,
            "supermercado": SUPERMERCADO
        }

        productos_pagina = extraer_productos_casa_rica(html_tree, contexto, selectors=selectors)
        productos_final.extend(productos_pagina)

print(f"\n✅ Total de productos extraídos: {len(productos_final)}")

# %%
df = pd.DataFrame(productos_final)
df.head()

# %%
save_df_as_csv(
    dataframe = df,
    name = 'casa_rica_productos',
    subfolder = 'casa_rica/productos'
)


