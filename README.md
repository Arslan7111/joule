# Joule — Gym Workout Analysis Pipeline

Per-person **rep counting** and **joint angle extraction** from gym camera footage.

Detection → tracking → pose → angles → rep state machine, one thread per camera.

| Stage | Tech |
|---|---|
| Person detection | YOLOv8n (COCO class 0) |
| Tracking | ByteTrack (60-frame lost-track buffer) |
| Pose estimation | MediaPipe Pose Landmarker (top-down crop) — falls back to YOLOv8n-Pose |
| Angles | 9 joints: shoulders, elbows, hips, knees + trunk lean |
| Rep counting | Adaptive state machine: waiting → descending → bottom → ascending |
| Exercise classification | Heuristic rules out of the box; trainable NumPy logistic regression |
| Form scoring | Per-rep 0–100: depth, tempo, trunk lean, symmetry, ROM consistency |
| Form correction | Coaching cue per detected issue (JSON + live dashboard) |
| Injury-risk signals | Set-level: fatigue decline, ROM degradation, tempo collapse, chronic asymmetry |
| Session Re-ID | Person identity persists across frame exits and cameras (MobileNetV3 + color embedding) |
| Check-in | HTTP endpoint binds a member name to a tracked person |

## Setup

```bash
conda activate hurricane_env          # Python 3.10 env with PyTorch
pip install -r requirements.txt
```

Model files expected in the project root (already present):
`yolov8n.pt`, `yolov8n-pose.pt`, `pose_landmarker_lite.task`

## Run

```bash
python pipeline.py \
  --sources squat_cam.mp4 pullup_cam.mp4 \
  --names squat_rack_1 pullup_bar \
  --exercises squat upper_body \
  --output results/ \
  --dashboard
```

Then open **http://localhost:5000** for the live dashboard.

| Flag | Meaning |
|---|---|
| `--sources` | Video files, RTSP/HTTP URLs, or webcam indices (`0`) — one per camera |
| `--names` | Unique station label per source (default `cam_0`, `cam_1`, …) |
| `--exercises` | `squat` \| `upper_body` \| `both` \| `auto` per source (default `both`) |
| `--output` | Results directory (default `results/`) |
| `--dashboard` | Live web dashboard on `--port` (default 5000) |
| `--live` | Native display window, press **q** to stop |
| `--visualise` | Save annotated MP4 per camera |
| `--collect-hard` | Save low-confidence pose crops to `<output>/hard_examples/` |

`--exercises auto` classifies the exercise from movement (re-evaluated every
2 s per person) and picks the matching rep counter automatically.

With no `--sources`, a synthetic test video is generated so the whole pipeline can be smoke-tested.

## Output

Per camera: `<name>.json` — plus `merged.json` combining all cameras.

```json
{
  "station": "squat_rack_1",
  "exercise": "squat",
  "primary_angles": ["left_knee", "right_knee", "left_hip", "right_hip", "trunk_lean"],
  "tracks": [
    {
      "track_id": 1,
      "rep_counts": {"squat": 8},
      "reps": [{"timestamp": 4.2, "lowest_angle": 84.1, "valid": true}],
      "angle_series": {"left_knee": [[0.0, 172.3], "..."]}
    }
  ]
}
```

A rep is `valid` when it reached the adaptive depth threshold. Each rep also
carries `duration` and a `form` block:

```json
"form": {"score": 82, "issues": ["too fast (0.5s) — likely using momentum"]}
```

Form checks: depth, tempo (0.8–12 s healthy), trunk lean (per-exercise limit),
left/right symmetry (>18° flagged), and ROM consistency vs the set median.
Each triggered check adds a corrective coaching `cue`. Weights, limits, and cue
text live in [src/form.py](src/form.py).

Each track also gets a `risk_assessment` per exercise — set-level injury-risk
signals (low/moderate/high): fatigue form decline, ROM degradation, tempo
collapse, chronic asymmetry ([src/risk.py](src/risk.py)). These are
training-load indicators, not medical advice; frontal-plane risks (knee
valgus) require the future multi-camera setup.

## Exercise classification

`--exercises auto` uses heuristic biomechanical rules by default (which joints
move, how much, torso position) — classes: squat, lunge, hinge, curl, press,
pullup, row. To upgrade to a model trained on your own footage:

1. Run the pipeline on videos of known exercises
2. Sort the result JSONs into folders named by class:
   `training_data/squat/*.json`, `training_data/curl/*.json`, …
3. Train: `python tools/train_classifier.py training_data/`

The model saves to `models/exercise_clf.npz` and is loaded automatically on
the next run (delete the file to fall back to heuristics).

## Session identity (Re-ID + check-in)

Re-ID is on by default (`--no-reid` disables). Every tracked person gets an
appearance embedding (MobileNetV3 features + clothing color histogram,
sampled ~1×/s). A session gallery shared across all cameras matches new
tracks against known people — identity survives leaving the frame, changing
stations, and switching cameras. Unmatched tracks enroll as `person_1`,
`person_2`, …

Check-in binds a real name (kiosk/QR integration point):

```bash
curl "http://localhost:8080/people"                          # who is tracked
curl "http://localhost:8080/checkin?person=person_1&name=Ahmed"
```

All exercise state — rep counters, angle history, classification, form —
is **keyed by person, not tracker track**. When the tracker fragments (fast
motion, occlusion), the fragments re-identify into the same person and their
set continues uninterrupted; output JSON records are one-per-person with the
merged `track_ids` listed. With Re-ID disabled each track is its own person.

The name appears live on the dashboard and in the output JSON (`person`
field per track). Matching is deliberately conservative
(`REID_MATCH_THRESHOLD` 0.75): an uncertain match enrolls a new anonymous
person rather than risking attributing reps to the wrong member. Embeddings
live only in memory for the session — nothing biometric is persisted.

## Multi-camera triangulation (3D)

[src/triangulation.py](src/triangulation.py) triangulates 2D keypoints from
2+ calibrated synchronized cameras into a 3D skeleton (DLT with per-joint
outlier-view rejection), computes true 3D joint angles (same joint names as
the 2D path), and measures frontal-plane knee valgus — the injury signal a
single camera cannot see.

Validated against CMU Panoptic motion-capture ground truth (101 frames,
5 cameras, full detector+pose+triangulation pipeline): mean joint-angle
error 3.7° with 100% joint coverage, vs 5.0° for a single view with entire
joints unmeasurable. Elbows improved most (10.5° → 4.1°); synthetic tests
with elevated 2 m cameras show single-view squat-depth error of ~11° at the
bottom position collapsing to <1° in 3D.

Calibrate a camera pair once with [tools/calibrate.py](tools/calibrate.py)
(checkerboard, both cameras simultaneously). Test data: CMU Panoptic sample
in `test_videos/panoptic/`.

## Improving pose robustness

Run with `--collect-hard` to save person crops where pose estimation failed or
was low-confidence to `<output>/hard_examples/<camera>/`. Review these to spot
systematic problems (occlusion by machines, unusual viewpoints); they are the
labelling starting point if pose fine-tuning ever becomes necessary.

## Rep detection & tuning

Walking/running is rejected two ways: the classifier flags gait-frequency
knee oscillation as `cardio` (no rep counting), and a rep-level locomotion
filter drops runs of ≥6 uniform sub-0.9s cycles (`locomotion: true` in the
JSON). Validated on treadmill footage: 23 phantom squat reps → ~1.

Rep thresholds are **adaptive by default**: each person's state machine learns
their observed motion range (10th–90th percentile of the last 3 s of joint
angle) and places the top/bottom triggers at fractions of that range. This
handles camera perspective, partial range of motion, and amplitude changes
mid-set (e.g. drop reps) without per-camera tuning. The signal is
median-filtered (5 frames) to remove keypoint flicker, and no reps are counted
until at least `MIN_ANGLE_RANGE` (12°) of motion is seen — so standing still
never counts.

Knobs in [src/config.py](src/config.py):

- `ADAPTIVE_THRESHOLDS` — set `False` to use the fixed thresholds below
- `TOP_FRACTION` / `BOTTOM_FRACTION` / `DEPTH_FRACTION` (0.70 / 0.35 / 0.25) — where in the motion range the triggers sit
- `MIN_ANGLE_RANGE` (12°) — motion required before counting starts
- `ADAPTIVE_WINDOW_SECONDS` (3 s) — how quickly thresholds re-learn a new rep amplitude
- `TOP_THRESHOLD` / `BOTTOM_THRESHOLD` / `DEPTH_THRESHOLD` (160° / 110° / 100°) — fixed-mode values
- `POSE_CONF_THRESHOLD` (0.5) — minimum keypoint visibility

## Layout

```
pipeline.py            CLI entry point, threading, live display
bytetrack_config.yaml  Tracker settings (track_buffer: 60 ≈ 2 s)
src/
  config.py            All constants and thresholds
  detector.py          YOLOv8n + ByteTrack
  pose.py              MediaPipe (CPU delegate) / YOLOv8n-Pose fallback
  angles.py            Joint angle + trunk lean math
  state_machine.py     Adaptive rep counting state machine
  features.py          Motion features from angle series
  exercise_classifier.py  Heuristic + trainable exercise classification
  form.py              Per-rep form quality scoring
  camera.py            Per-camera processing loop
  visualiser.py        Skeleton, angle arcs, rep overlay
  output.py            JSON writers
  dashboard.py         Zero-dependency web dashboard
tools/
  train_classifier.py  Train exercise classifier from labelled runs
```

## Notes

- MediaPipe runs with the **CPU delegate** — required on macOS to avoid a Metal
  conflict with PyTorch. Not an issue on Jetson.
- On macOS, `cv2.imshow` must run on the main thread; camera threads hand frames
  over via queues (`--live` handles this automatically).
- Press **q** (live window) or **Ctrl+C** to stop early — partial results are still written.
