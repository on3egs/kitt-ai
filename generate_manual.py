#!/usr/bin/env python3
"""
Générateur du Mode d'emploi KYRONEX — Style rétro-futuriste
Copyright 2026 Manix (Emmanuel Gelinne) — Elastic License 2.0
"""

from fpdf import FPDF

# ── Palette ──────────────────────────────────────────────────
BLACK    = (10, 10, 10)
DARK_BG  = (15, 15, 15)
RED      = (220, 30, 30)
RED_DIM  = (160, 20, 20)
RED_DARK = (80, 0, 0)
RED_GLOW = (255, 80, 80)
WHITE    = (225, 225, 225)
GREY     = (140, 140, 140)
GREY_DK  = (55, 55, 55)
AMBER    = (255, 180, 0)
GREEN    = (0, 200, 80)
CYAN     = (0, 200, 200)

FONTS_DIR = "/home/kitt/kitt-ai/fonts"


class KyronexManual(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Orb",  "",  f"{FONTS_DIR}/Orbitron-Regular.ttf")
        self.add_font("Orb",  "B", f"{FONTS_DIR}/Orbitron-Bold.ttf")
        self.add_font("Spc",  "",  f"{FONTS_DIR}/SpaceMono-Regular.ttf")
        self.add_font("Spc",  "B", f"{FONTS_DIR}/SpaceMono-Bold.ttf")
        self.chapter_num = 0

    # ── Fond ─────────────────────────────────────────────────
    def draw_bg(self):
        self.set_fill_color(*BLACK)
        self.rect(0, 0, 210, 297, "F")
        self.set_draw_color(18, 18, 18)
        self.set_line_width(0.1)
        for x in range(0, 211, 10):
            self.line(x, 0, x, 297)
        for y in range(0, 298, 10):
            self.line(0, y, 210, y)

    # ── Scanner ───────────────────────────────────────────────
    def scanner(self, y, pos=0.5, width=180):
        xs = (210 - width) / 2
        self.set_fill_color(30, 0, 0)
        self.rect(xs, y, width, 3.5, "F")
        lx = xs + pos * (width - 8)
        for i in range(22):
            a = 1.0 - i / 22.0
            self.set_fill_color(int(220 * a), 0, 0)
            gw = 30 - i * 1.3
            if gw > 0:
                self.rect(lx + 4 - gw / 2, y, gw, 3.5, "F")
        self.set_fill_color(255, 110, 110)
        self.rect(lx + 2, y + 0.5, 4, 2.5, "F")

    # ── Décorations haut/bas ──────────────────────────────────
    def header(self):
        if self.page_no() > 1:
            self.draw_bg()
            self.set_fill_color(*RED_DARK)
            self.rect(0, 0, 210, 1.5, "F")
            self.set_fill_color(*RED)
            self.rect(20, 0, 170, 0.4, "F")

    def footer(self):
        if self.page_no() > 1:
            y = 287
            self.set_fill_color(*RED_DARK)
            self.rect(0, y, 210, 0.4, "F")
            self.set_font("Spc", "", 7)
            self.set_text_color(*GREY_DK)
            self.set_xy(0, y + 1)
            self.cell(105, 5, "KYRONEX — Kinetic Yielding Responsive Onboard Neural EXpert", align="R")
            self.set_text_color(*RED_DIM)
            self.cell(95, 5, f"  Page {self.page_no()}", align="L")

    def new_page(self):
        self.add_page()
        if self.page_no() == 1:
            self.draw_bg()

    # ── Éléments typographiques ───────────────────────────────
    def section_title(self, title):
        self.chapter_num += 1
        y = self.get_y()
        if y > 240:
            self.new_page(); y = 20
        self.set_fill_color(*RED_DARK)
        self.rect(15, y, 180, 0.3, "F")
        y += 3
        self.set_font("Orb", "B", 13)
        self.set_text_color(*RED)
        self.set_xy(15, y)
        self.cell(0, 9, f"{self.chapter_num}. {title}", ln=True)
        y = self.get_y()
        self.scanner(y, pos=(self.chapter_num * 0.17) % 1.0, width=180)
        self.set_y(y + 7)

    def sub_title(self, title):
        y = self.get_y()
        if y > 260:
            self.new_page()
        self.set_font("Spc", "B", 9)
        self.set_text_color(*RED_GLOW)
        self.set_x(20)
        self.cell(4, 7, ">")
        self.set_font("Orb", "", 9)
        self.cell(0, 7, f" {title}", ln=True)
        self.ln(1)

    def body(self, text):
        self.set_font("Spc", "", 9)
        self.set_text_color(*WHITE)
        self.set_x(20)
        self.multi_cell(170, 5, text)
        self.ln(2)

    def bullets(self, items):
        self.set_font("Spc", "", 9)
        for item in items:
            y = self.get_y()
            if y > 270:
                self.new_page(); self.set_y(20)
            self.set_fill_color(*RED)
            self.rect(22, y + 1.8, 2, 2, "F")
            self.set_text_color(*WHITE)
            self.set_xy(27, y)
            self.multi_cell(160, 5, item)
            self.ln(1)
        self.ln(1)

    def code(self, text):
        y = self.get_y()
        lines = text.strip().split("\n")
        h = len(lines) * 5 + 6
        if y + h > 275:
            self.new_page(); y = 20
        self.set_fill_color(18, 18, 22)
        self.set_draw_color(*RED_DARK)
        self.rect(25, y, 160, h, "DF")
        self.set_fill_color(*RED_DIM)
        self.rect(25, y, 1.8, h, "F")
        self.set_font("Spc", "", 8)
        self.set_text_color(*AMBER)
        for i, ln in enumerate(lines):
            self.set_xy(30, y + 3 + i * 5)
            self.cell(150, 5, ln)
        self.set_y(y + h + 4)

    def info_box(self, title, text, color=None):
        if color is None:
            color = RED_DIM
        y = self.get_y()
        lines = text.split("\n")
        h = len(lines) * 5 + 14
        if y + h > 270:
            self.new_page(); y = 20
        self.set_fill_color(22, 10, 10)
        self.set_draw_color(*color)
        self.rect(20, y, 170, h, "DF")
        self.set_font("Orb", "B", 8)
        self.set_text_color(*RED_GLOW)
        self.set_xy(25, y + 2)
        self.cell(0, 5, title)
        self.set_font("Spc", "", 8)
        self.set_text_color(*WHITE)
        for i, ln in enumerate(lines):
            self.set_xy(25, y + 9 + i * 5)
            self.cell(160, 5, ln)
        self.set_y(y + h + 3)

    def green_box(self, title, text):
        y = self.get_y()
        lines = text.split("\n")
        h = len(lines) * 5 + 14
        if y + h > 270:
            self.new_page(); y = 20
        self.set_fill_color(10, 22, 10)
        self.set_draw_color(0, 120, 40)
        self.rect(20, y, 170, h, "DF")
        self.set_font("Orb", "B", 8)
        self.set_text_color(*GREEN)
        self.set_xy(25, y + 2)
        self.cell(0, 5, title)
        self.set_font("Spc", "", 8)
        self.set_text_color(*WHITE)
        for i, ln in enumerate(lines):
            self.set_xy(25, y + 9 + i * 5)
            self.cell(160, 5, ln)
        self.set_y(y + h + 3)

    def table_row(self, c1, c2, header=False):
        y = self.get_y()
        if y > 272:
            self.new_page(); self.set_y(20); y = 20
        if header:
            self.set_fill_color(40, 0, 0)
            self.set_font("Orb", "B", 7)
            self.set_text_color(*RED)
        else:
            self.set_fill_color(18, 18, 18)
            self.set_font("Spc", "", 8)
            self.set_text_color(*WHITE)
        self.set_x(20)
        self.cell(65, 7, f" {c1}", border=0, fill=True)
        self.set_text_color(*(GREY if not header else RED))
        self.cell(105, 7, f" {c2}", border=0, fill=True, ln=True)
        self.set_draw_color(40, 0, 0)
        self.line(20, self.get_y(), 190, self.get_y())


# ══════════════════════════════════════════════════════════════
# PAGE DE COUVERTURE
# ══════════════════════════════════════════════════════════════
def build_cover(pdf):
    pdf.new_page()

    # Cadre
    pdf.set_draw_color(*RED_DARK)
    pdf.set_line_width(0.5)
    pdf.rect(10, 10, 190, 277, "D")
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.2)
    pdf.rect(12, 12, 186, 273, "D")

    pdf.scanner(30, pos=0.5, width=160)

    # Titre principal
    pdf.set_font("Orb", "B", 44)
    pdf.set_text_color(*RED)
    pdf.set_xy(0, 46)
    pdf.cell(210, 20, "KYRONEX", align="C", ln=True)

    pdf.set_font("Orb", "", 7)
    pdf.set_text_color(*GREY)
    pdf.set_xy(0, 68)
    pdf.cell(210, 6, "KINETIC YIELDING RESPONSIVE ONBOARD NEURAL EXPERT", align="C", ln=True)

    # Ligne déco
    pdf.set_fill_color(*RED_DIM)
    pdf.rect(40, 80, 130, 0.5, "F")

    pdf.set_font("Orb", "B", 16)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(0, 90)
    pdf.cell(210, 11, "MODE D'EMPLOI", align="C", ln=True)

    pdf.set_font("Spc", "", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(210, 6, "Intelligence Artificielle Vocale Multilingue — Embarquée", align="C", ln=True)
    pdf.cell(210, 6, "NVIDIA Jetson Orin Nano Super 8 Go", align="C", ln=True)

    # Scanners deco
    for i, yp in enumerate([128, 133, 138]):
        pdf.scanner(yp, pos=(i * 0.28 + 0.08) % 1.0, width=140)

    # Tableau de bord
    dy = 155
    pdf.set_fill_color(18, 18, 18)
    pdf.rect(35, dy, 140, 55, "F")
    pdf.set_draw_color(50, 0, 0)
    pdf.rect(35, dy, 140, 55, "D")

    indicators = [
        ("LLM GPU",    GREEN),
        ("TTS CUDA",   GREEN),
        ("STT CUDA",   GREEN),
        ("VISION",     GREEN),
        ("VIGILANCE",  AMBER),
        ("MULTILINGUE",GREEN),
    ]
    for i, (label, color) in enumerate(indicators):
        col = i % 3
        row = i // 3
        ix = 42 + col * 46
        iy = dy + 8 + row * 22
        pdf.set_fill_color(*color)
        pdf.rect(ix, iy, 3, 3, "F")
        pdf.set_font("Spc", "", 6)
        pdf.set_text_color(*GREY)
        pdf.set_xy(ix + 5, iy - 1)
        pdf.cell(40, 5, label)

    pdf.set_font("Orb", "", 9)
    pdf.set_text_color(*RED_DIM)
    pdf.set_xy(0, 224)
    pdf.cell(210, 7, "Version 4.0  —  20 février 2026", align="C", ln=True)

    pdf.scanner(248, pos=0.7, width=160)

    pdf.set_font("Orb", "", 8)
    pdf.set_text_color(*RED_DIM)
    pdf.set_xy(0, 260)
    pdf.cell(210, 6, "CRÉÉ PAR MANIX — EMMANUEL GELINNE", align="C", ln=True)
    pdf.set_font("Spc", "", 7)
    pdf.set_text_color(*GREY)
    pdf.cell(210, 5, "on3egs@icloud.com  |  KITT Franco-Belge", align="C", ln=True)


# ══════════════════════════════════════════════════════════════
# TABLE DES MATIÈRES
# ══════════════════════════════════════════════════════════════
def build_toc(pdf):
    pdf.new_page()
    pdf.set_y(15)
    pdf.set_font("Orb", "B", 14)
    pdf.set_text_color(*RED)
    pdf.cell(0, 11, "   TABLE DES MATIÈRES", ln=True)
    pdf.scanner(pdf.get_y(), pos=0.5, width=180)
    pdf.ln(10)

    chapters = [
        ("Présentation",           "Qu'est-ce que KYRONEX ?"),
        ("Démarrage",              "Lancer le système"),
        ("Interface Web",          "Tableau de bord"),
        ("Identification",         "Prénom et langue persistants"),
        ("Chat vocal",             "Parler à KYRONEX"),
        ("Vision par caméra",      "Voir avec YOLOX-S"),
        ("Mode Vigilance",         "Surveillance caméra automatique"),
        ("Sons d'ambiance",        "Ambiance MOTHER / AMB"),
        ("Messages proactifs",     "Alertes et salutations auto"),
        ("Statistiques connexions","Panneau IPs et sessions"),
        ("Architecture technique", "Sous le capot"),
        ("Dépannage",              "Diagnostic et solutions"),
        ("Crédits et licence",     "Informations légales"),
    ]
    for i, (title, sub) in enumerate(chapters):
        y = pdf.get_y()
        pdf.set_font("Orb", "B", 10)
        pdf.set_text_color(*RED)
        pdf.set_xy(20, y)
        pdf.cell(12, 8, f"{i + 1}.")
        pdf.set_font("Orb", "", 10)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(32, y)
        pdf.cell(105, 8, title)
        pdf.set_font("Spc", "", 7)
        pdf.set_text_color(*GREY)
        pdf.set_xy(32, y + 7)
        pdf.cell(105, 5, sub)
        pdf.set_text_color(38, 38, 38)
        pdf.set_xy(142, y)
        pdf.cell(38, 8, "." * 20, align="R")
        pdf.set_y(y + 14)


# ══════════════════════════════════════════════════════════════
# CONTENU
# ══════════════════════════════════════════════════════════════
def build_content(pdf):

    # ── 1. PRÉSENTATION ───────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("PRÉSENTATION")

    pdf.body(
        "KYRONEX (Kinetic Yielding Responsive Onboard Neural EXpert) est une "
        "intelligence artificielle vocale embarquée au style rétro-futuriste, "
        "conçue par Manix (Emmanuel Gelinne). Elle tourne entièrement en local "
        "sur un NVIDIA Jetson Orin Nano Super — sans connexion cloud obligatoire."
    )
    pdf.body(
        "KYRONEX répond dans cinq langues (français, anglais, allemand, "
        "italien, portugais), reconnaît les utilisateurs par leur prénom, "
        "mémorise leur langue préférée, surveille son environnement via une "
        "caméra et envoie des alertes proactives. L'interface web adopte une "
        "esthétique MU-TH-UR 6000 / Knight Rider — fond noir, rouge, vert phosphore."
    )

    pdf.sub_title("Capacités principales")
    pdf.bullets([
        "LLM GPU : Qwen 2.5 3B (Q5_K_M) via llama.cpp — ~1 400 ms",
        "STT GPU : faster-whisper base CUDA (CTranslate2) — ~221 ms",
        "TTS GPU : Piper fr_FR-tom CUDA — ~265 ms (6x plus rapide que CPU)",
        "Vision : YOLOX-S ONNX (Apache 2.0, Megvii) — ~580 ms, 80 classes",
        "Mode Vigilance : surveillance caméra automatique + alertes temps réel",
        "Multilingue : fr/en/de/it/pt — langue mémorisée par utilisateur",
        "Identification : prénom demandé à la 1re connexion, mémorisé (MAC)",
        "Statistiques : connexions actives, 24 h, 7 jours avec liste IPs",
        "Sons MOTHER / Alien : ambiance oscillateur + double bip fin de message",
        "Orbe 3D réactif : 130 points Fibonacci réactifs à la voix",
        "Messages proactifs : salutations horaires, alertes température/RAM",
        "Mémoire persistante : faits utilisateur entre sessions",
        "Recherche web : DuckDuckGo sur mots-clés actualité/météo/prix",
        "Latence totale : ~2,3 s (parole → réponse audio complète)",
    ])

    pdf.info_box("FONCTIONNEMENT 100 % HORS LIGNE",
        "Aucune donnée n'est envoyée vers un serveur distant.\n"
        "LLM, STT et TTS tournent sur le GPU du Jetson.\n"
        "La recherche web (DuckDuckGo) est optionnelle et\n"
        "ne se déclenche que sur les mots-clés d'actualité.")

    # ── 2. DÉMARRAGE ──────────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("DÉMARRAGE")

    pdf.sub_title("Lancement normal")
    pdf.code(
        "cd /home/kitt/kitt-ai\n"
        "bash start_kyronex.sh"
    )
    pdf.body(
        "Le script démarre automatiquement :\n"
        "  1. llama-server sur le port 8080 (modèle LLM sur GPU)\n"
        "  2. kyronex_server.py sur le port 3000 (interface web HTTPS)\n"
        "  3. Boucle de surveillance : redémarre tout si l'un des deux plante"
    )

    pdf.sub_title("Service systemd (démarrage automatique au boot)")
    pdf.code(
        "# Activer le démarrage automatique :\n"
        "sudo systemctl enable kitt-kyronex.service\n"
        "\n"
        "# Démarrer / arrêter manuellement :\n"
        "sudo systemctl start  kitt-kyronex.service\n"
        "sudo systemctl stop   kitt-kyronex.service\n"
        "\n"
        "# Voir les logs en direct :\n"
        "journalctl -u kitt-kyronex -f"
    )

    pdf.sub_title("Mode tunnel (accès distant)")
    pdf.code("TUNNEL=1 bash start_kyronex.sh")
    pdf.body(
        "Active un tunnel Cloudflare. L'URL publique est affichée dans "
        "/tmp/cloudflared.log. Un mot de passe est requis "
        "(défaut : 1982, variable KYRONEX_PASSWORD)."
    )

    pdf.sub_title("Accès à l'interface")
    pdf.info_box("ADRESSES D'ACCÈS",
        "Depuis le Jetson  :  https://localhost:3000\n"
        "Depuis le réseau  :  https://192.168.1.4:3000\n"
        "\n"
        "Le certificat HTTPS est auto-signé — acceptez\n"
        "l'exception de sécurité dans votre navigateur.\n"
        "Chrome : cliquer 'Paramètres avancés > Continuer'.")

    pdf.sub_title("Indicateurs de démarrage réussi")
    pdf.code(
        "[OK] Whisper pret (CUDA float16)\n"
        "[OK] TTS fr GPU ready (265ms)\n"
        "[OK] Serveur HTTPS actif : https://localhost:3000"
    )
    pdf.body("La barre rouge en bas de l'interface affichera << EN LIGNE >>.")

    # ── 3. INTERFACE WEB ──────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("INTERFACE WEB")

    pdf.body(
        "L'interface adopte une esthétique rétro-futuriste : fond noir avec "
        "grille verte horizontale et rouge verticale, scanner KR descendant, "
        "orbe 3D réactif, terminal MU-TH-UR 6000 en bas à droite."
    )

    pdf.sub_title("Header — boutons de contrôle")
    pdf.table_row("Bouton", "Rôle", header=True)
    pdf.table_row("VIG (rouge)",   "Mode Vigilance — surveillance caméra auto")
    pdf.table_row("AMB (vert)",    "Sons d'ambiance MOTHER — drone 60 Hz + harmoniques")
    pdf.ln(3)

    pdf.sub_title("Zone d'entrée — boutons de chat")
    pdf.table_row("Bouton", "Rôle", header=True)
    pdf.table_row("MIC (rouge)",   "Push-to-talk — clic pour parler, clic pour arrêter")
    pdf.table_row("AUTO (vert)",   "Écoute continue VAD — détecte la parole automatiquement")
    pdf.table_row("WAKE (violet)", "Wake word -- reagit uniquement a KYRONEX")
    pdf.table_row("CAM (bleu)",    "Capture caméra + analyse YOLOX-S")
    pdf.table_row("ENVOYER",       "Envoi du message texte saisi")
    pdf.ln(3)

    pdf.sub_title("Panneau de connexions (gauche)")
    pdf.body(
        "Panneau translucide affiché à gauche (sur écrans > 700 px). "
        "Mis à jour toutes les 20 secondes :"
    )
    pdf.bullets([
        "EN LIGNE : nombre de sessions actives (heartbeat 30 s)",
        "24 H : nombre de connexions uniques sur les dernières 24 heures",
        "7 J : nombre de connexions uniques sur les 7 derniers jours",
        "IPs : liste des adresses IP des sessions actives",
    ])

    pdf.sub_title("Terminal MU-TH-UR 6000 (bas droite)")
    pdf.body(
        "Panneau de diagnostic style Alien — affiché sur grands écrans. "
        "Mis à jour toutes les secondes avec :"
    )
    pdf.bullets([
        "CORE STATUS : NOMINAL / WARNING selon RAM/température",
        "TEMP : température du SoC (°C)",
        "RAM : mémoire disponible (Mo)",
        "SESSIONS : nombre de connexions actives",
    ])

    pdf.sub_title("Voicebox et orbe")
    pdf.body(
        "La voicebox (barres verticales rouges animées) réagit à l'audio "
        "TTS via l'AnalyserNode Web Audio. L'orbe 3D (sphère Fibonacci "
        "130 points) est visible en arrière-plan et réagit également à "
        "l'amplitude audio."
    )

    # ── 4. IDENTIFICATION ─────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("IDENTIFICATION — PRÉNOM ET LANGUE PERSISTANTS")

    pdf.body(
        "À la première connexion depuis un appareil, KYRONEX affiche "
        "une fenêtre d'identification style MU-TH-UR 6000. Elle demande "
        "votre prénom et votre langue préférée. Ces informations sont "
        "mémorisées de façon permanente — elles survivent aux redémarrages."
    )

    pdf.sub_title("Fenêtre d'identification (1re connexion)")
    pdf.bullets([
        "Fond noir, titre vert phosphore MU-TH-UR 6000",
        "Saisie du prénom : champ texte (Entrée ou bouton CONFIRMER)",
        "Sélection de la langue : boutons FR / EN / DE / IT",
        "Mémorisation par adresse MAC — identifie l'appareil",
    ])

    pdf.sub_title("Comportement aux connexions suivantes")
    pdf.bullets([
        "KYRONEX vous salue par votre prenom : Bonsoir Manix.",
        "La langue choisie est verrouillée — KYRONEX ne change jamais de langue",
        "Même après un redémarrage complet du Jetson",
        "Même si vous lui parlez dans une autre langue",
    ])

    pdf.sub_title("Changer la langue")
    pdf.body(
        "Depuis l'interface web, les boutons FR / EN / DE / IT "
        "sont visibles dans la fenêtre d'identification (avant confirmation) "
        "ou via le panneau de configuration. La langue est envoyée au "
        "serveur via POST /api/set-lang."
    )

    pdf.info_box("RÈGLE ABSOLUE DE LANGUE",
        "Une fois la langue choisie, KYRONEX répond UNIQUEMENT\n"
        "dans cette langue, quelle que soit la langue de l'interlocuteur.\n"
        "Si vous choisissez l'anglais, il répond en anglais même\n"
        "si vous lui parlez en français.")

    # ── 5. CHAT VOCAL ─────────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("CHAT VOCAL")

    pdf.sub_title("Mode Push-to-Talk (MIC)")
    pdf.body(
        "Cliquez sur le bouton microphone (rond rouge). Il pulse "
        "pendant l'enregistrement. Parlez, puis cliquez à nouveau "
        "pour envoyer. La transcription est automatique (Whisper GPU)."
    )

    pdf.sub_title("Mode Auto-écoute (AUTO / VAD)")
    pdf.body(
        "Cliquez sur AUTO. KYRONEX écoute en permanence et détecte "
        "automatiquement la parole. Paramètres :"
    )
    pdf.bullets([
        "Seuil VAD : 0.008 (sensible, capte les voix douces)",
        "Durée silence : 800 ms (fin de phrase rapide)",
        "Parole minimum : 500 ms (évite les bruits courts)",
        "Anti-écho : sourdine pendant TTS + 1,5 s après",
    ])

    pdf.sub_title("Mode Wake Word (WAKE)")
    pdf.body(
        "Cliquez sur WAKE (violet). KYRONEX écoute passivement en continu "
        "et ne reagit que si vous prononcez KYRONEX (ou approximation). "
        "Après détection :"
    )
    pdf.bullets([
        "Fenêtre de 6 secondes pour poser votre question",
        "Ou dites KYRONEX seul -> attente de la commande",
        "Utile pour utilisation mains-libres",
    ])

    pdf.sub_title("Sons d'indication (style MOTHER/Alien)")
    pdf.bullets([
        "Pendant la réflexion LLM : sons sawtooth/square graves irréguliers",
        "Fin de message KYRONEX : double bip 523 Hz + 659 Hz (square, Q=6)",
        "Alerte vigilance : 4 bips 880/660/880/440 Hz (square, rapide)",
    ])

    pdf.sub_title("Exemples de phrases")
    pdf.bullets([
        "Bonjour, comment vas-tu ? (exemple)",
        "KYRONEX, quelle est la meteo a Paris ?",
        "What do you see? (en anglais si langue EN choisie)",
        "Regarde devant toi. -> declenche automatiquement la camera",
        "Qu'est-ce que je porte ? -> analyse vision + couleurs vetements",
    ])

    pdf.info_box("RECHERCHE WEB AUTOMATIQUE",
        "Sur les mots-clés : actualité, météo, prix, définition,\n"
        "aujourd'hui, bitcoin, etc. — KYRONEX consulte DuckDuckGo\n"
        "et injecte les résultats dans sa réponse.\n"
        "Entités privées (Manix, etc.) sont exclues du web search.")

    # ── 6. VISION PAR CAMÉRA ──────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("VISION PAR CAMÉRA")

    pdf.body(
        "KYRONEX peut voir grâce à la webcam connectée. Il utilise "
        "YOLOX-S (Apache 2.0, Megvii) via cv2.dnn pour détecter "
        "les objets et analyser les couleurs. "
        "Le daemon vision tourne en mémoire — modèle chargé une seule fois."
    )

    pdf.table_row("Paramètre",        "Valeur", header=True)
    pdf.table_row("Modèle",           "YOLOX-S ONNX (35 Mo)")
    pdf.table_row("Temps d'inférence","~580 ms")
    pdf.table_row("Classes",          "80 (COCO) — personnes, animaux, objets")
    pdf.table_row("Seuil détection",  "0.35 (réduit les faux positifs)")
    pdf.table_row("Résolution",       "640 × 480 (letterbox 640 × 640)")
    pdf.ln(3)

    pdf.sub_title("Utilisation manuelle")
    pdf.bullets([
        "Cliquer sur le bouton CAM (icône appareil photo)",
        "Le bouton devient bleu pendant la capture (~600 ms)",
        "KYRONEX décrit ce qu'il voit en langage naturel",
        "Tapez une question avant de cliquer pour contextualiser",
    ])

    pdf.sub_title("Déclenchement automatique par mots-clés")
    pdf.body("Ces mots dans votre message activent automatiquement la caméra :")
    pdf.code(
        "regarde-moi, devant toi, caméra, qu'est-ce que tu vois,\n"
        "comment je suis habillé, de quelle couleur, tu me vois,\n"
        "décris-moi, analyse-moi, scanne"
    )
    pdf.body("Cooldown : 30 s minimum entre deux captures auto.")

    pdf.sub_title("Capacités d'analyse")
    pdf.bullets([
        "Détection personnes, animaux, véhicules, objets du quotidien",
        "Couleurs dominantes de chaque objet (rouge, bleu, vert…)",
        "Pour les personnes : couleur haut du corps + bas du corps",
        "Description transmise au LLM pour une réponse naturelle",
    ])

    # ── 7. MODE VIGILANCE ─────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("MODE VIGILANCE")

    pdf.body(
        "Le Mode Vigilance transforme KYRONEX en gardien silencieux. "
        "Lorsqu'il est activé, KYRONEX surveille la caméra toutes les "
        "20 secondes et envoie une alerte si une présence est détectée "
        "dans des conditions suspectes."
    )

    pdf.sub_title("Activer / désactiver")
    pdf.bullets([
        "Cliquer sur le bouton VIG (rouge, en haut à droite du header)",
        "VIG rouge clignotant = surveillance active",
        "VIG sombre = surveillance désactivée",
        "L'état est synchronisé avec le serveur via POST /api/vigilance",
    ])

    pdf.sub_title("Conditions d'alerte")
    pdf.table_row("Situation",                             "Message envoyé", header=True)
    pdf.table_row("0 → 1 personne détectée,\nterminale inactif > 5 min",
                  "Présence détectée sur terminal inactif.\nIdentité non confirmée.")
    pdf.table_row("1 → 2+ personnes détectées",
                  "Présence non identifiée dans la zone.")
    pdf.ln(3)

    pdf.sub_title("Affichage de l'alerte")
    pdf.bullets([
        "Message rouge dans le chat avec étiquette [ VIGILANCE ]",
        "Animation flash rouge (3 cycles)",
        "Son d'alarme : 4 bips square 880/660/880/440 Hz",
        "Synthèse vocale du message (TTS GPU)",
    ])

    pdf.green_box("CONSEIL D'UTILISATION",
        "Activez VIG avant de quitter votre poste.\n"
        "KYRONEX vous alertera si quelqu'un s'approche\n"
        "du terminal pendant votre absence (> 5 min inactif).\n"
        "Nécessite une webcam connectée à /dev/video0.")

    pdf.sub_title("Exigences techniques")
    pdf.bullets([
        "Webcam disponible sur /dev/video0",
        "Aucun autre service ne doit utiliser la caméra (kitt-recognition OFF)",
        "KYRONEX doit avoir au moins 1 client WebSocket connecté",
        "VISION_SCRIPT doit exister (/home/kitt/kitt-ai/vision.py)",
    ])

    # ── 8. SONS D'AMBIANCE ────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("SONS D'AMBIANCE — BOUTON AMB")

    pdf.body(
        "Le bouton AMB (vert, header) active un son d'ambiance continu "
        "généré par la Web Audio API — sans téléchargement de fichier audio. "
        "Inspiré des sons de MÈRE (MU-TH-UR 6000) dans Alien (1979)."
    )

    pdf.sub_title("Composition du son d'ambiance")
    pdf.bullets([
        "Drone principal : oscillateur 60 Hz (sawtooth), gain 0.018",
        "Harmonique : oscillateur 120 Hz (triangle), gain 0.010",
        "Bruit filtré : buffer noise + filtre passe-bas 200 Hz (BiquadFilter)",
        "LFO : modulation lente 0.08 Hz sur le gain principal",
        "Fondu d'entrée 2,5 s / sortie 1,5 s",
    ])

    pdf.sub_title("Sons de réflexion LLM (style MOTHER/Alien)")
    pdf.body(
        "Pendant que KYRONEX réfléchit (appel LLM), des sons courts "
        "irréguliers sont joués toutes les 600–1500 ms :"
    )
    pdf.bullets([
        "19 sons prédéfinis : sawtooth + square, graves 55–1319 Hz",
        "Filtre résonant (BiquadFilter, Q = 2–12) pour le timbre MOTHER",
        "Attaque rapide 0.08 s / extinction rapide",
        "S'arrêtent dès que la réponse commence à s'afficher",
    ])

    pdf.sub_title("Son de fin de message")
    pdf.body(
        "Après chaque réponse complète de KYRONEX (audio terminé) :"
    )
    pdf.code("Double bip : 523 Hz + 659 Hz (square, Q=6) — 0.12 s chacun")

    # ── 9. MESSAGES PROACTIFS ─────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("MESSAGES PROACTIFS")

    pdf.body(
        "KYRONEX peut envoyer des messages spontanés sans que vous le "
        "demandiez, via le WebSocket proactif (/api/proactive/ws). "
        "Ces messages apparaissent en orange italique dans le chat."
    )

    pdf.sub_title("Salutations horaires")
    pdf.table_row("Heure", "Message", header=True)
    pdf.table_row("6 h 00",  "Mes systèmes sont en ligne. Une nouvelle journée commence.")
    pdf.table_row("7 h 00",  "Tous mes capteurs sont opérationnels. Prêt pour la mission.")
    pdf.table_row("12 h 00", "Peut-être une pause s'impose ? Mes circuits ne connaissent pas la faim.")
    pdf.table_row("18 h 00", "Bonsoir. La journée a été productive, j'espère.")
    pdf.table_row("22 h 00", "Je reste vigilant, mais vous devriez envisager du repos.")
    pdf.table_row("0 h 00",  "Mon scanner veille. Bonne nuit, Manix.")
    pdf.ln(3)

    pdf.sub_title("Alertes automatiques")
    pdf.table_row("Déclencheur",          "Alerte envoyée", header=True)
    pdf.table_row("Température > 85 °C",  "ALERTE CRITIQUE — surchauffe")
    pdf.table_row("Température > 75 °C",  "Température élevée — surveillance")
    pdf.table_row("Température > 70 °C",  "Information température (max 1/2 min)")
    pdf.table_row("RAM disponible < 500 Mo", "RAM critique — ralentissement possible")
    pdf.ln(3)

    pdf.body(
        "Les alertes Vigilance (type vigilance_alert) sont affichées "
        "en rouge avec le son d'alarme, distinctes des messages proactifs normaux."
    )

    # ── 10. STATISTIQUES CONNEXIONS ───────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("STATISTIQUES CONNEXIONS")

    pdf.body(
        "KYRONEX enregistre chaque connexion dans conn_stats.json "
        "(roulement 2 000 entrées). Le panneau gauche de l'interface "
        "affiche les statistiques en temps réel."
    )

    pdf.sub_title("Panneau gauche (connexions)")
    pdf.bullets([
        "EN LIGNE : sessions actives (heartbeat /api/ping toutes les 30 s)",
        "24 H : connexions uniques sur les dernières 24 heures",
        "7 J : connexions uniques sur les 7 derniers jours",
        "IPs : liste des IP actives (max 8 affichées)",
        "Rafraîchissement automatique toutes les 20 s",
    ])

    pdf.sub_title("API disponibles")
    pdf.table_row("Endpoint",         "Description", header=True)
    pdf.table_row("GET  /api/stats",  "Statistiques JSON (current/24h/7d/sessions)")
    pdf.table_row("POST /api/ping",   "Heartbeat session (renouvelle la présence)")
    pdf.table_row("POST /api/set-lang","Changer la langue persistante")
    pdf.table_row("GET  /api/whoami", "Infos session courante (nom, langue, MAC)")
    pdf.ln(3)

    pdf.sub_title("Fichiers de données")
    pdf.bullets([
        "users.json : { MAC → {name, lang} } — prénom + langue par appareil",
        "conn_stats.json : historique des connexions (IP, MAC, nom, heure)",
    ])

    # ── 11. ARCHITECTURE TECHNIQUE ────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("ARCHITECTURE TECHNIQUE")

    pdf.sub_title("Vue d'ensemble du flux")
    pdf.code(
        "Navigateur (port 3000 HTTPS)\n"
        "  |\n"
        "  +-- Texte/Voix  --> /api/chat/stream  --> LLM  (~1400ms)\n"
        "  +-- Voix        --> /api/stt           --> Whisper GPU (~221ms)\n"
        "  +-- Vision      --> /api/vision        --> YOLOX-S (~580ms)\n"
        "  +-- Vigilance   --> /api/vigilance     --> toggle mode\n"
        "  |\n"
        "  +-- Audio       <-- MultilingualTTS CUDA + SoX (~265ms fr)\n"
        "  +-- Proactif    <-- WebSocket /api/proactive/ws\n"
        "  +-- Monitor     <-- WebSocket /api/monitor/ws\n"
        "  |\n"
        "  +-- llama-server port 8080 (GPU CUDA, API OpenAI-compatible)"
    )

    pdf.ln(2)
    pdf.sub_title("Composants logiciels")
    pdf.table_row("Composant",          "Détail", header=True)
    pdf.table_row("Serveur",            "Python aiohttp, port 3000 HTTPS self-signed")
    pdf.table_row("LLM",                "Qwen 2.5 3B (Q5_K_M), llama.cpp, SM 87")
    pdf.table_row("STT",                "faster-whisper base, CTranslate2 CUDA float16")
    pdf.table_row("TTS fr",             "Piper fr_FR-tom-medium, ORT CUDA (permanent)")
    pdf.table_row("TTS autres",         "Piper en/de/it/pt, CPU, LRU cache x1")
    pdf.table_row("Vision",             "YOLOX-S ONNX via cv2.dnn, daemon persistant")
    pdf.table_row("Détection langue",   "langdetect (~3 ms, seed=0)")
    pdf.table_row("GPU",                "NVIDIA Orin Nano Super, CUDA 12.6, SM 87")
    pdf.table_row("ORT GPU",            "onnxruntime-gpu 1.23.0 (compilé pour Tegra)")
    pdf.table_row("CTranslate2",        "4.5.0 avec CUDA (compilé depuis sources)")
    pdf.ln(3)

    pdf.sub_title("Paramètres llama-server")
    pdf.table_row("Paramètre",          "Valeur", header=True)
    pdf.table_row("--n-gpu-layers",     "99 (tout sur GPU)")
    pdf.table_row("--ctx-size",         "1024 (anti-OOM)")
    pdf.table_row("--batch-size",       "512")
    pdf.table_row("--flash-attn",       "on (Flash Attention)")
    pdf.table_row("--threads",          "4")
    pdf.ln(3)

    pdf.sub_title("Arborescence des fichiers clés")
    pdf.code(
        "kitt-ai/\n"
        "  kyronex_server.py     # Serveur principal\n"
        "  piper_gpu.py          # TTS GPU + MultilingualTTS\n"
        "  vision.py             # Vision YOLOX-S (daemon)\n"
        "  start_kyronex.sh      # Script démarrage + surveillance\n"
        "  generate_manual.py    # Ce générateur de PDF\n"
        "  static/index.html     # Interface web (PWA)\n"
        "  models/               # LLM .gguf + TTS .onnx + YOLOX .onnx\n"
        "  audio_cache/          # Cache audio temp. (nettoyé 5 min)\n"
        "  users.json            # Prénoms + langues par MAC\n"
        "  conn_stats.json       # Historique connexions (2000 max)\n"
        "  memory.json           # Mémoire persistante utilisateur\n"
        "  certs/                # Certificats HTTPS auto-signés\n"
        "  logs/                 # Journaux JSONL conversations\n"
        "  site/                 # Site web GitHub Pages"
    )

    # ── 12. DÉPANNAGE ─────────────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("DÉPANNAGE")

    pdf.sub_title("KYRONEX ne démarre pas")
    pdf.bullets([
        "Vérifier les paquets : ffmpeg, sox, libportaudio2",
        "Vérifier LD_LIBRARY_PATH dans start_kyronex.sh",
        "Consulter : journalctl -u kitt-kyronex -f",
        "Tester llama-server séparément : curl http://localhost:8080/health",
    ])

    pdf.sub_title("LLM HORS LIGNE dans l'interface")
    pdf.bullets([
        "llama-server charge le modèle (~14 s au boot — attendre)",
        "Vérifier : curl http://localhost:8080/health",
        "Le fichier .gguf est-il présent dans models/ ?",
        "Mémoire insuffisante ? Vérifier : free -m",
    ])

    pdf.sub_title("Le microphone ne fonctionne pas")
    pdf.bullets([
        "Autoriser l'accès micro dans le navigateur",
        "HTTPS requis pour le micro (sauf localhost)",
        "Vérifier les appareils audio : arecord -l",
    ])

    pdf.sub_title("La caméra ne fonctionne pas / Vigilance inactive")
    pdf.bullets([
        "Vérifier : ls /dev/video* (doit afficher video0)",
        "Tester : /usr/bin/python3 vision.py --test",
        "Un seul programme peut utiliser la caméra à la fois",
        "Arrêter kitt-recognition si actif : sudo systemctl stop kitt-recognition",
        "kitt-driver utilise aussi /dev/video0 — le stopper si nécessaire",
    ])

    pdf.sub_title("La voix TTS est lente ou absente")
    pdf.bullets([
        "Vérifier SoX : sox --version",
        "Vérifier le modèle TTS : ls models/*.onnx",
        "ORT GPU disponible ? Relancer le serveur et vérifier les logs",
        "Vérifier la sortie audio : aplay /usr/share/sounds/alsa/Front_Center.wav",
    ])

    pdf.sub_title("Surveiller la mémoire (anti-OOM)")
    pdf.code(
        "# RAM / VRAM en temps réel\n"
        "tegrastats | grep 'RAM'\n"
        "\n"
        "# Log VRAM KYRONEX\n"
        "tail -f /tmp/kitt_vram.log\n"
        "\n"
        "# Statut service\n"
        "systemctl status kitt-kyronex.service"
    )

    pdf.info_box("PROTECTION OOM",
        "ctx-size 1024 + flash-attn activés par défaut.\n"
        "Si crash OOM répété : baisser ctx-size à 512.\n"
        "Le service redémarre automatiquement en cas de crash\n"
        "(Restart=always, jusqu'à 5 fois par 5 minutes).")

    # ── 13. CRÉDITS ET LICENCE ────────────────────────────────
    pdf.new_page(); pdf.set_y(15)
    pdf.section_title("CRÉDITS ET LICENCE")

    pdf.set_font("Orb", "B", 13)
    pdf.set_text_color(*RED)
    pdf.set_x(20)
    pdf.cell(170, 9, "CRÉATEUR", ln=True, align="C")

    pdf.set_font("Orb", "B", 20)
    pdf.set_text_color(*WHITE)
    pdf.set_x(20)
    pdf.cell(170, 13, "Manix", ln=True, align="C")

    pdf.set_font("Spc", "", 9)
    pdf.set_text_color(*GREY)
    pdf.set_x(20)
    pdf.cell(170, 6, "(Emmanuel Gelinne)", ln=True, align="C")
    pdf.ln(2)

    pdf.scanner(pdf.get_y(), pos=0.4, width=140)
    pdf.ln(7)

    pdf.sub_title("Contact")
    pdf.table_row("E-mail",    "on3egs@icloud.com")
    pdf.table_row("Site web",  "https://on3egs.github.io/manix-kitt/")
    pdf.table_row("GitHub",    "https://github.com/on3egs")
    pdf.table_row("Groupe",    "KITT Franco-Belge (Facebook)")
    pdf.ln(4)

    pdf.sub_title("Licence")
    pdf.info_box("ELASTIC LICENSE 2.0 (ELv2)",
        "Copyright (c) 2026 Manix (Emmanuel Gelinne)\n"
        "\n"
        "Utilisation libre pour usage personnel et éducatif.\n"
        "\n"
        "INTERDIT sans accord écrit de l'auteur :\n"
        "  - Offrir ce logiciel comme service commercial hébergé\n"
        "  - Retirer ou modifier les notices de licence\n"
        "  - Créer des produits dérivés commerciaux\n"
        "\n"
        "L'auteur conserve tous les droits commerciaux.\n"
        "Fichier LICENSE inclus dans le projet.")

    pdf.ln(3)
    pdf.sub_title("Technologies libres utilisées")
    pdf.bullets([
        "NVIDIA Jetson Orin Nano Super — CUDA 12.6, SM 87 (EULA commercial OK)",
        "llama.cpp — MIT — inférence LLM GPU optimisée",
        "Qwen 2.5 3B Instruct — Apache 2.0 — modèle de langage",
        "Piper TTS — MIT — synthèse vocale neuronale multilingue",
        "faster-whisper / CTranslate2 — MIT — STT GPU",
        "onnxruntime-gpu 1.23.0 — MIT — inférence ONNX CUDA",
        "YOLOX-S (Megvii) — Apache 2.0 — détection d'objets",
        "OpenCV — Apache 2.0 — vision par ordinateur",
        "SoX — GPL-2.0 — effets audio (outil externe, pas de contamination)",
        "FFmpeg — LGPL/GPL — conversion audio (outil externe)",
        "Python aiohttp — Apache 2.0 — serveur web asynchrone",
        "langdetect — Apache 2.0 — détection de langue",
        "fpdf2 — LGPL — génération PDF",
    ])

    pdf.ln(2)
    pdf.set_font("Spc", "", 9)
    pdf.set_text_color(*GREY)
    pdf.set_x(20)
    pdf.multi_cell(170, 5,
        "La technologie au service de l'humain.\n"
        "— Manix"
    )

    pdf.ln(3)
    pdf.scanner(pdf.get_y(), pos=0.6, width=160)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    pdf = KyronexManual()
    pdf.set_auto_page_break(auto=True, margin=20)

    build_cover(pdf)
    build_toc(pdf)
    build_content(pdf)

    out = "/home/kitt/kitt-ai/KYRONEX_Mode_Emploi.pdf"
    pdf.output(out)
    pages = pdf.page_no()
    print(f"[OK] PDF généré : {out}  ({pages} pages)")


if __name__ == "__main__":
    main()
