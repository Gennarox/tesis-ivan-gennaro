import subprocess

scripts = [
    ("Biggie", "biggie_refactorizado.py"),
    ("Supermecado Real", "real_refactorizado.py")
]

print("🚀 Iniciando orquestación de scrapers...\n")

for name, script in scripts:
    print(f"▶ Ejecutando {name}...")
    try:
        subprocess.run(["python3", script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[❌] Error ejecutando {name}: {e}")
    print("\n--------------------------------\n")

print("✅ Orquestación finalizada.")