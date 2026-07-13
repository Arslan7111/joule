import logging
import queue
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .angles import compute_all_angles
from .config import (
    ANGLE_DEFINITIONS,
    BOTTOM_THRESHOLD,
    CLASSIFY_INTERVAL_SECONDS,
    CLASSIFY_WINDOW_SECONDS,
    COAST_DISPLAY_FRAMES,
    DEPTH_THRESHOLD,
    HARD_EXAMPLE_CONF,
    HARD_EXAMPLE_MAX_PER_CAMERA,
    HARD_EXAMPLE_MIN_GAP_SECONDS,
    HYSTERESIS_FRAMES,
    LOST_TRACK_WARNING_SECONDS,
    MIN_TRACK_AGE_FRAMES,
    PROGRESS_LOG_FRAMES,
    REID_SAMPLE_INTERVAL_SECONDS,
    TOP_THRESHOLD,
)
from .detector import PersonDetectorTracker
from .exercise_classifier import ExerciseClassifier
from .form import score_rep
from .output import write_camera_json
from .pose import PoseEstimator
from .reid import EmbeddingExtractor
from .smoothing import KeypointOneEuro
from .state_machine import StateMachine
from .visualiser import draw_frame

logger = logging.getLogger(__name__)

_ALL_ANGLE_KEYS = list(ANGLE_DEFINITIONS.keys()) + ['trunk_lean']


def _init_track() -> dict:
    """Per-tracker-track state: viewpoint bookkeeping only.  All exercise
    state lives on the person (see _init_person) so it survives track
    fragmentation."""
    return {
        'frames': 0,
        'bbox': None,
        'last_keypoints': None,
        'last_seen_frame': -1,
        '_warned_lost': False,
        'kp_filter': KeypointOneEuro(),  # temporal smoothing per track
        'person_id': None,               # session identity from the gallery
        '_next_emb_t': 0.0,
        '_last_hard_t': -1e9,
    }


def _init_person() -> dict:
    """Per-person exercise state — one continuous rep/angle history per human,
    however many tracker tracks they fragment into."""
    return {
        'frames': 0,
        'track_ids': set(),
        'angles': {name: [] for name in _ALL_ANGLE_KEYS},
        'squat_sm': StateMachine(
            top_threshold=TOP_THRESHOLD,
            bottom_threshold=BOTTOM_THRESHOLD,
            depth_threshold=DEPTH_THRESHOLD,
            hysteresis_frames=HYSTERESIS_FRAMES,
        ),
        'upper_sm': StateMachine(
            top_threshold=TOP_THRESHOLD,
            bottom_threshold=BOTTOM_THRESHOLD,
            depth_threshold=DEPTH_THRESHOLD,
            hysteresis_frames=HYSTERESIS_FRAMES,
        ),
        'exercise_class': 'unknown',   # live classification (auto mode)
        'exercise_conf': 0.0,
        '_next_classify_t': CLASSIFY_INTERVAL_SECONDS,
        '_last_rep_totals': (0, 0),    # (squat, upper) — detect new reps for live form
        'last_form': None,             # form dict of the most recent rep
    }


class CameraProcessor:
    """Processes a single camera source end-to-end in its own thread."""

    def __init__(
        self,
        camera_id: str,
        source,
        output_dir: str,
        visualise: bool = False,
        exercise: str = 'both',
        display_queue: Optional[queue.Queue] = None,
        dashboard=None,
        stop_event: Optional[threading.Event] = None,
        collect_hard: bool = False,
        gallery=None,
    ) -> None:
        self.camera_id = camera_id
        self.source = source
        self.output_dir = output_dir
        self.visualise = visualise
        self.exercise = exercise                    # squat | upper_body | both | auto
        self.auto_mode = exercise == 'auto'
        self.display_queue = display_queue
        self.dashboard = dashboard
        self.stop_event = stop_event
        self.collect_hard = collect_hard
        self.gallery = gallery
        self.result: dict | None = None

    def run(self) -> None:
        # A bare digit string means a webcam index, not a file path
        source = int(self.source) if str(self.source).isdigit() else self.source
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"[{self.camera_id}] Cannot open: {self.source}")
            self.result = {'camera_id': self.camera_id, 'tracks': []}
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        logger.info(f"[{self.camera_id}] Opened at {fps:.1f} fps")

        detector = PersonDetectorTracker()
        pose_est = PoseEstimator()
        classifier = ExerciseClassifier() if self.auto_mode else None
        embedder = EmbeddingExtractor() if self.gallery is not None else None
        # In auto mode both state machines run; classification picks which counts.
        sm_exercise = 'both' if self.auto_mode else self.exercise

        hard_dir = None
        hard_count = 0
        if self.collect_hard:
            hard_dir = Path(self.output_dir) / 'hard_examples' / self.camera_id
            hard_dir.mkdir(parents=True, exist_ok=True)

        tracks_data: dict[int, dict] = {}
        persons_data: dict[str, dict] = {}
        frame_idx = 0

        writer = None
        if self.visualise:
            vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out_path = str(Path(self.output_dir) / f"{self.camera_id}_annotated.mp4")
            writer = cv2.VideoWriter(
                out_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (vw, vh)
            )

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        def resolve_person(td: dict, track_id: int, frame, bbox, timestamp) -> Optional[dict]:
            """Attach the track to a person (Re-ID or track-keyed fallback);
            returns the person record, or None while identity is unknown."""
            if td['person_id'] is None and embedder is None:
                td['person_id'] = f"track_{track_id}"

            if (
                embedder is not None
                and td['frames'] >= MIN_TRACK_AGE_FRAMES
                and timestamp >= td['_next_emb_t']
            ):
                emb = embedder.extract(frame, bbox)
                if emb is not None:
                    if td['person_id'] is None:
                        pid, sim = self.gallery.identify(emb, self.camera_id)
                        td['person_id'] = pid
                        logger.info(
                            f"[{self.camera_id}] track {track_id} → "
                            f"{self.gallery.label(pid)} (sim {sim:.2f})"
                        )
                    else:
                        self.gallery.update(td['person_id'], emb, self.camera_id)
                    td['_next_emb_t'] = timestamp + REID_SAMPLE_INTERVAL_SECONDS
                # On extraction failure retry next frame (no interval bump)

            pid = td['person_id']
            if pid is None:
                return None
            if pid not in persons_data:
                persons_data[pid] = _init_person()
            pd = persons_data[pid]
            pd['track_ids'].add(track_id)
            return pd

        try:
            while True:
                if self.stop_event is not None and self.stop_event.is_set():
                    logger.info(f"[{self.camera_id}] Stop requested — finishing early.")
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_idx / fps
                active_ids: set[int] = set()
                current_kps: dict[int, np.ndarray] = {}
                current_angles: dict[int, dict] = {}

                try:
                    detections = detector.detect_and_track(frame)
                except Exception as exc:
                    logger.warning(f"[{self.camera_id}] frame {frame_idx}: detection error: {exc}")
                    detections = []

                for track_id, x1, y1, x2, y2, conf in detections:
                    active_ids.add(track_id)

                    if track_id not in tracks_data:
                        tracks_data[track_id] = _init_track()

                    td = tracks_data[track_id]
                    td['frames'] += 1
                    td['bbox'] = (x1, y1, x2, y2)
                    td['last_seen_frame'] = frame_idx
                    td['_warned_lost'] = False

                    pd = resolve_person(td, track_id, frame, (x1, y1, x2, y2), timestamp)
                    if pd is None:
                        continue       # identity pending — retry next frame
                    pd['frames'] += 1

                    # Pose estimation with last-known-keypoints interpolation
                    keypoints = None
                    try:
                        keypoints = pose_est.estimate(frame, (x1, y1, x2, y2))
                    except Exception as exc:
                        logger.warning(
                            f"[{self.camera_id}] track {track_id} pose error: {exc}"
                        )

                    # Hard-example collection: pose failed or low visibility
                    is_hard = keypoints is None or (
                        float(np.mean(keypoints[:, 2])) < HARD_EXAMPLE_CONF
                    )
                    if (
                        hard_dir is not None and is_hard
                        and hard_count < HARD_EXAMPLE_MAX_PER_CAMERA
                        and timestamp - td['_last_hard_t'] >= HARD_EXAMPLE_MIN_GAP_SECONDS
                    ):
                        crop = frame[max(0, int(y1)):int(y2), max(0, int(x1)):int(x2)]
                        if crop.size:
                            cv2.imwrite(
                                str(hard_dir / f"f{frame_idx:06d}_t{track_id}.jpg"), crop
                            )
                            hard_count += 1
                            td['_last_hard_t'] = timestamp

                    if keypoints is not None:
                        keypoints = td['kp_filter'](timestamp, keypoints)
                        td['last_keypoints'] = keypoints
                    elif td['last_keypoints'] is not None:
                        keypoints = td['last_keypoints']   # interpolate

                    if keypoints is None:
                        continue

                    current_kps[track_id] = keypoints
                    angles = compute_all_angles(keypoints)
                    current_angles[track_id] = angles

                    for joint, val in angles.items():
                        if val is not None:
                            pd['angles'][joint].append((timestamp, val))

                    if sm_exercise in ('squat', 'both'):
                        lk = angles.get('left_knee')
                        rk = angles.get('right_knee')
                        knee_avg = (
                            (lk + rk) / 2 if lk is not None and rk is not None
                            else lk if lk is not None
                            else rk
                        )
                        pd['squat_sm'].update(knee_avg, timestamp)

                    if sm_exercise in ('upper_body', 'both'):
                        le = angles.get('left_elbow')
                        re = angles.get('right_elbow')
                        elbow_avg = (
                            (le + re) / 2 if le is not None and re is not None
                            else le if le is not None
                            else re
                        )
                        pd['upper_sm'].update(elbow_avg, timestamp)

                    # Periodic exercise classification (auto mode)
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

                    # Live form scoring for a just-completed rep
                    totals = (pd['squat_sm'].rep_count, pd['upper_sm'].rep_count)
                    if totals != pd['_last_rep_totals']:
                        fam = 'squat' if totals[0] > pd['_last_rep_totals'][0] else 'upper_body'
                        sm = pd['squat_sm'] if fam == 'squat' else pd['upper_sm']
                        new_rep = sm.reps[-1]
                        pd['last_form'] = score_rep(
                            {
                                'timestamp': new_rep.timestamp,
                                'start_timestamp': new_rep.start_timestamp,
                                'lowest_angle': new_rep.lowest_angle,
                                'valid': new_rep.valid,
                            },
                            pd['angles'], fam, pd['exercise_class'],
                            set_median_rom=None,   # set stats unknown mid-stream
                        )
                        pd['_last_rep_totals'] = totals

                # Warn on tracks lost for more than 2 seconds
                for track_id, td in tracks_data.items():
                    if track_id not in active_ids:
                        frames_lost = frame_idx - td['last_seen_frame']
                        if (
                            frames_lost / fps > LOST_TRACK_WARNING_SECONDS
                            and not td['_warned_lost']
                        ):
                            logger.warning(
                                f"[{self.camera_id}] Track {track_id} lost for "
                                f">{LOST_TRACK_WARNING_SECONDS:.0f}s"
                            )
                            td['_warned_lost'] = True

                need_vis = self.visualise or self.display_queue or self.dashboard
                if need_vis:
                    # Coast recently-lost tracks: keep the last box/skeleton on
                    # screen while ByteTrack's buffer still holds the ID.
                    draw_dets = [
                        d for d in detections
                        if tracks_data[d[0]]['frames'] >= MIN_TRACK_AGE_FRAMES
                    ]
                    draw_ids = {d[0] for d in draw_dets}
                    for tid, td in tracks_data.items():
                        if (
                            tid not in active_ids
                            and td['bbox'] is not None
                            and 0 < frame_idx - td['last_seen_frame'] <= COAST_DISPLAY_FRAMES
                        ):
                            draw_dets.append((tid, *td['bbox'], 0.0))
                            draw_ids.add(tid)
                            if td['last_keypoints'] is not None:
                                current_kps[tid] = td['last_keypoints']

                    rep_counts: dict[int, dict] = {}
                    sm_states: dict[int, str] = {}
                    for tid in draw_ids:
                        pid = tracks_data[tid]['person_id']
                        pd = persons_data.get(pid)
                        if pd is None:
                            rep_counts[tid] = {}
                            sm_states[tid] = 'waiting'
                            continue
                        fam = (
                            classifier.family(pd['exercise_class'])
                            if classifier is not None else self.exercise
                        )
                        rc = {}
                        if fam in ('squat', 'both'):
                            rc['squat'] = pd['squat_sm'].rep_count
                        if fam in ('upper_body', 'both'):
                            rc['upper_body'] = pd['upper_sm'].rep_count
                        rep_counts[tid] = rc
                        sm_states[tid] = (
                            pd['squat_sm'].state.value
                            if fam in ('squat', 'both')
                            else pd['upper_sm'].state.value
                        )
                    person_labels = {
                        tid: self.gallery.label(tracks_data[tid]['person_id'])
                        for tid in draw_ids
                    } if self.gallery is not None else None
                    vis = draw_frame(
                        frame, draw_dets, current_kps, current_angles,
                        rep_counts, sm_states=sm_states,
                        exercise='both' if self.auto_mode else self.exercise,
                        person_labels=person_labels,
                    )
                    if writer is not None:
                        writer.write(vis)
                    if self.display_queue is not None:
                        try:
                            self.display_queue.put_nowait((self.camera_id, vis))
                        except queue.Full:
                            pass

                    if self.dashboard is not None and active_ids:
                        # Push annotated frame
                        self.dashboard.push_frame(self.camera_id, vis)
                        # Push data for the person with the most frames
                        primary = max(active_ids, key=lambda t: tracks_data[t]['frames'])
                        ppd = persons_data.get(tracks_data[primary]['person_id'])
                        label = self.exercise
                        if self.auto_mode and ppd is not None:
                            label = (
                                f"{ppd['exercise_class']} ({ppd['exercise_conf']:.0%})"
                                if ppd['exercise_class'] != 'unknown' else 'detecting…'
                            )
                        self.dashboard.push_data(
                            self.camera_id,
                            rep_counts.get(primary, {}),
                            current_angles.get(primary, {}),
                            sm_states.get(primary, 'waiting'),
                            exercise=label,
                            form=ppd['last_form'] if ppd else None,
                            person=(person_labels or {}).get(primary, ''),
                        )

                frame_idx += 1
                if frame_idx % PROGRESS_LOG_FRAMES == 0:
                    pct = f" ({frame_idx / total_frames:.0%})" if total_frames > 0 else ""
                    logger.info(
                        f"[{self.camera_id}] {frame_idx} frames{pct}, "
                        f"{len(persons_data)} person(s), {len(tracks_data)} track(s)"
                    )

        finally:
            cap.release()
            if writer is not None:
                writer.release()
            pose_est.close()

        if self.gallery is not None:
            for pid, pd in persons_data.items():
                pd['person_label'] = self.gallery.label(pid)

        try:
            self.result = write_camera_json(
                self.camera_id, persons_data, self.output_dir, self.exercise
            )
        except Exception:
            logger.exception(f"[{self.camera_id}] Failed to write results JSON")
            self.result = {'camera_id': self.camera_id, 'tracks': []}
        logger.info(
            f"[{self.camera_id}] Done — {frame_idx} frames, "
            f"{len(persons_data)} person(s) across {len(tracks_data)} track(s)"
        )
