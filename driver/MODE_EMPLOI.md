
# KYRONEX — Mode d'emploi complet
## Kinetic Yielding Responsive Onboard Neural EXpert
### Auteur : ByManix (Emmanuel Gelinne) — Elastic License 2.0

---

## 1. Vue d'ensemble

KYRONEX est une intelligence artificielle locale embarquee sur Jetson Orin Nano Super.
Le systeme detecte automatiquement le conducteur (Bluetooth + camera) et lance l'assistant vocal.

```
Boot → Bluetooth scan → Telephone detecte → Camera → Visage reconnu
  → TTS "Bonjour Manix" → LLM demarre → KYRONEX en ligne
```

---

## 2. Fichiers du projet

```
/home/kitt/kitt-ai/
├── kyronex_server.py          # Serveur chatbot vocal
├── start_kyronex.sh           # Lanceur (LLM + serveur + tunnel)
├── piper_gpu.py               # TTS GPU (onnxruntime CUDA)
├── vision.py                  # Detection objets camera
├── LICENSE                    # Elastic License 2.0
├── piper/                     # Binaire TTS Piper
├── models/                    # Modeles LLM + voix + vision
├── venv/                      # Environnement Python
├── static/
│   ├── index.html             # Interface web (mobile-friendly)
│   └── manifest.json          # PWA manifest
├── certs/                     # Certificats SSL
├── audio_cache/               # Cache audio TTS (auto-nettoye)
└── driver/
    ├── install.sh             # Installeur (1 seule fois)
    ├── recognition.py         # Reconnaissance faciale
    ├── bluetooth_detect.sh    # Detection Bluetooth
    ├── kitt-driver.service    # Service systemd
    ├── kitt-recognition.service
    ├── LICENSE                # Elastic License 2.0
    ├── MODE_EMPLOI.md         # Ce fichier
    ├── models/
    │   ├── face_detection_yunet_2023mar.onnx
    │   └── face_recognition_sface_2021dec.onnx
    └── faces/
        └── Manix.npy          # Visage enregistre
```

---

## 3. Demarrage

### Mode local (usage quotidien) :
```bash
cd /home/kitt/kitt-ai
bash start_kyronex.sh
```
- Ferme automatiquement Chrome pour liberer la RAM
- Vide le swap et les caches
- Active les performances max (jetson_clocks)
- Lance le LLM (1 slot GPU) puis le serveur KYRONEX
- Interface : https://192.168.1.32:3000 (depuis iPhone/PC sur le WiFi)

### Mode partage Internet (pour les amis) :
```bash
cd /home/kitt/kitt-ai
TUNNEL=1 bash start_kyronex.sh
```
- Active le mot de passe (1982 par defaut)
- Cree un tunnel Cloudflare gratuit
- Affiche un lien public `https://xxx.trycloudflare.com`
- Envoyer ce lien par Messenger/SMS
- Tes amis tapent le mot de passe → ils sont dedans

### Changer le mot de passe :
```bash
TUNNEL=1 KYRONEX_PASSWORD=monmdp bash start_kyronex.sh
```

### Arreter tout :
`Ctrl+C` dans le terminal.

---

## 4. Interface web

### Acces :
| Depuis | Adresse |
|--------|---------|
| WiFi local (iPhone) | https://192.168.1.32:3000 |
| Internet (amis) | Le lien trycloudflare.com |

### Boutons :
| Bouton | Fonction |
|--------|----------|
| Micro (rouge) | Push-to-talk : appuyer pour parler, relacher pour envoyer |
| AUTO (vert) | Ecoute continue : detecte automatiquement quand tu parles |
| WAKE (violet) | Wake word : dis "KYRONEX" pour activer, puis ta commande |
| Camera (rouge) | Vision : KYRONEX regarde la camera et decrit ce qu'il voit |
| ENVOYER | Envoyer un message texte |

### A propos :
Toucher le texte `© 2026 ByManix` en bas de l'ecran.

### PWA (icone sur l'ecran d'accueil) :
Sur iPhone : Safari → Partager → Sur l'ecran d'accueil.
KYRONEX s'ouvre alors en plein ecran comme une vraie app.

---

## 5. Reconnaissance conducteur

### Enregistrer un visage :
```bash
cd /home/kitt/kitt-ai/driver
python3 recognition.py --enroll Manix
```
- 5 captures automatiques, bien se placer face a la camera
- Fichier cree : `faces/Manix.npy`

### Enregistrer un autre conducteur :
```bash
python3 recognition.py --enroll Prenom
```

### Supprimer un visage :
```bash
rm /home/kitt/kitt-ai/driver/faces/Prenom.npy
```

### Tester la reconnaissance :
```bash
python3 recognition.py
```

---

## 6. Service automatique (systemd)

Le service demarre au boot et surveille le Bluetooth en permanence.

```bash
# Statut
sudo systemctl status kitt-driver

# Demarrer / Arreter / Redemarrer
sudo systemctl start kitt-driver
sudo systemctl stop kitt-driver
sudo systemctl restart kitt-driver

# Activer / Desactiver au boot
sudo systemctl enable kitt-driver
sudo systemctl disable kitt-driver

# Logs en temps reel
journalctl -u kitt-driver -f
```

---

## 7. Bluetooth

Le MAC de l'iPhone est configure dans `bluetooth_detect.sh` :
```
PHONE_MAC="E0:33:8E:4B:75:AE"
```

### Trouver le MAC d'un autre telephone :
```bash
bluetoothctl scan on
# Attendre quelques secondes, Ctrl+C
bluetoothctl devices
```

---

## 8. Backup et restauration

### Sauvegarder :
```bash
cd /home/kitt
tar czf kitt-ai-backup-$(date +%Y%m%d).tar.gz \
  --exclude='kitt-ai/audio_cache/*.wav' \
  --exclude='kitt-ai/__pycache__' \
  kitt-ai/
```

### Restaurer :
```bash
cd /home/kitt
tar xzf kitt-ai-backup-XXXXXXXX.tar.gz
cd kitt-ai/driver && bash install.sh
```

### Restauration complete apres reinstall JetPack :
```bash
bash /home/kitt/restore_kitt.sh
```

---

## 9. Depannage

| Probleme | Solution |
|----------|----------|
| LLM crash / lent | Fermer Chrome, verifier `free -h` (swap = lent) |
| Camera non detectee | `ls /dev/video*` — rebrancher USB |
| Visage non reconnu | Refaire enrolement, meilleur eclairage |
| Bluetooth ne detecte pas | `hcitool dev` — verifier MAC |
| LLM ne demarre pas | `curl http://127.0.0.1:8080/health` |
| TTS muet | `aplay -l` — verifier audio USB |
| Tunnel ne marche pas | `cat /tmp/cloudflared.log` |
| Serveur plante | `cat /tmp/kyronex_server.log` |

### Tester chaque composant :
```bash
# Bluetooth
hcitool name E0:33:8E:4B:75:AE

# Camera
python3 -c "import cv2; c=cv2.VideoCapture(0); print(c.read()[0]); c.release()"

# TTS
cd /home/kitt/kitt-ai && source venv/bin/activate
python3 piper_gpu.py --model models/fr_FR-tom-medium.onnx --test "Bonjour"

# LLM
curl http://127.0.0.1:8080/health

# Memoire
free -h
```

---

## 10. Specifications techniques

| Composant | Detail |
|-----------|--------|
| Plateforme | Jetson Orin Nano Super 8 GB |
| OS | Ubuntu 22.04 — JetPack 6.2.2 |
| Detection visage | YuNet (OpenCV DNN, CPU) |
| Reconnaissance | SFace (cosine, seuil 0.363) |
| LLM | Qwen 2.5 3B Q5_K_M (CUDA, llama.cpp, 1 slot) |
| TTS | PiperGPU — fr_FR-tom-medium (CUDA via onnxruntime) |
| STT | faster-whisper base (CUDA float16) |
| Vision | YOLOv8 (CUDA) |
| Contexte LLM | 1024 tokens |
| Historique chat | 10 messages |
| Inference LLM | ~20 tokens/s |
| 100% offline | Oui (tunnel optionnel pour partage) |
| Licence | Elastic License 2.0 |

---

## 11. Credits

KYRONEX est une intelligence artificielle locale developpee par
**Emmanuel Gelinne (Manix)**, laureat d'un concours NVIDIA,
avec la participation de **Virginie Barbay** (testeuse officielle),
en s'appuyant sur les technologies NVIDIA, Ollama et Mistral.

---

*KYRONEX — "Tous les systemes sont operationnels."*
