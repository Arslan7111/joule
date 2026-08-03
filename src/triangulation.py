"""
Multi-view triangulation: 2D keypoints from calibrated cameras → 3D skeleton.

Given the same person seen by 2+ calibrated, synchronized cameras, each
joint is triangulated by DLT (direct linear transform) from the views where
it is confidently visible.  3D joint angles are then true anatomical angles,
independent of any camera's perspective — this is what removes the
angle-compression problem inherent to single-view measurement.

World frame convention: Z is up.

Calibration comes from tools/calibrate.py (checkerboard), which produces a
.npz per camera pair with K (intrinsics), R, t (extrinsics).
"""

from dataclasses import dataclass

import numpy as np

from .config import ANGLE_DEFINITIONS, KEYPOINT_IDX, POSE_CONF_THRESHOLD
from .angles import compute_angle   # dimension-agnostic (works for 3D)


@dataclass
class CalibratedCamera:
    """One camera's calibration. R, t map world coordinates to camera frame."""
    K: np.ndarray                  # (3, 3) intrinsics
    R: np.ndarray                  # (3, 3) rotation, world → camera
    t: np.ndarray                  # (3,)  translation, world → camera

    @property
    def P(self) -> np.ndarray:     # (3, 4) projection matrix
        return self.K @ np.hstack([self.R, self.t.reshape(3, 1)])

    def project(self, points_3d: np.ndarray) -> np.ndarray:
        """(N, 3) world points → (N, 2) pixel coordinates."""
        pts = np.asarray(points_3d, dtype=np.float64)
        cam = (self.R @ pts.T).T + self.t
        uvw = (self.K @ cam.T).T
        return uvw[:, :2] / uvw[:, 2:3]


def _triangulate_dlt(cams: list[CalibratedCamera], pts_2d: list[np.ndarray]) -> np.ndarray:
    """DLT triangulation of one point from ≥2 views → (3,) world point."""
    A = []
    for cam, (u, v) in zip(cams, pts_2d):
        P = cam.P
        A.append(u * P[2] - P[0])
        A.append(v * P[2] - P[1])
    _, _, vt = np.linalg.svd(np.asarray(A))
    X = vt[-1]
    return X[:3] / X[3]


TRIANGULATION_CONF = 0.35   # per-view visibility to contribute a joint
                            # (lower than the 2D display threshold: agreement
                            # between views is itself evidence of correctness)


def _reproj_errors(cams, pts, X) -> list[float]:
    return [
        float(np.linalg.norm(cam.project(X[None])[0] - pt))
        for cam, pt in zip(cams, pts)
    ]


def triangulate_skeleton(
    cameras: list[CalibratedCamera],
    keypoints_2d: list[np.ndarray],
    conf_thresh: float = TRIANGULATION_CONF,
    max_reproj_px: float = 25.0,
) -> np.ndarray:
    """
    cameras:      calibrated cameras that saw the person this frame
    keypoints_2d: matching list of (17, 3) [x, y, visibility] arrays

    Returns (17, 4) [X, Y, Z, confidence].  A joint's confidence is 0 when
    it could not be triangulated consistently from at least two views.

    A bad 2D detection in one view must not veto the joint: if the all-view
    solution reprojects poorly, every view pair is tried and the most
    consistent pair wins (RANSAC-lite for the small-view-count regime).
    """
    out = np.zeros((17, 4), dtype=np.float64)

    for j in range(17):
        views = [
            (cam, kps[j, :2], kps[j, 2])
            for cam, kps in zip(cameras, keypoints_2d)
            if kps[j, 2] >= conf_thresh
        ]
        if len(views) < 2:
            continue

        cams = [v[0] for v in views]
        pts = [v[1] for v in views]

        X = _triangulate_dlt(cams, pts)
        errs = _reproj_errors(cams, pts, X)
        used_conf = [v[2] for v in views]

        if max(errs) > max_reproj_px and len(views) > 2:
            # Drop outlier views: best-consistent pair wins
            best = None
            for a in range(len(views)):
                for b in range(a + 1, len(views)):
                    Xp = _triangulate_dlt([cams[a], cams[b]], [pts[a], pts[b]])
                    e = max(_reproj_errors([cams[a], cams[b]],
                                           [pts[a], pts[b]], Xp))
                    if best is None or e < best[0]:
                        best = (e, Xp, [views[a][2], views[b][2]])
            if best is not None and best[0] <= max_reproj_px:
                X, used_conf = best[1], best[2]
                errs = [best[0]]

        if max(errs) > max_reproj_px:
            continue

        out[j, :3] = X
        out[j, 3] = float(np.mean(used_conf))

    return out


WORLD_UP = np.array([0.0, 0.0, 1.0])   # default world vertical (Z up).
                                        # Panoptic uses Y-down: up = (0, -1, 0).


def compute_trunk_lean_3d(
    kps3d: np.ndarray,
    conf_thresh: float = POSE_CONF_THRESHOLD,
    up: np.ndarray = WORLD_UP,
) -> float | None:
    """Angle of the hip→shoulder line from world vertical, degrees."""
    ls = kps3d[KEYPOINT_IDX['left_shoulder']]
    rs = kps3d[KEYPOINT_IDX['right_shoulder']]
    lh = kps3d[KEYPOINT_IDX['left_hip']]
    rh = kps3d[KEYPOINT_IDX['right_hip']]
    if any(k[3] < conf_thresh for k in (ls, rs, lh, rh)):
        return None
    trunk = (ls[:3] + rs[:3]) / 2 - (lh[:3] + rh[:3]) / 2
    n = np.linalg.norm(trunk)
    if n < 1e-9:
        return None
    cos_val = np.dot(trunk / n, up / np.linalg.norm(up))
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def compute_all_angles_3d(
    kps3d: np.ndarray,
    conf_thresh: float = POSE_CONF_THRESHOLD,
    up: np.ndarray = WORLD_UP,
) -> dict[str, float | None]:
    """True 3D joint angles from a triangulated (17, 4) skeleton.
    Same joints as the 2D path, so downstream code is unchanged."""
    angles: dict[str, float | None] = {}
    for name, (a_n, b_n, c_n) in ANGLE_DEFINITIONS.items():
        a = kps3d[KEYPOINT_IDX[a_n]]
        b = kps3d[KEYPOINT_IDX[b_n]]
        c = kps3d[KEYPOINT_IDX[c_n]]
        if a[3] < conf_thresh or b[3] < conf_thresh or c[3] < conf_thresh:
            angles[name] = None
        else:
            angles[name] = compute_angle(a[:3], b[:3], c[:3])
    angles['trunk_lean'] = compute_trunk_lean_3d(kps3d, conf_thresh, up)
    return angles


# ── Cross-view association sanity check ──────────────────────────────────
#
# Cross-view person association (src/fusion.py) is decided purely by
# appearance embedding via the Re-ID gallery — nothing geometric. Two
# similarly-dressed people at different cameras can match to the same
# person_id and get "triangulated" into one confident-looking but bogus 3D
# skeleton. A genuine single person triangulates cleanly on nearly every
# jointly-visible joint; two different people's keypoints generally do not,
# EXCEPT that with exactly 2 cameras the epipolar constraint is only 1
# degree of freedom per point (a wrong match just has to land near the
# epipolar line, not at an exact point), so triangulate_skeleton's own
# lenient max_reproj_px (25px, tuned to tolerate real pose-estimation
# noise) is measurably too loose to catch this reliably — confirmed on a
# synthetic two-different-people case that still passed 11/17 joints at
# 25px. This runs its own independent, much tighter reprojection check
# rather than reusing the lenient triangulation's output.

CONSISTENCY_MAX_REPROJ_PX = 6.0    # tight — real matches should clear this
                                    # comfortably; only tested on synthetic
                                    # (noise-free) data so far, see ROADMAP.md
CONSISTENCY_MIN_ATTEMPTED = 4      # need this many jointly-visible joints to judge
CONSISTENCY_MIN_SUCCESS_FRAC = 0.5 # this fraction must triangulate cleanly


def cross_view_consistent(
    cameras: list[CalibratedCamera],
    keypoints_2d: list[np.ndarray],
    conf_thresh: float = TRIANGULATION_CONF,
    max_reproj_px: float = CONSISTENCY_MAX_REPROJ_PX,
    min_attempted: int = CONSISTENCY_MIN_ATTEMPTED,
    min_success_frac: float = CONSISTENCY_MIN_SUCCESS_FRAC,
) -> bool:
    """
    Independent, tight-tolerance triangulation check across the 2D inputs
    that would be fused for one person_id. Returns False when too few
    jointly-visible joints triangulate cleanly at max_reproj_px — evidence
    the views likely show two different people, not viewpoint noise on a
    single one. Returns True (benefit of the doubt) when too few joints are
    jointly visible to judge either way, e.g. heavy occlusion in one view.
    """
    attempted = 0
    succeeded = 0
    n_joints = keypoints_2d[0].shape[0]
    for j in range(n_joints):
        views = [
            (cam, kps[j, :2]) for cam, kps in zip(cameras, keypoints_2d)
            if kps[j, 2] >= conf_thresh
        ]
        if len(views) < 2:
            continue
        attempted += 1
        cams_j = [v[0] for v in views]
        pts_j = [v[1] for v in views]
        X = _triangulate_dlt(cams_j, pts_j)
        if max(_reproj_errors(cams_j, pts_j, X)) <= max_reproj_px:
            succeeded += 1

    if attempted < min_attempted:
        return True
    return (succeeded / attempted) >= min_success_frac


# ── Frontal-plane injury signals (only measurable in 3D) ────────────────────

def knee_valgus_angle(
    kps3d: np.ndarray,
    side: str,
    conf_thresh: float = POSE_CONF_THRESHOLD,
    up: np.ndarray = WORLD_UP,
) -> float | None:
    """
    Frontal-plane knee deviation in degrees: the hip–knee–ankle angle
    measured after projecting the leg onto the person's own frontal plane
    (spanned by the hip line and world vertical), reported as deviation
    from a straight line.  Knee flexion is a sagittal-plane motion and is
    projected out, so a clean deep squat reads ~0° while knees caving
    inward (valgus) reads positive.  Invisible to a single side camera —
    this is the multi-camera payoff for injury screening.
    """
    hip = kps3d[KEYPOINT_IDX[f'{side}_hip']]
    knee = kps3d[KEYPOINT_IDX[f'{side}_knee']]
    ankle = kps3d[KEYPOINT_IDX[f'{side}_ankle']]
    lh = kps3d[KEYPOINT_IDX['left_hip']]
    rh = kps3d[KEYPOINT_IDX['right_hip']]
    if any(k[3] < conf_thresh for k in (hip, knee, ankle, lh, rh)):
        return None

    # Person's frontal plane: medio-lateral axis (hip line) × world vertical
    ml = lh[:3] - rh[:3]
    n = np.linalg.norm(ml)
    if n < 1e-9:
        return None
    ml /= n
    up_n = up / np.linalg.norm(up)

    def frontal(p: np.ndarray) -> np.ndarray:
        return np.array([np.dot(p, ml), np.dot(p, up_n)])

    a2 = compute_angle(frontal(hip[:3]), frontal(knee[:3]), frontal(ankle[:3]))
    if a2 is None:
        return None
    return 180.0 - a2
