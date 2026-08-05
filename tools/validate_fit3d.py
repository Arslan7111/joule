"""Validate 3D triangulation/fusion against Fit3D mocap ground truth.

Fit3D gives real gym exercises (squat, deadlift, curls, rows, presses...)
shot with 4 calibrated, synchronized cameras and SMPLX-derived mocap-grade
3D ground truth (`joints3d_25` per exercise) -- a stronger validation
target than CMU Panoptic's generic dome poses (`tools/validate_panoptic.py`)
since it's real gym movement, not walking/standing, and directly exercises
the classifier/rep-counting/3D-angle path this project actually ships.

Two things about Fit3D's raw format are not documented inline in the
dataset and were reverse-engineered from the real data before trusting any
numbers out of this script (see `CAMERA_PLACEMENT.md`-adjacent session
notes / commit message for the verification detail):

1. **Extrinsics convention**: `extrinsics.T` is the camera CENTER in world
   coordinates, not the standard `t` in `P = K[R|t]` (i.e. NOT
   `X_cam = R @ X_world + T`). Verified by projecting a frame's GT joints
   onto its actual video frame: the standard-convention formula placed
   every joint ~3000px off-frame; `X_cam = R @ (X_world - T)` landed them
   exactly on the real body in the image. `build_rig()` below converts to
   the standard `t = -R @ T` once so the existing `CalibratedCamera` /
   `src/triangulation.py` code needs no changes.
2. **`joints3d_25` order and left/right**: recovered empirically, not from
   documentation. Bone-length invariance (anatomically connected joints
   keep ~0 coefficient-of-variation in pairwise distance across thousands
   of real frames spanning several exercises) recovered the skeleton
   topology; projecting the two symmetric chains onto a real frame where
   the subject's back is to the camera (so image-left = anatomical left,
   no mirroring) fixed which chain is left vs right. See `FIT3D_TO_COCO17`.

Usage:
    python tools/validate_fit3d.py s03 squat dumbbell_biceps_curls barbell_row \
        --cams 50591643 58860488 60457274 65906101 [--skip-run]

Expects (from the real Fit3D download, gitignored, not committed):
    Fit3D/fit3d_train/train/<subject>/camera_parameters/<cam>/<exercise>.json
    Fit3D/fit3d_train/train/<subject>/videos/<cam>/<exercise>.mp4
    Fit3D/fit3d_train/train/<subject>/joints3d_25/<exercise>.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.triangulation import compute_all_angles_3d  # noqa: E402

FIT3D_ROOT = PROJECT_ROOT / 'Fit3D' / 'fit3d_train' / 'train'
FIT3D_UP = np.array([0.0, 0.0, 1.0])   # Fit3D world is Z-up, matches pipeline default
ALL_CAMS = ['50591643', '58860488', '60457274', '65906101']

# Fit3D's 25-joint skeleton (see module docstring for how this was recovered)
# -> COCO-17 index used throughout this pipeline. Fit3D has no face
# keypoints (COCO 0-4: nose/eyes/ears) -- left at zero confidence, unused
# by ANGLE_DEFINITIONS / trunk_lean.
FIT3D_TO_COCO17 = {
    5: 11,   # left_shoulder
    6: 14,   # right_shoulder
    7: 12,   # left_elbow
    8: 15,   # right_elbow
    9: 13,   # left_wrist
    10: 16,  # right_wrist
    11: 1,   # left_hip
    12: 4,   # right_hip
    13: 2,   # left_knee
    14: 5,   # right_knee
    15: 3,   # left_ankle
    16: 6,   # right_ankle
}


def build_rig(subject_dir: Path, exercise: str, cam_ids: list[str], out_path: Path) -> None:
    Ks, Rs, ts, dists = [], [], [], []
    for cid in cam_ids:
        cp = json.loads(
            (subject_dir / 'camera_parameters' / cid / f'{exercise}.json').read_text())
        R = np.array(cp['extrinsics']['R'], dtype=np.float64)
        cam_center = np.array(cp['extrinsics']['T'], dtype=np.float64).ravel()
        t = -R @ cam_center                       # convert to standard P = K[R|t]

        intr = cp['intrinsics_w_distortion']       # K paired with these dist coeffs
        f = np.array(intr['f'], dtype=np.float64).ravel()
        c = np.array(intr['c'], dtype=np.float64).ravel()
        K = np.array([[f[0], 0, c[0]], [0, f[1], c[1]], [0, 0, 1]])
        k = np.array(intr['k'], dtype=np.float64).ravel()   # [k1, k2, k3]
        p = np.array(intr['p'], dtype=np.float64).ravel()   # [p1, p2]
        dist = np.array([k[0], k[1], p[0], p[1], k[2]])     # OpenCV order

        Ks.append(K); Rs.append(R); ts.append(t); dists.append(dist)
    np.savez(out_path, Ks=np.stack(Ks), Rs=np.stack(Rs), ts=np.stack(ts),
             dists=np.stack(dists), up=FIT3D_UP)
    print(f'rig -> {out_path} ({len(cam_ids)} cams)')


def load_gt_angles(subject_dir: Path, exercise: str) -> dict[int, dict]:
    """frame index -> {angle_name: degrees} from Fit3D mocap-grade joints."""
    frames = json.loads(
        (subject_dir / 'joints3d_25' / f'{exercise}.json').read_text())['joints3d_25']
    gt = {}
    for i, frame in enumerate(frames):
        pts = np.array(frame, dtype=np.float64)   # (25, 3)
        kps17 = np.zeros((17, 4), dtype=np.float64)
        for coco_idx, fit3d_idx in FIT3D_TO_COCO17.items():
            kps17[coco_idx, :3] = pts[fit3d_idx]
            kps17[coco_idx, 3] = 1.0
        gt[i] = compute_all_angles_3d(kps17, conf_thresh=0.5, up=FIT3D_UP)
    return gt


def score_exercise(subject: str, exercise: str, cam_ids: list[str],
                    out_root: Path, fps: float, skip_run: bool) -> dict:
    subject_dir = FIT3D_ROOT / subject
    ex_dir = out_root / exercise
    ex_dir.mkdir(parents=True, exist_ok=True)

    rig = ex_dir / 'rig.npz'
    build_rig(subject_dir, exercise, cam_ids, rig)

    result_json = ex_dir / f'{exercise}.json'   # pipeline.py names output after --names
    if not skip_run or not result_json.exists():
        sources = [str(subject_dir / 'videos' / c / f'{exercise}.mp4') for c in cam_ids]
        cmd = [sys.executable, str(PROJECT_ROOT / 'pipeline.py'),
               '--sources', *sources, '--fuse', str(rig),
               '--names', exercise, '--exercises', 'auto',
               '--output', str(ex_dir)]
        print(f'running fused pipeline for {exercise}...')
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    data = json.loads(result_json.read_text())
    if not data.get('tracks'):
        print(f'  [{exercise}] no tracks produced, skipping')
        return {'exercise': exercise, 'per_joint': {}, 'gt_avail': {}, 'offset': None}
    track = max(data['tracks'], key=lambda t: t['total_frames'])
    print(f"  [{exercise}] person {track['person']}: {track['total_frames']} frames, "
          f"classified {track.get('exercise_class', '?')}")

    gt = load_gt_angles(subject_dir, exercise)

    # Per-joint series, scored independently against GT (NOT joined through a
    # shared per-frame bucket -- see module note on _downsample_series: each
    # joint's ~30fps output sampling clock free-runs off its OWN data, so a
    # single transient 1-frame gap in one joint permanently shifts its output
    # timestamps out of native-frame alignment with other joints. Grouping
    # joints into one shared frame-indexed dict before scoring manufactures a
    # false anti-correlated "coverage" pattern between joints that never
    # actually goes missing at the same real moments -- confirmed against a
    # real deep-squat frame range where directly-traced per-frame keypoint
    # confidence stayed continuously healthy despite the old scoring method
    # showing ~50% "coverage". Each joint's own timestamp is rounded to its
    # own nearest native GT frame independently instead.
    series_by_joint = {
        j: [(ts, val) for ts, val in track['angle_series'].get(j, []) if val is not None]
        for j in gt[next(iter(gt))].keys()
    }

    def score(offset: int) -> tuple[float, int]:
        errs = []
        for joint, series in series_by_joint.items():
            for ts, val in series:
                g = gt.get(round(ts * fps) + offset)
                if g and g.get(joint) is not None:
                    errs.append(abs(val - g[joint]))
        return (float(np.median(errs)) if errs else np.inf), len(errs)

    offset = min(range(-8, 9), key=lambda o: score(o)[0])
    print(f'  [{exercise}] best GT frame offset: {offset:+d}')

    per_joint: dict[str, list[float]] = {}
    n_samples: dict[str, int] = {j: len(s) for j, s in series_by_joint.items()}
    for joint, series in series_by_joint.items():
        for ts, val in series:
            g = gt.get(round(ts * fps) + offset)
            if g and g.get(joint) is not None:
                per_joint.setdefault(joint, []).append(abs(val - g[joint]))

    # Coverage relative to whichever joint the pipeline emitted the most
    # samples for (empirically ~OUTPUT_FPS from the native frame rate) --
    # NOT relative to native GT frame count, since the ~30fps output
    # sampling rate is an intentional design ceiling (src/config.py
    # OUTPUT_FPS), not a data-availability defect on its own.
    max_n = max(n_samples.values()) if n_samples else 0
    gt_avail = {j: max_n for j in n_samples} if max_n else {}

    return {'exercise': exercise, 'per_joint': per_joint, 'gt_avail': gt_avail,
            'offset': offset, 'exercise_class': track.get('exercise_class')}


def print_table(title: str, per_joint: dict[str, list[float]], gt_avail: dict[str, int]) -> None:
    print(f'\n=== {title} ===')
    print(f"{'joint':16s} {'n':>5s} {'mean':>7s} {'median':>7s} {'p95':>7s} {'cover':>7s}")
    all_errs = []
    for joint in sorted(gt_avail):
        errs = per_joint.get(joint, [])
        cov = len(errs) / gt_avail[joint]
        if errs:
            all_errs += errs
            print(f'{joint:16s} {len(errs):5d} {np.mean(errs):7.1f} '
                  f'{np.median(errs):7.1f} {np.percentile(errs, 95):7.1f} {cov:6.0%}')
        else:
            print(f'{joint:16s} {0:5d} {"-":>7s} {"-":>7s} {"-":>7s} {cov:6.0%}')
    if all_errs:
        print(f"{'ALL':16s} {len(all_errs):5d} {np.mean(all_errs):7.1f} "
              f"{np.median(all_errs):7.1f} {np.percentile(all_errs, 95):7.1f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('subject', help='Fit3D subject id, e.g. s03')
    ap.add_argument('exercises', nargs='+', help='exercise names, e.g. squat deadlift')
    ap.add_argument('--cams', nargs='+', default=ALL_CAMS)
    ap.add_argument('--fps', type=float, default=50.0)
    ap.add_argument('--out', type=Path, default=PROJECT_ROOT / 'validation_results_fit3d')
    ap.add_argument('--skip-run', action='store_true',
                     help='reuse existing val.json from a previous run')
    args = ap.parse_args()

    out_root = args.out / args.subject
    out_root.mkdir(parents=True, exist_ok=True)

    results = []
    for exercise in args.exercises:
        results.append(score_exercise(args.subject, exercise, args.cams,
                                       out_root, args.fps, args.skip_run))

    for r in results:
        if r['per_joint']:
            print_table(f"{args.subject}/{r['exercise']} "
                        f"(classified {r.get('exercise_class', '?')})",
                        r['per_joint'], r['gt_avail'])

    combined_per_joint: dict[str, list[float]] = {}
    combined_gt_avail: dict[str, int] = {}
    for r in results:
        for joint, errs in r['per_joint'].items():
            combined_per_joint.setdefault(joint, []).extend(errs)
        for joint, n in r['gt_avail'].items():
            combined_gt_avail[joint] = combined_gt_avail.get(joint, 0) + n
    print_table(f"{args.subject} — ALL {len(args.exercises)} exercises combined",
                combined_per_joint, combined_gt_avail)

    report = {
        'subject': args.subject,
        'cams': args.cams,
        'fps': args.fps,
        'exercises': [
            {
                'exercise': r['exercise'],
                'exercise_class': r.get('exercise_class'),
                'offset': r['offset'],
                'per_joint': {
                    j: {'n': len(e), 'mean': float(np.mean(e)), 'median': float(np.median(e)),
                        'p95': float(np.percentile(e, 95))}
                    for j, e in r['per_joint'].items() if e
                },
            }
            for r in results
        ],
    }
    report_path = out_root / 'report.json'
    report_path.write_text(json.dumps(report, indent=2))
    print(f'\nreport -> {report_path}')


if __name__ == '__main__':
    main()
