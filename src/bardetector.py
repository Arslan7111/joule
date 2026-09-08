import logging
from pathlib import Path

import numpy as np

from .config import BAR_DETECTOR_CONF, BAR_DETECTOR_IMGSZ, BAR_DETECTOR_MODEL

logger = logging.getLogger(__name__)


class BarDetector:
    """
    Single-class barbell detector (YOLOv8n, tools/train_bar_detector.py).

    Equipment-context signal, not a person model: no tracking, no identity —
    every frame just reports its single best-confidence detection, since the
    features that consume this (bar presence, bar position relative to the
    lifter) only need "is a bar visible, and roughly where" per frame.

    Lazily loaded and silently inert if the weight file is missing, matching
    how PoseEstimator degrades rather than crashing when a model isn't
    present — BAR_DETECT_ENABLED stays a safe flag to flip even before a
    weight file has been trained/placed.
    """

    def __init__(
        self,
        model_path: str = BAR_DETECTOR_MODEL,
        conf: float = BAR_DETECTOR_CONF,
        imgsz: int = BAR_DETECTOR_IMGSZ,
    ) -> None:
        self.conf = conf
        self.imgsz = imgsz
        self.model = None
        if not Path(model_path).exists():
            logger.warning(
                f"Bar detector weights not found at {model_path} -- "
                "BAR_DETECT_ENABLED has no effect until they exist "
                "(see tools/train_bar_detector.py)."
            )
            return
        from ultralytics import YOLO
        self.model = YOLO(model_path)

    @property
    def available(self) -> bool:
        return self.model is not None

    def detect(self, frame: np.ndarray) -> tuple | None:
        """Returns (x1, y1, x2, y2, confidence) for the single highest-confidence
        bar detection this frame, or None if unavailable/none found."""
        if self.model is None:
            return None
        results = self.model.predict(
            frame, conf=self.conf, imgsz=self.imgsz, verbose=False,
        )
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return None
        boxes = results[0].boxes
        i = int(boxes.conf.argmax())
        x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
        conf = float(boxes.conf[i])
        return (float(x1), float(y1), float(x2), float(y2), conf)
