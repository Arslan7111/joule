"""
Spike: silhouette-based back-rounding / spinal-flexion metric.

Motivation (see plan `lovely-foraging-firefly.md`, workstream A). `src/form.py`
measures trunk *lean* — the angle of the rigid shoulder->hip segment. It cannot
see spinal *curvature*: a flat-back hip hinge and a rounded-back hip hinge have
nearly the same shoulder-hip angle. Rounding is the injury-relevant signal for
the deadlift / hinge family and the thing `src/risk.py` is pitched to catch but
currently can't. COCO-17 has no spine landmarks, so — following Jeremy Park's
deadlift project — this spike gets the back *contour* from MediaPipe's person
segmentation mask and fits it against the shoulder->hip chord.

What this proves (or disproves) before any pipeline integration:

  1. Feasibility  — a stable, low-noise per-frame back-curvature scalar can be
     pulled from the MediaPipe silhouette on real Fit3D footage.
  2. Signal      — the metric has a consistent within-rep trajectory that is
     repeatable across all 8 Fit3D subjects, and `deadlift` (a deep hip hinge)
     shows more back-shape change under load than `squat`.
  3. Independence — it is not predictable from `trunk_lean` (low correlation),
     i.e. it is a genuinely new measurement, not a repackaging.

Fit3D is validation-license only — this script only *reads* it, never trains.

Usage:
    python tools/spike_back_round.py                       # all 8 subjects, 3 exercises
    python tools/spike_back_round.py --subjects s03        # one subject, quick
    python tools/spike_back_round.py --exercises deadlift --stride 3

Outputs (per run) into validation_results_backround/:
    <subject>_<exercise>_roundness_map.png   per-frame bow vs rep phase, one line per rep
    <subject>_<exercise>_back_shape.png      back-edge contour at each rep's bottom, mean +/- sd
    summary.json                             per-clip + pooled stats and the decision-gate verdict
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions as _MPB

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.config import KEYPOINT_IDX, MP_TO_COCO, POSE_CONF_THRESHOLD   # noqa: E402
from src.pose import _DEFAULT_MODEL                                     # noqa: E402
from src.angles import compute_trunk_lean                              # noqa: E402
from src.state_machine import StateMachine                             # noqa: E402

FIT3D_ROOT = _ROOT / "Fit3D" / "fit3d_train" / "train"
OUT_DIR = _ROOT / "validation_results_backround"
CAMS = ["50591643", "58860488", "60457274", "65906101"]
DEFAULT_SUBJECTS = ["s03", "s04", "s05", "s07", "s08", "s09", "s10", "s11"]
DEFAULT_EXERCISES = ["deadlift", "squat", "dumbbell_reverse_lunge"]

N_CONTOUR = 24            # samples along the shoulder->hip chord
MARCH_FRAC = 0.7          # max march distance as a fraction of chord length


# ─────────────────────────── geometry ────────────────────────────

def _mid(kps: np.ndarray, a: str, b: str) -> np.ndarray:
    return (kps[KEYPOINT_IDX[a], :2] + kps[KEYPOINT_IDX[b], :2]) / 2.0


def _torso_ok(kps: np.ndarray) -> bool:
    idx = [KEYPOINT_IDX[k] for k in
           ("left_shoulder", "right_shoulder", "left_hip", "right_hip")]
    return bool(np.all(kps[idx, 2] >= POSE_CONF_THRESHOLD))


def _back_sign(mask, sm, hm, perp, length) -> np.ndarray:
    """Orient `perp` toward the posterior side of the torso."""
    h, w = mask.shape
    c = (sm + hm) / 2.0
    # Sample silhouette thickness a short way to each side, at the torso middle.
    depths = {}
    for s in (+1.0, -1.0):
        d = 0.0
        while d < 0.6 * length:
            d += 1.0
            p = c + s * perp * d
            px, py = int(round(p[0])), int(round(p[1]))
            if not (0 <= px < w and 0 <= py < h) or mask[py, px] < 0.5:
                break
        depths[s] = d
    # The back is the thicker side (spinal erectors + glute mass vs. the flatter
    # abdominal front) for a torso filmed side-on.
    return perp if depths[+1.0] >= depths[-1.0] else -perp


def back_contour(mask: np.ndarray, kps: np.ndarray,
                 n: int = N_CONTOUR) -> np.ndarray | None:
    """
    Signed perpendicular offset (normalised by torso length) of the *posterior
    boundary of the torso cross-section* from the shoulder->hip chord, sampled at
    `n` stations along the chord.

    At each station a full perpendicular scan (+/- 0.5 L) locates the contiguous
    silhouette run that contains the chord point; the posterior end of that run
    is the back-edge point. This deliberately does not walk out through arms, the
    barbell, or the far leg the way an unbounded outward march does.

    Returns None if the torso keypoints or mask are unusable.
    """
    if mask is None or not _torso_ok(kps):
        return None

    sm = _mid(kps, "left_shoulder", "right_shoulder")
    hm = _mid(kps, "left_hip", "right_hip")
    chord = hm - sm
    length = float(np.linalg.norm(chord))
    if length < 20.0:                     # torso < 20 px: pose too small/bad
        return None
    u = chord / length
    perp = np.array([-u[1], u[0]])

    # "Back" = away from the knees (anterior); fall back to the thicker side.
    kidx = [KEYPOINT_IDX["left_knee"], KEYPOINT_IDX["right_knee"]]
    if np.all(kps[kidx, 2] >= POSE_CONF_THRESHOLD):
        knee_mid = _mid(kps, "left_knee", "right_knee")
        if np.dot(knee_mid - (sm + hm) / 2.0, perp) > 0:
            perp = -perp
    else:
        perp = _back_sign(mask, sm, hm, perp, length)

    h, w = mask.shape
    reach = int(round(0.5 * length))
    offs = np.full(n, np.nan, dtype=np.float32)
    for i in range(n):
        base = sm + ((i + 0.5) / n) * chord
        # scan v from -reach..+reach along perp; +v is posterior
        vs = np.arange(-reach, reach + 1)
        pts = base[None, :] + vs[:, None] * perp[None, :]
        xi = np.round(pts[:, 0]).astype(int)
        yi = np.round(pts[:, 1]).astype(int)
        inb = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        prof = np.zeros(len(vs), dtype=bool)
        prof[inb] = mask[yi[inb], xi[inb]] >= 0.5
        z = np.where(vs == 0)[0][0]        # index of the chord point
        if not prof[z]:
            continue
        # posterior extent = contiguous True run from z toward +v
        j = z
        while j + 1 < len(prof) and prof[j + 1]:
            j += 1
        # require the run not to hit the scan boundary (would mean we clipped)
        if j == len(prof) - 1:
            continue
        offs[i] = vs[j] / length
    return offs


def centroid_offset(mask: np.ndarray, kps: np.ndarray) -> float:
    """
    Signed offset (normalised by torso length) of the torso-mask centroid from
    the shoulder->hip chord, along the posterior perpendicular. A back that
    rounds under load shifts torso mass posteriorly => more positive. Uses the
    whole mask region in the shoulder..hip band (robust, no edge tracing).
    """
    if mask is None or not _torso_ok(kps):
        return np.nan
    sm = _mid(kps, "left_shoulder", "right_shoulder")
    hm = _mid(kps, "left_hip", "right_hip")
    chord = hm - sm
    length = float(np.linalg.norm(chord))
    if length < 20.0:
        return np.nan
    u = chord / length
    perp = np.array([-u[1], u[0]])
    kidx = [KEYPOINT_IDX["left_knee"], KEYPOINT_IDX["right_knee"]]
    if np.all(kps[kidx, 2] >= POSE_CONF_THRESHOLD):
        if np.dot(_mid(kps, "left_knee", "right_knee") - (sm + hm) / 2.0, perp) > 0:
            perp = -perp
    else:
        perp = _back_sign(mask, sm, hm, perp, length)

    h, w = mask.shape
    ys, xs = np.nonzero(mask >= 0.5)
    if len(xs) < 50:
        return np.nan
    rel = np.stack([xs - sm[0], ys - sm[1]], axis=1).astype(np.float32)
    s = rel @ u                       # position along the chord (0..length in-band)
    band = (s >= 0.0) & (s <= length)
    if band.sum() < 50:
        return np.nan
    v = rel[band] @ perp             # posterior offset of each pixel
    # centre reference = the chord's own perpendicular position (0 by construction)
    return float(np.mean(v) / length)


def bow(offs: np.ndarray | None) -> float:
    """
    Sagitta of the posterior-boundary curve relative to the straight line joining
    its own first and last valid stations, normalised by torso length. Positive
    => the back bows outward past a straight line (rounded); ~0 => flat/neutral.
    NaN if too sparse.
    """
    if offs is None:
        return np.nan
    ok = np.isfinite(offs)
    if ok.sum() < max(6, N_CONTOUR // 2):
        return np.nan
    idx = np.arange(len(offs), dtype=np.float32)[ok]
    val = offs[ok]
    base = val[0] + (val[-1] - val[0]) * (idx - idx[0]) / (idx[-1] - idx[0])
    return float(np.max(val - base))


# ─────────────────────────── pose + segmentation ─────────────────
# The MediaPipe 1.0.0 Windows build aborts when segmentation masks are requested
# on a *cropped* input (1-vs-4 ChannelSize check inside the mask calculator).
# Full-frame input is stable, and for a single-subject Fit3D clip num_poses=1
# locates the lifter without a separate detector.

class _Pose:
    def __init__(self):
        self._lm = mp_vision.PoseLandmarker.create_from_options(
            mp_vision.PoseLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=_DEFAULT_MODEL, delegate=_MPB.Delegate.CPU),
                running_mode=mp_vision.RunningMode.IMAGE, num_poses=1,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_segmentation_masks=True,
            ))

    def run(self, frame) -> tuple[np.ndarray | None, np.ndarray | None]:
        h, w = frame.shape[:2]
        res = self._lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                       data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        if not res.pose_landmarks:
            return None, None
        lms = res.pose_landmarks[0]
        kps = np.zeros((17, 3), dtype=np.float32)
        for mp_idx, coco_idx in MP_TO_COCO.items():
            lm = lms[mp_idx]
            kps[coco_idx] = (lm.x * w, lm.y * h,
                             float(lm.visibility if lm.visibility is not None else 0.0))
        mask = None
        if res.segmentation_masks:
            mask = np.asarray(res.segmentation_masks[0].numpy_view(),
                              dtype=np.float32).squeeze()
        return kps, mask


# ─────────────────────────── per-clip run ────────────────────────

def _side_score(video: Path, pose: _Pose, probe: int = 20) -> float:
    """Lower = more side-on (shoulders stacked in x relative to torso height)."""
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ratios = []
    for f in np.linspace(n * 0.2, n * 0.8, probe).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, frame = cap.read()
        if not ok:
            continue
        kps, _ = pose.run(frame)
        if kps is None or not _torso_ok(kps):
            continue
        sh_w = abs(kps[KEYPOINT_IDX["left_shoulder"], 0]
                   - kps[KEYPOINT_IDX["right_shoulder"], 0])
        torso_h = np.linalg.norm(_mid(kps, "left_shoulder", "right_shoulder")
                                 - _mid(kps, "left_hip", "right_hip"))
        if torso_h > 1e-3:
            ratios.append(sh_w / torso_h)
    cap.release()
    return float(np.median(ratios)) if ratios else np.inf


def run_clip(subject: str, exercise: str, stride: int,
             max_seconds: float | None) -> dict | None:
    vids = {c: FIT3D_ROOT / subject / "videos" / c / f"{exercise}.mp4" for c in CAMS}
    vids = {c: p for c, p in vids.items() if p.exists()}
    if not vids:
        print(f"  {subject}/{exercise}: no video, skipping")
        return None

    pose = _Pose()
    scored = {c: _side_score(p, pose) for c, p in vids.items()}
    cam = min(scored, key=scored.get)
    print(f"  {subject}/{exercise}: cam {cam} (side-score {scored[cam]:.2f}; "
          f"others {[f'{k}:{v:.2f}' for k, v in scored.items() if k != cam]})")

    cap = cv2.VideoCapture(str(vids[cam]))
    fps = cap.get(cv2.CAP_PROP_FPS) or 50.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    limit = n if max_seconds is None else min(n, int(max_seconds * fps))

    ts, curv, lean, cent = [], [], [], []
    knee, hip = [], []
    contours: list[np.ndarray] = []
    seg_ms = []
    fidx = 0
    while fidx < limit:
        ok, frame = cap.read()
        if not ok:
            break
        if fidx % stride:
            fidx += 1
            continue
        t = fidx / fps
        t0 = time.time()
        kps, mask = pose.run(frame)
        seg_ms.append((time.time() - t0) * 1000.0)
        if kps is None:
            fidx += 1
            continue

        dv = back_contour(mask, kps)
        ts.append(t)
        curv.append(bow(dv))
        cent.append(centroid_offset(mask, kps))
        contours.append(dv if dv is not None else np.full(N_CONTOUR, np.nan))
        lean.append(compute_trunk_lean(kps) or np.nan)

        def _ang(a, b, c):
            pa, pb, pc = (kps[KEYPOINT_IDX[x]] for x in (a, b, c))
            if min(pa[2], pb[2], pc[2]) < POSE_CONF_THRESHOLD:
                return np.nan
            v1, v2 = pa[:2] - pb[:2], pc[:2] - pb[:2]
            cosv = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
            return float(np.degrees(np.arccos(np.clip(cosv, -1, 1))))

        kl = _ang("left_hip", "left_knee", "left_ankle")
        kr = _ang("right_hip", "right_knee", "right_ankle")
        hl = _ang("left_shoulder", "left_hip", "left_knee")
        hr = _ang("right_shoulder", "right_hip", "right_knee")
        knee.append(_nanmean([kl, kr]))
        hip.append(_nanmean([hl, hr]))
        fidx += 1
    cap.release()

    ts = np.array(ts)
    curv = np.array(curv)
    cent = np.array(cent)
    lean = np.array(lean)
    knee = np.array(knee)
    hip = np.array(hip)
    contours = np.array(contours)
    if len(ts) < 20 or np.isfinite(curv).sum() < 10:
        print(f"    too little usable data ({len(ts)} frames), skipping")
        return None

    # Rep segmentation on whichever driver joint actually cycles.
    def _rom(a):
        v = a[np.isfinite(a)]
        return float(np.percentile(v, 90) - np.percentile(v, 10)) if len(v) > 5 else 0.0
    driver, dname = (knee, "knee") if _rom(knee) >= _rom(hip) else (hip, "hip")
    sm = StateMachine()
    for t, a in zip(ts, driver):
        sm.update(None if not np.isfinite(a) else float(a), float(t))
    reps = [(r.start_timestamp, r.timestamp) for r in sm.reps if r.timestamp > r.start_timestamp]

    # Per-rep: bow at the top (max driver angle) vs bottom (min driver angle).
    per_rep = []
    bottom_contours = []
    for (a, b) in reps:
        m = (ts >= a) & (ts <= b)
        if m.sum() < 4 or np.isfinite(curv[m]).sum() < 3:
            continue
        seg_t, seg_c, seg_d = ts[m], curv[m], driver[m]
        if np.isfinite(seg_d).sum() < 3:
            continue
        seg_ce = cent[m]
        i_top = int(np.nanargmax(seg_d))
        i_bot = int(np.nanargmin(seg_d))
        top_bow = _nanmean(seg_c[max(0, i_top - 1):i_top + 2])
        bot_bow = _nanmean(seg_c[max(0, i_bot - 1):i_bot + 2])
        top_cent = _nanmean(seg_ce[max(0, i_top - 1):i_top + 2])
        bot_cent = _nanmean(seg_ce[max(0, i_bot - 1):i_bot + 2])
        per_rep.append({
            "t0": round(float(a), 2), "t1": round(float(b), 2),
            "top_bow": _f(top_bow), "bottom_bow": _f(bot_bow),
            "delta_bow": _f(bot_bow - top_bow),
            "top_cent": _f(top_cent), "bottom_cent": _f(bot_cent),
            "delta_cent": _f(bot_cent - top_cent),
            "trunk_lean_peak": _f(np.nanpercentile(lean[m], 95)),
        })
        cb = contours[m][i_bot]
        if np.isfinite(cb).sum() >= N_CONTOUR // 2:
            bottom_contours.append(cb)

    def _corr(a, b):
        f = np.isfinite(a) & np.isfinite(b)
        return float(np.corrcoef(a[f], b[f])[0, 1]) if f.sum() > 5 else np.nan
    corr = _corr(curv, lean)
    corr_cent = _corr(cent, lean)
    corr_cent_driver = _corr(cent, driver)

    _plots(subject, exercise, ts, curv, driver, reps, bottom_contours)

    return {
        "subject": subject, "exercise": exercise, "cam": cam, "driver": dname,
        "frames": int(len(ts)), "reps": len(per_rep),
        "seg_ms_median": round(float(np.median(seg_ms)), 1) if seg_ms else None,
        "curv_p50": _f(np.nanpercentile(curv, 50)),
        "curv_p95": _f(np.nanpercentile(curv, 95)),
        "curv_finite_frac": round(float(np.isfinite(curv).mean()), 3),
        "cent_finite_frac": round(float(np.isfinite(cent).mean()), 3),
        "corr_curv_trunklean": _f(corr),
        "corr_cent_trunklean": _f(corr_cent),
        "corr_cent_driver": _f(corr_cent_driver),
        "bottom_bow_mean": _f(_nanmean([r["bottom_bow"] for r in per_rep])),
        "top_bow_mean": _f(_nanmean([r["top_bow"] for r in per_rep])),
        "delta_bow_mean": _f(_nanmean([r["delta_bow"] for r in per_rep])),
        "delta_bow_sd": _f(np.std([r["delta_bow"] for r in per_rep
                                   if r["delta_bow"] is not None]) if per_rep else np.nan),
        "bottom_cent_mean": _f(_nanmean([r["bottom_cent"] for r in per_rep])),
        "delta_cent_mean": _f(_nanmean([r["delta_cent"] for r in per_rep])),
        "delta_cent_sd": _f(np.std([r["delta_cent"] for r in per_rep
                                    if r["delta_cent"] is not None]) if per_rep else np.nan),
        "per_rep": per_rep,
    }


def _f(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, 4)


def _nanmean(vals) -> float:
    a = np.asarray(vals, dtype=np.float64)
    a = a[np.isfinite(a)]
    return float(a.mean()) if a.size else np.nan


# ─────────────────────────── plots ───────────────────────────────

def _plots(subject, exercise, ts, curv, driver, reps, bottom_contours):
    OUT_DIR.mkdir(exist_ok=True)
    tag = f"{subject}_{exercise}"

    fig, ax = plt.subplots(figsize=(7, 4))
    for (a, b) in reps:
        m = (ts >= a) & (ts <= b)
        if m.sum() < 4:
            continue
        phase = (ts[m] - a) / (b - a)
        ax.plot(phase, curv[m], lw=1, alpha=0.7)
    ax.set_xlabel("rep phase (0 = start, 1 = end)")
    ax.set_ylabel("back bow  (sagitta / chord length)")
    ax.set_title(f"Back Roundness Map — {tag}  ({len(reps)} reps)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{tag}_roundness_map.png", dpi=110)
    plt.close(fig)

    if bottom_contours:
        arr = np.array(bottom_contours)
        x = np.linspace(0, 1, arr.shape[1])
        with np.errstate(all="ignore"):
            mean = np.nanmean(arr, axis=0)
            sd = np.nanstd(arr, axis=0) if arr.shape[0] > 1 else np.zeros(arr.shape[1])
        mean = np.where(np.isfinite(mean), mean, np.nan)
        fig, ax = plt.subplots(figsize=(7, 4))
        for c in arr:
            ax.plot(x, c, color="0.7", lw=0.8, alpha=0.6)
        ax.plot(x, mean, color="C3", lw=2, label="mean")
        ax.fill_between(x, mean - sd, mean + sd, color="C3", alpha=0.2, label="+/- 1 sd")
        ax.set_xlabel("shoulder -> hip  (position along chord)")
        ax.set_ylabel("back-edge distance / chord length")
        ax.set_title(f"Average Back Shape at rep bottom — {tag}  (n={len(arr)})")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"{tag}_back_shape.png", dpi=110)
        plt.close(fig)


# ─────────────────────────── main ────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", nargs="+", default=DEFAULT_SUBJECTS)
    ap.add_argument("--exercises", nargs="+", default=DEFAULT_EXERCISES)
    ap.add_argument("--stride", type=int, default=2, help="process every Nth frame")
    ap.add_argument("--max-seconds", type=float, default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for subj in args.subjects:
        for ex in args.exercises:
            print(f"[{subj}/{ex}]")
            try:
                r = run_clip(subj, ex, args.stride, args.max_seconds)
            except Exception as exc:                       # noqa: BLE001
                print(f"    FAILED: {exc}")
                import traceback
                traceback.print_exc()
                r = None
            if r:
                results.append(r)
                print(f"    reps={r['reps']}  curv_p50={r['curv_p50']}  "
                      f"curv_p95={r['curv_p95']}  corr(trunk_lean)={r['corr_curv_trunklean']}  "
                      f"delta_bow={r['delta_bow_mean']}+/-{r['delta_bow_sd']}  "
                      f"seg={r['seg_ms_median']}ms")

    # ── decision-gate summary ──
    by_ex: dict[str, list] = {}
    for r in results:
        by_ex.setdefault(r["exercise"], []).append(r)

    def _col(rs, key):
        return [r[key] for r in rs if r.get(key) is not None]

    pooled = {}
    for ex, rs in by_ex.items():
        c = _col(rs, "corr_curv_trunklean")
        pooled[ex] = {
            "n_subjects": len(rs),
            "reps_total": sum(r["reps"] for r in rs),
            "bottom_bow_mean_of_means": _f(_nanmean(_col(rs, "bottom_bow_mean"))),
            "top_bow_mean_of_means": _f(_nanmean(_col(rs, "top_bow_mean"))),
            "delta_bow_mean_of_means": _f(_nanmean(_col(rs, "delta_bow_mean"))),
            "delta_bow_sd_across_subjects": _f(np.std(_col(rs, "delta_bow_mean")) if len(_col(rs, "delta_bow_mean")) > 1 else np.nan),
            "abs_corr_trunklean_mean": _f(_nanmean([abs(v) for v in c])),
            "curv_p50_mean": _f(_nanmean(_col(rs, "curv_p50"))),
            "curv_p95_mean": _f(_nanmean(_col(rs, "curv_p95"))),
        }

    abs_corrs = [abs(r["corr_curv_trunklean"]) for r in results
                 if r["corr_curv_trunklean"] is not None]
    dl = pooled.get("deadlift", {}).get("bottom_bow_mean_of_means")
    sq = pooled.get("squat", {}).get("bottom_bow_mean_of_means")
    verdict = {
        "feasible": bool(results) and all(r["curv_finite_frac"] >= 0.5 for r in results),
        "independent_of_trunk_lean": bool(abs_corrs) and float(np.mean(abs_corrs)) < 0.6,
        "mean_abs_corr_trunklean": _f(np.mean(abs_corrs)) if abs_corrs else None,
        "deadlift_bottom_bow_gt_squat": bool(dl is not None and sq is not None and dl > sq),
    }

    summary = {"pooled_by_exercise": pooled, "verdict": verdict, "clips": results}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== decision gate ===")
    print(json.dumps({"pooled_by_exercise": pooled, "verdict": verdict}, indent=2))
    print(f"\nwrote {OUT_DIR}/summary.json and per-clip PNGs")


if __name__ == "__main__":
    main()
