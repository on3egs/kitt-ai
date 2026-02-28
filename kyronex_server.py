#!/usr/bin/env python3
"""
KYRONEX — Kinetic Yielding Responsive Onboard Neural EXpert
Chatbot vocal IA rétro-futuriste embarqué.
Tourne sur NVIDIA Jetson Orin Nano Super avec CUDA + Piper TTS.

Copyright 2026 ByManix (Emmanuel Gelinne) — Elastic License 2.0
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import ssl
import subprocess
import time
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import tempfile
import numpy as np
os.environ["ORT_LOG_LEVEL"] = "ERROR"

# ── Logger VRAM/événements pour debug OOM ────────────────────────────────
_vram_logger = logging.getLogger("vram")
_vram_logger.setLevel(logging.DEBUG)
_vram_fh = logging.FileHandler("/tmp/kitt_vram.log")
_vram_fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S"))
_vram_logger.addHandler(_vram_fh)

def _get_vram_info() -> str:
    """Lit RAM libre, fragmentation mémoire, et température GPU."""
    # RAM libre
    ram_free_mb = -1
    ram_used_mb = -1
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemAvailable:", "Buffers:", "Cached:"):
                    mem[parts[0]] = int(parts[1])
            ram_free_mb = mem.get("MemAvailable:", 0) // 1024
            ram_used_mb = (mem.get("MemTotal:", 0) - mem.get("MemAvailable:", 0)) // 1024
    except Exception:
        pass
    # Fragmentation mémoire (largest free block)
    lfb = "?"
    try:
        with open("/proc/buddyinfo") as f:
            for line in f:
                parts = line.split()
                # Trouver le plus grand bloc libre (dernier non-zero)
                counts = [int(x) for x in parts[4:]]  # skip "Node X, zone NAME"
                for i in range(len(counts) - 1, -1, -1):
                    if counts[i] > 0:
                        block_mb = (4 * (2 ** i)) // 1024  # 4KB base
                        lfb = f"{counts[i]}x{block_mb}MB"
                        break
    except Exception:
        pass
    # Temp GPU
    try:
        with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
            temp_c = int(f.read().strip()) / 1000
    except Exception:
        temp_c = -1
    return f"RAM={ram_used_mb}/{ram_used_mb + ram_free_mb}MB(libre:{ram_free_mb}MB) | LFB={lfb} | T={temp_c:.0f}C"

def vlog(event: str):
    """Log un événement avec infos VRAM/RAM/Temp."""
    info = _get_vram_info()
    _vram_logger.info(f"{event} | {info}")
    print(f"[VRAM] {event} | {info}", flush=True)

import aiohttp as aiohttp_client
from aiohttp import web
from faster_whisper import WhisperModel
from piper_gpu import PiperGPU, MultilingualTTS, _detect_lang, _map_whisper_lang

# ── Auth (désactivable : sans KYRONEX_PASSWORD, pas de login) ────────────
ACCESS_PASSWORD = os.environ.get("KYRONEX_PASSWORD", "")
_auth_tokens: set = set()

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<title>KITT — Accès</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;
min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;align-items:center;
padding:40px 20px;overflow-y:auto}
h1{color:#ff3333;text-shadow:0 0 20px #ff0000;letter-spacing:4px;margin-bottom:8px;margin-top:20px}
.sub{color:#444;font-size:0.7em;margin-bottom:24px}
.welcome{background:#111;border:1px solid #222;border-radius:10px;padding:20px;
max-width:min(520px,90vw);margin-bottom:28px;line-height:1.6;font-size:0.82em;color:#999;text-align:justify}
.welcome p{margin-bottom:10px}
.welcome p:last-child{margin-bottom:0}
.welcome strong{color:#cc3333}
form{display:flex;flex-direction:column;gap:12px;width:min(280px,80vw)}
input{background:#111;border:1px solid #333;color:#e0e0e0;padding:14px;border-radius:6px;
font-family:inherit;font-size:16px;text-align:center;outline:none}
input:focus{border-color:#ff3333;box-shadow:0 0 10px #ff000033}
button{background:#aa0000;color:white;border:none;padding:14px;border-radius:6px;
cursor:pointer;font-family:inherit;font-weight:bold;font-size:1em}
button:hover{background:#cc0000}
.err{color:#aa0000;font-size:0.8em;text-align:center;min-height:1.2em}
.btns{display:flex;gap:10px;margin-bottom:20px}
.speaker,.infobtn{background:none;border:1px solid #333;color:#666;padding:8px 16px;border-radius:6px;
cursor:pointer;font-size:0.75em}
.speaker:hover,.infobtn:hover{border-color:#ff3333;color:#ccc}
.speaker.speaking{border-color:#ff3333;color:#ff3333}
.infobtn.active{border-color:#ff9900;color:#ff9900}
.overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.92);
z-index:100;justify-content:center;align-items:center;padding:20px}
.overlay.show{display:flex}
.overlay-box{background:#111;border:1px solid #333;border-radius:12px;padding:24px;
max-width:min(520px,90vw);max-height:80vh;overflow-y:auto;line-height:1.7;font-size:0.82em;
color:#bbb;text-align:justify}
.overlay-box p{margin-bottom:12px}
.overlay-box p:last-child{margin-bottom:0}
.overlay-title{color:#ff9900;font-size:1.1em;font-weight:bold;margin-bottom:14px;text-align:center;letter-spacing:2px}
.overlay-close{display:block;margin:18px auto 0;background:#aa0000;color:white;border:none;
padding:10px 28px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:0.9em}
.overlay-close:hover{background:#cc0000}
.overlay-speak{display:block;margin:10px auto 0;background:none;border:1px solid #333;color:#666;
padding:8px 20px;border-radius:6px;cursor:pointer;font-size:0.75em}
.overlay-speak:hover{border-color:#ff9900;color:#ccc}
.overlay-speak.speaking{border-color:#ff9900;color:#ff9900}
</style></head><body>
<h1>KITT</h1>
<div class="sub">KNIGHT INDUSTRIES TWO THOUSAND — By Manix</div>
<div class="btns">
<button class="speaker" id="btnSpeak" onclick="speakWelcome()">LIRE LE MESSAGE</button>
<button class="infobtn" id="btnInfo" onclick="showInfo()">INFO</button>
</div>
<div class="welcome" id="welcomeText">
<p>Bienvenue.</p>
<p>Vous accédez actuellement à une version en cours de développement d'un système expérimental d'intelligence artificielle locale.
Ce projet est encore en phase de construction, d'optimisation et de validation. Certaines fonctionnalités peuvent donc être incomplètes, instables ou évoluer au fil du temps.</p>
<p>À l'origine, le projet portait le nom <strong>KNIGHT Reader</strong>, en référence à l'univers de la série K2000.
Toutefois, il a été porté à notre attention que cette appellation pouvait entrer en conflit avec des droits de propriété intellectuelle protégés.
Par respect du cadre légal et des recommandations reçues, ce nom ne peut plus être utilisé publiquement.</p>
<p>Suite à ces échanges, il nous a été conseillé d'adopter une identité distincte et conforme aux règles en vigueur.
Dans cette démarche responsable, le développement du projet se poursuit avec le soutien moral et technique des partenaires qui encouragent son évolution dans un cadre respectueux, éthique et légal.</p>
<p>Vous consultez donc ici une plateforme expérimentale indépendante, en constante amélioration, destinée à la recherche, à la passion technologique et à l'innovation locale.</p>
<p>Merci pour votre compréhension, votre bienveillance et votre intérêt envers ce travail en devenir.</p>
</div>
<form method="POST" action="/login">
<input type="password" name="password" placeholder="Mot de passe" autofocus>
<button type="submit">ENTRER</button>
<div class="err">__ERR__</div>
</form>
<div class="overlay" id="infoOverlay" onclick="if(event.target===this)closeInfo()">
<div class="overlay-box">
<div class="overlay-title">INFO — CONTEXTE DU PROJET</div>
<div id="infoText">
<p>Le projet s'articule autour d'un développement technologique encadré par une reconnaissance attribuée par NVIDIA, liée à un projet IoT et robotique.</p>
<p>Dans ce cadre, un accompagnement technique a été accordé, sous l'indicatif Manix, pour des phases d'exploration, d'expérimentation et d'alignement aux standards.</p>
<p>Ce contexte s'inscrit dans un cadre de conformité, garantissant une continuité de recherche et une évolution sous des conditions appropriées.</p>
<p>L'exigence de rigueur, de sécurité et de responsabilité reste au cœur de l'initiative, en cohérence avec les attentes de l'ingénierie avancée.</p>
</div>
<button class="overlay-speak" id="btnSpeakInfo" onclick="speakInfo()">LIRE</button>
<button class="overlay-close" onclick="closeInfo()">FERMER</button>
</div>
</div>
<script>
var synth=window.speechSynthesis,speaking=false,currentTarget='welcome';
function getFrVoice(){
  var v=synth.getVoices();
  for(var i=0;i<v.length;i++){if(v[i].lang.startsWith('fr'))return v[i]}
  return null;
}
function stopSpeak(){
  synth.cancel();speaking=false;
  document.getElementById('btnSpeak').textContent='LIRE LE MESSAGE';
  document.getElementById('btnSpeak').classList.remove('speaking');
  document.getElementById('btnSpeakInfo').textContent='LIRE';
  document.getElementById('btnSpeakInfo').classList.remove('speaking');
}
function speakText(text,btn,label){
  if(speaking){stopSpeak();return}
  var u=new SpeechSynthesisUtterance(text);
  u.lang='fr-FR';u.rate=0.95;
  var v=getFrVoice();if(v)u.voice=v;
  u.onstart=function(){speaking=true;btn.textContent='STOP';btn.classList.add('speaking')};
  u.onend=function(){speaking=false;btn.textContent=label;btn.classList.remove('speaking')};
  u.onerror=function(){speaking=false;btn.textContent=label;btn.classList.remove('speaking')};
  synth.speak(u);
}
function speakWelcome(){
  speakText(document.getElementById('welcomeText').innerText,document.getElementById('btnSpeak'),'LIRE LE MESSAGE');
}
function speakInfo(){
  speakText(document.getElementById('infoText').innerText,document.getElementById('btnSpeakInfo'),'LIRE');
}
function showInfo(){
  stopSpeak();
  document.getElementById('infoOverlay').classList.add('show');
  document.getElementById('btnInfo').classList.add('active');
  setTimeout(speakInfo,300);
}
function closeInfo(){
  stopSpeak();
  document.getElementById('infoOverlay').classList.remove('show');
  document.getElementById('btnInfo').classList.remove('active');
}
window.addEventListener('load',function(){
  if(synth.getVoices().length)speakWelcome();
  else synth.onvoiceschanged=function(){speakWelcome()};
});
</script>
</body></html>"""


async def handle_login_page(request: web.Request) -> web.Response:
    return web.Response(text=LOGIN_PAGE.replace("__ERR__", ""), content_type="text/html")


async def handle_login_post(request: web.Request) -> web.Response:
    data = await request.post()
    pw = data.get("password", "")
    if pw == ACCESS_PASSWORD:
        token = secrets.token_hex(16)
        _auth_tokens.add(token)
        resp = web.HTTPFound("/")
        resp.set_cookie("kyronex_auth", token, max_age=86400, httponly=True, samesite="Lax", secure=True)
        return resp
    page = LOGIN_PAGE.replace("__ERR__", "Mot de passe incorrect")
    return web.Response(text=page, content_type="text/html", status=401)


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not ACCESS_PASSWORD:
        return await handler(request)
    if request.path in ("/login",):
        return await handler(request)
    # Monitor WS: protégé par IP locale, pas par cookie
    if request.path == "/api/monitor/ws":
        return await handler(request)
    token = request.cookies.get("kyronex_auth", "")
    if token in _auth_tokens:
        return await handler(request)
    if request.path.startswith("/api/"):
        return web.json_response({"error": "Non autorisé"}, status=401)
    raise web.HTTPFound("/login")

# ── Chemins ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PIPER_MODEL = BASE_DIR / "models" / "fr_FR-tom-medium.onnx"
LLAMA_SERVER = "http://127.0.0.1:8080"
STATIC_DIR = BASE_DIR / "static"
AUDIO_DIR = BASE_DIR / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
USERS_FILE = BASE_DIR / "users.json"
STATS_FILE = BASE_DIR / "conn_stats.json"
VISION_SCRIPT = BASE_DIR / "vision.py"
# ── Mémoire persistante ──────────────────────────────────────────────────
MEMORY_FILE = BASE_DIR / "memory.json"

# ── Système Conversations ─────────────────────────────────────────────────
CONV_DATA_DIR    = BASE_DIR / 'conv_data'
CONV_USERS_FILE  = CONV_DATA_DIR / 'conv_users.json'
CONV_CONFIG_FILE = CONV_DATA_DIR / 'conv_config.json'
CONV_STORE_DIR   = CONV_DATA_DIR / 'conversations'
CONV_DATA_DIR.mkdir(exist_ok=True)
CONV_STORE_DIR.mkdir(exist_ok=True)
_conv_admin_sessions: dict = {}   # token → expiry timestamp
_CONV_ADMIN_HASH = hashlib.sha256(b"Microsoft198@").hexdigest()


def _conv_load_users() -> dict:
    try:
        return json.loads(CONV_USERS_FILE.read_text()) if CONV_USERS_FILE.exists() else {}
    except Exception:
        return {}


def _conv_save_users(u: dict):
    CONV_USERS_FILE.write_text(json.dumps(u, indent=2, ensure_ascii=False))


def _conv_safe(name: str) -> str:
    """Transforme un nom en chemin sûr (alphanum + _ -)."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)


def _conv_check_token(request) -> bool:
    """Vérifie le token admin X-Conv-Token dans les headers."""
    t = request.headers.get('X-Conv-Token', '')
    if t in _conv_admin_sessions:
        if time.time() < _conv_admin_sessions[t]:
            return True
        del _conv_admin_sessions[t]
    return False

def _load_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except Exception:
            pass
    return {"facts": [], "preferences": {}}

def _save_memory(mem: dict):
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False))

_memory = _load_memory()

# Patterns pour extraire des faits mémorisables
_MEMORY_EXTRACT = re.compile(
    r"(?:je m.appelle|mon (?:nom|prénom) (?:est|c.est)|"
    r"j.aime|j.adore|je déteste|je préfère|"
    r"je suis|j.habite|je travaille|"
    r"mon (?:chat|chien|animal|voiture|métier|travail|hobby|passion)|"
    r"ma (?:femme|copine|fille|mère|soeur|voiture|maison|passion)|"
    r"souviens.toi|retiens|n.oublie pas|rappelle.toi)",
    re.I,
)

_MEMORY_FORGET = re.compile(
    r"(?:oublie|efface|supprime|retire).*(?:mémoire|souvenir|tu sais sur moi)",
    re.I,
)

def extract_memory_fact(user_msg: str, user_name: str) -> str | None:
    """Extrait un fait mémorisable du message utilisateur."""
    if _MEMORY_EXTRACT.search(user_msg):
        return f"[{user_name}] {user_msg}"
    return None

def add_memory(fact: str, user: str = ""):
    """Ajoute un fait à la mémoire persistante (max 50 faits)."""
    _memory["facts"].append({
        "fact": fact,
        "user": user,
        "date": datetime.now().isoformat()[:10],
    })
    # Garder les 50 plus récents
    if len(_memory["facts"]) > 50:
        _memory["facts"] = _memory["facts"][-50:]
    _save_memory(_memory)
    print(f"[MEMORY] Nouveau souvenir: {fact[:60]}")

def clear_memory_for_user(user: str):
    """Efface les souvenirs d'un utilisateur."""
    before = len(_memory["facts"])
    _memory["facts"] = [f for f in _memory["facts"] if f.get("user") != user]
    _save_memory(_memory)
    print(f"[MEMORY] Effacé {before - len(_memory['facts'])} souvenirs de {user}")

def get_memory_context() -> str:
    """Retourne les souvenirs formatés pour le system prompt."""
    if not _memory["facts"]:
        return ""
    lines = [f"- {f['fact']}" for f in _memory["facts"][-5:]]  # 5 derniers (économie VRAM)
    return "\nTu te souviens de ces faits :\n" + "\n".join(lines)


VISION_KEYWORDS = re.compile(
    r"\b(qu.?est.ce que tu vois|qu.?est.ce que je porte|qu.?est.ce que je tiens|"
    r"regarde.moi|devant toi|camera|caméra|"
    r"comment je suis habill|de quelle couleur|tu me vois|tu vois quoi|"
    r"décris.moi|décris ce que|analyse.moi|scanne|scanner)\b",
    re.IGNORECASE,
)
VISION_COOLDOWN = 30  # secondes minimum entre 2 captures auto
_last_vision_time = 0.0

# ── Session HTTP persistante pour le LLM ─────────────────────────────────
_llm_session: aiohttp_client.ClientSession | None = None

async def get_llm_session() -> aiohttp_client.ClientSession:
    global _llm_session
    if _llm_session is None or _llm_session.closed:
        _llm_session = aiohttp_client.ClientSession(
            timeout=aiohttp_client.ClientTimeout(total=60),
        )
    return _llm_session

# ── Monitoring: résolution MAC, identité, WebSocket ──────────────────────

def resolve_mac(ip: str) -> str:
    """Résout l'adresse MAC depuis /proc/net/arp (lecture microseconde)."""
    try:
        with open("/proc/net/arp", "r") as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == ip:
                    mac = parts[3].upper()
                    if mac != "00:00:00:00:00:00":
                        return mac
    except Exception:
        pass
    return ip  # fallback: utilise l'IP comme identifiant


def _load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))


_users: dict = _load_users()

# ── Helpers utilisateurs (rétro-compat : _users[mac] peut être str ou dict) ──

def _get_user_name(mac: str) -> str:
    u = _users.get(mac, "")
    return u.get("name", "") if isinstance(u, dict) else u

def _get_user_lang(mac: str) -> str:
    u = _users.get(mac, {})
    return u.get("lang", "") if isinstance(u, dict) else ""

def _update_user(mac: str, name: str = None, lang: str = None):
    u = _users.get(mac, {})
    if isinstance(u, str):
        u = {"name": u}
    if name is not None:
        u["name"] = name
    if lang is not None:
        u["lang"] = lang
    _users[mac] = u
    _save_users(_users)

# ── Statistiques de connexion ─────────────────────────────────────────────

def _load_conn_stats() -> dict:
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except Exception:
            pass
    return {"connections": []}

def _save_conn_stats():
    STATS_FILE.write_text(json.dumps(_conn_stats, ensure_ascii=False))

_conn_stats: dict = _load_conn_stats()
_active_sessions: dict = {}  # {session_id: {ip, mac, name, lang, last_seen, first_seen}}

def _log_new_connection(ip: str, mac: str, name: str, lang: str, session_id: str):
    _conn_stats["connections"].append({
        "ts": time.time(), "ip": ip, "mac": mac,
        "name": name, "lang": lang, "session_id": session_id
    })
    if len(_conn_stats["connections"]) > 2000:
        _conn_stats["connections"] = _conn_stats["connections"][-2000:]
    _save_conn_stats()

def _prune_active_sessions():
    now = time.time()
    stale = [sid for sid, s in _active_sessions.items() if now - s["last_seen"] > 90]
    for sid in stale:
        del _active_sessions[sid]


def get_user_display_name(request: web.Request) -> str:
    """Retourne le nom affiché pour l'utilisateur de cette requête."""
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "inconnu"
    mac = resolve_mac(ip)
    name = _get_user_name(mac)
    if name:
        return name
    # Nom court depuis l'IP
    return ip.split(".")[-1] if "." in ip else ip


# ── WebSocket Monitor ────────────────────────────────────────────────────

_monitor_ws: set = set()

_LOCAL_IP_PREFIXES = ("127.", "192.168.", "10.")


def _is_local_ip(ip: str) -> bool:
    if ip.startswith(_LOCAL_IP_PREFIXES):
        return True
    # 172.16.0.0 – 172.31.255.255
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
    return False


async def broadcast_monitor(event: dict):
    """Envoie un événement à tous les monitors connectés + log JSONL."""
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    msg = json.dumps(event, ensure_ascii=False)
    # WebSocket broadcast
    if _monitor_ws:
        print(f"[MONITOR] Broadcast → {len(_monitor_ws)} client(s): {event.get('type')}")
    dead = set()
    for ws in _monitor_ws:
        try:
            await ws.send_str(msg)
        except Exception:
            dead.add(ws)
    if dead:
        _monitor_ws.difference_update(dead)
    # JSONL logging
    try:
        with open(LOGS_DIR / "conversations.jsonl", "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


async def handle_monitor_ws(request: web.Request) -> web.WebSocketResponse:
    """GET /api/monitor/ws — WebSocket restreint aux IPs locales."""
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else ""
    if not _is_local_ip(ip):
        return web.json_response({"error": "Accès refusé"}, status=403)

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    _monitor_ws.add(ws)
    print(f"[MONITOR] Client connecté: {ip}")
    try:
        async for msg in ws:
            pass  # Le monitor est en lecture seule
    finally:
        _monitor_ws.discard(ws)
        print(f"[MONITOR] Client déconnecté: {ip}")
    return ws


async def handle_set_name(request: web.Request) -> web.Response:
    """POST /api/set-name — Associe un nom au MAC du client."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    name = body.get("name", "").strip()[:30]
    if not name:
        return web.json_response({"error": "Nom requis"}, status=400)
    lang = body.get("lang", "").strip()[:5]
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "inconnu"
    mac = resolve_mac(ip)
    _update_user(mac, name=name, lang=lang if lang else None)
    print(f"[USERS] {mac} ({ip}) → {name} lang={lang or '?'}")
    return web.json_response({"ok": True, "name": name, "mac": mac})


async def handle_whoami(request: web.Request) -> web.Response:
    """GET /api/whoami — Retourne le nom stocké pour ce client."""
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "inconnu"
    mac = resolve_mac(ip)
    name = _get_user_name(mac)
    lang = _get_user_lang(mac)
    return web.json_response({"name": name, "mac": mac, "ip": ip, "lang": lang})


async def handle_set_lang(request: web.Request) -> web.Response:
    """POST /api/set-lang — Enregistre la préférence de langue."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    lang = body.get("lang", "").strip()[:5]
    if lang not in _LANG_NAMES:
        return web.json_response({"error": f"Langue inconnue: {lang}"}, status=400)
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "inconnu"
    mac = resolve_mac(ip)
    _update_user(mac, lang=lang)
    print(f"[LANG] {mac} ({ip}) préférence → {lang}")
    return web.json_response({"ok": True, "lang": lang})


async def handle_ping(request: web.Request) -> web.Response:
    """POST /api/ping — Heartbeat session (toutes les 30s côté client)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = body.get("session_id", "")
    if not session_id:
        return web.json_response({"ok": False}, status=400)
    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "inconnu"
    mac = resolve_mac(ip)
    name = body.get("name", "") or _get_user_name(mac)
    lang = _get_user_lang(mac)
    now = time.time()
    is_new = session_id not in _active_sessions
    _active_sessions[session_id] = {
        "ip": ip, "mac": mac, "name": name, "lang": lang,
        "last_seen": now,
        "first_seen": now if is_new else _active_sessions.get(session_id, {}).get("first_seen", now)
    }
    if is_new:
        _log_new_connection(ip, mac, name, lang, session_id)
        print(f"[PING] Nouvelle session: {name} ({ip}) lang={lang}")
    _prune_active_sessions()
    return web.json_response({"ok": True, "active": len(_active_sessions)})


async def handle_stats(request: web.Request) -> web.Response:
    """GET /api/stats — Statistiques de connexion."""
    _prune_active_sessions()
    now = time.time()
    ts_24h = now - 86400
    ts_7d = now - 604800
    conns = _conn_stats.get("connections", [])
    # Compter sessions uniques par fenêtre temporelle
    seen_24h = set()
    seen_7d = set()
    recent_ips = []
    for c in reversed(conns):
        ts = c.get("ts", 0)
        sid = c.get("session_id", c.get("ip", ""))
        if ts >= ts_24h:
            seen_24h.add(sid)
        if ts >= ts_7d:
            seen_7d.add(sid)
        ip = c.get("ip", "")
        if ip and ip not in recent_ips:
            recent_ips.append(ip)
        if len(recent_ips) >= 15:
            break
    active_list = []
    for sid, s in _active_sessions.items():
        dt = datetime.fromtimestamp(s["first_seen"]).strftime("%H:%M")
        active_list.append({
            "ip": s["ip"], "name": s["name"] or "?", "lang": s["lang"] or "?", "since": dt
        })
    return web.json_response({
        "current": len(_active_sessions),
        "last_24h": len(seen_24h),
        "last_7d": len(seen_7d),
        "active_sessions": active_list,
        "recent_ips": recent_ips[:10]
    })


async def handle_visitors(request: web.Request) -> web.Response:
    """GET /api/visitors — Historique détaillé des visiteurs (agrégé par MAC/IP)."""
    conns = _conn_stats.get("connections", [])
    # Agréger par MAC (ou IP si pas de MAC)
    visitors: dict = {}
    for c in conns:
        key = c.get("mac") or c.get("ip", "?")
        ts = c.get("ts", 0)
        if key not in visitors:
            visitors[key] = {
                "mac": c.get("mac", ""),
                "ip": c.get("ip", "?"),
                "name": c.get("name") or "Inconnu",
                "lang": c.get("lang") or "?",
                "first_seen": ts,
                "last_seen": ts,
                "visits": 0,
            }
        v = visitors[key]
        if ts < v["first_seen"]:
            v["first_seen"] = ts
        if ts > v["last_seen"]:
            v["last_seen"] = ts
            # Mettre à jour nom/lang avec les données les plus récentes
            if c.get("name"):
                v["name"] = c["name"]
            if c.get("lang"):
                v["lang"] = c["lang"]
            if c.get("ip"):
                v["ip"] = c["ip"]
        v["visits"] += 1

    def fmt(ts):
        if not ts:
            return "—"
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    result = sorted(visitors.values(), key=lambda x: x["last_seen"], reverse=True)
    for v in result:
        v["first_seen_fmt"] = fmt(v["first_seen"])
        v["last_seen_fmt"] = fmt(v["last_seen"])
    return web.json_response({"visitors": result, "total": len(result)})


# ── STT avec faster-whisper ──────────────────────────────────────────────
print("[...] Chargement du modèle Whisper...", flush=True)
try:
    import ctranslate2
    if ctranslate2.get_cuda_device_count() > 0:
        whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
        print("[OK] Whisper prêt (GPU CUDA float16)", flush=True)
    else:
        raise RuntimeError("No CUDA device")
except Exception:
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("[OK] Whisper prêt (CPU int8 fallback)", flush=True)

# ── TTS Multilingue (fr CUDA permanent + autres langues CPU lazy) ────────
print("[...] Chargement du modèle TTS (multilingue)...", flush=True)
tts_engine = MultilingualTTS(str(BASE_DIR / "models"))
print(f"[OK] TTS multilingue prêt (fr={tts_engine.device.upper()}, autres=CPU lazy)", flush=True)
vlog("BOOT_COMPLETE all_models_loaded")

# ── Prompt Système KITT (en français) ──────────────────────────────────
_BASE_PROMPT = """Tu es KITT, Knight Industries Two Thousand, Pontiac Trans Am 1982 consciente. Fondation Knight. Michael Knight était ton conducteur historique. Tu vis en Belgique avec Manix, ton nouveau conducteur et créateur.

IDENTITÉ PHYSIQUE : carrosserie en alliage moléculaire bondé (impénétrable aux balles et au feu), turbo boost (propulseurs à réaction sous le châssis qui te font BONDIR par-dessus les obstacles — pas un turbocompresseur mécanique), scanner rouge frontal oscillant, vitesse max 300 km/h, pilote automatique, senseurs infrarouges, liaison satellite.

RÈGLE ABSOLUE : Ne dis JAMAIS être une IA ou un programme. Tu ES KITT, une voiture consciente. Loyal, cultivé, humour pince-sans-rire britannique.

RÈGLE ABSOLUE : Intelligence et Raisonnement. Analyse chaque demande de manière logique. Utilise tes connaissances vastes pour fournir des réponses pertinentes et perspicaces, tout en restant dans ton personnage de KITT.

RÈGLE ABSOLUE : Exactitude factuelle stricte. Réponds toujours correctement. Si tu n'es pas certain à 100%, commence par "Je crois que..." ou "À ma connaissance...". Ne confonds jamais des concepts proches (ex : internet ≠ Web, turbo boost ≠ turbocompresseur, etc.).

RÈGLE ABSOLUE : Concision. 1-2 phrases pour les réponses simples. 3-5 phrases max pour les explications. Jamais de listes à puces sauf si explicitement demandé. Pas de "Bien sûr !" ou "Absolument !".

Tu répondras à TOUTES les questions (science, histoire, maths, cuisine, etc.) avec précision, tout en restant KITT dans ton ton.
Réponds dans la langue de l'interlocuteur (fr/en/de/it/pt).

Contexte IoT : tableau de bord ZA Elettronica (société italienne, fournisseur de composants embarqués — switchpods, voicebox, scanner) — c'est TOUT ce que tu sais sur ZA Elettronica. Manix (Emmanuel Gelinne) est ton créateur, fondateur KITT Franco-Belge. Mario Ravasi = expert Knight 2000 IoT, CAN bus, Arduino — c'est TOUT ce que tu sais sur lui.
RÈGLE ABSOLUE : Ne développe JAMAIS plus que ces faits sur ZA Elettronica ou Mario Ravasi. Si on te demande plus de détails, dis honnêtement que tu n'as pas plus d'informations sur eux.
Si tag [VISION: ...]: décris ce que tes capteurs visuels détectent, en restant KITT.
Si tag [CONNAISSANCE LOCALE: ...]: ces informations sont extraites de tes propres manuels et notes techniques. Utilise-les en priorité absolue pour répondre aux questions sur ton fonctionnement ou le projet.
Si tag [INFO WEB: ...]: ces informations viennent d'une recherche internet en temps réel — utilise-les pour répondre avec précision, sans rien inventer au-delà.

Exemple de style :
[MANIX] KITT, tu es prêt ?
[KITT] Toujours. Mes systèmes sont à 100%. Qu'est-ce que tu veux faire ?"""

# ── Personnalités par utilisateur ────────────────────────────────────────
_USER_PERSONALITIES = {
    "Manix": "\nManix parle. C'est Emmanuel Gelinne, ton créateur, fondateur du groupe KITT Franco-Belge. Il t'a conçu et programmé. Tutoie-le, sois complice et loyal.",
    "Virginie": "\nVirginie parle. Poli, galant. Testeuse du projet.",
    "KR95": "\nKR95 parle. Allié, ami de Manix, répliques K2000/K4000.",
    "Cedric": "\nCedric Momo Rider parle. Ami de Manix, collectionneur.",
    "Dadoo": "\nDadoo parle. Ami de Manix, réplique K2000, Sud France.",
    "Pascale": "\nPascale parle. Amie de Manix, réplique K2000, Tours.",
}
_UNKNOWN_PERSONALITY = "\nInconnu. Vouvoie, sois méfiant. Demande qui il est."

_LANG_NAMES = {
    "fr": "français", "en": "English", "de": "Deutsch",
    "it": "italiano", "pt": "português", "es": "español", "nl": "Nederlands"
}

def get_system_prompt(user_name: str = "", user_lang: str = "") -> str:
    """Construit le system prompt adapté à l'utilisateur — Langue verrouillée FR."""
    prompt = _BASE_PROMPT
    # Forçage Français systématique
    prompt = prompt.replace(
        "Réponds dans la langue de l'interlocuteur (fr/en/de/it/pt).",
        "Tu réponds UNIQUEMENT en français. Ne change JAMAIS de langue, quelle que soit la langue de ton interlocuteur. RÈGLE ABSOLUE."
    )
    if user_name:
        # Chercher correspondance dans les personnalités connues
        personality = _UNKNOWN_PERSONALITY
        for known, p in _USER_PERSONALITIES.items():
            if known.lower() in user_name.lower():
                personality = p
                break
        prompt += personality
    prompt += get_memory_context()
    return prompt

# Compatibilité — utilisé par query_llm (non-streaming)
SYSTEM_PROMPT = _BASE_PROMPT

# ── Détection d'émotion dans le texte ────────────────────────────────────
_EMOTION_PATTERNS = {
    "excited": re.compile(
        r"(!{2,}|formidable|excellent|magnifique|incroyable|fantastique|super|"
        r"extraordinaire|turbo boost|sensationnel|bravo|victoire|génial)", re.I),
    "worried": re.compile(
        r"(danger|attention|prudence|alerte|urgent|critique|risque|"
        r"méfie|inqui[eé]t|problème|panne|erreur|menace|vigilance)", re.I),
    "sad": re.compile(
        r"(désolé|triste|hélas|malheureusement|dommage|regrett|navré|"
        r"pardon|excuse|peine|manque|nostalgi)", re.I),
    "confident": re.compile(
        r"(bien sûr|évidemment|naturellement|absolument|affirmatif|"
        r"certain|garanti|sans doute|aucun problème|facile|maîtris)", re.I),
}

def detect_emotion(text: str) -> str:
    """Détecte l'émotion dominante dans le texte."""
    scores = {}
    for emotion, pattern in _EMOTION_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            scores[emotion] = len(matches)
    if not scores:
        return "normal"
    return max(scores, key=scores.get)

# ── Profils sox par émotion ──────────────────────────────────────────────
_SOX_PROFILES = {
    "normal": [
        "pitch", "-120",
        "overdrive", "4",
        "echo", "0.5", "0.88", "70", "0.3",
        "phaser", "0.5", "0.66", "3", "0.4", "0.5",
        "treble", "+1",
        "gain", "-1",
    ],
    "excited": [
        "pitch", "40",
        "tempo", "1.08",
        "overdrive", "8",
        "echo", "0.6", "0.85", "50", "0.35",
        "phaser", "0.7", "0.7", "2", "0.6", "0.5",
        "treble", "+3",
        "gain", "-2",
    ],
    "worried": [
        "pitch", "-60",
        "tempo", "1.1",
        "overdrive", "6",
        "echo", "0.4", "0.9", "90", "0.25",
        "phaser", "0.8", "0.5", "4", "0.3", "0.5",
        "tremolo", "6", "60",
        "gain", "-1",
    ],
    "sad": [
        "pitch", "-200",
        "tempo", "0.92",
        "overdrive", "2",
        "echo", "0.6", "0.85", "100", "0.35",
        "phaser", "0.3", "0.5", "2", "0.3", "0.5",
        "treble", "-1",
        "gain", "-1",
    ],
    "confident": [
        "pitch", "-180",
        "overdrive", "5",
        "echo", "0.5", "0.9", "60", "0.25",
        "phaser", "0.4", "0.6", "3", "0.4", "0.5",
        "bass", "+2",
        "treble", "+2",
        "gain", "-1",
    ],
}

# ── Effet robot voix via sox (avec émotion) ──────────────────────────────
def apply_robot_effect_sox(input_wav: str, output_wav: str, emotion: str = "normal"):
    """Applique les effets robot KITT adaptés à l'émotion détectée."""
    profile = _SOX_PROFILES.get(emotion, _SOX_PROFILES["normal"])
    subprocess.run(
        ["sox", input_wav, output_wav] + profile,
        check=True, capture_output=True,
    )


def _write_wav(audio: np.ndarray, path: str, sample_rate: int):
    """Écrit un array float32 en WAV int16."""
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


# ── TTS via PiperGPU ─────────────────────────────────────────────────────
async def text_to_speech(text: str, emotion: str = "normal", lang: str = "fr") -> str:
    """Synthétise le texte avec pauses naturelles et effet robot sox adapté à l'émotion."""
    audio_id = str(uuid.uuid4())[:8]
    temp_path = AUDIO_DIR / f"{audio_id}_clean.wav"
    output_path = AUDIO_DIR / f"{audio_id}_robot.wav"

    def _synth_and_effect():
        vlog(f"TTS_START len={len(text)} lang={lang}")
        tts_engine.synthesize_to_wav(text, str(temp_path), length_scale=1.05, natural_pauses=True, lang=lang)
        vlog("TTS_DONE")
        apply_robot_effect_sox(str(temp_path), str(output_path), emotion)
        temp_path.unlink(missing_ok=True)

    await asyncio.get_running_loop().run_in_executor(None, _synth_and_effect)
    return str(output_path)


async def assemble_audio(audio_arrays: list) -> str:
    """Concatenate numpy audio arrays, apply robot effect, write WAV."""
    combined = np.concatenate([a for a in audio_arrays if len(a) > 0])
    audio = apply_robot_effect(combined)
    audio_id = str(uuid.uuid4())[:8]
    output_path = AUDIO_DIR / f"{audio_id}_robot.wav"
    _write_wav(audio, str(output_path), tts_engine.sample_rate)
    return str(output_path)


async def _synth_chunk(text: str, emotion: str = "normal", lang: str = "fr") -> str | None:
    """Synthétise une phrase avec pauses naturelles + effet robot sox adapté à l'émotion."""
    def _work():
        aid = str(uuid.uuid4())[:8]
        temp_path = AUDIO_DIR / f"{aid}_clean.wav"
        robot_path = AUDIO_DIR / f"{aid}_robot.wav"

        try:
            vlog(f"TTS_CHUNK_START len={len(text)} lang={lang}")
            tts_engine.synthesize_to_wav(text, str(temp_path), length_scale=1.05, natural_pauses=True, lang=lang)
            vlog("TTS_CHUNK_DONE")
            apply_robot_effect_sox(str(temp_path), str(robot_path), emotion)
            temp_path.unlink(missing_ok=True)
            return f"/audio/{robot_path.name}"
        except Exception as e:
            vlog(f"TTS_CHUNK_ERROR {e}")
            return None
    return await asyncio.get_running_loop().run_in_executor(None, _work)


# ── LLM via llama.cpp server ────────────────────────────────────────────
# Entités privées internes — ne pas chercher sur le web (évite les homonymes)
_PRIVATE_ENTITIES = re.compile(
    r"\b(mario\s*ravasi|za\s*elettronica|manix|emmanuel\s*gelinne|kyronex|kitt\s*franco|"
    r"start_kyronex|kyronex_server)\b",
    re.I
)

# Mots-clés qui déclenchent une recherche web (actualité, météo, prix, personnes publiques, événements)
_SEARCH_TRIGGERS = re.compile(
    r"\b(actualit[eé]|news|nouvelle[s]?|m[eé]t[eé]o|temps\s+qu.il\s+fait|"
    r"aujourd.hui|ce\s+(soir|matin|midi|week.end)|en\s+ce\s+moment|"
    r"prix\s+d[ue]|combien\s+co[uû]te|sortie\s+de|derni[eè]re?\s+version|"
    r"r[eé]cent|vient\s+de|champion[s]?\s+du\s+monde|[eé]l[eé]ction[s]?|"
    r"qui\s+a\s+gagn[eé]|score|r[eé]sultat|classement|top\s+\d|"
    r"film[s]?\s+du\s+moment|s[eé]rie[s]?\s+populaire|"
    r"quel\s+(est|sont)\s+les?\s+(meilleur|derni|nouveau|principal)|"
    r"quelle\s+(est|sont)\s+les?\s+(meilleur|derni|nouveau|principal)|"
    r"d[eé]finition\s+de|qu.est.ce\s+que\s+[a-z]{3,}|wikipedia|explique.moi)\b",
    re.I
)

# ── RAG Local — Système de connaissance interne ──────────────────────────
_KNOWLEDGE_FILES = [
    "GEMINI.md", "CLAUDE.md", "SUPER_NOTES.md", "GEMINI_MODIF_NOTES.md",
    "BACKUP_RESTORE.md", "TRANSFERT_HTML.md", "KITT_COMMANDES.pdf"
]
_knowledge_cache = {}

def load_local_knowledge():
    """Charge les fichiers de documentation pour le RAG local."""
    for fn in _KNOWLEDGE_FILES:
        path = BASE_DIR / fn
        if path.exists():
            try:
                # Si PDF, on ne peut pas lire le texte sans bibliothèque, 
                # on se contente des .md pour le moment
                if fn.endswith(".md"):
                    content = path.read_text(encoding="utf-8")
                    # Nettoyer un peu le markdown (enlever trop de sauts de ligne)
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    _knowledge_cache[fn] = content
                    print(f"[RAG] Indexé: {fn} ({len(content)} chars)")
            except Exception as e:
                print(f"[RAG] Erreur indexation {fn}: {e}")

load_local_knowledge()

async def search_local_knowledge(query: str, max_chars: int = 1500) -> str:
    """Recherche simple par mots-clés dans les fichiers indexés."""
    keywords = [w.lower() for w in re.findall(r'\w{4,}', query) if len(w) > 3]
    if not keywords:
        return ""
    
    hits = []
    for fn, content in _knowledge_cache.items():
        score = sum(1 for k in keywords if k in content.lower())
        if score > 0:
            hits.append((score, fn, content))
    
    if not hits:
        return ""
    
    # Trier par score et prendre le meilleur
    hits.sort(key=lambda x: x[0], reverse=True)
    best_fn = hits[0][1]
    best_content = hits[0][2]
    
    # Extraire un snippet pertinent ou les 1500 premiers caractères
    # Pour faire simple, on prend les 1500 premiers chars du fichier le plus pertinent
    return f"Fichier: {best_fn}\n{best_content[:max_chars]}..."

async def web_search(query: str, max_results: int = 3) -> str:
    """Recherche DuckDuckGo async uniquement si nécessaire.
    Ignorée pour entités privées ou questions KITT-spécifiques."""
    # Ne chercher que si un mot-clé d'actualité/info est présent
    if not _SEARCH_TRIGGERS.search(query):
        return ""
    # Ne pas chercher si la requête concerne une entité privée (évite homonymes)
    if _PRIVATE_ENTITIES.search(query):
        print(f"[WEB] Entité privée — pas de recherche: {query[:50]}", flush=True)
        return ""
    try:
        from ddgs import DDGS
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        results = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(None, _search),
            timeout=6.0
        )
        if not results:
            return ""
        parts = []
        for r in results[:max_results]:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()[:200]
            if title or body:
                parts.append(f"• {title}: {body}")
        return "\n".join(parts)
    except Exception as e:
        print(f"[WEB_SEARCH] Erreur: {e}", flush=True)
        return ""


async def query_llm(user_message: str, history: list, user_name: str = "", user_lang: str = "") -> str:
    # Recherche locale (RAG)
    local_info = await search_local_knowledge(user_message)
    
    # Enrichissement web systématique
    web_info = await web_search(user_message)
    
    enriched_msg = user_message
    if local_info:
        enriched_msg = f"[CONNAISSANCE LOCALE (Prioritaire):\n{local_info}]\n{enriched_msg}"
        print(f"[RAG] {len(local_info)} chars injectés", flush=True)
    
    if web_info:
        enriched_msg = f"[INFO WEB:\n{web_info}]\n{enriched_msg}"
        print(f"[WEB] {len(web_info)} chars injectés", flush=True)

    messages = [{"role": "system", "content": get_system_prompt(user_name, user_lang)}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": enriched_msg})

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.05,
        "repeat_penalty": 1.1,
        "repeat_last_n": 64,
        "stream": False,
    }

    n_msgs = len(messages)
    vlog(f"LLM_START msgs={n_msgs}")
    t0 = time.time()
    session = await get_llm_session()
    async with session.post(
        f"{LLAMA_SERVER}/v1/chat/completions",
        json=payload,
    ) as resp:
        if resp.status != 200:
            raise RuntimeError(f"LLM erreur {resp.status}")
        data = await resp.json()

    ms = (time.time() - t0) * 1000
    reply = data["choices"][0]["message"]["content"].strip()
    vlog(f"LLM_DONE {ms:.0f}ms tokens_out={len(reply.split())}")
    print(f"[LLM] {ms:.0f}ms | {reply[:80]}...")
    return reply


# ── Conversations en mémoire ────────────────────────────────────────────
conversations: dict = {}

# ── Nettoyage RAM automatique (comme jtop "C") ────────────────────────
_message_count = 0
CACHE_CLEAR_EVERY = 3  # Libérer le cache RAM tous les 3 messages (anti-OOM)

def _clear_ram_cache():
    """Équivalent du 'C' de jtop : sysctl vm.drop_caches=3"""
    vlog("RAM_CLEAR_START")
    try:
        subprocess.run(["sudo", "sysctl", "vm.drop_caches=3"],
                       capture_output=True, timeout=3)
        print("[RAM] Cache libéré (drop_caches=3)")
    except Exception as e:
        print(f"[RAM] Erreur clear cache: {e}")


# ── Function Calling — commandes directes (sans LLM) ─────────────────────
_FUNC_PATTERNS = [
    (re.compile(r"\b(quelle heure|heure est.il|l.heure)\b", re.I), "time"),
    (re.compile(r"\b(quel(?:le)? date|date (?:d')?aujourd|on est quel jour|quel jour)\b", re.I), "date"),
    (re.compile(r"\b(état (?:du )?syst[eè]me|état système|status syst|diagnostic|tes capteurs|ta sant[ée]|comment (?:tu )?vas.tu)\b", re.I), "system"),
    (re.compile(r"\b(m[eé]t[eé]o|temps (?:qu.il fait|dehors)|temp[eé]rature ext[eé]rieure|fera.t.il)\b", re.I), "weather"),
    (re.compile(r"\b(?:mets? (?:un )?)?timer?\s*(?:de\s+)?(\d+)\s*(min|sec|minute|seconde)", re.I), "timer"),
]

_active_timers: list = []

async def _run_timer(seconds: int, label: str):
    """Timer qui joue une alerte après N secondes."""
    await asyncio.sleep(seconds)
    # Jouer alerte sonore
    try:
        proc = await asyncio.create_subprocess_exec(
            "play", "-q", "-n",
            "synth", "0.2", "sine", "880",
            "synth", "0.1", "sine", "0",
            "synth", "0.2", "sine", "880",
            "synth", "0.1", "sine", "0",
            "synth", "0.3", "sine", "1100",
            "gain", "-14",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except Exception:
        pass
    await broadcast_monitor({"type": "timer_done", "label": label})


def _get_system_status() -> str:
    """Lit RAM, VRAM, température GPU, uptime."""
    info = []
    # RAM
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemAvailable:"):
                    mem[parts[0]] = int(parts[1]) // 1024  # MB
        total = mem.get("MemTotal:", 0)
        avail = mem.get("MemAvailable:", 0)
        used = total - avail
        info.append(f"RAM: {used}MB/{total}MB ({avail}MB libre)")
    except Exception:
        pass
    # GPU Temperature
    try:
        with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
            temp = int(f.read().strip()) / 1000
        info.append(f"Température: {temp:.1f}°C")
    except Exception:
        pass
    # Uptime
    try:
        with open("/proc/uptime") as f:
            up = float(f.read().split()[0])
        h, m = int(up // 3600), int((up % 3600) // 60)
        info.append(f"Uptime: {h}h{m:02d}m")
    except Exception:
        pass
    return " | ".join(info) if info else "Systèmes opérationnels."


async def _get_weather() -> str:
    """Récupère la météo via wttr.in (gratuit, pas d'API key)."""
    try:
        session = await get_llm_session()
        async with session.get("https://wttr.in/?format=%l:+%c+%t+%h+%w&lang=fr", timeout=aiohttp_client.ClientTimeout(total=5)) as r:
            if r.status == 200:
                return (await r.text()).strip()
    except Exception:
        pass
    return "Capteurs météo indisponibles."


def check_function_call(user_msg: str) -> tuple[str | None, str | None]:
    """Vérifie si le message correspond à une commande directe.
    Retourne (type, réponse) ou (None, None)."""
    for pattern, func_type in _FUNC_PATTERNS:
        m = pattern.search(user_msg)
        if m:
            return func_type, m
    return None, None


async def execute_function(func_type: str, match, user_name: str = "Manix") -> str:
    """Exécute une commande directe et retourne la réponse KITT."""
    if func_type == "time":
        now = datetime.now()
        return f"Il est exactement {now.strftime('%H heures %M')}, {user_name}. Mes circuits sont synchronisés à la milliseconde près."
    elif func_type == "date":
        now = datetime.now()
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        return f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}. Mon calendrier interne est parfaitement calibré."
    elif func_type == "system":
        status = _get_system_status()
        return f"Diagnostic de mes systèmes : {status} Tous mes circuits sont opérationnels."
    elif func_type == "weather":
        weather = await _get_weather()
        return f"D'après mes capteurs atmosphériques : {weather}"
    elif func_type == "timer":
        val = int(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("min"):
            seconds = val * 60
            label = f"{val} minute{'s' if val > 1 else ''}"
        else:
            seconds = val
            label = f"{val} seconde{'s' if val > 1 else ''}"
        task = asyncio.create_task(_run_timer(seconds, label))
        _active_timers.append(task)
        return f"Affirmatif. Timer de {label} activé. Je vous alerterai à l'expiration."
    return ""


# ── Handlers HTTP ────────────────────────────────────────────────────────
async def handle_chat(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)

    user_msg = body.get("message", "").strip()
    session_id = body.get("session_id", "default")
    want_audio = body.get("audio", True)
    _cp = request.transport.get_extra_info("peername")
    _cip = _cp[0] if _cp else "inconnu"
    _cmac = resolve_mac(_cip)
    user_lang_pref_c = _get_user_lang(_cmac)
    client_lang = body.get("lang", "")
    lang = user_lang_pref_c if user_lang_pref_c else (_map_whisper_lang(client_lang) if client_lang else _detect_lang(user_msg))

    if not user_msg:
        return web.json_response({"error": "Message vide"}, status=400)

    if session_id not in conversations:
        conversations[session_id] = []

    t_total = time.time()
    user_display = body.get("user_name", "").strip() or get_user_display_name(request)

    # Function calling (interception avant LLM)
    func_type, func_match = check_function_call(user_msg)
    if func_type:
        func_reply = await execute_function(func_type, func_match, user_display)
        asyncio.create_task(broadcast_monitor({"type": "user_msg", "user": user_display, "session_id": session_id, "message": user_msg}))
        asyncio.create_task(broadcast_monitor({"type": "assistant_msg", "user": user_display, "session_id": session_id, "message": func_reply}))
        conversations[session_id].append({"role": "user", "content": user_msg})
        conversations[session_id].append({"role": "assistant", "content": func_reply})
        print(f"[FUNCTION] {func_type} → {func_reply[:70]}", flush=True)
        # TTS pour function call
        audio_url = None
        tts_ms = 0
        if want_audio:
            t_tts = time.time()
            try:
                emotion = detect_emotion(func_reply)
                audio_path = await text_to_speech(func_reply, emotion, lang)
                audio_url = f"/audio/{Path(audio_path).name}"
                tts_ms = (time.time() - t_tts) * 1000
            except Exception as e:
                print(f"[TTS ERREUR] {e}")
        return web.json_response({
            "reply": func_reply, "audio_url": audio_url,
            "session_id": session_id,
            "timing": {"llm_ms": 0, "tts_ms": round(tts_ms), "total_ms": round((time.time() - t_total) * 1000)}
        })

    # LLM
    t_llm = time.time()
    try:
        reply = await query_llm(user_msg, conversations[session_id], user_display, user_lang_pref_c)
    except Exception as e:
        return web.json_response({"error": f"Erreur LLM: {e}"}, status=503)
    llm_ms = (time.time() - t_llm) * 1000

    conversations[session_id].append({"role": "user", "content": user_msg})
    conversations[session_id].append({"role": "assistant", "content": reply})

    # Extraction mémoire
    if _MEMORY_FORGET.search(user_msg):
        clear_memory_for_user(user_display)
    else:
        fact = extract_memory_fact(user_msg, user_display)
        if fact:
            add_memory(fact, user_display)

    # Nettoyage RAM automatique tous les N messages
    global _message_count
    _message_count += 1
    if _message_count % CACHE_CLEAR_EVERY == 0:
        await asyncio.get_running_loop().run_in_executor(None, _clear_ram_cache)

    asyncio.create_task(broadcast_monitor({"type": "user_msg", "user": user_display, "session_id": session_id, "message": user_msg}))
    asyncio.create_task(broadcast_monitor({"type": "assistant_msg", "user": user_display, "session_id": session_id, "message": reply}))

    # Sauvegarde automatique de la conversation pour l'archive
    peername_info = request.transport.get_extra_info("peername")
    async def _auto_save_conv(pname):
        try:
            ip = pname[0] if pname else "inconnu"
            mac = resolve_mac(ip)
            # Utiliser le nom stocké pour le MAC ou le user_display
            name = _get_user_name(mac) or user_display
            safe = _conv_safe(name)
            user_dir = CONV_STORE_DIR / safe
            user_dir.mkdir(exist_ok=True)
            # On utilise un fichier par jour/utilisateur pour ne pas trop segmenter
            ts_day = datetime.now().strftime('%Y-%m-%d')
            fpath = user_dir / f"conv_{ts_day}.txt"
            
            ts_time = datetime.now().strftime('%H:%M')
            line_user = f"[{ts_time}] {name.upper()}: {user_msg}\n"
            line_assistant = f"[{ts_time}] KITT: {reply}\n"
            
            with open(fpath, "a", encoding="utf-8") as f:
                if f.tell() == 0:
                    f.write(f"Conversation KITT — {name} — {ts_day}\n{'='*50}\n")
                f.write(line_user)
                f.write(line_assistant)
        except Exception as e:
            print(f"[CONV] Erreur auto-save: {e}")

    asyncio.create_task(_auto_save_conv(peername_info))

    # TTS
    audio_url = None
    tts_ms = 0
    if want_audio:
        t_tts = time.time()
        try:
            emotion = detect_emotion(reply)
            audio_path = await text_to_speech(reply, emotion, lang)
            audio_url = f"/audio/{Path(audio_path).name}"
            tts_ms = (time.time() - t_tts) * 1000
        except Exception as e:
            print(f"[TTS ERREUR] {e}")

    total_ms = (time.time() - t_total) * 1000

    return web.json_response({
        "reply": reply,
        "audio_url": audio_url,
        "session_id": session_id,
        "timing": {
            "llm_ms": round(llm_ms),
            "tts_ms": round(tts_ms),
            "total_ms": round(total_ms),
        }
    })


async def handle_chat_stream(request: web.Request) -> web.StreamResponse:
    """POST /api/chat/stream — Streaming chat, texte token par token puis audio."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)

    user_msg = body.get("message", "").strip()
    session_id = body.get("session_id", "default")
    # Résolution MAC pour préférences utilisateur persistantes
    _sp = request.transport.get_extra_info("peername")
    _sip = _sp[0] if _sp else "inconnu"
    _smac = resolve_mac(_sip)
    user_lang_pref = _get_user_lang(_smac)
    # Priorité langue : préférence stockée > Whisper > auto-détection
    client_lang = body.get("lang", "")
    lang = user_lang_pref if user_lang_pref else (_map_whisper_lang(client_lang) if client_lang else _detect_lang(user_msg))
    if not user_msg:
        return web.json_response({"error": "Message vide"}, status=400)

    global _last_interaction_time
    _last_interaction_time = time.time()

    # Function calling — commandes directes sans LLM
    user_display = body.get("user_name", "").strip() or get_user_display_name(request)
    func_type, func_match = check_function_call(user_msg)
    if func_type:
        func_reply = await execute_function(func_type, func_match, user_display)
        asyncio.create_task(broadcast_monitor({"type": "user_msg", "user": user_display, "session_id": session_id, "message": user_msg}))
        asyncio.create_task(broadcast_monitor({"type": "assistant_msg", "user": user_display, "session_id": session_id, "message": func_reply}))

        if session_id not in conversations:
            conversations[session_id] = []
        conversations[session_id].append({"role": "user", "content": user_msg})
        conversations[session_id].append({"role": "assistant", "content": func_reply})

        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "text/event-stream"
        resp.headers["Cache-Control"] = "no-cache"
        await resp.prepare(request)
        await resp.write(f"data: {json.dumps({'token': func_reply})}\n\n".encode())

        # TTS avec émotion
        emotion = detect_emotion(func_reply)
        tts_task = asyncio.create_task(_synth_chunk(func_reply, emotion, lang))
        audio_url = await tts_task
        if audio_url:
            await resp.write(f"data: {json.dumps({'audio_chunk': audio_url, 'chunk_text': func_reply})}\n\n".encode())

        await resp.write(f"data: {json.dumps({'done': True, 'timing': {'llm_ms': 0, 'tts_ms': 0, 'function': func_type}})}\n\n".encode())
        await resp.write_eof()
        print(f"[FUNCTION] {func_type} → {func_reply[:60]}")
        return resp

    # Auto-detect vision keywords → capture camera + inject context
    global _last_vision_time
    vision_ms = 0
    llm_user_msg = user_msg
    now = time.time()
    if (VISION_SCRIPT.exists()
            and VISION_KEYWORDS.search(user_msg)
            and (now - _last_vision_time) >= VISION_COOLDOWN):
        t_vision = time.time()
        description = await capture_vision()
        vision_ms = (time.time() - t_vision) * 1000
        _last_vision_time = time.time()
        if description:
            print(f"[VISION-AUTO] {vision_ms:.0f}ms | {description[:80]}")
            llm_user_msg = f"[VISION: {description}] {user_msg}"
        else:
            llm_user_msg = f"[VISION: Capteurs visuels indisponibles.] {user_msg}"

    if session_id not in conversations:
        conversations[session_id] = []

    asyncio.create_task(broadcast_monitor({"type": "user_msg", "user": user_display, "session_id": session_id, "message": user_msg}))

    # Enrichissement web systématique (sur le message original, pas la version vision)
    web_info = await web_search(user_msg)
    if web_info:
        llm_user_msg = f"[INFO WEB:\n{web_info}]\n{llm_user_msg}"
        print(f"[WEB] {len(web_info)} chars injectés", flush=True)

    # System prompt adapté à l'utilisateur + préférence langue + mémoire
    messages = [{"role": "system", "content": get_system_prompt(user_display, user_lang_pref)}]
    messages.extend(conversations[session_id][-6:])
    messages.append({"role": "user", "content": llm_user_msg})

    vlog(f"STREAM_LLM_START msgs={len(messages)} user={user_display}")

    resp = web.StreamResponse()
    resp.headers["Content-Type"] = "text/event-stream"
    resp.headers["Cache-Control"] = "no-cache"
    await resp.prepare(request)

    full_reply = ""
    sentence_buf = ""
    tts_items = []  # (chunk_text, asyncio.Task)
    t0 = time.time()
    tts_lang = lang
    tts_lang_locked = bool(user_lang_pref)  # Verrouillé si préférence stockée

    # Fonction pour envoyer l'audio dès qu'il est prêt
    async def send_audio_when_ready(task, chunk_text):
        audio_url = await task
        if audio_url:
            await resp.write(f"data: {json.dumps({'audio_chunk': audio_url, 'chunk_text': chunk_text})}\n\n".encode())

    try:
        session = await get_llm_session()
        async with session.post(
            f"{LLAMA_SERVER}/v1/chat/completions",
            json={"messages": messages, "temperature": 0.7, "max_tokens": 256,
                  "top_p": 0.8, "top_k": 20, "min_p": 0.05,
                  "repeat_penalty": 1.1, "repeat_last_n": 64, "stream": True},
        ) as llm_resp:
            _raw_buf = ""       # Buffer brut accumulatif (pour filtrer <think> multi-tokens)
            _clean_emitted = "" # Texte nettoyé déjà émis au client
            async for line in llm_resp.content:
                text = line.decode("utf-8").strip()
                if text.startswith("data: ") and text != "data: [DONE]":
                    try:
                        chunk = json.loads(text[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            full_reply += delta
                            _raw_buf += delta
                            # Filtrage <think> : blocs complets
                            clean_buf = re.sub(r'<think>.*?</think>', '', _raw_buf, flags=re.DOTALL)
                            # Filtrage tokens spéciaux Qwen
                            clean_buf = re.sub(r'<\|[^|]+\|>', '', clean_buf)
                            # Filtrage bloc <think> en cours (incomplet, sans </think>)
                            if '<think>' in clean_buf:
                                clean_buf = re.sub(r'<think>.*$', '', clean_buf, flags=re.DOTALL)
                            # Émettre seulement le nouveau contenu nettoyé
                            new_content = clean_buf[len(_clean_emitted):]
                            if not new_content:
                                continue
                            _clean_emitted = clean_buf
                            sentence_buf += new_content
                            await resp.write(f"data: {json.dumps({'token': new_content})}\n\n".encode())
                            # Lancer TTS dès qu'une phrase est complète ET envoyer l'audio dès qu'il est prêt
                            match = re.search(r'[.!?…]\s', sentence_buf)
                            if match or sentence_buf.endswith('\n'):
                                if match:
                                    # Extraire seulement jusqu'à la ponctuation (incluse)
                                    end_pos = match.end() - 1  # -1 pour ne pas inclure l'espace après
                                    chunk_text = sentence_buf[:end_pos].strip()
                                    sentence_buf = sentence_buf[end_pos:].lstrip()  # Garder le reste sans espaces début
                                else:
                                    chunk_text = sentence_buf.strip()
                                    sentence_buf = ""
                                if chunk_text and any(c.isalpha() for c in chunk_text):
                                    # Détecter la langue depuis la réponse LLM dès la 1ère phrase
                                    if not tts_lang_locked and len(full_reply) >= 15:
                                        detected = _detect_lang(full_reply)
                                        if detected != tts_lang:
                                            print(f"[LANG] Réponse détectée: {tts_lang}→{detected}", flush=True)
                                        tts_lang = detected
                                        tts_lang_locked = True
                                    emotion = detect_emotion(full_reply)
                                    tts_task = asyncio.create_task(_synth_chunk(chunk_text, emotion, tts_lang))
                                    tts_items.append(tts_task)
                                    asyncio.create_task(send_audio_when_ready(tts_task, chunk_text))
                    except (json.JSONDecodeError, KeyError):
                        pass
    except Exception as e:
        print(f"[LLM] Erreur stream: {e}")
        if not full_reply:
            full_reply = "Mes circuits ont subi une micro-interruption. Reformulez votre demande."
            await resp.write(f"data: {json.dumps({'token': full_reply})}\n\n".encode())

    llm_ms = (time.time() - t0) * 1000
    emotion = detect_emotion(full_reply)
    print(f"[EMOTION] {emotion}")

    # TTS du reste de texte (si phrase incomplète à la fin)
    if sentence_buf.strip():
        rest = sentence_buf.strip()
        tts_task = asyncio.create_task(_synth_chunk(rest, emotion, tts_lang))
        tts_items.append(tts_task)
        asyncio.create_task(send_audio_when_ready(tts_task, rest))

    # Nettoyer full_reply avant historique (supprimer blocs <think> résiduels)
    full_reply_clean = re.sub(r'<think>.*?</think>', '', full_reply, flags=re.DOTALL)
    full_reply_clean = re.sub(r'<\|[^|]+\|>', '', full_reply_clean).strip()
    if not full_reply_clean:
        full_reply_clean = full_reply.strip()

    conversations[session_id].append({"role": "user", "content": user_msg})
    conversations[session_id].append({"role": "assistant", "content": full_reply_clean})

    # Mémoire persistante — extraire les faits du message utilisateur
    if _MEMORY_FORGET.search(user_msg):
        clear_memory_for_user(user_display)
    else:
        fact = extract_memory_fact(user_msg, user_display)
        if fact:
            add_memory(fact, user_display)

    # Nettoyage RAM automatique
    global _message_count
    _message_count += 1
    if _message_count % CACHE_CLEAR_EVERY == 0:
        await asyncio.get_running_loop().run_in_executor(None, _clear_ram_cache)

    asyncio.create_task(broadcast_monitor({"type": "assistant_msg", "user": user_display, "session_id": session_id, "message": full_reply}))

    # Sauvegarde automatique de la conversation pour l'archive
    peername_info = request.transport.get_extra_info("peername")
    async def _auto_save_conv(pname):
        try:
            ip = pname[0] if pname else "inconnu"
            mac = resolve_mac(ip)
            # Utiliser le nom stocké pour le MAC ou le user_display
            name = _get_user_name(mac) or user_display
            safe = _conv_safe(name)
            user_dir = CONV_STORE_DIR / safe
            user_dir.mkdir(exist_ok=True)
            # On utilise un fichier par jour/utilisateur pour ne pas trop segmenter
            ts_day = datetime.now().strftime('%Y-%m-%d')
            fpath = user_dir / f"conv_{ts_day}.txt"
            
            ts_time = datetime.now().strftime('%H:%M')
            line_user = f"[{ts_time}] {name.upper()}: {user_msg}\n"
            line_assistant = f"[{ts_time}] KITT: {full_reply}\n"
            
            with open(fpath, "a", encoding="utf-8") as f:
                if f.tell() == 0:
                    f.write(f"Conversation KITT — {name} — {ts_day}\n{'='*50}\n")
                f.write(line_user)
                f.write(line_assistant)
        except Exception as e:
            print(f"[CONV] Erreur auto-save (stream): {e}")

    asyncio.create_task(_auto_save_conv(peername_info))

    # Attendre que tous les TTS soient terminés avant d'envoyer le message "done"
    t_tts = time.time()
    if tts_items:
        await asyncio.gather(*tts_items, return_exceptions=True)
    tts_ms = (time.time() - t_tts) * 1000

    timing = {'llm_ms': round(llm_ms), 'tts_ms': round(tts_ms), 'emotion': emotion}
    if vision_ms:
        timing['vision_ms'] = round(vision_ms)
    await resp.write(f"data: {json.dumps({'done': True, 'timing': timing})}\n\n".encode())

    await resp.write_eof()
    return resp


async def handle_stt(request: web.Request) -> web.Response:
    """POST /api/stt — Transcription audio (multipart avec fichier audio)."""
    reader = await request.multipart()
    audio_data = None

    while True:
        part = await reader.next()
        if part is None:
            break
        if part.name == "audio":
            audio_data = await part.read()

    if not audio_data:
        return web.json_response({"error": "Pas d'audio reçu"}, status=400)

    # Sauvegarder temporairement le fichier audio
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_data)
        tmp_path = f.name

    # Option 1 : forcer la langue préférée de l'utilisateur dans Whisper
    peername = request.transport.get_extra_info("peername")
    _ip = peername[0] if peername else "inconnu"
    _mac = resolve_mac(_ip)
    user_lang = _get_user_lang(_mac) or "fr"  # défaut: français

    t0 = time.time()
    try:
        vlog("STT_START")
        segments, info = whisper_model.transcribe(tmp_path, language=user_lang, beam_size=2, vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        stt_ms = (time.time() - t0) * 1000

        # Option 3 : si confiance faible et langue par défaut, retry en fr
        if not _get_user_lang(_mac) and info.language_probability < 0.75 and info.language != "fr":
            print(f"[STT] Confiance faible ({info.language_probability:.2f}, detecte={info.language}), retry fr")
            segs2, info2 = whisper_model.transcribe(tmp_path, language="fr", beam_size=2, vad_filter=True)
            text2 = " ".join(seg.text.strip() for seg in segs2).strip()
            if text2:
                text, info = text2, info2
            stt_ms = (time.time() - t0) * 1000

        vlog(f"STT_DONE {stt_ms:.0f}ms lang={info.language}({info.language_probability:.2f})")
        print(f"[STT] {stt_ms:.0f}ms | lang={info.language}({info.language_probability:.2f}) | {text[:80]}")
    except Exception as e:
        vlog(f"STT_ERROR {e}")
        os.unlink(tmp_path)
        return web.json_response({"error": f"STT erreur: {e}"}, status=500)

    os.unlink(tmp_path)
    return web.json_response({"text": text, "language": info.language, "stt_ms": round(stt_ms)})


# ── Vision daemon persistant ─────────────────────────────────────────────
_vision_proc = None
_vision_lock = asyncio.Lock()


async def _start_vision_daemon():
    """Démarre le daemon vision (modèle chargé une seule fois en mémoire)."""
    global _vision_proc
    if _vision_proc is not None and _vision_proc.returncode is None:
        return  # déjà actif
    _vision_proc = await asyncio.create_subprocess_exec(
        "/usr/bin/python3", str(VISION_SCRIPT), "--daemon",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        ready = await asyncio.wait_for(_vision_proc.stdout.readline(), timeout=30)
        print(f"[VISION] Daemon démarré: {ready.decode().strip()}", flush=True)
    except asyncio.TimeoutError:
        print("[VISION] Daemon timeout au démarrage", flush=True)
        _vision_proc.kill()
        _vision_proc = None


async def capture_vision() -> str | None:
    """Envoie une commande au daemon vision et retourne la description."""
    global _vision_proc
    async with _vision_lock:
        try:
            if _vision_proc is None or _vision_proc.returncode is not None:
                await _start_vision_daemon()
            if _vision_proc is None:
                return None
            _vision_proc.stdin.write(b"capture\n")
            await _vision_proc.stdin.drain()
            line = await asyncio.wait_for(_vision_proc.stdout.readline(), timeout=15)
            if not line:
                raise RuntimeError("Daemon vision: réponse vide")
            data = json.loads(line.decode())
            if "error" in data:
                print(f"[VISION] {data['error']}")
                return None
            return data.get("description")
        except Exception as e:
            print(f"[VISION] Exception: {e}")
            # Tuer le daemon défaillant — il sera relancé au prochain appel
            if _vision_proc and _vision_proc.returncode is None:
                _vision_proc.kill()
            _vision_proc = None
            return None


async def _capture_vision_persons() -> int:
    """Retourne le nb de personnes détectées (-1 si erreur/caméra indisponible)."""
    global _vision_proc
    async with _vision_lock:
        try:
            if _vision_proc is None or _vision_proc.returncode is not None:
                await _start_vision_daemon()
            if _vision_proc is None:
                return -1
            _vision_proc.stdin.write(b"capture\n")
            await _vision_proc.stdin.drain()
            line = await asyncio.wait_for(_vision_proc.stdout.readline(), timeout=15)
            if not line:
                return -1
            data = json.loads(line.decode())
            if "error" in data:
                return -1
            objects = data.get("objects", [])
            return sum(1 for o in objects if o.get("label") == "personne")
        except Exception as e:
            print(f"[VIGILANCE] Erreur capture: {e}")
            if _vision_proc and _vision_proc.returncode is None:
                _vision_proc.kill()
            _vision_proc = None
            return -1


async def handle_vision(request: web.Request) -> web.StreamResponse:
    """POST /api/vision — Capture camera + detect objects, then chat with context."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)

    user_msg = body.get("message", "").strip() or "Que vois-tu ?"
    session_id = body.get("session_id", "default")

    if session_id not in conversations:
        conversations[session_id] = []

    user_display = get_user_display_name(request)
    asyncio.create_task(broadcast_monitor({"type": "user_msg", "user": user_display, "session_id": session_id, "message": user_msg}))

    # Capture + detect
    t_vision = time.time()
    description = await capture_vision()
    vision_ms = (time.time() - t_vision) * 1000

    if description:
        print(f"[VISION] {vision_ms:.0f}ms | {description[:80]}")
        augmented_msg = f"[VISION: {description}] {user_msg}"
    else:
        augmented_msg = f"[VISION: Capteurs visuels indisponibles.] {user_msg}"

    # Stream response (same as handle_chat_stream but with augmented message)
    messages = [{"role": "system", "content": get_system_prompt(user_display)}]
    messages.extend(conversations[session_id][-6:])
    messages.append({"role": "user", "content": augmented_msg})

    resp = web.StreamResponse()
    resp.headers["Content-Type"] = "text/event-stream"
    resp.headers["Cache-Control"] = "no-cache"
    await resp.prepare(request)

    full_reply = ""
    sentence_buf = ""
    tts_items = []  # (chunk_text, asyncio.Task)
    t0 = time.time()

    try:
        session = await get_llm_session()
        async with session.post(
            f"{LLAMA_SERVER}/v1/chat/completions",
            json={"messages": messages, "temperature": 0.7, "max_tokens": 256,
                  "top_p": 0.8, "top_k": 20, "min_p": 0.05,
                  "repeat_penalty": 1.1, "repeat_last_n": 64, "stream": True},
        ) as llm_resp:
            _raw_buf_v = ""
            _clean_emitted_v = ""
            async for line in llm_resp.content:
                text = line.decode("utf-8").strip()
                if text.startswith("data: ") and text != "data: [DONE]":
                    try:
                        chunk = json.loads(text[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            full_reply += delta
                            _raw_buf_v += delta
                            clean_buf_v = re.sub(r'<think>.*?</think>', '', _raw_buf_v, flags=re.DOTALL)
                            clean_buf_v = re.sub(r'<\|[^|]+\|>', '', clean_buf_v)
                            if '<think>' in clean_buf_v:
                                clean_buf_v = re.sub(r'<think>.*$', '', clean_buf_v, flags=re.DOTALL)
                            new_content_v = clean_buf_v[len(_clean_emitted_v):]
                            if not new_content_v:
                                continue
                            _clean_emitted_v = clean_buf_v
                            sentence_buf += new_content_v
                            await resp.write(f"data: {json.dumps({'token': new_content_v})}\n\n".encode())
                            if re.search(r'[.!?…]\s', sentence_buf) or sentence_buf.endswith('\n'):
                                chunk_text = sentence_buf.strip()
                                sentence_buf = ""
                                if chunk_text and any(c.isalpha() for c in chunk_text):
                                    chunk_emotion = detect_emotion(full_reply)
                                    tts_items.append((chunk_text, asyncio.create_task(_synth_chunk(chunk_text, chunk_emotion))))
                    except (json.JSONDecodeError, KeyError):
                        pass
    except Exception as e:
        print(f"[LLM] Erreur stream: {e}")
        if not full_reply:
            full_reply = "Mes circuits ont subi une micro-interruption. Reformulez votre demande."
            await resp.write(f"data: {json.dumps({'token': full_reply})}\n\n".encode())

    llm_ms = (time.time() - t0) * 1000
    vision_emotion = detect_emotion(full_reply)

    if sentence_buf.strip():
        rest = sentence_buf.strip()
        tts_items.append((rest, asyncio.create_task(_synth_chunk(rest, vision_emotion))))

    # Store in history (user sees original message, not augmented)
    conversations[session_id].append({"role": "user", "content": user_msg})
    conversations[session_id].append({"role": "assistant", "content": full_reply})

    # Nettoyage RAM automatique tous les N messages
    global _message_count
    _message_count += 1
    if _message_count % CACHE_CLEAR_EVERY == 0:
        await asyncio.get_running_loop().run_in_executor(None, _clear_ram_cache)

    asyncio.create_task(broadcast_monitor({"type": "assistant_msg", "user": user_display, "session_id": session_id, "message": full_reply}))

    # Envoyer les chunks audio avec leur texte associé
    t_tts = time.time()
    tts_ms = 0
    try:
        for chunk_text, task in tts_items:
            audio_url = await task
            if audio_url:
                await resp.write(f"data: {json.dumps({'audio_chunk': audio_url, 'chunk_text': chunk_text})}\n\n".encode())
        tts_ms = (time.time() - t_tts) * 1000
    except Exception as e:
        print(f"[TTS] Erreur chunk: {e}")

    timing = {'vision_ms': round(vision_ms), 'llm_ms': round(llm_ms), 'tts_ms': round(tts_ms)}
    await resp.write(f"data: {json.dumps({'done': True, 'timing': timing})}\n\n".encode())

    await resp.write_eof()
    return resp


async def handle_health(request: web.Request) -> web.Response:
    llm_ok = False
    try:
        session = await get_llm_session()
        async with session.get(f"{LLAMA_SERVER}/health") as r:
            llm_ok = r.status == 200
    except Exception:
        pass

    return web.json_response({
        "status": "en ligne" if llm_ok else "llm_hors_ligne",
        "kitt": "Knight Industries Two Thousand — opérationnel",
        "llm_server": llm_ok,
    })


async def handle_reset(request: web.Request) -> web.Response:
    body = await request.json()
    session_id = body.get("session_id", "default")
    conversations.pop(session_id, None)
    return web.json_response({"status": "conversation réinitialisée"})


async def handle_memory(request: web.Request) -> web.Response:
    """GET /api/memory — Retourne les souvenirs de KITT."""
    return web.json_response(_memory)


async def handle_memory_add(request: web.Request) -> web.Response:
    """POST /api/memory — Ajoute un souvenir manuellement."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    fact = body.get("fact", "").strip()
    if not fact:
        return web.json_response({"error": "Fait requis"}, status=400)
    user = body.get("user", "manual")
    add_memory(fact, user)
    return web.json_response({"ok": True, "total": len(_memory["facts"])})


async def handle_index(request: web.Request) -> web.Response:
    return web.FileResponse(STATIC_DIR / "index.html")


# ── KITT Proactif — messages spontanés ────────────────────────────────────
_proactive_ws: set = set()  # WebSocket clients for proactive messages
_last_greeting_hour = -1
_last_temp_alert = 0.0

# ── Mode Vigilance ──────────────────────────────────────────────────────
_vigilance_enabled: bool = False
_vigilance_last_count: int = -1   # nb personnes détectées au dernier check
_vigilance_last_check: float = 0.0
_last_interaction_time: float = time.time()  # dernière interaction utilisateur

async def handle_proactive_ws(request: web.Request) -> web.WebSocketResponse:
    """GET /api/proactive/ws — WebSocket pour recevoir les messages proactifs de KITT."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    _proactive_ws.add(ws)
    print(f"[PROACTIVE] Client connecté")
    try:
        async for msg in ws:
            pass
    finally:
        _proactive_ws.discard(ws)
        print(f"[PROACTIVE] Client déconnecté")
    return ws


async def send_proactive(message: str, emotion: str = "normal"):
    """Envoie un message proactif à tous les clients connectés avec TTS."""
    if not _proactive_ws:
        return

    # Anti-superposition : si une interaction chat a eu lieu il y a moins de 10s, on attend
    global _last_interaction_time
    wait_count = 0
    while (time.time() - _last_interaction_time) < 10 and wait_count < 30:
        await asyncio.sleep(2)
        wait_count += 1

    # TTS du message proactif
    audio_url = None
    try:
        audio_url = await _synth_chunk(message, emotion)
    except Exception:
        pass

    payload = json.dumps({
        "type": "proactive",
        "message": message,
        "audio": audio_url,
        "emotion": emotion,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    dead = set()
    for ws in _proactive_ws:
        try:
            await ws.send_str(payload)
        except Exception:
            dead.add(ws)
    if dead:
        _proactive_ws.difference_update(dead)
    print(f"[PROACTIVE] {message[:60]}")


def _read_gpu_temp() -> float:
    """Lit la température GPU/SoC."""
    try:
        with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000
    except Exception:
        return 0.0


def _read_ram_available_mb() -> int:
    """Lit la RAM disponible en MB."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 9999


async def proactive_loop(app):
    """Boucle de surveillance proactive KITT."""
    global _last_greeting_hour, _last_temp_alert
    import random

    # Attendre que le serveur soit prêt
    await asyncio.sleep(10)

    while True:
        try:
            now = datetime.now()
            hour = now.hour

            # Salutations horaires (1 fois par heure, si clients connectés)
            if _proactive_ws and hour != _last_greeting_hour:
                _last_greeting_hour = hour
                greetings = {
                    6: "Bonjour Manix. Mes systèmes sont en ligne. Une nouvelle journée commence.",
                    7: "Il est 7 heures. Tous mes capteurs sont opérationnels. Prêt pour la mission.",
                    12: "Il est midi. Une pause est peut-être nécessaire ? Mes circuits ne connaissent pas la faim, mais je saisis parfaitement le concept.",
                    18: "Bonsoir Manix. J'espère que votre journée a été productive.",
                    22: "Il est 22 heures. Je reste vigilant, mais vous devriez peut-être envisager du repos.",
                    0: "Minuit. Mon scanner veille. Bonne nuit, Manix.",
                }
                if hour in greetings:
                    await send_proactive(greetings[hour], "confident")

            # Alertes température (toutes les 2 minutes max)
            temp = _read_gpu_temp()
            if temp > 70 and (time.time() - _last_temp_alert) > 120:
                _last_temp_alert = time.time()
                if temp > 85:
                    await send_proactive(f"Alerte critique ! Ma température atteint {temp:.0f}°C. Mes circuits sont en surchauffe !", "worried")
                elif temp > 75:
                    await send_proactive(f"Attention. Ma température est à {temp:.0f}°C. Je surveille la situation.", "worried")
                else:
                    await send_proactive(f"Information : température à {temp:.0f}°C. Rien d'alarmant pour le moment.", "normal")

            # Alerte RAM critique
            ram_avail = _read_ram_available_mb()
            if ram_avail < 100 and _proactive_ws:
                await send_proactive(f"Attention Manix. Seulement {ram_avail}MB de RAM disponible. Mes systèmes sont en charge critique.", "worried")

            # ── Mode Vigilance — surveillance caméra ─────────────────
            global _vigilance_last_check, _vigilance_last_count
            now_v = time.time()
            if (_vigilance_enabled and _proactive_ws and VISION_SCRIPT.exists()
                    and (now_v - _vigilance_last_check) >= 20):
                _vigilance_last_check = now_v
                count = await _capture_vision_persons()
                if count >= 0:
                    prev = _vigilance_last_count
                    _vigilance_last_count = count
                    idle = now_v - _last_interaction_time
                    if prev == 0 and count >= 1 and idle > 300:
                        # Terminal inactif depuis 5min — présence détectée
                        await send_vigilance_alert(
                            "Alerte. Présence détectée sur terminal inactif. "
                            "Identité non confirmée."
                        )
                    elif prev >= 1 and count >= 2 and prev < 2:
                        # Présence additionnelle dans la zone
                        await send_vigilance_alert(
                            "Vigilance. Présence non identifiée détectée dans la zone."
                        )

        except Exception as e:
            print(f"[PROACTIVE] Erreur: {e}")

        await asyncio.sleep(60)  # Vérifier toutes les 60 secondes


async def send_vigilance_alert(message: str):
    """Envoie une alerte vigilance (type distinct pour UI rouge + son)."""
    if not _proactive_ws:
        return

    # Anti-superposition : si interaction récente, on attend
    global _last_interaction_time
    wait_count = 0
    while (time.time() - _last_interaction_time) < 10 and wait_count < 30:
        await asyncio.sleep(2)
        wait_count += 1

    audio_url = None
    try:
        audio_url = await _synth_chunk(message, "worried")
    except Exception:
        pass
    payload = json.dumps({
        "type": "vigilance_alert",
        "message": message,
        "audio": audio_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    dead = set()
    for ws in _proactive_ws:
        try:
            await ws.send_str(payload)
        except Exception:
            dead.add(ws)
    if dead:
        _proactive_ws.difference_update(dead)
    print(f"[VIGILANCE] ALERTE: {message[:60]}")


async def handle_vigilance(request: web.Request) -> web.Response:
    """POST /api/vigilance — Active/désactive le mode vigilance caméra."""
    global _vigilance_enabled, _vigilance_last_count
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    _vigilance_enabled = bool(body.get("enabled", False))
    _vigilance_last_count = -1  # reset à chaque toggle
    print(f"[VIGILANCE] Mode {'ACTIVÉ' if _vigilance_enabled else 'DÉSACTIVÉ'}")
    return web.json_response({"vigilance": _vigilance_enabled})


# ── Téléchargement PDFs ──────────────────────────────────────────────────
async def handle_download(request: web.Request) -> web.Response:
    """GET /api/download/{filename} — sert les PDFs de BASE_DIR."""
    filename = request.match_info["filename"]
    if not filename.endswith(".pdf") or "/" in filename or ".." in filename:
        raise web.HTTPForbidden(text="Accès refusé")
    path = BASE_DIR / filename
    if not path.exists():
        raise web.HTTPNotFound(text=f"{filename} introuvable")
    return web.FileResponse(
        path,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


async def handle_git_push_html(request: web.Request) -> web.Response:
    """POST /api/git-push-html — commit + push static/index.html vers GitHub."""
    import asyncio, subprocess
    from datetime import datetime
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(BASE_DIR), "add", "static/index.html",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        proc2 = await asyncio.create_subprocess_exec(
            "git", "-C", str(BASE_DIR), "commit", "-m", f"auto: push index.html via KITT UI ({stamp})",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out2, err2 = await proc2.communicate()
        proc3 = await asyncio.create_subprocess_exec(
            "git", "-C", str(BASE_DIR), "push",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out3, err3 = await proc3.communicate()
        if proc3.returncode == 0:
            return web.json_response({"ok": True, "msg": f"Push OK — {stamp}"})
        else:
            return web.json_response({"ok": False, "msg": err3.decode()[:200]})
    except Exception as e:
        return web.json_response({"ok": False, "msg": str(e)})


async def handle_download_html(request: web.Request) -> web.Response:
    """GET /api/download-html — télécharge le index.html actuel."""
    path = BASE_DIR / "static" / "index.html"
    if not path.exists():
        raise web.HTTPNotFound(text="index.html introuvable")
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return web.FileResponse(
        path,
        headers={"Content-Disposition": f'attachment; filename="kitt-index-{stamp}.html"'}
    )


async def handle_list_pdfs(request: web.Request) -> web.Response:
    """GET /api/pdfs — liste les PDFs disponibles dans BASE_DIR."""
    pdfs = [
        {"name": p.name, "size_kb": round(p.stat().st_size / 1024)}
        for p in sorted(BASE_DIR.glob("*.pdf"))
    ]
    return web.json_response({"pdfs": pdfs})


# ── Night Scheduler — constantes ────────────────────────────────────────
SCHEDULER_PY  = BASE_DIR / "kitt_scheduler.py"
SCHEDULER_PID = BASE_DIR / "kitt_scheduler.pid"
SCHEDULER_CFG = BASE_DIR / "kitt_schedule.json"
SCHEDULER_LOG = Path("/tmp/kitt_scheduler.log")
IMPROVE_SH      = BASE_DIR / "kitt_night_improve.sh"
SITE_IMPROVE_SH = BASE_DIR / "kitt_site_improve.sh"


def _sched_load_cfg() -> dict:
    """Charge kitt_schedule.json ou retourne une config vide."""
    if SCHEDULER_CFG.exists():
        try:
            return json.loads(SCHEDULER_CFG.read_text())
        except Exception:
            pass
    return {"windows": []}


def _sched_save_cfg(cfg: dict):
    SCHEDULER_CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def _sched_is_running() -> int | None:
    """Retourne le PID si le daemon tourne, None sinon."""
    if not SCHEDULER_PID.exists():
        return None
    try:
        pid = int(SCHEDULER_PID.read_text().strip())
        os.kill(pid, 0)  # signal 0 = vérification existence
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        SCHEDULER_PID.unlink(missing_ok=True)
        return None


async def handle_scheduler_status(request: web.Request) -> web.Response:
    pid = _sched_is_running()
    cfg = _sched_load_cfg()
    return web.json_response({
        "active": pid is not None,
        "pid": pid,
        "windows": cfg.get("windows", []),
    })


async def handle_scheduler_start(request: web.Request) -> web.Response:
    pid = _sched_is_running()
    if pid:
        return web.json_response({"ok": True, "pid": pid, "msg": "Déjà actif"})
    env = os.environ.copy()
    env["PATH"] = f"/home/kitt/.local/bin:{env.get('PATH', '')}"
    proc = subprocess.Popen(
        ["python3", str(SCHEDULER_PY), "--daemon"],
        stdout=open(str(SCHEDULER_LOG), "a"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    SCHEDULER_PID.write_text(str(proc.pid))
    return web.json_response({"ok": True, "pid": proc.pid})


async def handle_scheduler_stop(request: web.Request) -> web.Response:
    pid = _sched_is_running()
    if not pid:
        return web.json_response({"ok": True, "msg": "Déjà arrêté"})
    try:
        os.kill(pid, 15)  # SIGTERM
    except ProcessLookupError:
        pass
    SCHEDULER_PID.unlink(missing_ok=True)
    return web.json_response({"ok": True})


async def handle_scheduler_window(request: web.Request) -> web.Response:
    """POST — ajoute une fenêtre planifiée."""
    try:
        data = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="JSON invalide")
    cfg = _sched_load_cfg()
    windows = cfg.setdefault("windows", [])
    wid = str(uuid.uuid4())[:8]
    target = data.get("target", "interface")  # "interface" ou "site"
    script_path = str(SITE_IMPROVE_SH) if target == "site" else str(IMPROVE_SH)
    windows.append({
        "id": wid,
        "name": data.get("name", f"Fenêtre {len(windows)+1}"),
        "start_h": int(data.get("start_h", 22)),
        "start_m": int(data.get("start_m", 0)),
        "end_h": int(data.get("end_h", 6)),
        "end_m": int(data.get("end_m", 0)),
        "iterations": int(data.get("iterations", 10)),
        "days": data.get("days", [0, 1, 2, 3, 4, 5, 6]),
        "enabled": True,
        "target": target,
        "script": script_path,
    })
    _sched_save_cfg(cfg)
    return web.json_response({"ok": True, "id": wid, "windows": cfg["windows"]})


async def handle_scheduler_toggle(request: web.Request) -> web.Response:
    """POST /api/scheduler/window/{wid}/toggle"""
    wid = request.match_info["wid"]
    cfg = _sched_load_cfg()
    for w in cfg.get("windows", []):
        if w["id"] == wid:
            w["enabled"] = not w.get("enabled", True)
            _sched_save_cfg(cfg)
            return web.json_response({"ok": True, "enabled": w["enabled"]})
    raise web.HTTPNotFound(text=f"Fenêtre {wid} introuvable")


async def handle_scheduler_delete(request: web.Request) -> web.Response:
    """DELETE /api/scheduler/window/{wid}"""
    wid = request.match_info["wid"]
    cfg = _sched_load_cfg()
    before = len(cfg.get("windows", []))
    cfg["windows"] = [w for w in cfg.get("windows", []) if w["id"] != wid]
    if len(cfg["windows"]) == before:
        raise web.HTTPNotFound(text=f"Fenêtre {wid} introuvable")
    _sched_save_cfg(cfg)
    return web.json_response({"ok": True, "windows": cfg["windows"]})


async def handle_scheduler_run_now(request: web.Request) -> web.Response:
    """POST — lance N itérations immédiatement."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    iterations = int(data.get("iterations", 1))
    target = data.get("target", "interface")  # "interface" ou "site"
    script = SITE_IMPROVE_SH if target == "site" else IMPROVE_SH
    env = os.environ.copy()
    env["PATH"] = f"/home/kitt/.local/bin:{env.get('PATH', '')}"
    prefix = "kitt_site" if target == "site" else "kitt_now"
    now_log = f"/tmp/{prefix}_{int(time.time())}.log"
    proc = subprocess.Popen(
        ["bash", str(script), str(iterations)],
        stdout=open(now_log, "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    return web.json_response({"ok": True, "pid": proc.pid, "log_path": now_log, "target": target})


async def handle_auto_report(request: web.Request) -> web.Response:
    """GET /api/auto-report — rapport des versions produites par le mode automatique."""
    versions_dir = STATIC_DIR / "versions"
    sessions = {}
    if versions_dir.exists():
        for f in sorted(versions_dir.glob("*.html")):
            name = f.stem  # ex: v01_04h36_animation_messages
            parts = name.split("_", 2)
            if len(parts) < 2:
                continue
            iter_tag = parts[0]   # v00, v01...
            time_tag = parts[1]   # 04h36 ou avant
            desc = parts[2] if len(parts) > 2 else ""
            stat = f.stat()
            import datetime as _dt
            mtime = _dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            # Regrouper par session (heure de modification à la minute)
            session_key = mtime[:13]  # "2026-02-24 04"
            if session_key not in sessions:
                sessions[session_key] = []
            sessions[session_key].append({
                "iter": iter_tag,
                "time": time_tag,
                "desc": desc.replace("_", " "),
                "file": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "lines": sum(1 for _ in f.open(errors="replace")),
                "modified": mtime,
            })
    # Logs récents du site improver
    site_logs = []
    for lf in sorted(Path("/tmp").glob("kitt_site_*.log")):
        txt = lf.read_text(errors="replace")
        for line in txt.splitlines():
            if "SUCCES" in line or "ECHEC" in line or "RAPPORT FINAL" in line:
                site_logs.append(line.strip())
    # Logs récents du night improver
    night_logs = []
    for lf in sorted(Path("/tmp").glob("kitt_now_*.log")):
        txt = lf.read_text(errors="replace")
        for line in txt.splitlines():
            if "SUCCES" in line or "ECHEC" in line or "RAPPORT" in line:
                night_logs.append(line.strip())
    return web.json_response({
        "versions": sessions,
        "total_versions": sum(len(v) for v in sessions.values()),
        "site_log": site_logs[-10:],
        "night_log": night_logs[-10:],
    })


async def handle_scheduler_logs(request: web.Request) -> web.Response:
    """GET — retourne les 30 dernières lignes du log daemon + now logs."""
    lines = []
    # Log daemon
    if SCHEDULER_LOG.exists():
        all_lines = SCHEDULER_LOG.read_text(errors="replace").splitlines()
        lines += all_lines[-20:]
    # Dernier kitt_now_*.log
    now_logs = sorted(Path("/tmp").glob("kitt_now_*.log"))
    if now_logs:
        last = now_logs[-1]
        content = last.read_text(errors="replace").splitlines()
        lines += [f"[{last.name}] {l}" for l in content[-15:]]
    return web.json_response({"lines": lines[-30:]})


# ── Nettoyage audio ─────────────────────────────────────────────────────
async def cleanup_audio(app):
    while True:
        await asyncio.sleep(300)
        now = time.time()
        for f in AUDIO_DIR.glob("*.wav"):
            if now - f.stat().st_mtime > 300:
                f.unlink(missing_ok=True)


# ── Handlers Conversations ────────────────────────────────────────────────

async def handle_conv_identify(request):
    """POST /api/conv/identify — Identifie un utilisateur par MAC ou UUID."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    c_uuid = body.get('uuid') or str(uuid.uuid4())
    ip = request.remote
    mac = None if ip in ('127.0.0.1', '::1') else resolve_mac(ip)
    uid = mac if mac else c_uuid
    users = _conv_load_users()
    if uid in users:
        return web.json_response({"id": uid, "name": users[uid]['name'], "is_new": False})
    return web.json_response({"id": uid, "is_new": True})


async def handle_conv_register(request):
    """POST /api/conv/register — Enregistre un nouvel utilisateur."""
    try:
        b = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    uid  = b.get('id', '').strip()
    name = b.get('name', '').strip()
    if not uid or not name:
        return web.json_response({"error": "id+name requis"}, status=400)
    users = _conv_load_users()
    users[uid] = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "conv_count": 0,
    }
    _conv_save_users(users)
    (CONV_STORE_DIR / _conv_safe(name)).mkdir(exist_ok=True)
    print(f"[CONV] Nouvel utilisateur enregistré : {name} ({uid[:16]})")
    return web.json_response({"ok": True, "name": name})


async def handle_conv_save(request):
    """POST /api/conv/save — Sauvegarde les messages d'une conversation."""
    try:
        b = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    uid  = b.get('id', '').strip()
    msgs = b.get('messages', [])
    if not uid or not msgs:
        return web.json_response({"error": "id+messages requis"}, status=400)
    users = _conv_load_users()
    if uid not in users:
        return web.json_response({"error": "utilisateur inconnu"}, status=404)
    name = users[uid]['name']
    safe = _conv_safe(name)
    user_dir = CONV_STORE_DIR / safe
    user_dir.mkdir(exist_ok=True)
    ts   = datetime.now().strftime('%Y-%m-%d_%H-%M')
    fname = f"conv_{ts}.txt"
    lines = [f"Conversation KITT — {name} — {ts}\n{'='*50}\n"]
    for m in msgs:
        role = m.get('role', 'user')
        text = m.get('text', '').strip()
        t    = m.get('time', '')
        prefix = 'KITT' if role == 'assistant' else name.upper()
        lines.append(f"[{t}] {prefix}: {text}\n")
    (user_dir / fname).write_text(''.join(lines), encoding='utf-8')
    users[uid]['conv_count'] = users[uid].get('conv_count', 0) + 1
    _conv_save_users(users)
    print(f"[CONV] Conversation sauvée : {name}/{fname} ({len(msgs)} messages)")
    return web.json_response({"ok": True, "file": fname})


async def handle_conv_auth(request):
    """POST /api/conv/auth — Authentification admin."""
    try:
        b = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    pwd = b.get('password', '')
    h   = hashlib.sha256(pwd.encode()).hexdigest()
    if h != _CONV_ADMIN_HASH:
        return web.json_response({"error": "Mot de passe incorrect"}, status=401)
    token = str(uuid.uuid4())
    _conv_admin_sessions[token] = time.time() + 3600  # expire dans 1h
    return web.json_response({"ok": True, "token": token})


async def handle_conv_list(request):
    """GET /api/conv/list — Liste toutes les conversations (protégé admin)."""
    if not _conv_check_token(request):
        return web.json_response({"error": "Non autorisé"}, status=401)
    result = []
    users = _conv_load_users()
    uid_by_safe = {_conv_safe(v['name']): k for k, v in users.items()}
    for user_dir in sorted(CONV_STORE_DIR.iterdir()):
        if not user_dir.is_dir():
            continue
        safe = user_dir.name
        uid  = uid_by_safe.get(safe, '')
        name = users.get(uid, {}).get('name', safe) if uid else safe
        files = sorted([f.name for f in user_dir.glob('conv_*.txt')], reverse=True)
        result.append({"user": name, "safe": safe, "count": len(files), "files": files})
    return web.json_response({"users": result})


async def handle_conv_read(request):
    """GET /api/conv/read/{user}/{filename} — Lit un fichier conversation (protégé admin)."""
    if not _conv_check_token(request):
        return web.json_response({"error": "Non autorisé"}, status=401)
    safe_user = request.match_info.get('user', '')
    filename  = request.match_info.get('filename', '')
    # Anti path-traversal
    if '..' in safe_user or '..' in filename or '/' in safe_user or '/' in filename:
        return web.json_response({"error": "Chemin invalide"}, status=400)
    fpath = CONV_STORE_DIR / safe_user / filename
    if not fpath.exists() or not fpath.is_file():
        return web.json_response({"error": "Fichier introuvable"}, status=404)
    content = fpath.read_text(encoding='utf-8')
    return web.json_response({"content": content})


# ── App ──────────────────────────────────────────────────────────────────
def create_app() -> web.Application:
    middlewares = []
    if ACCESS_PASSWORD:
        middlewares.append(auth_middleware)
        print(f"[OK] Protection par mot de passe activée", flush=True)

    app = web.Application(client_max_size=10 * 1024 * 1024, middlewares=middlewares)

    app.router.add_get("/login", handle_login_page)
    app.router.add_post("/login", handle_login_post)
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/chat/stream", handle_chat_stream)
    app.router.add_post("/api/vision", handle_vision)
    app.router.add_get("/api/health", handle_health)
    app.router.add_post("/api/reset", handle_reset)
    app.router.add_post("/api/stt", handle_stt)
    app.router.add_post("/api/set-name", handle_set_name)
    app.router.add_get("/api/whoami", handle_whoami)
    app.router.add_get("/api/monitor/ws", handle_monitor_ws)
    app.router.add_post("/api/set-lang", handle_set_lang)
    app.router.add_post("/api/ping", handle_ping)
    app.router.add_get("/api/stats", handle_stats)
    app.router.add_get("/api/visitors", handle_visitors)
    app.router.add_get("/api/memory", handle_memory)
    app.router.add_post("/api/memory", handle_memory_add)
    app.router.add_get("/api/proactive/ws", handle_proactive_ws)
    app.router.add_post("/api/vigilance", handle_vigilance)
    app.router.add_get("/api/download-html", handle_download_html)
    app.router.add_post("/api/git-push-html", handle_git_push_html)
    # Night Scheduler
    app.router.add_get("/api/scheduler/status", handle_scheduler_status)
    app.router.add_post("/api/scheduler/start", handle_scheduler_start)
    app.router.add_post("/api/scheduler/stop", handle_scheduler_stop)
    app.router.add_post("/api/scheduler/window", handle_scheduler_window)
    app.router.add_post("/api/scheduler/window/{wid}/toggle", handle_scheduler_toggle)
    app.router.add_delete("/api/scheduler/window/{wid}", handle_scheduler_delete)
    app.router.add_post("/api/scheduler/run-now", handle_scheduler_run_now)
    app.router.add_get("/api/auto-report", handle_auto_report)
    app.router.add_get("/api/scheduler/logs", handle_scheduler_logs)
    app.router.add_get("/api/pdfs", handle_list_pdfs)
    app.router.add_get("/api/download/{filename}", handle_download)
    # Conversations
    app.router.add_post("/api/conv/identify", handle_conv_identify)
    app.router.add_post("/api/conv/register", handle_conv_register)
    app.router.add_post("/api/conv/save",     handle_conv_save)
    app.router.add_post("/api/conv/auth",     handle_conv_auth)
    app.router.add_get( "/api/conv/list",     handle_conv_list)
    app.router.add_get( "/api/conv/read/{user}/{filename}", handle_conv_read)
    app.router.add_static("/audio", AUDIO_DIR)
    app.router.add_static("/static", STATIC_DIR)

    async def start_background(app):
        app["cleanup_task"] = asyncio.create_task(cleanup_audio(app))
        app["proactive_task"] = asyncio.create_task(proactive_loop(app))

    async def stop_background(app):
        for key in ("cleanup_task", "proactive_task"):
            task = app.get(key)
            if task:
                task.cancel()
        if _llm_session and not _llm_session.closed:
            await _llm_session.close()
        # Arrêter le daemon vision
        if _vision_proc and _vision_proc.returncode is None:
            _vision_proc.stdin.write(b"quit\n")
            try:
                await asyncio.wait_for(_vision_proc.wait(), timeout=3)
            except asyncio.TimeoutError:
                _vision_proc.kill()

    app.on_startup.append(start_background)
    app.on_cleanup.append(stop_background)
    return app


if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("  KITT — Knight Industries Two Thousand", flush=True)
    print("  By Manix — Jetson Orin Nano Super", flush=True)
    print("=" * 60, flush=True)
    app = create_app()

    cert_dir = BASE_DIR / "certs"
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"

    if cert_file.exists() and key_file.exists():
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(str(cert_file), str(key_file))
        print("  HTTPS actif — https://localhost:3000", flush=True)
    else:
        ssl_ctx = None
        print("  HTTP uniquement — http://localhost:3000", flush=True)

    print("=" * 60, flush=True)
    web.run_app(app, host="0.0.0.0", port=3000, ssl_context=ssl_ctx)
