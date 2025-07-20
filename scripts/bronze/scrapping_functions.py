import requests
import random
import time
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# Opciones de User-Agent impersonation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/15.4 Safari/605.1.15"
]

def get_json_from_url(url, use_random_wait=True):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    if use_random_wait:
        wait_time = random.uniform(2.5, 8.0)
        print(f"[⏱️] Esperando {wait_time:.2f}s para simular comportamiento humano...")
        time.sleep(wait_time)

    try:
        print(f"[🌐] Solicitando: {url}")
        response = requests.get(url, headers=headers, timeout=15)
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

    timestamp = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{name}_{timestamp}.json"

    with open(output_dir / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[💾] Guardado en: {output_dir / filename}")