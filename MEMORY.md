# KYRONEX — Mémoire de projet
# Historique des sessions et état courant

---

## Version courante : V37.12 (2026-02-28)

### Historique V37.x (session 2026-02-28)
- V37.0: Refonte Modern Knight Rider (CSS Grid, variables :root, suppression hacks Gemini/Maestro)
- V37.1: Suppression boutons CAM et AUDIO (auto-activation audio sur 1er clic)
- V37.2: Suppression bouton ENVOYER (enterkeyhint="send", Entrée suffit)
- V37.3: Fix clavier mobile (_focusInput avec pointer:fine, suppression autofocus)
- V37.4: Plein écran auto + bouton × pour quitter (API Fullscreen cross-browser)
- V37.5: Fix bug TTS "(f)" quand KITT lit un "." (filtre isalpha côté serveur + piper_gpu.py)
- V37.6: STT Lang Lock — Whisper forcé avec langue préférée user, selectLang() envoie /api/set-lang
- V37.7: GitHub Pages kitt-ai (docs/index.html = vitrine avec intro + showcase)
- V37.11: Fix volume AUTO (micro muet → haut-parleurs, ducking PulseAudio)
- V37.12: Filtrage `<think>` Qwen + paramètres LLM optimaux

---

## Paramètres LLM actifs (V37.12)

```python
"temperature":    0.7,   # sweet spot Alibaba/Qwen officiel
"top_p":          0.8,   # nucleus sampling Qwen recommandé
"top_k":          20,    # filtre agressif petits modèles
"min_p":          0.05,  # ICLR 2025
"repeat_penalty": 1.1,
"repeat_last_n":  64,
"max_tokens":     256,   # au-delà 300 le 3B divague
```

---

## Filtrage `<think>` Qwen (V37.12)

Pattern implémenté dans les boucles SSE (chat + vision) de `kyronex_server.py` :

```python
_raw_buf = ""        # Buffer brut accumulatif
_clean_emitted = ""  # Texte nettoyé déjà émis

# Pour chaque delta :
_raw_buf += delta
clean_buf = re.sub(r'<think>.*?</think>', '', _raw_buf, flags=re.DOTALL)
clean_buf = re.sub(r'<\|[^|]+\|>', '', clean_buf)       # tokens spéciaux
if '<think>' in clean_buf:
    clean_buf = re.sub(r'<think>.*$', '', clean_buf, flags=re.DOTALL)  # bloc incomplet
new_content = clean_buf[len(_clean_emitted):]
if new_content:
    _clean_emitted = clean_buf
    # → envoyer new_content au client et au TTS
```

`full_reply` nettoyé avant ajout dans l'historique :
```python
full_reply_clean = re.sub(r'<think>.*?</think>', '', full_reply, flags=re.DOTALL)
full_reply_clean = re.sub(r'<\|[^|]+\|>', '', full_reply_clean).strip()
```

Filet JS côté client (`streamChat()` dans `index.html`) :
```javascript
let tok = data.token.replace(/<think>[\s\S]*?<\/think>/g, '')
                    .replace(/<\|[^|]+\|>/g, '');
```

---

## System prompt `_BASE_PROMPT`

- Fin du prompt : exemple de style dialogue pour calibrer Qwen 3B
- `get_system_prompt(user_name, user_lang)` : ajoute personnalité + mémoire
- Max ~147 tokens total (OOM si trop gros sur Jetson)

---

## Stack technique

| Composant | Modèle / Config | VRAM | Latence |
|-----------|-----------------|------|---------|
| LLM | Qwen 2.5 3B Q5 (qwen2.5-3b-instruct-q5_k_m.gguf) | ~3GB | ~1400ms |
| STT | Whisper base GPU float16 | ~500MB | ~350ms |
| TTS | Piper fr_FR-tom-medium GPU | ~300MB | ~490ms |
| **Total** | | **~3.9GB / 8GB** | |

llama.cpp : `--parallel 1 --ctx-size 2048`

---

## Services systemd

```bash
# Redémarrer kyronex
echo "5505" | sudo -S systemctl restart kitt-kyronex.service

# Voir les logs
journalctl -u kitt-kyronex.service -f

# Statut
systemctl status kitt-kyronex kitt-tunnel kitt-driver kitt-recognition
```

---

## Git

```bash
# Commit standard
git add static/index.html kyronex_server.py
git commit -m "KITT-CORE: description (VXX.YY)"
git push

# Backup avant modif
cp static/index.html static/index.html.bak-$(date +%Y%m%d_%H%M%S)
```

Repo : https://github.com/on3egs/kitt-ai (branche `main`)
