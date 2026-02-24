# 💾 KYRONEX — Backup & Restauration

Guide complet pour sauvegarder et restaurer KYRONEX automatiquement.

---

## 🎯 Vue d'ensemble

- **`backup.sh`** — Crée un backup complet du système (fichiers + config)
- **`install_kyronex.sh`** — Installation automatique OU restauration depuis backup

---

## 📦 Créer un Backup

```bash
cd /home/kitt/kitt-ai
bash backup.sh
```

**Ce qui est sauvegardé:**
- ✅ Tous les scripts Python (kyronex_server.py, piper_gpu.py, etc.)
- ✅ Scripts shell (start_kyronex.sh, etc.)
- ✅ Interface web (static/)
- ✅ Certificats SSL (certs/)
- ✅ Système driver (driver/)
- ✅ Données utilisateur (users.json)
- ✅ Documentation (SUPER_NOTES.md, etc.)
- ✅ Dépendances Python (requirements.txt)

**Résultat:**
- Archive: `BACKUP_YYYYMMDD_HHMMSS.tar.gz`
- Dossier: `BACKUP_YYYYMMDD_HHMMSS/`

---

## 🔄 Restaurer depuis un Backup

### 1️⃣ Restauration complète (installation + backup)

Si le système est cassé et que vous partez de zéro:

```bash
cd /home/kitt/kitt-ai
bash install_kyronex.sh restore BACKUP_20260213_001530.tar.gz
```

**Ce que ça fait:**
1. Installe toutes les dépendances système (sox, pulseaudio, etc.)
2. Compile llama.cpp avec CUDA
3. Télécharge les modèles (LLM, Whisper, Piper)
4. Crée le venv Python
5. **Restaure tous vos fichiers depuis le backup**
6. Configure SSL, audio, permissions
7. Installe le driver system
8. Teste que tout fonctionne

⏱️ **Durée:** ~30-60 minutes (selon téléchargements)

### 2️⃣ Restauration rapide (fichiers uniquement)

Si juste les fichiers sont cassés mais le système est OK:

```bash
# Extraire le backup manuellement
tar -xzf BACKUP_20260213_001530.tar.gz
cd BACKUP_20260213_001530

# Copier les fichiers
cp *.py /home/kitt/kitt-ai/
cp *.sh /home/kitt/kitt-ai/
cp -r static /home/kitt/kitt-ai/
cp -r driver /home/kitt/kitt-ai/
# etc.
```

---

## 🆕 Installation from Scratch

Si vous installez sur un **nouveau Jetson** sans backup:

```bash
cd /home/kitt/kitt-ai
bash install_kyronex.sh
```

⚠️ **Note:** Ce mode suppose que les fichiers Python sont déjà présents.
Pour une vraie installation from scratch, utilisez un backup existant.

---

## 📋 Checklist après Restauration

Après restauration, vérifiez:

```bash
# 1. Test sox
sox --version

# 2. Test pulseaudio
paplay --version

# 3. Test llama.cpp
/home/kitt/llama.cpp/build/bin/llama-server --version

# 4. Test Python venv
source venv/bin/activate
python3 -c "import aiohttp, onnxruntime; print('OK')"
deactivate

# 5. Lancer KYRONEX
bash start_kyronex.sh
```

---

## 🔧 Dépannage

### Problème: "llama.cpp not found"

```bash
cd /home/kitt
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir -p build && cd build
cmake .. -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build . --config Release -j6
```

### Problème: "Models not found"

Les modèles ne sont PAS dans le backup (trop gros).
Le script `install_kyronex.sh` les télécharge automatiquement.

Ou manuellement:

```bash
cd /home/kitt/kitt-ai/models

# LLM (2.3GB)
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q5_k_m.gguf

# Whisper base (500MB)
wget https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt
mkdir -p whisper-base && mv base.pt whisper-base/

# Piper (50MB)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json
```

### Problème: "Permission denied"

```bash
chmod +x /home/kitt/kitt-ai/*.sh
chmod +x /home/kitt/kitt-ai/driver/*.sh
```

---

## 💡 Bonnes Pratiques

### Backup régulier

Créez un backup **avant toute modification importante**:

```bash
# Avant de modifier le code
bash backup.sh

# Faire les modifications...

# Si problème, restaurer:
bash install_kyronex.sh restore BACKUP_xxx.tar.gz
```

### Backups automatiques (cron)

Pour créer un backup tous les jours à 3h du matin:

```bash
crontab -e

# Ajouter:
0 3 * * * cd /home/kitt/kitt-ai && bash backup.sh > /tmp/backup.log 2>&1
```

### Nettoyer les vieux backups

Garder seulement les 5 derniers:

```bash
cd /home/kitt/kitt-ai
ls -t BACKUP_*.tar.gz | tail -n +6 | xargs rm -f
```

---

## 📊 Tailles des Fichiers

- **Backup KYRONEX:** ~5-10 MB (sans modèles)
- **Modèles LLM:** ~2.3 GB
- **Modèles Whisper:** ~500 MB
- **Modèles Piper:** ~50 MB
- **Total système:** ~3 GB

---

## 🎯 Résumé des Commandes

```bash
# Créer un backup
bash backup.sh

# Restauration complète
bash install_kyronex.sh restore BACKUP_xxx.tar.gz

# Installation from scratch
bash install_kyronex.sh

# Démarrer KYRONEX
bash start_kyronex.sh
```

---

**🛡️ Avec ces scripts, KYRONEX est immortel!** 🤖✨
