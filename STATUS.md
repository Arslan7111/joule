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
  gym exercises, not generic dome poses. Full-scale run: all 8 licensed
  subjects × all 28 named exercises (224 clips, ~1.16M joint-frame
  samples) — mean 10.1°, median 6.2°, zero failed/empty/missing clips.
  Standing/unencumbered exercises land in the same 5–7° range as the
  Panoptic figures above; squat/pushup show real, larger error on
  genuinely harder, more self-occluded poses. One subject (s10)'s 13.0°
  mean outlier is now root-caused: an isolated tracking dropout on one
  exercise (`walk_the_box`) plus a separate, consistent `left_hip` bias
  across several other exercises — neither threatens the headline number.
  A follow-up camera-count/angle sweep found 3-of-4 cameras barely matters
  (any combination), but for a 2-camera station specifically, avoid
  placing the two cameras directly opposite each other (~180°) — measured
  7.7–11.8° mean error at 47–133° convergence vs. 16.5–18.2° at ~180°,
  confirmed on two different exercises. See [ROADMAP.md](ROADMAP.md)
  Phase C3 and [CAMERA_PLACEMENT.md](CAMERA_PLACEMENT.md) rule 4.

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
- Exercise classifier: the original full-scale Fit3D check (224 clips)
  reported 0% accuracy on press/raise/situp — largely a mismapped-test
  artifact (RepCount's `press` is bench press, not the standing overhead
  press Fit3D was mapped to; same issue for `raise`/`situp`), not a real
  domain-shift failure. Corrected mapping + a real classification-
  aggregation bug fix (`src/camera.py::_record_classification`, was
  keeping only the last ~6s snapshot instead of voting across a track)
  brings the two genuinely-matched classes (squat, pushup) to 100%/88%,
  and independently improves 6 of 7 classes on RepCount itself (58%→62%
  overall).
- Follow-up: added a confidence gate on the *final* classification
  (`FINAL_CONFIDENCE_GATE = 0.40`, withholds the answer as `'unknown'`
  rather than guessing when unconfident) plus a confined heuristic
  fallback for `hinge`/`lunge`/`curl`/`row` (still not in the trained
  model's own class list, but the heuristic rules can now surface them
  when the trained model is unconfident *and* the heuristic has a clear
  majority). Real tradeoff, not a free win: RepCount overall accuracy
  moves 62%→58% (20/133 tracks now honestly `'unknown'` instead of a
  guess — mostly former wrong answers, a few low-confidence-correct
  ones). `curl` recognition goes 0%→41% on Fit3D; `hinge`/`lunge` are
  still essentially unrecognized (0%), just honestly so now instead of a
  confident wrong guess. Fit3D's out-of-scope `pullup` bias drops
  52%→43%. Actually recognizing hinge/lunge/row still needs a dataset
  with those exact movements (RepCount doesn't have them) or real gym
  footage.
- Follow-up (2026-08-12): recovered `lunge` via a hip-ROM-asymmetry
  heuristic — `classify_heuristic()` previously had no path that could
  ever return `'lunge'` at all. Validated against RepCount's 149 licensed
  tracks as the regression check (zero false positives, zero flipped
  tracks) and Fit3D's `dumbbell_reverse_lunge` as the recovery check
  (0/8 → 6/8). `hinge` was tried the same way (hip:knee ratio) and
  rejected — sit-ups share the same ratio signature, so no threshold
  separates them without misclassifying real sit-ups. `hinge`/`row`
  remain unrecognized; still need labeled training data, not a heuristic.
  See [ROADMAP.md](ROADMAP.md) Phase C3.
- Follow-up (2026-09-08): a **barbell detector** was trained (YOLOv8n on a
  public CC BY 4.0 dataset) specifically to give `hinge`/`row` an
  equipment-context signal that sidesteps the sit-up feature-overlap
  above — strong numbers on its own held-out set (mAP50 0.85) but **0 of 3
  real bar-visible clips (Fit3D + RepCount) detected correctly** when
  actually checked, so it was **not** wired into the classifier. Kept
  disabled (`BAR_DETECT_ENABLED = False`); full finding in `HANDOVER.md`'s
  2026-09-07/08 session and `validation_results_backround/
  BAR_DETECTOR_FINDINGS.md`.
- Also added (2026-09-08), shipped and safe: a **second, non-authoritative
  rep-count cross-check** (`rep_count_crosscheck` in the output JSON) from
  hip-vertical-displacement, independent of the joint-angle counter.
  **Validated on the full 53-clip squat/pull_up/push_up RepCount set and
  it beats the existing primary counter on every class**: normalized MAE
  0.582→0.316 and OBO 40.0%→58.0% pooled (pull_up 36.8%→57.9% OBO, squat
  50.0%→68.8%). **Recommended next step, not yet actioned**: consider
  promoting it to (co-)primary for squat/pull_up specifically, or at
  minimum surfacing `rep_count_crosscheck` disagreement to a human — this
  is a real, measured accuracy gain on the project's own benchmark, left
  as a decision rather than silently flipped, since `rep_counts` is what
  every existing tool and the historical "MAE 0.742" headline figure
  reads. Full numbers: `HANDOVER.md`'s 2026-09-07/08 session.
  A silhouette-based spinal-flexion/"back-rounding" safety metric was also
  investigated (3 geometries tried) and abandoned — no stable signal, see
  `HANDOVER.md`.

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
7. **Decide whether to promote the displacement rep-count cross-check to
   (co-)primary** for squat/pull_up — measured, not projected, accuracy
   gain on the full 53-clip RepCount benchmark (see above). No engineering
   blocker, just needs a call on changing a cited headline number.
8. **Consider a ViTPose+ Large reprocessing pass for the post-set report.**
   Measured (2026-09-08) on Fit3D squat/pushup: pooled mean joint-angle
   error 14.57°→5.93° swapping only the pose backbone, at ~17× the
   per-frame cost (~305ms vs ~18ms). Too slow for live 30fps, but the
   product's own report window is already 2–5s post-set — plausibly wide
   enough for a heavier backbone on just-finished clips. Also appears to
   resolve the unexplained s10 `left_hip` bias from the original Fit3D
   batch as a MediaPipe-specific weakness. See `HANDOVER.md`.

### Lower priority
- Hip-driven rep counter (sit-ups, and would improve hinge movements).
- Scale classifier training to the full 758-video RepCount train split
  (likely modest gains over the current 280-video subset).
- Retrain the barbell detector properly (full dataset, full resolution,
  off-topic images filtered) if `hinge`/`row` equipment-context detection
  is revisited — see the 2026-09-08 finding above for exactly what a first
  attempt got wrong.
- Silhouette-based back-rounding safety metric — three approaches tried
  and abandoned 2026-09-08; needs real torso/limb isolation or real gym
  footage to have another shot.
