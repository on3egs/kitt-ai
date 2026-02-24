#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║  KITT SITE IMPROVER — Amélioration autonome site GitHub  ║
# ║  Usage: bash kitt_site_improve.sh [nb_iterations]        ║
# ║  Exemple: bash kitt_site_improve.sh 5                    ║
# ╚══════════════════════════════════════════════════════════╝
export PATH="/home/kitt/.local/bin:$PATH"

TARGET="/home/kitt/kitt-ai/site/index.html"
SITE_DIR="/home/kitt/kitt-ai/site"
BACKUP_DIR="/home/kitt/kitt-ai/site/backups_night"
VERSIONS_DIR="/home/kitt/kitt-ai/site/versions"
SESSION_ID="$(date +%Y%m%d_%H%M%S)"
LOG="/tmp/kitt_site_${SESSION_ID}.log"
NB_ITER="${1:-5}"

# ── Couleurs terminal ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  SITE GITHUB IMPROVER — KYRONEX"
echo -e "${NC}"
echo -e "${YELLOW}  Mode: AMÉLIORATIONS SITE GITHUB AUTONOMES${NC}"
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
    echo -e "${RED}ERREUR: Claude Code introuvable (claude non dans le PATH)${NC}"
    exit 1
fi

if ! git -C "$SITE_DIR" status &> /dev/null; then
    echo -e "${RED}ERREUR: $SITE_DIR n'est pas un dépôt git${NC}"
    exit 1
fi

# ── Dossiers ──
mkdir -p "$BACKUP_DIR"
mkdir -p "$VERSIONS_DIR"

# ── Version v00 = état initial ──
V0="${VERSIONS_DIR}/v00_avant_session_${SESSION_ID}.html"
cp "$TARGET" "$V0"
echo -e "${GREEN}Version v00 (état initial) : $V0${NC}"
echo ""

# ── Liste des tâches d'amélioration ──
TASKS=(
    "Analyse le fichier ${TARGET} (site vitrine GitHub Pages de KYRONEX) et améliore UNE chose dans la section héro (titre, sous-titre, animation, lisibilité). Fais un seul changement précis."

    "Analyse le fichier ${TARGET} (site vitrine GitHub Pages) et améliore la section des FONCTIONNALITÉS : meilleure mise en page des cards, icônes, descriptions plus claires. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} (site vitrine GitHub Pages) et améliore la NAVIGATION ou le FOOTER : liens plus visibles, meilleur contraste, ou layout amélioré sur mobile. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} (site vitrine GitHub Pages) et améliore les PERFORMANCES : minifier du CSS redondant, optimiser une animation, ou améliorer le chargement. Fais un seul changement précis."

    "Analyse le fichier ${TARGET} (site vitrine GitHub Pages) et améliore le SEO ou l'ACCESSIBILITÉ : balises alt manquantes, meta description, aria-labels, ou structure heading. Fais un seul changement précis."
)

# ── Boucle principale ──
SUCCESSES=0
FAILURES=0
PUSHED=0
START_TIME=$(date +%s)

for i in $(seq 1 $NB_ITER); do
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ITÉRATION ${i}/${NB_ITER} — $(date '+%H:%M:%S')${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    BACKUP_ITER="${BACKUP_DIR}/index_iter${i}_$(date +%H%M%S).html"
    cp "$TARGET" "$BACKUP_ITER"

    TASK_IDX=$(( (i - 1) % ${#TASKS[@]} ))
    TASK="${TASKS[$TASK_IDX]}"

    echo -e "  ${GREEN}Tâche: ${TASK:0:80}...${NC}"
    echo "=== ITERATION $i — $(date) ===" >> "$LOG"
    echo "TACHE: $TASK" >> "$LOG"

    claude --dangerously-skip-permissions \
        --print \
        "$TASK" \
        2>&1 | tee -a "$LOG"

    EXIT_CODE=${PIPESTATUS[0]}

    if [ $EXIT_CODE -eq 0 ]; then
        VER_NUM=$(printf "%02d" $i)
        VER_TIME=$(date +%Hh%M)
        VERSION_FILE="${VERSIONS_DIR}/v${VER_NUM}_${VER_TIME}_site.html"
        cp "$TARGET" "$VERSION_FILE"
        echo -e "\n  ${GREEN}OK  Version sauvegardée : v${VER_NUM}${NC}"
        SUCCESSES=$((SUCCESSES + 1))
        echo "RESULTAT: SUCCESS | VERSION: $VERSION_FILE" >> "$LOG"

        # ── Git push automatique ──
        echo -e "  ${CYAN}Git push vers GitHub...${NC}"
        cd "$SITE_DIR"
        git add index.html
        COMMIT_MSG="KYRONEX Night Scheduler — amélioration auto v${VER_NUM} [$(date '+%Y-%m-%d %H:%M')]"
        if git commit -m "$COMMIT_MSG" >> "$LOG" 2>&1; then
            if git push >> "$LOG" 2>&1; then
                echo -e "  ${GREEN}Push OK — site mis à jour en ligne${NC}"
                PUSHED=$((PUSHED + 1))
                echo "GIT PUSH: OK" >> "$LOG"
            else
                echo -e "  ${YELLOW}Push échoué (réseau ?) — changement conservé localement${NC}"
                echo "GIT PUSH: ECHEC" >> "$LOG"
            fi
        else
            echo -e "  ${YELLOW}Rien à committer (pas de changement détecté)${NC}"
        fi
        cd - > /dev/null
    else
        echo -e "\n  ${RED}ECHEC iteration $i (code $EXIT_CODE) — restauration...${NC}"
        FAILURES=$((FAILURES + 1))
        cp "$BACKUP_ITER" "$TARGET"
        echo "RESULTAT: FAILURE — restaure depuis backup" >> "$LOG"
    fi

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
echo -e "${CYAN}║      RAPPORT FINAL SITE GITHUB        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo -e "  ${GREEN}Succès  : ${SUCCESSES}/${NB_ITER}${NC}"
echo -e "  ${GREEN}Pushes  : ${PUSHED}/${SUCCESSES}${NC}"
echo -e "  ${RED}Échecs  : ${FAILURES}/${NB_ITER}${NC}"
echo -e "  Durée   : ${MINUTES}m ${SECONDS}s"
echo -e "  Log     : ${LOG}"
echo ""
echo "=== RAPPORT FINAL ===" >> "$LOG"
echo "Succes: $SUCCESSES/$NB_ITER | Pushes: $PUSHED | Echecs: $FAILURES | Duree: ${MINUTES}m${SECONDS}s" >> "$LOG"
