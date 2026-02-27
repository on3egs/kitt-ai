#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  KYRONEX — Kinetic Yielding Responsive Onboard Neural EXpert
#  Script de démarrage — Jetson Orin Nano Super
# ══════════════════════════════════════════════════════════════

set -e

KYRONEX_DIR="$(cd "$(dirname "$0")" && pwd)"
LLAMA_SERVER="/home/kitt/llama.cpp/build/bin/llama-server"
MODEL="$KYRONEX_DIR/models/qwen2.5-3b-instruct-q5_k_m.gguf"
VENV="$KYRONEX_DIR/venv/bin/activate"

export HF_HUB_OFFLINE=1

echo "══════════════════════════════════════════════════════════"
echo "  KITT — Knight Industries Two Thousand"
echo "  By Manix — Démarrage du système..."
echo "══════════════════════════════════════════════════════════"

# ── Libérer la RAM ────────────────────────────────────────
echo "[...] Libération de la mémoire..."

# Fermer les navigateurs (gourmands en RAM/VRAM)
pkill -f "chrome" 2>/dev/null || true
pkill -f "chromium" 2>/dev/null || true
pkill -f "firefox" 2>/dev/null || true

# Arrêter les instances précédentes de KYRONEX
pkill -f "llama-server" 2>/dev/null || true
pkill -f "kyronex_server" 2>/dev/null || true
sleep 1

# Vider les caches et le swap pour tout remettre en RAM
sync
echo "5505" | sudo -S sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true
echo "5505" | sudo -S swapoff -a 2>/dev/null && echo "5505" | sudo -S swapon -a 2>/dev/null || true
echo "[OK] Mémoire libérée"

# Activer les performances max
echo "5505" | sudo -S jetson_clocks 2>/dev/null || true
echo "[OK] Performances maximales activées"

# Démarrer llama.cpp server avec CUDA
echo "[...] Démarrage du serveur LLM (Qwen 2.5 3B)..."
export LD_LIBRARY_PATH="/home/kitt/CTranslate2/install/lib:/home/kitt/llama.cpp/build/bin:/home/kitt/llama.cpp/build/ggml/src:$LD_LIBRARY_PATH"
$LLAMA_SERVER \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port 8080 \
    --n-gpu-layers 99 \
    --ctx-size 1536 \
    --batch-size 512 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --threads 6 \
    --parallel 1 \
    --flash-attn on \
    &

LLM_PID=$!
echo "[OK] LLM PID: $LLM_PID"

# Attendre que le LLM soit prêt
echo "[...] Attente du LLM..."
LLM_READY=0
for i in $(seq 1 60); do
    if ! kill -0 "$LLM_PID" 2>/dev/null; then
        echo "[ERREUR] LLM s'est arrêté prématurément (OOM ou modèle manquant)!"
        exit 1
    fi
    if curl -s http://127.0.0.1:8080/health | grep -q "ok"; then
        echo "[OK] LLM prêt en ${i}s!"
        LLM_READY=1
        break
    fi
    sleep 1
done
if [ "$LLM_READY" = "0" ]; then
    echo "[ERREUR] LLM n'a pas démarré après 60s!"
    kill "$LLM_PID" 2>/dev/null || true
    exit 1
fi

# Démarrer le serveur KYRONEX
echo "[...] Démarrage du serveur KITT..."
source "$VENV"
cd "$KYRONEX_DIR"
"$KYRONEX_DIR/venv/bin/python3" kyronex_server.py &
KYRONEX_PID=$!

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  KITT EST EN LIGNE"
echo ""
echo "  Interface web : https://$(hostname -I | awk '{print $1}'):3000"
echo "  (Ouvrir depuis iPhone/tablette — pas de navigateur sur le Jetson !)"
echo "  API Chat      : http://$(hostname -I | awk '{print $1}'):3000/api/chat"
echo "  API Santé     : http://$(hostname -I | awk '{print $1}'):3000/api/health"
echo "  LLM Server    : http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "  PID LLM     : $LLM_PID"
echo "  PID KITT    : $KYRONEX_PID"
echo "══════════════════════════════════════════════════════════"

# ── Tunnel public (optionnel) ─────────────────────────────
if [ "${TUNNEL:-0}" = "1" ]; then
    export KYRONEX_PASSWORD="${KYRONEX_PASSWORD:-1982}"
    echo ""
    echo "[...] Ouverture du tunnel Cloudflare..."
    echo "  Mot de passe d'accès : $KYRONEX_PASSWORD"
    cloudflared tunnel --url https://localhost:3000 --no-tls-verify &
    TUNNEL_PID=$!
    echo "  PID Tunnel : $TUNNEL_PID"
    echo "  Le lien public s'affichera ci-dessous..."
    echo ""
fi

# ── Surveillance des processus — sortie non-zero si crash ─────
echo "[...] Surveillance des processus (PID LLM=$LLM_PID, KYRONEX=$KYRONEX_PID)..."
while true; do
    if ! kill -0 "$LLM_PID" 2>/dev/null; then
        echo "[FATAL] llama-server (PID $LLM_PID) s'est arrêté — redémarrage systemd..."
        kill "$KYRONEX_PID" 2>/dev/null || true
        [ -n "${TUNNEL_PID:-}" ] && kill "$TUNNEL_PID" 2>/dev/null || true
        exit 1
    fi
    if ! kill -0 "$KYRONEX_PID" 2>/dev/null; then
        echo "[FATAL] kyronex_server (PID $KYRONEX_PID) s'est arrêté — redémarrage systemd..."
        kill "$LLM_PID" 2>/dev/null || true
        [ -n "${TUNNEL_PID:-}" ] && kill "$TUNNEL_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 5
done
