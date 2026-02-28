# MODULE TECH & AI — Jetson / LLM / STT / TTS Optimisation

## Matériel de référence
NVIDIA Jetson : Nano (472 GFLOPS), Xavier NX (21 TOPS), Orin Nano (40 TOPS), Orin NX (100 TOPS), AGX Orin (275 TOPS)
RAM unifiée CPU/GPU — pas de transfert PCIe. Avantage : bande passante interne élevée.

## LLM sur Jetson — Hiérarchie d'optimisation

### Modèles recommandés (2025)
- 3B Q5_K_M : Qwen2.5-3B, Phi-3-mini — idéal Orin Nano 8GB
- 7B Q4_K_M : Qwen2.5-7B, Mistral-7B — AGX Orin 32GB minimum
- Quantisation : Q5_K_M = meilleur compromis qualité/VRAM, Q4_K_M = vitesse max

### Paramètres optimaux Qwen 2.5 3B Q5
temperature=0.7, top_p=0.8, top_k=20, min_p=0.05
repeat_penalty=1.1, repeat_last_n=64, max_tokens=256
System prompt : max 147 tokens (OOM si dépassé sur Orin Nano 8GB)
History : max 6 messages, ctx_size 2048, --parallel 1

### Filtrage tokens Qwen (obligatoire)
Supprimer balises <think>...</think> et tokens spéciaux <|...|>
Buffer accumulatif côté serveur — ne pas émettre avant bloc complet.

## STT — Whisper
- Modèle base : GPU float16, ~350ms, 500MB VRAM
- Modèle small : ~600ms, 900MB VRAM
- VAD (Voice Activity Detection) : seuil 0.015 RMS recommandé
- Silence : 1200ms pour déclencher transcription

## TTS — Piper
- Modèle tom-medium (fr) : GPU, ~490ms, 300MB VRAM
- length_scale 1.05 : débit naturel
- Pauses : 3 espaces = point, 2 espaces = virgule
- Fusionner segments < 4 chars avant synthèse
- Filtrer ponctuation isolée avant envoi (évite "(f)", "(,)")

## RAG — Retrieval Augmented Generation
- Keyword matching simple : efficace pour domaines métier spécifiques
- Embedding/cosine : meilleure pertinence mais +100ms et VRAM
- Chunking optimal : 500–1500 chars par document
- Injection via tag [CONNAISSANCE LOCALE: ...] dans le message user
- Seuil de déclenchement : score keyword ≥ 2 mots significatifs

## Réduction de latence (classée par impact)
1. Session HTTP persistante pour LLM (aiohttp ClientSession)
2. Streaming SSE token par token (première réponse perçue ~300ms)
3. TTS par phrase (ne pas attendre réponse complète)
4. Cache audio SHA256 (évite re-synthèse réponses communes)
5. Vision démon séparé (CUDA context persistant)

## Audio Jetson
- paplay uniquement (jamais aplay — latence + blocage)
- PulseAudio : carte USB prioritaire
- Format optimal : WAV 22050Hz mono 16bit

## Surveillance système
- GPU temp > 70°C → alerte KITT proactive
- RAM libre < 500MB → alerte + drop_caches
- VRAM OOM → NvMapMemAllocInternalTagged error 12
