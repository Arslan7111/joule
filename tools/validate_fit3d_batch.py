"""Batch driver for tools/validate_fit3d.py -- scales single-subject/single-
exercise validation runs up to the full 8-subject x 28-named-exercise Fit3D
sweep (Track A of `FIT3D_UTILIZATION_PLAN.md`).

`tools/validate_fit3d.py`'s `score_exercise()` already does the right thing
for one clip; this driver adds what's needed to run all of them unattended:

- **Resumability.** Each clip's scored result is checkpointed to
  `<out>/<subject>/<exercise>/score.json` as soon as it's computed. Before
  launching a clip (running the fused pipeline, which is the expensive
  part), the driver checks for that checkpoint and skips the clip entirely
  if it's already there -- a killed/restarted run picks up where it left
  off instead of redoing finished work. `score_exercise(..., skip_run=True)`
  additionally skips the pipeline subprocess itself if its raw output JSON
  exists but the checkpoint doesn't (e.g. pipeline ran, driver died before
  scoring) -- so no completed pipeline run is ever redone.
- **Per-clip failure isolation.** One bad clip (no detection, corrupt
  video, pipeline crash) is caught, logged to
  `<out>/<subject>/<exercise>/failure.json`, and does not stop the batch.
- **Modest parallelism.** `--workers N` runs N clips concurrently via a
  thread pool -- safe here because each clip's real work is a `subprocess`
  call (GIL released while the child pipeline process runs).
- **Combined report.** `--report-only` (re)builds the aggregate report from
  whatever checkpoints exist on disk without launching anything, so
  progress can be inspected from another terminal mid-run, or the final
  report regenerated after a hard kill.

Usage:
    # full sweep, 3 concurrent clips
    python tools/validate_fit3d_batch.py --workers 3

    # small test batch
    python tools/validate_fit3d_batch.py --subjects s03 s04 \
        --exercises squat pushup deadlift barbell_row dumbbell_biceps_curls \
        --workers 2

    # just rebuild the aggregate report from whatever's on disk
    python tools/validate_fit3d_batch.py --report-only
"""

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_fit3d import ALL_CAMS, FIT3D_ROOT, score_exercise  # noqa: E402


def discover_subjects() -> list[str]:
    return sorted(p.name for p in FIT3D_ROOT.iterdir() if p.is_dir())


def discover_named_exercises(subject: str, cam: str = ALL_CAMS[0]) -> list[str]:
    """Named (non-warmup) exercise clips available for `subject`."""
    vids = FIT3D_ROOT / subject / 'videos' / cam
    return sorted(p.stem for p in vids.glob('*.mp4') if not p.stem.startswith('warmup_'))


def checkpoint_path(out_root: Path, subject: str, exercise: str) -> Path:
    return out_root / subject / exercise / 'score.json'


def failure_path(out_root: Path, subject: str, exercise: str) -> Path:
    return out_root / subject / exercise / 'failure.json'


def run_one(subject: str, exercise: str, cams: list[str], out_root: Path,
            fps: float, force: bool) -> tuple[str, str, str]:
    """Score one (subject, exercise) clip, checkpointing the result.

    Returns (subject, exercise, status) where status is 'done', 'skipped'
    (checkpoint already existed), 'empty' (pipeline produced no tracks), or
    'failed'.
    """
    ckpt = checkpoint_path(out_root, subject, exercise)
    fail = failure_path(out_root, subject, exercise)
    if ckpt.exists() and not force:
        return subject, exercise, 'skipped'

    fail.unlink(missing_ok=True)
    try:
        result = score_exercise(subject, exercise, cams, out_root / subject, fps,
                                 skip_run=not force)
    except Exception as e:
        fail.parent.mkdir(parents=True, exist_ok=True)
        fail.write_text(json.dumps({
            'subject': subject, 'exercise': exercise,
            'error': str(e), 'traceback': traceback.format_exc(),
        }, indent=2))
        return subject, exercise, 'failed'

    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_text(json.dumps(result, indent=2))
    return subject, exercise, ('empty' if not result['per_joint'] else 'done')


def _stats(per_joint: dict[str, list[float]]) -> dict:
    out = {}
    for joint, errs in per_joint.items():
        if not errs:
            continue
        out[joint] = {'n': len(errs), 'mean': float(np.mean(errs)),
                       'median': float(np.median(errs)), 'p95': float(np.percentile(errs, 95))}
    return out


def build_report(out_root: Path, subjects: list[str], exercises: list[str],
                  cams: list[str], fps: float) -> dict:
    """Aggregate every checkpoint found on disk under `out_root`, not just
    ones produced by this invocation -- so `--report-only` reflects the
    true cumulative state of a possibly-interrupted-and-resumed batch."""
    per_subject: dict[str, dict] = {}
    per_exercise_pooled: dict[str, dict[str, list[float]]] = {}
    grand_pooled: dict[str, list[float]] = {}
    failures = []
    empty = []
    missing = []

    for subject in subjects:
        subj_per_joint_all: dict[str, list[float]] = {}
        subj_exercises = []
        for exercise in exercises:
            ckpt = checkpoint_path(out_root, subject, exercise)
            fail = failure_path(out_root, subject, exercise)
            if fail.exists():
                failures.append(json.loads(fail.read_text()))
                continue
            if not ckpt.exists():
                missing.append({'subject': subject, 'exercise': exercise})
                continue
            r = json.loads(ckpt.read_text())
            if not r['per_joint']:
                empty.append({'subject': subject, 'exercise': exercise})
                continue
            subj_exercises.append({
                'exercise': exercise,
                'exercise_class': r.get('exercise_class'),
                'offset': r['offset'],
                'per_joint': _stats(r['per_joint']),
            })
            for joint, errs in r['per_joint'].items():
                subj_per_joint_all.setdefault(joint, []).extend(errs)
                per_exercise_pooled.setdefault(exercise, {}).setdefault(joint, []).extend(errs)
                grand_pooled.setdefault(joint, []).extend(errs)
        if subj_exercises:
            per_subject[subject] = {
                'exercises': subj_exercises,
                'combined': _stats(subj_per_joint_all),
            }

    return {
        'subjects': subjects,
        'exercises': exercises,
        'cams': cams,
        'fps': fps,
        'per_subject': per_subject,
        'per_exercise_pooled': {ex: _stats(pj) for ex, pj in per_exercise_pooled.items()},
        'pooled_total': _stats(grand_pooled),
        'failures': failures,
        'empty': empty,
        'missing': missing,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--subjects', nargs='+', default=None,
                     help='default: all subjects found under Fit3D/fit3d_train/train')
    ap.add_argument('--exercises', nargs='+', default=None,
                     help='default: all named (non-warmup) exercises for the first subject')
    ap.add_argument('--cams', nargs='+', default=ALL_CAMS)
    ap.add_argument('--fps', type=float, default=50.0)
    ap.add_argument('--out', type=Path, default=PROJECT_ROOT / 'validation_results_fit3d')
    ap.add_argument('--workers', type=int, default=1, help='concurrent clips')
    ap.add_argument('--force', action='store_true',
                     help='re-run clips even if a checkpoint/pipeline output already exists')
    ap.add_argument('--report-only', action='store_true',
                     help='skip running anything, just rebuild the aggregate report')
    args = ap.parse_args()

    subjects = args.subjects or discover_subjects()
    exercises = args.exercises or discover_named_exercises(subjects[0])
    args.out.mkdir(parents=True, exist_ok=True)

    if not args.report_only:
        jobs = [(s, e) for s in subjects for e in exercises]
        print(f'{len(jobs)} clips ({len(subjects)} subjects x {len(exercises)} exercises), '
              f'{args.workers} worker(s)')
        t0 = time.time()
        counts = {'done': 0, 'skipped': 0, 'empty': 0, 'failed': 0}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(run_one, s, e, args.cams, args.out, args.fps, args.force): (s, e)
                for s, e in jobs
            }
            try:
                for i, fut in enumerate(as_completed(futures), 1):
                    subject, exercise, status = fut.result()
                    counts[status] += 1
                    elapsed = time.time() - t0
                    print(f'[{i}/{len(jobs)}] {subject}/{exercise}: {status} '
                          f'({elapsed:6.0f}s elapsed, {counts})')
            except KeyboardInterrupt:
                print('\ninterrupted -- cancelling pending jobs (already-running clips '
                      'finish their current subprocess) ...')
                for f in futures:
                    f.cancel()
                pool.shutdown(wait=False, cancel_futures=True)

    report = build_report(args.out, subjects, exercises, args.cams, args.fps)
    report_path = args.out / 'batch_report.json'
    report_path.write_text(json.dumps(report, indent=2))

    n_ok = sum(len(v['exercises']) for v in report['per_subject'].values())
    print(f"\n{n_ok} clips scored across {len(report['per_subject'])} subjects, "
          f"{len(report['failures'])} failed, {len(report['empty'])} empty, "
          f"{len(report['missing'])} not yet run")
    if report['pooled_total']:
        all_n = sum(v['n'] for v in report['pooled_total'].values())
        all_mean = np.average([v['mean'] for v in report['pooled_total'].values()],
                               weights=[v['n'] for v in report['pooled_total'].values()])
        print(f"pooled: {all_n} joint-frame samples, weighted mean error {all_mean:.1f} deg")
    if report['failures']:
        print('failed clips:', [(f['subject'], f['exercise']) for f in report['failures']])
    print(f'report -> {report_path}')


if __name__ == '__main__':
    main()
