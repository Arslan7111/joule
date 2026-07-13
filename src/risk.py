"""
Session-level injury-risk signals from rep sequence trends.

Single-camera scope: these are training-load and fatigue indicators derived
from patterns across a set, not medical diagnoses.  Frontal-plane risks
(knee valgus, hip shift) require additional camera angles and are out of
scope until the multi-camera setup exists.

Signals:

  fatigue_form_decline   — form scores trending sharply down across the set
  rom_degradation        — later reps noticeably shallower than early reps
  tempo_collapse         — reps getting fast/bouncy as the set progresses
  chronic_asymmetry      — one-sided loading in most reps (compensation risk)

Risk level: low → moderate → high, from the number and severity of signals.
"""

import numpy as np

MIN_REPS_FOR_ASSESSMENT = 4

FORM_DECLINE_LIMIT = 15.0       # pts drop, first-third vs last-third mean
ROM_DEGRADATION_RATIO = 0.75    # late-rep median ROM below this × early median
TEMPO_FAST_S = 0.8
TEMPO_COLLAPSE_FRACTION = 0.5   # ≥ this fraction of late reps too fast
ASYMMETRY_FRACTION = 0.6        # ≥ this fraction of reps flagged asymmetric


def assess_track(reps: list[dict]) -> dict:
    """
    reps: serialized reps (with 'form', 'duration', 'lowest_angle') in order.
    Returns {'risk_level', 'signals': [{'signal', 'detail'}, ...]}.
    """
    if len(reps) < MIN_REPS_FOR_ASSESSMENT:
        return {
            'risk_level': 'low',
            'signals': [],
            'note': f'fewer than {MIN_REPS_FOR_ASSESSMENT} reps — not enough data',
        }

    signals: list[dict] = []
    n = len(reps)
    third = max(1, n // 3)
    early, late = reps[:third], reps[-third:]

    # ── fatigue: form score decline ──────────────────────────────────────
    early_form = float(np.mean([r['form']['score'] for r in early]))
    late_form = float(np.mean([r['form']['score'] for r in late]))
    drop = early_form - late_form
    if drop >= FORM_DECLINE_LIMIT:
        signals.append({
            'signal': 'fatigue_form_decline',
            'detail': f'form fell from {early_form:.0f} to {late_form:.0f} across the set',
        })

    # ── ROM degradation: lowest angle rising (not going as deep) ────────
    early_low = float(np.median([r['lowest_angle'] for r in early]))
    late_low = float(np.median([r['lowest_angle'] for r in late]))
    early_depth = max(1.0, 180.0 - early_low)      # depth achieved from full extension
    late_depth = 180.0 - late_low
    if late_depth < ROM_DEGRADATION_RATIO * early_depth:
        signals.append({
            'signal': 'rom_degradation',
            'detail': f'depth shrank — lowest angle rose from {early_low:.0f}° to {late_low:.0f}°',
        })

    # ── tempo collapse: late reps bouncy ─────────────────────────────────
    late_fast = sum(1 for r in late if 0 < r.get('duration', 0) < TEMPO_FAST_S)
    if late_fast / len(late) >= TEMPO_COLLAPSE_FRACTION:
        signals.append({
            'signal': 'tempo_collapse',
            'detail': f'{late_fast}/{len(late)} of the final reps were faster than '
                      f'{TEMPO_FAST_S}s — control is degrading',
        })

    # ── chronic asymmetry ────────────────────────────────────────────────
    asym = sum(
        1 for r in reps
        if any('asymmetry' in i for i in r['form'].get('issues', []))
    )
    if asym / n >= ASYMMETRY_FRACTION:
        signals.append({
            'signal': 'chronic_asymmetry',
            'detail': f'{asym}/{n} reps loaded one side harder — possible '
                      f'compensation pattern worth checking',
        })

    level = 'low'
    if len(signals) >= 3:
        level = 'high'
    elif len(signals) >= 1:
        level = 'moderate'

    return {'risk_level': level, 'signals': signals}
