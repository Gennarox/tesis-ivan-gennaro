# %%
# Librerías
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

# Funciones del proyecto
import scrapping_functions
from scrapping_functions import get_json_from_url, save_json

# %% [markdown]
# ##### Categorías

# %%
json_response = get_json_from_url(
    url = "https://api.app.biggie.com.py/api/classifications/web?take=-1&storeType="
)

# %%
save_json(
    data=json_response.get("items", []),
    name="biggie_categorias",
    subfolder="biggie/categorias"
)

# %%
if json_response:
    items = json_response.get("items", [])
    df = pd.DataFrame(items)
    df["ingestion_time"] = datetime.now(ZoneInfo("America/Asuncion"))
    df["supermarket"] = "biggie"

# %%
df.head()

# %% [markdown]
# ##### Productos

# %%
categories = df["slug"].unique()
np.random.shuffle(categories)
print(f"Number of categories -> {categories.size}")
categories

# %%
NOW = datetime.now(ZoneInfo("America/Asuncion"))
NumberResults = 24
BASE_URL = "https://api.app.biggie.com.py/api/articles"
all_items = []
total_calls = 0

for i, category in enumerate(categories, start=1):
    print(f"[{i}/{len(categories)}] Scrapeando categoría: {category}")
    skip = 0
    page = 1

    while True:
        url = (
            f"{BASE_URL}?take={NumberResults}&skip={skip}&classificationName={category}"
        )

        wait = random.uniform(1.0, 10.0)
        time.sleep(wait)

        try:
            data = get_json_from_url(
                url=url, 
                use_random_wait=True,
                fixed_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                silent=True
            )
        except Exception as e:
            print(f"[❌] Fallo en categoría {category}, skip={skip}: {e}")
            break

        items = data.get("items", [])
        total_calls += 1

        if not items:
            break

        for item in items:
            item["category"] = category
            item["ingestion_time"] = NOW

        all_items.extend(items)

        print(f"    ↳ Página {page}: {len(items)} productos")
        skip += NumberResults
        page += 1

print(f"\n✅ Fin del scraping: {len(all_items)} productos recolectados en {total_calls} requests.")

# %%
save_json(
    data=all_items,
    name="biggie_productos",
    subfolder="biggie/productos"
)


