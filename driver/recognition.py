#!/usr/bin/env python3
"""
K.I.T.T. Driver Recognition System By Manix.
Offline face detection + recognition using OpenCV DNN (YuNet + SFace).
Optimized for NVIDIA Jetson Orin Nano 8GB.

Auteur : ByManix (Emmanuel Gelinne)
License: Elastic License 2.0 (ELv2)

Usage:
    python3 recognition.py --enroll Manix   # Enroll a face
    python3 recognition.py                  # Run recognition
"""

import os
import sys
import time
import subprocess
import numpy as np
from pathlib import Path

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import cv2

# ── Paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
KITT_DIR = BASE_DIR.parent
MODEL_DIR = BASE_DIR / "models"
FACE_DIR = BASE_DIR / "faces"

YUNET_MODEL = str(MODEL_DIR / "face_detection_yunet_2023mar.onnx")
SFACE_MODEL = str(MODEL_DIR / "face_recognition_sface_2021dec.onnx")

PIPER_BIN = KITT_DIR / "piper" / "piper" / "piper"
PIPER_MODEL = KITT_DIR / "models" / "fr_FR-tom-medium.onnx"

# ── Config ───────────────────────────────────────────────────
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
COSINE_THRESHOLD = 0.363
CONSECUTIVE_MATCHES = 3
ENROLL_CAPTURES = 5


def open_camera():
    """Open camera — try V4L2 first, fallback to GStreamer CSI."""
    cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap
    # CSI camera fallback (Jetson)
    gst = (
        "nvarguscamerasrc ! video/x-raw(memory:NVMM),"
        f"width={FRAME_WIDTH},height={FRAME_HEIGHT},framerate=30/1 ! "
        "nvvidconv ! video/x-raw,format=BGRx ! "
        "videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
    )
    cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
    if cap.isOpened():
        return cap
    return None


def create_detector(w, h):
    det = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (w, h))
    det.setScoreThreshold(0.7)
    return det


def create_recognizer():
    return cv2.FaceRecognizerSF.create(SFACE_MODEL, "")


# ── TTS ──────────────────────────────────────────────────────
def speak(text):
    """Play text via Piper TTS."""
    wav = "/tmp/kitt_greet.wav"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/home/kitt/CTranslate2/install/lib:" + str(PIPER_BIN.parent) + ":" + env.get("LD_LIBRARY_PATH", "")
    try:
        subprocess.run(
            [str(PIPER_BIN), "--model", str(PIPER_MODEL),
             "--output_file", wav, "--length_scale", "0.9"],
            input=text.encode(),
            env=env,
            capture_output=True,
            timeout=10,
        )
        if os.path.exists(wav):
            subprocess.run(["paplay", wav], timeout=10)
            os.unlink(wav)
    except Exception as e:
        print(f"[TTS] Erreur: {e}")


# ── LLM ──────────────────────────────────────────────────────
def start_llm(user):
    """Start the LLM via start_kyronex.sh."""
    env = os.environ.copy()
    start_script = KITT_DIR / "start_kyronex.sh"
    if start_script.exists():
        print(f"[LLM] Démarrage via start_kyronex.sh (conducteur={user})")
        subprocess.Popen(["bash", str(start_script)], env=env)
        return
    print("[LLM] Aucun LLM disponible (start_kyronex.sh introuvable)")


# ── Enrollment ───────────────────────────────────────────────
def enroll(name):
    """Capture face encodings and store them."""
    cap = open_camera()
    if not cap:
        print("[ERREUR] Impossible d'ouvrir la caméra")
        return False

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    detector = create_detector(w, h)
    recognizer = create_recognizer()

    print(f"[INFO] Enrôlement de '{name}'")
    print(f"[INFO] Placez votre visage devant la caméra...")
    time.sleep(2)

    # Vider le buffer caméra
    for _ in range(5):
        cap.read()

    encodings = []
    attempts = 0
    max_attempts = 150  # ~5 seconds at 30fps

    while len(encodings) < ENROLL_CAPTURES and attempts < max_attempts:
        ret, frame = cap.read()
        attempts += 1
        if not ret:
            time.sleep(0.1)
            continue
        _, faces = detector.detect(frame)
        if faces is not None and len(faces) > 0:
            aligned = recognizer.alignCrop(frame, faces[0])
            enc = recognizer.feature(aligned)
            encodings.append(enc.copy())
            print(f"  Capture {len(encodings)}/{ENROLL_CAPTURES} "
                  f"(conf={faces[0][14]:.2f})")
            time.sleep(0.3)  # Pause entre captures pour varier les angles

    cap.release()

    if len(encodings) < 3:
        print("[ERREUR] Pas assez de captures. Réessayez avec un meilleur éclairage.")
        return False

    avg = np.mean(encodings, axis=0)
    FACE_DIR.mkdir(parents=True, exist_ok=True)
    save_path = FACE_DIR / f"{name}.npy"
    np.save(str(save_path), avg)
    print(f"[OK] Visage '{name}' enregistré -> {save_path}")
    return True


# ── Recognition ──────────────────────────────────────────────
def recognize():
    """Detect and recognize driver face. Greet + start LLM on match."""
    # Load known faces
    known = {}
    for f in FACE_DIR.glob("*.npy"):
        known[f.stem] = np.load(str(f))
    if not known:
        print("[ERREUR] Aucun visage enregistré. Utilisez: --enroll <nom>")
        return False

    print(f"[INFO] Visages chargés: {list(known.keys())}")

    cap = open_camera()
    if not cap:
        print("[ERREUR] Impossible d'ouvrir la caméra")
        return False

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    detector = create_detector(w, h)
    recognizer = create_recognizer()

    print("[INFO] Reconnaissance en cours...")

    streak = 0
    matched_name = None
    timeout_start = time.time()
    timeout_sec = 30

    while time.time() - timeout_start < timeout_sec:
        ret, frame = cap.read()
        if not ret:
            continue

        _, faces = detector.detect(frame)
        if faces is None or len(faces) == 0:
            streak = 0
            matched_name = None
            continue

        aligned = recognizer.alignCrop(frame, faces[0])
        enc = recognizer.feature(aligned)

        best_name = None
        best_score = 0.0
        for name, stored in known.items():
            score = recognizer.match(
                enc, stored, cv2.FaceRecognizerSF_FR_COSINE
            )
            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score >= COSINE_THRESHOLD:
            if best_name == matched_name:
                streak += 1
            else:
                matched_name = best_name
                streak = 1

            if streak >= CONSECUTIVE_MATCHES:
                print(f"[OK] Conducteur reconnu: {matched_name} "
                      f"(score={best_score:.3f})")
                cap.release()
                speak(f"Bonjour {matched_name}")
                start_llm(matched_name)
                return True
        else:
            streak = 0
            matched_name = None

    cap.release()
    print("[INFO] Timeout — aucun conducteur reconnu")
    return False


# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--enroll":
        name = sys.argv[2] if len(sys.argv) > 2 else "Manix"
        sys.exit(0 if enroll(name) else 1)
    else:
        sys.exit(0 if recognize() else 1)
