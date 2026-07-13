import cv2
import numpy as np

from .config import (
    ANGLE_DEFINITIONS,
    EXERCISE_ANGLES,
    KEYPOINT_IDX,
    POSE_CONF_THRESHOLD,
    SKELETON_CONNECTIONS,
)

_TRACK_COLORS = [
    (255, 80,  80),
    (80,  255, 80),
    (80,  80,  255),
    (255, 255, 80),
    (255, 80,  255),
    (80,  255, 255),
    (180, 80,  255),
    (255, 160, 80),
]

_STATE_COLORS = {
    'waiting':    (160, 160, 160),
    'descending': (0,   200, 255),
    'bottom':     (0,   0,   255),
    'ascending':  (0,   220, 100),
}


def _track_color(track_id: int) -> tuple:
    return _TRACK_COLORS[track_id % len(_TRACK_COLORS)]


def _identity_color(track_id: int, person_label: str | None) -> tuple:
    """Stable color per person when Re-ID is active — the tracker recreates
    track ids constantly, and color-by-track makes the overlay flicker."""
    if person_label:
        return _TRACK_COLORS[hash(person_label) % len(_TRACK_COLORS)]
    return _track_color(track_id)


def _text(img, text, pos, scale=0.5, color=(255, 255, 255), thickness=1):
    """Draw text with a dark outline for readability on any background."""
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def _draw_angle_at_joint(
    img: np.ndarray,
    joint_xy: np.ndarray,
    a_xy: np.ndarray,
    c_xy: np.ndarray,
    angle_deg: float,
    color: tuple,
    radius: int = 28,
) -> None:
    """
    Draw an arc between the two limb vectors at the joint, with the angle
    value placed along the arc.
    """
    jx, jy = int(joint_xy[0]), int(joint_xy[1])

    va = a_xy - joint_xy
    vc = c_xy - joint_xy

    # Angles from positive x-axis in OpenCV image coords (y-down → atan2 unchanged)
    angle_a = float(np.degrees(np.arctan2(va[1], va[0])))
    angle_c = float(np.degrees(np.arctan2(vc[1], vc[0])))

    start_a = min(angle_a, angle_c)
    end_a   = max(angle_a, angle_c)
    # Always take the shorter arc
    if end_a - start_a > 180:
        start_a, end_a = end_a, start_a + 360

    cv2.ellipse(img, (jx, jy), (radius, radius), 0,
                start_a, end_a, color, 1, cv2.LINE_AA)

    # Label position: midpoint of the arc, pushed outward
    mid_rad = np.radians((start_a + end_a) / 2)
    tx = int(jx + (radius + 10) * np.cos(mid_rad))
    ty = int(jy + (radius + 10) * np.sin(mid_rad))
    _text(img, f"{angle_deg:.0f}", (tx, ty), scale=0.45, color=color, thickness=1)


def draw_frame(
    frame: np.ndarray,
    tracks: list[tuple],
    keypoints_map: dict,
    angles_map: dict,
    rep_counts: dict,
    sm_states: dict | None = None,
    exercise: str = 'both',
    person_labels: dict | None = None,
) -> np.ndarray:
    vis = frame.copy()
    h, w = vis.shape[:2]
    primary = set(EXERCISE_ANGLES.get(exercise, EXERCISE_ANGLES['both']))

    for track_id, x1, y1, x2, y2, _ in tracks:
        who = (person_labels or {}).get(track_id)
        color = _identity_color(track_id, who)
        xi1, yi1, xi2, yi2 = int(x1), int(y1), int(x2), int(y2)

        state_str = (sm_states or {}).get(track_id, 'waiting')

        # Bounding box in the stable identity color; the rep state is shown
        # in the label text, not by recoloring the box (which strobes when
        # the state cycles quickly).
        cv2.rectangle(vis, (xi1, yi1), (xi2, yi2), color, 2)

        state_color = _STATE_COLORS.get(state_str, (255, 255, 255))
        _text(vis, f"{who or f'ID {track_id}'} · {state_str.upper()}",
              (xi1 + 4, max(yi1 - 6, 14)), scale=0.5, color=state_color, thickness=1)

        # Rep count — large, just above the box
        if track_id in rep_counts:
            rc = rep_counts[track_id]
            parts = [f"{k.replace('_body','').upper()}  {v}" for k, v in rc.items()]
            _text(vis, "   ".join(parts),
                  (xi1 + 4, max(yi1 - 24, 28)), scale=1.0,
                  color=(255, 255, 255), thickness=2)

        # ── Skeleton ───────────────────────────────────────────────────────
        if track_id not in keypoints_map:
            continue
        kps = keypoints_map[track_id]

        # Limb lines
        for a_idx, b_idx in SKELETON_CONNECTIONS:
            if kps[a_idx, 2] >= POSE_CONF_THRESHOLD and kps[b_idx, 2] >= POSE_CONF_THRESHOLD:
                pa = (int(kps[a_idx, 0]), int(kps[a_idx, 1]))
                pb = (int(kps[b_idx, 0]), int(kps[b_idx, 1]))
                cv2.line(vis, pa, pb, color, 3, cv2.LINE_AA)

        # Joint dots
        for i in range(17):
            if kps[i, 2] >= POSE_CONF_THRESHOLD:
                cx, cy = int(kps[i, 0]), int(kps[i, 1])
                if 0 <= cx < w and 0 <= cy < h:
                    cv2.circle(vis, (cx, cy), 5, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(vis, (cx, cy), 5, color, 1, cv2.LINE_AA)

        # ── Angle arcs at joints ──────────────────────────────────────────
        if track_id not in angles_map:
            continue
        angles = angles_map[track_id]

        for angle_name, (a_name, b_name, c_name) in ANGLE_DEFINITIONS.items():
            val = angles.get(angle_name)
            if val is None:
                continue

            a_kp = kps[KEYPOINT_IDX[a_name]]
            b_kp = kps[KEYPOINT_IDX[b_name]]
            c_kp = kps[KEYPOINT_IDX[c_name]]
            if (a_kp[2] < POSE_CONF_THRESHOLD or
                    b_kp[2] < POSE_CONF_THRESHOLD or
                    c_kp[2] < POSE_CONF_THRESHOLD):
                continue

            # Primary angles get a larger radius and brighter arc
            is_primary = angle_name in primary
            arc_color  = (255, 255, 255) if is_primary else (120, 120, 120)
            arc_radius = 32 if is_primary else 20

            _draw_angle_at_joint(
                vis,
                b_kp[:2], a_kp[:2], c_kp[:2],
                val, arc_color, radius=arc_radius,
            )

        # Trunk lean — special label at hip midpoint
        tl = angles.get('trunk_lean')
        if tl is not None and 'trunk_lean' in primary:
            lh = kps[KEYPOINT_IDX['left_hip']]
            rh = kps[KEYPOINT_IDX['right_hip']]
            if lh[2] >= POSE_CONF_THRESHOLD and rh[2] >= POSE_CONF_THRESHOLD:
                mx = int((lh[0] + rh[0]) / 2)
                my = int((lh[1] + rh[1]) / 2)
                _text(vis, f"trunk {tl:.0f}", (mx + 6, my),
                      scale=0.45, color=(255, 255, 255), thickness=1)

    return vis
