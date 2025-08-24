import time
import random
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path



BASE_WAIT = (1.0, 3.0)
def esperar():
    time.sleep(random.uniform(*BASE_WAIT))

def obtener_max_page_retail(tree):
    """
    USO EXCLUSIVO PARA SUPER SEIS Y STOCK, CADENA RETAIL.

    Obtiene el numero maximo de la paginacion disponible para una categoria de productos determinada.
    Navega el HTML resultante de una categoria dentro del e-commerce en busca de las etiquetas correspondientes.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.

    Returns:
        nums[dict]: Lista de productos enriquecidos.

    """
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

def obtener_max_page_casa_rica (tree):
    """Detectar el número máximo de páginas desde la paginación"""
    pages = [int(a.text(strip=True)) for a in tree.css("nav.ecommercepro-pagination a.page-numbers") if a.text(strip=True).isdigit()]
    return max(pages) if pages else 1

def extraer_productos_retail(tree, contexto, selectors=None):
    """
    USO EXCLUSIVO PARA SUPER SEIS Y STOCK, CADENA RETAIL.
    
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

def extraer_productos_casa_rica(tree, contexto, selectors):
    productos = []
    for nodo in tree.css(selectors["producto"]):
        titulo_node = nodo.css_first(selectors["titulo"])
        titulo = titulo_node.text(strip=True) if titulo_node else None

        precio = None

        # 1️⃣ Buscar precio de oferta (si existe y no está vacío)
        ins_node = nodo.css_first("span.price ins span.amount")
        if ins_node and ins_node.text(strip=True):
            precio = ins_node.text(strip=True)

        # 2️⃣ Si no hay oferta válida, buscar precio normal
        if not precio:
            for p in nodo.css("span.price span.amount"):
                txt = p.text(strip=True)
                if txt:
                    precio = txt
                    break

        productos.append({
            "titulo": titulo,
            "precio": precio,  # siempre el precio vigente (oferta o normal)
            "category_slug": contexto["category_slug"],
            "supermercado": contexto["supermercado"],
            "ingestion_time": contexto["ingestion_time"]
        })
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
