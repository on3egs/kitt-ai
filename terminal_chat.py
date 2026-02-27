#!/usr/bin/env python3
"""
KYRONEX Terminal — Chat vocal en mode terminal.
Zéro navigateur, zéro GUI → économie mémoire maximale.
KYRONEX parle à voix haute + écoute le micro.

Lancement : venv/bin/python3 terminal_chat.py
Quitter  : touche Fin (End) ou Ctrl+C

Entrée vide = active le micro (parle puis Entrée pour envoyer)
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import termios
import tty

# ── Couleurs ANSI ────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
GRAY = "\033[90m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SERVER = "https://127.0.0.1:3000"
SESSION_ID = f"terminal-{os.getpid()}"

import ssl as _ssl
_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl.CERT_NONE


def clear_screen():
    print("\033[2J\033[H", end="", flush=True)


def print_banner():
    clear_screen()
    print(f"{RED}{BOLD}")
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║              K  I  T  T                   ║")
    print("  ║   Knight Industries Two Thousand           ║")
    print("  ║          By Manix — Terminal               ║")
    print("  ╚═══════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"  {GRAY}Tapez votre message + Entrée")
    print(f"  Entrée seule = micro (parlez puis Entrée)")
    print(f"  Tapez {WHITE}auto{GRAY} = écoute automatique continue")
    print(f"  Tapez {WHITE}kitt{GRAY} = wake word (dites \"KITT\" pour activer)")
    print(f"  Touche Fin (End) ou Ctrl+C pour quitter{RESET}")
    print(f"  {DIM}{'─' * 45}{RESET}")
    print()


# ── Audio playback ───────────────────────────────────────────────────────

_current_playback = None  # process paplay en cours

async def play_audio(session, audio_url: str):
    """Télécharge le WAV et le joue via paplay en arrière-plan."""
    global _current_playback
    try:
        async with session.get(f"{SERVER}{audio_url}", ssl=_ssl_ctx) as resp:
            if resp.status != 200:
                return
            wav_data = await resp.read()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_data)
            tmp_path = f.name

        _current_playback = await asyncio.create_subprocess_exec(
            "paplay", tmp_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await _current_playback.wait()
        _current_playback = None
        os.unlink(tmp_path)
    except Exception:
        _current_playback = None


async def wait_for_playback():
    """Attend la fin de la lecture audio en cours."""
    if _current_playback and _current_playback.returncode is None:
        await _current_playback.wait()


# ── Sons de réflexion (thinking) ─────────────────────────────────────────

_thinking_task = None

async def _play_kitt_scanner():
    """Joue un sweep sinusoïdal KITT scanner (montant puis descendant)."""
    try:
        tmp_up = tempfile.mktemp(suffix="_up.wav")
        tmp_down = tempfile.mktemp(suffix="_down.wav")
        tmp_scan = tempfile.mktemp(suffix="_scan.wav")

        # Générer sweep montant + descendant, concaténer
        p1 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp_up, "synth", "0.4", "sine", "300:900",
            "gain", "-20", "fade", "t", "0.03", "0.4", "0.03",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        p2 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp_down, "synth", "0.4", "sine", "900:300",
            "gain", "-20", "fade", "t", "0.03", "0.4", "0.03",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p1.wait()
        await p2.wait()

        p3 = await asyncio.create_subprocess_exec(
            "sox", tmp_up, tmp_down, tmp_scan,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p3.wait()

        p4 = await asyncio.create_subprocess_exec(
            "play", "-q", tmp_scan,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p4.wait()

        for f in (tmp_up, tmp_down, tmp_scan):
            try:
                os.unlink(f)
            except OSError:
                pass
    except Exception:
        pass


async def play_kitt_turbo():
    """Son turbo boost KITT (sweep rapide montant + écho)."""
    try:
        tmp1 = tempfile.mktemp(suffix="_t1.wav")
        tmp2 = tempfile.mktemp(suffix="_t2.wav")
        tmp_out = tempfile.mktemp(suffix="_turbo.wav")

        p1 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp1, "synth", "0.3", "sine", "200:1200", "gain", "-16",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        p2 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp2, "synth", "0.15", "sine", "1200:1800", "gain", "-16",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p1.wait()
        await p2.wait()

        p3 = await asyncio.create_subprocess_exec(
            "sox", tmp1, tmp2, tmp_out,
            "echo", "0.6", "0.7", "40", "0.4",
            "fade", "t", "0.02", "0.45", "0.1",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p3.wait()

        p4 = await asyncio.create_subprocess_exec(
            "play", "-q", tmp_out,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p4.wait()

        for f in (tmp1, tmp2, tmp_out):
            try:
                os.unlink(f)
            except OSError:
                pass
    except Exception:
        pass


async def play_kitt_alert():
    """Bip d'alerte KITT (double bip aigu)."""
    try:
        tmp1 = tempfile.mktemp(suffix="_b1.wav")
        tmp_s = tempfile.mktemp(suffix="_bs.wav")
        tmp2 = tempfile.mktemp(suffix="_b2.wav")
        tmp_out = tempfile.mktemp(suffix="_alert.wav")

        p1 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp1, "synth", "0.1", "sine", "880", "gain", "-18",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        p2 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp_s, "synth", "0.05", "sine", "0", "gain", "-60",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        p3 = await asyncio.create_subprocess_exec(
            "sox", "-n", tmp2, "synth", "0.1", "sine", "880", "gain", "-18",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p1.wait()
        await p2.wait()
        await p3.wait()

        p4 = await asyncio.create_subprocess_exec(
            "sox", tmp1, tmp_s, tmp2, tmp_out,
            "fade", "t", "0.01", "0.25", "0.02",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p4.wait()

        p5 = await asyncio.create_subprocess_exec(
            "play", "-q", tmp_out,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p5.wait()

        for f in (tmp1, tmp_s, tmp2, tmp_out):
            try:
                os.unlink(f)
            except OSError:
                pass
    except Exception:
        pass


async def _thinking_loop():
    """Boucle de sons scanner KITT pendant la réflexion."""
    try:
        while True:
            await _play_kitt_scanner()
            await asyncio.sleep(0.3)
    except asyncio.CancelledError:
        pass


def start_thinking():
    global _thinking_task
    if _thinking_task is None:
        _thinking_task = asyncio.create_task(_thinking_loop())


def stop_thinking():
    global _thinking_task
    if _thinking_task:
        _thinking_task.cancel()
        _thinking_task = None


# ── Microphone recording ────────────────────────────────────────────────

async def record_and_transcribe(session) -> str:
    """Enregistre via arecord, envoie à /api/stt, retourne le texte."""
    tmp_path = tempfile.mktemp(suffix=".wav")

    print(f"  {YELLOW}{BOLD}[MIC]{RESET} {YELLOW}Parlez maintenant... (Entrée pour arrêter){RESET}", flush=True)

    # Start arecord
    proc = await asyncio.create_subprocess_exec(
        "arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav", tmp_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    # Wait for Enter key in a thread to not block
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _wait_for_enter)

    # Stop recording
    proc.send_signal(signal.SIGINT)
    try:
        await asyncio.wait_for(proc.wait(), timeout=2)
    except asyncio.TimeoutError:
        proc.kill()

    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 1000:
        print(f"  {DIM}Rien enregistré.{RESET}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return ""

    # Send to STT
    print(f"  {DIM}Transcription...{RESET}", end="", flush=True)
    try:
        import aiohttp
        with open(tmp_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("audio", f, filename="recording.wav", content_type="audio/wav")
            async with session.post(f"{SERVER}/api/stt", data=data, ssl=_ssl_ctx) as resp:
                result = await resp.json()

        os.unlink(tmp_path)
        text = result.get("text", "").strip()
        stt_ms = result.get("stt_ms", 0)

        if text:
            print(f"\r  {DIM}STT: {stt_ms}ms{RESET}              ")
            return text
        else:
            print(f"\r  {DIM}Rien compris — parlez plus fort{RESET}    ")
            return ""
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        print(f"\r  {DIM}Erreur STT: {e}{RESET}    ")
        return ""


def _wait_for_enter():
    """Bloque jusqu'à ce que l'utilisateur appuie sur Entrée."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n", "\x03"):
                return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ── Mode auto-écoute (VAD) ──────────────────────────────────────────────

import struct
import select

VAD_THRESHOLD = 500      # seuil RMS pour int16 (0-32767)
SILENCE_MS = 750         # ms de silence avant fin de phrase
MIN_SPEECH_MS = 600      # durée minimum de parole
SAMPLE_RATE = 16000
CHUNK_BYTES = 4096       # ~128ms à 16kHz mono 16bit


def _check_key_pressed() -> bool:
    """Vérifie si une touche a été pressée (non bloquant)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        r, _, _ = select.select([fd], [], [], 0)
        if r:
            sys.stdin.read(1)
            return True
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _rms_int16(data: bytes) -> float:
    """Calcule le RMS d'un buffer PCM int16."""
    count = len(data) // 2
    if count == 0:
        return 0
    samples = struct.unpack(f"<{count}h", data[:count * 2])
    s = sum(x * x for x in samples)
    return (s / count) ** 0.5


async def auto_listen_loop(session, name: str):
    """Boucle d'écoute automatique avec VAD. Entrée pour quitter."""
    print(f"\n  {YELLOW}{BOLD}[AUTO]{RESET} {YELLOW}Écoute automatique activée{RESET}")
    print(f"  {DIM}Appuyez sur Entrée pour désactiver{RESET}\n")

    while True:
        print(f"  {DIM}En attente de voix...{RESET}", end="\r", flush=True)

        # Lancer arecord en mode raw vers stdout
        proc = await asyncio.create_subprocess_exec(
            "arecord", "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-c", "1",
            "-t", "raw", "-q", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        is_speaking = False
        speech_start = 0
        silence_start = 0
        audio_chunks = []
        got_speech = False

        try:
            while True:
                # Vérifier si Entrée pressée (quitter auto)
                loop = asyncio.get_event_loop()
                key = await loop.run_in_executor(None, _check_key_pressed)
                if key:
                    proc.kill()
                    print(f"\r  {YELLOW}{BOLD}[AUTO]{RESET} {DIM}Écoute automatique désactivée{RESET}    ")
                    print()
                    return

                # Lire un chunk audio
                try:
                    chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_BYTES), timeout=0.2)
                except asyncio.TimeoutError:
                    continue

                if not chunk:
                    break

                rms = _rms_int16(chunk)
                now = asyncio.get_event_loop().time() * 1000  # ms

                if rms > VAD_THRESHOLD:
                    if not is_speaking:
                        is_speaking = True
                        speech_start = now
                        audio_chunks = []
                        print(f"\r  {YELLOW}{BOLD}[MIC]{RESET} {YELLOW}Parole détectée...{RESET}        ", flush=True)
                    silence_start = 0
                    audio_chunks.append(chunk)
                elif is_speaking:
                    audio_chunks.append(chunk)
                    if silence_start == 0:
                        silence_start = now
                    if now - silence_start > SILENCE_MS:
                        is_speaking = False
                        duration = now - speech_start
                        if duration > MIN_SPEECH_MS:
                            got_speech = True
                            break
                        else:
                            # Trop court, ignorer
                            audio_chunks = []
                            silence_start = 0
                            print(f"\r  {DIM}En attente de voix...{RESET}", end="\r", flush=True)

        finally:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass

        if not got_speech:
            continue

        # Sauvegarder le WAV
        import wave
        tmp_path = tempfile.mktemp(suffix=".wav")
        raw_data = b"".join(audio_chunks)
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(raw_data)

        # STT
        print(f"\r  {DIM}Transcription...{RESET}                  ", end="", flush=True)
        try:
            import aiohttp
            with open(tmp_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("audio", f, filename="recording.wav", content_type="audio/wav")
                async with session.post(f"{SERVER}/api/stt", data=data, ssl=_ssl_ctx) as resp:
                    result = await resp.json()

            os.unlink(tmp_path)
            text = result.get("text", "").strip()
            stt_ms = result.get("stt_ms", 0)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            print(f"\r  {DIM}Erreur STT: {e}{RESET}              ")
            continue

        if not text:
            print(f"\r  {DIM}Rien compris — parlez plus fort{RESET}       ")
            continue

        print(f"\r  {DIM}STT: {stt_ms}ms{RESET}                        ")
        print(f"  {GREEN}{BOLD}{name}:{RESET} {GREEN}{text}{RESET}")

        # Chat + réponse vocale
        await stream_chat(session, text)

        # Attendre fin de la lecture audio avant de ré-écouter
        await wait_for_playback()
        await asyncio.sleep(0.5)


# ── Chat streaming + audio ──────────────────────────────────────────────

async def stream_chat(session, message: str):
    """Envoie un message, affiche le texte, joue l'audio en streaming fluide."""
    # Sons de réflexion démarrent IMMÉDIATEMENT (avant même d'envoyer)
    start_thinking()

    payload = {"message": message, "session_id": SESSION_ID}
    full_reply = ""
    first_token = True

    # Queue pour jouer les chunks audio dans l'ordre
    audio_queue = asyncio.Queue()
    playback_task = None

    async def audio_player():
        """Lit la queue et joue chaque chunk audio dans l'ordre."""
        first_chunk = True
        while True:
            url = await audio_queue.get()
            if url is None:  # Signal de fin
                break
            # Petit délai uniquement pour le 1er chunk (laisser quelques mots s'afficher)
            if first_chunk:
                await asyncio.sleep(0.3)
                first_chunk = False
            # Jouer immédiatement (pendant que le texte continue à s'écrire)
            await play_audio(session, url)

    print(f"  {RED}{BOLD}KITT:{RESET} {RED}", end="", flush=True)

    try:
        async with session.post(
            f"{SERVER}/api/chat/stream", json=payload, ssl=_ssl_ctx,
        ) as resp:
            buffer = ""
            async for chunk in resp.content:
                buffer += chunk.decode("utf-8")
                lines = buffer.split("\n")
                buffer = lines.pop()
                for line in lines:
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("token"):
                                if first_token:
                                    stop_thinking()
                                    first_token = False
                                print(data["token"], end="", flush=True)
                                full_reply += data["token"]
                            # Ajouter chunk audio à la queue → joué immédiatement en parallèle
                            if data.get("audio_chunk"):
                                if playback_task is None:
                                    playback_task = asyncio.create_task(audio_player())
                                await audio_queue.put(data["audio_chunk"])
                            if data.get("done"):
                                if data.get("timing"):
                                    t = data["timing"]
                                    parts = []
                                    if t.get("vision_ms"):
                                        parts.append(f"Vision:{t['vision_ms']}ms")
                                    parts.append(f"LLM:{t.get('llm_ms', 0)}ms")
                                    parts.append(f"TTS:{t.get('tts_ms', 0)}ms")
                                    print(f"{RESET}")
                                    print(f"  {DIM}{' '.join(parts)}{RESET}")
                        except (json.JSONDecodeError, KeyError):
                            pass
    except Exception as e:
        stop_thinking()
        print(f"{RESET}")
        print(f"  {DIM}Erreur: {e}{RESET}")

    stop_thinking()

    if full_reply and not full_reply.endswith("\n"):
        print(f"{RESET}")

    print()

    # Signaler fin de stream audio et attendre la fin de lecture
    if playback_task:
        await audio_queue.put(None)  # Signal de fin
        await playback_task  # Attendre que tout soit joué

    return full_reply


# ── Helpers serveur ──────────────────────────────────────────────────────

async def check_health(session) -> bool:
    try:
        async with session.get(f"{SERVER}/api/health", ssl=_ssl_ctx) as resp:
            data = await resp.json()
            return data.get("llm_server", False)
    except Exception:
        return False


async def set_name(session, name: str):
    try:
        await session.post(f"{SERVER}/api/set-name", json={"name": name}, ssl=_ssl_ctx)
    except Exception:
        pass


async def get_whoami(session) -> str:
    try:
        async with session.get(f"{SERVER}/api/whoami", ssl=_ssl_ctx) as resp:
            data = await resp.json()
            return data.get("name", "")
    except Exception:
        return ""


# ── Input avec touche Fin ────────────────────────────────────────────────

def read_input_with_end_key(prompt: str) -> str | None:
    """Lit une ligne. Retourne None si touche Fin (End) pressée."""
    sys.stdout.write(prompt)
    sys.stdout.flush()

    buf = []
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)

            if ch == "\r" or ch == "\n":
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(buf)

            if ch == "\x03":  # Ctrl+C
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return None

            if ch == "\x1b":  # Escape sequence
                seq1 = sys.stdin.read(1)
                if seq1 == "[":
                    seq2 = sys.stdin.read(1)
                    if seq2 == "F":  # End key
                        sys.stdout.write("\r\n")
                        sys.stdout.flush()
                        return None
                    if seq2 == "4":  # End key \x1b[4~
                        sys.stdin.read(1)
                        sys.stdout.write("\r\n")
                        sys.stdout.flush()
                        return None
                    continue
                elif seq1 == "O":
                    seq2 = sys.stdin.read(1)
                    if seq2 == "F":  # End key alternate
                        sys.stdout.write("\r\n")
                        sys.stdout.flush()
                        return None
                    continue
                continue

            if ch == "\x7f" or ch == "\x08":  # Backspace
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            if ch.isprintable():
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ── Mode Wake Word "KITT" ────────────────────────────────────────────────

import re as _re
WAKE_REGEX = _re.compile(r"\bki+t+\b", _re.IGNORECASE)

async def wake_word_loop(session, name: str):
    """Boucle d'écoute permanente avec détection du mot-clé KITT."""
    print(f"\n  {YELLOW}{BOLD}[WAKE]{RESET} {YELLOW}Mode wake word actif — dites \"KITT\" pour parler{RESET}")
    print(f"  {DIM}Appuyez sur Entrée pour désactiver{RESET}\n")

    while True:
        print(f"  {DIM}En attente de \"KITT\"...{RESET}", end="\r", flush=True)

        proc = await asyncio.create_subprocess_exec(
            "arecord", "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-c", "1",
            "-t", "raw", "-q", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        is_speaking = False
        speech_start = 0
        silence_start = 0
        audio_chunks = []
        got_speech = False

        try:
            while True:
                loop = asyncio.get_event_loop()
                key = await loop.run_in_executor(None, _check_key_pressed)
                if key:
                    proc.kill()
                    print(f"\r  {YELLOW}{BOLD}[WAKE]{RESET} {DIM}Wake word désactivé{RESET}    ")
                    print()
                    return

                try:
                    chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_BYTES), timeout=0.2)
                except asyncio.TimeoutError:
                    continue

                if not chunk:
                    break

                rms = _rms_int16(chunk)
                now = asyncio.get_event_loop().time() * 1000

                if rms > VAD_THRESHOLD:
                    if not is_speaking:
                        is_speaking = True
                        speech_start = now
                        audio_chunks = []
                    silence_start = 0
                    audio_chunks.append(chunk)
                elif is_speaking:
                    audio_chunks.append(chunk)
                    if silence_start == 0:
                        silence_start = now
                    if now - silence_start > SILENCE_MS:
                        is_speaking = False
                        duration = now - speech_start
                        if duration > MIN_SPEECH_MS:
                            got_speech = True
                            break
                        else:
                            audio_chunks = []
                            silence_start = 0
        finally:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass

        if not got_speech:
            continue

        # Sauvegarder le WAV et transcrire
        import wave as _wave
        tmp_path = tempfile.mktemp(suffix=".wav")
        raw_data = b"".join(audio_chunks)
        with _wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(raw_data)

        try:
            import aiohttp
            with open(tmp_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("audio", f, filename="recording.wav", content_type="audio/wav")
                async with session.post(f"{SERVER}/api/stt", data=data, ssl=_ssl_ctx) as resp:
                    result = await resp.json()
            os.unlink(tmp_path)
            text = result.get("text", "").strip()
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            continue

        if not text:
            continue

        # Vérifier si "KITT" est dans la transcription
        match = WAKE_REGEX.search(text)
        if not match:
            print(f"\r  {DIM}Pas de wake word: \"{text[:40]}\"{RESET}          ")
            continue

        # Extraire la commande après "KITT"
        command = text[match.end():].strip()
        command = _re.sub(r'^[,.\s!?:]+', '', command).strip()

        if command:
            # "KITT quelle heure est-il" → envoyer directement
            print(f"\r  {YELLOW}{BOLD}[KITT]{RESET} {YELLOW}Wake word + commande détectée{RESET}")
            print(f"  {GREEN}{BOLD}{name}:{RESET} {GREEN}{command}{RESET}")
            await play_kitt_alert()
            await stream_chat(session, command)
            await wait_for_playback()
            await asyncio.sleep(0.5)
        else:
            # "KITT" seul → attendre une commande (6 secondes)
            print(f"\r  {YELLOW}{BOLD}[KITT]{RESET} {YELLOW}Wake word détecté ! Parlez maintenant...{RESET}")
            await play_kitt_alert()

            # Enregistrer la commande suivante
            follow_up = await _record_follow_up(session)
            if follow_up:
                print(f"  {GREEN}{BOLD}{name}:{RESET} {GREEN}{follow_up}{RESET}")
                await stream_chat(session, follow_up)
                await wait_for_playback()
                await asyncio.sleep(0.5)
            else:
                print(f"  {DIM}Pas de commande reçue.{RESET}")


async def _record_follow_up(session, timeout_s: float = 6.0) -> str:
    """Enregistre une commande de suivi après le wake word (max 6s)."""
    proc = await asyncio.create_subprocess_exec(
        "arecord", "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-c", "1",
        "-t", "raw", "-q", "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    is_speaking = False
    silence_start = 0
    speech_start = 0
    audio_chunks = []
    got_speech = False
    start_time = asyncio.get_event_loop().time()

    try:
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_s:
                break

            try:
                chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_BYTES), timeout=0.2)
            except asyncio.TimeoutError:
                continue

            if not chunk:
                break

            rms = _rms_int16(chunk)
            now = asyncio.get_event_loop().time() * 1000

            if rms > VAD_THRESHOLD:
                if not is_speaking:
                    is_speaking = True
                    speech_start = now
                    audio_chunks = []
                silence_start = 0
                audio_chunks.append(chunk)
            elif is_speaking:
                audio_chunks.append(chunk)
                if silence_start == 0:
                    silence_start = now
                if now - silence_start > SILENCE_MS:
                    is_speaking = False
                    if now - speech_start > MIN_SPEECH_MS:
                        got_speech = True
                        break
                    else:
                        audio_chunks = []
                        silence_start = 0
    finally:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass

    if not got_speech or not audio_chunks:
        return ""

    import wave as _wave
    tmp_path = tempfile.mktemp(suffix=".wav")
    raw_data = b"".join(audio_chunks)
    with _wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(raw_data)

    try:
        import aiohttp
        with open(tmp_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("audio", f, filename="recording.wav", content_type="audio/wav")
            async with session.post(f"{SERVER}/api/stt", data=data, ssl=_ssl_ctx) as resp:
                result = await resp.json()
        os.unlink(tmp_path)
        return result.get("text", "").strip()
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return ""


# ── Main ─────────────────────────────────────────────────────────────────

async def main():
    import aiohttp

    print_banner()

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:

        # Health check
        print(f"  {GRAY}Connexion au serveur...{RESET}", end="", flush=True)
        online = await check_health(session)
        if online:
            print(f"\r  {GREEN}Serveur en ligne{RESET}              ")
        else:
            print(f"\r  {RED}Serveur hors ligne — lancez start_kyronex.sh{RESET}")
            return

        # Identification
        name = await get_whoami(session)
        if not name:
            print()
            raw_name = read_input_with_end_key(f"  {WHITE}Votre prénom : {RESET}")
            if raw_name is None or not raw_name.strip():
                print(f"\n  {GRAY}Au revoir.{RESET}\n")
                return
            name = raw_name.strip()[:30]
            await set_name(session, name)

        print()
        print(f"  {RED}{BOLD}KITT:{RESET} {RED}Bonjour {name}. Je suis KITT, Knight Industries Two Thousand.")
        print(f"  Comment puis-je vous assister ?{RESET}")
        print()

        # Chat loop
        while True:
            line = read_input_with_end_key(f"  {GREEN}{BOLD}{name}:{RESET} {GREEN}")
            print(f"{RESET}", end="")

            if line is None:
                print(f"\n  {RED}KITT:{RESET} {DIM}Fin de session. Au revoir {name}.{RESET}\n")
                break

            msg = line.strip()

            # "auto" = basculer en écoute automatique
            if msg.lower() == "auto":
                await auto_listen_loop(session, name)
                continue

            # "kitt" = mode wake word
            if msg.lower() == "kitt":
                await wake_word_loop(session, name)
                continue

            # Entrée vide = mode micro (push-to-talk)
            if not msg:
                text = await record_and_transcribe(session)
                if not text:
                    continue
                msg = text
                print(f"  {GREEN}{BOLD}{name}:{RESET} {GREEN}{msg}{RESET}")

            reply = await stream_chat(session, msg)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n  {DIM}Session terminée.{RESET}\n")
