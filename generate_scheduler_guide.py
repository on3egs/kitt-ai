#!/usr/bin/env python3
"""Génère le PDF guide du KITT Night Scheduler"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from pathlib import Path

OUT = Path("/home/kitt/kitt-ai/KITT_Scheduler_Guide.pdf")

# ── Couleurs KITT ────────────────────────────────────────────────
NOIR    = HexColor('#0a0a0a')
ROUGE   = HexColor('#cc2200')
ROUGE_C = HexColor('#ff3300')
VERT    = HexColor('#00aa33')
GRIS    = HexColor('#222222')
GRIS_C  = HexColor('#333333')
GRIS_L  = HexColor('#888888')
BLANC   = HexColor('#f0f0f0')
JAUNE   = HexColor('#ffaa00')
CYAN    = HexColor('#006688')

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm
)

styles = getSampleStyleSheet()

# ── Styles personnalisés ─────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

s_titre = S('titre',
    fontSize=28, textColor=ROUGE_C, alignment=TA_CENTER,
    fontName='Helvetica-Bold', spaceAfter=4)

s_sous = S('sous',
    fontSize=11, textColor=GRIS_L, alignment=TA_CENTER,
    fontName='Helvetica', spaceAfter=2)

s_h1 = S('h1',
    fontSize=16, textColor=ROUGE_C, fontName='Helvetica-Bold',
    spaceBefore=16, spaceAfter=6,
    borderPadding=(0,0,4,0))

s_h2 = S('h2',
    fontSize=12, textColor=JAUNE, fontName='Helvetica-Bold',
    spaceBefore=10, spaceAfter=4)

s_body = S('body',
    fontSize=10, textColor=BLANC, fontName='Helvetica',
    leading=16, spaceAfter=6)

s_code = S('code',
    fontSize=10, textColor=VERT, fontName='Courier',
    backColor=GRIS, leading=14, spaceAfter=2,
    leftIndent=12, rightIndent=12,
    borderPadding=6)

s_note = S('note',
    fontSize=9, textColor=JAUNE, fontName='Helvetica-Oblique',
    leading=13, leftIndent=8, spaceAfter=4)

s_warn = S('warn',
    fontSize=10, textColor=HexColor('#ff8800'), fontName='Helvetica-Bold',
    leading=14, spaceAfter=4)

s_center = S('center',
    fontSize=9, textColor=GRIS_L, alignment=TA_CENTER,
    fontName='Helvetica', spaceAfter=2)

def hr():
    return HRFlowable(width="100%", thickness=1, color=ROUGE, spaceAfter=8, spaceBefore=4)

def sp(h=8):
    return Spacer(1, h)

def code_block(*lines):
    items = []
    for l in lines:
        items.append(Paragraph(l, s_code))
    return items

def table_cmd(rows, col_w=None):
    col_w = col_w or [5*cm, 10.5*cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), GRIS_C),
        ('BACKGROUND',  (0,1), (-1,-1), HexColor('#111111')),
        ('TEXTCOLOR',   (0,0), (-1,0), JAUNE),
        ('TEXTCOLOR',   (0,1), (0,-1), VERT),
        ('TEXTCOLOR',   (1,1), (1,-1), BLANC),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME',    (0,1), (0,-1), 'Courier'),
        ('FONTNAME',    (1,1), (1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#111111'), HexColor('#181818')]),
        ('GRID',        (0,0), (-1,-1), 0.5, GRIS_C),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    return t

# ════════════════════════════════════════════════════════════════
story = []

# ── PAGE DE GARDE ────────────────────────────────────────────────
story += [
    sp(40),
    Paragraph("K I T T", s_titre),
    Paragraph("KNIGHT INDUSTRIES TWO THOUSAND", s_sous),
    sp(6),
    HRFlowable(width="80%", thickness=2, color=ROUGE, hAlign='CENTER'),
    sp(10),
    Paragraph("KITT Night Scheduler", S('t2', fontSize=20, textColor=BLANC,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=4)),
    Paragraph("Guide du débutant", S('t3', fontSize=14, textColor=GRIS_L,
        alignment=TA_CENTER, fontName='Helvetica', spaceAfter=2)),
    sp(6),
    HRFlowable(width="80%", thickness=1, color=GRIS_C, hAlign='CENTER'),
    sp(30),
    Paragraph("Claude Code améliore ta page web automatiquement pendant que tu dors.", S('tag',
        fontSize=12, textColor=JAUNE, alignment=TA_CENTER,
        fontName='Helvetica-Oblique', spaceAfter=4)),
    sp(80),
    Paragraph("by Manix — KYRONEX A.I.", s_center),
    Paragraph("Jetson Orin Nano Super 8GB", s_center),
    PageBreak()
]

# ── SECTION 1 : C'est quoi ? ─────────────────────────────────────
story += [
    Paragraph("1. C'est quoi le Kitt Night Scheduler ?", s_h1),
    hr(),
    Paragraph(
        "Le Kitt Night Scheduler est un programme qui demande à <b>Claude Code</b> "
        "(une IA d'Anthropic) d'améliorer ta page web <b>automatiquement</b>, "
        "pendant que tu dors ou que tu fais autre chose.",
        s_body),
    Paragraph(
        "Tu programmes des <b>fenêtres horaires</b> (ex: de 22h00 à 06h00), "
        "et Claude travaille tout seul dans ces créneaux. "
        "Chaque version améliorée est <b>sauvegardée</b> pour que tu puisses "
        "comparer et choisir celle que tu préfères.",
        s_body),
    sp(),
    Paragraph("Ce dont tu as besoin :", s_h2),
    Paragraph("• Le Jetson allumé (pas besoin de rester devant)", s_body),
    Paragraph("• Claude Code installé (c'est déjà fait !)", s_body),
    Paragraph("• Le fichier <font color='#00aa33'>kitt_scheduler.py</font> dans "
              "<font color='#00aa33'>/home/kitt/kitt-ai/</font>", s_body),
    sp(),
]

# ── SECTION 2 : Lancer Claude ───────────────────────────────────
story += [
    Paragraph("2. Comment lancer Claude Code ?", s_h1),
    hr(),
    Paragraph(
        "Claude Code est la commande <b>claude</b>. Elle est déjà installée sur le Jetson. "
        "Le Kitt Scheduler l'utilise automatiquement — tu n'as pas besoin de "
        "la lancer toi-même.",
        s_body),
    sp(4),
    Paragraph("Vérifier que Claude est bien là :", s_h2),
    *code_block("claude --version"),
    Paragraph(
        "Si tu vois un numéro de version (ex: 2.1.51), c'est bon. "
        "Si tu vois une erreur, relis la section Installation.",
        s_note),
    sp(4),
    Paragraph("Le scheduler utilise Claude avec ces options :", s_h2),
    *code_block(
        "claude --dangerously-skip-permissions --print",
        "       \"Ta demande ici...\""),
    Paragraph(
        "<b>--dangerously-skip-permissions</b> : Claude accepte tout sans demander "
        "à appuyer sur Y. C'est ce qui permet le travail automatique la nuit.",
        s_note),
    Paragraph(
        "<b>--print</b> : mode non-interactif, une seule question/réponse.",
        s_note),
    sp(),
]

# ── SECTION 3 : Démarrage rapide ────────────────────────────────
story += [
    Paragraph("3. Démarrage en 3 étapes", s_h1),
    hr(),

    Paragraph("Étape 1 — Ouvrir le menu", s_h2),
    *code_block("kittsched"),
    Paragraph("(Si ça ne marche pas : source ~/.bashrc  puis  kittsched)", s_note),
    sp(6),

    Paragraph("Étape 2 — Choisir dans le menu", s_h2),
    table_cmd([
        ['Option du menu', 'Ce que ça fait'],
        ['Ma tache —\nDemander qqch', "Tu écris ta propre demande à Claude\n(comme un message, dans nano)"],
        ['Ameliorations auto\nMAINTENANT', "Lance des améliorations prédéfinies\nimmédiatement (tu choisis combien)"],
        ['Ajouter une fenetre\nhoraire', "Programme une session automatique\nà une heure précise"],
        ['Planificateur',      "Démarre/arrête le daemon\n(tourne en fond même terminal fermé)"],
    ], col_w=[4.5*cm, 11*cm]),
    sp(6),

    Paragraph("Étape 3 — Fermer le terminal et aller dormir", s_h2),
    Paragraph(
        "Le programme continue à tourner même si tu fermes le terminal. "
        "Le matin, tu retrouves toutes les versions créées.",
        s_body),
    sp(),
]

# ── SECTION 4 : Ma tâche ────────────────────────────────────────
story += [
    PageBreak(),
    Paragraph("4. Donner une tâche personnalisée à Claude", s_h1),
    hr(),
    Paragraph(
        "C'est la fonction la plus puissante. Tu peux demander à Claude "
        "<b>n'importe quoi</b>, exactement comme tu lui parles ici dans ce chat.",
        s_body),
    sp(4),
    Paragraph("Comment ça marche :", s_h2),
    Paragraph("1. Lance le menu : <font color='#00aa33'>kittsched</font>", s_body),
    Paragraph("2. Choisis <b>Ma tache</b>", s_body),
    Paragraph("3. L'éditeur <b>nano</b> s'ouvre — écris ta demande", s_body),
    Paragraph("4. Appuie sur <b>Ctrl+X</b> puis <b>Y</b> puis <b>Entrée</b> pour sauvegarder", s_body),
    Paragraph("5. Choisis : <b>maintenant</b> ou <b>programmer la nuit</b>", s_body),
    sp(6),
    Paragraph("Exemples de tâches que tu peux écrire dans nano :", s_h2),
    *code_block(
        "Ajoute un bouton plein écran dans le header de",
        "/home/kitt/kitt-ai/static/index.html.",
        "Le bouton doit être discret, en bas à droite.",
        ""),
    sp(4),
    *code_block(
        "Améliore les animations de la sphère 3D dans",
        "/home/kitt/kitt-ai/static/index.html :",
        "je voudrais qu'elle tourne plus vite quand KITT parle",
        "et très lentement quand il écoute.",
        ""),
    sp(4),
    Paragraph(
        "Conseil : Sois précis sur le fichier à modifier et ce que tu attends. "
        "Plus ta demande est claire, meilleur sera le résultat.",
        s_note),
    sp(),
]

# ── SECTION 5 : Fenêtres horaires ──────────────────────────────
story += [
    Paragraph("5. Programmer des fenêtres horaires", s_h1),
    hr(),
    Paragraph(
        "Tu peux créer plusieurs fenêtres sur différents jours/heures. "
        "Le planificateur daemon vérifie chaque minute si une fenêtre est active.",
        s_body),
    sp(4),
    Paragraph("Exemple de configuration multi-fenêtres :", s_h2),
    table_cmd([
        ['Fenêtre',      'Horaire',          'Itérations', 'Jours'],
        ['Nuit semaine', '23:00 → 06:00',    '10x',        'Lun-Ven'],
        ['Weekend',      '01:00 → 09:00',    '15x',        'Sam-Dim'],
        ['Ma tâche',     '22:00 → 23:00',    '3x',         'Tous'],
    ], col_w=[4*cm, 4*cm, 3*cm, 4.5*cm]),
    sp(8),
    Paragraph("Démarrer le planificateur (une seule fois) :", s_h2),
    *code_block(
        "kittsched",
        "  → Planificateur → Demarrer"),
    Paragraph(
        "Le planificateur tourne en fond et survit à la fermeture du terminal.",
        s_note),
    sp(),
]

# ── SECTION 6 : Versions ────────────────────────────────────────
story += [
    Paragraph("6. Retrouver les versions créées", s_h1),
    hr(),
    Paragraph(
        "Après chaque amélioration réussie, Claude sauvegarde une copie "
        "numérotée avec l'heure et le sujet.",
        s_body),
    sp(4),
    Paragraph("Voir toutes les versions :", s_h2),
    *code_block("kittvers"),
    sp(4),
    Paragraph("Structure du dossier versions/ :", s_h2),
    *code_block(
        "static/versions/",
        "  v00_avant_session_20260225_230000.html   ← état initial",
        "  v01_23h05_Ameliore_la_zone_de_CHAT.html",
        "  v02_23h22_Ameliore_linterface_INPUT.html",
        "  v03_00h01_Ameliore_la_SPHERE_3D.html",
        "  ..."),
    sp(6),
    Paragraph("Revenir à une version précédente :", s_h2),
    *code_block(
        "cp /home/kitt/kitt-ai/static/versions/v03*.html \\",
        "   /home/kitt/kitt-ai/static/index.html"),
    sp(),
]

# ── SECTION 7 : Commandes résumé ───────────────────────────────
story += [
    PageBreak(),
    Paragraph("7. Toutes les commandes — Aide-mémoire", s_h1),
    hr(),
    table_cmd([
        ['Commande',       'Description'],
        ['kittsched',      'Ouvrir le menu principal du scheduler'],
        ['kittnight',      'Lancer 10 améliorations auto maintenant\n(sans passer par le menu)'],
        ['kittvers',       'Lister toutes les versions sauvegardées'],
        ['source ~/.bashrc','Activer les alias (une seule fois par session)'],
    ]),
    sp(16),
    Paragraph("Surveiller le travail en cours :", s_h2),
    *code_block(
        "# Voir ce que Claude fait en ce moment",
        "tail -f /tmp/kitt_night_*.log",
        "",
        "# Voir les logs du planificateur",
        "tail -f /tmp/kitt_scheduler.log",
        "",
        "# Voir tous les processus KITT actifs",
        "pgrep -a -f kitt"),
    sp(12),
    Paragraph("Arrêter une amélioration en cours :", s_h2),
    *code_block(
        "# Trouver le PID",
        "pgrep -f kitt_night_improve",
        "",
        "# Arrêter",
        "kill <PID>"),
    sp(),
]

# ── SECTION 8 : Problèmes courants ─────────────────────────────
story += [
    Paragraph("8. Problèmes courants", s_h1),
    hr(),
    table_cmd([
        ['Problème',                     'Solution'],
        ['kittsched: commande\nintrouvable',
         'Tape: source ~/.bashrc\npuis réessaie kittsched'],
        ['claude: commande\nintrouvable',
         'Vérifie: ls ~/.local/bin/claude\nSi absent, réinstalle Claude Code'],
        ['Claude ne modifie\nrien',
         'Vérifie la tâche dans nano : sois plus\nprécis sur le fichier à modifier'],
        ['Je veux annuler\nen cours',
         'pgrep -f kitt_night  puis  kill <PID>'],
        ['Restaurer l\'original',
         'cp static/versions/v00_*.html\n   static/index.html'],
    ], col_w=[4.5*cm, 11*cm]),
    sp(16),

    Paragraph("Note importante :", s_h2),
    Paragraph(
        "Claude Code utilise ton compte Anthropic et consomme des tokens. "
        "10 itérations sur index.html ≈ quelques centimes. "
        "Ne lance pas des centaines d'itérations sans surveiller.",
        s_warn),
    sp(),
]

# ── PAGE FINALE ──────────────────────────────────────────────────
story += [
    PageBreak(),
    sp(60),
    HRFlowable(width="60%", thickness=2, color=ROUGE, hAlign='CENTER'),
    sp(20),
    Paragraph("K I T T", S('fin', fontSize=32, textColor=ROUGE_C,
        alignment=TA_CENTER, fontName='Helvetica-Bold')),
    Paragraph("Bonne nuit, Manix.", S('fin2', fontSize=14, textColor=GRIS_L,
        alignment=TA_CENTER, fontName='Helvetica-Oblique', spaceAfter=4)),
    sp(10),
    Paragraph("KITT travaille pour toi pendant que tu dors.", S('fin3',
        fontSize=11, textColor=BLANC, alignment=TA_CENTER, fontName='Helvetica')),
    sp(60),
    HRFlowable(width="40%", thickness=1, color=GRIS_C, hAlign='CENTER'),
    sp(10),
    Paragraph("KYRONEX A.I. — by Manix — Jetson Orin Nano Super 8GB", s_center),
]

# ── Fond noir sur toutes les pages ──────────────────────────────
def page_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NOIR)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    # Liseré rouge en bas
    canvas.setFillColor(ROUGE)
    canvas.rect(0, 0, A4[0], 3, fill=1, stroke=0)
    # Numéro de page
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRIS_L)
    canvas.drawRightString(A4[0]-2*cm, 1*cm, f"Page {doc.page}")
    canvas.restoreState()

doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
print(f"PDF genere : {OUT}")
