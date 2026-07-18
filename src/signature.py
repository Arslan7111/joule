"""
Exercise signatures: reference-based form comparison (AIFit-style).

Two ideas adapted from Fieraru et al., "AIFit" (CVPR 2021):

  1. Active/passive angle mining — for a given exercise, the joints that
     carry the motion energy (knees in a squat) are found automatically by
     ranking each angle's total trajectory energy and cutting the ranking at
     its largest margin.  Active angles define the movement; passive angles
     are form constraints that should stay still.

  2. Reference signatures — a rep is summarised by statistics chosen per
     category (active: min/max reached + left/right synchrony; passive:
     mean position + wobble).  A reference signature built from good
     executions (a trainer's set) gives per-entry tolerances; a trainee rep
     is scored by which entries deviate beyond tolerance, scaled by a
     "critic" strictness parameter (0 = harsh, 1 = relaxed).

This complements the rule-based checks in form.py: rules work out of the
box, references sharpen scoring once good executions have been recorded
(tools/build_reference.py).
"""

import json
from itertools import combinations
from pathlib import Path

import numpy as np

from .config import CRITIC_DELTA, REFERENCE_DIR

# Minimum tolerance per entry kind, degrees (correlation entries are unitless).
# Guards against a metronomic reference (tiny std) flagging everything.
_TOL_FLOOR_DEG = 6.0
_TOL_FLOOR_CORR = 0.15
_TOL_STD_MULT = 2.0          # tolerance = max(mult * reference std, floor)

# Deviations are also graded against this span for severity 0→1
_SEVERITY_SPAN_DEG = 20.0
_SEVERITY_SPAN_CORR = 0.4


def _window(series: list[tuple], t0: float, t1: float) -> list[tuple]:
    return [(t, v) for t, v in series if v is not None and t0 <= t <= t1]


def _median_filter(vals: np.ndarray, k: int = 5) -> np.ndarray:
    half = k // 2
    return np.array([
        np.median(vals[max(0, i - half):i + half + 1]) for i in range(len(vals))
    ])


def angle_energies(
    angle_series: dict[str, list[tuple]],
    t0: float = -np.inf,
    t1: float = np.inf,
) -> dict[str, float]:
    """Total trajectory energy Σ|Δθ| per angle over [t0, t1] (AIFit eq. 7).

    Each series is median-filtered first: AIFit mined energy from clean
    mocap, but 2D keypoint jitter also produces Σ|Δθ| — unsmoothed, a noisy
    elbow outranks the slow big-range knees on a squat (measured on
    RepCount footage: elbows mined as the active joints of a squat).
    """
    energies = {}
    for joint, series in angle_series.items():
        vals = np.asarray([v for _, v in _window(series, t0, t1)], dtype=np.float64)
        if len(vals) >= 4:
            energies[joint] = float(np.sum(np.abs(np.diff(_median_filter(vals)))))
    return energies


def split_active_passive(energies: dict[str, float]) -> tuple[list[str], list[str]]:
    """Cut the descending energy ranking at its largest margin: everything
    above the cut is active (drives the movement), the rest passive."""
    if len(energies) < 2:
        return list(energies), []
    ranked = sorted(energies, key=energies.get, reverse=True)
    gaps = [energies[a] - energies[b] for a, b in zip(ranked, ranked[1:])]
    cut = int(np.argmax(gaps)) + 1
    return ranked[:cut], ranked[cut:]


def _pair_correlation(sa: list[tuple], sb: list[tuple]) -> float | None:
    """Correlation of two angle series over their common timestamps."""
    da = {round(t, 2): v for t, v in sa}
    db = {round(t, 2): v for t, v in sb}
    common = sorted(set(da) & set(db))
    if len(common) < 5:
        return None
    va = np.array([da[t] for t in common])
    vb = np.array([db[t] for t in common])
    if np.std(va) < 1e-6 or np.std(vb) < 1e-6:
        return None
    return float(np.corrcoef(va, vb)[0, 1])


def rep_signature(
    angle_series: dict[str, list[tuple]],
    t0: float,
    t1: float,
    active: list[str],
    passive: list[str],
) -> dict[str, float]:
    """One rep → {entry: value}. Active angles: min/max (+ pairwise
    correlation for left/right pairs); passive angles: mean/std."""
    sig: dict[str, float] = {}
    for joint in active:
        vals = [v for _, v in _window(angle_series.get(joint, []), t0, t1)]
        if len(vals) >= 4:
            sig[f'{joint}:min'] = float(np.min(vals))
            sig[f'{joint}:max'] = float(np.max(vals))
    for a, b in combinations(sorted(active), 2):
        # Only mirror pairs — cross-joint phase differs by exercise style
        if a.replace('left', '') != b.replace('right', ''):
            continue
        corr = _pair_correlation(
            _window(angle_series.get(a, []), t0, t1),
            _window(angle_series.get(b, []), t0, t1),
        )
        if corr is not None:
            sig[f'{a}~{b}:corr'] = corr
    for joint in passive:
        vals = [v for _, v in _window(angle_series.get(joint, []), t0, t1)]
        if len(vals) >= 4:
            sig[f'{joint}:mean'] = float(np.mean(vals))
            sig[f'{joint}:std'] = float(np.std(vals))
    return sig


def build_reference(
    recordings: list[tuple[dict[str, list[tuple]], list[tuple[float, float]]]],
    exercise: str,
    must_active: list[str] | None = None,
) -> dict:
    """Reference signature from good executions.

    recordings: [(angle_series, [(rep_t0, rep_t1), ...]), ...] — one entry
    per recorded set.  The active/passive split is mined from the summed
    energy over every set, then per-entry mean/std across all reps.

    must_active: joints guaranteed to end up active regardless of mining.
    Unlike AIFit we know the exercise class, so its primary joints can be
    pinned; mining then only *adds* whatever else the reference execution
    moves (measured on RepCount squats: arm swing often out-energies the
    knees, which would have put the knees in the passive set).
    """
    n_reps = sum(len(w) for _, w in recordings)
    if n_reps == 0:
        raise ValueError('no reps to build a reference from')

    combined: dict[str, float] = {}
    for series, windows in recordings:
        if not windows:
            continue
        t0 = min(w[0] for w in windows)
        t1 = max(w[1] for w in windows)
        for joint, e in angle_energies(series, t0, t1).items():
            combined[joint] = combined.get(joint, 0.0) + e
    active, passive = split_active_passive(combined)
    for joint in must_active or []:
        if joint in passive:
            passive.remove(joint)
            active.append(joint)

    per_entry: dict[str, list[float]] = {}
    for series, windows in recordings:
        for w0, w1 in windows:
            for entry, val in rep_signature(series, w0, w1, active, passive).items():
                per_entry.setdefault(entry, []).append(val)

    return {
        'exercise': exercise,
        'active': active,
        'passive': passive,
        'n_reps': n_reps,
        'entries': {
            entry: {'mean': float(np.mean(vals)), 'std': float(np.std(vals))}
            for entry, vals in per_entry.items()
            if len(vals) >= max(2, n_reps // 2)
        },
    }


def _entry_phrase(entry: str, diff: float) -> str:
    """One deviation → a coaching phrase (AIFit-style grammar, simplified)."""
    name, stat = entry.rsplit(':', 1)
    if stat == 'corr':
        a, b = name.split('~')
        pair = a.replace('left_', '').replace('_', ' ')
        return f"left and right {pair} are out of sync with each other"
    joint = name.replace('_', ' ')
    mag = f"{abs(diff):.0f}°"
    if stat == 'min':
        return (f"{joint} not closing enough at the bottom ({mag} short of reference)"
                if diff > 0 else
                f"{joint} closing {mag} further than reference — control the bottom")
    if stat == 'max':
        return (f"extend the {joint} more at the top ({mag} short of reference)"
                if diff < 0 else
                f"{joint} over-extending by {mag} at the top")
    if stat == 'mean':
        return f"keep your {joint} closer to the reference position ({mag} off)"
    return f"keep your {joint} steadier — moving {mag} more than reference"


def compare_to_reference(
    angle_series: dict[str, list[tuple]],
    t0: float,
    t1: float,
    reference: dict,
    critic: float = CRITIC_DELTA,
) -> list[dict]:
    """Score one rep window against a reference signature.

    Returns deviations beyond tolerance, worst first:
    [{'entry', 'value', 'reference', 'deviation', 'severity', 'cue'}, ...]
    critic ∈ [0, 1] scales every tolerance: 0 harsh, 1 relaxed (AIFit's δ).
    """
    sig = rep_signature(angle_series, t0, t1,
                        reference['active'], reference['passive'])
    scale = 0.5 + 1.5 * float(np.clip(critic, 0.0, 1.0))

    deviations = []
    for entry, val in sig.items():
        ref = reference['entries'].get(entry)
        if ref is None:
            continue
        is_corr = entry.endswith(':corr')
        floor = _TOL_FLOOR_CORR if is_corr else _TOL_FLOOR_DEG
        span = _SEVERITY_SPAN_CORR if is_corr else _SEVERITY_SPAN_DEG
        tol = max(_TOL_STD_MULT * ref['std'], floor) * scale
        diff = val - ref['mean']
        if is_corr and diff > 0:      # more synchronous than reference is fine
            continue
        if abs(diff) <= tol:
            continue
        deviations.append({
            'entry': entry,
            'value': round(val, 1),
            'reference': round(ref['mean'], 1),
            'deviation': round(diff, 1),
            'severity': round(min(1.0, (abs(diff) - tol) / span), 2),
            'cue': _entry_phrase(entry, diff),
        })
    return sorted(deviations, key=lambda d: d['severity'], reverse=True)


# ── reference file loading ──────────────────────────────────────────────────

_ref_cache: dict[str, dict | None] = {}


def load_reference(exercise_class: str) -> dict | None:
    """models/references/<exercise>.json, cached; None when absent."""
    if exercise_class not in _ref_cache:
        path = Path(REFERENCE_DIR) / f'{exercise_class}.json'
        _ref_cache[exercise_class] = (
            json.loads(path.read_text()) if path.exists() else None
        )
    return _ref_cache[exercise_class]
