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
from html_utils import esperar, obtener_max_page_s6_new, save_df_as_csv, extraer_productos_s6_new

# %% [markdown]
# ##### Categorias

# %%
response = requests.get("https://www.superseis.com.py/default.aspx")
html = response.text
tree = HTMLParser(html)

# %%
data = []

# 🔹 Buscar todas las categorías principales
for lvl1_li in tree.css("li.nav-item.dropdown-categories"):
    lvl1_a = lvl1_li.css_first("a.header-menu, a.dropdown-toggle-categories")
    if not lvl1_a:
        continue
    lvl1_name = lvl1_a.text(strip=True)

    # 🔹 Dentro de cada categoría principal, buscar subcategorías (nivel 2)
    for lvl2_li in lvl1_li.css("li.dropdown-submenu"):
        lvl2_a = lvl2_li.css_first("a.submenu-title[href]")
        if not lvl2_a:
            continue
        lvl2_name = lvl2_a.text(strip=True)
        lvl2_url = lvl2_a.attributes.get("href")

        # 🔹 Dentro de cada subcategoría, buscar sub-subcategorías (nivel 3)
        for lvl3_a in lvl2_li.css("ul.grand-child a[href]"):
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
print(f"✅ Total de categorías encontradas: {len(df_categorias)}")

# %%
df_categorias.head()

# %%
save_df_as_csv(
    dataframe = df_categorias,
    name = 'super_seis_categorias',
    subfolder = 'super_seis/categorias'
)

# %% [markdown]
# # Productos

# %%
INGESTION_TIME = datetime.now(ZoneInfo("America/Asuncion"))
SUPERMERCADO = "super_seis"
productos_final = []
selectors = {
    "producto": "div.content",
    "titulo": "div.description h4 a[data-product-name]",
    "precio": "div.price span.price-new",
    "unidad_medida": "span.sale-type-badge",
    "marca": "",  # No disponible actualmente
    }

for _, row in df_categorias.iterrows():
    categoria_url = row["url"]
    category_slug = row["category_slug"]

    print(f"\n🔎 Scrapeando categoría: {category_slug}")
    esperar()
    
    response = requests.get(categoria_url)
    tree = HTMLParser(response.text)
    max_page = obtener_max_page_s6_new(tree)
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

        productos_pagina = extraer_productos_s6_new(html_tree, contexto, selectors=selectors)
        productos_final.extend(productos_pagina)


# %%
df = pd.DataFrame(productos_final)
df.head()

# %%
save_df_as_csv(
    dataframe = df,
    name = 'super_seis_productos',
    subfolder = 'super_seis/productos'
)


