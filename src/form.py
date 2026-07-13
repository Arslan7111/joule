"""
Per-rep form quality scoring — rule-based, no training required.

Each completed rep gets a 0–100 score with a list of detected issues.
Checks (side-view camera):

  depth        — how close the lowest angle came to the set's typical depth
  tempo        — rep duration outside a healthy range (bouncing / grinding)
  trunk        — excessive forward trunk lean during the rep
  symmetry     — sustained left/right difference in the primary joint pair
  consistency  — rep range of motion shrinking vs the rest of the set

Scores are relative to the person's own set where possible (median-based),
so they tolerate camera perspective the same way the adaptive rep counter does.
"""

import numpy as np

# Penalty weights (points deducted at full severity)
_PENALTY = {
    'depth': 25,
    'tempo': 15,
    'trunk': 25,
    'symmetry': 20,
    'consistency': 15,
}

# Corrective coaching cue per check — actionable phrasing, not diagnosis.
CORRECTIVE_CUES = {
    'depth': "go deeper — control the descent and pause briefly at the bottom",
    'tempo_fast': "slow down — 2s down, 1s up; let the muscle do the work, not momentum",
    'tempo_slow': "keep the rep moving — long grinds under load add strain",
    'trunk': "keep your chest up and core braced — hinge less at the waist",
    'symmetry': "push evenly through both sides — check your stance and grip width",
    'consistency': "range of motion is shrinking — reduce the weight or end the set",
}

TRUNK_LEAN_LIMIT = {          # max acceptable trunk lean (deg) during a rep
    'squat': 55.0, 'lunge': 50.0, 'hinge': 95.0,
    'curl': 25.0, 'press': 25.0, 'pullup': 35.0, 'row': 95.0,
    'unknown': 60.0, 'both': 60.0, 'upper_body': 30.0,
}

TEMPO_MIN_S = 0.8             # faster = bouncing / using momentum
TEMPO_MAX_S = 12.0            # slower = likely a tracking artefact
SYMMETRY_LIMIT_DEG = 18.0     # sustained L/R difference considered asymmetric

_PRIMARY_PAIR = {
    'squat': ('left_knee', 'right_knee'),
    'upper_body': ('left_elbow', 'right_elbow'),
}


def _window(series: list[tuple], t0: float, t1: float) -> list[float]:
    return [v for t, v in series if t0 <= t <= t1]


def score_rep(
    rep: dict,
    angle_series: dict[str, list[tuple]],
    family: str,
    exercise_class: str,
    set_median_rom: float | None,
) -> dict:
    """
    rep: {'timestamp', 'start_timestamp', 'lowest_angle', 'valid'}
    Returns {'score': int, 'issues': [str, ...]}.
    """
    t0, t1 = rep.get('start_timestamp', 0.0), rep['timestamp']
    score = 100.0
    issues: list[str] = []
    fired: list[str] = []          # which checks triggered → corrective cues

    # ── depth ────────────────────────────────────────────────────────────
    if not rep.get('valid', True):
        score -= _PENALTY['depth']
        issues.append('shallow rep — did not reach full depth')
        fired.append('depth')

    # ── tempo ────────────────────────────────────────────────────────────
    dur = t1 - t0
    if 0 < dur < TEMPO_MIN_S:
        score -= _PENALTY['tempo']
        issues.append(f'too fast ({dur:.1f}s) — likely using momentum')
        fired.append('tempo_fast')
    elif dur > TEMPO_MAX_S:
        score -= _PENALTY['tempo'] * 0.5
        issues.append(f'very slow rep ({dur:.1f}s)')
        fired.append('tempo_slow')

    # ── trunk lean ───────────────────────────────────────────────────────
    trunk = _window(angle_series.get('trunk_lean', []), t0, t1)
    if trunk:
        peak = float(np.percentile(trunk, 95))
        limit = TRUNK_LEAN_LIMIT.get(exercise_class,
                                     TRUNK_LEAN_LIMIT.get(family, 60.0))
        if peak > limit:
            severity = min(1.0, (peak - limit) / 25.0)
            score -= _PENALTY['trunk'] * severity
            issues.append(f'excessive trunk lean ({peak:.0f}° vs {limit:.0f}° limit)')
            fired.append('trunk')

    # ── left/right symmetry ──────────────────────────────────────────────
    lj, rj = _PRIMARY_PAIR.get(family, _PRIMARY_PAIR['upper_body'])
    lw = {round(t, 2): v for t, v in angle_series.get(lj, []) if t0 <= t <= t1}
    rw = {round(t, 2): v for t, v in angle_series.get(rj, []) if t0 <= t <= t1}
    common = sorted(set(lw) & set(rw))
    if len(common) >= 5:
        diff = float(np.median([abs(lw[t] - rw[t]) for t in common]))
        if diff > SYMMETRY_LIMIT_DEG:
            severity = min(1.0, (diff - SYMMETRY_LIMIT_DEG) / 20.0)
            score -= _PENALTY['symmetry'] * severity
            issues.append(f'left/right asymmetry (median {diff:.0f}° difference)')
            fired.append('symmetry')

    # ── ROM consistency vs the set ───────────────────────────────────────
    prim = _window(angle_series.get(lj, []), t0, t1) + \
           _window(angle_series.get(rj, []), t0, t1)
    if prim and set_median_rom and set_median_rom > 0:
        rom = max(prim) - min(prim)
        if rom < 0.7 * set_median_rom:
            score -= _PENALTY['consistency']
            issues.append(
                f'range of motion dropped ({rom:.0f}° vs set median {set_median_rom:.0f}°)'
            )
            fired.append('consistency')

    return {
        'score': int(max(0.0, round(score))),
        'issues': issues,
        'cues': [CORRECTIVE_CUES[k] for k in fired],
    }


def score_track_reps(
    reps: list[dict],
    angle_series: dict[str, list[tuple]],
    family: str,
    exercise_class: str = 'unknown',
) -> list[dict]:
    """Score every rep of a track. Mutates nothing; returns list of form dicts
    aligned with `reps`."""
    lj, rj = _PRIMARY_PAIR.get(family, _PRIMARY_PAIR['upper_body'])

    roms = []
    for rep in reps:
        t0, t1 = rep.get('start_timestamp', 0.0), rep['timestamp']
        prim = _window(angle_series.get(lj, []), t0, t1) + \
               _window(angle_series.get(rj, []), t0, t1)
        roms.append(max(prim) - min(prim) if prim else 0.0)
    set_median_rom = float(np.median([r for r in roms if r > 0])) if any(roms) else None

    return [
        score_rep(rep, angle_series, family, exercise_class, set_median_rom)
        for rep in reps
    ]
