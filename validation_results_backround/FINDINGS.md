# Workstream A spike — silhouette back-rounding metric: FINDING = do not integrate

Date: 2026-09-08. Script: `tools/spike_back_round.py` (tracked). Data: Fit3D
`deadlift`, `squat`, `dumbbell_reverse_lunge`, subjects s03 + s10, auto-selected
side-view camera per clip. Fit3D read only (validation licence).

## Decision-gate outcome

**FAIL.** A stable, orientation-independent, cross-subject-repeatable
spinal-flexion signal could not be pulled from the MediaPipe person-segmentation
silhouette within a spike's budget. Per the plan, workstream A does **not**
proceed to integration (no `src/pose.py` change, no `back_round` series, no
`form.py` metric). `src/pose.py` was reverted; the only surviving change is the
spike script and this note.

## What was confirmed to work

- **MediaPipe segmentation is available and cheap on full frames**:
  `output_segmentation_masks=True` + `RunningMode.IMAGE` + `num_poses=1`,
  ~20 ms/frame on this CPU, 300+/300 frames returning a pose+mask across 3 test
  clips, zero crashes.
- **It aborts on *cropped* input** on this build (mediapipe 1.0.0, Windows):
  `image_frame.cc:415 Check failed: 1 == ChannelSize() (1 vs. 4)`, a hard
  `abort()` inside the mask calculator. Any future attempt must run the
  segmented pass on whole frames, not `PoseEstimator`'s padded crop.
- Auto side-camera pick (narrowest shoulder-width / torso-height) chose a
  sensible profile view on every clip.

## What failed, and why

Three geometry attempts at "the back contour", each on the same silhouette:

| Attempt | Method | Result |
|---|---|---|
| 1 | March perpendicular from the shoulder→hip chord until the mask ends | Back-edge distance came out at **0.6–0.7 × torso length** — the ray punches through the torso and out the far side (arms, plates, far leg). Measures body width, not spine shape. |
| 2 | Scan the full perpendicular cross-section, take the posterior end of the contiguous run through the chord point | Collapses at the flexed part of every rep: valid only for the top ~25 % of each rep, `bottom_bow = null` for squat both subjects. `corr(trunk_lean)` per clip: −0.81, −0.22, −0.41, −0.35, +0.29, +0.33 — no stable relationship. |
| 3 | Torso-mask centroid offset from the chord along the posterior normal | Always computable (`cent_finite = 1.0`), but `corr(trunk_lean)` per clip: −0.27, −0.80, +0.43, −0.82, −0.08, −0.72 and `corr(driver angle)`: 0.39, 0.72, −0.42, 0.85, 0.02, 0.66 — sometimes tracks torso orientation, sometimes the rep motion, sometimes neither. `bottom_cent` per clip ranged −0.48 … +0.08 (posterior-direction sign flips on s10/deadlift). |

Across all three: no repeatable within-rep trajectory, no sensible
exercise discrimination (`deadlift_bottom_bow > squat` was false), and the
signal is not cleanly independent of trunk lean — on several clips it *is* trunk
lean, on others it is noise.

Root cause: isolating the **posterior torso boundary** (excluding arms, the
implement, the far-side leg; picking the correct "back" side; normalising for
camera obliqueness) is the entire problem, and it is not robust on Fit3D's
varied camera geometry with a naive silhouette march. Jeremy Park's demo very
likely had a fixed camera, a fixed subject position, and deliberately
exaggerated rounded-vs-flat reps; Fit3D is varied geometry and uniformly coached
(good) form, so there is little genuine rounding to separate and lots of
confounds.

## If this is revisited (not now)

1. **Re-add the `src/pose.py` scaffolding** — `segmentation: bool = False` ctor
   flag driving `output_segmentation_masks`, a `self.last_mask` frame-coord
   attribute set in `_estimate_mediapipe`, **run on the full frame** not the
   crop (the crop path aborts). ~6 lines; was written and reverted this session,
   see git history for commit-free diff or just redo.
2. **Proper torso isolation before any contour**: mask out limb regions using
   the arm/leg landmarks, restrict to the shoulder–hip band, work in a
   torso-normalised frame (u = chord, v = posterior normal), and take the
   posterior boundary of *that* region only.
3. **Try RF-DETR segmentation** (Apache-2.0) instead of MediaPipe's mask —
   sharper body boundary, and it was Park's actual choice.
4. **Anchor to the subject's own standing baseline** per clip (first/last
   upright frames) and report *change* from it, not an absolute silhouette
   measure — kills body-shape and camera-distance confounds.
5. Consider that the honest home for this may be **fixed-camera gym-install
   footage** (Phase D), where camera geometry is constant and form actually
   varies, rather than a dataset of coached studio reps.

## Evidence in this directory

- `summary.json` — per-clip + pooled stats, the numbers quoted above.
- `s03_deadlift_roundness_map.png`, `s03_deadlift_back_shape.png`, etc. — the
  per-clip plots showing the flat/noisy per-frame signal and the
  0.6–0.7-torso-length back-edge distances from attempt 1.
