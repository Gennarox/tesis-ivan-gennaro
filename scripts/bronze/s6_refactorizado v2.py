# %%
#import curl_cffi
#from curl_cffi import requests
#import scraper_functions
#from scraper_functions import VPNTester
import random, time
import selectolax
from selectolax.parser import HTMLParser
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

# %%
# Funciones del proyecto
import scrapping_functions
from scrapping_functions import get_json_from_url, save_json, parse_json_to_model

# %%
import requests

# %% [markdown]
# ##### Categorias

# %%
response = requests.get("https://www.superseis.com.py/default.aspx")

# %%
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
            })

# %%
df_categorias = pd.DataFrame(data)
df_categorias.head()
df_categorias.nunique()

# %% [markdown]
# # Productos

# %%
df_categorias.head()

# %%
BASE_WAIT = (2.0, 5.0)
def esperar():
    time.sleep(random.uniform(*BASE_WAIT))

# %%
def obtener_max_page(tree):
    paginador = tree.css("div.product-pager-box div")
    if not paginador:
        return 1
    nums = []
    for a in paginador[0].css("a"):
        try:
            nums.append(int(a.text(strip=True)))
        except ValueError:
            continue
    for span in paginador[0].css("span"):
        try:
            nums.append(int(span.text(strip=True)))
        except ValueError:
            continue
    return max(nums) if nums else 1

# %%
def extraer_productos(tree, contexto):
    productos = []
    for prod in tree.css("div.producto"):
        try:
            titulo = prod.css_first("h2.product-title").text(strip=True)
            marca = prod.css_first("div.product-brand").text(strip=True)
            precio = prod.css_first("span.price-label").text(strip=True)
            precio = prod.css_first("span.unidad-medida").text(strip=True)

            productos.append({
                "titulo": titulo,
                "marca": marca,
                "precio": precio,
                **contexto  # ← añadimos todos los metadatos de golpe
            })
        except AttributeError:
            continue
    return productos


# %%
INGESTION_TIME = datetime.now(ZoneInfo("America/Asuncion"))
SUPERMERCADO = "Super Seis"
productos_final = []

# 🔁 Iterar sobre cada categoría (nivel 3) con contexto
for _, row in df_categorias.iterrows():
    categoria_url = row["url"]
    cat1 = row["categoria_nivel_1"]
    cat2 = row["categoria_nivel_2"]
    cat3 = row["categoria_nivel_3"]

    print(f"\n🔎 Scrapeando categoría: {cat1} > {cat2} > {cat3}")
    esperar()
    
    response = requests.get(categoria_url)
    tree = HTMLParser(response.text)
    max_page = obtener_max_page(tree)
    print(f"📄 Total de páginas: {max_page}")

    for page in range(1, max_page + 1):
        page_url = f"{categoria_url}?pageindex={page}"
        print(f"➡️ Página {page}: {page_url}")
        esperar()

        resp = requests.get(page_url)
        html_tree = HTMLParser(resp.text)

        contexto = {
            "categoria_nivel_1": cat1,
            "categoria_nivel_2": cat2,
            "categoria_nivel_3": cat3,
            "url_categoria": categoria_url,
            "ingestion_time": INGESTION_TIME,
            "supermercado": SUPERMERCADO
        }

    productos_pagina = extraer_productos(html_tree, contexto)
    productos_final.extend(productos_pagina)


# %%
df = pd.DataFrame(productos_final)
df.head(10)

# %%
df.info()

# %%



