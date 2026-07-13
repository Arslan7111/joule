"""
One Euro filter for temporal keypoint smoothing.

Removes high-frequency jitter while keeping latency negligible during fast
movement — the filter cutoff adapts to speed (slow motion → strong smoothing,
fast motion → light smoothing).  Reference: Casiez et al., CHI 2012.

Applied per track to the (17, 3) keypoint array; x/y are filtered,
visibility is passed through untouched.
"""

import numpy as np

# Filter tuning — pixel coordinates at ~30 fps.
MIN_CUTOFF = 1.2     # Hz — base smoothing for slow/static joints
BETA = 0.015         # speed coefficient — higher = less lag on fast motion
D_CUTOFF = 1.0       # Hz — derivative smoothing
RESET_GAP_S = 0.5    # re-initialise after a tracking gap


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * np.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class KeypointOneEuro:
    """One Euro filter over a (17, 2) coordinate array."""

    def __init__(self) -> None:
        self._x: np.ndarray | None = None      # filtered positions (17, 2)
        self._dx: np.ndarray | None = None     # filtered velocities (17, 2)
        self._t: float | None = None

    def __call__(self, timestamp: float, keypoints: np.ndarray) -> np.ndarray:
        """keypoints: (17, 3) [x, y, vis] → same shape, x/y smoothed."""
        xy = keypoints[:, :2].astype(np.float64)

        if (
            self._x is None
            or self._t is None
            or timestamp - self._t > RESET_GAP_S
            or timestamp <= self._t
        ):
            self._x = xy.copy()
            self._dx = np.zeros_like(xy)
            self._t = timestamp
            return keypoints

        dt = timestamp - self._t
        self._t = timestamp

        dx = (xy - self._x) / dt
        a_d = _alpha(D_CUTOFF, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx

        cutoff = MIN_CUTOFF + BETA * np.linalg.norm(self._dx, axis=1, keepdims=True)
        a = _alpha(cutoff, dt)
        self._x = a * xy + (1 - a) * self._x

        out = keypoints.copy()
        out[:, :2] = self._x.astype(keypoints.dtype)
        return out
