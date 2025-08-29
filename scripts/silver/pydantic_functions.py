import requests
import random
import time
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Union

"""
########################################################################################################
        Deprecar y mover a silver
########################################################################################################
"""

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