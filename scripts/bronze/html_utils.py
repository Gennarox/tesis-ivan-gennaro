import time
import random
import pandas as pd


BASE_WAIT = (1.0, 3.0)
def esperar():
    time.sleep(random.uniform(*BASE_WAIT))

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

def save_df_as_csv(dataframe, path, filename):
    dataframe.to_csv(f"{path}/{filename}")
    return print(f"Dataframe guardado en ubicación {path}/{filename}")
