#!/usr/bin/env bash
# backup_html.sh — Centralise tous les fichiers HTML des projets KITT
# Usage : ./backup_html.sh
# Sortie : /home/kitt/backup_html/

set -euo pipefail

BACKUP_DIR="/home/kitt/backup_html"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.log"
INDEX_FILE="$BACKUP_DIR/index_backup.html"

SCAN_DIRS=(
    "/home/kitt/kitt-ai"
    "/home/kitt/Kitt-franco-belge"
)

EXCLUDE_DIRS=(".git" "venv" "audio_cache" "__pycache__" "node_modules")

# Compteurs
found=0
copied=0
errors=0

# Tableau des fichiers copiés : "new_name|source_path|size"
declare -a FILE_RECORDS=()

START_TS=$(date +%s)

# --- Initialisation ---
mkdir -p "$BACKUP_DIR"
echo "=== BACKUP HTML — $TIMESTAMP ===" > "$LOG_FILE"
echo "Répertoires scannés : ${SCAN_DIRS[*]}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

log() {
    echo "$*" | tee -a "$LOG_FILE"
}

# --- Construction des arguments d'exclusion find ---
build_find_cmd() {
    local scan_dir="$1"
    local prune_args=()
    for ex in "${EXCLUDE_DIRS[@]}"; do
        prune_args+=(-name "$ex" -o)
    done
    # Supprimer le dernier -o
    unset 'prune_args[${#prune_args[@]}-1]'

    find "$scan_dir" \
        \( "${prune_args[@]}" \) -prune \
        -o -name "*.html" -type f -print0
}

# --- Scan et copie ---
for scan_dir in "${SCAN_DIRS[@]}"; do
    if [ ! -d "$scan_dir" ]; then
        log "ATTENTION : répertoire introuvable : $scan_dir"
        continue
    fi
    log "Scan : $scan_dir"

    while IFS= read -r -d '' filepath; do
        ((found++)) || true
        filename="$(basename "$filepath")"
        stem="${filename%.html}"
        new_name="${stem}_${TIMESTAMP}.html"
        dest="$BACKUP_DIR/$new_name"

        # Anti-collision
        counter=1
        while [ -f "$dest" ]; do
            new_name="${stem}_${TIMESTAMP}_${counter}.html"
            dest="$BACKUP_DIR/$new_name"
            ((counter++))
        done

        # Taille source
        size_bytes="$(wc -c < "$filepath" 2>/dev/null || echo 0)"
        if [ "$size_bytes" -ge 1048576 ]; then
            size_human="$(echo "scale=1; $size_bytes/1048576" | bc)M"
        elif [ "$size_bytes" -ge 1024 ]; then
            size_human="$(echo "scale=1; $size_bytes/1024" | bc)K"
        else
            size_human="${size_bytes}B"
        fi

        if cp "$filepath" "$dest" 2>> "$LOG_FILE"; then
            ((copied++)) || true
            FILE_RECORDS+=("${new_name}|${filepath}|${size_human}")
            log "OK  $new_name  ← $filepath  ($size_human)"
        else
            ((errors++)) || true
            log "ERR $filepath"
        fi
    done < <(build_find_cmd "$scan_dir")
done

END_TS=$(date +%s)
DURATION=$(( END_TS - START_TS ))

log ""
log "Trouvés: $found / Copiés: $copied / Erreurs: $errors / Durée: ${DURATION}s"

# --- Génération de l'index HTML ---

# Construire les lignes du tableau
TABLE_ROWS=""
row_num=0
for record in "${FILE_RECORDS[@]}"; do
    IFS='|' read -r fname fpath fsize <<< "$record"
    ((row_num++)) || true
    # Alterner couleur de fond
    if (( row_num % 2 == 0 )); then
        row_bg="#0d0d0d"
    else
        row_bg="#111111"
    fi
    # Échapper les caractères HTML dans le chemin
    fpath_escaped="${fpath//&/&amp;}"
    fpath_escaped="${fpath_escaped//</&lt;}"
    fpath_escaped="${fpath_escaped//>/&gt;}"
    fname_escaped="${fname//&/&amp;}"

    TABLE_ROWS+="<tr style=\"background:${row_bg}\">"
    TABLE_ROWS+="<td style=\"color:#888;text-align:right;padding-right:8px\">${row_num}</td>"
    TABLE_ROWS+="<td><span style=\"color:#ff4444\">${fname_escaped}</span></td>"
    TABLE_ROWS+="<td style=\"color:#666;font-size:0.85em;word-break:break-all\">${fpath_escaped}</td>"
    TABLE_ROWS+="<td style=\"color:#aaa;text-align:right\">${fsize}</td>"
    TABLE_ROWS+="<td style=\"text-align:center\">"
    TABLE_ROWS+="<a href=\"${fname}\" download style=\"background:#1a1a2e;color:#ff4444;border:1px solid #ff4444;padding:2px 8px;text-decoration:none;font-size:0.85em;border-radius:2px\" title=\"Télécharger\">DL</a>"
    TABLE_ROWS+="</td>"
    TABLE_ROWS+="<td style=\"text-align:center\">"
    TABLE_ROWS+="<button onclick=\"speak('${fname_escaped}')\" style=\"background:none;border:1px solid #333;color:#aaa;cursor:pointer;font-size:1em;padding:2px 6px;border-radius:2px\" title=\"Lire le nom\">&#128266;</button>"
    TABLE_ROWS+="</td>"
    TABLE_ROWS+="</tr>"$'\n'
done

# Status couleur selon erreurs
if [ "$errors" -eq 0 ]; then
    STATUS_COLOR="#44ff44"
    STATUS_TEXT="OK"
else
    STATUS_COLOR="#ffaa00"
    STATUS_TEXT="${errors} erreur(s)"
fi

SCAN_DIRS_DISPLAY="${SCAN_DIRS[*]}"

cat > "$INDEX_FILE" << HTMLEOF
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KITT — Backup HTML — ${TIMESTAMP}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0a;
    color: #cccccc;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    padding: 20px;
  }
  h1 {
    color: #ff4444;
    font-size: 1.4em;
    letter-spacing: 0.15em;
    border-bottom: 1px solid #ff4444;
    padding-bottom: 8px;
    margin-bottom: 16px;
  }
  .stats {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    margin-bottom: 20px;
    padding: 12px;
    background: #111;
    border: 1px solid #333;
    border-left: 3px solid #ff4444;
  }
  .stat { display: flex; flex-direction: column; }
  .stat-label { font-size: 0.75em; color: #666; text-transform: uppercase; letter-spacing: 0.1em; }
  .stat-value { font-size: 1.3em; color: #ff4444; font-weight: bold; }
  .stat-value.ok { color: #44ff44; }
  .stat-value.warn { color: #ffaa00; }
  .search-bar {
    width: 100%;
    max-width: 500px;
    background: #111;
    border: 1px solid #444;
    color: #ccc;
    padding: 6px 12px;
    font-family: inherit;
    font-size: 0.9em;
    margin-bottom: 12px;
    outline: none;
  }
  .search-bar:focus { border-color: #ff4444; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88em;
  }
  thead tr {
    background: #1a0000;
    color: #ff4444;
    text-transform: uppercase;
    font-size: 0.78em;
    letter-spacing: 0.08em;
  }
  th, td {
    padding: 5px 8px;
    text-align: left;
    border-bottom: 1px solid #1a1a1a;
  }
  tbody tr:hover { background: #1a0a0a !important; }
  .footer {
    margin-top: 24px;
    font-size: 0.78em;
    color: #444;
    border-top: 1px solid #1a1a1a;
    padding-top: 12px;
  }
</style>
</head>
<body>
<h1>KITT — BACKUP HTML</h1>

<div class="stats">
  <div class="stat">
    <span class="stat-label">Fichiers copiés</span>
    <span class="stat-value">${copied}</span>
  </div>
  <div class="stat">
    <span class="stat-label">Fichiers trouvés</span>
    <span class="stat-value">${found}</span>
  </div>
  <div class="stat">
    <span class="stat-label">Erreurs</span>
    <span class="stat-value $([ "$errors" -eq 0 ] && echo ok || echo warn)">${errors}</span>
  </div>
  <div class="stat">
    <span class="stat-label">Statut</span>
    <span class="stat-value" style="color:${STATUS_COLOR}">${STATUS_TEXT}</span>
  </div>
  <div class="stat">
    <span class="stat-label">Durée</span>
    <span class="stat-value" style="color:#aaa">${DURATION}s</span>
  </div>
  <div class="stat">
    <span class="stat-label">Session</span>
    <span class="stat-value" style="color:#888;font-size:0.9em">${TIMESTAMP}</span>
  </div>
</div>

<input class="search-bar" type="search" id="searchInput" placeholder="Filtrer les fichiers..." oninput="filterTable()">

<table id="fileTable">
<thead>
<tr>
  <th style="width:40px">#</th>
  <th>Nouveau nom</th>
  <th>Chemin source</th>
  <th style="width:70px">Taille</th>
  <th style="width:60px">DL</th>
  <th style="width:50px">Lire</th>
</tr>
</thead>
<tbody id="tableBody">
${TABLE_ROWS}
</tbody>
</table>

<div class="footer">
  <p>Generé le : $(date '+%Y-%m-%d %H:%M:%S')</p>
  <p>Répertoires scannés : ${SCAN_DIRS_DISPLAY}</p>
  <p>Destination : ${BACKUP_DIR}</p>
  <p>Log : ${LOG_FILE}</p>
</div>

<script>
function speak(name) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  var text = name.replace(/_/g, ' ').replace(/\.html$/i, '');
  var u = new SpeechSynthesisUtterance(text);
  u.lang = 'fr-FR';
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
}

function filterTable() {
  var q = document.getElementById('searchInput').value.toLowerCase();
  var rows = document.getElementById('tableBody').getElementsByTagName('tr');
  for (var i = 0; i < rows.length; i++) {
    var text = rows[i].textContent.toLowerCase();
    rows[i].style.display = text.includes(q) ? '' : 'none';
  }
}
</script>
</body>
</html>
HTMLEOF

# --- Rapport terminal ---
echo ""
echo "=== RAPPORT BACKUP HTML ==="
echo "Fichiers trouvés : $found"
echo "Fichiers copiés  : $copied"
echo "Erreurs          : $errors"
echo "Durée            : ${DURATION}s"
echo "Destination      : $BACKUP_DIR"
echo "Index            : $INDEX_FILE"
echo "Log              : $LOG_FILE"
echo ""
