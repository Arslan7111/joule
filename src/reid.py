"""
Appearance embeddings for person re-identification.

Within-session Re-ID: clothing stays constant, so the embedding combines
- deep features (MobileNetV3-small, ImageNet-pretrained, torchvision) and
- an HSV color histogram of the torso region (clothing color/texture).

Both parts are L2-normalised and concatenated with a weighting; similarity
is cosine.  Falls back to histogram-only if torchvision is unavailable.

Embeddings are extracted from detector crops roughly once per second per
track — negligible compute next to detection and pose.
"""

import logging

import cv2
import numpy as np

from .config import REID_LOCK_MIN_SAMPLES, REID_LOCK_WINDOW_SECONDS

logger = logging.getLogger(__name__)

_DEEP_WEIGHT = 0.6      # deep features vs color histogram in the embedding
_HIST_BINS = (8, 8, 4)  # H, S, V bins

_torch = None
_model = None
_transform = None


def _init_deep() -> bool:
    global _torch, _model, _transform
    if _model is not None:
        return True
    try:
        import torch
        from torchvision import transforms
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

        m = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        m.classifier = torch.nn.Identity()      # 576-d pooled features
        m.eval()
        _torch = torch
        _model = m
        _transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((224, 112)),      # person aspect ratio
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        logger.info("ReID: MobileNetV3 deep features enabled")
        return True
    except Exception as exc:
        logger.warning(f"ReID: torchvision unavailable ({exc}) — color histogram only")
        return False


def _color_histogram(crop_bgr: np.ndarray) -> np.ndarray:
    """HSV histogram of the torso band (middle 60% vertically) — clothing."""
    h = crop_bgr.shape[0]
    torso = crop_bgr[int(0.2 * h):int(0.8 * h)]
    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, _HIST_BINS,
                        [0, 180, 0, 256, 0, 256]).flatten()
    n = np.linalg.norm(hist)
    return hist / n if n > 0 else hist


class EmbeddingExtractor:
    def __init__(self) -> None:
        self._deep = _init_deep()

    def extract(self, frame: np.ndarray, bbox: tuple) -> np.ndarray | None:
        """frame + (x1, y1, x2, y2) → L2-normalised embedding, or None."""
        x1, y1, x2, y2 = (int(v) for v in bbox)
        h, w = frame.shape[:2]
        crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size == 0 or crop.shape[0] < 32 or crop.shape[1] < 16:
            return None

        hist = _color_histogram(crop)

        if self._deep:
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            with _torch.no_grad():
                feat = _model(_transform(rgb).unsqueeze(0)).squeeze(0).numpy()
            n = np.linalg.norm(feat)
            feat = feat / n if n > 0 else feat
            emb = np.concatenate([
                _DEEP_WEIGHT * feat,
                (1.0 - _DEEP_WEIGHT) * hist,
            ])
        else:
            emb = hist

        n = np.linalg.norm(emb)
        return (emb / n if n > 0 else emb).astype(np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))       # embeddings are already unit-norm


class ProvisionalIdentity:
    """
    Buffers a track's early embedding samples instead of matching the first
    one straight against the gallery.  A single occluded or blurry birth
    crop would otherwise lock the wrong person for the track's whole
    lifetime (rep counting, form, everything is keyed off person_id).

    Call add() per sample; it returns None while still buffering, and the
    averaged, re-normalised embedding once ready — call gallery.identify()
    on that return value exactly once, then discard this instance.
    """

    def __init__(
        self,
        min_samples: int = REID_LOCK_MIN_SAMPLES,
        window_seconds: float = REID_LOCK_WINDOW_SECONDS,
    ) -> None:
        self._min_samples = min_samples
        self._window_seconds = window_seconds
        self._embeddings: list[np.ndarray] = []
        self._first_t: float | None = None

    def add(self, embedding: np.ndarray, timestamp: float) -> np.ndarray | None:
        self._embeddings.append(embedding)
        if self._first_t is None:
            self._first_t = timestamp
        elapsed = timestamp - self._first_t

        ready = (
            len(self._embeddings) >= self._min_samples
            or elapsed >= self._window_seconds
        )
        if not ready:
            return None

        avg = np.mean(self._embeddings, axis=0)
        n = np.linalg.norm(avg)
        return (avg / n if n > 0 else avg).astype(np.float32)
