from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from .config import (
    ADAPTIVE_THRESHOLDS,
    ADAPTIVE_WINDOW_SECONDS,
    BOTTOM_FRACTION,
    BOTTOM_THRESHOLD,
    DEPTH_FRACTION,
    DEPTH_THRESHOLD,
    HYSTERESIS_FRAMES,
    MIN_ANGLE_RANGE,
    SMOOTHING_WINDOW,
    TOP_FRACTION,
    TOP_THRESHOLD,
)


class RepState(Enum):
    WAITING = "waiting"
    DESCENDING = "descending"
    BOTTOM = "bottom"
    ASCENDING = "ascending"


@dataclass
class Rep:
    timestamp: float          # rep completion time (s)
    lowest_angle: float
    valid: bool
    start_timestamp: float = 0.0   # descent start time (s)

    @property
    def duration(self) -> float:
        return self.timestamp - self.start_timestamp


class StateMachine:
    """
    One-exercise rep counter driven by a joint-angle signal.

    States cycle:  WAITING → DESCENDING → BOTTOM → ASCENDING → WAITING (rep done)

    WAITING is also the "at top" resting state. The machine only begins tracking
    a rep after the signal has first reached the top threshold, preventing a
    partial rep from being counted if recording starts mid-movement.

    The raw signal is median-filtered (SMOOTHING_WINDOW frames) to remove
    single-frame keypoint flicker.

    Adaptive mode (default): thresholds are derived from the person's observed
    motion range — the 10th–90th percentile of the last ADAPTIVE_WINDOW_SECONDS
    of signal — rather than fixed angles.  Real footage rarely reaches textbook
    extension angles (camera perspective, partial range of motion), so fixed
    thresholds silently miss reps.  No reps are counted until the observed
    range exceeds MIN_ANGLE_RANGE, which suppresses counting while a person
    stands still or fidgets.
    """

    def __init__(
        self,
        top_threshold: float = TOP_THRESHOLD,
        bottom_threshold: float = BOTTOM_THRESHOLD,
        depth_threshold: float = DEPTH_THRESHOLD,
        hysteresis_frames: int = HYSTERESIS_FRAMES,
        adaptive: bool = ADAPTIVE_THRESHOLDS,
        window_seconds: float = ADAPTIVE_WINDOW_SECONDS,
        min_range: float = MIN_ANGLE_RANGE,
    ) -> None:
        self.top_threshold = top_threshold
        self.bottom_threshold = bottom_threshold
        self.depth_threshold = depth_threshold
        self.hysteresis_frames = hysteresis_frames
        self.adaptive = adaptive
        self.window_seconds = window_seconds
        self.min_range = min_range

        self.state = RepState.WAITING
        self.rep_count = 0
        self.reps: list[Rep] = []

        self._at_top = False         # seen at least one frame at the top
        self._min_angle = float('inf')
        self._descent_start = 0.0
        self._pending: Optional[RepState] = None
        self._pending_count = 0

        self._median_buf: deque[float] = deque(maxlen=SMOOTHING_WINDOW)
        self._history: deque[tuple[float, float]] = deque()   # (timestamp, angle)

    def _update_adaptive_thresholds(self, angle: float, timestamp: float) -> bool:
        """Refresh thresholds from the recent signal. Returns False while the
        observed motion range is too small to count reps reliably."""
        self._history.append((timestamp, angle))
        while self._history and timestamp - self._history[0][0] > self.window_seconds:
            self._history.popleft()

        vals = [v for _, v in self._history]
        lo, hi = (float(x) for x in np.percentile(vals, [10, 90]))
        rng = hi - lo
        if rng < self.min_range:
            return False

        self.top_threshold = lo + TOP_FRACTION * rng
        self.bottom_threshold = lo + BOTTOM_FRACTION * rng
        self.depth_threshold = lo + DEPTH_FRACTION * rng

        # Retroactive arming: calibration needs a rep or two of data, so the
        # signal may already be mid-descent by the time thresholds are valid.
        # If the recent past reached the top, count the rep in progress too.
        if self.state == RepState.WAITING and not self._at_top:
            if any(v >= self.top_threshold for _, v in self._history):
                self._at_top = True
        return True

    def update(self, angle: Optional[float], timestamp: float) -> None:
        if angle is None:
            return

        # Median smoothing — kills single-frame keypoint flicker
        self._median_buf.append(float(angle))
        angle = float(np.median(self._median_buf))

        if self.adaptive and not self._update_adaptive_thresholds(angle, timestamp):
            # Not enough motion observed yet — hold state, don't count
            self._pending = None
            self._pending_count = 0
            return

        if self.state in (RepState.DESCENDING, RepState.BOTTOM, RepState.ASCENDING):
            self._min_angle = min(self._min_angle, angle)

        desired = self._desired_transition(angle)

        if desired is not None:
            if self._pending == desired:
                self._pending_count += 1
                if self._pending_count >= self.hysteresis_frames:
                    self._do_transition(desired, timestamp)
            else:
                self._pending = desired
                self._pending_count = 1
        else:
            self._pending = None
            self._pending_count = 0

    def _desired_transition(self, angle: float) -> Optional[RepState]:
        if self.state == RepState.WAITING:
            if angle >= self.top_threshold:
                self._at_top = True
            if self._at_top and angle < self.top_threshold:
                return RepState.DESCENDING
            return None

        if self.state == RepState.DESCENDING:
            if angle <= self.bottom_threshold:
                return RepState.BOTTOM
            if angle >= self.top_threshold:
                # Went back up without reaching bottom — abort this rep
                return RepState.WAITING
            return None

        if self.state == RepState.BOTTOM:
            if angle > self.bottom_threshold:
                return RepState.ASCENDING
            return None

        if self.state == RepState.ASCENDING:
            if angle >= self.top_threshold:
                return RepState.WAITING   # rep complete
            if angle <= self.bottom_threshold:
                return RepState.BOTTOM    # dropped back down
            return None

        return None

    def _do_transition(self, new_state: RepState, timestamp: float) -> None:
        old_state = self.state
        self.state = new_state
        self._pending = None
        self._pending_count = 0

        if old_state == RepState.ASCENDING and new_state == RepState.WAITING:
            lowest = self._min_angle if self._min_angle < float('inf') else self.top_threshold
            self.reps.append(Rep(
                timestamp=round(float(timestamp), 3),
                lowest_angle=round(float(lowest), 2),
                valid=bool(lowest <= self.depth_threshold),
                start_timestamp=round(float(self._descent_start), 3),
            ))
            self.rep_count += 1
            self._min_angle = float('inf')

        elif new_state == RepState.DESCENDING:
            self._min_angle = float('inf')
            self._descent_start = timestamp
