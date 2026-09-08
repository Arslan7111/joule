"""
Workstream D: pose-backbone benchmark — MediaPipe (current) vs ViTPose+ Large.

Motivation: Jeremy Park's chin-up tracker uses ViTPose+ Large instead of
MediaPipe. Question this answers: does a stronger 2D pose backbone reduce our
Fit3D 3D-triangulation error (10.1 deg mean, worse on the self-occluded squat/
pushup tail), and at what CPU cost? Measurement only, per the plan — this does
not change src/pose.py or the shipped pipeline. A follow-up decides adoption.

Method: for each (subject, exercise), build the Fit3D rig (reused from
tools/validate_fit3d.py), run detector -> {MediaPipe | ViTPose+} -> undistort
-> triangulate_skeleton -> compute_all_angles_3d independently per backend on
the SAME sampled frames, and score against joints3d_25 ground truth with the
same per-joint, frame-offset-search method tools/validate_fit3d.py uses (so
numbers are directly comparable to the existing Fit3D headline figures).

Fit3D is read-only here (validation-license only, same as every other Fit3D
tool in this repo) -- no training, no fine-tuning.

Extra dependencies beyond requirements.txt, only needed to run this tool:
    pip install transformers scipy

Usage:
    python tools/bench_pose_backbone.py --subjects s03 s10 \
        --exercises squat pushup --stride 8 --backends mediapipe vitpose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.config import KEYPOINT_NAMES                                   # noqa: E402
from src.detector import PersonDetectorTracker                          # noqa: E402
from src.pose import PoseEstimator                                      # noqa: E402
from src.triangulation import (                                          # noqa: E402
    CalibratedCamera,
    compute_all_angles_3d,
    triangulate_skeleton,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_fit3d import ALL_CAMS, FIT3D_ROOT, FIT3D_UP, build_rig, load_gt_angles  # noqa: E402

OUT_DIR = _ROOT / "validation_results_backbone"
VITPOSE_MODEL = "usyd-community/vitpose-plus-large"


# ─────────────────────────── backends ─────────────────────────────

class MediaPipeBackend:
    name = "mediapipe"

    def __init__(self):
        self._pose = PoseEstimator()

    def estimate(self, frame, box_xyxy) -> np.ndarray | None:
        return self._pose.estimate(frame, box_xyxy)


class ViTPoseBackend:
    """ViTPose+ (transformers). Keypoint order/names match COCO-17 exactly
    (verified against src.config.KEYPOINT_NAMES), so no remap is needed."""
    name = "vitpose"

    def __init__(self, model_id: str = VITPOSE_MODEL):
        import torch
        from transformers import AutoProcessor, VitPoseForPoseEstimation
        self._torch = torch
        self._proc = AutoProcessor.from_pretrained(model_id)
        self._model = VitPoseForPoseEstimation.from_pretrained(model_id)
        self._model.eval()
        names = [self._model.config.id2label[i].lower().replace("l_", "left_")
                                                        .replace("r_", "right_")
                 for i in range(len(self._model.config.id2label))]
        assert names == KEYPOINT_NAMES, (names, KEYPOINT_NAMES)

    def estimate(self, frame, box_xyxy) -> np.ndarray | None:
        import torch
        from PIL import Image
        x1, y1, x2, y2 = box_xyxy
        box = np.array([[x1, y1, x2 - x1, y2 - y1]], dtype=np.float32)
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = self._proc(img, boxes=[box], return_tensors="pt")
        with torch.no_grad():
            outputs = self._model(**inputs, dataset_index=torch.tensor([0]))  # 0 = COCO
        results = self._proc.post_process_pose_estimation(outputs, boxes=[box])
        if not results or not results[0]:
            return None
        pr = results[0][0]
        kps = np.zeros((17, 3), dtype=np.float32)
        for kp, lbl, sc in zip(pr["keypoints"], pr["labels"], pr["scores"]):
            kps[int(lbl.item())] = (float(kp[0]), float(kp[1]), float(sc.item()))
        return kps


def make_backend(name: str):
    return MediaPipeBackend() if name == "mediapipe" else ViTPoseBackend()


# ─────────────────────────── per-clip run ────────────────────────

def _largest_box(dets):
    best, area = None, -1.0
    for (_tid, x1, y1, x2, y2, _c) in dets:
        a = (x2 - x1) * (y2 - y1)
        if a > area:
            best, area = (x1, y1, x2, y2), a
    return best


def run_backend(subject: str, exercise: str, cam_ids: list[str], backend_name: str,
                stride: int, fps: float) -> dict:
    subject_dir = FIT3D_ROOT / subject
    backend = make_backend(backend_name)
    detectors = [PersonDetectorTracker() for _ in cam_ids]
    caps = [cv2.VideoCapture(str(subject_dir / "videos" / c / f"{exercise}.mp4"))
            for c in cam_ids]
    rig_path = OUT_DIR / subject / exercise / "rig.npz"
    rig_path.parent.mkdir(parents=True, exist_ok=True)
    build_rig(subject_dir, exercise, cam_ids, rig_path)
    data = np.load(rig_path)
    cams = [CalibratedCamera(K=data["Ks"][i], R=data["Rs"][i], t=data["ts"][i])
            for i in range(len(cam_ids))]

    n_frames = int(min(c.get(cv2.CAP_PROP_FRAME_COUNT) for c in caps))
    series_by_joint: dict[str, list[tuple]] = {}
    infer_ms = []
    n_triangulated = 0
    n_frames_seen = 0

    for fidx in range(0, n_frames, stride):
        for c in caps:
            c.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        frames = [c.read() for c in caps]
        if not all(ok for ok, _ in frames):
            continue
        views_kps, views_cams = [], []
        for (ok, frame), det, cam in zip(frames, detectors, cams):
            box = _largest_box(det.detect_and_track(frame))
            if box is None:
                continue
            t0 = time.time()
            kps = backend.estimate(frame, box)
            infer_ms.append((time.time() - t0) * 1000.0)
            if kps is not None:
                views_kps.append(kps)
                views_cams.append(cam)
        n_frames_seen += 1
        if len(views_kps) < 2:
            continue
        kps3d = triangulate_skeleton(views_cams, views_kps)
        angles = compute_all_angles_3d(kps3d, up=FIT3D_UP)
        n_triangulated += 1
        ts = fidx / fps
        for joint, val in angles.items():
            if val is not None:
                series_by_joint.setdefault(joint, []).append((ts, val))

    for c in caps:
        c.release()

    gt = load_gt_angles(subject_dir, exercise)

    def score(offset: int) -> float:
        errs = []
        for joint, series in series_by_joint.items():
            for ts, val in series:
                g = gt.get(round(ts * fps) + offset)
                if g and g.get(joint) is not None:
                    errs.append(abs(val - g[joint]))
        return float(np.median(errs)) if errs else np.inf

    offset = min(range(-8, 9), key=score)
    per_joint: dict[str, list[float]] = {}
    for joint, series in series_by_joint.items():
        for ts, val in series:
            g = gt.get(round(ts * fps) + offset)
            if g and g.get(joint) is not None:
                per_joint.setdefault(joint, []).append(abs(val - g[joint]))

    all_errs = [e for errs in per_joint.values() for e in errs]
    return {
        "subject": subject, "exercise": exercise, "backend": backend_name,
        "frames_seen": n_frames_seen, "frames_triangulated": n_triangulated,
        "ms_per_infer_mean": round(float(np.mean(infer_ms)), 1) if infer_ms else None,
        "ms_per_infer_median": round(float(np.median(infer_ms)), 1) if infer_ms else None,
        "n_infer_calls": len(infer_ms),
        "offset": offset,
        "mean_deg": round(float(np.mean(all_errs)), 2) if all_errs else None,
        "median_deg": round(float(np.median(all_errs)), 2) if all_errs else None,
        "p95_deg": round(float(np.percentile(all_errs, 95)), 2) if all_errs else None,
        "n_samples": len(all_errs),
        "per_joint": {j: {"n": len(e), "mean": round(float(np.mean(e)), 2),
                          "median": round(float(np.median(e)), 2)}
                     for j, e in per_joint.items() if e},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", nargs="+", default=["s03", "s10"])
    ap.add_argument("--exercises", nargs="+", default=["squat", "pushup"])
    ap.add_argument("--cams", nargs="+", default=ALL_CAMS)
    ap.add_argument("--backends", nargs="+", default=["mediapipe", "vitpose"],
                     choices=["mediapipe", "vitpose"])
    ap.add_argument("--stride", type=int, default=8,
                     help="process every Nth native frame (ViTPose+ CPU inference "
                          "is ~1.2s/call -- keep this high unless you have hours)")
    ap.add_argument("--fps", type=float, default=50.0)
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for backend_name in args.backends:
        for subj in args.subjects:
            for ex in args.exercises:
                print(f"[{backend_name}] {subj}/{ex} ...")
                t0 = time.time()
                r = run_backend(subj, ex, args.cams, backend_name, args.stride, args.fps)
                r["wall_s"] = round(time.time() - t0, 1)
                results.append(r)
                print(f"    mean={r['mean_deg']} median={r['median_deg']} "
                      f"p95={r['p95_deg']} n={r['n_samples']} "
                      f"infer={r['ms_per_infer_median']}ms/call  "
                      f"({r['frames_triangulated']}/{r['frames_seen']} frames fused, "
                      f"{r['wall_s']}s wall)")

    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2))

    print("\n=== backend comparison (pooled across subjects/exercises) ===")
    for backend_name in args.backends:
        rs = [r for r in results if r["backend"] == backend_name]
        errs = [r["mean_deg"] for r in rs if r["mean_deg"] is not None]
        infers = [r["ms_per_infer_median"] for r in rs if r["ms_per_infer_median"]]
        print(f"{backend_name:10s} clips={len(rs)}  "
              f"mean_of_means={np.mean(errs):.2f} deg  "
              f"median_infer={np.median(infers):.0f} ms/call")
    print(f"\nwrote {OUT_DIR}/results.json")


if __name__ == "__main__":
    main()
