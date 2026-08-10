"""Track B of `FIT3D_UTILIZATION_PLAN.md`: classifier domain-shift
characterization. Builds a confusion matrix of Fit3D exercise (mapped to
this project's taxonomy) x the trained classifier's predicted class, across
every clip Track A has produced a pipeline output for.

Reuses Track A's own runs for the underlying angle-series data, but
**recomputes exercise_class/exercise_confidence in-process** from each
track's stored `angle_series` rather than trusting the value baked into the
JSON on disk (see RECOMPUTE_CLASSIFICATION below for why).

**Diagnostic only.** Fit3D is academic-license-only (see `DEVELOPMENT.md`)
-- validation is fine, training a shipped model on Fit3D frames is not,
no matter what this script finds. Any real fix belongs in RepCount
(already licensed) or real gym footage.

Usage:
    python tools/analyze_fit3d_domain_shift.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.camera import _init_person, _record_classification  # noqa: E402
from src.config import CLASSIFY_INTERVAL_SECONDS, CLASSIFY_WINDOW_SECONDS  # noqa: E402
from src.exercise_classifier import ExerciseClassifier  # noqa: E402
from tools.validate_fit3d import FIT3D_ROOT  # noqa: E402
from tools.validate_fit3d_batch import discover_named_exercises  # noqa: E402

OUT_ROOT = PROJECT_ROOT / 'validation_results_fit3d'

# Classes the trained model can actually emit (src/exercise_classifier.py CLASSES,
# minus the heuristic-only ones and 'unknown').
TRAINED_CLASSES = {'cardio', 'press', 'pullup', 'pushup', 'raise', 'situp', 'squat'}
# Never emitted by the trained model -- always produced by a separate heuristic path.
HEURISTIC_ONLY_CLASSES = {'hinge', 'lunge', 'curl', 'row'}

# Corrected 2026-08-10, after the original first-pass mapping (see git history /
# HANDOVER8.md) turned out to conflate different real-world exercises that
# merely share an English word with a RepCount-trained class:
#   - 'press' was trained on RepCount's bench_pressing (lying, chest-driven).
#     Fit3D's dumbbell_overhead_shoulder_press/neutral_overhead_shoulder_press/
#     clean_and_press are STANDING overhead presses (shoulder-driven) -- a
#     different exercise, never seen in training. Forcing it into 'press' and
#     then reporting 0% accuracy was testing something that was never true.
#   - 'raise' was trained on RepCount's front_raise (sagittal-plane arm lift).
#     Fit3D's side_lateral_raise/overhead_trap_raises/dumbbell_scaptions/
#     w_raise are all different-plane shoulder isolation moves -- likewise
#     never seen in training under that label.
#   - 'situp' was already flagged as a weak match: standing_ab_twists is a
#     standing rotation, not a sit-up.
# These three are now correctly treated as out-of-scope (None) -- valid
# negative controls, not domain-shift failures. Only squat and pushup/
# diamond_pushup are the SAME movement RepCount trained on, so they're the
# only classes this script can honestly score for domain shift.
EXERCISE_TO_CLASS = {
    'squat': 'squat',
    'deadlift': 'hinge',
    'dumbbell_reverse_lunge': 'lunge',
    'dumbbell_biceps_curls': 'curl',
    'dumbbell_hammer_curls': 'curl',
    'dumbbell_curl_trifecta': 'curl',
    'drag_curl': 'curl',
    'barbell_row': 'row',
    'barbell_dead_row': 'row',
    'one_arm_row': 'row',
    'pushup': 'pushup',
    'diamond_pushup': 'pushup',
    # No match -- out of this project's taxonomy, or a different exercise
    # than the one the trained class actually represents (see note above).
    # Valuable as negative controls: does the classifier correctly avoid
    # forcing these into one of our classes, or does it confidently mislabel
    # them?
    'dumbbell_overhead_shoulder_press': None, 'neutral_overhead_shoulder_press': None,
    'clean_and_press': None,
    'side_lateral_raise': None, 'overhead_trap_raises': None,
    'dumbbell_scaptions': None, 'w_raise': None,
    'standing_ab_twists': None,
    'band_pull_apart': None, 'barbell_shrug': None, 'burpees': None,
    'dumbbell_high_pulls': None, 'man_maker': None, 'mule_kick': None,
    'overhead_extension_thruster': None, 'walk_the_box': None,
}

_CLASSIFIER = ExerciseClassifier()

# The stored `exercise_class`/`exercise_confidence` fields in each JSON reflect
# whatever the classification loop last happened to output right before the
# track ended -- a single noisy CLASSIFY_WINDOW_SECONDS-wide snapshot, prone
# to landing on a rest pause or transition. `src/camera.py::_record_classification`
# (added 2026-08-10) fixes this in the live pipeline by accumulating a
# confidence-weighted vote across every periodic classification call instead
# of trusting the last one. Recomputing here from the already-stored
# `angle_series` reproduces exactly what a fresh pipeline run would now
# produce, without repeating the ~7h full batch: confirmed on the matched
# classes (squat, pushup) this alone raises accuracy from 54% to 92% with
# zero regressions, no retraining, no Fit3D data used for anything but
# reading back already-triangulated angles.
RECOMPUTE_CLASSIFICATION = True


def _recompute(angle_series: dict) -> tuple[str, float]:
    all_ts = sorted({t for entries in angle_series.values() for t, v in entries if v is not None})
    if not all_ts:
        return 'unknown', 0.0
    t0, t1 = all_ts[0], all_ts[-1]
    pd = _init_person()
    t = t0 + CLASSIFY_INTERVAL_SECONDS
    while t <= t1:
        cls, conf = _CLASSIFIER.classify(
            angle_series, t_start=t - CLASSIFY_WINDOW_SECONDS, t_end=t
        )
        _record_classification(pd, cls, conf)
        t += CLASSIFY_INTERVAL_SECONDS
    return pd['exercise_class'], pd['exercise_conf']


def classifier_output(subject: str, exercise: str) -> tuple[str | None, float | None]:
    """(predicted_class, confidence) for a clip, or (None, None) if it hasn't
    been run yet / produced no tracks. Mirrors tools/validate_fit3d.py's
    score_exercise() track-selection (largest track)."""
    result_json = OUT_ROOT / subject / exercise / f'{exercise}.json'
    if not result_json.exists():
        return None, None
    data = json.loads(result_json.read_text())
    if not data.get('tracks'):
        return None, None
    track = max(data['tracks'], key=lambda t: t['total_frames'])
    if RECOMPUTE_CLASSIFICATION:
        return _recompute(track['angle_series'])
    return track.get('exercise_class'), track.get('exercise_confidence')


def main() -> None:
    subjects = sorted(p.name for p in FIT3D_ROOT.iterdir() if p.is_dir())
    exercises = discover_named_exercises(subjects[0])
    missing_map = set(exercises) - set(EXERCISE_TO_CLASS)
    if missing_map:
        raise SystemExit(f'EXERCISE_TO_CLASS is missing: {sorted(missing_map)}')

    # confusion[mapped_class_or_"out_of_scope"][predicted_class_or_"(no track)"] = count
    confusion: dict[str, Counter] = defaultdict(Counter)
    confidences: dict[str, list[float]] = defaultdict(list)
    n_seen = 0
    n_total = len(subjects) * len(exercises)

    for subject in subjects:
        for exercise in exercises:
            pred, conf = classifier_output(subject, exercise)
            if pred is None and conf is None and not (OUT_ROOT / subject / exercise /
                                                        f'{exercise}.json').exists():
                continue  # not run yet
            n_seen += 1
            mapped = EXERCISE_TO_CLASS[exercise] or 'out_of_scope'
            key = pred if pred is not None else '(no track)'
            confusion[mapped][key] += 1
            if conf is not None:
                confidences[f'{mapped}:{key}'].append(conf)

    print(f'{n_seen}/{n_total} clips have pipeline output so far\n')

    print('=== Confusion matrix: mapped Fit3D class -> classifier prediction ===')
    for mapped in sorted(confusion):
        total = sum(confusion[mapped].values())
        tag = ' [heuristic-only, never trained-model output]' if mapped in HEURISTIC_ONLY_CLASSES \
            else ' [out-of-taxonomy negative control]' if mapped == 'out_of_scope' else ''
        print(f'\n{mapped}{tag} (n={total}):')
        for pred, count in confusion[mapped].most_common():
            confs = confidences.get(f'{mapped}:{pred}', [])
            conf_str = f', avg conf {sum(confs) / len(confs):.2f}' if confs else ''
            correct = ' <-- correct' if pred == mapped else ''
            print(f'  {pred:12s} {count:3d} ({count / total:.0%}){conf_str}{correct}')

    print('\n=== Accuracy on classes the trained model can actually predict ===')
    for mapped in sorted(TRAINED_CLASSES & confusion.keys()):
        total = sum(confusion[mapped].values())
        correct = confusion[mapped].get(mapped, 0)
        print(f'  {mapped:12s} {correct}/{total} ({correct / total:.0%})')

    print('\n=== Heuristic-only classes (domain-shift/coverage-gap probes, not "wrong") ===')
    for mapped in sorted(HEURISTIC_ONLY_CLASSES & confusion.keys()):
        total = sum(confusion[mapped].values())
        top = confusion[mapped].most_common(1)[0]
        print(f'  {mapped:12s} n={total}, most common prediction: {top[0]} ({top[1]}/{total})')

    if 'out_of_scope' in confusion:
        print('\n=== Out-of-taxonomy negative controls: scattered/low-confidence (good) '
              'vs. confidently wrong (bad)? ===')
        total = sum(confusion['out_of_scope'].values())
        top = confusion['out_of_scope'].most_common(1)[0]
        dominance = top[1] / total
        print(f'  n={total}, most common prediction {top[0]} ({dominance:.0%} of clips)')
        if dominance > 0.6:
            confs = confidences.get(f"out_of_scope:{top[0]}", [])
            avg_conf = sum(confs) / len(confs) if confs else float('nan')
            print(f'  -> concentrated on one class, avg confidence {avg_conf:.2f} for that '
                  f'prediction -- {"looks like a real bias" if avg_conf > 0.6 else "low-confidence, plausibly just noise"}')
        else:
            print('  -> scattered across classes, consistent with a well-calibrated classifier '
                  'that has no good answer for out-of-taxonomy movement')

    out = {
        'n_seen': n_seen, 'n_total': n_total,
        'confusion': {k: dict(v) for k, v in confusion.items()},
        'exercise_to_class': EXERCISE_TO_CLASS,
    }
    out_path = OUT_ROOT / 'domain_shift_report.json'
    out_path.write_text(json.dumps(out, indent=2))
    print(f'\nreport -> {out_path}')


if __name__ == '__main__':
    main()
