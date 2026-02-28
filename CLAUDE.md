# KITT — Briefing complet pour Claude Code
# Lu automatiquement avant chaque tâche autonome

---

## PROJET : KYRONEX A.I. — by Manix (Emmanuel Gelinne)
Jetson Orin Nano Super 8GB — JetPack 6.2.2 — Ubuntu 22.04
Interface web vocale pour KITT (Knight Industries Two Thousand — Trans Am 1982)
KITT NE DIT JAMAIS qu'il est une IA. Il EST KITT, point final.

---

## FICHIER PRINCIPAL
```
/home/kitt/kitt-ai/static/index.html   (~3040 lignes, HTML+CSS+JS tout-en-un)
```
Serveur : `kyronex_server.py` — HTTPS port 3000 — aiohttp + Whisper + Piper + llama.cpp

---

## RÈGLES ABSOLUES (ne jamais enfreindre)

1. **Lire le fichier avant de modifier** — ne jamais supposer le contenu
2. **Une seule amélioration par session** — précise et testable
3. **Ne pas casser l'existant** — préférer ajouter plutôt que remplacer
4. **Pas d'emojis** dans le code HTML/CSS/JS
5. **Pas de `aplay`** — uniquement `paplay` pour l'audio
6. **iOS/Safari** : pas de `inset:0`, utiliser `top:0;left:0;right:0;bottom:0`
7. **SVG fixed invisible** : ajouter `transform:translate3d(0,0,0)` (force GPU)
8. **Double opacité CSS/SVG** : opacity CSS × stroke-opacity SVG se multiplient
9. **System prompt Qwen** : max ~147 tokens (OOM si trop gros)
10. **Animations Safari** : ajouter `-webkit-animation` + `@-webkit-keyframes`
11. **SMIL SVG** (`<animate>`) = 0 JS, 0 VRAM — idéal Jetson
12. **HTML valide** — le fichier doit rester HTML5 valide après modification

---

## CE QUI A DÉJÀ ÉTÉ FAIT (ne pas refaire / ne pas dupliquer)

### Améliorations Web UI (2026-02-24)
- **Scanner KI2000** : JS rAF, `#scannerHead` + `#scannerTrail`, 8 états vitesse/couleur ✅
- **Émotions visuelles** : `applyEmotion()`, `EMOTION_COLORS`, sphère colorée, orbe `_kittOrbEmotion` ✅
- **Jarvis filtre émotion** : `dataset.emotionFilter` + drop-shadow préservé ✅
- **Panneau mémoire** : section MEMOIRE dans `.mother-panel`, `/api/memory`, refresh 60s ✅
- **Timing visible** : `.message .timing` couleur `#552222`, opacité 0.5, italic ✅
- **Bouton RST** : `resetChat()`, `#resetbtn` header gauche ✅
- **Historique localStorage** : `_saveChatHistory()`, `_loadChatHistory()`, 20 msgs ✅
- **Placeholder multilingue** : `PLACEHOLDERS` dans `unlockUI()` + `_updateLangDetection()` ✅
- **Boutons 48px mobile** : `@media (max-width: 480px)` ✅
- **Badge stats mobile** : `#mobileStats`, `#ms-online`, `#ms-health` ✅
- **Orbe mobile** : `N = window.innerWidth <= 600 ? 80 : 130` ✅
- **Bouton AUTO (Amélioration Auto)** : `toggleEnhance()`, `#enhancebtn`, thème violet `#aa44ff`, `body.enhanced`, 7 langues `enhance_active` ✅

### Fonctionnalités serveur existantes (kyronex_server.py)
- **5 émotions vocales** : `detect_emotion()` → sox profiles ✅
- **Function calling 0ms** : heure, date, système, météo wttr.in, timer ✅
- **Mémoire persistante** : `memory.json` 50 faits, extraction auto regex ✅
- **Multi-user** : Manix (complice), Virginie (galant), inconnu (méfiant) ✅
- **KITT proactif** : WebSocket `/api/proactive/ws`, salutations 6/7/12/18/22/0h ✅
- **Wake word** : regex `/\bki+t+\b/i`, VAD + Whisper ✅
- **Cookie auth**, JSONL logs, WebSocket monitor, Identity API ✅
- **Filtrage `<think>` Qwen** (V37.12) : buffer accumulatif `_raw_buf`/`_clean_emitted` dans les boucles SSE (chat + vision), nettoyage `full_reply` avant historique ✅
- **Paramètres LLM optimaux** (V37.12) : temp=0.7, top_p=0.8, top_k=20, min_p=0.05, max_tokens=256 (valeurs Alibaba/ICLR recommandées) ✅
- **Filtrage JS côté client** (V37.12) : regex `<think>` + tokens spéciaux dans `streamChat()` ✅
- **Exemple style `_BASE_PROMPT`** (V37.12) : dialogue calibré Qwen 3B en fin de prompt ✅

---

## ARCHITECTURE index.html

### IDs HTML importants
```
#chat          — Container messages
#input         — Input text utilisateur
#send          — Bouton ENVOYER
#status        — Barre statut (online/offline)
#lang-badge    — Badge langue détectée
#scanner       — Scanner div parent (classes: speaking/listening/auto-*/wake-*)
#scannerHead   — Tête lumineuse scanner (JS rAF)
#scannerTrail  — Trainée scanner (JS rAF)
#jarvis-bg     — Fond SVG Jarvis
#jarvis-svg    — SVG animé Jarvis (dataset.emotionFilter)
#sphere-wrap   — Wrapper sphère 3D CSS
#sphere-3d     — Sphère 3D
#orb           — Canvas orbe pulsant (particules)
#voicebox      — Canvas voicebox 280×44
#mic           — Bouton push-to-talk
#automic       — Bouton auto-écoute
#wakemic       — Bouton wake-word
#cam           — Bouton caméra vision
#audiobtn      — Bouton activation audio (obligatoire iOS)
#resetbtn      — Bouton RST (reset historique)
#vigbtn        — Bouton VIG (vigilance caméra)
#ambientbtn    — Bouton AMB (sons d'ambiance)
#connPanel     — Panneau CONNEXIONS gauche (stats)
#motherPanel   — Panneau MU-TH-UR 6000 droite (status/lang/mémoire)
#mp-memory-list — Liste faits mémoire KITT
#mobileStats   — Badge stats mobile (sous scanner, <600px)
#ms-online     — Nb connectés (mobile)
#ms-health     — Statut santé (mobile)
#nameOverlay   — Overlay saisie nom utilisateur
#about         — Overlay à propos
#cp-current    — Nb connectés maintenant
#cp-24h        — Connexions 24h
#cp-7d         — Connexions 7 jours
#mp-status     — Statut (MU-TH-UR)
#mp-lang       — Langue (MU-TH-UR)
#mp-session    — Session (MU-TH-UR)
#mp-time       — Heure (MU-TH-UR)
```

### Fonctions JavaScript principales
```javascript
addMessage(text, who, timing)     // Ajoute message DOM
sendMessage()                     // Envoie depuis input
streamChat(msg)                   // POST /api/chat/stream SSE
sendVision()                      // POST /api/vision caméra
toggleMic()                       // Push-to-talk
toggleAutoListen()                // Auto-écoute continue VAD
toggleWakeListen()                // Mode wake-word "KITT"
activateAudio()                   // Active AudioContext (iOS)
applyEmotion(emotion)             // Colore scanner/orbe/sphère/jarvis
resetChat()                       // Efface historique + localStorage
unlockUI(name, lang)              // Déverrouille après identification
lockUI()                          // Verrouille pendant traitement
checkHealth()                     // GET /api/health
connectProactive()                // WebSocket /api/proactive/ws
_refreshStats()                   // GET /api/stats
_refreshMemory()                  // GET /api/memory
_saveChatHistory(html, who)       // Save localStorage
_loadChatHistory()                // Load localStorage au démarrage
_updateLangDetection(lang, text)  // Maj langue + placeholder
toggleVigilance()                 // POST /api/vigilance
toggleAmbient()                   // Sons d'ambiance
startThinkingLoop()               // Sons réflexion KITT
stopThinkingLoop()                // Arrête sons réflexion
playEndOfMessageSound()           // Son fin de message
queueAudioChunk(url, text)        // Queue streaming audio
_playAndRevealNext()              // Joue chunk + révèle texte
drawVoicebox()                    // Animation voicebox canvas
```

### Variables globales importantes
```javascript
sessionId          // 'kyronex-' + Date.now()
currentUserName    // Nom utilisateur courant
_preferredLang     // Langue localStorage (défaut 'fr')
_lastDetectedLang  // Dernière langue Whisper
_chunkQueue        // Queue audio [{url, text}]
_chunkPlaying      // Flag playback en cours
_revealDiv         // Div révélation progressive
autoListenActive   // État auto-écoute
wakeListenActive   // État wake-word
audioActivated     // État audio iOS
CHAT_HISTORY_KEY   // 'kyronex_chat_history'
CHAT_HISTORY_MAX   // 20 messages max
EMOTION_COLORS     // {normal,excited,worried,sad,confident}
_kittOrbEmotion    // {r,g,b} couleur orbe actuelle
_kittEmotionScanColor // 'r,g,b' couleur scanner actuelle
VAD_THRESHOLD      // 0.015
SILENCE_DURATION   // 1200ms
```

### Classes CSS importantes
```css
.message           /* Bulles de conversation */
.message.kitt      /* Réponse KITT (rouge) */
.message.user      /* Message utilisateur */
.message.proactive /* Message proactif */
.timing            /* Timing LLM/TTS sous réponse */
.online / .offline /* Couleur statut */
.typing            /* Animation ... */
.scanner-head      /* Tête scanner (JS rAF) */
.scanner-trail     /* Trainée scanner (JS rAF) */
.s-core            /* Noyau sphère 3D */
.s-mer / .s-par    /* Anneaux sphère 3D */
.mic-btn .auto-btn .wake-btn .cam-btn .audio-btn /* Boutons audio */
.reset-btn .vig-btn .ambient-btn                /* Boutons utilitaires */
.mother-panel      /* Panneau MU-TH-UR droite */
.mp-mem-item       /* Ligne mémoire dans panneau */
.conn-panel        /* Panneau connexions gauche */
.mobile-stats      /* Badge mobile (display:none > 600px) */
.scanner           /* Container scanner (id=scanner) */
.voicebox-container /* Container canvas voicebox */
.input-area        /* Barre de saisie bas de page */
.chat-area         /* Zone messages */
.header            /* En-tête KITT */
```

---

## ROUTES API SERVEUR (/home/kitt/kitt-ai/kyronex_server.py)

```
GET  /                    → index.html
POST /api/chat/stream     → SSE streaming {token, audio_chunk, done+timing+emotion}
POST /api/vision          → Caméra YOLOv8 + chat SSE
POST /api/stt             → Whisper transcription audio WAV
GET  /api/health          → {llm_server: bool}
POST /api/reset           → Efface historique session
GET  /api/memory          → {facts: [{fact, user, date}]}
POST /api/memory          → Ajoute fait
GET  /api/stats           → {current, last_24h, last_7d, active_sessions}
GET  /api/whoami          → {name, lang, mac}
POST /api/set-name        → Enregistre nom ↔ MAC
POST /api/set-lang        → Enregistre langue
POST /api/ping            → Heartbeat session
POST /api/vigilance       → Toggle surveillance caméra
WS   /api/proactive/ws   → Messages proactifs (greeting/alert/vigilance/emotion)
WS   /api/monitor/ws     → Monitoring (IP locale uniquement)
```

### SSE done payload (important pour émotions)
```javascript
// data.done = true
// data.timing = {llm_ms, tts_ms, emotion, vision_ms?}
// Lire l'émotion : data.timing.emotion → appeler applyEmotion()
```

---

## CONFIG SERVEUR

```
LLM  : llama.cpp qwen2.5-3b-instruct-q5_k_m.gguf (port 8080)
STT  : Whisper base GPU float16 (~350ms)
TTS  : Piper fr_FR-tom-medium.onnx GPU (~490ms)
VRAM : ~3.9GB / 8GB — --parallel 1 -- ctx-size 2048
SSL  : certs/ auto-signés — port 3000 HTTPS
```

---

## CONTRAINTES TECHNIQUES JETSON

```
RAM  : 8GB partagée CPU/GPU — éviter fuites mémoire JS
GPU  : Tegra — NvMapMemAllocInternalTagged error 12 = GPU OOM
AUDIO: paplay jamais aplay
PATH : /home/kitt/.local/bin dans PATH
LD_LIBRARY_PATH : /home/kitt/CTranslate2/install/lib
Python: 3.10.12 / reportlab OK / fpdf NON
Claude Code: /home/kitt/.local/bin/claude v2.1.51
```

---

## OUTILS KITT NIGHT SCHEDULER

```
kitt_night_improve.sh  — boucle bash claude autonome
kitt_scheduler.py      — menu whiptail (fenetres + taches custom)
static/versions/       — versions sauvées après chaque iter
CLAUDE.md (ce fichier) — lu automatiquement par Claude Code
```

### Redémarrer kyronex après modification
```bash
LD_LIBRARY_PATH=/home/kitt/CTranslate2/install/lib \
  venv/bin/python3 kyronex_server.py > /tmp/kyronex.log 2>&1 &
```

---

## JOURNAL DES SESSIONS

Voir : /home/kitt/kitt-ai/static/versions/ — Session 20260228, V37.12 — Filtrage <think> Qwen + paramètres LLM optimaux
