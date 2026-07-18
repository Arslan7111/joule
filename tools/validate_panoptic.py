"""Validate 3D triangulation/fusion against CMU Panoptic mocap ground truth.

Builds a rig .npz from the sequence's calibration.json, runs the fused
pipeline (pipeline.py --fuse) on the chosen HD views, then scores the
pipeline's 3D joint-angle series against angles computed from the
hdPose3d_stage1_coco19 mocap skeletons.

Usage:
    python tools/validate_panoptic.py test_videos/panoptic_pose2 \
        --cams 16 23 30 [--skip-run]

Expects in <dir>: calibration.json, cam_<id>.mp4 per --cams, and gt3d.tar
(or an already-extracted hdPose3d_stage1_coco19/ directory). Panoptic HD
frame index i corresponds to body3DScene_<i>.json; a small constant offset
is searched automatically (±5 frames).
"""

import argparse
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.triangulation import compute_all_angles_3d  # noqa: E402

PANOPTIC_UP = np.array([0.0, -1.0, 0.0])   # Panoptic world is Y-down

# Panoptic joints19 order → COCO-17 order used by the pipeline
COCO19_TO_17 = [1, 15, 17, 16, 18, 3, 9, 4, 10, 5, 11, 6, 12, 7, 13, 8, 14]


def build_rig(calib_path: Path, cam_ids: list[int], out_path: Path) -> None:
    calib = json.loads(calib_path.read_text())
    by_name = {c['name']: c for c in calib['cameras']}
    Ks, Rs, ts, dists = [], [], [], []
    for cid in cam_ids:
        c = by_name[f'00_{cid:02d}']
        Ks.append(np.array(c['K'], dtype=np.float64))
        Rs.append(np.array(c['R'], dtype=np.float64))
        ts.append(np.array(c['t'], dtype=np.float64).ravel())
        d = np.array(c['distCoef'], dtype=np.float64).ravel()
        dists.append(d[:5] if d.size >= 5 else np.pad(d, (0, 5 - d.size)))
    np.savez(out_path, Ks=np.stack(Ks), Rs=np.stack(Rs), ts=np.stack(ts),
             dists=np.stack(dists), up=PANOPTIC_UP)
    print(f'rig -> {out_path} ({len(cam_ids)} cams)')


def load_gt_angles(gt_dir: Path) -> dict[int, dict]:
    """frame index -> {angle_name: degrees} from mocap skeletons."""
    gt = {}
    for f in sorted(gt_dir.glob('body3DScene_*.json')):
        idx = int(f.stem.split('_')[1])
        try:
            bodies = json.loads(f.read_text()).get('bodies', [])
        except json.JSONDecodeError:
            continue
        if not bodies:
            continue
        j19 = np.array(bodies[0]['joints19'], dtype=np.float64).reshape(-1, 4)
        kps = j19[COCO19_TO_17]                    # (17, 4) x y z conf
        kps[:, 3] = np.where(kps[:, 3] > 0, 1.0, 0.0)
        gt[idx] = compute_all_angles_3d(kps, conf_thresh=0.5, up=PANOPTIC_UP)
    return gt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset_dir', type=Path)
    ap.add_argument('--cams', nargs='+', type=int, default=[16, 23, 30])
    ap.add_argument('--skip-run', action='store_true',
                    help='reuse existing results/ from a previous run')
    args = ap.parse_args()
    d = args.dataset_dir

    rig = d / f"rig_{'_'.join(str(c) for c in args.cams)}.npz"
    build_rig(d / 'calibration.json', args.cams, rig)

    gt_dir = d / 'hdPose3d_stage1_coco19'
    if not gt_dir.exists():
        with tarfile.open(d / 'gt3d.tar') as tf:
            tf.extractall(d)
        print(f'extracted GT -> {gt_dir}')

    out_dir = d / 'validation_results'
    result_json = out_dir / 'val.json'
    if not args.skip_run or not result_json.exists():
        out_dir.mkdir(exist_ok=True)
        sources = [str(d / f'cam_{c}.mp4') for c in args.cams]
        cmd = [sys.executable, str(PROJECT_ROOT / 'pipeline.py'),
               '--sources', *sources, '--fuse', str(rig),
               '--names', 'val', '--exercises', 'auto',
               '--output', str(out_dir)]
        print('running fused pipeline...')
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    data = json.loads(result_json.read_text())
    track = max(data['tracks'], key=lambda t: t['total_frames'])
    print(f"person {track['person']}: {track['total_frames']} frames, "
          f"classified {track.get('exercise_class', '?')}")

    gt = load_gt_angles(gt_dir)
    print(f'GT frames: {len(gt)} ({min(gt)}..{max(gt)})')
    fps = 29.97

    # Pipeline angle series: timestamp -> per-joint value at video frame
    pred: dict[int, dict[str, float]] = {}
    for joint, series in track['angle_series'].items():
        if joint.endswith('_valgus'):
            continue
        for ts, val in series:
            if val is not None:
                pred.setdefault(round(ts * fps), {})[joint] = val

    def score(offset: int) -> tuple[float, int]:
        errs = []
        for fi, joints in pred.items():
            g = gt.get(fi + offset)
            if not g:
                continue
            for joint, val in joints.items():
                if g.get(joint) is not None:
                    errs.append(abs(val - g[joint]))
        return (float(np.median(errs)) if errs else np.inf), len(errs)

    offset = min(range(-5, 6), key=lambda o: score(o)[0])
    print(f'best GT frame offset: {offset:+d}')

    per_joint: dict[str, list[float]] = {}
    gt_avail: dict[str, int] = {}
    for fi, joints in pred.items():
        g = gt.get(fi + offset)
        if not g:
            continue
        for joint, gval in g.items():
            if gval is None:
                continue
            gt_avail[joint] = gt_avail.get(joint, 0) + 1
            if joint in joints:
                per_joint.setdefault(joint, []).append(abs(joints[joint] - gval))

    print(f"\n=== 3D angle error vs mocap ({'/'.join(str(c) for c in args.cams)}) ===")
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
    print(f"{'ALL':16s} {len(all_errs):5d} {np.mean(all_errs):7.1f} "
          f"{np.median(all_errs):7.1f} {np.percentile(all_errs, 95):7.1f}")


if __name__ == '__main__':
    main()
