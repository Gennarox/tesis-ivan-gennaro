from curl_cffi import requests
from pydantic import ValidationError

import random
import time
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Union



# Lista de inmpersonates válidas
IMPERSONATE_OPTIONS = [
    "chrome99", "chrome100", "chrome101", "chrome104", "chrome107", "chrome110",
    "chrome116", "chrome119", "chrome120", "chrome123", "chrome124", "chrome131",
    "chrome133a", "chrome136", "chrome99_android", "chrome131_android",
    "edge99", "edge101", "safari153", "safari155", "safari170", "safari172_ios",
    "safari180", "safari180_ios", "safari184", "safari184_ios", "firefox133", "tor145"
]


class VPNTester:
    def __init__(self, impersonate="chrome120"):
        self.impersonate = impersonate

    def vpn_check(self):
        try:
            ip = requests.get("https://ipinfo.io/ip", impersonate=self.impersonate).text.strip()
            print(f"[🛡️  VPN Check] Your current IP: {ip}")
        except Exception as e:
            print(f"[❌] VPN Check failed: {e}")


class ScraperClient:
    def __init__(self, url: str, impersonate: str = None, random_wait: bool = False):
        self.url = url
        self.impersonate = impersonate or random.choice(IMPERSONATE_OPTIONS)
        self.random_wait = random_wait

    def get_json(self, method: str = "GET", payload: dict | list = None, headers: dict = None):
        try:
            if self.random_wait:
                wait_time = random.uniform(2.5, 10.0)
                print(f"[⏱️] Waiting {wait_time:.2f}s to simulate human behavior...")
                time.sleep(wait_time)

            print(f"[🎭 Impersonation] Using: {self.impersonate}")
            method = method.upper()

            # Headers por defecto para GraphQL
            default_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }

            # Si se proporcionan headers adicionales, combinarlos
            if headers:
                default_headers.update(headers)

            if method == "GET":
                response = requests.get(
                    url=self.url,
                    impersonate=self.impersonate,
                    headers=default_headers,
                    verify=True
                )
            elif method == "POST":
                response = requests.post(
                    url=self.url,
                    json=payload,
                    impersonate=self.impersonate,
                    headers=default_headers,
                    verify=True
                )
            else:
                raise ValueError("Unsupported HTTP method")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"[❌] Request failed: {e}")
            return None

    def parse_json_to_model(json_data: Union[dict, list], model_class, supermarket: str) -> list:
        """
        Converts JSON data into a list of Pydantic model instances.
        Accepts both list of dicts or dicts with 'items' key.

        Args:
            json_data (Union[dict, list]): Either a full response dict with 'items' key or a raw list of dicts.
            model_class: The Pydantic class to instantiate.
            supermarket (str): The name of the supermarket to attach.

        Returns:
            list: A list of validated model_class instances.
        """
        ingestion_time = datetime.now(ZoneInfo("America/Asuncion"))

        try:
            models = []

            # Determine if we were passed a dict with 'items' or a plain list
            if isinstance(json_data, dict):
                items = json_data.get("items", [])
            elif isinstance(json_data, list):
                items = json_data
            else:
                raise ValueError("json_data must be a dict with 'items' or a list of dicts.")

            for item in items:
                item_copy = item.copy()

                if "ingestion_time" not in item_copy and "ingestion_date" not in item_copy:
                    item_copy["ingestion_time"] = ingestion_time

                item_copy["supermarket"] = supermarket
                models.append(model_class(**item_copy))

            return models

        except ValidationError as e:
            print("[❌] Validation error during model creation:")
            print(e.errors())
            return []

        
    @staticmethod
    def save_json_raw(data: list[dict], supermarket: str, subfolder: str = "outputs", name: str = None):
        """
        Guarda una lista de diccionarios como archivo JSON formateado con timestamp.

        Args:
            data (list): Lista de diccionarios enriquecidos.
            supermarket (str): Nombre del supermercado (usado en el nombre del archivo).
            subfolder (str): Carpeta base de salida.
        """
        # Convertir datetime a string si existe
        for item in data:
            if isinstance(item.get("ingestion_time"), datetime):
                item["ingestion_time"] = item["ingestion_time"].isoformat()

        # Crear carpeta de salida
        output_dir = Path(f"{subfolder}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Crear nombre del archivo con timestamp
        timestamp_str = datetime.now(ZoneInfo("America/Asuncion")).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{supermarket.lower()}_{name}_{timestamp_str}.json"

        # Guardar
        with open(output_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[💾] Archivo guardado en: {output_dir / filename}")