"""
Session gallery — persistent person identity within a gym session.

One gallery is shared by every camera thread.  Each person has an
EMA-updated appearance embedding.  When a new track appears anywhere,
its embedding is matched against the gallery:

  similarity ≥ REID_MATCH_THRESHOLD → existing person (identity carries over
      across frame exits, station changes, and cameras)
  otherwise → a new person is enrolled (person_1, person_2, …)

Check-in binds a real name to a person id (kiosk/QR integration later;
GET /checkin on the dashboard for now).  Mis-attribution is the worst
failure mode, so matching is deliberately conservative: below-threshold
tracks stay anonymous rather than guessing.
"""

import logging
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from .config import REID_EMA_ALPHA, REID_MATCH_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class Person:
    person_id: str
    embedding: np.ndarray            # unit-norm, EMA-updated
    name: str | None = None
    n_updates: int = 1
    last_seen: float = field(default_factory=time.time)
    last_camera: str = ''

    @property
    def label(self) -> str:
        return self.name or self.person_id


class SessionGallery:
    """Thread-safe identity gallery for one session."""

    def __init__(self, match_threshold: float = REID_MATCH_THRESHOLD) -> None:
        self.match_threshold = match_threshold
        self._people: dict[str, Person] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def identify(self, embedding: np.ndarray, camera_id: str = '') -> tuple[str, float]:
        """
        Match an embedding against the gallery; enroll a new person when no
        match clears the threshold.  Returns (person_id, similarity).
        """
        with self._lock:
            best_id, best_sim = None, -1.0
            for pid, person in self._people.items():
                sim = float(np.dot(embedding, person.embedding))
                if sim > best_sim:
                    best_id, best_sim = pid, sim

            if best_id is not None and best_sim >= self.match_threshold:
                self._update_locked(best_id, embedding, camera_id)
                return best_id, best_sim

            self._counter += 1
            pid = f"person_{self._counter}"
            self._people[pid] = Person(
                person_id=pid, embedding=embedding.copy(), last_camera=camera_id
            )
            logger.info(f"Gallery: enrolled {pid} (best existing sim {best_sim:.2f})")
            return pid, 1.0

    def update(self, person_id: str, embedding: np.ndarray, camera_id: str = '') -> None:
        with self._lock:
            self._update_locked(person_id, embedding, camera_id)

    def _update_locked(self, person_id: str, embedding: np.ndarray, camera_id: str) -> None:
        p = self._people.get(person_id)
        if p is None:
            return
        e = (1.0 - REID_EMA_ALPHA) * p.embedding + REID_EMA_ALPHA * embedding
        n = np.linalg.norm(e)
        p.embedding = (e / n if n > 0 else e).astype(np.float32)
        p.n_updates += 1
        p.last_seen = time.time()
        p.last_camera = camera_id

    def bind_name(self, person_id: str, name: str) -> bool:
        """Check-in: attach a member name to a person id."""
        with self._lock:
            p = self._people.get(person_id)
            if p is None:
                return False
            p.name = name
            logger.info(f"Gallery: {person_id} checked in as '{name}'")
            return True

    def label(self, person_id: str | None) -> str:
        if person_id is None:
            return ''
        with self._lock:
            p = self._people.get(person_id)
            return p.label if p else person_id

    def people(self) -> list[dict]:
        with self._lock:
            return [
                {
                    'person_id': p.person_id,
                    'name': p.name,
                    'sightings': p.n_updates,
                    'last_camera': p.last_camera,
                    'last_seen': round(time.time() - p.last_seen, 1),
                }
                for p in self._people.values()
            ]
