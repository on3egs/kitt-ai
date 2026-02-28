#!/usr/bin/env python3
"""
KITT — Fine-tuning Whisper small pour la voix de Manix
A lancer sur Google Colab (GPU T4 gratuit)

Etapes :
  1. Uploade stt_data.zip sur Colab
  2. Colle ce script dans une cellule Colab
  3. Lance toutes les cellules dans l'ordre
  4. Telecharge whisper-kitt-manix/ a la fin
  5. Copie sur le Jetson et convertis avec whisper_convert.py
"""

# ============================================================
# CELLULE 1 — Installation des dependances
# ============================================================
CELL_1 = """
!pip install -q transformers datasets accelerate evaluate jiwer
!pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cu118
"""

# ============================================================
# CELLULE 2 — Upload et extraction des donnees
# ============================================================
CELL_2 = """
from google.colab import files
import zipfile, os

print("Uploade ton fichier stt_data.zip...")
uploaded = files.upload()

with zipfile.ZipFile("stt_data.zip", "r") as z:
    z.extractall(".")

import pandas as pd
df = pd.read_csv("stt_data/metadata.csv")
print(f"Donnees chargees : {len(df)} echantillons")
print(df.head())
"""

# ============================================================
# CELLULE 3 — Preparation du dataset HuggingFace
# ============================================================
CELL_3 = """
import os
import torch
import torchaudio
import pandas as pd
from datasets import Dataset, Audio
from transformers import WhisperProcessor

MODEL_NAME = "openai/whisper-small"
processor = WhisperProcessor.from_pretrained(MODEL_NAME, language="French", task="transcribe")

df = pd.read_csv("stt_data/metadata.csv")
df["audio"] = df["file_name"].apply(lambda f: f"stt_data/{f}")

dataset = Dataset.from_pandas(df)
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

def prepare_batch(batch):
    audio = batch["audio"]
    batch["input_features"] = processor(
        audio["array"],
        sampling_rate=audio["sampling_rate"],
        return_tensors="pt"
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["transcription"]).input_ids
    return batch

dataset = dataset.map(prepare_batch, remove_columns=dataset.column_names)

# Split train/validation 90/10
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
eval_dataset  = split["test"]
print(f"Train: {len(train_dataset)} | Eval: {len(eval_dataset)}")
"""

# ============================================================
# CELLULE 4 — Fine-tuning
# ============================================================
CELL_4 = """
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)
from dataclasses import dataclass
from typing import Any, Dict, List, Union
import torch
import evaluate

MODEL_NAME = "openai/whisper-small"
model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME)
model.config.forced_decoder_ids = None
model.config.suppress_tokens = []

metric = evaluate.load("wer")

def compute_metrics(pred):
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
    pred_str  = processor.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
    wer = 100 * metric.compute(predictions=pred_str, references=label_str)
    return {"wer": wer}

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any
    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]):
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch

data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

training_args = Seq2SeqTrainingArguments(
    output_dir="./whisper-kitt-manix",
    per_device_train_batch_size=8,
    gradient_accumulation_steps=1,
    learning_rate=1e-5,
    warmup_steps=50,
    max_steps=400,
    gradient_checkpointing=True,
    fp16=True,
    evaluation_strategy="steps",
    per_device_eval_batch_size=8,
    predict_with_generate=True,
    generation_max_length=225,
    save_steps=100,
    eval_steps=100,
    logging_steps=25,
    report_to=["tensorboard"],
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    push_to_hub=False,
)

trainer = Seq2SeqTrainer(
    args=training_args,
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    tokenizer=processor.feature_extractor,
)

print("Lancement du fine-tuning...")
trainer.train()
print("Fine-tuning termine !")
trainer.save_model("./whisper-kitt-manix")
processor.save_pretrained("./whisper-kitt-manix")
print("Modele sauvegarde dans ./whisper-kitt-manix/")
"""

# ============================================================
# CELLULE 5 — Telecharger le modele fine-tune
# ============================================================
CELL_5 = """
import shutil
from google.colab import files

shutil.make_archive("whisper-kitt-manix", "zip", ".", "whisper-kitt-manix")
files.download("whisper-kitt-manix.zip")
print("Telecharge whisper-kitt-manix.zip et copie-le sur le Jetson.")
print("Puis lance : python3 whisper_convert.py")
"""

# ============================================================
# AFFICHAGE DES CELLULES
# ============================================================
if __name__ == "__main__":
    cells = [
        ("Installation dependances", CELL_1),
        ("Upload et extraction donnees", CELL_2),
        ("Preparation dataset HuggingFace", CELL_3),
        ("Fine-tuning Whisper small", CELL_4),
        ("Telecharger le modele", CELL_5),
    ]
    print("=" * 60)
    print("  KITT — Notebook Google Colab Fine-tuning Whisper")
    print("=" * 60)
    print("\nCopie chaque cellule dans Google Colab dans l'ordre.\n")
    for i, (title, code) in enumerate(cells, 1):
        print(f"\n{'='*60}")
        print(f"  CELLULE {i} — {title}")
        print(f"{'='*60}")
        print(code)
