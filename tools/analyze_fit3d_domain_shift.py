"""Track B of `FIT3D_UTILIZATION_PLAN.md`: classifier domain-shift
characterization. Builds a confusion matrix of Fit3D exercise (mapped to
this project's taxonomy) x the trained classifier's predicted class, across
every clip Track A has produced a pipeline output for.

Reuses Track A's own runs -- the classifier's prediction is already
recorded in every `<subject>/<exercise>/<exercise>.json` pipeline output,
so this needs no new pipeline runs, only reading what's already on disk.
Not gated on the full Track A sweep finishing: it reports on however many
clips currently have output, and can be re-run any time (including after
Track A completes) to pick up more.

**Diagnostic only.** Fit3D is academic-license-only (see `DEVELOPMENT.md`)
-- validation is fine, training a shipped model on Fit3D frames is not,
no matter what this script finds. Any real fix belongs in RepCount
(already licensed) or real gym footage.

The exercise -> taxonomy mapping below is transcribed from
`FIT3D_UTILIZATION_PLAN.md`'s table, which was itself built by reading
Fit3D's exercise names against `src/exercise_classifier.py`'s
CLASSES/CLASS_FAMILY -- a first-pass judgment call, not authoritative.

Usage:
    python tools/analyze_fit3d_domain_shift.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_fit3d import FIT3D_ROOT  # noqa: E402
from tools.validate_fit3d_batch import discover_named_exercises  # noqa: E402

OUT_ROOT = PROJECT_ROOT / 'validation_results_fit3d'

# Classes the trained model can actually emit (src/exercise_classifier.py CLASSES,
# minus the heuristic-only ones and 'unknown').
TRAINED_CLASSES = {'cardio', 'press', 'pullup', 'pushup', 'raise', 'situp', 'squat'}
# Never emitted by the trained model -- always produced by a separate heuristic path.
HEURISTIC_ONLY_CLASSES = {'hinge', 'lunge', 'curl', 'row'}

EXERCISE_TO_CLASS = {
    'squat': 'squat',
    'deadlift': 'hinge',
    'dumbbell_reverse_lunge': 'lunge',
    'dumbbell_biceps_curls': 'curl',
    'dumbbell_hammer_curls': 'curl',
    'dumbbell_curl_trifecta': 'curl',
    'drag_curl': 'curl',
    'dumbbell_overhead_shoulder_press': 'press',
    'neutral_overhead_shoulder_press': 'press',
    'clean_and_press': 'press',
    'barbell_row': 'row',
    'barbell_dead_row': 'row',
    'one_arm_row': 'row',
    'pushup': 'pushup',
    'diamond_pushup': 'pushup',
    'side_lateral_raise': 'raise',
    'overhead_trap_raises': 'raise',
    'dumbbell_scaptions': 'raise',
    'w_raise': 'raise',
    'standing_ab_twists': 'situp',   # weak match -- core movement, not a sit-up motion
    # No match -- out of this project's taxonomy. Negative controls: does the
    # classifier correctly avoid forcing these into one of our classes?
    'band_pull_apart': None, 'barbell_shrug': None, 'burpees': None,
    'dumbbell_high_pulls': None, 'man_maker': None, 'mule_kick': None,
    'overhead_extension_thruster': None, 'walk_the_box': None,
}


def classifier_output(subject: str, exercise: str) -> tuple[str | None, float | None]:
    """(predicted_class, confidence) from the raw pipeline output, or (None, None)
    if the clip hasn't been run yet / produced no tracks. Mirrors
    tools/validate_fit3d.py's score_exercise() track-selection (largest track)."""
    result_json = OUT_ROOT / subject / exercise / f'{exercise}.json'
    if not result_json.exists():
        return None, None
    data = json.loads(result_json.read_text())
    if not data.get('tracks'):
        return None, None
    track = max(data['tracks'], key=lambda t: t['total_frames'])
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
