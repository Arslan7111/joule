"""Camera-count/adjacency sensitivity sweep for Fit3D triangulation
accuracy -- the stretch goal flagged in FIT3D_UTILIZATION_PLAN.md's Track A
but never run: does src/triangulation.py's CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS
table (tuned entirely on CMU Panoptic's 5-camera dome rig) transfer to a
second real rig with fewer/different camera counts, or does accuracy fall
off a cliff below some camera count on Fit3D's own geometry?

Writes to a SEPARATE output root (validation_results_fit3d_camsweep/) so it
never touches the canonical 4-of-4 batch results in
validation_results_fit3d/ that Track A/B/C's numbers already depend on.

Usage:
    python tools/validate_fit3d_camsweep.py
"""

import itertools
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_fit3d import ALL_CAMS, score_exercise  # noqa: E402

OUT_ROOT = PROJECT_ROOT / 'validation_results_fit3d_camsweep'

# (subject, exercise) pairs to sweep, and which camera-count combos to run
# for each. Full 2-of-4 (6 pairs) + 3-of-4 (4 triples) on s03/squat -- the
# original single-subject pilot exercise, well understood from prior
# sessions. Spot-checks on s03/pushup (the hardest exercise in the existing
# results, largest baseline error) with just the best/worst pair from the
# squat sweep plus one triple, to see whether camera-count sensitivity gets
# worse on harder poses. 4-of-4 is not re-run here -- already the canonical
# batch result in validation_results_fit3d/<subject>/<exercise>/.
PAIRS = list(itertools.combinations(ALL_CAMS, 2))     # 6
TRIPLES = list(itertools.combinations(ALL_CAMS, 3))   # 4

PLAN = [
    ('s03', 'squat', PAIRS + TRIPLES),
    # filled in after the squat sweep identifies the best/worst pair
]


def run_combo(subject: str, exercise: str, cams: tuple[str, ...]) -> dict:
    tag = '+'.join(c[-4:] for c in cams)  # last 4 digits per cam id, readable
    out = OUT_ROOT / f'{subject}_{exercise}_{tag}'
    result_json = out / exercise / f'{exercise}.json'
    if result_json.exists():
        print(f'[skip, already run] {subject}/{exercise} cams={tag}')
    else:
        print(f'[running] {subject}/{exercise} cams={tag} ({len(cams)} cameras)')
    t0 = time.time()
    r = score_exercise(subject, exercise, list(cams), out, fps=50.0,
                        skip_run=result_json.exists())
    dt = time.time() - t0
    all_errs = [e for errs in r['per_joint'].values() for e in errs]
    import numpy as np
    mean = float(np.mean(all_errs)) if all_errs else None
    median = float(np.median(all_errs)) if all_errs else None
    print(f'  -> mean={mean}, median={median}, n={len(all_errs)}, {dt:.0f}s')
    return {'subject': subject, 'exercise': exercise, 'cams': list(cams),
            'n_cams': len(cams), 'tag': tag, 'mean': mean, 'median': median,
            'n': len(all_errs)}


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for subject, exercise, combos in PLAN:
        for cams in combos:
            results.append(run_combo(subject, exercise, cams))

    results.sort(key=lambda r: (r['n_cams'], r['mean'] or 1e9))
    print('\n=== Summary, sorted by camera count then accuracy ===')
    for r in results:
        print(f"{r['subject']}/{r['exercise']:12s} n_cams={r['n_cams']} "
              f"cams={r['tag']:20s} mean={r['mean']:.2f} median={r['median']:.2f} n={r['n']}")

    (OUT_ROOT / 'sweep_summary.json').write_text(json.dumps(results, indent=2))
    print(f'\nsummary -> {OUT_ROOT / "sweep_summary.json"}')


if __name__ == '__main__':
    main()
