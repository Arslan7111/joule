# Fit3D Dataset — Full Utilization Plan

Written 2026-08-05, after the first Fit3D validation pass (1 subject, 7
exercises — see `ROADMAP.md` Phase C3). This is a planning document, not
an execution log: nothing below has been run yet. Time/compute is
explicitly not a constraint on this plan (per direction) — the goal is to
work out what's actually worth doing with this dataset, then sequence it,
not to minimize runtime. `tools/validate_fit3d.py` already exists and
works; this plan is about scaling and extending its use, not rebuilding it.

## Why this is worth a real plan, not just "run more of the same"

The first pass proved the tool is correct (reverse-engineered format,
verified against real frames, a real scoring bug found and fixed). But it
touched **1 of 8 subjects and 7 of 47 exercises per subject** — a
correctness check, not a statistically solid result, and it only asked
one question ("does 3D triangulation work on real gym exercises?"). This
dataset can answer at least three separate questions this project cares
about, not just that one. The rest of this document works out what those
are and what it would take to answer each properly.

## What's actually in the dataset (full inventory)

- **8 train subjects** (s03, s04, s05, s07, s08, s09, s10, s11), each with
  identical structure: **47 exercise clips**, all 4 cameras, real
  calibration, full `joints3d_25` mocap ground truth.
- Of those 47 clips per subject: **28 are named exercises**, **19 are
  numbered warmup clips** (`warmup_1`...`warmup_19` — generic movement,
  not part of this project's exercise taxonomy).
- **3 test subjects** (s02, s12, s13) — footage + calibration only, no
  ground truth. Correctly unusable for validation (see the discussion in
  today's team update); not revisited by this plan.
- Total real footage available: **284,863 frames across the 28 named
  exercises × 8 subjects**, another **159,960 frames** across the 19
  warmup clips × 8 subjects.
- Measured pipeline throughput from today's run: **~0.22s of wall-clock
  processing per video frame** (4-camera fused: detection + pose +
  triangulation). At that rate:
  - All 28 named exercises × 8 subjects: **~17 hours**
  - Adding all 19 warmups × 8 subjects too: **~27 hours total**
  - Both estimates are for *one process running exercises serially* —
    see the parallelization note below, which changes this materially.

## The 28 named exercises, mapped to this project's taxonomy

For the classifier domain-shift study (Track B below). This mapping is a
first-pass judgment call, not authoritative — worth a quick sanity check
before relying on it, but good enough to plan against.

| Fit3D exercise | Maps to our class | Notes |
|---|---|---|
| squat | `squat` | |
| deadlift | `hinge` | heuristic-only class, never a trained-model output (see below) |
| dumbbell_reverse_lunge | `lunge` | heuristic-only class |
| dumbbell_biceps_curls, dumbbell_hammer_curls, dumbbell_curl_trifecta, drag_curl | `curl` | heuristic-only class |
| dumbbell_overhead_shoulder_press, neutral_overhead_shoulder_press, clean_and_press | `press` | |
| barbell_row, barbell_dead_row, one_arm_row | `row` | heuristic-only class |
| pushup, diamond_pushup | `pushup` | |
| side_lateral_raise, overhead_trap_raises, dumbbell_scaptions, w_raise | `raise` | |
| standing_ab_twists | `situp`? | weak match, core movement but not a sit-up motion — worth checking by eye before trusting |
| band_pull_apart, barbell_shrug, burpees, dumbbell_high_pulls, man_maker, mule_kick, overhead_extension_thruster, walk_the_box | **no match — out of scope** | valuable as negative controls: does the classifier correctly avoid forcing these into one of our classes, or does it confidently mislabel them? |

Reminder from today's session: the **trained classifier only outputs 7
classes** (cardio, press, pullup, pushup, raise, situp, squat) —
`hinge`, `lunge`, `curl`, `row` are heuristic-only and never appear as
trained-model output. Every Fit3D exercise mapped to one of those four in
the table above is *automatically* a domain-shift/coverage-gap probe,
independent of whatever the classifier actually outputs.

## Track A — Full 3D-triangulation accuracy validation

**Question**: does the 5–13° accuracy picture from today's 7-exercise,
1-subject pass hold up across real body-type/clothing/proportion
variation, and across the full range of real gym movements?

- Run all 28 named exercises across all 8 subjects (skip the 19 warmups
  for this track — they're generic movement, not exercises this project
  needs to score, and 8× the frame count for no new stress-test value).
  That's the ~17-hour estimate above, serially.
- **Report per-subject AND pooled statistics**, not just one combined
  number. Today's report only had one subject, so there was no way to
  tell "hard exercise" error from "this particular body type" error —
  8 subjects fixes that.
- **New stress test this scale unlocks**: Fit3D's 4-camera rig lets us
  directly test camera-*count* sensitivity on independent real data for
  the first time. `src/triangulation.py`'s `CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS`
  table (2v/3v/4v/5v thresholds) was tuned entirely against CMU
  Panoptic's 5-camera dome rig. Re-running a subset of exercises with
  2-of-4 and 3-of-4 camera combinations (in addition to today's 4-of-4)
  would show whether that threshold table transfers to a second real
  camera rig with different geometry, or needs a Fit3D-specific
  adjustment — this is exactly the kind of thing that shouldn't be
  assumed from one dataset.

## Track B — Classifier domain-shift characterization

**Question**: today's small sample showed the trained classifier badly
misclassifying Fit3D footage (curls/squat/row/press all read as
"pullup") — is that a real, systematic domain-shift problem worth fixing,
or noise from a 7-exercise sample?

- Run the same footage (Track A's runs produce this for free — the
  classifier's output is already recorded in every pipeline run) and
  build a full confusion matrix: Fit3D exercise (mapped via the table
  above) × classifier's predicted class, across all 8 subjects.
- Specifically check the 8 "no match" exercises as negative controls —
  a classifier that's well-calibrated should show low confidence or
  scattered/inconsistent labels on movements it was never designed to
  recognize, not confidently wrong answers.
- **Hard constraint, not optional**: `DEVELOPMENT.md` already notes
  Fit3D is **academic-license-only — validation is fine, training a
  shipped model is not**. This track is diagnostic only. If it surfaces
  a real, fixable domain-shift problem, the fix has to be executed via
  RepCount (already licensed for this) or real gym footage once
  available — never by fine-tuning on Fit3D frames directly.

  **2026-08-10 update — the initial 0% numbers were mostly measuring the
  wrong thing, not the classifier.** See `ROADMAP.md` Phase C3's dated
  addendum for the full writeup and `AIFit`/Fieraru et al. CVPR'21 (the
  Fit3D paper) reading that prompted a closer look at what was actually
  being compared. Two root causes, both fixed, no Fit3D data used for
  training either fix:
  1. The exercise→class mapping table above conflated different real
     exercises under a shared English word (RepCount's `press` class is
     bench press, lying/chest-driven; Fit3D's mapped `press` exercises are
     standing overhead presses, shoulder-driven — a different movement the
     classifier was never trained on). Corrected in
     `tools/analyze_fit3d_domain_shift.py`; `press`, `raise`, and `situp`
     are now out-of-scope negative controls, not scored classes.
  2. A separate, real bug in `src/camera.py`/`src/fusion.py`: the classifier
     re-runs every `CLASSIFY_INTERVAL_SECONDS` on a trailing
     `CLASSIFY_WINDOW_SECONDS` window, and the *last* call before a track
     ends was simply overwriting the class — a single noisy snapshot, not
     an aggregate. Fixed with a confidence-weighted vote across every call
     (`_record_classification`).
  On the classes that were actually the same movement as training (squat,
  pushup), accuracy went from the original 25%/62% to **100%/88%**. Fix 2
  also validated as a net improvement on RepCount itself (the classifier's
  own licensed domain) — see `ROADMAP.md` Phase C3 for the full breakdown.

## Track C — Camera-rig geometry as a second real data point

**Question**: `CAMERA_PLACEMENT.md`'s spacing/count guidance (3+
cameras, 60–90° apart) was derived from CMU Panoptic's dome rig
geometry and this project's own reasoning. Fit3D is a second, real,
independently-built 4-camera studio rig — does its actual geometry
(already sitting in every `camera_parameters/*.json` file) agree,
disagree, or add nuance?

- Extract the real inter-camera angles and distances from Fit3D's
  calibration data (already have the R/T extraction code from
  `tools/validate_fit3d.py`'s `build_rig()` — this is a small, cheap
  analysis script, not new infrastructure).
- Compare against the 60–90° recommendation and the "3+ over exactly 2"
  guidance. If Fit3D's rig sits outside that range and still produced
  good triangulation results in Track A, that's worth knowing and
  folding back into `CAMERA_PLACEMENT.md` as a second real data point,
  not just Panoptic's.

## Tooling work needed to actually run Track A/B at this scale

`tools/validate_fit3d.py` already does the right thing for one
subject/exercise list at a time; scaling to 8×28 (or 8×47) needs:

1. **A batch driver**, not manual CLI invocations per subject — loop over
   `(subject, exercise)` pairs, calling the existing scoring logic
   (`score_exercise()` is already a clean per-clip function, this is
   mostly a wrapper).
2. **Resumability.** A ~17-27 hour run risks interruption (sleep, reboot,
   anything). `--skip-run` already skips a clip if its output JSON
   exists — the batch driver just needs to check that *before* deciding
   to launch a clip at all, so a restarted run picks up where it left
   off instead of re-doing finished work.
3. **Per-clip failure isolation.** One bad clip (no detection, corrupt
   video, whatever) shouldn't kill an overnight run — catch, log, and
   move on, then report which clips failed at the end rather than
   silently losing that subject/exercise's data from the aggregate.
4. **Modest parallelism.** Each clip's pipeline run is CPU-bound but
   doesn't saturate a modern multi-core machine on its own (4 camera
   threads). Running 2–3 clips concurrently instead of strictly serially
   would cut the ~17-hour estimate meaningfully without much risk of
   resource contention — worth testing with a small batch before
   committing to a concurrency level for the full run.
5. **A combined report format** that keeps per-subject and per-exercise
   breakdowns *and* the pooled total — matching the existing
   `report.json` shape but with a `subject` dimension added, not a
   flat re-run of today's single-subject structure.
6. **Disk/repo hygiene**, same as today: only the final aggregate
   `report.json` (or one per subject) gets committed; per-clip
   `rig.npz`/pipeline JSONs/`merged.json` stay disk-only
   (`validation_results_fit3d/` is already gitignored).

## Explicitly out of scope for now (backlog, not rejected)

- **Rendering synthetic training data from the `smplx`/`gpp` folders.**
  Fit3D ships full SMPLX body-model parameters per frame, which could in
  principle drive synthetic rendering (different camera angles, lighting,
  etc.) beyond what the real footage covers. This would need the actual
  SMPLX body model files (separately licensed, not bundled) and a
  rendering pipeline this project doesn't have yet — a real project in
  its own right, not a next step. Worth remembering it exists if a much
  larger classifier-training effort is ever justified, but not before
  the license question (SMPLX's own terms, on top of Fit3D's) is
  checked.
- **Running the 19 warmup clips.** Lower value than the 28 named
  exercises (generic movement, not part of this project's taxonomy) —
  worth doing only if the named-exercise run leaves spare
  time/curiosity, not as a priority.
- **The 3-subject test split.** No ground truth, genuinely unusable for
  this project's purposes (validation, not leaderboard submission) —
  not revisited unless the goal changes.

## Plan for tomorrow

A concrete, ordered starting point — not everything above, a first slice:

1. Build the batch driver + resumability + failure isolation (tooling
   items 1–3 above) — this is required infrastructure before any large
   run, and is a well-scoped, boundable piece of work on its own.
2. Test it on a small batch (e.g. 2 subjects × 5 exercises) to confirm
   resumability actually works (kill it mid-run, restart, confirm it
   picks up correctly) and to get a real parallelism-vs-runtime data
   point (tooling item 4) before committing to a concurrency level for
   the full run.
3. Kick off the full Track A run: 28 named exercises × 8 subjects, with
   whatever parallelism step 2 justified. This is the long-running part —
   start it early in the session so it's progressing in the background
   while other work continues.
4. While Track A runs: write the Track C camera-geometry analysis script
   (small, cheap, doesn't depend on Track A finishing) and get that
   result independently.
5. Once Track A's runs land: build Track B's confusion matrix from the
   classifier output Track A already recorded (no new pipeline runs
   needed for this part) and write up what it shows.
6. Document results the same way today's session did — update
   `ROADMAP.md` Phase C3 (or a new entry if this outgrows Phase C),
   commit the aggregate report(s), and produce a team update if the
   results are big enough (any of these three tracks could turn up
   something as significant as today's threshold-transfer/scoring-bug
   findings — worth the same rigor of write-up, not a rushed footnote).

## What I did to produce this plan

Checked that all 8 train subjects have identical structure (47 clips
each — confirmed, not assumed). Split each subject's 47 clips into 28
named exercises vs. 19 numbered warmups and built the exercise → this
project's class-taxonomy mapping table above by reading Fit3D's own
exercise names against `src/exercise_classifier.py`'s `CLASSES`/
`CLASS_FAMILY`. Computed real frame-count totals across all subjects
(284,863 named-exercise frames, 159,960 warmup frames) and turned that
into wall-clock estimates using today's actually-measured throughput
(~0.22s/frame), rather than guessing. No pipeline runs were executed for
this plan — it's frame-counting and file-structure inspection only, nothing
that touched the fused pipeline itself.
