#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║  KITT NIGHT IMPROVER — Améliorations autonomes nocturnes ║
# ║  Usage: bash kitt_night_improve.sh [nb_iterations]       ║
# ║  Exemple: bash kitt_night_improve.sh 10                  ║
# ╚══════════════════════════════════════════════════════════╝
export PATH="/home/kitt/.local/bin:$PATH"

TARGET="/home/kitt/kitt-ai/static/index.html"
BACKUP_DIR="/home/kitt/kitt-ai/static/backups_night"
VERSIONS_DIR="/home/kitt/kitt-ai/static/versions"
SESSION_ID="$(date +%Y%m%d_%H%M%S)"
LOG="/tmp/kitt_night_${SESSION_ID}.log"
NB_ITER="${1:-10}"
CUSTOM_TASK_FILE="${2:-}"   # Optionnel : fichier contenant une tache personnalisee

# ── Couleurs terminal ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  ██╗  ██╗██╗████████╗████████╗    ███╗   ██╗██╗ ██████╗ ██╗  ██╗████████╗"
echo "  ██║ ██╔╝██║╚══██╔══╝╚══██╔══╝    ████╗  ██║██║██╔════╝ ██║  ██║╚══██╔══╝"
echo "  █████╔╝ ██║   ██║      ██║       ██╔██╗ ██║██║██║  ███╗███████║   ██║   "
echo "  ██╔═██╗ ██║   ██║      ██║       ██║╚██╗██║██║██║   ██║██╔══██║   ██║   "
echo "  ██║  ██╗██║   ██║      ██║       ██║ ╚████║██║╚██████╔╝██║  ██║   ██║   "
echo "  ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝       ╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   "
echo -e "${NC}"
echo -e "${YELLOW}  Mode: AMÉLIORATIONS AUTONOMES NOCTURNES${NC}"
echo -e "  Fichier cible : ${TARGET}"
echo -e "  Itérations    : ${NB_ITER}"
echo -e "  Log           : ${LOG}"
echo ""

# ── Vérifications ──
if [ ! -f "$TARGET" ]; then
    echo -e "${RED}ERREUR: Fichier cible introuvable: $TARGET${NC}"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo -e "${RED}ERREUR: Claude Code n'est pas installé (commande 'claude' introuvable)${NC}"
    exit 1
fi

# ── Dossiers ──
mkdir -p "$BACKUP_DIR"
mkdir -p "$VERSIONS_DIR"

# ── Version v00 = état initial avant toute modification ──
V0="${VERSIONS_DIR}/v00_avant_session_${SESSION_ID}.html"
cp "$TARGET" "$V0"
echo -e "${GREEN}Version v00 (état initial) : $V0${NC}"
echo ""

# ── Liste des tâches d'amélioration ──
# Chaque tâche est une instruction précise pour Claude
TASKS=(
    "Analyse le fichier ${TARGET} et améliore UNE chose dans la zone de CHAT : meilleure lisibilité des bulles de message (padding, border-radius, couleurs), transitions d'apparition des messages plus fluides, ou scrollbar stylisée. Fais un seul changement précis et testé."

    "Analyse le fichier ${TARGET} et améliore l'interface INPUT en bas de page : meilleur focus visuel sur l'input, animation du bouton SEND quand actif, ou indicateur visuel pendant l'envoi. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore l'accessibilité MOBILE : vérifier que les zones tactiles sont suffisamment grandes, que le scroll fonctionne bien, ou optimiser le layout pour les petits écrans (<400px). Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore les PERFORMANCES JavaScript : cherche une fonction qui pourrait être optimisée (mémoisation, réduction de reflows DOM, debounce manquant) et améliore-la. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore l'effet visuel de la SPHERE 3D CSS : meilleure animation des anneaux, effet de profondeur plus réaliste, ou transition plus douce des couleurs. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore le HEADER : meilleur affichage sur mobile (le titre K I T T et le sous-titre), animation subtile au chargement, ou meilleure visibilité des boutons VIG/AMB/RST. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore les animations du SCANNER KI2000 : ajuste les paramètres de vitesse, de luminosité de la tête, ou de longueur de la trainée pour un rendu encore plus fidèle au KITT original. Fais un seul changement précis dans le JS rAF du scanner."

    "Analyse le fichier ${TARGET} et améliore la TYPOGRAPHIE : meilleure hiérarchie visuelle des textes, espacement des lettres optimisé pour la lisibilité, ou un style amélioré pour les messages d'erreur/statut. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} et améliore les TRANSITIONS et ANIMATIONS CSS : cherche une transition trop abrupte ou manquante et ajoute une animation smooth. Par exemple: apparition du panneau mémoire, feedback des boutons, ou transition des états du scanner. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} dans son ensemble. Trouve le bug visuel ou l'incohérence UX la plus évidente et corrige-la. Documente dans un commentaire HTML ce que tu as corrigé et pourquoi."
)

# ── Boucle principale ──
SUCCESSES=0
FAILURES=0
START_TIME=$(date +%s)

for i in $(seq 1 $NB_ITER); do
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ITÉRATION ${i}/${NB_ITER} — $(date '+%H:%M:%S')${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Snapshot AVANT (sécurité restauration)
    BACKUP_ITER="${BACKUP_DIR}/index_iter${i}_$(date +%H%M%S).html"
    cp "$TARGET" "$BACKUP_ITER"

    # Selectionner la tache : custom ou auto
    if [ -n "$CUSTOM_TASK_FILE" ] && [ -f "$CUSTOM_TASK_FILE" ]; then
        TASK="$(cat "$CUSTOM_TASK_FILE")"
    else
        TASK_IDX=$(( (i - 1) % ${#TASKS[@]} ))
        TASK="${TASKS[$TASK_IDX]}"
    fi

    echo -e "  ${GREEN}Tâche: ${TASK:0:80}...${NC}"
    echo "" | tee -a "$LOG"
    echo "=== ITERATION $i — $(date) ===" >> "$LOG"
    echo "TACHE: $TASK" >> "$LOG"
    echo "" >> "$LOG"

    # Mettre à jour le journal de session dans CLAUDE.md
    LINES_NOW=$(wc -l < "$TARGET")
    SIZE_NOW=$(du -h "$TARGET" | cut -f1)
    sed -i "s|^Voir : .*versions.*|Voir : /home/kitt/kitt-ai/static/versions/ — Session ${SESSION_ID}, itération ${i}/${NB_ITER} en cours, fichier ${SIZE_NOW}/${LINES_NOW} lignes|" /home/kitt/kitt-ai/CLAUDE.md

    # ── Lancer Claude en mode autonome ──
    # Claude lit automatiquement CLAUDE.md (briefing projet) avant d'agir
    claude --dangerously-skip-permissions \
        --print \
        "$TASK" \
        2>&1 | tee -a "$LOG"

    EXIT_CODE=${PIPESTATUS[0]}

    if [ $EXIT_CODE -eq 0 ]; then
        # ── Sauvegarder la nouvelle version créée ──
        VER_NUM=$(printf "%02d" $i)
        VER_TIME=$(date +%Hh%M)
        VER_TASK_SHORT=$(echo "${TASK:0:40}" | tr ' ' '_' | tr -cd '[:alnum:]_-')
        VERSION_FILE="${VERSIONS_DIR}/v${VER_NUM}_${VER_TIME}_${VER_TASK_SHORT}.html"
        cp "$TARGET" "$VERSION_FILE"
        LINES=$(wc -l < "$TARGET")
        SIZE=$(du -h "$TARGET" | cut -f1)
        echo -e "\n  ${GREEN}OK  Version sauvegardee : v${VER_NUM}${NC}"
        echo -e "  ${CYAN}     Fichier : $(basename $VERSION_FILE)${NC}"
        echo -e "  ${CYAN}     Taille  : ${SIZE} — ${LINES} lignes${NC}"
        echo "RESULTAT: SUCCESS | VERSION: $VERSION_FILE" >> "$LOG"
        SUCCESSES=$((SUCCESSES + 1))
        # Noter ce qui vient d'être fait dans CLAUDE.md pour les prochaines itérations
        TASK_NOTE="- v${VER_NUM} [$(date '+%Hh%M')] : ${TASK:0:80}... ✅"
        sed -i "s|^## Journal des sessions.*|## Journal des sessions (mis à jour automatiquement)\n${TASK_NOTE}|" /home/kitt/kitt-ai/CLAUDE.md
    else
        echo -e "\n  ${RED}ECHEC iteration $i (code $EXIT_CODE) — restauration...${NC}"
        echo "RESULTAT: FAILURE (code $EXIT_CODE) — restaure depuis backup" >> "$LOG"
        FAILURES=$((FAILURES + 1))
        cp "$BACKUP_ITER" "$TARGET"
        echo -e "  ${YELLOW}Fichier restaure a l'etat precedent${NC}"
    fi

    # Pause entre les itérations (laisser le temps au LLM de se libérer)
    if [ $i -lt $NB_ITER ]; then
        echo -e "  ${CYAN}Pause 15s avant prochaine itération...${NC}"
        sleep 15
    fi
done

# ── Résumé final ──
END_TIME=$(date +%s)
DURATION=$(( END_TIME - START_TIME ))
MINUTES=$(( DURATION / 60 ))
SECONDS=$(( DURATION % 60 ))

echo -e "\n${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         RAPPORT FINAL KITT            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo -e "  ${GREEN}Succes  : ${SUCCESSES}/${NB_ITER}${NC}"
echo -e "  ${RED}Echecs  : ${FAILURES}/${NB_ITER}${NC}"
echo -e "  Duree   : ${MINUTES}m ${SECONDS}s"
echo -e "  Log     : ${LOG}"
echo ""
echo -e "${CYAN}  Versions creees dans : ${VERSIONS_DIR}/${NC}"
echo ""

# Lister toutes les versions de cette session
NB_VERS=$(ls "${VERSIONS_DIR}"/v[0-9]*.html 2>/dev/null | wc -l)
if [ $NB_VERS -gt 0 ]; then
    echo -e "  ${BOLD}Toutes les versions disponibles :${NC}"
    ls -1 "${VERSIONS_DIR}"/v[0-9]*.html 2>/dev/null | while read f; do
        SIZE=$(du -h "$f" | cut -f1)
        echo -e "    ${GREEN}$(basename $f)${NC}  (${SIZE})"
    done
fi

echo ""
echo -e "${YELLOW}  KITT a travaille pour toi cette nuit !${NC}"
echo -e "${DG}  Compare les versions avec : diff ${VERSIONS_DIR}/v00_*.html ${VERSIONS_DIR}/vNN_*.html${NC}"
echo ""

echo "" >> "$LOG"
echo "=== RAPPORT FINAL ===" >> "$LOG"
echo "Succes: $SUCCESSES/$NB_ITER | Echecs: $FAILURES/$NB_ITER | Duree: ${MINUTES}m${SECONDS}s" >> "$LOG"
echo "Versions dans: $VERSIONS_DIR" >> "$LOG"
ls "${VERSIONS_DIR}"/v[0-9]*.html 2>/dev/null >> "$LOG"
