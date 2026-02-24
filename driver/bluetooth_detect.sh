#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  K.I.T.T. — Détection Bluetooth du conducteur
#  Détecte le téléphone du propriétaire, lance la reconnaissance.
#
#  Auteur : ByManix (Emmanuel Gelinne)
#  Licence : Elastic License 2.0 (ELv2)
#  Cible : Jetson Orin Nano 8GB — Ubuntu 22.04
# ══════════════════════════════════════════════════════════════

# ── Configuration ─────────────────────────────────────────────
# Adresse MAC Bluetooth du téléphone du propriétaire
PHONE_MAC="E0:33:8E:4B:75:AE"

# Intervalle entre les scans (secondes)
SCAN_INTERVAL=5

# Délai avant re-scan après reconnaissance réussie (secondes)
COOLDOWN=300
# ──────────────────────────────────────────────────────────────

DRIVER_DIR="$(cd "$(dirname "$0")" && pwd)"
RECOGNITION="$DRIVER_DIR/recognition.py"
PYTHON="python3"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

detect_phone() {
    # Méthode 1 : résolution de nom (Bluetooth classique) — timeout augmenté pour iPhone
    local name
    name=$(timeout 8 hcitool name "$PHONE_MAC" 2>/dev/null)
    if [ -n "$name" ]; then
        return 0
    fi
    # Méthode 2 : vérification via bluetoothctl (appareil appairé)
    if bluetoothctl info "$PHONE_MAC" 2>/dev/null | grep -q "Connected: yes"; then
        return 0
    fi
    return 1
}

log "K.I.T.T. Détection Bluetooth active"
log "Recherche de : $PHONE_MAC"
log "Intervalle : ${SCAN_INTERVAL}s"

LLM_ACTIVE=false
RUNNING=true

# Arrêt propre sur SIGTERM/SIGINT
cleanup() {
    log "Signal reçu — arrêt propre..."
    RUNNING=false
    pkill -f "llama-server" 2>/dev/null || true
    pkill -f "kyronex_server" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

while $RUNNING; do
    if detect_phone; then
        if [ "$LLM_ACTIVE" = false ]; then
            log "Téléphone détecté ! Lancement reconnaissance faciale..."
            if $PYTHON "$RECOGNITION"; then
                log "Conducteur reconnu. Système actif."
                LLM_ACTIVE=true
                sleep "$COOLDOWN"
            else
                log "Reconnaissance échouée. Nouvelle tentative dans ${SCAN_INTERVAL}s."
            fi
        fi
    else
        if [ "$LLM_ACTIVE" = true ]; then
            log "Téléphone hors de portée. Arrêt LLM..."
            pkill -f "llama-server" 2>/dev/null || true
            pkill -f "kyronex_server" 2>/dev/null
            LLM_ACTIVE=false
            log "Système en veille."
        fi
    fi
    sleep "$SCAN_INTERVAL"
done
