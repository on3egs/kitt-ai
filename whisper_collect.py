#!/usr/bin/env python3
"""
KITT — Collecte de données pour fine-tuning Whisper
Enregistre ta voix sur 200 phrases prédéfinies.
Résultat : stt_data/ avec .wav + metadata.csv prêt pour Google Colab.

Usage : python3 whisper_collect.py
"""

import os
import csv
import time
import subprocess
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "stt_data")
META_FILE = os.path.join(DATA_DIR, "metadata.csv")
SAMPLE_RATE = 16000
RECORD_CMD = ["arecord", "-D", "pulse", "-r", str(SAMPLE_RATE), "-c", "1", "-f", "S16_LE"]

# 200 phrases couvrant : KITT/vocab spécifique, débit rapide, questions, chiffres, phrases courtes/longues
PHRASES = [
    # KITT & KYRONEX
    "KITT, quelle heure est-il ?",
    "KITT, quel temps fait-il aujourd'hui ?",
    "KITT, allume les turboboosts.",
    "KITT, analyse la situation.",
    "KITT, active le mode furtif.",
    "KITT, quelle est la température du moteur ?",
    "KITT, scan de l'environnement.",
    "KITT, contact avec la fondation.",
    "KITT, je suis prêt à démarrer.",
    "KITT, vitesse maximale autorisée.",
    "KYRONEX est opérationnel.",
    "Système KYRONEX en ligne.",
    "Intelligence artificielle activée.",
    "Knight Industries Two Thousand.",
    "Bonjour KITT, comment vas-tu ?",
    "KITT, donne-moi un rapport de statut.",
    "KITT, connecte-toi au réseau.",
    "KITT, mémorise cette information.",
    "KITT, rappelle-moi demain matin.",
    "KITT, quelle est la distance jusqu'à Liège ?",

    # Phrases courtes et rapides
    "Oui.",
    "Non.",
    "Peut-être.",
    "D'accord.",
    "Très bien.",
    "Absolument.",
    "Certainement.",
    "Je ne sais pas.",
    "C'est exact.",
    "Pas du tout.",
    "Bien sûr que non.",
    "Évidemment.",
    "Sans aucun doute.",
    "Tu as raison.",
    "Je comprends.",
    "C'est possible.",
    "Allons-y.",
    "Attends un instant.",
    "Répète s'il te plaît.",
    "Plus fort.",

    # Questions
    "Quelle heure est-il ?",
    "Quel jour sommes-nous ?",
    "Quelle est la météo ?",
    "Combien de temps reste-t-il ?",
    "Où en sommes-nous ?",
    "Qu'est-ce qui se passe ?",
    "Pourquoi ça ne fonctionne pas ?",
    "Comment faire ça ?",
    "Est-ce que tu m'entends ?",
    "Tu comprends ce que je dis ?",
    "Qu'est-ce que tu penses de ça ?",
    "Est-ce que c'est grave ?",
    "Combien ça coûte ?",
    "Quand est-ce que ça arrive ?",
    "Qui est là ?",
    "Où sont les clés ?",
    "Qu'est-ce qu'on mange ce soir ?",
    "C'est loin d'ici ?",
    "Tu peux m'aider ?",
    "Qu'est-ce que tu fais ?",

    # Chiffres et données
    "Un deux trois quatre cinq.",
    "Six sept huit neuf dix.",
    "Cent, mille, un million.",
    "La température est de vingt-deux degrés.",
    "Il est exactement quatorze heures trente.",
    "Le code d'accès est cinq cinq zéro cinq.",
    "Vitesse : cent vingt kilomètres par heure.",
    "Distance : quarante-cinq kilomètres.",
    "Batterie à quatre-vingt-cinq pourcents.",
    "Mémoire disponible : trois gigaoctets.",
    "Deux mille vingt-six, le vingt-huit février.",
    "Premier, deuxième, troisième, quatrième.",
    "Cinquante euros.",
    "Trente minutes.",
    "Quatre-vingt-dix secondes.",
    "Le modèle trois b est chargé.",
    "Fréquence : quatre-vingt-dix mégahertz.",
    "Altitude : cinq cents mètres.",
    "Coordonnées GPS reçues.",
    "Signal détecté sur le canal sept.",

    # Phrases longues et complexes
    "L'intelligence artificielle va transformer notre façon de vivre et de travailler.",
    "Le Jetson Orin Nano est une plateforme très puissante pour l'inférence locale.",
    "Je voudrais que tu mémorises cette information pour plus tard.",
    "Est-ce que tu peux analyser cette image et me dire ce que tu vois ?",
    "La reconnaissance vocale s'améliore avec l'entraînement sur des données spécifiques.",
    "Envoie un message à Virginie pour lui dire que j'arrive dans vingt minutes.",
    "Quel est le meilleur itinéraire pour éviter les embouteillages à cette heure-ci ?",
    "Rappelle-moi de prendre mes médicaments tous les matins à huit heures.",
    "Je pense que le problème vient de la configuration du réseau local.",
    "Est-ce que tu as détecté des anomalies dans les logs du système ce matin ?",
    "La voiture a besoin d'une révision avant la prochaine balade des Vî Bielles Gaumaises.",
    "Manix veut savoir si tout fonctionne correctement ce soir.",
    "Le serveur kyronex tourne sur le port trois mille en HTTPS.",
    "Active le mode de surveillance et préviens-moi si quelqu'un approche.",
    "Je rentre dans deux heures, prépare un rapport sur la journée.",
    "Quel est l'état de la mémoire partagée entre le CPU et le GPU ?",
    "La température du processeur est dans les limites normales.",
    "Télécharge les dernières mises à jour et installe-les cette nuit.",
    "Crée un backup de la configuration avant de modifier quoi que ce soit.",
    "Lance une analyse complète des fichiers journaux depuis ce matin.",

    # Débit rapide
    "Vite vite vite on n'a pas le temps !",
    "Dépêche-toi c'est urgent !",
    "Maintenant tout de suite immédiatement !",
    "Ça marche ou ça marche pas ?",
    "T'as compris ou pas ?",
    "On y va on y va !",
    "C'est bon j'ai compris merci.",
    "Attends non arrête tout.",
    "Ok ok ok je vois le problème.",
    "C'est exactement ce que je voulais dire.",

    # Noms propres et lieux (Belgique/contexte Manix)
    "Liège, Bruxelles, Gaume, Arlon.",
    "Virginie est arrivée.",
    "Cedric appelle depuis la route.",
    "KR95 est en ligne.",
    "La bourse de Libramont c'est le deux et trois mai.",
    "Les Vî Bielles Gaumaises organisent une balade.",
    "Emmanuel Gelinne dit bonjour.",
    "Michel est le président du club.",
    "La Trans Am mille neuf cent quatre-vingt-deux.",
    "Le salon de l'auto de Bruxelles.",

    # Technologie et informatique
    "Redémarre le serveur s'il te plaît.",
    "La connexion WiFi est instable.",
    "Le modèle de langage est chargé en mémoire.",
    "Whisper transcrit la voix en texte.",
    "Piper génère la voix à partir du texte.",
    "Le GPU est à soixante-cinq degrés.",
    "La RAM est utilisée à soixante-dix pourcents.",
    "Lance un commit git avec le message mis à jour.",
    "Pousse les modifications sur GitHub.",
    "Le service est actif et fonctionne correctement.",
    "Vérifie les logs pour voir s'il y a des erreurs.",
    "Python trois virgule dix est installé.",
    "L'environnement virtuel est activé.",
    "Installe les dépendances avec pip.",
    "Le port trois mille est ouvert.",
    "Certificat SSL auto-signé accepté.",
    "Connexion sécurisée établie.",
    "Données chiffrées en transit.",
    "Sauvegarde automatique en cours.",
    "Mise à jour disponible pour le système.",

    # Météo et quotidien
    "Il fait beau aujourd'hui.",
    "Il pleut depuis ce matin.",
    "La température va descendre cette nuit.",
    "Je prends un café.",
    "On mange dans une heure.",
    "Le téléphone sonne.",
    "J'ai un rendez-vous à quinze heures.",
    "La voiture est garée devant la maison.",
    "Les courses sont faites.",
    "Je vais me coucher tôt ce soir.",
    "Le journal télévisé commence dans dix minutes.",
    "Quelle heure est le lever du soleil demain ?",
    "Il y a des nuages à l'horizon.",
    "La route est glissante ce matin.",
    "Mets de la musique s'il te plaît.",

    # Phrases avec accents et liaison (difficiles pour STT)
    "C'est un objet intéressant.",
    "Ils ont analysé les données.",
    "Vous avez vu l'événement ?",
    "Elle est arrivée en avance.",
    "Les enfants ont adoré ça.",
    "On a eu un problème hier.",
    "C'était très intéressant à voir.",
    "Il faut y aller maintenant.",
    "Je n'en ai aucune idée.",
    "C'est à toi de décider.",
    "Il n'y a pas de solution simple.",
    "Qu'est-ce qu'on fait ensuite ?",
    "Tout va bien se passer.",
    "C'est exactement ce qu'il faut faire.",
    "Je suis complètement d'accord avec toi.",

    # Phrases longues à débit naturel (test de compréhension globale)
    "Bonjour KITT, j'ai besoin que tu m'aides à planifier ma journée de demain.",
    "Est-ce que tu peux vérifier si la connexion internet est stable et me dire la vitesse actuelle ?",
    "Je pense qu'il faudrait améliorer la reconnaissance vocale pour qu'elle soit plus précise.",
    "Peux-tu me lire les derniers messages reçus et me dire s'il y a quelque chose d'urgent ?",
    "Active le mode économie d'énergie pour préserver la batterie pendant la nuit.",
    "Je veux que tu enregistres cette conversation et que tu en fasses un résumé.",
    "Est-ce que le système de surveillance est actif et est-ce qu'il y a eu des alertes ?",
    "Explique-moi comment fonctionne le système de reconnaissance vocale que tu utilises.",
    "Quelle est la probabilité qu'il pleuve demain après-midi selon les prévisions météo ?",
    "Dis-moi tout ce que tu sais sur les voitures anciennes et les clubs de passionnés.",

    # Répétitions (renforcement)
    "KITT.",
    "KITT !",
    "KITT, tu m'entends ?",
    "Oui KITT.",
    "Non KITT.",
    "Merci KITT.",
    "Bravo KITT.",
    "Bien joué KITT.",
    "Parfait KITT.",
    "Excellent KITT.",
]

os.makedirs(DATA_DIR, exist_ok=True)

# Charger les samples déjà enregistrés
done = set()
if os.path.exists(META_FILE):
    with open(META_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row["file_name"])

def record_phrase(idx, phrase, duration=None):
    """Enregistre une phrase, durée automatique (max 8s) ou fixe."""
    fname = f"sample_{idx:04d}.wav"
    fpath = os.path.join(DATA_DIR, fname)

    # Durée auto selon longueur de la phrase
    if duration is None:
        words = len(phrase.split())
        duration = max(3, min(8, int(words * 0.5) + 1))

    print(f"\n[{idx+1}/{len(PHRASES)}] Lis cette phrase ({duration}s) :")
    print(f"\n  >>> {phrase}\n")
    input("    Appuie sur ENTREE quand tu es prêt...")

    print(f"  ENREGISTREMENT... ({duration}s)", end="", flush=True)
    cmd = RECORD_CMD + ["-d", str(duration), fpath]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(" OK")

    # Vérifier que le fichier existe et a du contenu
    if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000:
        print("  ERREUR: enregistrement vide, recommencer...")
        return None

    return fname, phrase, duration

def save_meta(fname, phrase):
    """Ajoute une ligne au metadata.csv."""
    file_exists = os.path.exists(META_FILE)
    with open(META_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "transcription"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"file_name": fname, "transcription": phrase})

def main():
    print("=" * 60)
    print("  KITT — Collecte de données Whisper fine-tuning")
    print("=" * 60)
    print(f"\nDossier de sortie : {DATA_DIR}")
    print(f"Phrases restantes : {len(PHRASES) - len(done)}/{len(PHRASES)}")
    print(f"Micro utilisé     : PulseAudio (défaut système)")
    print("\nTu peux arrêter avec Ctrl+C et reprendre plus tard.")
    print("Les phrases déjà enregistrées sont automatiquement sautées.\n")

    remaining = [(i, p) for i, p in enumerate(PHRASES)
                 if f"sample_{i:04d}.wav" not in done]

    if not remaining:
        print("Toutes les phrases sont enregistrées ! Lance whisper_finetune.py sur Colab.")
        return

    try:
        for idx, phrase in remaining:
            result = record_phrase(idx, phrase)
            if result:
                fname, phrase_text, dur = result
                save_meta(fname, phrase_text)
                done.add(fname)
                pct = len(done) / len(PHRASES) * 100
                print(f"  Progression : {len(done)}/{len(PHRASES)} ({pct:.0f}%)")
            else:
                # Retry
                result = record_phrase(idx, phrase)
                if result:
                    fname, phrase_text, dur = result
                    save_meta(fname, phrase_text)

    except KeyboardInterrupt:
        print(f"\n\nPause. {len(done)} phrases enregistrées sur {len(PHRASES)}.")
        print("Relance le script pour continuer.")

    print(f"\nTermine ! Données dans : {DATA_DIR}/")
    print(f"Prochaine étape : zippe stt_data/ et uploade sur Google Colab.")
    print(f"  zip -r stt_data.zip stt_data/")

if __name__ == "__main__":
    main()
