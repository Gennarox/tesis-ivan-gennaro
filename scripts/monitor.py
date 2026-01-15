import os
import pandas as pd
from pathlib import Path

BASE_PATH = Path("/app/ingestions") # ruta dentro del contenedor
IGNORE_DIRS = {'logs', 'pgdata'} # Carpetas a ignorar durante el escaneo

def parse_filename(filename: str):
    """
    Parsea el nombre del archivo en sus componentes.
    Estrategia: Divide de derecha a izquierda para manejar nombres de 
    supermercados que contengan guiones bajos (ej: super_seis).
    """
    name, ext = os.path.splitext(filename)
    
    parts = name.rsplit("_", 3)

    if len(parts) != 4:
        return None 

    supermercado = parts[0]
    dato = parts[1]         
    fecha = parts[2]        
    hora = parts[3].replace("-", ":")
    tipo_archivo = ext.lstrip(".")

    return {
        "supermercado": supermercado,
        "dato": dato,
        "fecha": fecha,
        "hora": hora,
        "tipo_archivo": tipo_archivo,
        "archivo": filename,
    }

def build_monitor_dataframe(base_path=BASE_PATH):
    registros = []
    print(f"[DEBUG] Escaneando: {base_path}")
    
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for f in files:
            parsed = parse_filename(f)
            if parsed:
                parsed['ruta_completa'] = os.path.join(root, f)
                registros.append(parsed)
            else:
                if not f.startswith('.'):
                    print(f"[DEBUG] Archivo ignorado: {f}")

    df = pd.DataFrame(registros)
    
    if df.empty:
        print("[WARN] DataFrame vacío: no se encontraron archivos con el patrón esperado.")
    else:
        df = df.sort_values(by=['fecha', 'hora'], ascending=False)
        
    return df

if __name__ == "__main__":
    df = build_monitor_dataframe()
    
    print("[INFO] Vista previa del DataFrame:")
    print(df[['supermercado', 'dato', 'fecha']].head(10))

    output_dir = Path("/app/logs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "monitor_ingestas.csv"
    df.to_csv(output_path, index=False)
    print(f"[INFO] Monitor guardado en {output_path}")