import requests
import random
import time
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import ValidationError
from typing import Union

# Opciones de User-Agent impersonation
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
    Realiza una solicitud HTTP (GET o POST) y devuelve el JSON parseado.

    Parámetros:
        url (str): URL a solicitar.
        method (str): 'GET' o 'POST'.
        payload (dict | list): Datos para enviar si el método es POST.
        use_random_wait (bool): Espera aleatoria antes de la solicitud.
        fixed_user_agent (str): User-Agent fijo (opcional).
        silent (bool): Si True, omite prints de log.

    Retorna:
        dict o None
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
    Guarda un archivo JSON en la carpeta outputs/subfolder/ con timestamp.

    Args:
        data (list or dict): Datos a guardar.
        name (str): Nombre base del archivo.
        subfolder (str): Ruta dentro de 'outputs/', por ejemplo: "biggie/categories"
    """
    base_path = Path(__file__).parent
    output_dir = base_path / "outputs" / subfolder
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convertir datetime a string si existe
    for item in data:
        if isinstance(item.get("ingestion_time"), datetime):
            item["ingestion_time"] = item["ingestion_time"].isoformat()

    timestamp = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{name}_{timestamp}.json"

    with open(output_dir / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[💾] Guardado en: {output_dir / filename}")

def parse_json_to_model(json_data: Union[dict, list], model_class, supermarket: str) -> list:
    """
    Convierte una respuesta JSON en una lista de instancias validadas del modelo Pydantic.
    """
    if not json_data:
        return []

    items = json_data.get("items") if isinstance(json_data, dict) else json_data
    if not isinstance(items, list):
        raise ValueError("json_data debe ser una lista o un diccionario con clave 'items'")

    ingestion_time = datetime.now(ZoneInfo("America/Asuncion"))

    models = []
    for item in items:
        enriched = {
            **item,
            "ingestion_time": item.get("ingestion_time") or ingestion_time,
            "supermarket": supermarket
        }

        try:
            models.append(model_class(**enriched))
        except ValidationError as e:
            print("[❌] Error de validación para item:")
            print(e.json(indent=2))

    return models
