import time
import random
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

"""
=========================================================
 Módulo: html_utils.py
 Autor: Iván Gennaro
 Descripción:
     Este archivo contiene funciones utilitarias para la
     extracción y procesamiento de datos HTML específicos
     de los supermercados **Super Seis**, **Stock** y 
     **Casa Rica** dentro del proceso de web scraping.

Observacion: 
    Las funciones con el sufijo retail aplican 
    únicamente a Super Seis y Stock, ambos pertenecientes 
    a la cadena retail. 
=========================================================
"""

BASE_WAIT = (1.0, 3.0)

def esperar():
    """
    Espera un tiempo aleatorio entre 1 y 3 segundos.

    Útil para evitar bloqueos al realizar múltiples requests 
    en el proceso de web scraping.
    """
    time.sleep(random.uniform(*BASE_WAIT))


def obtener_max_page_retail(tree):
    """
    Obtiene el número máximo de páginas disponibles 
    en la paginación de categorías para los supermercados 
    Super Seis y Stock.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.

    Returns:
        int: Número máximo de página encontrado (al menos 1).
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

def obtener_max_page_s6_new(tree):
    """
    Detecta el número máximo de páginas en la paginación del nuevo sitio de Super Seis.
    """
    paginador = tree.css("ul.pagination li a, ul.pagination li span")
    if not paginador:
        return 1

    nums = []
    for node in paginador:
        txt = node.text(strip=True)
        if txt.isdigit():
            nums.append(int(txt))

    return max(nums) if nums else 1


def obtener_max_page_casa_rica(tree):
    """
    Obtiene el número máximo de páginas disponibles 
    en la paginación de Casa Rica.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.

    Returns:
        int: Número máximo de página encontrado (al menos 1).
    """
    pages = [
        int(a.text(strip=True))
        for a in tree.css("nav.ecommercepro-pagination a.page-numbers")
        if a.text(strip=True).isdigit()
    ]
    return max(pages) if pages else 1


def extraer_productos_retail(tree, contexto, selectors=None):
    """
    Extrae productos de los supermercados Super Seis y Stock 
    desde un árbol HTML usando selectores CSS configurables.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.
        contexto (dict): Metadatos adicionales a incluir en cada producto.
        selectors (dict, opcional): Diccionario con los selectores CSS 
            para cada campo (producto, título, marca, precio, unidad de medida).
            Si no se proporciona, se usan valores por defecto.

    Returns:
        list[dict]: Lista de productos con sus campos y metadatos.
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
            marca = (
                prod.css_first(selectors["marca"]).text(strip=True)
                if prod.css_first(selectors["marca"])
                else ""
            )
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
    """
    Extrae productos del supermercado Casa Rica desde un árbol HTML.

    Busca primero precios de oferta (si existen) y en caso contrario 
    asigna el precio normal.

    Args:
        tree (HTMLTree): Árbol parseado con selectolax.
        contexto (dict): Metadatos adicionales a incluir en cada producto.
        selectors (dict): Diccionario con los selectores CSS 
            para cada campo (producto, título).

    Returns:
        list[dict]: Lista de productos con sus campos y metadatos.
    """
    productos = []
    for nodo in tree.css(selectors["producto"]):
        titulo_node = nodo.css_first(selectors["titulo"])
        titulo = titulo_node.text(strip=True) if titulo_node else None

        precio = None

        # Intentar primero con precio en oferta
        ins_node = nodo.css_first("span.price ins span.amount")
        if ins_node and ins_node.text(strip=True):
            precio = ins_node.text(strip=True)

        # Si no hay oferta válida, tomar precio normal
        if not precio:
            for p in nodo.css("span.price span.amount"):
                txt = p.text(strip=True)
                if txt:
                    precio = txt
                    break

        productos.append({
            "titulo": titulo,
            "precio": precio,
            "category_slug": contexto["category_slug"],
            "supermercado": contexto["supermercado"],
            "ingestion_time": contexto["ingestion_time"]
        })
    return productos

def extraer_productos_s6_new(tree, contexto, selectors=None):
    """
    Extrae productos del nuevo sitio de Super Seis.
    """
    productos = []

    # Buscar todos los productos en el grid
    for prod in tree.css("div.content"):
        try:
            titulo_node = prod.css_first("div.description h4 a[data-product-name]")
            precio_node = prod.css_first("div.price span.price-new")
            unidad_node = prod.css_first("span.sale-type-badge")

            titulo = titulo_node.text(strip=True) if titulo_node else None
            precio = precio_node.text(strip=True) if precio_node else None
            unidad = unidad_node.text(strip=True) if unidad_node else None

            productos.append({
                "titulo": titulo,
                "precio": precio,
                "unidad_medida": unidad,
                "marca": "",
                **contexto
            })
        except Exception as e:
            print(f"⚠️ Error al parsear producto: {e}")
            continue

    return productos



def save_df_as_csv(dataframe: pd.DataFrame, name: str, subfolder: str = ""):
    """
    Guarda un DataFrame como archivo CSV en la carpeta 
    `outputs/subfolder/`, incluyendo un timestamp en el nombre.

    Args:
        dataframe (pd.DataFrame): DataFrame a guardar.
        name (str): Nombre base del archivo.
        subfolder (str, opcional): Subcarpeta dentro de `outputs/`, 
            por ejemplo: "superseis/products".
    """
    base_path = Path(__file__).parent
    output_dir = base_path / "outputs" / subfolder
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{name}_{timestamp}.csv"

    file_path = output_dir / filename
    dataframe.to_csv(file_path, index=False)

    print(f"[💾] Guardado en: {file_path}")