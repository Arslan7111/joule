"""
Live multi-camera fusion: N synchronized views of ONE station → 3D analysis.

FusedCameraProcessor mirrors CameraProcessor's per-person logic, but each
frame it:

  1. detects + tracks people independently in every view
  2. resolves each view-track to a session person via the Re-ID gallery
     (the same person seen in two views gets the same person_id — this is
     the cross-view association)
  3. triangulates every person seen in ≥2 views into a 3D skeleton and
     computes true 3D joint angles (single-view fallback: 2D angles, so
     analysis continues when a view drops the person)
  4. feeds the same per-person state machines / classifier / form scorer
     as the 2D pipeline, plus frontal-plane knee-valgus series that only
     exist in 3D

Synchronization: sources are read in lockstep, one frame each per
iteration — correct for pre-synchronized recordings (Panoptic, clap-aligned
phone clips trimmed to the same start). Live RTSP streams need timestamp
alignment upstream; not handled here yet.

Rig file (--fuse rig.npz), one entry per source in --sources order:
    Ks (N,3,3)  Rs (N,3,3)  ts (N,3)  dists (N,5)
tools/calibrate.py pair output (K1,K2,R,t,dist1,dist2) is also accepted:
camera A is the world frame.
"""

import logging
import queue
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .angles import compute_all_angles
from .camera import _init_person, _init_track
from .config import (
    CLASSIFY_INTERVAL_SECONDS,
    CLASSIFY_WINDOW_SECONDS,
    MIN_TRACK_AGE_FRAMES,
    PROGRESS_LOG_FRAMES,
    REID_SAMPLE_INTERVAL_SECONDS,
)
from .detector import PersonDetectorTracker
from .exercise_classifier import ExerciseClassifier
from .form import score_rep
from .output import write_camera_json
from .pose import PoseEstimator
from .reid import EmbeddingExtractor
from .session import SessionGallery
from .triangulation import (
    CalibratedCamera,
    compute_all_angles_3d,
    cross_view_consistent,
    knee_valgus_angle,
    triangulate_skeleton,
)
from .visualiser import draw_frame

logger = logging.getLogger(__name__)


def load_rig(path: str) -> tuple[list[dict], np.ndarray]:
    """Load per-camera calibration.
    Returns ([{'cam', 'K', 'dist'}, ...], world_up_vector)."""
    data = np.load(path)
    up = data['up'] if 'up' in data else np.array([0.0, 0.0, 1.0])
    rig = []
    if 'Ks' in data:
        n = data['Ks'].shape[0]
        for i in range(n):
            rig.append({
                'cam': CalibratedCamera(K=data['Ks'][i], R=data['Rs'][i], t=data['ts'][i]),
                'K': data['Ks'][i],
                'dist': data['dists'][i] if 'dists' in data else np.zeros(5),
            })
    elif 'K1' in data:   # tools/calibrate.py pair format — camera A is world
        rig.append({
            'cam': CalibratedCamera(K=data['K1'], R=np.eye(3), t=np.zeros(3)),
            'K': data['K1'], 'dist': data['dist1'].ravel(),
        })
        rig.append({
            'cam': CalibratedCamera(K=data['K2'], R=data['R'], t=data['t'].ravel()),
            'K': data['K2'], 'dist': data['dist2'].ravel(),
        })
    else:
        raise ValueError(f"Unrecognised rig file format: {path}")
    return rig, up


def _undistort(kps: np.ndarray, K: np.ndarray, dist: np.ndarray) -> np.ndarray:
    pts = kps[:, :2].astype(np.float64).reshape(-1, 1, 2)
    ud = cv2.undistortPoints(pts, K, dist, P=K).reshape(-1, 2)
    out = kps.copy()
    out[:, :2] = ud
    return out


class FusedCameraProcessor:
    """N synchronized views of one station, fused into per-person 3D analysis."""

    def __init__(
        self,
        camera_id: str,
        sources: list,
        rig_path: str,
        output_dir: str,
        visualise: bool = False,
        exercise: str = 'both',
        display_queue: Optional[queue.Queue] = None,
        dashboard=None,
        stop_event: Optional[threading.Event] = None,
        gallery=None,
    ) -> None:
        self.camera_id = camera_id
        self.sources = sources
        self.rig, self.world_up = load_rig(rig_path)
        if len(self.rig) != len(sources):
            raise ValueError(
                f"Rig has {len(self.rig)} cameras but {len(sources)} sources given"
            )
        self.output_dir = output_dir
        self.visualise = visualise
        self.exercise = exercise
        self.auto_mode = exercise == 'auto'
        self.display_queue = display_queue
        self.dashboard = dashboard
        self.stop_event = stop_event
        # Fusion needs identity to associate views — always have a gallery
        self.gallery = gallery if gallery is not None else SessionGallery()
        self.result: dict | None = None

    def run(self) -> None:
        caps = [cv2.VideoCapture(int(s) if str(s).isdigit() else s) for s in self.sources]
        for s, cap in zip(self.sources, caps):
            if not cap.isOpened():
                logger.error(f"[{self.camera_id}] Cannot open: {s}")
                self.result = {'camera_id': self.camera_id, 'tracks': []}
                return
        fps = caps[0].get(cv2.CAP_PROP_FPS) or 30.0
        logger.info(
            f"[{self.camera_id}] Fused station: {len(caps)} views at {fps:.1f} fps"
        )

        detectors = [PersonDetectorTracker() for _ in caps]
        poses = [PoseEstimator() for _ in caps]
        embedder = EmbeddingExtractor()
        classifier = ExerciseClassifier() if self.auto_mode else None
        sm_exercise = 'both' if self.auto_mode else self.exercise

        # Per-view track bookkeeping; exercise state lives on persons
        view_tracks: list[dict[int, dict]] = [{} for _ in caps]
        persons_data: dict[str, dict] = {}
        frame_idx = 0
        total_frames = int(caps[0].get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        writer = None
        if self.visualise:
            vw = int(caps[0].get(cv2.CAP_PROP_FRAME_WIDTH))
            vh = int(caps[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
            writer = cv2.VideoWriter(
                str(Path(self.output_dir) / f"{self.camera_id}_annotated.mp4"),
                cv2.VideoWriter_fourcc(*'mp4v'), fps, (vw, vh),
            )

        try:
            while True:
                if self.stop_event is not None and self.stop_event.is_set():
                    logger.info(f"[{self.camera_id}] Stop requested.")
                    break
                frames = []
                ok = True
                for cap in caps:
                    ret, f = cap.read()
                    ok &= ret
                    frames.append(f)
                if not ok:
                    break
                timestamp = frame_idx / fps

                # person_id → list of (view_idx, undistorted_kps)
                person_views: dict[str, list[tuple[int, np.ndarray]]] = {}
                view0_draw = []      # (track_id, x1,y1,x2,y2,conf) for display
                view0_kps: dict[int, np.ndarray] = {}
                view0_person: dict[int, str] = {}

                for vi, (frame, det, pose) in enumerate(zip(frames, detectors, poses)):
                    try:
                        detections = det.detect_and_track(frame)
                    except Exception as exc:
                        logger.warning(f"[{self.camera_id}] view {vi} detect error: {exc}")
                        continue
                    tracks = view_tracks[vi]
                    for track_id, x1, y1, x2, y2, conf in detections:
                        td = tracks.setdefault(track_id, _init_track())
                        td['frames'] += 1
                        td['bbox'] = (x1, y1, x2, y2)
                        td['last_seen_frame'] = frame_idx

                        # Cross-view identity via the shared gallery
                        if (
                            td['frames'] >= MIN_TRACK_AGE_FRAMES
                            and timestamp >= td['_next_emb_t']
                        ):
                            emb = embedder.extract(frame, (x1, y1, x2, y2))
                            if emb is not None:
                                cam_tag = f"{self.camera_id}/v{vi}"
                                if td['person_id'] is None:
                                    avg = td['_provisional'].add(emb, timestamp)
                                    if avg is not None:
                                        pid, sim = self.gallery.identify(avg, cam_tag)
                                        td['person_id'] = pid
                                        logger.info(
                                            f"[{self.camera_id}] view {vi} track {track_id}"
                                            f" → {self.gallery.label(pid)} (sim {sim:.2f})"
                                        )
                                else:
                                    self.gallery.update(td['person_id'], emb, cam_tag)
                                td['_next_emb_t'] = timestamp + REID_SAMPLE_INTERVAL_SECONDS
                        if td['person_id'] is None:
                            continue

                        kps = None
                        try:
                            kps = pose.estimate(frame, (x1, y1, x2, y2))
                        except Exception as exc:
                            logger.warning(f"[{self.camera_id}] view {vi} pose error: {exc}")
                        if kps is None:
                            continue
                        kps = td['kp_filter'](timestamp, kps)

                        person_views.setdefault(td['person_id'], []).append(
                            (vi, _undistort(kps, self.rig[vi]['K'], self.rig[vi]['dist']))
                        )
                        if vi == 0:
                            view0_draw.append((track_id, x1, y1, x2, y2, conf))
                            view0_kps[track_id] = kps
                            view0_person[track_id] = td['person_id']

                # ── per-person fusion and analysis ────────────────────────
                current_angles_by_person: dict[str, dict] = {}
                for pid, views in person_views.items():
                    pd = persons_data.setdefault(pid, _init_person())
                    pd['frames'] += 1

                    if len(views) >= 2:
                        cams = [self.rig[vi]['cam'] for vi, _ in views]
                        kps_list = [k for _, k in views]
                        kps3d = triangulate_skeleton(cams, kps_list)
                        if cross_view_consistent(cams, kps_list):
                            angles = compute_all_angles_3d(kps3d, up=self.world_up)
                            for side in ('left', 'right'):
                                val = knee_valgus_angle(kps3d, side, up=self.world_up)
                                if val is not None:
                                    pd['angles'].setdefault(f'{side}_knee_valgus', []).append(
                                        (timestamp, val)
                                    )
                        else:
                            # Triangulation failed on most jointly-visible joints —
                            # the views likely show two different people the Re-ID
                            # gallery mismatched to the same person_id (appearance
                            # match only, no geometric check). Don't emit a
                            # confident-looking but bogus 3D skeleton: fall back to
                            # the single best-visibility view for this frame.
                            logger.warning(
                                f"[{self.camera_id}] person {pid}: cross-view "
                                f"triangulation inconsistent across {len(views)} views "
                                "— likely a Re-ID cross-view mismatch; falling back to 2D"
                            )
                            best_view = max(views, key=lambda vk: float(np.mean(vk[1][:, 2])))
                            angles = compute_all_angles(best_view[1])
                    else:
                        angles = compute_all_angles(views[0][1])   # 2D fallback

                    current_angles_by_person[pid] = angles
                    for joint, val in angles.items():
                        if val is not None:
                            pd['angles'].setdefault(joint, []).append((timestamp, val))

                    if sm_exercise in ('squat', 'both'):
                        lk, rk = angles.get('left_knee'), angles.get('right_knee')
                        knee = ((lk + rk) / 2 if lk is not None and rk is not None
                                else lk if lk is not None else rk)
                        pd['squat_sm'].update(knee, timestamp)
                    if sm_exercise in ('upper_body', 'both'):
                        le, re = angles.get('left_elbow'), angles.get('right_elbow')
                        elbow = ((le + re) / 2 if le is not None and re is not None
                                 else le if le is not None else re)
                        pd['upper_sm'].update(elbow, timestamp)

                    if classifier is not None and timestamp >= pd['_next_classify_t']:
                        cls, cconf = classifier.classify(
                            pd['angles'],
                            t_start=timestamp - CLASSIFY_WINDOW_SECONDS,
                            t_end=timestamp,
                        )
                        if cls != 'unknown':
                            pd['exercise_class'] = cls
                            pd['exercise_conf'] = cconf
                        pd['_next_classify_t'] = timestamp + CLASSIFY_INTERVAL_SECONDS

                    totals = (pd['squat_sm'].rep_count, pd['upper_sm'].rep_count)
                    if totals != pd['_last_rep_totals']:
                        fam = ('squat' if totals[0] > pd['_last_rep_totals'][0]
                               else 'upper_body')
                        sm = pd['squat_sm'] if fam == 'squat' else pd['upper_sm']
                        r = sm.reps[-1]
                        pd['last_form'] = score_rep(
                            {'timestamp': r.timestamp, 'start_timestamp': r.start_timestamp,
                             'lowest_angle': r.lowest_angle, 'valid': r.valid},
                            pd['angles'], fam, pd['exercise_class'], set_median_rom=None,
                        )
                        pd['_last_rep_totals'] = totals

                # ── display on view 0 ─────────────────────────────────────
                if self.visualise or self.display_queue or self.dashboard:
                    rep_counts, sm_states, labels = {}, {}, {}
                    for tid, _, _, _, _, _ in [d[:6] for d in view0_draw]:
                        pid = view0_person.get(tid)
                        pd = persons_data.get(pid)
                        if pd is None:
                            continue
                        fam = (classifier.family(pd['exercise_class'])
                               if classifier is not None else self.exercise)
                        rc = {}
                        if fam in ('squat', 'both'):
                            rc['squat'] = pd['squat_sm'].rep_count
                        if fam in ('upper_body', 'both'):
                            rc['upper_body'] = pd['upper_sm'].rep_count
                        rep_counts[tid] = rc
                        sm_states[tid] = (pd['squat_sm'].state.value
                                          if fam in ('squat', 'both')
                                          else pd['upper_sm'].state.value)
                        n_views = len(person_views.get(pid, []))
                        labels[tid] = (f"{self.gallery.label(pid)}"
                                       f" [{n_views}cam{'·3D' if n_views >= 2 else ''}]")
                    angles_by_track = {
                        tid: current_angles_by_person.get(view0_person.get(tid), {})
                        for tid in view0_kps
                    }
                    vis = draw_frame(
                        frames[0], view0_draw, view0_kps, angles_by_track,
                        rep_counts, sm_states=sm_states,
                        exercise='both' if self.auto_mode else self.exercise,
                        person_labels=labels,
                    )
                    if writer is not None:
                        writer.write(vis)
                    if self.display_queue is not None:
                        try:
                            self.display_queue.put_nowait((self.camera_id, vis))
                        except queue.Full:
                            pass
                    if self.dashboard is not None and view0_draw:
                        self.dashboard.push_frame(self.camera_id, vis)
                        primary = max(view0_draw, key=lambda d: (d[3]-d[1])*(d[4]-d[2]))[0]
                        pid = view0_person.get(primary)
                        pd = persons_data.get(pid)
                        if pd is not None:
                            label = self.exercise
                            if self.auto_mode:
                                label = (f"{pd['exercise_class']} ({pd['exercise_conf']:.0%})"
                                         if pd['exercise_class'] != 'unknown' else 'detecting…')
                            self.dashboard.push_data(
                                self.camera_id, rep_counts.get(primary, {}),
                                current_angles_by_person.get(pid, {}),
                                sm_states.get(primary, 'waiting'),
                                exercise=label, form=pd['last_form'],
                                person=self.gallery.label(pid),
                            )

                frame_idx += 1
                if frame_idx % PROGRESS_LOG_FRAMES == 0:
                    pct = f" ({frame_idx / total_frames:.0%})" if total_frames else ""
                    logger.info(f"[{self.camera_id}] {frame_idx} frames{pct}, "
                                f"{len(persons_data)} person(s)")
        finally:
            for cap in caps:
                cap.release()
            if writer is not None:
                writer.release()
            for p in poses:
                p.close()

        for pid, pd in persons_data.items():
            pd['person_label'] = self.gallery.label(pid)
            pd['track_ids'] = set()   # per-view track ids aren't meaningful here
        try:
            self.result = write_camera_json(
                self.camera_id, persons_data, self.output_dir, self.exercise
            )
        except Exception:
            logger.exception(f"[{self.camera_id}] Failed to write results JSON")
            self.result = {'camera_id': self.camera_id, 'tracks': []}
        logger.info(f"[{self.camera_id}] Done — {frame_idx} frames, "
                    f"{len(persons_data)} person(s), {len(caps)} views fused")
