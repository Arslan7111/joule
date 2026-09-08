"""
Train a barbell detector for the equipment-context features (workstream C,
plan `lovely-foraging-firefly.md`). Fine-tunes YOLOv8n (same architecture
family as the existing person detector, src/config.py DETECTOR_MODEL) on a
public barbell dataset.

Data: `computer-vision-1bdzc/barbell-detection-yolov5` v6, Roboflow Universe,
CC BY 4.0, single class ("barbell" — in practice boxes tend to land on one
end/plate-stack of the bar, not a full bar-to-bar span; see the sample review
in validation_results_backround/ for a visual check). ~1,712 source images,
4,149 after Roboflow's own augmentation, single class. Community-sourced, not
studio-clean: a visual spot-check found roughly 1 in 12 images is off-topic
(stock/clipart) rather than real gym footage — acceptable noise for a single-
class detector at this dataset size, not filtered out here.

Not derived from Fit3D or RepCount — this is the one workstream that needed
external data, since neither licensed dataset has barbell annotations.

Usage:
    python tools/train_bar_detector.py
    python tools/train_bar_detector.py --epochs 15 --imgsz 512   # faster/CPU
"""

import argparse
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
DATA_YAML = ROOT / "datasets" / "barbell-yolov5-v6" / "data.yaml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_YAML)
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--fraction", type=float, default=1.0,
                     help="subsample the training set (CPU-time knob)")
    ap.add_argument("--name", default="barbell_yolov8n")
    args = ap.parse_args()

    model = YOLO(str(ROOT / "yolov8n.pt"))
    model.train(
        data=str(args.data), epochs=args.epochs, imgsz=args.imgsz,
        batch=args.batch, patience=args.patience, fraction=args.fraction,
        device="cpu", workers=4,
        project=str(ROOT / "runs" / "detect"), name=args.name, exist_ok=True,
    )
    best = ROOT / "runs" / "detect" / args.name / "weights" / "best.pt"
    print(f"\nbest weights -> {best}")


if __name__ == "__main__":
    main()
