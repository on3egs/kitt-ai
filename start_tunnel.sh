#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
# KITT Franco-Belge — Démarrage Tunnel Cloudflare + Auto-Update
# ══════════════════════════════════════════════════════════════════
# Usage:
#   chmod +x start_tunnel.sh
#   ./start_tunnel.sh
#   ./start_tunnel.sh --port 3000          # port local (défaut: 3000)
#   ./start_tunnel.sh --named MON_TUNNEL   # tunnel nommé cloudflare
# ══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Variables configurables ────────────────────────────────────────
LOCAL_PORT="${TUNNEL_PORT:-3000}"          # Port local du serveur KITT
CF_LOG="/tmp/cloudflared.log"              # Log cloudflared
UPDATER_LOG="/tmp/tunnel_updater.log"      # Log du script Python
UPDATER_PID_FILE="/tmp/tunnel_updater.pid"
CF_PID_FILE="/tmp/cloudflared.pid"
URL_TIMEOUT=30                             # secondes max pour détecter l'URL
NAMED_TUNNEL=""                            # Nom du tunnel nommé (optionnel)

# ── Charger les variables d'environnement ─────────────────────────
ENV_FILE="${HOME}/.env.tunnel"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
    echo "[INFO] Environnement chargé depuis $ENV_FILE"
fi

# ── Parse arguments ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)   LOCAL_PORT="$2"; shift 2 ;;
        --named)  NAMED_TUNNEL="$2"; shift 2 ;;
        *)        echo "Usage: $0 [--port PORT] [--named NOM_TUNNEL]"; exit 1 ;;
    esac
done

# ── Vérifications ─────────────────────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
    echo "[ERREUR] cloudflared non trouvé. Installer avec :"
    echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o /usr/local/bin/cloudflared"
    echo "  chmod +x /usr/local/bin/cloudflared"
    exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "[ERREUR] GITHUB_TOKEN non défini. Créer ~/.env.tunnel avec :"
    echo "  GITHUB_TOKEN=ghp_..."
    echo "  GITHUB_REPO=on3egs/Kitt-franco-belge"
    exit 1
fi

# ── Nettoyage des processus précédents ────────────────────────────
cleanup_previous() {
    echo "[INFO] Nettoyage des processus précédents..."

    if [[ -f "$CF_PID_FILE" ]]; then
        OLD_PID=$(cat "$CF_PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID" && echo "[INFO] cloudflared (PID $OLD_PID) arrêté"
        fi
        rm -f "$CF_PID_FILE"
    fi

    if [[ -f "$UPDATER_PID_FILE" ]]; then
        OLD_PID=$(cat "$UPDATER_PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID" && echo "[INFO] tunnel_updater (PID $OLD_PID) arrêté"
        fi
        rm -f "$UPDATER_PID_FILE"
    fi

    # Mise offline lors du nettoyage
    python3 "$(dirname "$0")/tunnel_updater.py" --offline 2>/dev/null || true
}

# Nettoyage au SIGTERM / SIGINT
trap 'cleanup_previous; echo "[INFO] Tunnel arrêté."; exit 0' SIGTERM SIGINT

cleanup_previous
rm -f "$CF_LOG"

# ── Démarrage de cloudflared ──────────────────────────────────────
echo ""
echo "  ██╗  ██╗██╗████████╗████████╗"
echo "  ██║ ██╔╝██║╚══██╔══╝╚══██╔══╝"
echo "  █████╔╝ ██║   ██║      ██║"
echo "  FRANCO-BELGE — TUNNEL CLOUDFLARE"
echo ""

if [[ -n "$NAMED_TUNNEL" ]]; then
    echo "[INFO] Démarrage tunnel nommé : $NAMED_TUNNEL"
    cloudflared tunnel \
        --metrics 127.0.0.1:8081 \
        run "$NAMED_TUNNEL" \
        > "$CF_LOG" 2>&1 &
else
    # Détection automatique HTTP/HTTPS selon présence des certs
    KITT_DIR="$(dirname "$(realpath "$0")")"
    if [[ -f "$KITT_DIR/certs/cert.pem" && -f "$KITT_DIR/certs/key.pem" ]]; then
        PROTO="https"
        echo "[INFO] Certificats SSL détectés — tunnel → https://localhost:$LOCAL_PORT"
    else
        PROTO="http"
        echo "[INFO] Pas de certificats — tunnel → http://localhost:$LOCAL_PORT"
    fi
    cloudflared tunnel \
        --metrics 127.0.0.1:8081 \
        --url "${PROTO}://localhost:${LOCAL_PORT}" \
        --no-tls-verify \
        > "$CF_LOG" 2>&1 &
fi

CF_PID=$!
echo "$CF_PID" > "$CF_PID_FILE"
echo "[INFO] cloudflared démarré (PID $CF_PID)"

# ── Attente et détection de l'URL ─────────────────────────────────
echo "[INFO] Attente de l'URL publique (max ${URL_TIMEOUT}s)..."
TUNNEL_URL=""

for i in $(seq 1 "$URL_TIMEOUT"); do
    # Chercher une URL Cloudflare dans le log
    if [[ -f "$CF_LOG" ]]; then
        # Pattern strict : uniquement domaines Cloudflare reconnus
        TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$CF_LOG" 2>/dev/null | tail -1 || true)
        if [[ -z "$TUNNEL_URL" ]]; then
            # Tunnels nommés : pattern cfargotunnel.com uniquement
            TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.cfargotunnel\.com' "$CF_LOG" 2>/dev/null | tail -1 || true)
        fi
    fi

    if [[ -n "$TUNNEL_URL" ]]; then
        break
    fi
    sleep 1
done

if [[ -n "$TUNNEL_URL" ]]; then
    echo ""
    echo "  ┌───────────────────────────────────────────────┐"
    echo "  │  TUNNEL ACTIF                                 │"
    echo "  │  URL : $TUNNEL_URL"
    echo "  └───────────────────────────────────────────────┘"
    echo ""
    # Exporter pour que tunnel_updater.py puisse la lire
    export CLOUDFLARE_TUNNEL_URL="$TUNNEL_URL"
else
    echo "[WARN] URL non détectée après ${URL_TIMEOUT}s — le script Python continuera à chercher"
fi

# ── Démarrage de l'updater Python ─────────────────────────────────
echo "[INFO] Démarrage tunnel_updater.py (daemon)..."

export GITHUB_TOKEN GITHUB_REPO CLOUDFLARE_TUNNEL_URL

python3 "$(dirname "$0")/tunnel_updater.py" \
    >> "$UPDATER_LOG" 2>&1 &

UPDATER_PID=$!
echo "$UPDATER_PID" > "$UPDATER_PID_FILE"
echo "[INFO] tunnel_updater démarré (PID $UPDATER_PID)"
echo "[INFO] Logs : tail -f $UPDATER_LOG"
echo ""
echo "[INFO] Ctrl+C pour arrêter proprement (mise offline automatique)"

# ── Attendre la fin des processus ─────────────────────────────────
wait "$CF_PID" "$UPDATER_PID"
