#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  K.I.T.T. Driver Recognition — Installer
#  Auteur : ByManix (Emmanuel Gelinne)
#  License: Elastic License 2.0 (ELv2)
#  Target: Jetson Orin Nano 8GB — JetPack 6.2.2 — Ubuntu 22.04
# ══════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
fail() { echo -e "  ${RED}[ERREUR]${NC} $1"; exit 1; }

DRIVER_DIR="$(cd "$(dirname "$0")" && pwd)"
KITT_DIR="$(dirname "$DRIVER_DIR")"
MODEL_DIR="$DRIVER_DIR/models"
FACE_DIR="$DRIVER_DIR/faces"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  K.I.T.T. Driver Recognition — Installation"
echo "══════════════════════════════════════════════════════════"
echo ""

# ── 1. System dependencies ───────────────────────────────────
echo "━━━ 1/5 : Dépendances système ━━━"

PKGS=""
command -v bluetoothctl &>/dev/null || PKGS="$PKGS bluez"
dpkg -s python3-opencv &>/dev/null 2>&1 || PKGS="$PKGS python3-opencv"
dpkg -s python3-numpy &>/dev/null 2>&1 || PKGS="$PKGS python3-numpy"
command -v paplay &>/dev/null || PKGS="$PKGS pulseaudio-utils"
command -v hcitool &>/dev/null || PKGS="$PKGS bluez-tools"

if [ -n "$PKGS" ]; then
    echo "  Installation :$PKGS"
    sudo apt-get update -qq
    sudo apt-get install -y $PKGS
fi
ok "Dépendances système OK"

# ── 2. Face detection/recognition models (OpenCV Zoo) ────────
echo ""
echo "━━━ 2/5 : Modèles de reconnaissance faciale ━━━"

mkdir -p "$MODEL_DIR"

YUNET="$MODEL_DIR/face_detection_yunet_2023mar.onnx"
SFACE="$MODEL_DIR/face_recognition_sface_2021dec.onnx"

if [ ! -f "$YUNET" ]; then
    echo "  Téléchargement YuNet face detector (~220 KB)..."
    curl -L -o "$YUNET" \
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ok "YuNet téléchargé"
else
    ok "YuNet déjà présent"
fi

if [ ! -f "$SFACE" ]; then
    echo "  Téléchargement SFace recognizer (~37 MB)..."
    curl -L -o "$SFACE" \
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ok "SFace téléchargé"
else
    ok "SFace déjà présent"
fi

# ── 3. Verify existing components ────────────────────────────
echo ""
echo "━━━ 3/5 : Vérification composants existants ━━━"

PIPER_BIN="$KITT_DIR/piper/piper/piper"
[ -f "$PIPER_BIN" ] && ok "Piper TTS trouvé" || fail "Piper TTS manquant dans $KITT_DIR/piper/"
[ -f "$KITT_DIR/models/fr_FR-tom-medium.onnx" ] && ok "Modèle TTS français trouvé" || fail "Modèle TTS manquant"

python3 -c "import cv2; assert hasattr(cv2, 'FaceDetectorYN')" 2>/dev/null \
    && ok "OpenCV FaceDetectorYN disponible" \
    || fail "OpenCV trop ancien — FaceDetectorYN requis (>= 4.5.4)"

python3 -c "import cv2; assert hasattr(cv2, 'FaceRecognizerSF')" 2>/dev/null \
    && ok "OpenCV FaceRecognizerSF disponible" \
    || fail "OpenCV FaceRecognizerSF manquant"

hcitool dev | grep -q hci \
    && ok "Adaptateur Bluetooth détecté" \
    || fail "Aucun adaptateur Bluetooth"

[ -e /dev/video0 ] && ok "Caméra détectée (/dev/video0)" || echo "  [WARN] Pas de caméra — branchez avant utilisation"

# ── 4. Permissions ────────────────────────────────────────────
echo ""
echo "━━━ 4/5 : Permissions ━━━"

chmod +x "$DRIVER_DIR/bluetooth_detect.sh"
chmod +x "$DRIVER_DIR/recognition.py"
chmod +x "$DRIVER_DIR/install.sh"
mkdir -p "$FACE_DIR"
ok "Permissions OK"

# ── 5. Systemd service ───────────────────────────────────────
echo ""
echo "━━━ 5/5 : Service systemd ━━━"

sudo cp "$DRIVER_DIR/kitt-driver.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kitt-driver.service
ok "Service kitt-driver.service installé et activé"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}INSTALLATION TERMINÉE${NC}"
echo ""
echo "  Prochaines étapes :"
echo ""
echo "  1. Configurez le MAC Bluetooth dans bluetooth_detect.sh :"
echo "     PHONE_MAC=\"XX:XX:XX:XX:XX:XX\""
echo ""
echo "  2. Enrôlez votre visage :"
echo "     python3 $DRIVER_DIR/recognition.py --enroll Manix"
echo ""
echo "  3. Testez la reconnaissance :"
echo "     python3 $DRIVER_DIR/recognition.py"
echo ""
echo "  4. Démarrez le service :"
echo "     sudo systemctl start kitt-driver.service"
echo ""
echo "══════════════════════════════════════════════════════════"
