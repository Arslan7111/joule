"""
Exercise classification from joint-angle motion features.

Two tiers:

1. Heuristic rules (default) — biomechanical thresholds on range of motion.
   Works with zero training data.
2. Trained model — multinomial logistic regression (pure NumPy, trained by
   tools/train_classifier.py).  If  models/exercise_clf.npz  exists it is
   loaded automatically and takes precedence over the heuristics.

Classes and their rep-counting family:

    squat, lunge, hinge (deadlift/RDL)      → 'squat'      (knee/hip driven)
    curl, press, pullup, row                → 'upper_body' (elbow driven)
    unknown                                 → 'both'
"""

import logging
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES, extract_features

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / 'models' / 'exercise_clf.npz'

CLASSES = ['squat', 'lunge', 'hinge', 'curl', 'press', 'pullup', 'row',
           'pushup', 'raise', 'situp', 'cardio', 'unknown']

# Which rep state machine drives the count for each class.
# 'none' = no rep counting (locomotion/cardio is not a rep exercise;
# sit-ups are hip-driven — honest 'none' until a hip counter exists).
CLASS_FAMILY = {
    'squat': 'squat', 'lunge': 'squat', 'hinge': 'squat',
    'curl': 'upper_body', 'press': 'upper_body',
    'pullup': 'upper_body', 'row': 'upper_body',
    'pushup': 'upper_body', 'raise': 'upper_body',
    'situp': 'none',
    'cardio': 'none',
    'unknown': 'both',
}

_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def _f(vec: np.ndarray, name: str) -> float:
    return float(vec[_IDX[name]])


def classify_heuristic(vec: np.ndarray) -> str:
    """
    Rule-based classification from a feature vector.  Thresholds assume a
    roughly side-on camera; they only compare relative motion between joints,
    so they tolerate perspective compression.
    """
    knee = max(_f(vec, 'left_knee_rom'), _f(vec, 'right_knee_rom'))
    hip = max(_f(vec, 'left_hip_rom'), _f(vec, 'right_hip_rom'))
    elbow = max(_f(vec, 'left_elbow_rom'), _f(vec, 'right_elbow_rom'))
    shoulder = max(_f(vec, 'left_shoulder_rom'), _f(vec, 'right_shoulder_rom'))
    trunk_rom = _f(vec, 'trunk_lean_rom')
    trunk_mean = _f(vec, 'trunk_lean_mean')
    knee_freq = _f(vec, 'knee_freq')

    lower_active = knee > 25 or hip > 25
    upper_active = elbow > 25 or shoulder > 25

    # Gait check first: walking/running cycles knees faster than squat sets
    # (measured: treadmill 0.79 Hz vs barbell squats 0.2–0.35 Hz on the
    # smoothed-hysteresis measure — threshold sits mid-gap).  Very fast
    # bodyweight squat sets may approach this from below; the trained
    # classifier should own this boundary once real footage is labelled.
    if lower_active and knee_freq >= 0.6:
        return 'cardio'

    # NOTE: a lying-posture rule (trunk_mean ≥ 65 → bench press) was tried
    # and reverted: RepCount bench-press videos are shot from the head/foot
    # of the bench, so the foreshortened 2D trunk reads *upright* (measured
    # 6–22°) while the bent legs fake large knee ROM.  Lying exercises are
    # not separable by trunk thresholds across viewpoints — the trained
    # classifier owns them.
    if lower_active and (knee >= hip * 0.6 or knee > 40):
        # Knee-dominant lower-body movement.  (Lunge is only distinguishable
        # by the trained classifier — side-view occlusion makes the
        # left/right ROM asymmetry heuristic unreliable.)
        return 'squat'

    if lower_active and hip > 30 and knee < 25:
        return 'hinge'              # hip hinge with stiff knees (deadlift/RDL)

    if upper_active:
        if shoulder > 45 and elbow > 30:
            return 'press' if trunk_mean < 25 else 'pullup'
        if elbow > 35 and trunk_mean > 30:
            return 'row'            # bent-over torso + elbow drive
        if elbow > 35:
            return 'curl'
        return 'press'

    return 'unknown'


class ExerciseClassifier:
    """Classifies exercise from an angle-series window. Uses the trained
    model when available, heuristics otherwise."""

    def __init__(self) -> None:
        self._W = None            # (n_classes, n_features)
        self._b = None
        self._mu = None           # feature standardisation
        self._sigma = None
        self._classes: list[str] = []

        if MODEL_PATH.exists():
            try:
                data = np.load(MODEL_PATH, allow_pickle=False)
                self._W, self._b = data['W'], data['b']
                self._mu, self._sigma = data['mu'], data['sigma']
                self._classes = [c for c in data['classes'].tolist()]
                logger.info(
                    f"ExerciseClassifier: trained model loaded "
                    f"({len(self._classes)} classes: {', '.join(self._classes)})"
                )
            except Exception:
                logger.exception("Failed to load trained classifier — using heuristics")
                self._W = None

        if self._W is None:
            logger.info("ExerciseClassifier: heuristic rules (no trained model found)")

    @property
    def is_trained(self) -> bool:
        return self._W is not None

    def classify(
        self,
        angle_series: dict[str, list[tuple]],
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> tuple[str, float]:
        """Returns (class_name, confidence 0-1)."""
        vec = extract_features(angle_series, t_start, t_end)
        if not np.any(vec):
            return 'unknown', 0.0

        if self._W is not None:
            z = (vec - self._mu) / self._sigma
            logits = self._W @ z + self._b
            logits -= logits.max()
            p = np.exp(logits)
            p /= p.sum()
            i = int(np.argmax(p))
            return self._classes[i], float(p[i])

        return classify_heuristic(vec), 0.5   # heuristics carry fixed confidence

    def family(self, class_name: str) -> str:
        """Map an exercise class to its rep-counting family."""
        return CLASS_FAMILY.get(class_name, 'both')
