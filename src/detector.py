import logging
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from .config import DETECTOR_CONF, DETECTOR_IMGSZ, DETECTOR_MODEL

logger = logging.getLogger(__name__)

_TRACKER_CFG = str(Path(__file__).parent.parent / 'bytetrack_config.yaml')


class PersonDetectorTracker:
    """
    YOLOv8 person detector with ByteTrack multi-object tracking.

    Each instance owns its own model and tracker state, so it is safe to run
    one instance per camera thread without any locking.
    """

    def __init__(
        self,
        model_path: str = DETECTOR_MODEL,
        conf: float = DETECTOR_CONF,
        imgsz: int = DETECTOR_IMGSZ,
    ) -> None:
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz

    def detect_and_track(self, frame: np.ndarray) -> list[tuple]:
        """
        Returns a list of (track_id, x1, y1, x2, y2, confidence) for every
        active person track in this frame.  Returns an empty list when no
        persons are detected.
        """
        results = self.model.track(
            frame,
            persist=True,           # keep tracker state between calls
            tracker=_TRACKER_CFG,
            classes=[0],            # COCO class 0 = person
            conf=self.conf,
            imgsz=self.imgsz,
            verbose=False,
        )

        tracks: list[tuple] = []
        if not results or results[0].boxes is None:
            return tracks

        boxes = results[0].boxes
        if boxes.id is None:
            return tracks

        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()

        for i in range(len(ids)):
            x1, y1, x2, y2 = xyxy[i]
            tracks.append((int(ids[i]), float(x1), float(y1), float(x2), float(y2), float(confs[i])))

        return tracks
