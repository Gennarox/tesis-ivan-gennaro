import requests
import random
import time
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Union

"""
=========================================================
 Módulo: api_utils.py
 Autor: Iván Gennaro
 Descripción:
     Este archivo contiene funciones utilitarias para 
     interactuar con APIs ocultas utilizadas en el 
     web scraping de los supermercados **Biggie**, 
     **Real**
=========================================================
"""

# Lista de User-Agents para rotación en las solicitudes
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/15.4 Safari/605.1.15"
]

def get_json_from_url(
    url: str,
    method: str = "GET",
    payload: Union[dict, list] = None,
    use_random_wait: bool = True,
    fixed_user_agent: str = None,
    silent: bool = False
):
    """
    Realiza una solicitud HTTP (GET o POST) y devuelve la respuesta en formato JSON.

    Args:
        url (str): URL a solicitar.
        method (str, opcional): Método HTTP. Puede ser "GET" o "POST". 
            Por defecto "GET".
        payload (dict | list, opcional): Datos para enviar si el método es POST.
        use_random_wait (bool, opcional): Si True, espera un tiempo aleatorio 
            antes de la solicitud (para evitar bloqueos). 
            Por defecto True.
        fixed_user_agent (str, opcional): User-Agent fijo para la solicitud.
        silent (bool, opcional): Si True, no muestra mensajes en consola.
            Por defecto False.

    Returns:
        dict | list | None: Respuesta en formato JSON, o None si ocurre un error.
    """
    method = method.upper()
    user_agent = fixed_user_agent or random.choice(USER_AGENTS)

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    if use_random_wait:
        wait_time = random.uniform(0, 5)
        if not silent:
            print(f"[⏱️] Esperando {wait_time:.2f}s...")
        time.sleep(wait_time)

    if not silent:
        print(f"[🌐] {method} → {url}")

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=60)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload, timeout=60)
        else:
            raise ValueError("Método HTTP no soportado: usa 'GET' o 'POST'.")

        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[❌] Error en la solicitud: {e}")
        return None


def save_json(data, name: str, subfolder: str = ""):
    """
    Guarda datos en un archivo JSON dentro de la carpeta 
    `outputs/subfolder/`, con un nombre que incluye un timestamp.

    Args:
        data (list | dict): Datos a guardar en el archivo JSON.
        name (str): Nombre base del archivo.
        subfolder (str, opcional): Subcarpeta dentro de `outputs/`, 
            por ejemplo: "biggie/categories".
    """
    base_path = Path(__file__).parent
    output_dir = base_path / "outputs" / subfolder
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convertir ingestion_time a string si existe en los datos
    for item in data:
        if isinstance(item.get("ingestion_time"), datetime):
            item["ingestion_time"] = item["ingestion_time"].isoformat()

    timestamp = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{name}_{timestamp}.json"

    with open(output_dir / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[💾] Guardado en: {output_dir / filename}")