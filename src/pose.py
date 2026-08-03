import cv2
import logging
from pathlib import Path

import numpy as np

from .config import MP_TO_COCO, BBOX_PADDING

logger = logging.getLogger(__name__)

# Model priority. Benchmarked on real footage: full gave the best angle
# coverage (100% elbow vs 96% lite, 90% heavy — heavy's confidence calibration
# is stricter and starves the 0.5 threshold). Delete full/heavy to force lite
# on constrained hardware.
_MODEL_CANDIDATES = [
    'pose_landmarker_full.task',
    'pose_landmarker_heavy.task',
    'pose_landmarker_lite.task',
]
_PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_MODEL = next(
    (str(_PROJECT_ROOT / m) for m in _MODEL_CANDIDATES if (_PROJECT_ROOT / m).exists()),
    str(_PROJECT_ROOT / _MODEL_CANDIDATES[-1]),
)

_MP_AVAILABLE = False
_YOLO_POSE_AVAILABLE = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.core.base_options import BaseOptions as _MPBaseOptions
    _MP_AVAILABLE = True
except Exception:
    logger.warning(
        "MediaPipe not available. Falling back to YOLOv8n-Pose.  "
        "Install with: pip install mediapipe"
    )

# Checked unconditionally, not just when MediaPipe itself fails to import --
# MediaPipe can import fine but still have no usable model (.task file
# missing), in which case this is the only fallback and must already be
# known available.
try:
    from ultralytics import YOLO as _YOLO  # noqa: F401
    _YOLO_POSE_AVAILABLE = True
except Exception:
    if not _MP_AVAILABLE:
        logger.error("Neither MediaPipe nor ultralytics YOLOv8-Pose is available.")


class PoseEstimator:
    """
    Top-down pose estimator.

    Primary backend: MediaPipe Pose Landmarker (Tasks API, 0.10+).
    Fallback:        YOLOv8n-Pose when MediaPipe is unavailable.

    Always returns COCO-17 keypoints in full-frame pixel coordinates as a
    (17, 3) float32 array [x, y, visibility].
    """

    def __init__(self, min_confidence: float = 0.5) -> None:
        self.min_confidence = min_confidence
        self._backend: str | None = None

        if _MP_AVAILABLE and Path(_DEFAULT_MODEL).exists():
            try:
                # Force CPU delegate: PyTorch Metal conflicts with MediaPipe's GPU path on macOS
                base_opts = mp_python.BaseOptions(
                    model_asset_path=_DEFAULT_MODEL,
                    delegate=_MPBaseOptions.Delegate.CPU,
                )
                opts = mp_vision.PoseLandmarkerOptions(
                    base_options=base_opts,
                    running_mode=mp_vision.RunningMode.IMAGE,
                    num_poses=1,
                    min_pose_detection_confidence=min_confidence,
                    min_pose_presence_confidence=min_confidence,
                    min_tracking_confidence=min_confidence,
                    output_segmentation_masks=False,
                )
                self._landmarker = mp_vision.PoseLandmarker.create_from_options(opts)
                self._backend = 'mediapipe'
                logger.info(
                    f"PoseEstimator: MediaPipe backend loaded ({Path(_DEFAULT_MODEL).name})"
                )
            except Exception as exc:
                logger.warning(f"MediaPipe init failed ({exc}). Falling back to YOLOv8n-Pose.")

        if self._backend is None and _MP_AVAILABLE and not Path(_DEFAULT_MODEL).exists():
            logger.warning(
                f"MediaPipe model not found at {_DEFAULT_MODEL}. "
                "Download pose_landmarker_lite.task into the project root."
            )

        if self._backend is None:
            if _YOLO_POSE_AVAILABLE:
                from ultralytics import YOLO
                self._pose_model = YOLO('yolov8n-pose.pt')
                self._backend = 'yolo_pose'
                logger.info("PoseEstimator: YOLOv8n-Pose backend loaded")
            else:
                logger.error("No pose estimator available.")

    def estimate(self, frame: np.ndarray, bbox: tuple) -> np.ndarray | None:
        """
        Run pose on the padded crop around bbox.

        Returns (17, 3) float32 [x_frame, y_frame, visibility], or None.
        """
        if self._backend == 'mediapipe':
            return self._estimate_mediapipe(frame, bbox)
        if self._backend == 'yolo_pose':
            return self._estimate_yolo_pose(frame, bbox)
        return None

    def _padded_crop(self, frame: np.ndarray, bbox: tuple) -> tuple:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        bw, bh = x2 - x1, y2 - y1
        x1p = max(0, x1 - int(BBOX_PADDING * bw))
        y1p = max(0, y1 - int(BBOX_PADDING * bh))
        x2p = min(w, x2 + int(BBOX_PADDING * bw))
        y2p = min(h, y2 + int(BBOX_PADDING * bh))
        return frame[y1p:y2p, x1p:x2p], x1p, y1p

    def _estimate_mediapipe(self, frame: np.ndarray, bbox: tuple) -> np.ndarray | None:
        crop, x1p, y1p = self._padded_crop(frame, bbox)
        if crop.size == 0:
            return None

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return None

        crop_h, crop_w = crop.shape[:2]
        landmarks = result.pose_landmarks[0]   # first (and only) pose
        keypoints = np.zeros((17, 3), dtype=np.float32)

        for mp_idx, coco_idx in MP_TO_COCO.items():
            lm = landmarks[mp_idx]
            keypoints[coco_idx, 0] = x1p + lm.x * crop_w
            keypoints[coco_idx, 1] = y1p + lm.y * crop_h
            keypoints[coco_idx, 2] = float(lm.visibility if lm.visibility is not None else 0.0)

        return keypoints

    def _estimate_yolo_pose(self, frame: np.ndarray, bbox: tuple) -> np.ndarray | None:
        crop, x1p, y1p = self._padded_crop(frame, bbox)
        if crop.size == 0:
            return None

        results = self._pose_model(crop, verbose=False)
        if not results or results[0].keypoints is None:
            return None

        kps = results[0].keypoints
        if len(kps.xy) == 0:
            return None

        xy = kps.xy[0].cpu().numpy()
        conf = (
            kps.conf[0].cpu().numpy()
            if kps.conf is not None
            else np.ones(17, dtype=np.float32)
        )

        keypoints = np.zeros((17, 3), dtype=np.float32)
        for i in range(min(17, len(xy))):
            keypoints[i, 0] = x1p + xy[i, 0]
            keypoints[i, 1] = y1p + xy[i, 1]
            keypoints[i, 2] = float(conf[i])
        return keypoints

    def close(self) -> None:
        if self._backend == 'mediapipe' and hasattr(self, '_landmarker'):
            self._landmarker.close()
