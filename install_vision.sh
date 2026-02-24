#!/bin/bash
# Download YOLOv8n ONNX model for KITT vision module
set -e

MODELS_DIR="$(dirname "$0")/models"
MODEL_PATH="$MODELS_DIR/yolov8n.onnx"

if [ -f "$MODEL_PATH" ]; then
    echo "[OK] Modele deja present: $MODEL_PATH"
    /usr/bin/python3 -c "import cv2; net=cv2.dnn.readNetFromONNX('$MODEL_PATH'); print('[OK] Modele valide')"
    exit 0
fi

echo "[...] Telechargement YOLOv8n ONNX..."
/usr/bin/python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.export(format='onnx', imgsz=640, opset=12)
import shutil
shutil.move('yolov8n.onnx', '$MODEL_PATH')
print('[OK] Modele exporte: $MODEL_PATH')
"

# Verify
/usr/bin/python3 -c "import cv2; net=cv2.dnn.readNetFromONNX('$MODEL_PATH'); print('[OK] Modele verifie avec cv2.dnn')"
echo "[OK] Installation vision terminee"
