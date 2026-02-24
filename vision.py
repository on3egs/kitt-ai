#!/usr/bin/env python3
"""
KYRONEX Vision Module — YOLOX-S (Apache 2.0) + auto-enhancement.
Runs with system python3 + cv2 (no venv needed).

Usage:
    /usr/bin/python3 vision.py              # capture + detect, JSON to stdout
    /usr/bin/python3 vision.py --test       # test camera only
    /usr/bin/python3 vision.py --debug      # save debug images
    /usr/bin/python3 vision.py --benchmark  # speed test
"""

import json
import os
import sys
import time
import numpy as np
from pathlib import Path
from collections import Counter

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import cv2

# ── Paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ONNX_MODEL = BASE_DIR / "models" / "yolox_s.onnx"

INPUT_SIZE = 640
CONF_THRESHOLD = 0.35
NMS_THRESHOLD = 0.45

# ── COCO class names (French) ───────────────────────────────
COCO_NAMES = [
    "personne", "velo", "voiture", "moto", "avion", "bus", "train", "camion",
    "bateau", "feu de signalisation", "bouche d'incendie", "panneau stop",
    "parcmetre", "banc", "oiseau", "chat", "chien", "cheval", "mouton",
    "vache", "elephant", "ours", "zebre", "girafe", "sac a dos", "parapluie",
    "sac a main", "cravate", "valise", "frisbee", "skis", "snowboard",
    "balle", "cerf-volant", "batte", "gant", "skateboard", "planche de surf",
    "raquette", "bouteille", "verre a vin", "tasse", "fourchette", "couteau",
    "cuillere", "bol", "banane", "pomme", "sandwich", "orange", "brocoli",
    "carotte", "hot-dog", "pizza", "donut", "gateau", "chaise", "canape",
    "plante en pot", "lit", "table", "toilettes", "ecran", "ordinateur portable",
    "souris", "telecommande", "clavier", "telephone portable", "micro-ondes",
    "four", "grille-pain", "evier", "refrigerateur", "livre", "horloge",
    "vase", "ciseaux", "ours en peluche", "seche-cheveux", "brosse a dents",
]

# ── Color mapping (HSV hue ranges -> French names) ──────────
COLOR_RANGES = [
    ((0, 10), "rouge"),
    ((10, 25), "orange"),
    ((25, 35), "jaune"),
    ((35, 85), "vert"),
    ((85, 130), "bleu"),
    ((130, 160), "violet"),
    ((160, 180), "rouge"),
]


# ══════════════════════════════════════════════════════════════
# Image preprocessing
# ══════════════════════════════════════════════════════════════

def enhance_image(frame):
    """Auto-enhance brightness and contrast for better detection."""
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(grey))

    if mean_brightness < 60:
        # Dark image: apply CLAHE (adaptive histogram equalization)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        frame = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    elif mean_brightness < 90:
        # Slightly dark: mild brightness boost
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        frame = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    return frame


def letterbox(frame, target=640):
    """Resize with padding (letterbox) — preserves aspect ratio."""
    img_h, img_w = frame.shape[:2]
    scale = min(target / img_w, target / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    pad_w = (target - new_w) // 2
    pad_h = (target - new_h) // 2
    padded = np.full((target, target, 3), 114, dtype=np.uint8)
    padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

    return padded, scale, pad_w, pad_h


def preprocess(frame):
    """Letterbox + NCHW float32 blob (YOLOX: 0-255, BGR, no normalization)."""
    padded, scale, pad_w, pad_h = letterbox(frame, INPUT_SIZE)
    blob = padded.astype(np.float32)  # YOLOX expects 0-255
    blob = blob.transpose(2, 0, 1)   # HWC -> CHW
    blob = blob[np.newaxis, ...]     # add batch dim -> NCHW
    blob = np.ascontiguousarray(blob)
    return blob, scale, pad_w, pad_h


# ══════════════════════════════════════════════════════════════
# Camera capture
# ══════════════════════════════════════════════════════════════

def capture_frame():
    """Capture a single fresh frame from the webcam."""
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Flush stale frames (BUFFERSIZE=1 réduit le besoin)
    for _ in range(5):
        cap.grab()

    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


# ══════════════════════════════════════════════════════════════
# YOLOX grid generation
# ══════════════════════════════════════════════════════════════

def _make_grids(input_size=640, strides=(8, 16, 32)):
    """Build YOLOX anchor grids for decoding raw predictions."""
    grids = []
    exp_strides = []
    for s in strides:
        h, w = input_size // s, input_size // s
        yv, xv = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        grid = np.stack([xv, yv], axis=2).reshape(-1, 2).astype(np.float32)
        grids.append(grid)
        exp_strides.append(np.full((h * w, 1), s, dtype=np.float32))
    return np.concatenate(grids, axis=0), np.concatenate(exp_strides, axis=0)

GRIDS, STRIDES_GRID = _make_grids(INPUT_SIZE)


# ══════════════════════════════════════════════════════════════
# ONNX inference (YOLOX-S)
# ══════════════════════════════════════════════════════════════

_cached_net = None

def _get_net():
    """Charge le modèle YOLOX-S une seule fois (cache global)."""
    global _cached_net
    if _cached_net is None:
        _cached_net = cv2.dnn.readNetFromONNX(str(ONNX_MODEL))
    return _cached_net


def run_onnx(frame, enhanced, model_path):
    """Run YOLOX-S via cv2.dnn (modèle en cache)."""
    net = _get_net()
    blob, scale, pad_w, pad_h = preprocess(enhanced)
    net.setInput(blob)
    outputs = net.forward(net.getUnconnectedOutLayersNames())
    return postprocess(outputs[0], frame.shape, scale, pad_w, pad_h)


# ══════════════════════════════════════════════════════════════
# Post-processing (YOLOX)
# ══════════════════════════════════════════════════════════════

def postprocess(output, orig_shape, scale, pad_w, pad_h):
    """Parse YOLOX output -> list of (class_id, confidence, x1, y1, x2, y2).

    YOLOX output: [1, 8400, 85] = 4 bbox + 1 objectness + 80 class scores.
    Bbox coords are raw offsets; decoded via grid + stride.
    """
    img_h, img_w = orig_shape[:2]

    # output shape: [1, 8400, 85]
    predictions = output[0]  # (8400, 85)

    # Decode bbox: cx = (raw_x + grid_x) * stride, cy = (raw_y + grid_y) * stride
    #              w  = exp(raw_w) * stride,        h  = exp(raw_h) * stride
    cx = (predictions[:, 0] + GRIDS[:, 0]) * STRIDES_GRID[:, 0]
    cy = (predictions[:, 1] + GRIDS[:, 1]) * STRIDES_GRID[:, 0]
    w = np.exp(predictions[:, 2]) * STRIDES_GRID[:, 0]
    h = np.exp(predictions[:, 3]) * STRIDES_GRID[:, 0]

    # Score = objectness * max(class_scores)
    objectness = predictions[:, 4]
    class_scores = predictions[:, 5:]
    max_class_scores = np.max(class_scores, axis=1)
    scores = objectness * max_class_scores

    mask = scores > CONF_THRESHOLD
    cx, cy, w, h = cx[mask], cy[mask], w[mask], h[mask]
    filtered_scores = scores[mask]
    class_ids = np.argmax(class_scores[mask], axis=1)

    rects = []
    confidences = []
    ids = []

    for i in range(len(filtered_scores)):
        x1 = int((cx[i] - w[i] / 2 - pad_w) / scale)
        y1 = int((cy[i] - h[i] / 2 - pad_h) / scale)
        bw = int(w[i] / scale)
        bh = int(h[i] / scale)
        rects.append([x1, y1, bw, bh])
        confidences.append(float(filtered_scores[i]))
        ids.append(int(class_ids[i]))

    detections = []
    if rects:
        indices = cv2.dnn.NMSBoxes(rects, confidences, CONF_THRESHOLD, NMS_THRESHOLD)
        if len(indices) > 0:
            for idx in indices.flatten():
                x1, y1, bw, bh = rects[idx]
                x2, y2 = x1 + bw, y1 + bh
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(img_w, x2)
                y2 = min(img_h, y2)
                detections.append((ids[idx], confidences[idx], x1, y1, x2, y2))

    return detections


# ══════════════════════════════════════════════════════════════
# Color analysis
# ══════════════════════════════════════════════════════════════

def detect_color(roi):
    """Detect dominant color in a region of interest."""
    if roi.size == 0 or roi.shape[0] < 5 or roi.shape[1] < 5:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))

    if mean_s < 30:
        return "blanc" if mean_v > 170 else ("noir" if mean_v < 60 else "gris")

    mask = (s > 40) & (v > 40)
    if np.sum(mask) < 20:
        return "gris"

    hist = cv2.calcHist([h], [0], mask.astype(np.uint8) * 255, [180], [0, 180])
    dominant_hue = int(np.argmax(hist))

    for (lo, hi), name in COLOR_RANGES:
        if lo <= dominant_hue < hi:
            return name
    return None


def detect_clothing_colors(frame, box):
    """For person detections, analyze upper/lower body colors."""
    x1, y1, x2, y2 = box
    h = y2 - y1
    if h < 30:
        return None, None

    upper_roi = frame[y1 + int(h * 0.15):y1 + int(h * 0.45), x1:x2]
    lower_roi = frame[y1 + int(h * 0.55):y1 + int(h * 0.90), x1:x2]

    return detect_color(upper_roi), detect_color(lower_roi)


# ══════════════════════════════════════════════════════════════
# Build description
# ══════════════════════════════════════════════════════════════

def check_brightness(frame):
    """Mean brightness (0-255)."""
    return float(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))


def build_description(frame, detections):
    """Build French description from detections."""
    brightness = check_brightness(frame)
    dark_warning = ""
    if brightness < 30:
        dark_warning = " La scene est tres sombre, les resultats peuvent etre imprecis."

    if not detections:
        if brightness < 30:
            return {"objects": [], "brightness": round(brightness),
                    "description": "Scene tres sombre. Impossible de detecter des objets. Allumez la lumiere."}
        return {"objects": [], "brightness": round(brightness),
                "description": "Aucun objet detecte dans le champ de vision."}

    objects = []
    description_parts = []

    for class_id, conf, x1, y1, x2, y2 in detections:
        name = COCO_NAMES[class_id] if class_id < len(COCO_NAMES) else f"objet_{class_id}"
        obj = {"name": name, "confidence": round(conf, 2)}

        if class_id == 0:  # person
            upper, lower = detect_clothing_colors(frame, (x1, y1, x2, y2))
            clothing = []
            if upper:
                clothing.append(f"haut {upper}")
                obj["upper_color"] = upper
            if lower:
                clothing.append(f"bas {lower}")
                obj["lower_color"] = lower
            if clothing:
                description_parts.append(f"une personne ({', '.join(clothing)})")
            else:
                description_parts.append("une personne")
        else:
            color = detect_color(frame[y1:y2, x1:x2])
            if color:
                obj["color"] = color
                description_parts.append(f"{name} ({color})")
            else:
                description_parts.append(name)

        objects.append(obj)

    counts = Counter(description_parts)
    parts = []
    for item, count in counts.items():
        parts.append(f"{count}x {item}" if count > 1 else item)

    desc = "Objets detectes: " + ", ".join(parts) + "." + dark_warning
    return {"objects": objects, "brightness": round(brightness), "description": desc}


# ══════════════════════════════════════════════════════════════
# Main detection pipeline
# ══════════════════════════════════════════════════════════════

def detect(frame, debug=False):
    """Full pipeline: enhance -> detect -> describe."""
    t0 = time.time()
    enhanced = enhance_image(frame)
    t_enhance = time.time()

    # Run YOLOX-S ONNX
    try:
        if ONNX_MODEL.exists():
            detections = run_onnx(frame, enhanced, ONNX_MODEL)
            backend_name = "YOLOX-S"
        else:
            return {"error": "Modele YOLOX-S introuvable: " + str(ONNX_MODEL)}
    except Exception as e:
        return {"error": str(e)}

    t_detect = time.time()

    result = build_description(frame, detections)
    result["backend"] = backend_name
    result["timing_ms"] = {
        "enhance": round((t_enhance - t0) * 1000),
        "detect": round((t_detect - t_enhance) * 1000),
        "total": round((time.time() - t0) * 1000),
    }

    if debug:
        debug_frame = frame.copy()
        for class_id, conf, x1, y1, x2, y2 in detections:
            name = COCO_NAMES[class_id] if class_id < len(COCO_NAMES) else f"#{class_id}"
            cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(debug_frame, f"{name} {conf:.0%}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.imwrite(str(BASE_DIR / "debug_capture.jpg"), frame)
        cv2.imwrite(str(BASE_DIR / "debug_enhanced.jpg"), enhanced)
        cv2.imwrite(str(BASE_DIR / "debug_detections.jpg"), debug_frame)
        print("[DEBUG] Images sauvees: debug_capture/enhanced/detections.jpg", file=sys.stderr)

    return result


def daemon_mode():
    """Mode persistant: modèle chargé une fois, requêtes via stdin/stdout."""
    _get_net()  # Charge le modèle au démarrage
    print("READY", flush=True)

    for line in sys.stdin:
        cmd = line.strip()
        if cmd == "capture":
            try:
                frame = capture_frame()
                if frame is None:
                    print(json.dumps({"error": "Camera indisponible"}), flush=True)
                    continue
                result = detect(frame)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)
        elif cmd == "quit":
            break


def main():
    if "--daemon" in sys.argv:
        daemon_mode()
        sys.exit(0)

    if "--test" in sys.argv:
        frame = capture_frame()
        if frame is None:
            print("ERREUR: Camera indisponible")
            sys.exit(1)
        print(f"OK: Frame capturee ({frame.shape[1]}x{frame.shape[0]})")
        sys.exit(0)

    if "--benchmark" in sys.argv:
        frame = capture_frame()
        if frame is None:
            print("ERREUR: Camera indisponible")
            sys.exit(1)
        # Warmup
        detect(frame)
        # Benchmark 5 runs
        times = []
        for _ in range(5):
            t0 = time.time()
            detect(frame)
            times.append((time.time() - t0) * 1000)
        print(f"Benchmark (5 runs): min={min(times):.0f}ms avg={sum(times)/len(times):.0f}ms max={max(times):.0f}ms")
        sys.exit(0)

    debug = "--debug" in sys.argv

    frame = capture_frame()
    if frame is None:
        print(json.dumps({"error": "Camera indisponible"}))
        sys.exit(1)

    result = detect(frame, debug=debug)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
