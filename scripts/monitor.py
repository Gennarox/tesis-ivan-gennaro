import os
import pandas as pd
from pathlib import Path

# Ruta a tu carpeta de ingestas
BASE_PATH = Path.home() / "docker-data/webscrapping-tesis"

def parse_filename(filename: str):
    """
    Parsea el nombre del archivo en sus componentes.
    Espera formato: supermercado_tipo_fecha_hora.ext
    Ejemplo: biggie_categoria_2025-08-28_10-30.json
    """
    name, ext = os.path.splitext(filename)
    parts = name.split("_")

    if len(parts) < 4:
        return None  # no cumple el formato esperado

    supermercado = parts[0]
    dato = parts[1]  # categoria o producto
    fecha = parts[2]
    hora = parts[3].replace("-", ":")  # ej: 10-30 → 10:30
    tipo_archivo = ext.lstrip(".")

    return {
        "supermercado": supermercado,
        "fecha": fecha,
        "hora": hora,
        "tipo_archivo": tipo_archivo,
        "dato": dato,
        "archivo": filename,
    }

def build_monitor_dataframe(base_path=BASE_PATH):
    registros = []
    for root, _, files in os.walk(base_path):
        for f in files:
            parsed = parse_filename(f)
            if parsed:
                registros.append(parsed)

    df = pd.DataFrame(registros)
    return df

if __name__ == "__main__":
    df = build_monitor_dataframe()
    print(df.head())
    
    # Guardar CSV de control
    output_path = BASE_PATH / "monitor_ingestas.csv"
    df.to_csv(output_path, index=False)
    print(f"Monitor guardado en {output_path}")
