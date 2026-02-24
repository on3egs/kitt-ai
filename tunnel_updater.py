#!/usr/bin/env python3
"""
KITT Franco-Belge — Cloudflare Tunnel Auto-Updater
====================================================
Détecte l'URL du tunnel Cloudflare et met à jour tunnel.json
sur GitHub via l'API REST.

Usage:
    export GITHUB_TOKEN="ghp_..."
    export GITHUB_REPO="on3egs/Kitt-franco-belge"
    python3 tunnel_updater.py

Ou en passant l'URL directement (depuis start_tunnel.sh) :
    python3 tunnel_updater.py --url https://xxx.trycloudflare.com
    python3 tunnel_updater.py --offline
"""

import os
import re
import sys
import json
import time
import base64
import signal
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERREUR] pip install requests")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════
# CONFIGURATION (depuis variables d'environnement)
# ══════════════════════════════════════════════════════════════════

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO   = os.environ.get("GITHUB_REPO",  "on3egs/Kitt-franco-belge")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
TUNNEL_FILE   = os.environ.get("TUNNEL_FILE",   "tunnel.json")

# API locale de cloudflared (activée avec --metrics 127.0.0.1:8080)
CF_METRICS_URL  = "http://127.0.0.1:8081"
CF_LOG_FILE     = "/tmp/cloudflared.log"
CF_CONFIG_FILE  = str(Path.home() / ".cloudflared/config.yml")

POLL_INTERVAL   = 30   # secondes entre chaque vérification
HEARTBEAT_SECS  = 240  # heartbeat toutes les 4 min (garde last_update frais)
RETRY_DELAY     = 5    # secondes avant réessai en cas d'erreur réseau
MAX_RETRIES     = 3    # tentatives GitHub API

# ══════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/tunnel_updater.log", mode="a"),
    ],
)
log = logging.getLogger("tunnel-updater")

# ══════════════════════════════════════════════════════════════════
# DÉTECTION URL TUNNEL — 4 méthodes en cascade
# ══════════════════════════════════════════════════════════════════

# Patterns d'URLs Cloudflare reconnus
_CF_PATTERNS = [
    r"https://[a-z0-9\-]+\.trycloudflare\.com",   # quick tunnel
    r"https://[a-z0-9\-]+\.cfargotunnel\.com",     # tunnel nommé
    r"https://[a-z0-9\-\.]+\.workers\.dev",         # worker tunnel
]

def _extract_cf_url(text: str) -> str | None:
    """Extrait la première URL Cloudflare trouvée dans un texte."""
    for pattern in _CF_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[-1]   # la plus récente
    return None

def _method_env() -> str | None:
    """Méthode 1 : variable d'environnement CLOUDFLARE_TUNNEL_URL.
    Utilisé quand start_tunnel.sh a capturé l'URL et l'a exportée.
    Valide que l'URL correspond bien à un domaine Cloudflare."""
    url = os.environ.get("CLOUDFLARE_TUNNEL_URL", "").strip()
    if url and _extract_cf_url(url):
        return _extract_cf_url(url)
    return None

def _method_metrics_api() -> str | None:
    """Méthode 2 : API locale cloudflared sur 127.0.0.1:8080.
    Nécessite '--metrics 127.0.0.1:8080' dans la commande cloudflared."""
    try:
        # Endpoint JSON (versions récentes de cloudflared)
        r = requests.get(f"{CF_METRICS_URL}/", timeout=2)
        if r.status_code == 200:
            try:
                data = r.json()
                url = data.get("url") or data.get("hostname")
                if url:
                    return url if url.startswith("http") else f"https://{url}"
            except Exception:
                pass
            # Fallback : cherche une URL dans le HTML de la page de métriques
            url = _extract_cf_url(r.text)
            if url:
                return url
    except Exception:
        pass
    return None

def _method_log_file() -> str | None:
    """Méthode 3 : parse le fichier log de cloudflared.
    start_tunnel.sh redirige stdout/stderr vers /tmp/cloudflared.log."""
    try:
        if not Path(CF_LOG_FILE).exists():
            return None
        # Lire les 50 dernières lignes (les plus récentes)
        result = subprocess.run(
            ["tail", "-n", "50", CF_LOG_FILE],
            capture_output=True, text=True, timeout=3
        )
        return _extract_cf_url(result.stdout)
    except Exception:
        return None

def _method_process_output() -> str | None:
    """Méthode 4 : interroge cloudflared tunnel list (tunnel nommé).
    Fonctionne si cloudflared est configuré avec un tunnel nommé."""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "list", "--output", "json"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout:
            tunnels = json.loads(result.stdout)
            if tunnels:
                # Prend le premier tunnel actif
                t = tunnels[0]
                hostname = t.get("hostname") or t.get("name")
                if hostname:
                    h = hostname if hostname.startswith("http") else f"https://{hostname}"
                    return h
    except Exception:
        pass
    return None

def get_tunnel_url() -> str | None:
    """Cascade des 4 méthodes de détection. Retourne l'URL ou None."""
    methods = [
        ("Variable ENV", _method_env),
        ("API Métriques",  _method_metrics_api),
        ("Fichier log",    _method_log_file),
        ("CLI cloudflared",_method_process_output),
    ]
    for name, fn in methods:
        try:
            url = fn()
            if url:
                log.info(f"URL détectée via [{name}] → {url}")
                return url
        except Exception as e:
            log.debug(f"[{name}] exception: {e}")
    return None

# ══════════════════════════════════════════════════════════════════
# PAYLOAD JSON
# ══════════════════════════════════════════════════════════════════

def make_payload(status: str, url: str = "") -> dict:
    return {
        "status": status,            # "online" | "offline"
        "url": url,                  # URL publique du tunnel
        "last_update": datetime.now(timezone.utc).isoformat(),
        "host": "kitt-jetson",
        "version": "1.0",
    }

# ══════════════════════════════════════════════════════════════════
# GITHUB API
# ══════════════════════════════════════════════════════════════════

def _gh_headers() -> dict:
    if not GITHUB_TOKEN:
        raise EnvironmentError("GITHUB_TOKEN non défini")
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _get_file_sha() -> str | None:
    """Récupère le SHA du fichier existant (requis pour PUT de mise à jour)."""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TUNNEL_FILE}"
    try:
        r = requests.get(
            api_url,
            headers=_gh_headers(),
            params={"ref": GITHUB_BRANCH},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("sha")
        if r.status_code == 404:
            return None   # Fichier inexistant → on va le créer
        log.warning(f"SHA fetch HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log.warning(f"SHA fetch error: {e}")
    return None

def push_to_github(payload: dict) -> bool:
    """Upload tunnel.json sur GitHub via API REST. Retourne True si succès."""
    if not GITHUB_TOKEN:
        log.error("GITHUB_TOKEN manquant — export GITHUB_TOKEN=ghp_...")
        return False

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TUNNEL_FILE}"

    # Encodage Base64 du contenu JSON
    content_str = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("ascii")

    body = {
        "message": f"[auto] tunnel {payload['status']} — {payload['last_update']}",
        "content": content_b64,
        "branch":  GITHUB_BRANCH,
    }

    # SHA requis pour mise à jour (pas pour création)
    sha = _get_file_sha()
    if sha:
        body["sha"] = sha

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.put(api_url, headers=_gh_headers(), json=body, timeout=15)
            if r.status_code in (200, 201):
                log.info(f"GitHub OK — tunnel.json → status={payload['status']}")
                return True
            # Rate limit ?
            if r.status_code == 403:
                reset = r.headers.get("X-RateLimit-Reset", "?")
                log.error(f"GitHub 403 — rate limit ou token invalide. Reset: {reset}")
                return False
            log.warning(f"GitHub {r.status_code} (essai {attempt}): {r.text[:150]}")
        except requests.RequestException as e:
            log.warning(f"Réseau error (essai {attempt}): {e}")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    log.error("Échec GitHub API après tous les essais")
    return False

def set_offline() -> None:
    """Met à jour tunnel.json en mode offline."""
    log.info("Mise à jour → OFFLINE")
    push_to_github(make_payload("offline"))

# ══════════════════════════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════

def main_loop():
    """Boucle de surveillance continue (mode daemon)."""
    log.info("══ KITT Tunnel Updater — démarrage (mode daemon) ══")
    log.info(f"Repo  : {GITHUB_REPO}")
    log.info(f"Fichier : {TUNNEL_FILE} (branche {GITHUB_BRANCH})")
    log.info(f"Intervalle : {POLL_INTERVAL}s")

    if not GITHUB_TOKEN:
        log.error("ERREUR : GITHUB_TOKEN non défini !")
        sys.exit(1)

    last_status    = None
    last_url       = None
    last_push_time = 0.0

    while True:
        url = get_tunnel_url()
        current_status = "online" if url else "offline"
        now = time.time()

        # Push si changement d'état/URL OU heartbeat toutes les 4 min
        need_push = (
            current_status != last_status
            or url != last_url
            or (now - last_push_time) >= HEARTBEAT_SECS
        )
        if need_push:
            payload = make_payload(current_status, url or "")
            push_to_github(payload)
            last_status    = current_status
            last_url       = url
            last_push_time = now
        else:
            log.debug(f"Pas de changement — status={current_status}")

        time.sleep(POLL_INTERVAL)

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def _handle_shutdown(sig, frame):
    log.info("Signal reçu — mise offline avant arrêt...")
    set_offline()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KITT Tunnel Updater")
    parser.add_argument("--url",     help="Forcer une URL de tunnel",     default=None)
    parser.add_argument("--offline", help="Forcer le mode offline",        action="store_true")
    parser.add_argument("--once",    help="Mise à jour unique (pas daemon)", action="store_true")
    args = parser.parse_args()

    # Gestion SIGTERM / SIGINT (arrêt propre)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT,  _handle_shutdown)

    if args.offline:
        set_offline()
        sys.exit(0)

    if args.url:
        # Mode manuel : URL fournie en argument
        if not re.match(r"https://[a-zA-Z0-9\-\.]+", args.url):
            log.error(f"URL invalide : {args.url}")
            sys.exit(1)
        os.environ["CLOUDFLARE_TUNNEL_URL"] = args.url
        log.info(f"URL forcée : {args.url}")
        if args.once:
            push_to_github(make_payload("online", args.url))
            sys.exit(0)

    if args.once:
        url = get_tunnel_url()
        if url:
            push_to_github(make_payload("online", url))
        else:
            set_offline()
        sys.exit(0)

    # Mode daemon par défaut
    main_loop()
