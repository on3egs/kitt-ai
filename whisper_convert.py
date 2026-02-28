#!/usr/bin/env python3
"""
KITT — Conversion du modele Whisper fine-tune → CTranslate2
A lancer sur le Jetson apres avoir telecharge whisper-kitt-manix.zip depuis Colab.

Usage :
  1. Copie whisper-kitt-manix.zip dans /home/kitt/kitt-ai/
  2. python3 whisper_convert.py
  3. Redemarrer kyronex : sudo systemctl restart kitt-kyronex.service
"""

import os
import sys
import subprocess
import zipfile
import shutil

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ZIP_FILE   = os.path.join(BASE_DIR, "whisper-kitt-manix.zip")
SRC_DIR    = os.path.join(BASE_DIR, "whisper-kitt-manix")
OUTPUT_DIR = os.path.join(BASE_DIR, "models", "whisper-kitt-manix-ct2")
VENV_PY    = os.path.join(BASE_DIR, "venv", "bin", "python3")

def run(cmd, env=None):
    e = os.environ.copy()
    e["LD_LIBRARY_PATH"] = "/home/kitt/CTranslate2/install/lib"
    if env:
        e.update(env)
    result = subprocess.run(cmd, shell=True, env=e)
    if result.returncode != 0:
        print(f"ERREUR: {cmd}")
        sys.exit(1)

print("=" * 60)
print("  KITT — Conversion Whisper fine-tune → CTranslate2")
print("=" * 60)

# 1. Extraire le zip si necessaire
if not os.path.isdir(SRC_DIR):
    if not os.path.exists(ZIP_FILE):
        print(f"\nERREUR : {ZIP_FILE} introuvable.")
        print("Telecharge whisper-kitt-manix.zip depuis Google Colab et copie-le ici.")
        sys.exit(1)
    print(f"\n[1/3] Extraction de {ZIP_FILE}...")
    with zipfile.ZipFile(ZIP_FILE, "r") as z:
        z.extractall(BASE_DIR)
    print("    OK")
else:
    print(f"\n[1/3] Dossier {SRC_DIR} deja present, extraction ignoree.")

# 2. Convertir avec ct2-transformers-converter
print(f"\n[2/3] Conversion vers CTranslate2 (float16)...")
print(f"    Source  : {SRC_DIR}")
print(f"    Sortie  : {OUTPUT_DIR}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

run(
    f"LD_LIBRARY_PATH=/home/kitt/CTranslate2/install/lib "
    f"{VENV_PY} -m ctranslate2.converters.transformers "
    f"--model {SRC_DIR} "
    f"--output_dir {OUTPUT_DIR} "
    f"--quantization float16 "
    f"--force"
)
print("    OK")

# 3. Mettre a jour kyronex_server.py pour utiliser le nouveau modele
SERVER_FILE = os.path.join(BASE_DIR, "kyronex_server.py")
print(f"\n[3/3] Mise a jour de kyronex_server.py...")

with open(SERVER_FILE, "r") as f:
    content = f.read()

old1 = 'whisper_model = WhisperModel("small", device="cuda", compute_type="float16")'
new1 = f'whisper_model = WhisperModel("{OUTPUT_DIR}", device="cuda", compute_type="float16")'

old2 = 'whisper_model = WhisperModel("small", device="cpu", compute_type="float32")'
new2 = f'whisper_model = WhisperModel("{OUTPUT_DIR}", device="cpu", compute_type="float32")'

old3 = 'print("[OK] Whisper prêt (GPU CUDA float16 - small)"'
new3 = 'print("[OK] Whisper prêt (GPU CUDA float16 - kitt-manix)"'

old4 = 'print("[OK] Whisper prêt (CPU float32 fallback - small)"'
new4 = 'print("[OK] Whisper prêt (CPU float32 fallback - kitt-manix)"'

if old1 not in content:
    print("    ATTENTION : modele deja mis a jour ou kyronex_server.py modifie.")
else:
    content = content.replace(old1, new1).replace(old2, new2)
    content = content.replace(old3, new3).replace(old4, new4)
    with open(SERVER_FILE, "w") as f:
        f.write(content)
    print("    kyronex_server.py mis a jour.")

print("\n" + "=" * 60)
print("  Conversion terminee !")
print("=" * 60)
print(f"\nModele CTranslate2 : {OUTPUT_DIR}")
print("\nRedemarrer kyronex pour utiliser le nouveau modele :")
print("  echo '5505' | sudo -S systemctl restart kitt-kyronex.service")
print("\nVerifier les logs :")
print("  journalctl -u kitt-kyronex.service -f | grep Whisper")
