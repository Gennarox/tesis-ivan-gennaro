import time
import random
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path



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

def extraer_productos(tree, contexto, selectors=None):
    """
    Extrae productos desde un árbol HTML usando selectores CSS configurables.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.
        contexto (dict): Diccionario con metadatos que se agregarán a cada producto.
        selectors (dict): Diccionario con los selectores CSS para cada campo.

    Returns:
        list[dict]: Lista de productos enriquecidos.
    """
    if selectors is None:
        selectors = {
            "producto": "div.producto",
            "titulo": "h2.product-title",
            "marca": "div.product-brand",
            "precio": "span.price-label",
            "unidad_medida": "span.unidad-medida",
        }

    productos = []
    for prod in tree.css(selectors["producto"]):
        try:
            titulo = prod.css_first(selectors["titulo"]).text(strip=True)
            marca = prod.css_first(selectors["marca"]).text(strip=True) if prod.css_first(selectors["marca"]) else ""
            precio = prod.css_first(selectors["precio"]).text(strip=True)
            unidad_medida = prod.css_first(selectors["unidad_medida"]).text(strip=True)

            productos.append({
                "titulo": titulo,
                "marca": marca,
                "precio": precio,
                "unidad_medida": unidad_medida,
                **contexto
            })
        except AttributeError:
            continue
    return productos

def save_df_as_csv(dataframe: pd.DataFrame, name: str, subfolder: str = ""):
    """
    Guarda un DataFrame como archivo CSV en la carpeta outputs/subfolder/ con timestamp.

    Args:
        dataframe (pd.DataFrame): DataFrame a guardar.
        name (str): Nombre base del archivo.
        subfolder (str): Ruta dentro de 'outputs/', por ejemplo: "superseis/products"
    """
    base_path = Path(__file__).parent
    output_dir = base_path / "outputs" / subfolder
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{name}_{timestamp}.csv"

    file_path = output_dir / filename
    dataframe.to_csv(file_path, index=False)

    print(f"[💾] Guardado en: {file_path}")
