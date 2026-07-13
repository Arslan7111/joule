import numpy as np
from .config import KEYPOINT_IDX, ANGLE_DEFINITIONS, POSE_CONF_THRESHOLD


def compute_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    """Angle in degrees at point b, given three 2-D points a, b, c."""
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return None
    cos_val = np.dot(ba, bc) / (norm_ba * norm_bc)
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def compute_trunk_lean(
    keypoints: np.ndarray,
    conf_thresh: float = POSE_CONF_THRESHOLD,
) -> float | None:
    """
    Angle in degrees between the shoulder–hip midpoint line and vertical.
    0° = fully upright, 90° = horizontal (completely folded forward).

    Requires both shoulders and both hips above the confidence threshold so
    the midpoints are stable even when one side is partially occluded.
    """
    ls = keypoints[KEYPOINT_IDX['left_shoulder']]
    rs = keypoints[KEYPOINT_IDX['right_shoulder']]
    lh = keypoints[KEYPOINT_IDX['left_hip']]
    rh = keypoints[KEYPOINT_IDX['right_hip']]

    if any(kp[2] < conf_thresh for kp in (ls, rs, lh, rh)):
        return None

    shoulder_mid = (ls[:2] + rs[:2]) / 2.0
    hip_mid      = (lh[:2] + rh[:2]) / 2.0

    trunk_vec = shoulder_mid - hip_mid   # points hip → shoulder
    norm = np.linalg.norm(trunk_vec)
    if norm < 1e-6:
        return None

    # In image coordinates y increases downward, so "up" is (0, -1).
    cos_val = np.dot(trunk_vec / norm, np.array([0.0, -1.0]))
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def compute_all_angles(
    keypoints: np.ndarray,
    conf_thresh: float = POSE_CONF_THRESHOLD,
) -> dict[str, float | None]:
    """
    keypoints: (17, 3) array — columns are [x, y, confidence].

    Returns a dict with 9 entries:
      left_shoulder, right_shoulder,
      left_elbow,    right_elbow,
      left_hip,      right_hip,
      left_knee,     right_knee,
      trunk_lean
    """
    angles: dict[str, float | None] = {}

    for name, (a_name, b_name, c_name) in ANGLE_DEFINITIONS.items():
        a = keypoints[KEYPOINT_IDX[a_name]]
        b = keypoints[KEYPOINT_IDX[b_name]]
        c = keypoints[KEYPOINT_IDX[c_name]]
        if a[2] < conf_thresh or b[2] < conf_thresh or c[2] < conf_thresh:
            angles[name] = None
        else:
            angles[name] = compute_angle(a[:2], b[:2], c[:2])

    angles['trunk_lean'] = compute_trunk_lean(keypoints, conf_thresh)
    return angles
