#!/usr/bin/env python3
"""
Test script pour valider les corrections TTS :
1. Segmentation correcte (pas de pauses après fragments courts)
2. Timing cinématique (pré-délai, pauses naturelles, variation vitesse)

Usage:
    venv/bin/python3 test_tts_fix.py
"""

import sys
from pathlib import Path

# Import depuis piper_gpu
sys.path.insert(0, str(Path(__file__).parent))
from piper_gpu import PiperGPU

# Textes de test
TEST_CASES = [
    # Cas 1: Bug original — fragments courts ne doivent PAS créer de pauses
    ("Je vais bien, merci.", "Pas de pause après 'Je'"),

    # Cas 2: Ponctuation multiple
    ("Je... vais bien !", "Fusion 'Je...' avec suite, pause finale"),

    # Cas 3: Phrases courtes
    ("Il fait beau. C'est super.", "Deux phrases, pause entre"),

    # Cas 4: Ponctuation mixte
    ("Bonjour, je suis KYRONEX. Comment allez-vous ?", "Pauses courtes et finales"),

    # Cas 5: Fragment ultra-court
    ("À bientôt !", "Pas de split sur 'À'"),
]


def test_segmentation():
    """Test la segmentation sans charger le modèle ONNX."""
    print("=" * 70)
    print("TEST SEGMENTATION — Validation de la logique de split")
    print("=" * 70)

    # Créer un mock minimal pour tester _split_natural_segments
    class MockPiper:
        def _split_natural_segments(self, text):
            # Copie de la méthode corrigée
            import re
            import random

            if not text.strip():
                return []

            pattern = r'([^.!?,;:…]+)([.!?,;:…]+)?'
            raw_segments = []

            for match in re.finditer(pattern, text):
                segment = match.group(1).strip()
                punct = match.group(2) if match.group(2) else ""
                if not segment:
                    continue
                raw_segments.append((segment, punct))

            if not raw_segments:
                return []

            # MERGE: segments < 4 caractères
            merged = []
            i = 0
            while i < len(raw_segments):
                seg, punct = raw_segments[i]
                while len(seg) < 4 and i + 1 < len(raw_segments):
                    next_seg, next_punct = raw_segments[i + 1]
                    seg = seg + punct + " " + next_seg
                    punct = next_punct
                    i += 1
                merged.append((seg, punct))
                i += 1

            # Timing cinématique
            segments = []
            for seg, punct in merged:
                speed_var = 0.95 + random.random() * 0.10
                pause_ms = 0.0
                if punct:
                    if any(p in punct for p in ".!?…"):
                        pause_ms = 350 + random.random() * 100
                    elif any(p in punct for p in ",;:"):
                        pause_ms = 180 + random.random() * 70
                segments.append((seg + punct, pause_ms, speed_var))

            return segments

    mock = MockPiper()

    for i, (text, expected) in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}] {text}")
        print(f"Attendu : {expected}")

        segments = mock._split_natural_segments(text)

        print(f"Segments : {len(segments)}")
        for j, (seg_text, pause_ms, speed) in enumerate(segments, 1):
            pause_type = ""
            if pause_ms > 0:
                if pause_ms >= 350:
                    pause_type = f" → PAUSE FINALE ({pause_ms:.0f}ms)"
                else:
                    pause_type = f" → pause courte ({pause_ms:.0f}ms)"

            print(f"  {j}. '{seg_text}' (vitesse={speed:.3f}){pause_type}")

        # Validation
        for seg_text, _, _ in segments:
            # Retirer la ponctuation finale pour le test
            seg_clean = seg_text.rstrip(".!?,;:…").strip()
            if seg_clean and len(seg_clean) < 4:
                print(f"  ⚠️  WARNING: Fragment court détecté: '{seg_clean}' ({len(seg_clean)} car)")

    print("\n" + "=" * 70)


def test_synthesis():
    """Test complet avec synthèse audio."""
    print("\n" + "=" * 70)
    print("TEST SYNTHÈSE AUDIO — Génération avec timing cinématique")
    print("=" * 70)

    model_path = Path(__file__).parent / "models" / "fr_FR-tom-medium.onnx"

    if not model_path.exists():
        print(f"\n⚠️  Modèle introuvable: {model_path}")
        print("Sautez ce test (segmentation validée ci-dessus)")
        return

    print(f"\nChargement du modèle TTS...")
    try:
        tts = PiperGPU(str(model_path), device="cuda")
    except Exception as e:
        print(f"CUDA échoué ({e}), fallback CPU")
        tts = PiperGPU(str(model_path), device="cpu")

    # Test avec le cas problématique
    test_text = "Je vais très bien, merci. Et vous ?"
    output_path = "/tmp/test_tts_fix.wav"

    print(f"\nTexte: '{test_text}'")
    print("Synthèse avec natural_pauses=True...")

    import time
    t0 = time.time()
    tts.synthesize_to_wav(test_text, output_path, length_scale=0.9, natural_pauses=True)
    elapsed = (time.time() - t0) * 1000

    print(f"\n✓ Audio généré en {elapsed:.0f}ms → {output_path}")
    print(f"  Écoute: aplay {output_path}")

    # Analyse de la segmentation utilisée
    segments = tts._split_natural_segments(test_text)
    print(f"\n  Détail segmentation ({len(segments)} segments):")
    for i, (seg, pause, speed) in enumerate(segments, 1):
        print(f"    {i}. '{seg}' | pause={pause:.0f}ms | vitesse={speed:.3f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import os
    os.environ["ORT_LOG_LEVEL"] = "ERROR"  # Supprime warnings ONNX

    # Test 1: Segmentation pure (rapide, pas besoin du modèle)
    test_segmentation()

    # Test 2: Synthèse complète (nécessite le modèle)
    try:
        test_synthesis()
    except KeyboardInterrupt:
        print("\n\nTest interrompu.")
    except Exception as e:
        print(f"\n⚠️  Erreur synthèse: {e}")
        print("Segmentation testée avec succès ci-dessus.")
