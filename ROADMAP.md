# Joule — Roadmap (Revamped)

Written 2026-08-03, after an independent evaluation of the project against
its own docs and code (see "Evaluation findings" below). This supersedes
the flat "what's left" list in `STATUS.md` with a phased plan. `STATUS.md`
stays as the always-current done/left-to-do snapshot; this file is the
sequenced execution plan behind it. Technical detail and history remain in
`DEVELOPMENT.md`.

## Why this revamp

The 9 build phases are real and the component-level benchmarks (RepCount,
CMU Panoptic) are credible. But an independent review found the claim of
"validated" holds at the component level, not the system level: the two
pieces sitting directly under the core product promise — **per-person
identity (Re-ID)** and **cross-view association (fusion)** — are the least
tested parts of the pipeline, and neither benchmark stresses them (RepCount
is single-subject footage; the benchmark script itself only scores the
largest track; Panoptic is a clean, occlusion-free dome with no equipment
or mirrors). Sending real gym footage straight at the current system risks
burning the highest-value validation opportunity on failures that were
foreseeable and fixable in advance.

This plan reorders the work so the foreseeable failure modes are hardened
**before** real footage is spent, and puts everything that has no
dependency on footage into a parallel prep track so nothing sits idle
waiting on filming logistics.

## Phase A — Harden before footage (no footage required)

Highest priority. Cheap, testable now against existing Panoptic/stock/RepCount
assets, and directly protects the value of the first real capture session.

- **A1. Re-ID identity locking.** ✅ Implemented and validated (2026-08-03).
  `src/session.py` / `src/reid.py` used to bind a person's identity from a
  single embedding at track birth and never revisit it — one bad occluded
  crop misattributed an entire set. Fixed via `ProvisionalIdentity`
  (`src/reid.py`): buffers `REID_LOCK_MIN_SAMPLES` (3) embedding samples or
  `REID_LOCK_WINDOW_SECONDS` (3.0s), whichever comes first, averages and
  re-normalises them, and matches the gallery once on that average — applied
  identically in `src/camera.py` (`resolve_person`) and `src/fusion.py`
  (both previously called `gallery.identify()` on the very first sample).
  Validated two ways: (1) targeted unit tests against the real
  `ProvisionalIdentity`/`SessionGallery` classes showing a bad first crop
  alone causes a spurious new-person enrollment under the old single-sample
  behaviour, while the buffered average correctly matches the true person;
  (2) a real end-to-end pipeline run (Windows env set up this session:
  Python 3.11 venv, full dependency stack, MediaPipe pose model fetched) on
  a public-domain person-detection test clip — ByteTrack fragmented the
  subject into 4 tracks, all 4 correctly consolidated into one `person_1`
  via the new buffered-match path (one re-match logged at `sim 0.79`).
  **Real-data validation (2026-08-03, same day, second session)**: real CMU
  Panoptic 5-camera footage (`test_videos/panoptic/`, pushed and verified —
  see below) was run through a git worktree at the pre-A1 commit (`35af8b7`)
  for a true before/after. The **baseline (pre-A1) code actually
  fragmented this real capture's single subject into 2 person identities** —
  camera 8's view scored only 0.73 cosine similarity on its single first
  embedding sample, just under the 0.75 match threshold, so it silently
  enrolled as a phantom `person_2`, invisibly reducing "5-view fusion" to 4
  views. This was a real, previously-undetected bug in this project's own
  reference validation clip, not a hypothetical. **Current (post-A1) code
  correctly resolves all 5 views to one `person_1`** (sims 0.87–1.00) —
  direct, on-camera-data confirmation the fix works, not just synthetic
  validation.
  **New finding from this same real run**: `REID_LOCK_WINDOW_SECONDS` (3.0s)
  consumes most of this specific clip's very short duration (101 frames /
  ~3.4s) before any identity resolves at all (identity locks in around
  frame 60), leaving only 41/101 frames with any person-level output at all
  — vs. the old code's immediate 101/101. Not a product bug (real sets last
  far longer than 3s) but it does mean this particular 101-frame clip can no
  longer cleanly isolate A1/A2's *accuracy* impact on its own; noted for
  whoever next re-runs this validation.
- **A2. Re-ID match confidence.** ✅ Implemented and validated (2026-08-03).
  `src/session.py`'s `identify()` used to accept any match clearing the flat
  0.75 threshold, even when a second candidate was nearly as close (more
  likely as the gallery grows — many members in similar gym clothing).
  Added `REID_MATCH_MARGIN` (0.05): a match must beat the runner-up by this
  much or the track enrolls as a new anonymous person instead of guessing.
  Also added `REID_STALE_SECONDS` (30 min): people not updated within that
  window are excluded from match candidacy (but kept in the gallery for
  check-in/dashboard) so an old embedding from early in the session can't
  keep competing with people seen recently. Validated with unit tests
  against the real `SessionGallery` class: an engineered ambiguous
  best-vs-second-best case (both candidates individually clear the raw
  threshold, margin ≈ 0) correctly enrolls a new person instead of
  guessing; a clearly-closer case still matches correctly; a 31-minute-old
  person is correctly excluded from candidacy yet remains listed in
  `gallery.people()`. Regression-checked against the same real test clip
  used for A1 — identical correct result (4 fragmented tracks → 1 person).
- **A3. Epipolar check in fusion.** ✅ Implemented and unit-validated
  (2026-08-03), ⚠️ not yet run on real multi-camera footage.
  `src/fusion.py` associated cross-view identity purely by appearance
  embedding via the Re-ID gallery — no geometric check at all, despite
  calibration already being loaded, so two similarly-dressed people at
  adjacent stations could merge into one confident-looking but bogus 3D
  skeleton. Added `cross_view_consistent()` in `src/triangulation.py`:
  before accepting a person's multi-view triangulation, it independently
  re-checks reprojection error per jointly-visible joint at a tight 6px
  tolerance (`CONSISTENCY_MAX_REPROJ_PX`); if too few joints clear it, the
  frame falls back to single-view 2D for that person rather than emitting a
  bogus 3D skeleton, with a warning logged. Wired into `src/fusion.py`'s
  per-person triangulation block.
  **Notable finding while building this**: `triangulate_skeleton`'s own
  existing lenient tolerance (25px, tuned for real pose-estimation noise)
  is measurably too loose to catch this — a synthetic two-different-people
  case still passed 11/17 joints at 25px, because with exactly 2 cameras
  the epipolar constraint is only 1 degree of freedom per point (a wrong
  match just has to land near the epipolar line, not at an exact point).
  The tight independent 6px check correctly separates the same case
  (0/17 by 4px) while a genuine match with ~1.5px synthetic jitter still
  passes cleanly (17/17). Validated with 4 unit tests: genuine single
  person (pass), fabricated cross-view mismatch (correctly rejected),
  heavy occlusion / too few jointly-visible joints (benefit of the doubt,
  pass), and realistic keypoint jitter (still passes).
  **Real-data validation (2026-08-03, same day, second session), redesigned
  from a flat 6px to a view-count-scaled threshold.** The flat 6px was
  confirmed too tight on real data — running the real 5-camera Panoptic
  sequence, **100% of frames with resolved identity (41/41) failed the 6px
  check** and fell back to 2D, degrading the aggregate accuracy figure from
  3.7° to 6.3° mean (an artifact of scoring degraded single-view 2D angles
  against 3D-quality mocap ground truth, not a real triangulation
  regression). Root cause, precisely diagnosed: the naive all-views DLT this
  check deliberately uses (no outlier-view dropping) has reprojection error
  that *inherently grows with camera count* even for a genuine match (one
  view's few pixels of ordinary noise drags the shared least-squares fit) —
  measured real per-joint max-error p95 by view count: 2v=6.7px, 3v=15.4px,
  4v=45.0px, 5v=78.3px.
  **Considered and rejected: outlier-view dropping** (mirroring
  `triangulate_skeleton`'s own best-pair retry) as the fix instead of a
  wider number — tested against a synthetic single-wrong-of-5-views
  mismatch and it **passed cleanly in 100% of cases**: dropping the one bad
  view leaves the other 4 looking perfectly consistent, silently defeating
  the exact failure mode this check exists to catch. Not used.
  **Fix shipped**: `CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS` in
  `src/triangulation.py` — a per-view-count lookup (2v: 9px, 3v: 20px, 4v:
  30px, 5v: 90px) derived from the real noise data above plus a synthetic
  mismatch-error sweep (adversarial worst-case *and* randomized-direction
  trials, using the real 5-camera rig geometry, at realistic 40cm–2m
  person-separation scale) to find, per view count, where real noise ends
  and a real mismatch begins. Re-running the real Panoptic sequence with
  this fix: **0/41 frames (down from 41/41) now fall back to 2D**; mean
  error for those frames improved 6.3°→5.2° (remaining gap to the original
  3.7° baseline is expected — it's now a different, smaller 41-frame subset
  per A1's finding above, not a fusion defect). Re-verified the existing
  synthetic A3 unit tests (genuine match, fabricated 2-camera mismatch,
  occlusion, jitter) all still pass unchanged.
  **Two known, accepted residual limits, both real and neither fully
  closable by any threshold**: (1) **2 cameras** — inherent 1-DOF epipolar
  ambiguity (already flagged when 6px was first chosen): a synthetic
  axis-aligned mismatch can measure as low as 0.6px, indistinguishable from
  noise. Not new, not worsened. (2) **4 cameras specifically** — a
  narrow, unlucky camera/direction alignment can produce a mismatch
  measuring *below* real noise's own p95 at that view count (33.5px
  adversarial floor vs. 45.0px noise p95) — no single number is both safe
  against real noise and airtight against that alignment. Chose to favor
  catching the mismatch (30px, at the adversarial floor rather than above
  it) over maximizing pass-rate, matching this project's stated
  conservative-matching philosophy (`src/session.py`: "mis-attribution is
  the worst failure mode"). Realistic (non-adversarial) 4-camera mismatches
  still measure ~108px+ at the 5th percentile in random-direction trials —
  this is a narrow, deliberately-accepted edge case, not a general weakness
  at 4 cameras.

  **The CMU Panoptic dataset itself, pushed and verified this session**:
  `test_videos/panoptic/` (5-cam, 101-frame, the original tuned sequence)
  and `test_videos/panoptic_pose2/` (3-cam, 2036-frame held-out sequence,
  precomputed validation artifacts only — raw footage/GT intentionally
  omitted to keep the push small, so it can't be independently re-run, only
  inspected) arrived via a separate commit. Verified genuine before
  trusting it: calibration.json's camera-panel structure (31 HD cams on
  panel 0, VGA on panels 1–20, Kinects on panel 50) matches real Panoptic
  calibration exactly; ground-truth `body3DScene_*.json` files have the
  correct `joints19`/`univTime`/`hd_29_97` schema; the videos are real
  playable 1920×1080 footage at 29.97fps with non-blank pixel content and
  the exact documented frame count; and `panoptic_pose2/validation.log`
  reproduces the already-published Phase 8 figures (6.1° mean, 4.0° median,
  right-elbow 39% coverage) exactly, joint-by-joint. Also fixed a small,
  unrelated pre-existing bug found while using it: `tools/validate_panoptic.py`
  wasn't zero-padding camera IDs in video filenames (`cam_0.mp4` instead of
  `cam_00.mp4`), breaking any camera ID under 10.
- **A4. Depth/tempo stress tests.** ✅ Written finding (2026-08-03), no code
  change needed. No rep-bearing footage exists on this machine to retime
  (the only local clip, `person_test.mp4`, is a walking/bicycle test asset
  with no exercise reps), so instead of retiming video this drove the real
  `src/state_machine.py` `StateMachine` directly with synthetic squat-shaped
  angle signals — a more direct test of the exact component in question
  (`ADAPTIVE_WINDOW_SECONDS`=3.0 vs. tempo, and `angle=None` handling) than
  a real clip would give without pose-estimation noise as a confound.
  **(a) Tempo**: ran 8-rep sets at 1.5s/rep (fast bodyweight), 3.0s/rep
  (matches window), 5.0s/rep (barbell), and 8.0s/rep (very slow heavy) —
  all four counted every rep correctly with the right depth/validity, even
  at 8s/rep where the window sees under half of one cycle at any instant.
  Reason: the adaptive window uses 10th/90th-percentile range over its
  trailing samples, and a cosine-shaped rep signal spends most of its time
  (lowest velocity) near the top/bottom extremes regardless of period, so
  the trailing window keeps recapturing values close to the true range even
  when it can't see a whole cycle. **(b) Occlusion**: fed `angle=None` for
  1.0s (mid-rep, sub-window), 6.0s (~2 rep-periods, exceeds the window), and
  4.5s (near-one-period at 5s/rep tempo). In every case: zero false/extra
  reps, exactly the rep(s) physically inside the blackout went uncounted
  (graceful undercount, not corruption), and counting resumed immediately
  once fresh variance reappeared after the gap — no extra "re-warm-up" dead
  time beyond the occlusion itself, and the first rep after resuming had
  normal, uncorrupted depth/validity values. **Caveat**: this used an
  idealised smooth waveform, not real noisy pose output — real keypoint
  jitter is a separate, already-mitigated concern (`SMOOTHING_WINDOW`
  median filter, validated in earlier phases), not something this test
  re-checks. Script kept in this session's scratchpad only (not committed —
  no `tests/` convention exists in this repo; matches how A1–A3 validation
  scripts were handled).
- **A5. Mirror-detection sanity check.** ✅ Written finding (2026-08-03), no
  code change now. No mirror-containing clip exists on this machine, so
  this is a code-grounded analysis rather than an observed run — confirmed
  by reading `src/detector.py` (plain 2D YOLO person detector, no depth or
  geometric cue of any kind) and `src/reid.py`/`src/session.py` (identity
  match is pure cosine similarity on appearance) that **nothing anywhere in
  the pipeline can distinguish a mirror reflection from a real person** — a
  reflection that clears `DETECTOR_CONF` is just another tracked person.
  Two distinct failure paths depending on what Re-ID then does with it
  (`src/camera.py`'s `resolve_person`, `src/session.py`'s `identify`):
  (1) **Re-ID matches the reflection to the real person** (likely if the
  reflection is a clean, similarly-lit, same-clothing view) — both the real
  track and the reflection track resolve to the same `person_id`, and
  `camera.py`'s per-frame loop calls that one shared `StateMachine.update()`
  from *both* tracks in the same iteration. The state machine has no
  concept of "these two calls are the same instant from two sources" — it
  treats them as sequential samples, so a reflection's angle reading (often
  a different apparent angle: oblique glass, partial crop, mirrored limb
  layout) gets interleaved into the same median-filter buffer and adaptive
  history as the real body's reading. Not proven to cause a wrong rep count
  outright — one interleaved outlier per frame is unlikely to survive
  `HYSTERESIS_FRAMES`=2 — but it is a real, code-confirmed contamination
  path into person-level state that would need a live mirror clip to size
  properly. (2) **Re-ID does not match** (plausible — mirror crops tend to
  be dimmer, cropped by the frame edge, and shot at an oblique angle, all
  of which lower cosine similarity below `REID_MATCH_THRESHOLD`+margin) —
  the reflection enrolls as a brand-new phantom person who then appears to
  perform the identical exercise in perfect real-time sync with the real
  person for as long as the mirror is in frame: inflated headcount in the
  gallery/dashboard and every real rep double-counted in aggregate reporting
  under a second identity. This is the more consequential and, given how
  Re-ID matching is deliberately conservative (A2), probably the more
  likely of the two paths in practice.
  **Recommendation: placement rule, not a code fix.** Reliably telling a
  reflection from a real person needs depth or a per-camera calibrated
  exclusion zone — neither is justified before a real installation exists to
  calibrate against, and the "no mirrors in frame" rule is already planned
  independently in Phase C1's camera-placement doc. The one cheap follow-up
  worth keeping on the backlog once real camera installs exist: a static
  per-camera polygon dead-zone mask (drop detections whose bbox centroid
  falls inside a manually marked mirror region) as a machine-enforced
  backstop for whenever the placement rule isn't followed perfectly — not
  worth building blind now with no installation to calibrate the mask
  against.

Exit criteria: A1–A3 shipped with a before/after test on Panoptic showing
the fix actually changes behaviour (not just a code diff); A4–A5 produce a
short written finding even if the answer is "acceptable as-is." **Phase A
is now fully closed, including the real-footage before/after** (2026-08-03,
second session same day): real CMU Panoptic footage was obtained, verified
genuine, and used to run an actual pre-A1-vs-current comparison — which
caught and fixed a real bug in A1's target scenario (the exact fragmentation
A1 was built to prevent, confirmed happening in this project's own reference
clip) and a real design flaw in A3's threshold (confirmed too tight on real
noise, redesigned to a view-count-scaled lookup, re-verified against both
the real footage and the original synthetic mismatch tests). Two narrow,
accepted residual limits remain (2-camera epipolar ambiguity, a specific
4-camera adversarial alignment) — both documented above, neither closable
by any threshold, and both consciously resolved in favor of catching
mismatches over maximizing pass-rate.

## Phase B — Reproducibility & doc hygiene (no footage required, parallel with A)

Low effort, currently makes every headline number in the docs unverifiable
from a fresh clone.

- **B1.** ✅ Done, both halves (2026-08-03/04).
  **Panoptic half**: the real CMU Panoptic dataset arrived and was used for
  Phase A's real validation anyway (see A1/A3 above), producing a genuine,
  current `validation_results/val.json` + `merged.json` (5-camera sequence,
  current post-A1–A3-hardened code) — force-committed despite the blanket
  `test_videos/` gitignore (small JSON/rig files only, no video/dataset
  content).
  **RepCount half**: downloaded the full 152-video RepCount Part-A test
  split fresh from the public `momo321654/RepCountA-videos` HF mirror (no
  access blocker, unlike Panoptic/Fit3D/M3GYM) and ran
  `tools/benchmark_repcount.py` end to end. Result: **ALL n=152, MAE 0.742,
  OBO 22.4%**; gym-core classes — squat 44.4%, front_raise 33.3%, pull_up
  36.8%, push_up 31.2% OBO. Confirmed the trained classifier
  (`models/exercise_clf.npz`) was actually active throughout, not a silent
  heuristic fallback — every `classified=` value across all 152 videos was
  one of the model's 7 trained output classes, never a heuristic-only class
  (lunge/hinge/curl/row never appeared).
  **These numbers legitimately differ from the historical Phase 8/9 figures
  in `DEVELOPMENT.md`** (which predate this session's A1–A3 hardening) —
  not a regression or a bug. A1's buffered Re-ID identity lock changes
  exactly which frames/timespans get attributed to a track over a video's
  timeline, which shifts the classifier's feature windows and rep counts
  slightly from the pre-hardening baseline those historical numbers were
  computed on. This fresh run is now the current, authoritative figure for
  the present codebase; `report.json` (19KB, force-committed) is the
  auditable artifact — the 1.4GB of downloaded source video and the 51MB of
  per-video pipeline JSONs are disk-only, not committed, and are safe to
  delete (freely re-downloadable from the public mirror if ever needed
  again).
- **B2.** Fix `README.md`: model weight files (`yolov8n.pt`,
  `yolov8n-pose.pt`, `pose_landmarker_*.task`) are claimed "already present
  in the project root" but are not in a fresh clone — add a download step.
  Reconcile the `lite` vs `full` pose-model naming inconsistency
  (`README.md` vs `src/pose.py`).
- **B3.** Update `README.md`'s Layout section — missing `reid.py`,
  `session.py`, `risk.py`, `smoothing.py`, `triangulation.py`, `fusion.py`,
  `signature.py`, and most of `tools/`.
- **B4.** Reorder `DEVELOPMENT.md` so Phases 7–9 sit above the "Validation
  results" table and "Deployment guidance" (currently below, reads as
  stale); add RepCount rows to that table; update the Roadmap section at
  the bottom (item 3, "trained classifier," is already done).
- **B5.** Reconcile the "~6°" (STATUS.md) vs "3.7°" (README.md) Panoptic
  error figures — both are correct (held-out vs. tuned sequence) but need a
  one-line clarification wherever they appear standalone.

Exit criteria: a fresh `git clone` + setup instructions in README actually
works end to end; no contradicting numbers appear without context.

## Phase C — Footage prep track (no footage required, parallel with A/B)

Everything that can be decided or built before a camera is ever pointed at
a real gym.

- **C1.** ✅ Done (2026-08-05). Written as `CAMERA_PLACEMENT.md` — every
  rule traced to a specific validated finding in this codebase rather than
  generic camera advice: feet-in-frame-on-every-camera (rule 1), bench/press
  side-view requirement from the confirmed head-on-counting-is-weak finding
  (rule 2), hard mirror-avoidance rule tied to A5's blind-spot analysis
  (rule 3), 3+ cameras preferred over exactly 2 for fused stations (ties to
  A3's accepted 2-camera epipolar-ambiguity residual limit) with 60–90°
  spacing and ~2m elevation (rule 4), ~3–4 machines per 2D camera (rule 5),
  physical separation between adjacent stations sized off A3's 40cm–2m
  person-separation test scale to reduce Re-ID mismatch risk (rule 6),
  calibration-rigidity warning for `tools/calibrate.py` rigs (rule 7), and a
  flagged-not-hard lighting-consistency note tied to A5's dimmer-mirror
  observation (rule 8).
- **C2.** ✅ Done (2026-08-05). Written as `CAPTURE_PROTOCOL.md` — a
  checklist, each item tied to a specific existing finding rather than
  generic filming advice: side+45° view per exercise and feet-in-frame
  (ties to `CAMERA_PLACEMENT.md`), a deliberate squat + floor-exercise
  capture (Fit3D's C3 finding that these are the harder poses, now to be
  checked on a real gym floor instead of a clean studio rig), two-person
  crossing and a real mirror clip (A1/A2 and A5's stress tests — A5 in
  particular has never been run against real footage, only reasoned
  about), a slow heavy set and a deliberate occlusion (A4's synthetic
  tempo/occlusion tests, now with real pose noise instead of an idealized
  waveform), a treadmill regression check (the pre-Phase-A locomotion
  filter validation), and the first real clap-synced multi-camera
  calibration + fusion run on this project's own hardware.
- **C3. Submit Fit3D and M3GYM registration forms now.** ✅ Fit3D half done
  (2026-08-05) — not via the registration-form path this bullet originally
  described, but the real dataset (8 train subjects × 47 exercises × 4
  calibrated cameras, SMPLX-derived mocap-grade 3D ground truth) was
  already present locally, provided directly rather than through
  `fit3d.imar.ro`. Gitignored (`Fit3D/`, ~44GB, matches the `test_videos/`
  pattern) so it can't land in a commit. M3GYM (Google Form, academic
  email/affiliation/purpose required) is still outstanding — user is
  submitting it independently.

  **Built `tools/validate_fit3d.py`** to actually use the Fit3D data for
  what it's uniquely good for: real gym exercises (squat, deadlift, curls,
  rows, presses) with mocap-grade 3D ground truth, unlike CMU Panoptic's
  generic dome poses. Two things about Fit3D's raw format aren't documented
  inline and had to be reverse-engineered from the real data before
  trusting any number out of the tool, both verified empirically rather
  than assumed:
  1. **Extrinsics convention.** `camera_parameters/<cam>/<exercise>.json`'s
     `extrinsics.T` is the camera *center* in world coordinates, not the
     standard `t` in `P = K[R|t]`. Projecting GT joints with the standard
     `X_cam = R@X + t` formula landed every joint ~3000px off-frame;
     `X_cam = R @ (X_world - T)` put them exactly on the real body in the
     real video frame. `build_rig()` converts once (`t = -R @ T`) so
     `src/triangulation.py` needed no changes.
  2. **`joints3d_25` order and left/right.** Recovered by (a) bone-length
     invariance — pairwise distances between anatomically connected joints
     have ~0 coefficient-of-variation across thousands of real frames
     spanning six exercises, which cleanly recovers the skeleton topology
     (25 = 1 pelvis + 2×(hip, knee, ankle, foot, toe) + 4 spine/neck/head +
     2×(shoulder, elbow, wrist, 2 hand points)) — then (b) projecting the
     two symmetric chains onto a real frame where the subject's back is to
     the camera (so image-left = anatomical left, no mirroring possible)
     to fix which chain is left vs. right.

  **Ran a real validation sweep**: subject s03, 7 exercises (squat,
  deadlift, barbell_row, dumbbell_overhead_shoulder_press, pushup,
  side_lateral_raise, dumbbell_biceps_curls), all 4 cameras fused, ~6,800
  frames of real footage. **Standing/unencumbered upper-body exercises
  validate cleanly and land in the same range as the Panoptic figures**
  (curls 4.9° mean/2.8° median, press 6.9°/5.2°, lateral raise 6.5°/5.3° —
  all ~100% per-joint coverage). **Squat and pushup show real, larger
  error** (10.7° and 13.3° mean respectively, p95 up to 52° on pushup) —
  a believable, expected result (harder poses, more self-occlusion), not a
  broken pipeline. Combined across all 7: mean 9.1°, median 6.4°, p95
  26.2° over 30,270 joint-frame samples.

  **A validation-tool bug was found and fixed along the way, not a
  pipeline bug** — worth recording since it nearly got reported as a real
  finding. The first pass showed squat/pushup "coverage" collapsing to
  ~50%, with a suspicious pattern: `left_shoulder`+`left_elbow` present
  exactly when every other joint was absent, and vice versa. Investigated
  properly rather than accepting the number at face value: (1) checked
  whether `src/triangulation.py`'s A3 cross-view-consistency threshold was
  false-positiving on Fit3D's different camera rig, tuned as it was on
  Panoptic noise — ruled out, only 2% of squat frames trigger it; (2)
  replayed the real detector+pose+triangulate_skeleton path frame-by-frame
  on the actual video at the affected timestamps — ruled out, per-joint
  3D confidence stayed continuously healthy throughout, no collapse; (3)
  checked for Re-ID track-id restarts forcing A1's buffered-lock
  re-acquisition window — ruled out, exactly one resolution event per
  camera view for the whole clip, no restarts logged. The actual cause:
  `src/output.py`'s `_downsample_series` (30fps output from Fit3D's native
  50fps, `OUTPUT_FPS` in `src/config.py`) runs an independent sampling
  clock **per joint**, keyed off that joint's own emitted timestamps. A
  single ordinary transient 1-frame confidence dip in one joint (real,
  expected, harmless on its own) permanently shifts that joint's output
  timestamps out of frame-grid alignment with every other joint's — a real
  effect, confirmed directly: `left_hip`'s and `left_elbow`'s output
  timestamps started perfectly aligned, then diverged by exactly one
  native frame after one such gap. The validation script joined all
  joints through one shared per-frame bucket before scoring, which turned
  that harmless per-joint phase drift into a manufactured "joints
  alternate presence" artifact. Fixed by scoring each joint independently
  against its own nearest GT frame instead of through a shared bucket;
  rescoring from the *same* already-computed pipeline output changed
  coverage from 50–56% to 92–100% for squat/pushup while leaving every
  error number (mean/median/p95/n) unchanged, confirming the error figures
  above were trustworthy the whole time — only the coverage metric had
  been wrong.

  **Full-scale batch validation (2026-08-06/07), all 8 subjects × 28 named
  exercises — Tracks A/B/C from `FIT3D_UTILIZATION_PLAN.md`.** ✅ Done. The
  1-subject/7-exercise pass above proved the tool was correct; this run
  scales it to the full licensed dataset to turn that correctness check
  into a statistically solid result and answer two further questions the
  first pass couldn't. Built `tools/validate_fit3d_batch.py` (resumable
  batch driver — skips clips whose output already exists, isolates
  per-clip failures so one bad clip can't lose an overnight run, modest
  parallelism across subjects), `tools/analyze_fit3d_domain_shift.py`
  (Track B), and `tools/analyze_fit3d_rig_geometry.py` (Track C). Ran
  overnight (~19:14–02:38, ~7h20m wall-clock with parallelism): **224/224
  clips completed, zero failures, zero empty, zero missing.**

  **Track A — full-scale 3D-triangulation accuracy.** Mean **10.1°** /
  median **6.2°** across all 8 subjects × 28 exercises, ~1.16M
  joint-frame samples — consistent with, and now far more statistically
  solid than, the original 1-subject/7-exercise pass above (9.1°/6.4°).
  Per-subject means are tight for 7 of 8 subjects (8.7°–10.2°); **s10 is
  an outlier at 13.0° mean** despite a normal 5.8° median — a normal
  median with an elevated mean points to a fatter error tail on a subset
  of exercises/frames rather than uniformly worse tracking, consistent
  with the already-known squat/pushup difficulty rather than a new
  failure mode, but not yet root-caused to a specific exercise or cause
  for s10 specifically. Worth a closer look before treating it as
  understood.

  **Track B — classifier domain-shift, confirmed at scale and worse than
  the small sample suggested.** Accuracy on the 5 classes the trained
  classifier can actually output: pushup 10/16 (62%), squat 2/8 (25%),
  **press 0/24 (0%)**, **raise 0/32 (0%)**, **situp 0/8 (0%)**. Press and
  raise clips are being called `pullup` 88% and 50% of the time
  respectively, at real confidence (0.68, 0.51 avg) — confidently wrong,
  not low-confidence hedging. This is not noise from the earlier
  7-exercise/1-subject sample; it's a real, severe domain-shift problem at
  full scale. One reassuring result: the 64 out-of-taxonomy negative-
  control clips (burpees, man_maker, walk_the_box, etc.) scatter across
  predicted classes with no dominant confident-wrong answer (pullup at
  48%, next-most 30%, rest low single digits) — consistent with a
  classifier that's honestly uncertain on movements it was never trained
  for, rather than confidently hallucinating. Per the hard constraint
  already established above: **diagnostic only** — Fit3D is
  validation-license-only, so any fix has to come from RepCount (already
  licensed) or real gym footage once available, never from fine-tuning on
  this data.

  **Track B correction (2026-08-10), after reading the Fit3D paper
  (Fieraru et al., "AIFit," CVPR'21) and diagnosing the 0% numbers directly
  against the classifier's own weights.** The paper doesn't classify
  exercises at all — it assumes the exercise label is already known and
  compares a trainee's per-repetition angular signature against an
  instructor's — which prompted checking whether this project's own
  exercise→class *mapping* (not just the classifier) was actually testing
  a like-for-like comparison. It wasn't, and there was a second, unrelated
  bug found at the same time. Root-caused both with real numbers, not
  guesses:

  1. **Taxonomy mismatch, not domain shift.** Inspecting the trained
     model's weights directly on a misclassified press clip (`python`,
     `np.load('models/exercise_clf.npz')`, per-feature logit contribution)
     showed `trunk_lean_mean` was the single largest driver toward the
     wrong answer (`pullup`). Tracing why: RepCount's `press` class is
     **bench press** — lying down, chest-driven (`benchpressing` in the
     annotations). Fit3D's exercises mapped to `press`
     (`dumbbell_overhead_shoulder_press`, `neutral_overhead_shoulder_press`,
     `clean_and_press`) are **standing overhead presses** — a different,
     shoulder-driven exercise the classifier was never trained on under
     that label. Same problem for `raise` (RepCount trained on
     `front_raise`; Fit3D's mapped `side_lateral_raise` /
     `overhead_trap_raises` / `dumbbell_scaptions` / `w_raise` are
     different-plane shoulder isolation moves) and `situp` (already
     flagged in `FIT3D_UTILIZATION_PLAN.md` as a weak match —
     `standing_ab_twists` is a standing rotation, not a sit-up). These
     three were reporting 0% because they were never a valid test of the
     trained class, not because the model failed to generalize. Fixed in
     `tools/analyze_fit3d_domain_shift.py`'s `EXERCISE_TO_CLASS`: these
     exercises now map to `None` (out-of-scope negative controls) instead
     of a mismatched class.
  2. **A real bug, independent of Fit3D**: `pd['exercise_class']` in
     `src/camera.py`/`src/fusion.py` was being *overwritten* by each
     periodic classification call (every `CLASSIFY_INTERVAL_SECONDS` on a
     trailing `CLASSIFY_WINDOW_SECONDS` window) rather than aggregated —
     so the value written to a track's final JSON was whichever single
     ~6s window happened to be last before the track ended, not a
     representative sample of the whole set. Confirmed by simulating the
     periodic-classification loop offline from stored `angle_series` data
     (no pipeline re-run needed): classifying off the full track at once
     already scored far better than the live "last window" value, and a
     **confidence-weighted vote across every periodic call** (new
     `src/camera.py::_record_classification`, used by both the
     single-view and fused paths) closes nearly all of that gap while
     staying usable live (it updates incrementally, unlike a
     whole-track-only approach). This is a pipeline fix, not a Fit3D-data
     fix — it changes nothing about the model or its training data.

  **Result, recomputed from the already-stored Fit3D `angle_series` data
  (no pipeline re-run — `RECOMPUTE_CLASSIFICATION` in
  `tools/analyze_fit3d_domain_shift.py`) with both fixes applied.** On the
  two exercises that are genuinely the same movement as training (squat,
  pushup/diamond_pushup — the only ones left in scope after the mapping
  fix): **squat 8/8 (100%), pushup 14/16 (88%), overall 22/24 (92%)** — up
  from the original 25%/62%/44%. `press`/`raise`/`situp` are now correctly
  out of scope rather than reported as failures.

  **Fix 2 validated independently on RepCount** (the classifier's actual
  licensed training/eval domain, using the 133 already-cached
  `test_videos/repcount/bench_results/*.json` from the last full
  benchmark — again no pipeline re-run): recomputing classification with
  the vote-aggregation logic improves 6 of 7 classes and overall accuracy
  58%→62% (77/133 → 83/133), with one mild regression (squat 71%→59%, 2
  videos, both landing on a different but still-low-confidence class,
  <0.4). Net positive and not Fit3D-specific — this is a general
  classification-robustness fix that also helps the model's real,
  licensed domain, not something tuned to Fit3D's quirks.

  **Still open**: the out-of-taxonomy negative controls now skew `pullup`
  52% of the time at 0.59 avg confidence (down from the original sample's
  more even scatter but not equivalent to it) — below this script's 60%
  "concentrated" threshold, but a real, mild bias worth watching, not a
  clean bill of health. And `hinge`/`lunge`/`curl`/`row` remain structurally
  unreachable: the trained model's `CLASSES` list doesn't include them at
  all, so real footage of those exercises will always be forced into one
  of the 7 trained classes regardless of any fix here — a known, accepted
  gap (`DEVELOPMENT.md` Phase 9), not something this session touched.

  **Track C — camera-rig geometry as a second real data point.** Fit3D's
  4-camera rig is bimodal, not evenly spaced: adjacent-camera gaps
  cluster at **~47° and ~132–133°**, identical in pattern across all 8
  subjects (same physical rig every time; elevation ~1.54m and radius
  ~4.39m equally consistent). **0 of 32 adjacent-camera gaps fall inside
  `CAMERA_PLACEMENT.md`'s recommended 60–90° band.** Yet Track A's
  triangulation accuracy on this same rig (10.1° mean) lands in the same
  range as CMU Panoptic's dome rig. That's a second independent real data
  point suggesting the 60–90° guidance may be tighter than strictly
  necessary for usable accuracy — worth folding into `CAMERA_PLACEMENT.md`
  as a caveat/data point alongside the Panoptic-derived rule, not as
  grounds to relax it outright (Panoptic and Fit3D are both controlled
  studio rigs; a real gym floor per Phase D is still the test that
  matters most).

Exit criteria: C1–C2 are documents ready to hand to whoever holds the
camera; C3 is submitted/requested, not necessarily approved yet. C3's
Fit3D half exceeds that bar — real validation results, not just access,
now at full dataset scale across all three planned tracks.

(C4, Sussex gym floor plan, dropped 2026-08-05 — that deployment is no
longer the target.)

## Phase D — Real footage validation (blocked on footage)

The actual highest-value step, now de-risked by Phases A–C.

- **D1.** Film per the Phase C2 protocol. Run the full pipeline on it.
- **D2.** Score against the Phase A hardening: does Re-ID hold up with real
  multiple people, real clothing, real occlusion? Does fusion correctly
  reject the mismatched-person case if staged?
- **D3.** Build a real trainer reference signature
  (`tools/build_reference.py`) from good-form footage and check whether the
  deviation cues are actually useful coaching, not just self-consistent
  (the only test run so far scored a reference against its own source
  video).
- **D4.** Feed misclassifications / low-confidence pose crops back into
  `training_data/` and `<output>/hard_examples/` for the next classifier
  iteration.

Exit criteria: a written finding per stress dimension (identity, occlusion,
tempo, mirrors, 3D fusion) — pass/fail plus what broke, not just "it ran."

## Phase E — Live deployment readiness (blocked on Phase D findings)

- **E1.** RTSP timestamp sync — needed before live streams replace
  pre-synced recordings.
- **E2.** Jetson port and throughput tuning — currently entirely unmeasured
  on target hardware; MediaPipe's CPU-delegate workaround is macOS-specific
  and should be revisited for Jetson.
- **E3.** Kiosk/QR check-in integration against the existing `/checkin`
  endpoint.

## Backlog — lower priority, revisit after Phase D

- Hip-driven rep counter (sit-ups, and would improve hinge movements) —
  currently deliberately counts zero.
- Scale classifier training to the full 758-video RepCount train split
  (current 280-video subset already improved every gym-core class; likely
  modest further gains).
- Any UI/dashboard polish not blocking validation.

## Sequencing summary

```
Phase A (harden Re-ID/fusion)  ─┐
Phase B (repro/doc hygiene)     ├─ run in parallel, no footage needed
Phase C (footage prep)         ─┘
                │
                ▼
         Phase D (real footage validation)
                │
                ▼
         Phase E (live deployment readiness)
                │
                ▼
              Backlog
```

Phases A, B, and C have no dependency on each other or on footage — they
should start immediately and in parallel. Phase D should not start until at
least A1–A3 are done, since the first real capture session is the most
expensive and least repeatable input in the whole project and shouldn't be
spent on foreseeable failure modes.
