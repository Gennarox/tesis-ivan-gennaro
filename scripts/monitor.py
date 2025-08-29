import os
import re
from pathlib import Path
import pandas as pd

# Lee rutas desde variables de entorno (defectos coherentes con el contenedor)
BASE_PATH = Path(os.getenv("INGESTIONS_DIR", "/app/ingestions"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "/app/logs"))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Patrón de filename esperado:
# ejemplo: biggie_categoria_2025-08-28_10-30.json
# tolera segundos opcionales: _HH-MM(-SS)?
FNAME_RE = re.compile(
    r"^(?P<supermercado>[a-zA-Z0-9\-]+)_(?P<dato>categoria|producto)_(?P<fecha>\d{4}-\d{2}-\d{2})_(?P<hora>\d{2}-\d{2}(?:-\d{2})?)\.(?P<ext>[a-zA-Z0-9]+)$"
)

print(f"[DEBUG] BASE_PATH = {BASE_PATH}")
print(f"[DEBUG] Contenido de {BASE_PATH}:")
for p in BASE_PATH.iterdir():
    print(" -", p)

"""
def parse_filename(fname: str):
    m = FNAME_RE.match(fname)
    if not m:
        return None
    d = m.groupdict()
    # Normalizar hora a HH:MM[:SS]
    hora = d["hora"].replace("-", ":")
    return {
        "supermercado": d["supermercado"],
        "fecha": d["fecha"],
        "hora": hora,
        "tipo_archivo": d["ext"],
        "dato": d["dato"],
        "archivo": fname,
    }

def build_monitor_dataframe(base_path: Path):
    if not base_path.exists():
        print(f"[WARN] Carpeta base no existe dentro del contenedor: {base_path}")
        return pd.DataFrame()

    registros = []
    # Recorre todo, por si tenés subcarpetas
    for p in base_path.rglob("*"):
        if p.is_file():
            parsed = parse_filename(p.name)
            if parsed:
                parsed["ruta_absoluta"] = str(p)
                registros.append(parsed)

    return pd.DataFrame(registros)

if __name__ == "__main__":
    print(f"[INFO] Escaneando: {BASE_PATH}")
    df = build_monitor_dataframe(BASE_PATH)
    print(df.head())

    out_csv = LOGS_DIR / "monitor_ingestas.csv"
    if df.empty:
        print("[WARN] DataFrame vacío: no se encontraron archivos con el patrón esperado.")
    df.to_csv(out_csv, index=False)
    print(f"[INFO] Monitor guardado en {out_csv}")
"""