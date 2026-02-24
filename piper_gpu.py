#!/usr/bin/env python3
"""
PiperGPU — Wrapper Python pour Piper TTS avec onnxruntime GPU.
Charge le modele ONNX une seule fois, fait l'inference via CUDAExecutionProvider.
Remplace le subprocess piper binary (qui recharge le modele a chaque appel).

Copyright 2026 ByManix (Emmanuel Gelinne) — Elastic License 2.0
"""

import json
import random
import re
import struct
import subprocess
import threading
import time
import wave
from collections import OrderedDict
from pathlib import Path

import numpy as np
import onnxruntime as ort


class PiperGPU:
    def __init__(self, model_path: str, device: str = "cuda"):
        model_path = Path(model_path)
        config_path = model_path.with_suffix(".onnx.json")

        # Load config
        with open(config_path) as f:
            self.config = json.load(f)

        self.sample_rate = self.config["audio"]["sample_rate"]
        self.phoneme_id_map = self.config["phoneme_id_map"]
        inference = self.config.get("inference", {})
        self.noise_scale = inference.get("noise_scale", 0.667)
        self.length_scale = inference.get("length_scale", 1.0)
        self.noise_w = inference.get("noise_w", 0.8)
        self.espeak_voice = self.config.get("espeak", {}).get("voice", "fr")

        # Load ONNX model
        providers = []
        if device == "cuda":
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        t0 = time.time()
        self.session = ort.InferenceSession(
            str(model_path), sess_options=sess_options, providers=providers
        )
        active = self.session.get_providers()
        ms = (time.time() - t0) * 1000
        self.device = "cuda" if "CUDAExecutionProvider" in active else "cpu"
        print(f"[TTS] Modele charge en {ms:.0f}ms ({self.device.upper()})", flush=True)

    def phonemize(self, text: str) -> str:
        """Convert text to IPA phonemes via espeak-ng."""
        result = subprocess.run(
            ["espeak-ng", "--ipa", "-v", self.espeak_voice, "-q", "--", text],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()

    def phonemes_to_ids(self, phonemes: str) -> list[int]:
        """Convert IPA phoneme string to Piper phoneme IDs with intersperse padding."""
        ids = []

        # BOS
        if "^" in self.phoneme_id_map:
            ids.extend(self.phoneme_id_map["^"])
            ids.extend(self.phoneme_id_map["_"])  # pad after BOS

        for ch in phonemes:
            if ch == "\n":
                # Sentence boundary — insert silence (space + pad)
                if " " in self.phoneme_id_map:
                    ids.extend(self.phoneme_id_map[" "])
                    ids.extend(self.phoneme_id_map["_"])
                continue
            if ch in self.phoneme_id_map:
                ids.extend(self.phoneme_id_map[ch])
                ids.extend(self.phoneme_id_map["_"])  # pad after each phoneme

        # EOS
        if "$" in self.phoneme_id_map:
            ids.extend(self.phoneme_id_map["$"])

        return ids

    def _split_natural_segments(self, text: str) -> list[tuple[str, float, float]]:
        """
        Split text into natural speech segments with cinematic pauses and speed variation.

        Returns: list of (segment_text, pause_duration_ms, speed_variation) tuples
        Pause durations:
            . ! ? … → 350-450ms (phrase finale, variable)
            , ; :   → 180-250ms (pause courte, variable)
        Speed variation: 0.95-1.05 (±5% per sentence for natural rhythm)

        Segments shorter than 4 characters are merged with the next segment to avoid
        unnatural fragmentation (fixes "Je … vais bien" bug).
        """
        if not text.strip():
            return []

        # Regex: capture texte + ponctuation séparément
        # Match: texte non-vide suivi optionnellement de ponctuation
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

        # MERGE: Fusionner les segments trop courts (< 4 caractères) avec le suivant
        # Évite les pauses artificielles après "Je", "Il", "Un", etc.
        merged = []
        i = 0
        while i < len(raw_segments):
            seg, punct = raw_segments[i]

            # Si segment court ET pas le dernier, fusionner avec le suivant
            while len(seg) < 4 and i + 1 < len(raw_segments):
                next_seg, next_punct = raw_segments[i + 1]
                seg = seg + punct + " " + next_seg  # Garder l'espace naturel
                punct = next_punct
                i += 1

            merged.append((seg, punct))
            i += 1

        # Construire les segments finaux avec timing cinématique
        segments = []

        for seg, punct in merged:
            # Variation de vitesse aléatoire (±5%) pour éviter le ton robotique
            speed_var = 0.95 + random.random() * 0.10  # 0.95 à 1.05

            # Pauses naturelles avec variation
            pause_ms = 0.0
            if punct:
                # Ponctuation forte → pause longue (350-450ms)
                if any(p in punct for p in ".!?…"):
                    pause_ms = 350 + random.random() * 100
                # Ponctuation légère → pause courte (180-250ms)
                elif any(p in punct for p in ",;:"):
                    pause_ms = 180 + random.random() * 70

            segments.append((seg + punct, pause_ms, speed_var))

        return segments

    def synthesize(self, text: str, length_scale: float | None = None, natural_pauses: bool = False) -> np.ndarray:
        """
        Synthesize text to audio waveform (float32 numpy array).

        Args:
            text: Text to synthesize
            length_scale: Speech rate (lower = faster, higher = slower)
            natural_pauses: If True, insert subtle pauses at punctuation (optimized for speed)
        """
        if not text.strip():
            return np.array([], dtype=np.float32)

        # Mode RAPIDE avec pauses subtiles (UNE SEULE inférence)
        if natural_pauses:
            # Remplacer ponctuation par silences courts dans le texte avant synthèse
            # Ceci permet 1 seule inférence au lieu de 3-4
            processed_text = text

            # Points/questions → pause longue (3 espaces = ~120ms)
            processed_text = processed_text.replace('. ', '.   ')
            processed_text = processed_text.replace('! ', '!   ')
            processed_text = processed_text.replace('? ', '?   ')
            processed_text = processed_text.replace('… ', '…   ')

            # Virgules/deux-points → pause moyenne (2 espaces = ~60ms)
            processed_text = processed_text.replace(', ', ',  ')
            processed_text = processed_text.replace(': ', ':  ')
            processed_text = processed_text.replace('; ', ';  ')

            # UNE SEULE inférence rapide
            return self._synthesize_raw(processed_text, length_scale)

        # Mode standard (sans pauses)
        return self._synthesize_raw(text, length_scale)

    def _synthesize_raw(self, text: str, length_scale: float | None = None) -> np.ndarray:
        """Internal method: synthesize text without preprocessing."""
        if not text.strip():
            return np.array([], dtype=np.float32)

        phonemes = self.phonemize(text)
        if not phonemes:
            return np.array([], dtype=np.float32)

        ids = self.phonemes_to_ids(phonemes)
        if len(ids) < 3:
            return np.array([], dtype=np.float32)

        ls = length_scale if length_scale is not None else self.length_scale
        scales = np.array([self.noise_scale, ls, self.noise_w], dtype=np.float32)
        input_ids = np.array([ids], dtype=np.int64)
        input_lengths = np.array([len(ids)], dtype=np.int64)

        t0 = time.time()
        output = self.session.run(
            None,
            {"input": input_ids, "input_lengths": input_lengths, "scales": scales},
        )
        ms = (time.time() - t0) * 1000

        audio = output[0].squeeze()
        print(f"[TTS] Inference {ms:.0f}ms | {len(audio)} samples ({len(audio)/self.sample_rate:.2f}s) [{self.device.upper()}]", flush=True)
        return audio

    def synthesize_to_wav(self, text: str, output_path: str, length_scale: float | None = None, natural_pauses: bool = False) -> str:
        """
        Synthesize text and write to WAV file. Returns the output path.

        Args:
            text: Text to synthesize
            output_path: Output WAV file path
            length_scale: Speech rate
            natural_pauses: If True, insert pauses at punctuation marks
        """
        audio = self.synthesize(text, length_scale=length_scale, natural_pauses=natural_pauses)
        if len(audio) == 0:
            raise RuntimeError("TTS: aucun audio genere")

        # Clip and convert to int16
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)

        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return output_path


# ── TTS Multilingue ─────────────────────────────────────────────────────

LANG_MODELS = {
    "fr": "fr_FR-tom-medium.onnx",
    "en": "en_US-lessac-medium.onnx",
    "de": "de_DE-thorsten-medium.onnx",
    "it": "it_IT-paola-medium.onnx",
    "pt": "pt_BR-faber-medium.onnx",   # pt_PT-tugao est 0 octets → BR fallback
}
SUPPORTED_LANGS = set(LANG_MODELS.keys())

# Langues Whisper sans modèle TTS → langue de fallback
_LANG_FALLBACK = {
    "nl": "fr",   # néerlandais/flamand → fr
    "es": "fr",   # espagnol → fr
    "af": "fr",   # afrikaans → fr
    "ca": "fr",   # catalan → fr
    "pl": "fr",   # polonais → fr
    "ru": "fr",   # russe → fr
    "zh": "en",   # chinois → en
    "ja": "en",   # japonais → en
    "ko": "en",   # coréen → en
    "ar": "fr",   # arabe → fr
    "tr": "fr",   # turc → fr
    "pt-br": "pt", "pt-pt": "pt",  # variantes portugais
}

# Heuristiques rapides par mots fréquents (pour textes courts < 20 chars)
_LANG_PATTERNS = {
    "fr": re.compile(
        r"\b(je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|est|sont|"
        r"avec|pour|dans|sur|par|et|ou|mais|que|qui|quoi|comment|quand|bonjour|"
        r"merci|oui|non|voici|j'ai|j'aime|c'est|j'|d'|l'|m'|t'|s'|n')\b", re.I),
    "en": re.compile(
        r"\b(i|you|he|she|we|they|it|is|are|was|were|have|has|the|a|an|and|or|"
        r"but|in|on|at|to|for|with|from|this|that|what|how|when|where|hello|"
        r"yes|no|please|thank|thanks|okay|ok|hi|hey|my|your|do|don't|can|"
        r"will|would|could|should)\b", re.I),
    "de": re.compile(
        r"\b(ich|du|er|sie|wir|ihr|es|ist|bin|hat|haben|der|die|das|ein|eine|"
        r"und|oder|aber|in|auf|mit|für|von|was|wie|wann|wo|hallo|danke|bitte|"
        r"ja|nein|nicht|kein|sehr|auch|noch|dann|jetzt)\b", re.I),
    "it": re.compile(
        r"\b(io|tu|lui|lei|noi|voi|loro|è|sono|ho|ha|il|la|lo|i|le|un|una|e|"
        r"o|ma|in|su|per|con|da|cosa|come|quando|dove|ciao|grazie|prego|sì|no|"
        r"anche|molto|bene|buongiorno|salve)\b", re.I),
    "pt": re.compile(
        r"\b(eu|tu|ele|ela|nós|vocês|eles|elas|é|são|tem|tenho|o|a|os|as|um|"
        r"uma|e|ou|mas|em|no|na|para|com|de|que|como|quando|onde|olá|obrigado|"
        r"obrigada|sim|não|também|muito|bom|boa|tudo|bem)\b", re.I),
}


def _map_whisper_lang(whisper_lang: str) -> str:
    """Mappe les codes langue Whisper vers les codes TTS supportés."""
    if not whisper_lang:
        return "fr"
    lang = whisper_lang.lower().strip()
    # Chercher dans le fallback map d'abord
    if lang in _LANG_FALLBACK:
        return _LANG_FALLBACK[lang]
    # Tronquer à 2 chars
    lang2 = lang[:2]
    if lang2 in _LANG_FALLBACK:
        return _LANG_FALLBACK[lang2]
    return lang2 if lang2 in SUPPORTED_LANGS else "fr"


class MultilingualTTS:
    """
    Moteur TTS multilingue avec lazy loading et cache LRU.
    - Français (fr) : toujours chargé en CUDA (langue principale)
    - Autres langues : chargées à la demande en CPU, cache LRU de taille 1
    - Interface identique à PiperGPU pour compatibilité totale
    """
    _MAX_CPU_CACHED = 1  # 1 langue secondaire en CPU max (VRAM limitée)

    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)
        self._lock = threading.Lock()
        self._cpu_cache: OrderedDict = OrderedDict()  # lang -> PiperGPU (CPU)

        # Charger le français en CUDA au boot
        fr_path = self.models_dir / LANG_MODELS["fr"]
        self._fr_engine = PiperGPU(str(fr_path), device="cuda")
        self.device = self._fr_engine.device  # Pour compatibilité

    @property
    def sample_rate(self) -> int:
        """Retourne le sample rate du modèle français (référence)."""
        return self._fr_engine.sample_rate

    def _get_engine(self, lang: str) -> PiperGPU:
        """Retourne le moteur pour la langue donnée. Lazy loading avec LRU."""
        lang = lang.lower()[:2] if lang else "fr"
        if lang not in SUPPORTED_LANGS:
            lang = "fr"

        if lang == "fr":
            return self._fr_engine

        model_file = LANG_MODELS[lang]
        if not (self.models_dir / model_file).exists():
            print(f"[TTS] Modèle {model_file} absent — fallback fr", flush=True)
            return self._fr_engine

        with self._lock:
            if lang in self._cpu_cache:
                self._cpu_cache.move_to_end(lang)
                return self._cpu_cache[lang]

            # Évincer le modèle le moins récent si cache plein
            if len(self._cpu_cache) >= self._MAX_CPU_CACHED:
                evicted_lang, evicted = self._cpu_cache.popitem(last=False)
                del evicted
                print(f"[TTS] Eviction cache lang={evicted_lang}", flush=True)

            # Charger sur CPU (pas de conflit VRAM avec LLM)
            model_path = self.models_dir / model_file
            print(f"[TTS] Chargement lang={lang} (CPU)...", flush=True)
            engine = PiperGPU(str(model_path), device="cpu")
            self._cpu_cache[lang] = engine
            return engine

    def synthesize_to_wav(self, text: str, output_path: str,
                          length_scale: float | None = None,
                          natural_pauses: bool = False,
                          lang: str = "fr") -> str:
        """Synthétise le texte dans la langue donnée. Interface identique à PiperGPU."""
        engine = self._get_engine(lang)
        return engine.synthesize_to_wav(text, output_path,
                                        length_scale=length_scale,
                                        natural_pauses=natural_pauses)


def _detect_lang(text: str) -> str:
    """Détecte la langue du texte avec heuristiques + langdetect. Fallback: 'fr'."""
    if not text or not text.strip():
        return "fr"
    t = text.strip()

    # Phase 1 — heuristiques par regex (rapide, fiable sur phrases courtes)
    scores = {}
    for lang, pattern in _LANG_PATTERNS.items():
        scores[lang] = len(pattern.findall(t))

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    # Si un pattern domine clairement → on lui fait confiance
    if best_score >= 2:
        return best_lang
    if best_score == 1 and len(t.split()) <= 6:
        return best_lang

    # Phase 2 — langdetect sur textes plus longs (plus fiable)
    if len(t) >= 20:
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0
            lang = detect(t)
            lang = _LANG_FALLBACK.get(lang, lang[:2] if len(lang) > 2 else lang)
            return lang if lang in SUPPORTED_LANGS else "fr"
        except Exception:
            pass

    # Phase 3 — si heuristique a un score de 1, on l'utilise quand même
    if best_score >= 1:
        return best_lang

    return "fr"


# ── CLI pour test et benchmark ──────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="PiperGPU — TTS wrapper")
    parser.add_argument("--model", default="models/fr_FR-tom-medium.onnx")
    parser.add_argument("--test", type=str, help="Generate WAV from text")
    parser.add_argument("--benchmark", type=str, help="Benchmark GPU vs CPU")
    parser.add_argument("--output", default="/tmp/piper_gpu_test.wav")
    parser.add_argument("--length-scale", type=float, default=0.9)
    args = parser.parse_args()

    if args.test:
        engine = PiperGPU(args.model, device="cuda")
        t0 = time.time()
        engine.synthesize_to_wav(args.test, args.output, length_scale=args.length_scale)
        total = (time.time() - t0) * 1000
        print(f"[TEST] Total {total:.0f}ms -> {args.output}")

    elif args.benchmark:
        text = args.benchmark
        print("=" * 60)
        print(f"Benchmark: \"{text}\"")
        print("=" * 60)

        for device in ["cuda", "cpu"]:
            print(f"\n--- {device.upper()} ---")
            engine = PiperGPU(args.model, device=device)
            # Warmup
            engine.synthesize(text, length_scale=args.length_scale)
            # Benchmark 5 runs
            times = []
            for i in range(5):
                t0 = time.time()
                audio = engine.synthesize(text, length_scale=args.length_scale)
                times.append((time.time() - t0) * 1000)
            avg = sum(times) / len(times)
            duration = len(audio) / engine.sample_rate
            rtf = (avg / 1000) / duration if duration > 0 else float("inf")
            print(f"  Moyenne: {avg:.0f}ms (RTF={rtf:.3f})")
            print(f"  Runs: {', '.join(f'{t:.0f}ms' for t in times)}")
            del engine

        print("\n" + "=" * 60)
    else:
        parser.print_help()
