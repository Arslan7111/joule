# Joule — First Real Shoot: Capture Protocol

Written 2026-08-05, per `ROADMAP.md` Phase C2. A short checklist for
whoever holds the camera on the first real footage session. Read
`CAMERA_PLACEMENT.md` first — that's where the cameras go; this is what to
film once they're there. Every item below exists to stress-test something
specific this project has already found or built, not generic filming
advice — the reason is next to each one so it's obvious if it gets
skipped.

## Per-exercise coverage

- [ ] **One side view + one 45° view, minimum, per exercise.** Confirmed
  finding: bench/overhead press rep *counting* is weak head-on (elbow
  signal too foreshortened) even though classification works fine —
  `CAMERA_PLACEMENT.md` rule 2. A 45° angle does not fix this; it needs a
  genuine side-on view.
- [ ] **Feet visible in every frame, on every camera, for every exercise.**
  Hard rule, not a preference — `CAMERA_PLACEMENT.md` rule 1. Check this
  live on the monitor/phone screen before moving to the next exercise, not
  after the fact.
- [ ] **Include at least one squat set and one floor-level exercise
  (push-up or similar).** Not just "cover the basics" — Fit3D's mocap
  validation (`ROADMAP.md` Phase C3, 2026-08-05) found these are
  genuinely the harder cases for this pipeline (10.7–13.3° mean 3D-angle
  error vs. 5–7° for standing exercises like curls/presses/raises), on a
  clean studio rig with no equipment clutter or crowded gym floor. A real
  gym's squat rack and push-up floor space are exactly where that error
  is most likely to be *worse*, not better — this needs real data, not an
  assumption either way.

## Stress-test clips (one of each, deliberately)

- [ ] **Two people crossing/occluding paths.** Re-ID stress test for A1's
  buffered identity lock and A2's match-margin logic
  (`ROADMAP.md` Phase A). The existing validation for both used a
  public-domain test clip and a synthetic engineered case, respectively —
  neither is this project's own camera, own lighting, own gym clothing.
- [ ] **A mirror somewhere in frame.** A5's entire finding
  (`ROADMAP.md` Phase A) is a written, code-grounded analysis with **no
  real mirror clip ever run through the pipeline** — this is the one
  piece of Phase A that's still purely theoretical. Deliberately include
  what the placement doc says to avoid, once, so the two predicted
  failure paths (contaminated shared state vs. phantom double-counted
  person) can actually be observed instead of just reasoned about.
- [ ] **One slow, heavy set** (5+ seconds per rep — a heavy barbell lift,
  not a fast bodyweight movement). A4's tempo validation
  (`ROADMAP.md` Phase A) used a synthetic idealized angle waveform driven
  directly into `StateMachine`, explicitly *not* real pose-estimation
  noise. This is the real-noise version of that test.
- [ ] **One deliberate occlusion**: step fully behind a machine/pillar
  mid-set for a few seconds, then continue. A4 validated this
  synthetically too (1.0s / 4.5s / 6.0s blackouts, all recovering
  cleanly with no phantom reps) — same gap, real tracking loss and
  re-detection instead of a synthetic `angle=None` injection.
- [ ] **One walking/treadmill clip.** Regression check, not a new
  test — the locomotion filter was already validated pre-Phase-A
  (23 phantom squat reps → ~1, `README.md`/`DEVELOPMENT.md`). Cheap to
  confirm it still holds after this session's Re-ID/fusion hardening,
  since none of that touched `src/state_machine.py`'s locomotion logic
  directly but everything upstream of it changed.

## First real 3D fusion run

- [ ] **Two-phone (or more) clap-synced squat set**, checkerboard
  calibration pass first via `tools/calibrate.py`. Every 3D validation
  run so far — CMU Panoptic, Fit3D — has been someone else's footage on
  someone else's camera rig. This is the first time this project's own
  cameras, own calibration, own sync method get tested end to end.
  Follow `CAMERA_PLACEMENT.md` rules 4 and 7 (3+ cameras if the phone
  count allows it, 60–90° spacing, don't touch the cameras once
  calibrated).

## While filming

- [ ] Label each clip with the exercise name as it's shot (matches this
  project's existing `training_data/<class>/` convention) — makes it
  directly usable as classifier training/eval data later
  (`ROADMAP.md` Phase D4), not just a validation clip to watch once.
- [ ] Keep clips separate per exercise/stress-test rather than one long
  continuous recording — every existing benchmark/validation tool in this
  project (`tools/benchmark_repcount.py`, `tools/validate_panoptic.py`,
  `tools/validate_fit3d.py`) expects one file per exercise, and re-cutting
  a long recording afterward is pure avoidable friction.

## Exit criteria

Every checkbox above ticked once is enough for the first session —
`ROADMAP.md` Phase D (D1–D2) is where this footage actually gets scored
against these predictions, not here.
