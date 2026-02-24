#!/usr/bin/env python3
"""
Guide Night Scheduler — PDF simple et clair
Copyright 2026 Manix (Emmanuel Gelinne) — Elastic License 2.0
"""

from fpdf import FPDF

BLACK   = (10, 10, 10)
DARK    = (18, 18, 25)
GREEN   = (0, 255, 136)
GREEN2  = (0, 180, 90)
GREEN3  = (0, 80, 40)
WHITE   = (220, 220, 220)
GREY    = (120, 120, 120)
AMBER   = (255, 200, 0)
BLUE    = (80, 160, 255)
RED     = (220, 50, 50)

FONTS_DIR = "/home/kitt/kitt-ai/fonts"


class NightGuide(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Orb", "",  f"{FONTS_DIR}/Orbitron-Regular.ttf")
        self.add_font("Orb", "B", f"{FONTS_DIR}/Orbitron-Bold.ttf")
        self.add_font("Spc", "",  f"{FONTS_DIR}/SpaceMono-Regular.ttf")
        self.add_font("Spc", "B", f"{FONTS_DIR}/SpaceMono-Bold.ttf")

    def bg(self):
        self.set_fill_color(*BLACK)
        self.rect(0, 0, 210, 297, "F")

    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self.set_font("Spc", "", 6)
        self.set_text_color(*GREY)
        self.cell(0, 5, f"KYRONEX — NIGHT SCHEDULER GUIDE — PAGE {self.page_no()}", align="C")

    # ── Titre de section ──────────────────────────────────────
    def section(self, num, title, color=GREEN):
        self.set_fill_color(*GREEN3)
        self.rect(10, self.get_y(), 190, 8, "F")
        self.set_font("Orb", "B", 9)
        self.set_text_color(*color)
        self.set_x(12)
        self.cell(0, 8, f"{num}  {title}", ln=True)
        self.ln(3)

    # ── Texte normal ─────────────────────────────────────────
    def body(self, text, color=WHITE, size=9):
        self.set_font("Spc", "", size)
        self.set_text_color(*color)
        self.set_x(14)
        self.multi_cell(182, 5.5, text)
        self.ln(2)

    # ── Bloc code ────────────────────────────────────────────
    def code(self, text):
        y0 = self.get_y()
        self.set_fill_color(10, 25, 15)
        lines = text.strip().split("\n")
        h = len(lines) * 5.5 + 6
        self.rect(12, y0, 186, h, "F")
        self.set_draw_color(*GREEN3)
        self.rect(12, y0, 186, h)
        self.set_xy(16, y0 + 3)
        self.set_font("Spc", "", 7.5)
        self.set_text_color(*GREEN)
        self.multi_cell(178, 5.5, text.strip())
        self.ln(4)

    # ── Encadré info ─────────────────────────────────────────
    def info_box(self, text, color=AMBER):
        y0 = self.get_y()
        self.set_fill_color(20, 18, 5)
        lines = text.count("\n") + 2
        h = lines * 5.5 + 8
        self.rect(12, y0, 186, h, "F")
        self.set_draw_color(*color)
        self.set_line_width(0.5)
        self.rect(12, y0, 3, h, "F")
        self.set_line_width(0.2)
        self.set_xy(18, y0 + 4)
        self.set_font("Spc", "", 8)
        self.set_text_color(*color)
        self.multi_cell(178, 5.5, text)
        self.ln(4)

    # ── Puce ─────────────────────────────────────────────────
    def bullet(self, text, color=WHITE):
        self.set_font("Spc", "", 8.5)
        self.set_text_color(*color)
        self.set_x(14)
        self.cell(6, 6, "\u25b8", ln=False)
        self.set_x(20)
        self.multi_cell(176, 5.5, text)


# ═══════════════════════════════════════════════════════════════
def build():
    pdf = NightGuide()

    # ── PAGE 1 : Couverture ─────────────────────────────────
    pdf.add_page()
    pdf.bg()

    # Cadre décoratif
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(0.8)
    pdf.rect(8, 8, 194, 281)
    pdf.set_line_width(0.3)
    pdf.rect(10, 10, 190, 277)

    # Logo / titre
    pdf.set_xy(0, 55)
    pdf.set_font("Orb", "B", 20)
    pdf.set_text_color(*GREEN)
    pdf.cell(210, 12, "KYRONEX", align="C", ln=True)

    pdf.set_font("Orb", "", 10)
    pdf.set_text_color(*GREEN2)
    pdf.cell(210, 8, "NIGHT SCHEDULER", align="C", ln=True)

    # Séparateur
    pdf.set_draw_color(*GREEN3)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y() + 3, 170, pdf.get_y() + 3)
    pdf.ln(10)

    # Sous-titre
    pdf.set_font("Spc", "B", 12)
    pdf.set_text_color(*WHITE)
    pdf.cell(210, 8, "Guide d'utilisation complet", align="C", ln=True)
    pdf.ln(4)
    pdf.set_font("Spc", "", 9)
    pdf.set_text_color(*GREY)
    pdf.cell(210, 6, "Comment faire travailler ton Jetson pendant que tu dors", align="C", ln=True)

    pdf.ln(20)

    # Schéma simple
    pdf.set_font("Spc", "", 9)
    pdf.set_text_color(*GREEN2)
    schema = [
        "   TOI                    JETSON (la nuit)",
        "",
        "  [Dors]   =====>   [Claude Code travaille]",
        "                          |",
        "                          v",
        "                    [Interface amelioree]",
        "                          |",
        "                          v",
        "  [Te reveilles] <===  [Versions sauvees]",
    ]
    for line in schema:
        pdf.set_x(0)
        pdf.cell(210, 5.5, line, align="C", ln=True)

    pdf.ln(20)

    # Infos bas de page
    pdf.set_font("Spc", "", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(210, 5, "By Manix (Emmanuel Gelinne) \u00b7 KYRONEX A.I. \u00b7 Jetson Orin Nano Super", align="C", ln=True)
    pdf.cell(210, 5, "2026 \u00b7 Elastic License 2.0", align="C", ln=True)

    # ── PAGE 2 : C'est quoi ? ───────────────────────────────
    pdf.add_page()
    pdf.bg()

    pdf.ln(6)
    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 10, "C'EST QUOI LE NIGHT SCHEDULER ?", ln=True, align="C")
    pdf.ln(4)

    pdf.section("1", "L'IDEE EN UNE PHRASE")
    pdf.body(
        "Le Night Scheduler fait travailler ton Jetson tout seul pendant la nuit.\n"
        "Il lance Claude Code automatiquement a une heure que tu choisis, et Claude\n"
        "ameliore l'interface web de KYRONEX sans que tu aies a faire quoi que ce soit."
    )

    pdf.section("2", "COMMENT CA MARCHE (version enfant de 8 ans)")
    pdf.bullet("Tu configures une \"fenetre\" : par exemple de 22h a 6h du matin.")
    pdf.ln(1)
    pdf.bullet("Quand l'horloge arrive a 22h, le Jetson se reveille tout seul.")
    pdf.ln(1)
    pdf.bullet("Il lance Claude Code N fois (ex: 10 fois).")
    pdf.ln(1)
    pdf.bullet("Chaque fois, Claude lit la page web de KYRONEX et y fait une petite amelioration.")
    pdf.ln(1)
    pdf.bullet("A chaque etape, une sauvegarde est faite. Si Claude fait une erreur -> retour arriere auto.")
    pdf.ln(1)
    pdf.bullet("Le matin, tu trouves une interface un peu mieux qu'avant !")
    pdf.ln(4)

    pdf.section("3", "CE QU'IL AMELIORE")
    pdf.body(
        "Il ameliore UNIQUEMENT l'interface web locale :\n"
        "   -> Le fichier : /home/kitt/kitt-ai/static/index.html\n"
        "   -> Ta page KYRONEX : https://192.168.1.4:3000\n\n"
        "Il ne touche PAS :\n"
        "   -> Ton site GitHub (on3egs.github.io/manix-kitt)\n"
        "   -> Le serveur Python (kyronex_server.py)\n"
        "   -> Le modele IA (Qwen 2.5)\n\n"
        "Exemples de ce qu'il peut ameliorer :\n"
        "   -> Animations plus fluides\n"
        "   -> Meilleure lisibilite des messages\n"
        "   -> Scanner KI2000 plus realiste\n"
        "   -> Bugs CSS corriges\n"
        "   -> Optimisations mobile"
    )

    pdf.section("4", "LES 3 PIECES DU SYSTEME")
    pdf.bullet("kitt_night_improve.sh  ->  le script qui lance Claude Code en boucle")
    pdf.ln(1)
    pdf.bullet("kitt_scheduler.py      ->  le daemon qui surveille l'heure")
    pdf.ln(1)
    pdf.bullet("Bouton NIGHT dans l'interface web  ->  l'interface graphique pour tout controler")

    # ── PAGE 3 : Utilisation interface web ──────────────────
    pdf.add_page()
    pdf.bg()

    pdf.ln(6)
    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 10, "UTILISER LE PANNEAU WEB", ln=True, align="C")
    pdf.ln(4)

    pdf.section("1", "OUVRIR LE PANNEAU")
    pdf.body(
        "1. Ouvre l'interface KYRONEX dans ton navigateur :\n"
        "   https://192.168.1.4:3000\n\n"
        "2. Dans le header en haut a droite, clique sur le bouton :\n"
        "   [ NIGHT ]\n\n"
        "3. Le panneau vert MU-TH-UR s'ouvre."
    )

    pdf.section("2", "CONFIGURER UNE FENETRE NOCTURNE")
    pdf.body("Dans la section \"AJOUTER UNE FENETRE\" :")
    pdf.bullet("DEBUT : heure de debut (ex: 22 h 00)")
    pdf.ln(1)
    pdf.bullet("FIN : heure de fin (ex: 6 h 00)")
    pdf.ln(1)
    pdf.bullet("ITERATIONS : combien de fois Claude ameliore (ex: 10)")
    pdf.ln(1)
    pdf.bullet("JOURS : quels jours de la semaine (cliquer pour selectionner/deselectionner)")
    pdf.ln(1)
    pdf.bullet("NOM : un nom pour reconnaitre la fenetre (ex: \"Nuit semaine\")")
    pdf.ln(2)
    pdf.body("Puis clique sur [+ PROGRAMMER].")

    pdf.section("3", "DEMARRER LE DAEMON")
    pdf.body(
        "Apres avoir ajoute ta fenetre, clique sur [START].\n"
        "Le badge passe de  O ARRETE  a  * ACTIF PID:XXXX\n"
        "Le daemon surveille l'heure toutes les minutes.\n"
        "Il se lance automatiquement quand on entre dans la fenetre horaire."
    )

    pdf.section("4", "LANCER MAINTENANT (sans attendre la nuit)")
    pdf.body(
        "Dans la section \"LANCER MAINTENANT\" :\n"
        "1. Tape le nombre d'iterations (ex: 3)\n"
        "2. Clique sur [ > GO ]\n"
        "3. Attends 2-3 minutes par iteration\n"
        "4. Clique sur [RAFRAICHIR] pour voir les logs"
    )

    pdf.info_box(
        "IMPORTANT : Chaque iteration prend environ 2 a 3 minutes.\n"
        "10 iterations = environ 30 minutes de travail.\n"
        "Ne pas eteindre le Jetson pendant que ca tourne !",
        color=AMBER
    )

    pdf.section("5", "GERER LES FENETRES")
    pdf.bullet("[ON/OFF] -> activer ou desactiver une fenetre sans la supprimer")
    pdf.ln(1)
    pdf.bullet("[X]      -> supprimer definitivement une fenetre")
    pdf.ln(1)
    pdf.bullet("[STOP]   -> arreter le daemon (les fenetres sont conservees)")

    # ── PAGE 4 : Commandes SSH ───────────────────────────────
    pdf.add_page()
    pdf.bg()

    pdf.ln(6)
    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 10, "COMMANDES SSH (terminal)", ln=True, align="C")
    pdf.ln(4)

    pdf.body(
        "Si tu preferes utiliser le terminal SSH plutot que l'interface web,\n"
        "voici toutes les commandes utiles.",
        color=GREY
    )

    pdf.section("1", "CONNEXION SSH AU JETSON")
    pdf.code(
        "# Depuis Windows (PowerShell ou PuTTY) :\n"
        "ssh kitt@192.168.1.4\n"
        "# Mot de passe sudo : 5505"
    )

    pdf.section("2", "DEMARRER KYRONEX")
    pdf.code(
        "cd /home/kitt/kitt-ai\n"
        "bash start_kyronex.sh"
    )

    pdf.section("3", "LANCER DES AMELIORATIONS MAINTENANT (ligne de commande)")
    pdf.code(
        "cd /home/kitt/kitt-ai\n"
        "# 1 iteration (test rapide, ~2-3 min) :\n"
        "bash kitt_night_improve.sh 1\n\n"
        "# 10 iterations (session complete, ~30 min) :\n"
        "bash kitt_night_improve.sh 10"
    )

    pdf.section("4", "DEMARRER LE DAEMON MANUELLEMENT")
    pdf.code(
        "cd /home/kitt/kitt-ai\n"
        "python3 kitt_scheduler.py --daemon &\n"
        "echo $! > kitt_scheduler.pid\n\n"
        "# Verifier qu'il tourne :\n"
        "cat kitt_scheduler.pid\n"
        "ps aux | grep kitt_scheduler"
    )

    pdf.section("5", "ARRETER LE DAEMON")
    pdf.code(
        "# Via l'API web :\n"
        "curl -sk -X POST https://localhost:3000/api/scheduler/stop\n\n"
        "# Ou manuellement :\n"
        "kill $(cat /home/kitt/kitt-ai/kitt_scheduler.pid)"
    )

    pdf.section("6", "VOIR LES LOGS EN TEMPS REEL")
    pdf.code(
        "# Logs du daemon :\n"
        "tail -f /tmp/kitt_scheduler.log\n\n"
        "# Logs du dernier GO (remplacer XXXX par le timestamp) :\n"
        "tail -f /tmp/kitt_now_XXXX.log\n\n"
        "# Lister tous les logs de nuit :\n"
        "ls -lt /tmp/kitt_night_*.log | head -5"
    )

    # ── PAGE 5 : Fichiers et dossiers ───────────────────────
    pdf.add_page()
    pdf.bg()

    pdf.ln(6)
    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 10, "FICHIERS ET DOSSIERS IMPORTANTS", ln=True, align="C")
    pdf.ln(4)

    pdf.section("1", "FICHIERS DU NIGHT SCHEDULER")
    pdf.code(
        "/home/kitt/kitt-ai/\n"
        "  kitt_night_improve.sh   <- Le script principal (lance Claude)\n"
        "  kitt_scheduler.py       <- Le daemon planificateur\n"
        "  kitt_schedule.json      <- Tes fenetres configurees (cree auto)\n"
        "  kitt_scheduler.pid      <- PID du daemon (cree auto)\n\n"
        "/tmp/\n"
        "  kitt_scheduler.log      <- Log du daemon\n"
        "  kitt_now_XXXX.log       <- Log d'un GO immediat\n"
        "  kitt_night_XXXX.log     <- Log d'une session nocturne"
    )

    pdf.section("2", "VERSIONS SAUVEGARDEES")
    pdf.body(
        "Apres chaque iteration reussie, une version est sauvegardee ici :"
    )
    pdf.code(
        "/home/kitt/kitt-ai/static/versions/\n"
        "  v00_avant_session_XXXX.html   <- Etat avant la session\n"
        "  v01_04h22_Analyse_le_xxx.html <- Version apres iteration 1\n"
        "  v02_04h25_Analyse_le_xxx.html <- Version apres iteration 2\n"
        "  ..."
    )
    pdf.body(
        "Si une amelioration casse quelque chose :\n"
        "-> Le fichier est automatiquement restaure a la version precedente.\n"
        "-> Tu peux aussi revenir manuellement :"
    )
    pdf.code(
        "# Revenir a une version specifique :\n"
        "cp /home/kitt/kitt-ai/static/versions/v00_avant_session_XXX.html \\\n"
        "   /home/kitt/kitt-ai/static/index.html\n\n"
        "# Puis redemarrer KYRONEX :\n"
        "cd /home/kitt/kitt-ai && bash start_kyronex.sh"
    )

    pdf.section("3", "VOIR CE QUI A ETE FAIT")
    pdf.code(
        "# Comparer avant/apres une session :\n"
        "diff /home/kitt/kitt-ai/static/versions/v00_avant_session_XXX.html \\\n"
        "     /home/kitt/kitt-ai/static/versions/v10_05h00_xxx.html\n\n"
        "# Lister toutes les versions (plus recentes en premier) :\n"
        "ls -lt /home/kitt/kitt-ai/static/versions/*.html | head -20"
    )

    # ── PAGE 6 : API et résumé ───────────────────────────────
    pdf.add_page()
    pdf.bg()

    pdf.ln(6)
    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 10, "ROUTES API ET RESUME", ln=True, align="C")
    pdf.ln(4)

    pdf.section("1", "ROUTES API (pour les curieux)")
    pdf.body("Toutes ces routes sont disponibles sur https://192.168.1.4:3000", color=GREY)
    pdf.code(
        "GET  /api/scheduler/status              <- Etat daemon + fenetres\n"
        "POST /api/scheduler/start               <- Demarrer le daemon\n"
        "POST /api/scheduler/stop                <- Arreter le daemon\n"
        "POST /api/scheduler/window              <- Ajouter une fenetre\n"
        "POST /api/scheduler/window/{id}/toggle  <- Activer/desactiver\n"
        "DELETE /api/scheduler/window/{id}       <- Supprimer\n"
        "POST /api/scheduler/run-now             <- GO (lancer maintenant)\n"
        "GET  /api/scheduler/logs                <- Voir les logs"
    )

    pdf.body("Exemple avec curl (depuis le Jetson) :")
    pdf.code(
        "# Voir le statut :\n"
        "curl -sk https://localhost:3000/api/scheduler/status\n\n"
        "# Ajouter une fenetre 22h->6h, 10 iterations, tous les jours :\n"
        "curl -sk -X POST https://localhost:3000/api/scheduler/window \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"name\":\"Nuit auto\",\"start_h\":22,\"end_h\":6,\"iterations\":10,\n"
        "       \"days\":[0,1,2,3,4,5,6]}'\n\n"
        "# Lancer 3 iterations maintenant :\n"
        "curl -sk -X POST https://localhost:3000/api/scheduler/run-now \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"iterations\": 3}'"
    )

    pdf.section("2", "RESUME EN 5 ETAPES")
    pdf.bullet("1. Ouvre https://192.168.1.4:3000", color=GREEN2)
    pdf.ln(1)
    pdf.bullet("2. Clique NIGHT -> Ajoute une fenetre (22h->6h, 10x, tous les jours)", color=GREEN2)
    pdf.ln(1)
    pdf.bullet("3. Clique START -> le daemon est actif", color=GREEN2)
    pdf.ln(1)
    pdf.bullet("4. Eteins ton ecran. La nuit, le Jetson travaille.", color=GREEN2)
    pdf.ln(1)
    pdf.bullet("5. Le matin, l'interface est amelioree. Les versions sont dans /static/versions/", color=GREEN2)
    pdf.ln(4)

    pdf.info_box(
        "CONSEIL : Commence par tester avec 1 iteration via le bouton GO.\n"
        "Regarde les logs. Si tout va bien, programme une fenetre nocturne.\n"
        "Commence avec 5 iterations, pas 50 !",
        color=BLUE
    )

    pdf.info_box(
        "ATTENTION : Le Jetson consomme beaucoup de RAM pendant les ameliorations.\n"
        "Ne pas utiliser le chatbot KYRONEX pendant qu'une session est en cours.\n"
        "Le Night Scheduler est fait pour tourner quand tu dors.",
        color=RED
    )

    return pdf


if __name__ == "__main__":
    out = "/home/kitt/kitt-ai/KYRONEX_Night_Scheduler_Guide.pdf"
    pdf = build()
    pdf.output(out)
    print(f"PDF genere : {out}")
