# Workstream C spike — barbell detector: trained, validated, NOT integrated

Date: 2026-09-08. Model: YOLOv8n fine-tuned on `computer-vision-1bdzc/
barbell-detection-yolov5` v6 (Roboflow Universe, CC BY 4.0, 1,712 source
images / 4,149 after their own augmentation, single `barbell` class).
12 epochs, imgsz 320, 35% data subsample (CPU time budget), `patience=5`.
Weights: `models/bar_detector.pt` (6.2 MB, not committed — see below).

## Training-set validation numbers (Roboflow's own held-out split)

Precision 0.878, Recall 0.750, **mAP50 0.852**, mAP50-95 0.498, 16.9 ms/image
CPU inference at 320px. Looked like a genuinely usable single-class detector
on paper.

## Real-footage check: it doesn't generalize. Decision = do NOT integrate.

Tested on footage the model never saw in training — Fit3D (studio, real
license, validation-only) and RepCount (real YouTube gym footage, licensed):

| Clip | Bar actually visible? | Detection |
|---|---|---|
| Fit3D s03 deadlift | yes, clearly (gold bar, held) | **missed** (no detection) |
| Fit3D s10 deadlift | yes, clearly | **missed** (no detection) |
| Fit3D s03 barbell_row | yes, clearly | **false positive** — boxed the red studio carpet at 0.82 confidence, not the bar |
| Fit3D s03 squat | no bar in this rep (bodyweight-style) | false positive — boxed the carpet at 0.44 |
| RepCount `stu9_64`/`stu6_63` ("squat") | no — real bodyweight backyard squats | false positive — boxed a wooden fence post at 0.65/0.41 |

**On the three real clips that should have shown a bar, it got 0 of 3
right** — either missing an obviously-visible bar entirely, or confidently
boxing an unrelated vertical/textured background element (a carpet edge, a
fence post) instead. Confidence scores for the false positives (0.41–0.82)
span too wide a range for a simple threshold change to fix this.

**Likely cause**: the training images (Roboflow's community-sourced set) are
mostly real gyms with loaded plates near floor level; Fit3D's bar is bare
(no plates, motion-capture studio, red carpet) and RepCount is unconstrained
home-workout footage — genuine domain shift, on top of the ~8% off-topic/
stock images already noted in the dataset itself
(`tools/train_bar_detector.py` docstring). A 12-epoch nano model on a 35%
subsample at 320px is also a deliberately cheap first pass, not a serious
attempt.

## Disposition

- **`BAR_DETECT_ENABLED` stays `False`.** The plumbing (`src/bardetector.py`,
  the per-frame hook in `src/camera.py`, `bar_series` in the output JSON) is
  built, tested for graceful no-weight degradation, and safe to leave in
  place — it does nothing until both the flag is flipped and a
  weight file is at `models/bar_detector.pt`.
- **Did not proceed to feature/classifier integration** (extending
  `src/features.py`, retraining `models/exercise_clf.npz`, the hinge/row
  heuristic). Building on a bar signal that's wrong ~100% of the time on
  real footage in this check would actively hurt classification, not help
  it — the same reasoning that sank the first per-window confidence-gate
  attempt on 2026-08-11 (`ROADMAP.md`).

## If this is revisited

1. Train longer, on the full dataset (100% not 35%), at full 640px — this
   pass was deliberately cut down for same-session CPU/time budget, not
   because 320px/35% was judged sufficient.
2. Manually filter the ~8% off-topic images noted in the dataset before
   retraining, rather than accepting the noise.
3. Try one of the other CC BY 4.0 candidates found the same session
   (`hackerfit/barbell-detector-svmfh-da6pw`, 444 images, YOLO11-oriented)
   or combine multiple sources.
4. Best real fix: validate against real gym footage once Phase D lands —
   both Fit3D (studio) and RepCount (unconstrained home workouts) are
   genuinely different visual domains from a normal gym floor with loaded
   plates, which is what this detector was actually trained to see.
