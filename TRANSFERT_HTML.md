# KITT — Transfert HTML vers Windows / iPhone

IP du Jetson (vérifier si DHCP change) : **192.168.1.4**
Utilisateur SSH : **kitt**
Dossier HTML backupé : `/home/kitt/backup_html/`

---

## 1. DEPUIS WINDOWS (PowerShell)

### Télécharger TOUS les HTML d'un coup
```powershell
scp -r kitt@192.168.1.32:/home/kitt/backup_html/ C:\Users\Manix\Desktop\kitt-html\
```

### Télécharger un seul fichier HTML
```powershell
scp kitt@192.168.1.32:/home/kitt/kitt-ai/static/index.html C:\Users\Manix\Desktop\index.html
```

### Synchroniser (rsync via WSL si installé)
```bash
rsync -avz --progress kitt@192.168.1.32:/home/kitt/backup_html/ ~/Desktop/kitt-html/
```

> Si l'IP a changé, la retrouver sur le Jetson avec : `hostname -I`

---

## 2. DEPUIS IPHONE (app Termius, a-Shell, ou SSH Files)

### App recommandée : **Termius** (gratuit sur App Store)
1. Ouvrir Termius → New Host → IP: 192.168.1.32 / User: kitt
2. Onglet SFTP → naviguer vers `/home/kitt/backup_html/`
3. Sélectionner les fichiers → Télécharger

### Via a-Shell (terminal iPhone)
```bash
scp -r kitt@192.168.1.32:/home/kitt/backup_html/ ~/Documents/kitt-html/
```

---

## 3. LANCER LE BACKUP HTML (sur le Jetson)

Génère tous les HTML dans `/home/kitt/backup_html/` + index navigable :
```bash
cd /home/kitt/kitt-ai && ./backup_html.sh
```

---

## 4. AMÉLIORER UN HTML AVEC CLAUDE (sur le Jetson)

### Améliorer un seul fichier (3 itérations par défaut)
```bash
cd /home/kitt/kitt-ai
./improve_any_html.sh /home/kitt/backup_html/monsite_20260224.html
```

### Améliorer avec plus d'itérations
```bash
./improve_any_html.sh /home/kitt/backup_html/monsite_20260224.html 5
```

### Améliorer avec une tâche personnalisée
```bash
echo "Améliore les performances CSS de ce fichier, supprime les règles dupliquées" > tache.txt
./improve_any_html.sh monsite.html 3 tache.txt
```

### Améliorer TOUS les HTML du backup en série
```bash
for f in /home/kitt/backup_html/*.html; do
    echo "=== $f ==="
    ./improve_any_html.sh "$f" 2
done
```

### Résultats
- Fichier amélioré : à côté du fichier original → `nom_improved_TIMESTAMP.html`
- Versions intermédiaires : `improved_nom/v01_... v02_...`
- Log : `improved_nom/improve_TIMESTAMP.log`

---

## WORKFLOW COMPLET

```bash
# 1. Backup tous les HTML du Jetson
cd /home/kitt/kitt-ai && ./backup_html.sh

# 2. Améliorer un fichier spécifique
./improve_any_html.sh /home/kitt/backup_html/index_20260224_XXXXX.html 5

# 3. Récupérer le résultat depuis Windows
scp kitt@192.168.1.32:/home/kitt/backup_html/index_improved_*.html C:\Users\Manix\Desktop\
```
