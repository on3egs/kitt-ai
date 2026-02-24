#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  KYRONEX — Installation/Restauration Automatique Complète
#  Installation from scratch OU restauration depuis backup
# ══════════════════════════════════════════════════════════════

set -e

INSTALL_DIR="/home/kitt/kitt-ai"
SUDO_PASS="5505"

echo "══════════════════════════════════════════════════════════"
echo "  KYRONEX — Installation Automatique"
echo "  Jetson Orin Nano Super 8GB"
echo "══════════════════════════════════════════════════════════"
echo ""

# ── Mode de fonctionnement ────────────────────────────────────
if [ "$1" = "restore" ] && [ -n "$2" ]; then
    MODE="restore"
    BACKUP_ARCHIVE="$2"
    echo "🔄 MODE: Restauration depuis backup"
    echo "📦 Archive: $BACKUP_ARCHIVE"
else
    MODE="install"
    echo "🆕 MODE: Installation complète from scratch"
fi
echo ""

# ── Fonction d'installation des dépendances système ──────────
install_system_deps() {
    echo "[1/12] Installation des dépendances système..."
    echo "$SUDO_PASS" | sudo -S apt-get update -qq
    echo "$SUDO_PASS" | sudo -S apt-get install -y -qq \
        python3 python3-pip python3-venv \
        git curl wget \
        sox libsox-fmt-all \
        pulseaudio pulseaudio-utils \
        alsa-utils \
        build-essential cmake \
        libopencv-dev \
        bluez bluez-tools \
        cloudflared \
        > /dev/null 2>&1
    echo "  ✅ Dépendances système installées"
}

# ── Installation llama.cpp ────────────────────────────────────
install_llama_cpp() {
    echo "[2/12] Installation de llama.cpp avec CUDA..."
    if [ ! -d "/home/kitt/llama.cpp" ]; then
        cd /home/kitt
        git clone https://github.com/ggerganov/llama.cpp.git
        cd llama.cpp
        mkdir -p build && cd build
        cmake .. -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
        cmake --build . --config Release -j$(nproc)
        echo "  ✅ llama.cpp compilé avec CUDA"
    else
        echo "  ⏭️  llama.cpp déjà installé"
    fi
}

# ── Téléchargement des modèles ────────────────────────────────
download_models() {
    echo "[3/12] Téléchargement des modèles..."
    mkdir -p "$INSTALL_DIR/models"
    cd "$INSTALL_DIR/models"

    # LLM Qwen 2.5 3B
    if [ ! -f "qwen2.5-3b-instruct-q5_k_m.gguf" ]; then
        echo "  📥 Téléchargement LLM (Qwen 2.5 3B)... (~2.3GB)"
        wget -q --show-progress https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q5_k_m.gguf
    else
        echo "  ⏭️  LLM déjà téléchargé"
    fi

    # Whisper base
    if [ ! -d "whisper-base" ]; then
        echo "  📥 Téléchargement Whisper base... (~500MB)"
        wget -q --show-progress https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt -O base.pt
        mkdir -p whisper-base
        mv base.pt whisper-base/
    else
        echo "  ⏭️  Whisper déjà téléchargé"
    fi

    # Piper voice model
    if [ ! -f "fr_FR-siwis-medium.onnx" ]; then
        echo "  📥 Téléchargement Piper FR (siwis-medium)... (~50MB)"
        wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx
        wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json
    else
        echo "  ⏭️  Piper déjà téléchargé"
    fi

    echo "  ✅ Modèles prêts"
}

# ── Création du venv et installation Python ──────────────────
setup_python_env() {
    echo "[4/12] Configuration de l'environnement Python..."
    cd "$INSTALL_DIR"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    source venv/bin/activate

    if [ -f "requirements.txt" ]; then
        echo "  📦 Installation des dépendances Python..."
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
    else
        echo "  📦 Installation des dépendances Python de base..."
        pip install -q --upgrade pip
        pip install -q \
            aiohttp \
            numpy \
            onnxruntime-gpu \
            openai-whisper \
            opencv-python \
            phonemizer \
            ultralytics \
            websockets
    fi

    deactivate
    echo "  ✅ Environnement Python prêt"
}

# ── Création des certificats SSL ──────────────────────────────
create_ssl_certs() {
    echo "[5/12] Création des certificats SSL..."
    mkdir -p "$INSTALL_DIR/certs"
    cd "$INSTALL_DIR/certs"

    if [ ! -f "cert.pem" ]; then
        openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
            -days 365 -nodes -subj "/CN=kyronex.local" > /dev/null 2>&1
        echo "  ✅ Certificats SSL créés"
    else
        echo "  ⏭️  Certificats SSL déjà présents"
    fi
}

# ── Création des dossiers ──────────────────────────────────────
create_directories() {
    echo "[6/12] Création des dossiers..."
    mkdir -p "$INSTALL_DIR/audio_cache"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/static"
    echo "  ✅ Dossiers créés"
}

# ── Restauration depuis backup ────────────────────────────────
restore_from_backup() {
    echo "[7/12] Restauration depuis le backup..."

    # Extraire l'archive
    TEMP_DIR=$(mktemp -d)
    tar -xzf "$BACKUP_ARCHIVE" -C "$TEMP_DIR"
    BACKUP_FOLDER=$(ls "$TEMP_DIR")

    # Copier les fichiers
    cp -v "$TEMP_DIR/$BACKUP_FOLDER"/*.py "$INSTALL_DIR/" 2>/dev/null || true
    cp -v "$TEMP_DIR/$BACKUP_FOLDER"/*.sh "$INSTALL_DIR/" 2>/dev/null || true
    cp -v "$TEMP_DIR/$BACKUP_FOLDER"/*.md "$INSTALL_DIR/" 2>/dev/null || true
    cp -v "$TEMP_DIR/$BACKUP_FOLDER"/LICENSE "$INSTALL_DIR/" 2>/dev/null || true
    cp -v "$TEMP_DIR/$BACKUP_FOLDER"/users.json "$INSTALL_DIR/" 2>/dev/null || true
    cp -rv "$TEMP_DIR/$BACKUP_FOLDER"/static/* "$INSTALL_DIR/static/" 2>/dev/null || true
    cp -rv "$TEMP_DIR/$BACKUP_FOLDER"/certs/* "$INSTALL_DIR/certs/" 2>/dev/null || true
    cp -rv "$TEMP_DIR/$BACKUP_FOLDER"/driver "$INSTALL_DIR/" 2>/dev/null || true

    # Requirements.txt pour l'installation Python
    if [ -f "$TEMP_DIR/$BACKUP_FOLDER/requirements.txt" ]; then
        cp "$TEMP_DIR/$BACKUP_FOLDER/requirements.txt" "$INSTALL_DIR/"
    fi

    rm -rf "$TEMP_DIR"
    echo "  ✅ Fichiers restaurés depuis backup"
}

# ── Téléchargement des fichiers depuis GitHub ─────────────────
download_from_github() {
    echo "[7/12] Téléchargement des fichiers KYRONEX..."

    # Note: Adapter ces URLs si vous avez un repo GitHub
    # Pour l'instant, on suppose que les fichiers sont déjà en place
    # ou seront restaurés depuis un backup

    echo "  ⚠️  Mode installation: Fichiers doivent être présents dans $INSTALL_DIR"
    echo "  💡 Utilisez 'restore' avec un backup pour restaurer les fichiers"
}

# ── Configuration des permissions ──────────────────────────────
set_permissions() {
    echo "[8/12] Configuration des permissions..."
    chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
    chmod +x "$INSTALL_DIR"/driver/*.sh 2>/dev/null || true
    echo "  ✅ Permissions configurées"
}

# ── Installation du driver system ──────────────────────────────
install_driver() {
    echo "[9/12] Installation du système driver..."
    if [ -d "$INSTALL_DIR/driver" ] && [ -f "$INSTALL_DIR/driver/install.sh" ]; then
        cd "$INSTALL_DIR/driver"
        bash install.sh
        echo "  ✅ Driver installé"
    else
        echo "  ⏭️  Pas de driver à installer"
    fi
}

# ── Configuration PulseAudio ───────────────────────────────────
configure_audio() {
    echo "[10/12] Configuration audio (PulseAudio)..."
    # Démarrer PulseAudio si pas actif
    pulseaudio --check || pulseaudio --start
    echo "  ✅ PulseAudio configuré"
}

# ── Test du système ────────────────────────────────────────────
test_system() {
    echo "[11/12] Test du système..."

    # Test sox
    if command -v sox &> /dev/null; then
        echo "  ✅ Sox installé"
    else
        echo "  ❌ Sox manquant"
    fi

    # Test paplay
    if command -v paplay &> /dev/null; then
        echo "  ✅ PulseAudio (paplay) installé"
    else
        echo "  ❌ PulseAudio manquant"
    fi

    # Test llama.cpp
    if [ -f "/home/kitt/llama.cpp/build/bin/llama-server" ]; then
        echo "  ✅ llama.cpp compilé"
    else
        echo "  ❌ llama.cpp manquant"
    fi

    # Test Python venv
    if [ -d "$INSTALL_DIR/venv" ]; then
        echo "  ✅ Python venv créé"
    else
        echo "  ❌ Python venv manquant"
    fi
}

# ── Résumé final ───────────────────────────────────────────────
print_summary() {
    echo "[12/12] Installation terminée!"
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  ✅ KYRONEX INSTALLÉ ET PRÊT!"
    echo "══════════════════════════════════════════════════════════"
    echo ""
    echo "📍 Dossier: $INSTALL_DIR"
    echo ""
    echo "🚀 Pour démarrer KYRONEX:"
    echo "   cd $INSTALL_DIR"
    echo "   bash start_kyronex.sh"
    echo ""
    echo "💾 Pour créer un backup:"
    echo "   bash backup.sh"
    echo ""
    echo "📱 Interface web (après démarrage):"
    echo "   https://192.168.1.32:3000"
    echo ""
    echo "🖥️  Terminal chat:"
    echo "   venv/bin/python3 terminal_chat.py"
    echo ""
    echo "══════════════════════════════════════════════════════════"
}

# ══════════════════════════════════════════════════════════════
#  EXÉCUTION PRINCIPALE
# ══════════════════════════════════════════════════════════════

cd "$INSTALL_DIR"

install_system_deps
install_llama_cpp
download_models

if [ "$MODE" = "restore" ]; then
    restore_from_backup
else
    download_from_github
fi

create_ssl_certs
create_directories
setup_python_env
set_permissions
install_driver
configure_audio
test_system
print_summary

echo ""
echo "🎉 Installation terminée avec succès!"
echo ""
