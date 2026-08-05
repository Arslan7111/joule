# Joule — Status

Where the project stands and what's left. For full technical detail and
dated entries, see [DEVELOPMENT.md](DEVELOPMENT.md); for usage, see
[README.md](README.md); for the phased execution plan behind the items
below, see [ROADMAP.md](ROADMAP.md).

## Done

**Core pipeline** — person detection (YOLOv8n) + ByteTrack, MediaPipe pose
(top-down crop, CPU delegate), 9 joint angles incl. trunk lean, adaptive
per-person rep counting, multi-camera threading, JSON output, live
dashboard, annotated video export.

**Intelligence layer** — exercise classification (heuristic rules, now
also a trained model), per-rep form scoring with coaching cues, set-level
injury-risk signals (fatigue, ROM degradation, tempo collapse, asymmetry),
reference-based form scoring against a recorded good execution (AIFit-style).

**Session identity** — appearance-embedding Re-ID gallery shared across
cameras, survives track loss and camera switches, `/checkin` endpoint to
bind a real name.

**3D triangulation** — DLT triangulation from 2+ calibrated cameras, true
3D joint angles, frontal-plane knee valgus (invisible to a single camera),
checkerboard calibration tool.

**Live multi-camera fusion** — `--fuse rig.npz` runs N synchronized
sources as one station: cross-view Re-ID association, per-person 3D with
single-view 2D fallback.

**External validation (no footage required)**
- Rep counting benchmarked on RepCount Part-A (152 real YouTube workout
  videos, published dataset): competitive with trained CVPR-level methods
  ([TransRAC](https://arxiv.org/pdf/2204.01018)) using zero training on
  our side.
- 3D triangulation validated against CMU Panoptic motion-capture ground
  truth: 3.7° mean joint-angle error on the original tuned 5-camera
  sequence, 6.1° on a second, held-out, untuned sequence with a less
  favorable 3-camera arc (see [README.md](README.md) and
  [DEVELOPMENT.md](DEVELOPMENT.md) Phase 8 — both figures are correct,
  different sequences, not a regression).
- Exercise classifier trained on 280 labeled RepCount videos — every
  gym-core class (squat, front raise, pull-up, push-up) improved over the
  heuristic rules.
- 3D triangulation also validated against Fit3D mocap ground truth — real
  gym exercises (squat, deadlift, curls, rows, presses), not generic dome
  poses. Standing/unencumbered exercises land in the same 5–7° range as
  the Panoptic figures above; squat/pushup show real, larger error (up to
  13.3° mean) on genuinely harder, more self-occluded poses. See
  [ROADMAP.md](ROADMAP.md) Phase C3.

**All of the above is committed and pushed** to
[github.com/Arslan7111/joule](https://github.com/Arslan7111/joule) (private).

## Known limitations (honest, not blockers)

- Single-view absolute angles carry perspective bias; rep *counting* is
  immune (adaptive), depth *certification* needs 3D.
- Bench press: classification is fixed, but counting is weak when filmed
  head-on — the elbow signal is too foreshortened/occluded. Needs a side
  camera angle, not a code fix.
- Sit-ups deliberately count zero — no hip-driven rep counter exists yet.
- Full body **including feet** must stay in frame.
- Risk signals are training-load indicators, not medical claims.

## What's left

### Blocked on you
1. **Real gym footage** — the single highest-value next step. Phone clips
   of real exercises (validates everything under real conditions, doubles
   as classifier training data), plus a two-phone clap-synced squat set
   with a checkerboard calibration pass, for the first real-world 3D
   fusion run. Feet in frame on every camera.
2. **M3GYM dataset access** — needs a form
   ([M3GYM request form](https://forms.gle/stJZgHaji7KNa5t7A), academic
   email/affiliation/purpose); approval takes days. Would let us score
   Re-ID against ground-truth subject IDs in a real multi-person gym.
   Academic-license-only, fine for validation, not for training a shipped
   model. (Fit3D obtained 2026-08-05 and already used — see Done above.)

### Ready whenever, no blockers
4. Build a real trainer reference signature once any good-form footage
   exists (feature already built and tested, just needs footage).
5. RTSP timestamp sync — needed before live streams replace pre-synced
   recordings.
6. Jetson port and throughput tuning.

### Lower priority
- Hip-driven rep counter (sit-ups, and would improve hinge movements).
- Scale classifier training to the full 758-video RepCount train split
  (likely modest gains over the current 280-video subset).
