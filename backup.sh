#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  KYRONEX — Backup Complet du Système
#  Sauvegarde tous les fichiers critiques pour restauration
# ══════════════════════════════════════════════════════════════

set -e

KYRONEX_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$KYRONEX_DIR/BACKUP_$(date +%Y%m%d_%H%M%S)"

echo "══════════════════════════════════════════════════════════"
echo "  KYRONEX — Backup Complet"
echo "══════════════════════════════════════════════════════════"
echo ""

# Créer le dossier de backup
mkdir -p "$BACKUP_DIR"

echo "[1/10] Sauvegarde des scripts Python..."
cp -v kyronex_server.py "$BACKUP_DIR/"
cp -v piper_gpu.py "$BACKUP_DIR/"
cp -v terminal_chat.py "$BACKUP_DIR/"
cp -v monitor.py "$BACKUP_DIR/"
cp -v vision.py "$BACKUP_DIR/" 2>/dev/null || true

echo "[2/10] Sauvegarde des scripts shell..."
cp -v start_kyronex.sh "$BACKUP_DIR/"
cp -v backup.sh "$BACKUP_DIR/"

echo "[3/10] Sauvegarde de l'interface web..."
cp -rv static "$BACKUP_DIR/"

echo "[4/10] Sauvegarde des certificats SSL..."
cp -rv certs "$BACKUP_DIR/" 2>/dev/null || true

echo "[5/10] Sauvegarde du système driver..."
cp -rv driver "$BACKUP_DIR/" 2>/dev/null || true

echo "[6/10] Sauvegarde des données utilisateur..."
cp -v users.json "$BACKUP_DIR/" 2>/dev/null || echo "  (pas de users.json)"

echo "[7/10] Sauvegarde de la documentation..."
cp -v SUPER_NOTES.md "$BACKUP_DIR/" 2>/dev/null || true
cp -v README.md "$BACKUP_DIR/" 2>/dev/null || true
cp -v LICENSE "$BACKUP_DIR/" 2>/dev/null || true

echo "[8/10] Sauvegarde des dépendances Python..."
source venv/bin/activate
pip freeze > "$BACKUP_DIR/requirements.txt"
deactivate

echo "[9/10] Sauvegarde de la configuration système..."
cat > "$BACKUP_DIR/SYSTEM_INFO.txt" <<EOF
KYRONEX System Backup - $(date)
═══════════════════════════════════════════════

System:
- Jetson Orin Nano Super 8GB
- JetPack 6.2.2
- Ubuntu 22.04
- Python $(python3 --version)

Models:
- LLM: models/qwen2.5-3b-instruct-q5_k_m.gguf
- Whisper: models/whisper-base
- Piper: models/fr_FR-siwis-medium.onnx

Configuration:
- llama.cpp path: /home/kitt/llama.cpp/build/bin/llama-server
- CUDA: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo "N/A")
- Sox: $(sox --version 2>&1 | head -1)
- PulseAudio: $(pactl --version)

Backup créé: $(date)
EOF

echo "[10/10] Création de l'archive..."
cd "$KYRONEX_DIR"
tar -czf "$(basename $BACKUP_DIR).tar.gz" "$(basename $BACKUP_DIR)"
BACKUP_SIZE=$(du -sh "$(basename $BACKUP_DIR).tar.gz" | cut -f1)

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✅ BACKUP TERMINÉ!"
echo ""
echo "  📦 Archive: $(basename $BACKUP_DIR).tar.gz ($BACKUP_SIZE)"
echo "  📁 Dossier: $BACKUP_DIR"
echo ""
echo "  Pour restaurer: bash install_kyronex.sh restore <archive>"
echo "══════════════════════════════════════════════════════════"
