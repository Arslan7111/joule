"""
Motion features extracted from joint-angle time series.

Used by the exercise classifier (heuristic and trained) and reusable for any
downstream analysis.  A feature vector is computed over a window of the
angle series — either a rolling window during live processing or a whole
track for post-hoc classification.
"""

import numpy as np

from .config import ANGLE_DEFINITIONS

ALL_ANGLE_KEYS = list(ANGLE_DEFINITIONS.keys()) + ['trunk_lean']

# Per joint: range of motion (p90-p10), mean position, mean absolute velocity.
# Plus cross-joint features appended at the end.
FEATURE_NAMES = [
    f"{joint}_{stat}"
    for joint in ALL_ANGLE_KEYS
    for stat in ('rom', 'mean', 'vel')
] + ['knee_freq']


def _cycle_frequency(entries: list[tuple], delta: float = 12.0, k: int = 7) -> float:
    """
    Oscillation frequency (Hz) of one joint series: rolling-median smoothed,
    then median crossings counted with ±delta hysteresis.  Raw crossings
    without smoothing read keypoint flicker as oscillation (measured 2.7 Hz
    on a 0.3 Hz squat set); this version measured 0.2–0.35 Hz on squats vs
    0.79 Hz on a treadmill.
    """
    if len(entries) < 20:
        return 0.0
    arr = np.asarray(sorted(entries), dtype=np.float64)
    t, v = arr[:, 0], arr[:, 1]
    span = t[-1] - t[0]
    if span < 2.0 or np.std(v) < 3.0:
        return 0.0
    half = k // 2
    v = np.array([np.median(v[max(0, i - half):i + half + 1]) for i in range(len(v))])
    med = np.median(v)
    state, crossings = 0, 0
    for x in v:
        if x > med + delta:
            if state == -1:
                crossings += 1
            state = 1
        elif x < med - delta:
            state = -1
    return crossings / span


def _series_stats(entries: list[tuple]) -> tuple[float, float, float]:
    """entries: [(timestamp, angle), ...] → (rom, mean, mean_abs_velocity)."""
    if len(entries) < 4:
        return 0.0, 0.0, 0.0
    arr = np.asarray(entries, dtype=np.float64)
    t, v = arr[:, 0], arr[:, 1]
    rom = float(np.percentile(v, 90) - np.percentile(v, 10))
    mean = float(np.mean(v))
    dt = np.diff(t)
    good = dt > 1e-6
    vel = float(np.mean(np.abs(np.diff(v)[good] / dt[good]))) if good.any() else 0.0
    return rom, mean, vel


def extract_features(
    angle_series: dict[str, list[tuple]],
    t_start: float | None = None,
    t_end: float | None = None,
) -> np.ndarray:
    """
    angle_series: {joint: [(timestamp, angle), ...]} — as stored per track.
    Optional [t_start, t_end] restricts to a window.

    Returns a float64 vector aligned with FEATURE_NAMES.
    """
    lo = t_start if t_start is not None else -np.inf
    hi = t_end if t_end is not None else np.inf

    def window(joint: str) -> list[tuple]:
        entries = angle_series.get(joint, [])
        if t_start is None and t_end is None:
            return entries
        return [(t, v) for t, v in entries if lo <= t <= hi]

    feats = []
    for joint in ALL_ANGLE_KEYS:
        feats.extend(_series_stats(window(joint)))

    # Cross-joint: knee oscillation frequency from the best-observed knee.
    # (Merging both knees interleaves two different signals and fakes
    # high-frequency oscillation — measure one side only.)
    lk, rk = window('left_knee'), window('right_knee')
    best_knee = lk if len(lk) >= len(rk) else rk
    feats.append(_cycle_frequency(best_knee))

    return np.array(feats, dtype=np.float64)


def feature_dict(vector: np.ndarray) -> dict[str, float]:
    """Vector → named dict, for readability in logs and debugging."""
    return {name: round(float(v), 2) for name, v in zip(FEATURE_NAMES, vector)}
