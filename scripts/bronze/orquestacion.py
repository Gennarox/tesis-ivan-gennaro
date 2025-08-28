import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Lista de scripts por supermercado
scripts = [
    ("Biggie", "biggie.py"),
    ("Supermecado Real", "real.py"),
    ("Super Seis", "s6.py"),
    ("Stock", "stock.py"),
    ("Casa Rica", "casa_rica.py")
]

print("🚀 Iniciando orquestación de scrapers...\n")

for name, script in scripts:
    print(f"▶ Ejecutando {name}...")

    success = False
    for attempt in range(1, 4):  # Hasta 3 intentos
        try:
            print(f"🔁 Intento {attempt} para {name}...")
            script_path = BASE_DIR / script
            subprocess.run(["python3", str(script_path)], check=True)
            print(f"✅ {name} finalizado correctamente.")
            success = True
            break  # Salir del loop si tuvo éxito
        except subprocess.CalledProcessError as e:
            print(f"[❌] Error en {name} (intento {attempt}/3): {e}")
            if attempt < 3:
                wait = 180  # segundos de espera entre intentos
                print(f"⏳ Esperando {wait}s antes de reintentar...\n")
                time.sleep(wait)
    
    if not success:
        print(f"[🛑] {name} falló tras 3 intentos. Continuando con el siguiente.\n")

    print("\n--------------------------------\n")

print("✅ Orquestación finalizada.")
