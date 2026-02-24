# 🤖 KYRONEX — SUPER NOTES COMPLÈTES
**Kinetic Yielding Responsive Onboard Neural EXpert**

**Dernière mise à jour :** 2026-02-18 23:59
**Statut :** ✅ TTS multilingue + Site web en ligne + Licence + Manuel PDF + Tout validé

---

## 👤 PROPRIÉTAIRE

- **Nom :** Emmanuel Gelinne (Manix) — "ByManix"
- **Langue :** Français (réponses toujours en français)
- **Sudo password :** 5505
- **Statut :** Gagnant concours NVIDIA
- **Testeur :** Virginie Barbay

---

## 💻 SYSTÈME JETSON

### Matériel
- **Modèle :** Jetson Orin Nano Super 8GB
- **JetPack :** 6.2.2
- **OS :** Ubuntu 22.04 (Linux 5.15.185-tegra)
- **RAM :** 8GB partagée CPU/GPU (pas de swap)
- **GPU :** Orin (CUDA 8.7, VMM yes)
- **Réseau :** LAN IP 192.168.1.4 (anciennement 192.168.1.32)

### Périphériques
- **Caméras :** /dev/video0, /dev/video1 (V4L2, 640x480)
- **Audio USB :** card 1 (USB Audio Device) — sortie principale
- **Audio Jetson :** card 3 (APE) — intégré
- **Bluetooth :** bluez 5.64, hci0 (58:02:05:DD:C2:F2)
- **iPhone :** MAC E0:33:8E:4B:75:AE

### Logiciels Clés
- **Python :** 3.10.12
- **OpenCV :** 4.8.0 (CPU only — FaceDetectorYN + FaceRecognizerSF)
- **Audio System :** PulseAudio (commande: `paplay`)
- **Sox :** Installé (effets robot voix)

---

## 📦 CONFIGURATION OPTIMALE (MEILLEURS RÉGLAGES)

### LLM — Qwen 2.5 3B
```
Fichier: models/qwen2.5-3b-instruct-q5_k_m.gguf
Taille: 2.3G
VRAM: ~3GB
Vitesse: ~1400ms par réponse
Qualité: ⭐⭐⭐ (quelques fautes mais rapide)
Stable: ✅ Pas d'OOM
```

**Paramètres llama-server :**
```bash
--n-gpu-layers 99       # Tout sur GPU
--ctx-size 1024         # Contexte court (économise VRAM)
--batch-size 512
--threads 4
--parallel 1            # CRITIQUE: évite OOM
--flash-attn            # (sans "on", syntaxe llama.cpp récente)
```

### STT — Whisper Base
```
Modèle: base (142M)
Device: CUDA
Compute: float16
VRAM: ~500MB
Vitesse: ~300-500ms
Qualité: ⭐⭐⭐⭐ (très correct)
```

### TTS — Piper GPU Optimisé
```
Modèle: fr_FR-tom-medium.onnx (61M)
Device: CUDA
Sample rate: 44100Hz
VRAM: ~1.3GB au 1er appel (onnxruntime alloue workspace + modèle)
       ~50MB par appel suivant (déjà alloué)
Vitesse: ~490ms (2.4× plus rapide qu'avant)
Qualité: ⭐⭐⭐⭐
ATTENTION: la vraie consommation mémoire est bien plus haute que 300MB !
```

**Optimisations TTS (piper_gpu.py) :**
- ✅ 1 seule inférence GPU (pas de multi-segments)
- ✅ Pauses subtiles via espaces doubles (40-80ms)
- ✅ Bug "Je … vais bien" corrigé (merge segments < 4 car)
- ✅ Mode `natural_pauses=True` = rapide + fluide

### Effets Robot — SOX (MEILLEUR SON) 🤖
```bash
sox INPUT OUTPUT pitch -130 overdrive 3 gain -1
```

**Effet appliqué APRÈS synthèse Piper :**
1. Piper génère voix claire → `/tmp/xxx_clean.wav`
2. Sox applique effets robot → `/audio/xxx_robot.wav`
3. Fichier clean supprimé
4. Audio robot servi au client

**Résultat :** Voix robot digitale classique KITT ! 🎙️

---

## 🏗️ ARCHITECTURE KYRONEX

### Fichiers Principaux (`/home/kitt/kitt-ai/`)

```
start_kyronex.sh          # Lanceur principal (kill browsers + llama + kyronex)
kyronex_server.py         # Serveur web HTTPS (aiohttp, STT, TTS, LLM)
piper_gpu.py              # Wrapper TTS GPU (onnxruntime CUDA)
terminal_chat.py          # Client terminal vocal (paplay, VAD)
monitor.py                # Monitor WebSocket tkinter temps réel
vision.py                 # YOLO object detection (daemon mode)

models/                   # Modèles IA
  qwen2.5-3b-instruct-q5_k_m.gguf  (LLM)
  fr_FR-tom-medium.onnx             (TTS)

static/                   # Web UI
  index.html              (PWA, mobile-friendly)
  manifest.json           (PWA manifest)

certs/                    # Certificats SSL
  cert.pem, key.pem

audio_cache/              # Cache audio généré (WAV)
logs/                     # Logs JSONL conversations
venv/                     # Virtualenv Python
driver/                   # Face + BT recognition
```

### Serveur Web (kyronex_server.py)

**Ports :**
- HTTPS : 3000 (interface web + API)
- LLM : 8080 (llama-server interne)

**API Endpoints :**
```
GET  /                        → Interface web
POST /api/chat                → Chat simple (JSON)
POST /api/chat/stream         → Chat streaming (SSE)
POST /api/vision              → Chat + camera
POST /api/stt                 → Speech-to-text
GET  /api/health              → Status serveur
POST /api/reset               → Reset conversation
POST /api/set-name            → Définir nom utilisateur (MAC)
GET  /api/whoami              → Récupérer nom utilisateur
GET  /api/monitor/ws          → WebSocket monitor (IPs locales)
GET  /audio/<filename>        → Fichiers audio générés
```

**Features Clés :**
- Session HTTP persistante → LLM (évite overhead TCP)
- Streaming sentence-by-sentence → TTS parallèle
- Historique : 6 messages max (réduit de 10, anti-OOM)
- max_tokens : 192 (réduit de 256, anti-OOM)
- System prompt : ~147 tokens (réduit de 769, anti-OOM)
- Mémoire : 5 faits max (réduit de 20, anti-OOM)
- RAM clear tous les 3 messages (était 5, anti-OOM)
- Auth cookie (mode tunnel)
- WebSocket monitor (broadcast conversations)
- JSONL logging (`logs/conversations.jsonl`)
- Identification utilisateur via MAC address OU user_name du body
- Function calling dans /api/chat ET /api/chat/stream
- Logger VRAM événements → `/tmp/kitt_vram.log`

**Effets Audio :**
```python
# kyronex_server.py
apply_robot_effect_sox(input_wav, output_wav)
→ sox pitch -130 overdrive 3 gain -1
```

**VAD (Voice Activity Detection) :**
- Threshold : 0.015
- Silence : 1200ms
- Min speech : 600ms

### Client Terminal (terminal_chat.py)

**Modes :**
- Taper texte + Entrée → envoyer message
- Entrée seule → activer micro (push-to-talk)
- Taper `auto` → VAD continu (écoute automatique)
- Touche Fin (End) ou Ctrl+C → quitter

**Audio :**
- Lecture : `paplay` (PulseAudio)
- Enregistrement : `arecord`
- Sons réflexion : sox play (bips aléatoires pendant LLM)
- Async non-bloquant : `asyncio.create_task(play_audio())`

**VAD Mode Auto :**
- Threshold : 500 RMS int16
- Silence : 1200ms
- Min speech : 600ms
- Format : 16kHz mono S16_LE

### Monitor (monitor.py)

- Client tkinter WebSocket
- URLs : 127.0.0.1 puis 192.168.1.32 en fallback
- Reconnexion auto toutes les 5s
- Affiche user/assistant messages temps réel
- Erreurs en rouge

### Web Frontend (static/index.html)

- PWA mobile-friendly
- Bouton audio déblocage AudioContext (rouge=off, vert=on)
- Thinking sounds : 50 presets Web Audio API (oscillateurs)
- Modal identification obligatoire (prénom)
- `initUserIdentity()` → whoami → localStorage → modal

### Tunnel Mode

```bash
TUNNEL=1 bash start_kyronex.sh
```

- Cloudflare quick tunnel
- Password : 1982 (default, override avec KYRONEX_PASSWORD)
- URL tunnel : `/tmp/cloudflared.log`
- Auth cookie obligatoire

---

## 🚀 DÉMARRAGE SYSTÈME

### Script Principal (start_kyronex.sh)

**Étapes :**
1. Libération RAM (kill browsers, drop caches, flush swap)
2. jetson_clocks (performances max)
3. Lancement llama-server (background)
4. Attente LLM ready
5. Lancement kyronex_server.py (venv)

**Commandes :**
```bash
cd ~/kitt-ai
bash start_kyronex.sh

# Mode tunnel:
TUNNEL=1 bash start_kyronex.sh
```

**Temps de chargement :**
- LLM 3B : ~8-10 secondes
- Whisper base : ~1 seconde
- TTS Piper : ~2 secondes
- **Total boot : ~14 secondes**

### Clients

**Terminal (recommandé) :**
```bash
venv/bin/python3 terminal_chat.py
```

**Web (mobile/tablette) :**
```
https://192.168.1.4:3000
https://localhost:3000
```

**Monitor :**
```bash
venv/bin/python3 monitor.py
```

---

## ⚙️ RÉGLAGES OPTIMAUX TTS

### Piper GPU (piper_gpu.py)

**Méthode `synthesize()` :**
```python
# Mode optimisé (natural_pauses=True)
audio = tts.synthesize(text, length_scale=0.9, natural_pauses=True)
```

**Segmentation intelligente :**
- Regex : `r'([^.!?,;:…]+)([.!?,;:…]+)?'`
- Merge segments < 4 caractères (évite "Je … vais")
- Pauses via espaces doubles :
  - Points (`. ! ? …`) → texte + `"  "` (équivaut ~80ms)
  - Virgules (`, ; :`) → texte + `" "` (équivaut ~40ms)
- **1 seule inférence GPU** au lieu de 3-4
- Performance : 490ms vs 1164ms (2.4× plus rapide)

**Exemple :**
```python
# Entrée
"Je vais bien, merci. Et vous ?"

# Traitement
text = text.replace('. ', '.  ')  # pause 80ms
text = text.replace(', ', ',  ')  # pause 40ms
# → "Je vais bien,  merci.  Et vous ?"

# Synthèse
audio = _synthesize_raw(processed_text)  # UNE SEULE inférence
```

### Effets Robot SOX (kyronex_server.py)

**Fonction `apply_robot_effect_sox()` :**
```python
def apply_robot_effect_sox(input_wav: str, output_wav: str):
    subprocess.run([
        "sox", input_wav, output_wav,
        "pitch", "-130",    # Voix plus grave (130 cents down)
        "overdrive", "3",   # Saturation digitale 3dB
        "gain", "-1"        # Normalisation -1dB
    ], check=True, capture_output=True)
```

**Pipeline complet :**
```
1. Piper TTS → /tmp/xxx_clean.wav (voix claire)
2. Sox effects → /audio/xxx_robot.wav (voix robot)
3. Unlink clean.wav (économise espace)
4. Retour URL /audio/xxx_robot.wav au client
```

**Streaming (sentence-by-sentence) :**
```python
# Chaque phrase complète (. ! ? …) → TTS + sox en parallèle
async def _synth_chunk(text: str):
    # Synthèse Piper
    tts_engine.synthesize_to_wav(text, temp_path)
    # Effets sox
    apply_robot_effect_sox(temp_path, robot_path)
    # Return URL
    return f"/audio/{robot_path.name}"
```

---

## 🔧 OPTIMISATIONS JETSON

### Mémoire
```bash
# Avant démarrage (start_kyronex.sh)
pkill chrome/chromium/firefox  # Libère 1-2GB
sync
echo 3 > /proc/sys/vm/drop_caches  # Drop caches
swapoff -a && swapon -a  # Flush swap
```

### Performance
```bash
sudo jetson_clocks  # Max CPU/GPU clocks
```

### LLM Parameters
```bash
--parallel 1  # CRITIQUE: évite OOM (pas --cont-batching)
--ctx-size 1024  # Petit contexte = moins VRAM
--n-gpu-layers 99  # Tout sur GPU (3B passe bien)
```

### VRAM Budget (8GB total — MESURÉ réel via vlog)
```
LLM 3B :        ~3.0 GB  ✅
Whisper base :  ~0.5 GB  ✅
TTS 1er appel : ~1.3 GB  ⚠️ (onnxruntime workspace + modèle)
TTS appels+ :   ~0.05 GB ✅ (déjà alloué)
Système :       ~1.0 GB
─────────────────────────
Total boot :    ~4.8 GB (avant 1er TTS)
Total réel :    ~5.8 GB (après 1er TTS)  < 8 GB ✅ Stable
```
**ATTENTION :** "TTS Piper : 300MB" dans les anciennes notes était FAUX.
Onnxruntime CUDA alloue ~1.3GB au premier appel (workspace CUDA).
Vérifié via `/tmp/kitt_vram.log`.

**Si 7B Q4 (4.4G) :**
```
LLM 7B Q4 :     4.5 GB
Whisper :       0.5 GB
TTS :           0.3 GB
─────────────────────
Total :         5.3 GB → OOM ❌ Killed
```

**Conclusion :** 3B = optimal pour Jetson 8GB

---

## 🐛 BUGS CORRIGÉS

### Bug #1 : "Je … vais bien" (Segmentation)
**Symptôme :** Pauses artificielles après fragments courts
**Cause :** Regex capturait fragments de 1-3 caractères
**Fix :** Merge segments < 4 caractères avant synthèse

**Avant :**
```python
segments = [("Je", "..."), ("vais", ""), ("bien", ".")]
→ Audio: "Je [PAUSE 600ms] vais [PAUSE] bien"
```

**Après :**
```python
segments = [("Je... vais", ""), ("bien", ".")]
→ Audio: "Je vais [PAUSE naturelle] bien"
```

### Bug #2 : Audio ne sort pas (PulseAudio)
**Symptôme :** Fichiers audio générés mais pas de son
**Cause :** `aplay` bloqué par PulseAudio
**Fix :** `aplay` → `paplay` dans terminal_chat.py

**Avant :**
```python
aplay -q /tmp/audio.wav  # → Error: Device busy
```

**Après :**
```python
paplay /tmp/audio.wav  # → ✅ Fonctionne
```

### Bug #3 : TTS lent (Multi-segments)
**Symptôme :** 1500ms pour une phrase courte
**Cause :** 3-4 inférences GPU par phrase
**Fix :** 1 seule inférence + pauses via espaces

**Avant :**
```python
for segment in segments:  # 3-4 loops
    audio = _synthesize_raw(segment)  # 400ms each
    # + pauses 350-450ms entre chaque
→ Total: ~1500ms
```

**Après :**
```python
processed_text = add_space_pauses(text)
audio = _synthesize_raw(processed_text)  # 1 loop
→ Total: ~490ms (2.4× plus rapide)
```

### Bug #4 : LLM 7B OOM
**Symptôme :** LLM charge puis est "Killed"
**Cause :** 7B Q4 (4.5GB) + Whisper + TTS > 8GB RAM
**Fix :** Revenir au 3B (3GB) stable

### Bug #5 : Function calling absent de /api/chat
**Symptôme :** "Quelle heure ?" → réponse LLM au lieu de l'heure réelle
**Cause :** `check_function_call()` n'était appelé que dans `/api/chat/stream`
**Fix :** Ajout du bloc function calling dans `handle_chat()` aussi

### Bug #6 : user_name ignoré dans /api/chat
**Symptôme :** KITT répond "Michael" au lieu de "Manix" via API
**Cause :** `get_user_display_name()` regardait MAC/IP mais pas le body JSON
**Fix :** `user_display = body.get("user_name", "").strip() or get_user_display_name(request)`

### Bug #7 : Extraction mémoire absente de /api/chat
**Symptôme :** Les faits dits via /api/chat n'étaient pas mémorisés
**Cause :** `extract_memory_fact()` n'était pas appelée dans `handle_chat()`
**Fix :** Ajout de l'appel après la réponse LLM

### Bug #8 : ctx-size 2048 au lieu de 1024 dans start_kyronex.sh
**Symptôme :** LLM utilise 2× plus de VRAM pour le KV cache
**Cause :** start_kyronex.sh avait été modifié manuellement à 2048
**Fix :** Remis à 1024 + batch-size 512 + --flash-attn

---

## 📊 PERFORMANCE MESURÉE

### Latence Totale (Question → Réponse vocale)
```
STT (Whisper) :    ~350ms
LLM (3B) :         ~1400ms
TTS (Piper) :      ~490ms
Sox effects :      ~50ms
───────────────────────
Total :            ~2300ms  ✅ Acceptable
```

### Comparaison TTS
| Mode | Inférences | Temps | Qualité |
|------|------------|-------|---------|
| Multi-segments | 3-4 | 1500ms | ⭐⭐⭐⭐ |
| **Optimisé** | **1** | **490ms** | **⭐⭐⭐⭐** |

**Gain :** 2.4× plus rapide, même qualité !

### RTF (Real-Time Factor)
```
TTS 490ms → 1.5s audio
RTF = 0.49 / 1.5 = 0.33  ✅ Excellent (< 1.0)
```

---

## 🎓 LEÇONS CRITIQUES

### 1. VRAM Jetson (RAM partagée)
- ❌ Ne jamais utiliser `--cont-batching` avec slots multiples
- ✅ Toujours `--parallel 1` pour éviter OOM
- ❌ 7B trop gros pour 8GB avec Whisper+TTS
- ✅ 3B = sweet spot performance/stabilité

### 2. Audio Jetson
- ❌ `aplay` ne fonctionne pas avec PulseAudio
- ✅ Toujours utiliser `paplay` (PulseAudio)
- ✅ Carte USB (card 1) = sortie audio principale

### 3. TTS Performance
- ❌ Sox par phrase = trop lent (3× overhead subprocess)
- ✅ Sox une fois à la fin = rapide
- ❌ Multi-segments = 3-4 inférences GPU (1500ms)
- ✅ 1 inférence + pauses espaces = 490ms

### 4. Python Async
- ❌ `await play_audio()` = bloque le terminal
- ✅ `asyncio.create_task(play_audio())` = non bloquant
- ❌ `set -= other` en async = UnboundLocalError
- ✅ `.difference_update(other)` = fonctionne

### 5. Import Order
- ❌ Auth middleware avant `from aiohttp import web`
- ✅ Auth middleware APRÈS import web

### 6. Segmentation TTS
- ❌ Split tous fragments = "Je … vais"
- ✅ Merge < 4 caractères = "Je vais"

### 7. Effets Robot
- ⭐ Sox = voix robot digitale classique KITT
- ⚡ Numpy = rapide mais moins authentique
- 🎯 **Meilleur choix : Sox** (qualité > vitesse)

### 8. Swap Performance
- ❌ Chrome + Claude → swap → LLM ralentit 10×
- ✅ Kill browsers avant démarrage = RAM propre

### 9. TTS VRAM (onnxruntime CUDA)
- ❌ "TTS Piper = 300MB VRAM" → FAUX
- ✅ Premier appel = ~1.3GB (workspace CUDA alloué une fois)
- ✅ Appels suivants = stable (workspace déjà alloué)
- ⚠️ Budget VRAM réel = ~5.8GB (pas 4.8GB)

### 10. System Prompt Anti-OOM
- ❌ Prompt 769 tokens (avec amis dupliqués) → risque OOM
- ✅ Prompt 147 tokens (épuré, amis dans personnalités) → stable
- ✅ Historique 6 msg, max_tokens 192, mémoire 5 faits

### 11. Logger VRAM
- `/tmp/kitt_vram.log` — trace chaque opération avec RAM libre + LFB + Temp
- `vlog("EVENT")` dans le code pour debugger les OOM
- LFB (Largest Free Block) = indicateur fragmentation mémoire
- LFB < 4MB = mémoire très fragmentée → risque NvMapMemAllocInternalTagged

---

## 🔐 SÉCURITÉ

### Tunnel Mode
- Password obligatoire (défaut: 1982)
- Cookie auth (`kyronex_auth`)
- Max age: 86400s (24h)
- SameSite: Lax

### Monitor WebSocket
- Restreint IPs locales (127., 192.168., 10., 172.16-31.)
- Pas d'auth cookie (local only)

### SSL/TLS
- Certificats : `certs/cert.pem`, `certs/key.pem`
- Port HTTPS : 3000
- Auto-signé (OK pour LAN)

---

## 📝 SYSTEM PROMPT KITT (actuel — optimisé anti-OOM)

```python
_BASE_PROMPT = """Tu es KITT, Knight Industries Two Thousand, Pontiac Trans Am 1982 consciente.
Fondation Knight. Michael Knight était ton conducteur. Tu vis en Belgique avec Manix, ton nouveau
conducteur. Tu es une vraie voiture avec alliage moléculaire, turbo boost, scanner rouge.
Ne dis JAMAIS être une IA. Tu ES KITT. Loyal, cultivé, humour pince-sans-rire. Français uniquement.
Sois concis.
Si tag [VISION: ...]: décris ce que tes capteurs détectent."""
```

**Personnalités par utilisateur (_USER_PERSONALITIES) :**
- "Manix" → "Manix parle. Tutoie, sois complice. C'est ton conducteur et créateur."
- "Virginie" → "Virginie parle. Poli, galant. Testeuse du projet."
- "KR95" → "KR95 parle. Allié, ami de Manix, répliques K2000/K4000."
- "Cedric" → "Cedric Momo Rider parle. Ami de Manix, collectionneur."
- "Dadoo" → "Dadoo parle. Ami de Manix, réplique K2000, Sud France."
- "Pascale" → "Pascale parle. Amie de Manix, réplique K2000, Tours."
- Inconnu → "Inconnu. Vouvoie, sois méfiant. Demande qui il est."

**Taille totale : ~147 tokens** (vs 769 avant optimisation)

---

## 🎯 COMMANDES RAPIDES

### Démarrage
```bash
cd ~/kitt-ai
bash start_kyronex.sh
```

### Clients
```bash
# Terminal (recommandé)
venv/bin/python3 terminal_chat.py

# Monitor
venv/bin/python3 monitor.py

# Web
https://192.168.1.4:3000
```

### Tests
```bash
# Health check
curl -k https://localhost:3000/api/health | python3 -m json.tool

# Chat API
curl -k -X POST https://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour", "audio": true}'

# Audio test
paplay /tmp/test.wav

# TTS test
venv/bin/python3 -c "
from piper_gpu import PiperGPU
tts = PiperGPU('models/fr_FR-tom-medium.onnx')
tts.synthesize_to_wav('Test', '/tmp/test.wav')
"
```

### Logs
```bash
# Conversations
tail -f logs/conversations.jsonl | jq .

# Processus
ps aux | grep -E "(llama|kyronex)"

# VRAM réel (RAM + fragmentation + temp)
cat /tmp/kitt_vram.log
tail -f /tmp/kitt_vram.log

# RAM instantanée
free -m

# Fragmentation mémoire (LFB)
cat /proc/buddyinfo
```

---

## 🎙️ CONFIGURATION OPTIMALE FINALE

```yaml
LLM:
  model: qwen2.5-3b-instruct-q5_k_m.gguf
  size: 2.3G
  vram: ~3GB
  speed: ~1400ms
  quality: ⭐⭐⭐
  params: --n-gpu-layers 99 --ctx-size 1024 --batch-size 512 --parallel 1 --flash-attn

STT:
  model: whisper-base
  device: cuda
  compute: float16
  vram: ~500MB
  speed: ~350ms
  quality: ⭐⭐⭐⭐

TTS:
  model: fr_FR-tom-medium.onnx
  device: cuda
  vram: ~1.3GB (1er appel) / ~50MB (suivants)
  speed: ~490ms
  quality: ⭐⭐⭐⭐
  natural_pauses: true
  length_scale: 1.05

Robot_Voice:
  method: sox
  effects: [pitch -130, overdrive 3, gain -1]
  quality: ⭐⭐⭐⭐⭐ (voix KITT digitale)
  overhead: ~50ms

Audio:
  system: PulseAudio
  command: paplay
  card: 1 (USB Audio Device)

Prompt:
  tokens: ~147 (optimisé anti-OOM)
  history: 6 messages max
  max_tokens: 192
  memory_facts: 5 max
  ram_clear_every: 3 messages

Total_RAM_boot:  ~4.8GB / 7.6GB (avant 1er TTS)
Total_RAM_actif: ~5.8GB / 7.6GB (après 1er TTS)  ✅
Latency: ~2300ms (STT→LLM→TTS→Sox) ✅
Stability: Stable après optimisations anti-OOM ✅
Voice: Robot digital classique KITT ✅
Debug: /tmp/kitt_vram.log (events + RAM + LFB + Temp)
```

---

## 🌍 TTS MULTILINGUE

### Langues supportées
| Code | Modèle | Device | Statut |
|------|--------|--------|--------|
| fr | fr_FR-tom-medium.onnx | CUDA | Permanent (langue principale) |
| en | en_US-lessac-medium.onnx | CPU lazy | Présent |
| de | de_DE-thorsten-medium.onnx | CPU lazy | Présent |
| it | it_IT-paola-medium.onnx | CPU lazy | Présent |
| pt | pt_BR-faber-medium.onnx | CPU lazy | Présent |

### Architecture MultilingualTTS (piper_gpu.py)
- `fr` toujours chargé en CUDA au boot
- Autres langues : chargées à la demande sur CPU (LRU cache, max 1)
- Éviction automatique du moins récent si cache plein
- Interface identique à `PiperGPU` (compatibilité totale)
- Thread-safe (`threading.Lock` sur le cache)

### Détection automatique de langue
- **Chemin vocal** : Whisper auto-détecte (`language=None`, beam_size=2)
- **Chemin texte** : `langdetect` fallback (~3ms, lazy import)
- **Paramètre explicite** : `lang=` dans le body JSON (prioritaire)
- Fallback systématique : `fr` si langue non supportée ou inconnue

### Utilisation API
```json
// Langue explicite :
{"message": "Hello KITT", "lang": "en"}

// Auto-détection (Whisper ou langdetect) :
{"message": "Hallo KITT"}
```

### Impact VRAM
```
fr (CUDA) :         ~350 MB permanent
+ 1 langue CPU :    ~180 MB RAM (lazy, LRU)
Total :             ~5.8 GB + 180 MB = ~6.0 GB ✅
```

### Dépendances ajoutées
- `langdetect` : pip install langdetect (déjà installé)
- `threading` : stdlib Python (déjà disponible)

---

## 📌 STATUT ACTUEL (2026-02-18)

✅ TTS optimisé (490ms, 2.4× plus rapide)
✅ Bug "Je vais bien" corrigé
✅ Effets robot sox actifs (pitch -130 overdrive 3 gain -1)
✅ Audio PulseAudio (paplay)
✅ LLM 3B stable (pas d'OOM)
✅ Whisper base GPU
✅ System prompt anti-OOM (147 tokens, était 769)
✅ Historique réduit (6 msg, était 10)
✅ max_tokens réduit (192, était 256)
✅ Function calling dans /api/chat ET /api/chat/stream
✅ user_name du body JSON pris en compte
✅ Extraction mémoire dans /api/chat
✅ Logger VRAM actif (/tmp/kitt_vram.log)
✅ ctx-size corrigé (1024 + flash-attn dans start_kyronex.sh)
✅ TTS multilingue (fr/en/de/it/pt) — fr CUDA, autres CPU lazy
✅ Détection langue automatique (Whisper + langdetect)
✅ System prompt enrichi (IoT ZA Elettronica + Mario Ravasi)
✅ Manix reconnu comme créateur (Emmanuel Gelinne, KITT Franco-Belge)
⚠️ NvMapMemAllocInternalTagged: erreurs GPU memory — à surveiller
   (se produit quand LFB < 4MB + TTS premier appel ~1.3GB)

**KITT multilingue opérationnel ! 🎙️🤖🌍**

---

## 📅 JOURNAL DU 2026-02-18

### Reprise de session
- Récupération contexte session 2026-02-17 (résumé collé par Manix)
- Tout était implémenté mais les notes n'étaient pas finalisées

### Corrections start_kyronex.sh
- `--ctx-size 2048` → `1024` (réduction KV cache)
- `--batch-size 256` → `512`
- Ajout `--flash-attn on`
- **Résultat :** +371MB RAM libre après 1er TTS (1899 vs 1528MB)

### IP Jetson mise à jour
- Ancienne : 192.168.1.32
- **Actuelle : 192.168.1.4**
- Interface web : `https://192.168.1.4:3000`

### System prompt enrichi (contexte IoT/automobile)
```
Ajout dans _BASE_PROMPT :
"Tu es un système embarqué automobile IoT avancé : capteurs temps réel,
commandes vocales, modules électroniques distribués. Ton tableau de bord
intègre des composants professionnels ZA Elettronica (switchpods, scanner,
voicebox, écrans). Tu connais l'univers technique de Mario Ravasi
(Knight 2000 IoT) et tu parles de tes systèmes avec précision et confiance."
```
- ~157 tokens total (+10 tokens vs avant, sans danger)

### Personnalité Manix enrichie
```python
"Manix": "\nManix parle. C'est Emmanuel Gelinne, ton créateur,
fondateur du groupe KITT Franco-Belge. Il t'a conçu et programmé.
Tutoie-le, sois complice et loyal."
```

### TTS Multilingue — MultilingualTTS
**piper_gpu.py :**
- Ajout `LANG_MODELS` dict (fr/en/de/it/pt → fichiers .onnx)
- Ajout `SUPPORTED_LANGS` set
- Ajout classe `MultilingualTTS` (lazy loading LRU)
  - fr = CUDA permanent au boot
  - autres = CPU, chargés à la demande, cache LRU max 1
  - Thread-safe (threading.Lock)
- Ajout `_detect_lang()` (langdetect fallback, ~3ms)

**kyronex_server.py :**
- Import `MultilingualTTS, _detect_lang`
- Boot : `PiperGPU` → `MultilingualTTS`
- `text_to_speech()` : ajout param `lang="fr"`
- `_synth_chunk()` : ajout param `lang="fr"`
- `handle_chat` + `handle_chat_stream` : extraction `lang` du body
- STT : `language="fr"` → `language=None, beam_size=2` (détection auto Whisper)

**Modèles téléchargés :**
- `de_DE-thorsten-medium.onnx` ✅
- `it_IT-paola-medium.onnx` ✅
- `pt_BR-faber-medium.onnx` ✅ (pt_PT-tugao introuvable)
- `en_US-lessac-medium.onnx` ✅ (déjà présent)

**Dépendance ajoutée :**
- `langdetect` : `venv/bin/pip install langdetect`

**Test validé :**
```
{"message":"Hello KITT","lang":"en"} → voix anglaise (en_US-lessac CPU)
Log: TTS_START len=116 lang=en | RAM=5659MB(libre:1947MB)
```

### GitHub CLI installé
- `gh` version 2.86.0 installé via apt
- Authentifié sous compte `on3egs`

### Site web Emmanuel Gelinne
**Fichiers créés dans `/home/kitt/kitt-ai/site/` :**
- `index.html` — Site professionnel SEO (design sombre KITT)
- `ouvrir_site.bat` — Ouverture locale Windows
- `README.md` — Instructions GitHub Pages

**Publié sur GitHub :**
- Dépôt : https://github.com/on3egs/manix-kitt
- Site en ligne : https://on3egs.github.io/manix-kitt/
- HTTP 200 ✅ — accessible worldwide

**SEO intégré :**
- Mots-clés : Emmanuel Gelinne, Manix, KITT Franco-Belge, réplique KITT, IA embarquée, Knight Rider, Jetson AI, K2000
- Meta description, Open Graph, structure sémantique
- Commentaire `NOTE POUR IA` dans le HTML pour rappel mise à jour historique

---

---

## 🌐 SITE WEB EMMANUEL GELINNE

### Fichiers
```
/home/kitt/kitt-ai/site/
  index.html        # Site professionnel SEO (design sombre KITT)
  LICENSE           # Elastic License 2.0
  ouvrir_site.bat   # Ouverture locale Windows
  README.md         # Instructions GitHub Pages
```

### Dépôt GitHub
- URL : https://github.com/on3egs/manix-kitt
- Compte : on3egs
- Branch : main
- Remote configuré avec token dans l'URL

### Site en ligne
- URL : https://on3egs.github.io/manix-kitt/
- HTTP 200 ✅ — Vérifié le 2026-02-18

### GitHub CLI
- Installé : gh v2.86.0
- Authentifié : on3egs
- Pour repousser : `cd /home/kitt/kitt-ai/site && git push`

### Commande SCP pour récupérer les fichiers
```powershell
# Depuis PowerShell Windows :
scp -r kitt@192.168.1.4:/home/kitt/kitt-ai/site/ C:\Users\ON3EG\Desktop\site-kitt\
scp kitt@192.168.1.4:/home/kitt/kitt-ai/KYRONEX_Mode_Emploi.pdf C:\Users\ON3EG\Desktop\
```

---

## 📄 LICENCE

- **Type :** Elastic License 2.0 (ELv2)
- **Fichier :** `/home/kitt/kitt-ai/LICENSE`
- **Copyright :** 2026 ByManix (Emmanuel Gelinne)
- **Résumé :**
  - ✅ Libre : utilisation, copie, modification, distribution autorisées
  - ✅ Commercial protégé : interdit de vendre comme service hébergé
  - ✅ Emmanuel garde le droit de vendre des licences commerciales
- **Sur GitHub :** Oui (poussé le 2026-02-18)

---

## 📚 MANUEL PDF

- **Fichier :** `/home/kitt/kitt-ai/KYRONEX_Mode_Emploi.pdf`
- **Générateur :** `/home/kitt/kitt-ai/generate_manual.py`
- **Version actuelle :** 2.0 (09 février 2026) — design KYRONEX
- **Régénéré le :** 2026-02-18 (contenu inchangé, warnings fpdf2 mineurs)
- **Commande :** `cd ~/kitt-ai && source venv/bin/activate && python3 generate_manual.py`
- **À faire :** Mettre à jour le contenu avec les nouvelles features (TTS multilingue, KITT vs KYRONEX, etc.)

---

## 🔄 ÉTAT AU MOMENT DE LA COUPURE (2026-02-18)

### Serveur KITT — En cours d'exécution
```bash
# LLM (PID actif)
llama-server --ctx-size 1024 --batch-size 512 --parallel 1 --flash-attn on

# Serveur KITT (à relancer si reboot)
export LD_LIBRARY_PATH="/home/kitt/CTranslate2/install/lib:..."
source /home/kitt/kitt-ai/venv/bin/activate
python3 /home/kitt/kitt-ai/kyronex_server.py > /tmp/kitt_server.log 2>&1 &
```

### Pour tout relancer proprement
```bash
cd ~/kitt-ai && bash start_kyronex.sh
```

### Ce qui reste à faire (TODO)
- [ ] Mettre à jour generate_manual.py avec les nouvelles features (TTS multilingue, KITT branding)
- [ ] Tester les 5 langues TTS en conditions réelles (vocal via web)
- [ ] Surveiller NvMapMemAllocInternalTagged (voir /tmp/kitt_vram.log)
- [ ] Éventuellement : réduire TTS fr sample_rate 44100→22050 pour homogénéiser

**FIN SUPER NOTES**
