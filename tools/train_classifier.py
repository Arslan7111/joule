"""
Train the exercise classifier from labelled pipeline outputs.

Data layout — one folder per exercise class, containing result JSONs
produced by pipeline.py runs of footage showing that exercise:

    training_data/
        squat/rack1_monday.json
        squat/rack2.json
        curl/db_area.json
        press/bench.json
        ...

Folder names must be classes from src.exercise_classifier.CLASSES
(squat, lunge, hinge, curl, press, pullup, row).

Usage:
    python tools/train_classifier.py training_data/

Each track in each JSON is cut into sliding windows (6 s, stride 2 s); every
window becomes one training sample.  The model is multinomial logistic
regression (pure NumPy) saved to models/exercise_clf.npz — the pipeline
loads it automatically on the next run.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exercise_classifier import CLASSES, MODEL_PATH          # noqa: E402
from src.features import FEATURE_NAMES, extract_features         # noqa: E402

WINDOW_S = 6.0
STRIDE_S = 2.0


def _windows_from_track(track: dict) -> list[np.ndarray]:
    series = {
        joint: [(t, v) for t, v in entries if v is not None]
        for joint, entries in track.get('angle_series', {}).items()
    }
    all_ts = [t for entries in series.values() for t, _ in entries]
    if not all_ts:
        return []
    t_min, t_max = min(all_ts), max(all_ts)

    samples = []
    t = t_min
    while t + WINDOW_S <= t_max + 1e-9:
        vec = extract_features(series, t, t + WINDOW_S)
        if np.any(vec):
            samples.append(vec)
        t += STRIDE_S
    return samples


def load_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    X, y, classes = [], [], []
    for class_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        label = class_dir.name
        if label not in CLASSES:
            print(f"  skipping '{label}/' — not a known class {CLASSES}")
            continue
        n_before = len(X)
        for jf in sorted(class_dir.glob('*.json')):
            data = json.loads(jf.read_text())
            tracks = data.get('tracks', [])
            for cam in data.get('cameras', [data]):     # accept merged.json too
                tracks = cam.get('tracks', tracks)
                for track in tracks:
                    for vec in _windows_from_track(track):
                        X.append(vec)
                        y.append(label)
        n = len(X) - n_before
        print(f"  {label:8s}: {n} window samples")
        if n > 0 and label not in classes:
            classes.append(label)
    if not X:
        raise SystemExit("No training samples found — check the data layout.")
    return np.array(X), np.array(y), classes


def train_logreg(
    X: np.ndarray, y: np.ndarray, classes: list[str],
    lr: float = 0.1, epochs: int = 800, l2: float = 1e-3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma < 1e-9] = 1.0
    Z = (X - mu) / sigma

    n, d = Z.shape
    k = len(classes)
    Y = np.zeros((n, k))
    for i, label in enumerate(y):
        Y[i, classes.index(label)] = 1.0

    W = np.zeros((k, d))
    b = np.zeros(k)
    for epoch in range(epochs):
        logits = Z @ W.T + b
        logits -= logits.max(axis=1, keepdims=True)
        P = np.exp(logits)
        P /= P.sum(axis=1, keepdims=True)
        G = (P - Y) / n                       # (n, k)
        W -= lr * (G.T @ Z + l2 * W)
        b -= lr * G.sum(axis=0)
    return W, b, mu, sigma


def evaluate(W, b, mu, sigma, X, y, classes) -> float:
    Z = (X - mu) / sigma
    pred = np.argmax(Z @ W.T + b, axis=1)
    truth = np.array([classes.index(label) for label in y])
    return float(np.mean(pred == truth))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('data_dir', help='Directory of <class>/<result>.json files')
    parser.add_argument('--holdout', type=float, default=0.2,
                        help='Fraction held out for validation (default 0.2)')
    args = parser.parse_args()

    print(f"Loading dataset from {args.data_dir} …")
    X, y, classes = load_dataset(Path(args.data_dir))
    print(f"Total: {len(X)} samples, {len(classes)} classes, "
          f"{len(FEATURE_NAMES)} features")

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(X))
    n_val = max(1, int(len(X) * args.holdout)) if len(X) > 5 else 0
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    W, b, mu, sigma = train_logreg(X[train_idx], y[train_idx], classes)

    train_acc = evaluate(W, b, mu, sigma, X[train_idx], y[train_idx], classes)
    print(f"Train accuracy: {train_acc:.1%}")
    if n_val:
        val_acc = evaluate(W, b, mu, sigma, X[val_idx], y[val_idx], classes)
        print(f"Validation accuracy: {val_acc:.1%}  ({n_val} samples)")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        MODEL_PATH,
        W=W, b=b, mu=mu, sigma=sigma,
        classes=np.array(classes),
        feature_names=np.array(FEATURE_NAMES),
    )
    print(f"Model saved → {MODEL_PATH}")
    print("The pipeline will load it automatically on the next run.")


if __name__ == '__main__':
    main()
