import json
from pathlib import Path

from .config import (
    ANGLE_DEFINITIONS,
    EXERCISE_ANGLES,
    LOCOMOTION_MAX_DURATION,
    LOCOMOTION_MAX_INTERVAL,
    LOCOMOTION_MIN_RUN,
    OUTPUT_FPS,
)
from .exercise_classifier import CLASS_FAMILY
from .form import score_track_reps
from .risk import assess_track


def _mark_locomotion(reps: list[dict]) -> None:
    """
    Flag runs of ≥ LOCOMOTION_MIN_RUN consecutive fast, closely-spaced cycles
    as locomotion (walking/running) rather than exercise reps.
    """
    for r in reps:
        r['locomotion'] = False
    run: list[int] = []
    for i, r in enumerate(reps):
        fast = 0 < r['duration'] < LOCOMOTION_MAX_DURATION
        close = (
            i > 0 and
            r['timestamp'] - reps[i - 1]['timestamp'] < LOCOMOTION_MAX_INTERVAL
        )
        if fast and (close or not run):
            run.append(i)
        else:
            if len(run) >= LOCOMOTION_MIN_RUN:
                for j in run:
                    reps[j]['locomotion'] = True
            run = [i] if fast else []
    if len(run) >= LOCOMOTION_MIN_RUN:
        for j in run:
            reps[j]['locomotion'] = True

# All angle keys emitted per track (8 standard + trunk_lean)
_ALL_ANGLES = list(ANGLE_DEFINITIONS.keys()) + ['trunk_lean']


def _downsample_series(entries: list[tuple], target_fps: float) -> list[list]:
    """
    entries: [(timestamp, value), ...]  — already sorted by timestamp.
    Returns [[timestamp, value], ...] sampled at target_fps.
    """
    if not entries:
        return []

    interval = 1.0 / target_fps
    sampled = []
    next_t = entries[0][0]

    for ts, val in entries:
        if ts >= next_t - 1e-9:
            sampled.append([round(ts, 3), round(val, 2) if val is not None else None])
            next_t = ts + interval

    return sampled


def _rep_dicts(sm, angle_series: dict, family: str, exercise_class: str) -> list[dict]:
    """Serialize a state machine's reps with per-rep form scores."""
    reps = [
        {
            'timestamp': r.timestamp,
            'start_timestamp': r.start_timestamp,
            'duration': round(r.duration, 2),
            'lowest_angle': r.lowest_angle,
            'valid': r.valid,
        }
        for r in sm.reps
    ]
    forms = score_track_reps(reps, angle_series, family, exercise_class)
    for rep, form in zip(reps, forms):
        rep['form'] = form
    _mark_locomotion(reps)
    return reps


def build_track_dict(person_id, td: dict, exercise: str = 'both') -> dict:
    """td is a per-person record (state is keyed by Re-ID person, with a
    track-keyed fallback when Re-ID is disabled)."""
    exercise_class = td.get('exercise_class', 'unknown')
    if exercise == 'auto':
        family = CLASS_FAMILY.get(exercise_class, 'both')
    else:
        family = exercise

    rep_counts = {}
    reps = {}
    risk = {}
    if family in ('squat', 'both'):
        reps['squat'] = _rep_dicts(td['squat_sm'], td['angles'], 'squat', exercise_class)
        real = [r for r in reps['squat'] if not r['locomotion']]
        rep_counts['squat'] = len(real)
        risk['squat'] = assess_track(real)
    if family in ('upper_body', 'both'):
        reps['upper_body'] = _rep_dicts(td['upper_sm'], td['angles'], 'upper_body', exercise_class)
        real = [r for r in reps['upper_body'] if not r['locomotion']]
        rep_counts['upper_body'] = len(real)
        risk['upper_body'] = assess_track(real)

    track = {
        'person_id': person_id,
        'person': td.get('person_label') or person_id,
        'track_ids': sorted(td.get('track_ids', [])),
        'total_frames': td['frames'],
        'rep_counts': rep_counts,
        'reps': reps,
        'risk_assessment': risk,
        'angle_series': {
            joint: _downsample_series(td['angles'].get(joint, []), OUTPUT_FPS)
            for joint in _ALL_ANGLES
        },
    }
    if exercise == 'auto':
        track['exercise_class'] = exercise_class
        track['exercise_confidence'] = round(float(td.get('exercise_conf', 0.0)), 3)
    return track


def write_camera_json(
    camera_id: str,
    tracks_data: dict,
    output_dir: str,
    exercise: str = 'both',
) -> dict:
    primary_key = exercise if exercise != 'auto' else 'both'
    camera_result = {
        'station': camera_id,
        'exercise': exercise,
        'primary_angles': EXERCISE_ANGLES.get(primary_key, EXERCISE_ANGLES['both']),
        'tracks': [build_track_dict(pid, td, exercise) for pid, td in tracks_data.items()],
    }
    path = Path(output_dir) / f"{camera_id}.json"
    path.write_text(json.dumps(camera_result, indent=2))
    return camera_result


def write_merged_json(camera_results: list[dict], output_dir: str) -> None:
    merged = {'cameras': camera_results}
    path = Path(output_dir) / 'merged.json'
    path.write_text(json.dumps(merged, indent=2))
