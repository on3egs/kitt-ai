#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  KITT HTML IMPROVER — Améliore n'importe quel fichier HTML  ║
# ║  Usage: ./improve_any_html.sh <fichier.html> [iterations]   ║
# ║  Exemple: ./improve_any_html.sh monsite.html 5              ║
# ╚══════════════════════════════════════════════════════════════╝
export PATH="/home/kitt/.local/bin:$PATH"

# ── Arguments ──
TARGET="${1:-}"
NB_ITER="${2:-3}"
CUSTOM_TASK_FILE="${3:-}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Aide ──
if [ -z "$TARGET" ] || [ "$TARGET" = "-h" ] || [ "$TARGET" = "--help" ]; then
    echo -e "${CYAN}${BOLD}KITT HTML IMPROVER${NC}"
    echo ""
    echo -e "  Usage: $0 <fichier.html> [iterations] [task_file]"
    echo ""
    echo -e "  ${GREEN}Exemples :${NC}"
    echo "    $0 /home/kitt/backup_html/monsite_20260224.html"
    echo "    $0 /home/kitt/backup_html/monsite_20260224.html 5"
    echo "    $0 monsite.html 3 ma_tache.txt"
    echo ""
    echo -e "  ${CYAN}Pour améliorer tous les HTML d'un dossier :${NC}"
    echo "    for f in /home/kitt/backup_html/*.html; do $0 \"\$f\" 2; done"
    echo ""
    exit 0
fi

# Chemin absolu
TARGET="$(realpath "$TARGET" 2>/dev/null || echo "$TARGET")"

if [ ! -f "$TARGET" ]; then
    echo -e "${RED}ERREUR: Fichier introuvable: $TARGET${NC}"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    echo -e "${RED}ERREUR: Claude Code introuvable (commande 'claude')${NC}"
    exit 1
fi

# ── Dossiers de sortie ──
STEM="$(basename "$TARGET" .html)"
WORK_DIR="$(dirname "$TARGET")/improved_${STEM}"
mkdir -p "$WORK_DIR"

SESSION_ID="$(date +%Y%m%d_%H%M%S)"
LOG="${WORK_DIR}/improve_${SESSION_ID}.log"

echo -e "${CYAN}${BOLD}"
echo "  ██╗  ██╗████████╗████████╗██╗         ██╗███╗   ███╗██████╗ ██████╗  ██████╗ ██╗   ██╗███████╗██████╗ "
echo "  ██║ ██╔╝╚══██╔══╝╚══██╔══╝██║         ██║████╗ ████║██╔══██╗██╔══██╗██╔═══██╗██║   ██║██╔════╝██╔══██╗"
echo "  █████╔╝    ██║      ██║   ██║         ██║██╔████╔██║██████╔╝██████╔╝██║   ██║██║   ██║█████╗  ██████╔╝"
echo "  ██╔═██╗    ██║      ██║   ██║         ██║██║╚██╔╝██║██╔═══╝ ██╔══██╗██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗"
echo "  ██║  ██╗   ██║      ██║   ███████╗    ██║██║ ╚═╝ ██║██║     ██║  ██║╚██████╔╝ ╚████╔╝ ███████╗██║  ██║"
echo "  ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝    ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "  Fichier  : ${GREEN}${TARGET}${NC}"
echo -e "  Sortie   : ${CYAN}${WORK_DIR}${NC}"
echo -e "  Sessions : ${NB_ITER} itérations"
echo ""

# Version v00 — état avant toute modification
V0="${WORK_DIR}/v00_original.html"
cp "$TARGET" "$V0"
echo -e "${GREEN}  v00 sauvegardé : $V0${NC}"
echo ""

# Copie de travail (on améliore CETTE copie, pas l'original)
WORKING_COPY="${WORK_DIR}/working.html"
cp "$TARGET" "$WORKING_COPY"

# ── Tâches génériques d'amélioration HTML ──
TASKS=(
    "Analyse le fichier ${WORKING_COPY} et améliore la LISIBILITÉ : meilleure typographie (taille de police, interlignage, contraste), hiérarchie visuelle des titres, ou espacement entre sections. Fais un seul changement précis dans le CSS ou HTML."

    "Analyse le fichier ${WORKING_COPY} et améliore l'expérience MOBILE : vérifier les media queries, les zones tactiles (minimum 44px), le viewport, et le comportement du scroll sur iOS. Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} et améliore les PERFORMANCES : optimiser le CSS (supprimer les règles inutilisées, fusionner les sélecteurs similaires), différer le JS non critique, ou ajouter des attributs manquants (loading=lazy sur les images). Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} et améliore l'ACCESSIBILITÉ : ajouter des attributs alt manquants, des rôles ARIA, des labels sur les formulaires, ou améliorer le contraste des couleurs. Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} et améliore les ANIMATIONS et transitions CSS : rendre les transitions plus fluides (cubic-bezier approprié), ajouter un effet d'apparition subtil aux éléments importants, ou corriger une animation trop brusque. Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} et améliore la STRUCTURE HTML : vérifier la sémantique (utiliser header/main/footer/article/section), corriger les niveaux de titres (h1→h2→h3), ou améliorer l'organisation du DOM. Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} et améliore la ROBUSTESSE JavaScript : ajouter des vérifications null/undefined manquantes, utiliser addEventListener au lieu de onclick inline, ou corriger une gestion d'erreur absente. Fais un seul changement précis."

    "Analyse le fichier ${WORKING_COPY} dans son ensemble. Trouve le bug visuel ou l'incohérence UX la plus évidente et corrige-la. Ajoute un commentaire HTML pour documenter ce que tu as corrigé et pourquoi."
)

# ── Boucle principale ──
SUCCESSES=0
FAILURES=0
START_TIME=$(date +%s)

for i in $(seq 1 "$NB_ITER"); do
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ITÉRATION ${i}/${NB_ITER} — $(date '+%H:%M:%S')${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Snapshot avant (sécurité restauration)
    BACKUP_ITER="${WORK_DIR}/before_iter${i}.html"
    cp "$WORKING_COPY" "$BACKUP_ITER"

    # Sélection tâche
    if [ -n "$CUSTOM_TASK_FILE" ] && [ -f "$CUSTOM_TASK_FILE" ]; then
        TASK="$(cat "$CUSTOM_TASK_FILE")"
    else
        TASK_IDX=$(( (i - 1) % ${#TASKS[@]} ))
        TASK="${TASKS[$TASK_IDX]}"
    fi

    echo -e "  ${GREEN}Tâche: ${TASK:0:90}...${NC}"
    echo ""
    echo "=== ITERATION $i — $(date) ===" >> "$LOG"
    echo "TACHE: $TASK" >> "$LOG"
    echo "" >> "$LOG"

    # ── Claude améliore WORKING_COPY ──
    claude --dangerously-skip-permissions \
        --print \
        "$TASK" \
        2>&1 | tee -a "$LOG"

    EXIT_CODE=${PIPESTATUS[0]}

    if [ $EXIT_CODE -eq 0 ]; then
        VER_NUM=$(printf "%02d" "$i")
        VER_TIME=$(date +%Hh%M)
        VER_TASK_SHORT=$(echo "${TASK:0:35}" | tr ' ' '_' | tr -cd '[:alnum:]_-')
        VERSION_FILE="${WORK_DIR}/v${VER_NUM}_${VER_TIME}_${VER_TASK_SHORT}.html"
        cp "$WORKING_COPY" "$VERSION_FILE"
        LINES=$(wc -l < "$WORKING_COPY")
        SIZE=$(du -h "$WORKING_COPY" | cut -f1)
        echo -e "\n  ${GREEN}OK  Version : v${VER_NUM} — ${SIZE} — ${LINES} lignes${NC}"
        echo -e "  ${CYAN}     $(basename "$VERSION_FILE")${NC}"
        echo "RESULTAT: SUCCESS | VERSION: $VERSION_FILE" >> "$LOG"
        SUCCESSES=$((SUCCESSES + 1))
        # Nettoyer le snapshot temporaire
        rm -f "$BACKUP_ITER"
    else
        echo -e "\n  ${RED}ECHEC iteration $i (code $EXIT_CODE) — restauration...${NC}"
        echo "RESULTAT: FAILURE (code $EXIT_CODE) — restauré" >> "$LOG"
        FAILURES=$((FAILURES + 1))
        cp "$BACKUP_ITER" "$WORKING_COPY"
        echo -e "  ${YELLOW}Fichier restauré${NC}"
    fi

    if [ "$i" -lt "$NB_ITER" ]; then
        echo -e "  ${CYAN}Pause 10s...${NC}"
        sleep 10
    fi
done

# ── Résultat final ──
END_TIME=$(date +%s)
DURATION=$(( END_TIME - START_TIME ))
MINUTES=$(( DURATION / 60 ))
SECS=$(( DURATION % 60 ))

# Copier le résultat final à côté de l'original
FINAL_OUT="$(dirname "$TARGET")/${STEM}_improved_${SESSION_ID}.html"
cp "$WORKING_COPY" "$FINAL_OUT"

echo -e "\n${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         RAPPORT FINAL KITT IMPROVER          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo -e "  ${GREEN}Succès  : ${SUCCESSES}/${NB_ITER}${NC}"
echo -e "  ${RED}Échecs  : ${FAILURES}/${NB_ITER}${NC}"
echo -e "  Durée   : ${MINUTES}m ${SECS}s"
echo -e "  Original  : ${TARGET}"
echo -e "  ${GREEN}Résultat  : ${FINAL_OUT}${NC}"
echo -e "  Versions  : ${WORK_DIR}/"
echo -e "  Log       : ${LOG}"
echo ""
echo -e "${YELLOW}  Diff : diff ${V0} ${FINAL_OUT}${NC}"
echo ""

echo "" >> "$LOG"
echo "=== RAPPORT FINAL ===" >> "$LOG"
echo "Succès: $SUCCESSES/$NB_ITER | Durée: ${MINUTES}m${SECS}s" >> "$LOG"
echo "Original: $TARGET" >> "$LOG"
echo "Résultat: $FINAL_OUT" >> "$LOG"
