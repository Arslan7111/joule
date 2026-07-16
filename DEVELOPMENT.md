# Joule — Development Log

Gym computer-vision system: per-person rep counting, joint angles, exercise
classification, form scoring, injury-risk signals, session identity, and
multi-camera 3D triangulation. Target hardware: NVIDIA Jetson Orin Nano;
developed and validated on Apple Silicon (hurricane_env, Python 3.10).

---

## Architecture

```
video/RTSP/webcam per camera (one thread each)
  → YOLOv8 person detection + ByteTrack tracking      (src/detector.py)
  → Re-ID: appearance embedding → session gallery      (src/reid.py, src/session.py)
  → MediaPipe Pose (top-down crop, CPU delegate)       (src/pose.py)
  → One Euro keypoint smoothing                        (src/smoothing.py)
  → 9 joint angles incl. trunk lean                    (src/angles.py)
  → adaptive rep state machines (per PERSON)           (src/state_machine.py)
  → exercise classification (heuristic / trainable)    (src/exercise_classifier.py)
  → form scoring + coaching cues                       (src/form.py)
  → injury-risk signals per set                        (src/risk.py)
  → JSON output + live dashboard + annotated video     (src/output.py, src/dashboard.py, src/visualiser.py)

optional multi-camera:
  2D keypoints from 2+ calibrated views → DLT triangulation → true 3D angles,
  knee valgus                                          (src/triangulation.py, tools/calibrate.py)
```

Core design decisions:

- **Exercise state is keyed by person, not tracker track.** ByteTrack fragments
  under occlusion (measured: 13 track ids for 2 people in 20 s); the Re-ID
  gallery merges fragments so a set survives track loss.
- **Adaptive rep thresholds.** Fixed "textbook" angle thresholds missed most
  real reps (perspective compression, partial range of motion). Each state
  machine learns the person's motion range (p10–p90 of the last 3 s) and
  places triggers at fractions of it. Median-5 smoothing kills keypoint
  flicker; 12° minimum range prevents phantom reps while standing.
- **Conservative identity matching.** An uncertain Re-ID match enrolls a new
  anonymous person rather than risking attributing reps to the wrong member.
  Embeddings are session-only, never persisted.
- **Locomotion rejection in two layers.** Gait-frequency classification
  (`cardio`, no counting) plus a rep-level filter for runs of ≥6 uniform
  sub-0.9 s cycles.
- **MediaPipe on the CPU delegate** — its GPU path conflicts with PyTorch
  Metal on macOS. Model priority full > heavy > lite (benchmarked: full gave
  100% elbow-angle coverage vs 96% lite, 90% heavy).

## Development timeline

**Phase 1 — Core pipeline.** Detector + ByteTrack + MediaPipe (Tasks API)
+ angle math + rep state machine + multi-camera threading + JSON output +
station labels + per-camera exercise filtering + annotated video + live
display + zero-dependency web dashboard.

**Phase 2 — First real-footage validation.** A 25 s arm-exercise clip
exposed that fixed thresholds counted 1 rep out of ~13. Rebuilt rep counting
as adaptive; caught drop reps (small fast pulses) by shortening the adaptive
window to 3 s and lowering the min-range gate to 12°. 1 → 11 → 13 reps.
Upgraded pose model lite → full, added One Euro smoothing (removed false
asymmetry flags from keypoint noise).

**Phase 3 — Intelligence layer.** Exercise classification (heuristic rules
+ trainable NumPy logistic regression via `tools/train_classifier.py`),
per-rep form scoring (depth, tempo, trunk lean, symmetry, ROM consistency)
with coaching cues, set-level injury-risk signals (fatigue decline, ROM
degradation, tempo collapse, chronic asymmetry), hard-example collection
for future pose fine-tuning.

**Phase 4 — Session identity.** Appearance embeddings (MobileNetV3 +
clothing color histogram), thread-safe session gallery shared across
cameras, `/checkin` HTTP endpoint binding member names, person labels in
overlay/dashboard/JSON.

**Phase 5 — Multi-person validation (stock footage).** Re-ID consolidated
13 fragmented tracks into exactly 2 identities with zero cross-matches
(same-person sims 0.84–0.92, different-person 0.57–0.73, threshold 0.75).
Caught and fixed the treadmill false-positive (23 phantom squat reps → 0)
via cardio classification + locomotion filter. Refactored all exercise
state to per-person. Detector experiments (yolov8s@960, coasting,
probation) reverted by user preference; benchmarks preserved in config
comments for re-enabling.

**Phase 6 — 3D triangulation.** DLT triangulation with per-joint
outlier-view rejection, true 3D joint angles, frontal-plane knee-valgus
measure, checkerboard calibration tool. Validated against CMU Panoptic
motion-capture ground truth.

## Validation results

| Test | Result |
|---|---|
| Rep counting, real arm exercise (incl. drop set) | 13/≈13 reps |
| Rep counting, barbell squats (side view) | 6/6 reps |
| Rep counting, pull-ups | 4/4 reps |
| Treadmill false positives | 23 phantom reps → 0 |
| Standing still, 60 s with pose jitter | 0 phantom reps |
| Re-ID, 2 people crossing/occluding | 13 tracks → 2 identities, 0 mismatches |
| Check-in flow (enroll → name → attribution) | End-to-end verified |
| 3D angles vs motion capture (5 cams, 101 frames) | mean 3.7°, 100% joint coverage (single view: 5.0° with unmeasurable joints) |
| 3D elbow angle vs single view | 10.5° error → 4.1° |
| Synthetic elevated (2 m) camera, squat bottom | single view −11° bias; 3D < 1° |
| Knee valgus (synthetic 6 cm collapse) | 19.6° vs 5.4° clean — clearly separable |

Test assets: Pexels stock clips in `test_videos/`, CMU Panoptic sample
(5 synchronized HD views + calibration + mocap GT) in `test_videos/panoptic/`.

## Known limitations / honest notes

- Single-view absolute angles carry perspective bias (~7–11° at elevated
  mounts). Rep counting is immune (adaptive); depth *certification* is not —
  that's what 3D clusters are for.
- Knee valgus and other frontal-plane injury signals require ≥2 views.
- Heuristic exercise labels are family-accurate but coarse (pull-ups read
  as "press"); the trainable classifier should own fine labels once real
  labeled footage exists.
- Deep slow stretching can register as squat reps (kinematically similar).
- Full body **including feet** must be in frame on every camera — confirmed
  three separate times (own footage, stock footage, CMU dome cams).
- Risk signals are training-load indicators, not medical claims.

## Deployment guidance (current thinking)

- 2D covers counts, tempo, identity, trends — most of a gym. 3D (3–4 cameras,
  60–90° apart) only where joint-geometry claims matter: squat racks,
  Olympic platforms.
- One 2D camera covers ~3–4 adjacent machines.
- Sussex University gym estimate: ~20 cameras full coverage; ~10-camera
  2D-only MVP.
- Jetson budget: roughly 2–4 cameras per Orin Nano at reduced frame rates;
  detector/model/imgsz knobs in `src/config.py` trade accuracy for throughput.

**Phase 7 — Live multi-camera fusion.** `--fuse rig.npz` mode
(src/fusion.py): N synchronized sources processed as one station —
independent detection per view, cross-view person association via the Re-ID
gallery (validated live: 3 views matched to one person at sims 0.83–0.84),
per-person triangulation with single-view 2D fallback, valgus series in
output, world up-axis configurable in the rig file (Panoptic is Y-down).
End-to-end on Panoptic: fused left-elbow vs mocap mean 4.4°; trunk lean
1.6° median on an upright subject; valgus 3.5–4.8° median (no valgus,
correct); 100% frame coverage on all joints from 3 views.

## Roadmap

1. Real gym footage validation (highest information value per hour)
2. Camera layout plan from actual floor plan; on-site sight-line checks
3. Trained exercise classifier from labeled footage
4. Kiosk/QR check-in integration
5. Timestamp-based sync for live RTSP multi-camera streams
6. Jetson port and throughput tuning
