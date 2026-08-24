# Handover — Joule

Last updated: 2026-08-12 (consolidates `HANDOVER.md` through `HANDOVER8.md`,
plus the un-handed-off "Recover lunge heuristic" session — commit
`248adea`, into a single running log). Read this before doing anything else
in this repo. `STATUS.md` is the always-current done/left-to-do snapshot;
`ROADMAP.md` is the phased execution plan (Phases A–E, plus F–L for the
product-strategy docs); `DEVELOPMENT.md` is the full dated technical log.
This file is the session-by-session narrative behind those three — read it
when you need *why*, not just *what*.

## What this is

Gym computer-vision pipeline: per-person rep counting, joint angles,
exercise classification, form scoring, injury-risk signals, session Re-ID,
and multi-camera 3D triangulation, from gym camera footage. Target
hardware: NVIDIA Jetson Orin Nano; originally developed on Apple Silicon
(`hurricane_env`, Python 3.10), now also actively worked from a Windows
machine (`C:\Users\aa3163\joule`, Python 3.11 venv — see "Environment"
below). Repo: https://github.com/Arslan7111/joule (private). Usage:
`README.md`. Full dated technical log: `DEVELOPMENT.md`. Quick-reference
summary: `STATUS.md`.

## Current state (as of commit `248adea`, 2026-08-12)

Phases A and B are fully closed on real data. Phase C (footage-prep track)
is effectively closed except M3GYM access, which is outside this project's
control (user submitting independently). Phase D (real gym footage) is the
next actual milestone and remains blocked on camera/gym access — everything
in Phase C exists to de-risk that first real capture session, not replace
it. A parallel, forward-looking product-strategy deliverable (Phases F–L,
`PRODUCT_SPEC.md`/`PRODUCT_ROADMAP.md`) has also been written and committed
but not actioned.

### What's built

Detection (YOLOv8n) → ByteTrack → Re-ID gallery (MobileNetV3 + color hist,
buffered/locked identity, margin+staleness-gated matching, `/checkin`
endpoint) → MediaPipe pose → 9 joint angles → adaptive per-person rep
counting → exercise classification (heuristic + **trained** NumPy logreg,
confidence-gated final answer with a confined heuristic fallback for
classes the trained model can't emit) → form scoring with coaching cues +
reference-signature scoring (AIFit-style) → set-level injury-risk signals →
JSON/dashboard/video output. Optional: 2+ calibrated cameras → DLT
triangulation with an independent, view-count-scaled cross-view consistency
check → true 3D angles + knee valgus; `--fuse rig.npz` runs N synchronized
sources as one live 3D station.

### What's been validated

- **RepCount Part-A**, full 152-video test split (public YouTube-workout
  dataset): zero-shot adaptive rep counter competitive with TransRAC
  (CVPR'22, trained on this data). Current authoritative classifier-routing
  figures: 149 licensed tracks, 62% baseline → adjusted by later fixes (see
  "Session log" below for the exact sequence of numbers and why they
  moved).
- **CMU Panoptic**, real dataset (verified genuine before use, then pulled
  from a teammate's push): 3D triangulation validated against motion
  capture on a held-out sequence, ~3.7–6° mean joint-angle error depending
  on sequence/frame subset (see `DEVELOPMENT.md`'s validation table for
  exact figures per run — they are not contradictory, just different
  sequences/subsets, documented as such after an earlier session flagged
  the inconsistency).
- **Fit3D**, real dataset (8 subjects × 47 exercises × 4 calibrated
  cameras, mocap-grade 3D ground truth, provided directly — not through the
  `fit3d.imar.ro` registration flow): full-scale batch validation across
  all 8 subjects × 28 exercises (~1.16M joint-frame samples) — **mean
  10.1° / median 6.2°** triangulation error. Standing/unencumbered
  exercises land in the 5–7° range; squat/pushup show real, larger error
  (10.7–13.3° mean) from genuine self-occlusion, not a pipeline defect.
  Classifier domain-shift (Track B) and camera-rig geometry (Track C)
  covered in detail below.
- Exercise classifier trained on 280 labeled RepCount videos
  (`models/exercise_clf.npz`, 6 KB, committed). Every gym-core class
  improved over heuristic rules on the full RepCount re-benchmark.

**Never verified — do this first when real gym access exists:**
- Anything on real gym footage. Every number above comes from public/
  provided datasets (RepCount, CMU Panoptic, Fit3D) or stock clips — none
  of it has run on a phone filmed at an actual gym.
- The reference-signature scoring against a real trainer's set (only
  tested self-consistently against its own source video).
- Live multi-camera fusion on anything other than pre-synced recordings —
  no RTSP timestamp sync exists.
- Multi-camera fusion beyond what the validated datasets' rigs happened to
  provide (Panoptic: up to 5 views; Fit3D: 4 views, bimodal ~47°/~132°
  spacing — see the camera-count sensitivity sweep below for what's
  actually been measured vs. assumed).

## Known caveats

1. **System `git` was broken on the original Mac** (no Xcode Command Line
   Tools confirmed installed) — a working `git` existed at
   `/opt/miniconda3/bin/git` (conda). Not relevant to the current Windows
   machine, kept here for continuity/history.
2. **Windows git push 403s**: if `git push` ever fails with a 403 from Git
   Credential Manager even though the account (`MuhammadBilal2112`) is a
   real contributor, the fix is `cmdkey /delete:LegacyGeneric:target=git:https://github.com`
   then `git push` again to trigger a fresh browser login. Root-caused once
   (2026-08-03) to a stale/scope-limited cached GCM token, not a real
   permissions problem.
3. **Disk space policy**: dataset videos are deleted when not needed;
   annotations, result JSONs, and small aggregate reports are kept (or
   force-committed despite a blanket gitignore, e.g. `report.json` files)
   and re-download/regenerate on demand. `training_data/` (119 MB,
   gitignored) is a deliberate exception — regenerating it costs ~3 hours
   of pipeline processing.
4. **Bench press needs a side-on camera**, not head-on — foreshortened
   elbow signal makes counting weak head-on even though classification is
   fine.
5. **`hinge`/`lunge`/`curl`/`row` are structurally unreachable by the
   trained classifier** — its `CLASSES` output list doesn't include them at
   all. `lunge` was recovered via a calibrated heuristic fallback
   (2026-08-12, see below). `hinge` was investigated the same way and
   rejected — real sit-up tracks share the same hip:knee ROM ratio
   signature as deadlifts, so no threshold separates them without
   misclassifying sit-ups. `hinge`/`row` remain genuinely unrecognized;
   fixing them needs a labeled dataset containing those exact movements
   (RepCount doesn't have them) or real gym footage (Phase D).
6. **Mirror reflections**: nothing in the pipeline can distinguish a
   mirror reflection from a real person (plain 2D detector, pure
   appearance-based Re-ID). Two documented failure paths (contaminates the
   real person's state machine, or enrolls as a phantom duplicate person).
   Resolved as a **placement rule, not a code fix** — "no mirrors in frame"
   is part of `CAMERA_PLACEMENT.md`. A cheap follow-up (a static per-camera
   polygon dead-zone mask) is backlogged for whenever real camera installs
   exist, as a machine-enforced backstop.
7. **Fit3D data is validation-license-only** — real dataset now on disk
   (`Fit3D/`, ~44GB, gitignored), used extensively for validation, but
   never for fine-tuning anything that would ship, per license terms.
   M3GYM (`fit3d.imar.ro`/`forms.gle/stJZgHaji7KNa5t7A`, academic
   email/affiliation required) is separately still pending — user
   submitting independently, days for approval once submitted.

## Environment (Windows machine, set up 2026-08-03)

This machine previously had no Python setup. As of the environment-setup
session:
- Python 3.11.9 installed system-wide via `winget install -e --id
  Python.Python.3.11`
- Project venv at `C:\Users\aa3163\joule\.venv\` (gitignored) — activate
  via `.\.venv\Scripts\python.exe` or `.\.venv\Scripts\Activate.ps1`
- Installed: everything in `requirements.txt` **plus `torchvision`**
  (needed by `src/reid.py`'s deep-feature embedding path — missing from
  `requirements.txt`, a real gap, fixed as part of Phase B doc hygiene)
- Model files present in project root (all gitignored, machine-local):
  `yolov8n.pt`, `yolov8n-pose.pt` (auto-downloaded by ultralytics),
  `pose_landmarker_lite.task` (manually fetched from
  `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task`)
- A pre-existing `src/pose.py` bug was found and fixed as part of Phase B:
  when `mediapipe` is importable but its `.task` model file is missing,
  the old fallback logic never tried YOLOv8n-Pose, silently yielding no
  pose estimator at all.
- Real datasets now present on disk, all gitignored: `test_videos/panoptic/`
  + `test_videos/panoptic_pose2/` (CMU Panoptic), `test_videos/repcount/`
  (152 RepCount videos + per-video result JSONs), `Fit3D/` (~44GB, the raw
  Fit3D dataset) plus `validation_results_fit3d*/` (batch outputs).

## Session log

### 2026-07-29 and earlier — Phases 1–9 (pre-dating the handover series)

All 9 original build phases done, externally validated on public datasets
at the time, nothing running. Detection→tracking→Re-ID→pose→angles→rep
counting→classification→form scoring→injury signals→output, plus optional
3D fusion, all in place. First-pass RepCount and CMU Panoptic numbers
established (superseded by later, more rigorous re-validations below — see
`DEVELOPMENT.md` for the full original figures). Suggested next steps at
the time: film real gym footage, build a real trainer reference signature,
submit Fit3D/M3GYM forms, then RTSP sync and Jetson port. This framing
held until the roadmap revamp below reordered it.

### 2026-08-03 — Roadmap revamp + environment setup + Phase A1–A3

Read all four existing docs and reported status. Ran an independent
evaluation via the `planner` agent — not a rubber stamp, a critical review
cross-checking doc claims against actual code. Key finding: **Re-ID and
cross-view fusion association were the least-tested parts of the
pipeline**, despite sitting directly under the core product promise
(correct per-person attribution) — neither RepCount (single-subject) nor
Panoptic (clean, occlusion-free dome) stress them. Also found doc/repo
hygiene gaps (benchmark artifacts not committed, stale README claims,
inconsistent Panoptic error figures across docs read as contradictory
without context). Wrote `ROADMAP.md`, a phased plan (A: harden before
footage, B: repro/doc hygiene, C: footage-prep, D: real footage
validation, E: live deployment readiness) reordering remaining work so
foreseeable failure modes get hardened *before* real footage gets spent on
them.

Fixed a git push 403 (see Known caveats #2) and set up the Windows Python
environment from scratch (see Environment above), including downloading a
small public-domain test clip for real end-to-end validation
(`person_test.mp4`, Intel IoT Devkit `sample-videos`, MIT-licensed;
scratchpad only, not in the repo).

**Phase A1 — Re-ID identity locking** (`e1fff84` code, `44d2b75`
validation). Bug: `src/camera.py`/`src/fusion.py` bound a track's
`person_id` from a *single* embedding sample at track birth (frame one in
practice) and never revisited it — one occluded/blurry birth crop
misattributed an entire set. Fix: new `ProvisionalIdentity` class in
`src/reid.py`, buffers `REID_LOCK_MIN_SAMPLES` (3) samples or
`REID_LOCK_WINDOW_SECONDS` (3.0s) — whichever first — averages/
re-normalises, calls `gallery.identify()` once. Validated via unit tests
(proved the bug, proved the fix) and a real end-to-end run on the test
clip: ByteTrack fragmented one subject into 4 tracks; all 4 correctly
consolidated into one `person_1`.

**Phase A2 — Re-ID match confidence** (`4b329fb`). Bug: `src/session.py`'s
`identify()` accepted any match clearing a flat 0.75 cosine threshold, even
when a near-equally-close second candidate existed. Fix:
`REID_MATCH_MARGIN` (0.05 — must beat runner-up by this much or enroll as
new) + `REID_STALE_SECONDS` (30 min — stale people excluded from match
*candidacy* but stay listed). Validated with 5 unit tests covering the
ambiguous case, clear-match case, and staleness exclusion; regression-
checked against the same real test clip.

**Phase A3 — Epipolar check in fusion** (`bcb699a`). Bug:
`src/fusion.py` associated people across camera views *purely* by
appearance embedding, no geometric check, despite calibration already
being loaded — two similarly-dressed people at adjacent stations could
merge into one bogus 3D skeleton. Fix: `cross_view_consistent()` in
`src/triangulation.py`, independently re-checks reprojection error per
joint at a tight tolerance (deliberately separate from the accepted
skeleton's own lenient 25px tolerance), falls back to single-view 2D if
too few joints pass. Notable finding: the existing lenient 25px tolerance
alone is measurably too loose for cross-view mismatch detection — with
only 2 cameras the epipolar constraint is 1 DOF, so a wrong match just has
to land near the epipolar line. Validated with 4 unit tests on a synthetic
stereo rig (genuine match passes, fabricated mismatch fails, heavy
occlusion gets benefit of the doubt, realistic jitter still passes).

**Panoptic access problem** (surfaced this session, resolved on
2026-08-03/04, see below): the previous handover's claim that the CMU
Panoptic download process was documented turned out false — no downloader/
URL/script existed in the repo, and the specific validated sequence
normally needs a multi-GB pull via CMU's own `panoptic-toolbox`. Blocked
final real-data validation of A1/A2/A3 until a teammate separately pushed
the dataset (see next session).

### 2026-08-03 (continued) — Phase A4, A5 (synthetic/local only)

**A4 — Depth/tempo stress tests.** No rep-bearing footage existed yet, so
drove `src/state_machine.py`'s `StateMachine` directly with synthetic
squat-shaped angle signals (a more direct, confound-free test of the
concern than a real clip would give). **Tempo** (1.5s/3.0s/5.0s/8.0s per
rep): all four counted every rep correctly, even at 8s/rep where the
3-second adaptive window can't see even half a cycle — because the window
uses 10th/90th-percentile range, and a cosine-shaped rep spends most of
its time near the extremes regardless of period. **Occlusion**
(`angle=None` for 1.0s/6.0s/4.5s spans): zero false or extra reps in every
case, graceful undercount only, no corrupted first-rep-after-gap. Verdict:
acceptable as-is, no code change.

**A5 — Mirror-detection sanity check.** No mirror clip existed; a
code-grounded analysis instead confirmed nothing in `src/detector.py`
(plain 2D YOLO) or `src/reid.py`/`src/session.py` (pure cosine appearance
match) can distinguish a reflection from a real person. Two failure
paths identified (state contamination via shared `StateMachine.update()`
calls, or phantom duplicate enrollment — judged the more likely and more
consequential of the two given A2's conservative matching). Recommended a
placement rule over a code fix (see Known caveats #6). Phase A closed on
synthetic/local validation alone at this point — real-data validation of
A1/A3 still pending the Panoptic access problem.

### 2026-08-03 (continued) — Real Panoptic validation, A1/A3 revised

A teammate pushed the real CMU Panoptic dataset to GitHub. Verified it
genuinely was Panoptic data (calibration structure, ground-truth schema,
playable footage, and a reproduced-exactly validation log) before pulling,
rather than trusting the filename (`697046c`). Ran a real before/after
using a git worktree at the pre-A1 commit.

**Found a real, previously-undetected A1-shaped bug in the baseline**: the
pre-A1 code fragmented the real capture's single subject into 2 identities
(camera 8's first-sample embedding scored 0.73, just under threshold) —
invisibly reducing "5-view fusion" to 4 views. Current (post-A1) code
correctly resolves all 5 views to one person. Real, on-camera confirmation
A1 fixes a bug that was actually present in this project's own reference
clip.

**Found a real side effect of A1**: `REID_LOCK_WINDOW_SECONDS` (3.0s)
consumes most of this very short clip (101 frames / ~3.4s) before
resolving identity at all, leaving only 41/101 frames with output vs. the
old code's 101/101 — not a product bug (real sets last far longer) but
means this clip can no longer cleanly isolate A1/A2's accuracy impact.

**Found A3's 6px threshold measurably too tight on real data**: 100% of
identity-resolved frames (41/41) failed it and fell back to 2D, dragging
aggregate accuracy 3.7°→6.3° mean (a scoring artifact of comparing
degraded 2D against 3D ground truth, not a real regression). Root cause,
diagnosed precisely: the naive all-views DLT `cross_view_consistent()`
uses has reprojection error that inherently grows with camera count (it's
the max error across every contributing view). Measured real per-joint
max-error p95 by view count: 2v=6.7px, 3v=15.4px, 4v=45.0px, 5v=78.3px.

**Tried and rejected outlier-view dropping** (mirroring
`triangulate_skeleton`'s own best-pair retry): a synthetic
single-wrong-of-5-views mismatch passed cleanly 100% of the time —
dropping the one bad view silently defeats the exact check it exists to
provide.

**Derived a view-count-scaled threshold instead**
(`CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS`: 2v=9px, 3v=20px, 4v=30px, 5v=90px)
from real noise data plus a synthetic mismatch-error sweep at realistic
rig geometry — caught and fixed a units bug along the way (the rig is in
centimeters, not meters; an earlier sweep using 0.4–2.0 as "meters" was
actually testing sub-centimeter separations). Re-ran the real sequence
with the fix: **0/41 frames now fall back to 2D** (down from 41/41), mean
error improved 6.3°→5.2°.

Two narrow, **accepted** residual limits surfaced and resolved with the
user: 2-camera inherent 1-DOF ambiguity (known, unchanged); a narrow
4-camera alignment where a mismatch can measure below real noise's own
p95 — user chose to favor catching the mismatch (30px, at the adversarial
floor) over maximizing pass-rate, matching the project's stated
conservative-matching philosophy ("mis-attribution is the worst failure
mode"). Also fixed an unrelated bug in `tools/validate_panoptic.py` (camera
IDs weren't zero-padded in video filenames, breaking any camera ID under
10). Phase A now fully closed, including real-data validation.

### 2026-08-03/04 — Phase B (repro/doc hygiene)

B2–B5 (doc hygiene, dependency/fallback bug fixes — `torchvision` gap,
`src/pose.py` YOLO-fallback bug, stale README/DEVELOPMENT.md content)
done same day (`2daf547`). **B1** (commit small benchmark artifacts so
headline numbers are auditable): Panoptic half resolved as a side effect
of the A1/A3 real-data work above (`validation_results/val.json` +
`merged.json` force-committed, `eb665b5`). RepCount half: scoped with the
user (chose the full 152-video set over a smaller subset), installed
`huggingface_hub`, found the actual HF mirror file layout differs from
what `tools/benchmark_repcount.py` expected (`test/` prefix, not
`videos/`), downloaded all 152 videos (1.4GB), ran the full benchmark
(~90 minutes). **Result: ALL n=152, MAE 0.742, OBO 22.4%**; gym-core
classes — squat 44.4%, front_raise 33.3%, pull_up 36.8%, push_up 31.2%
OBO. Verified the trained classifier was actually active (not silently
falling back to heuristics) by grepping every `classified=` value across
all 152 videos. Explained why these differ from historical Phase 8/9
figures: A1's buffered Re-ID identity-lock changes which frames/timespans
get attributed to a track, shifting the classifier's feature windows and
rep counts — not a regression, the new authoritative figure. Committed
`report.json` (19KB) as the auditable artifact; left 1.4GB video + 51MB
per-video JSONs disk-only/gitignored (freely re-downloadable). Phase A and
Phase B both fully closed as of this session (`aac8bfc`).

### 2026-08-05 — Phase C start: camera placement, Fit3D access

**C1 (camera-placement doc)**: written as `CAMERA_PLACEMENT.md`, every
rule traced to a specific validated finding already in this codebase
(feet-in-frame, bench/press side-view requirement, mirror avoidance,
3+ cameras preferred with 60–90° spacing tied to A3's 2-camera epipolar
limit, station separation sized off A3's test scale, calibration-rigidity
warning).

**C3 (Fit3D)**: asked the user for registration details to submit the
Fit3D/M3GYM forms; user said they'd handle both themselves, held off. User
then pointed out a real `Fit3D/` folder already on disk (8 subjects × 47
exercises × 4 calibrated cameras, provided directly rather than through
registration). Immediately added `Fit3D/` to `.gitignore` (~44GB) before
it could land in a commit.

Built `tools/validate_fit3d.py`. Two undocumented format quirks
reverse-engineered from the real data, both verified rather than assumed:
`camera_parameters` extrinsics' `T` is the camera *center* in world
coordinates, not the standard `P=K[R|t]` translation (confirmed by
projecting GT joints — standard convention landed ~3000px off-frame,
`X_cam = R@(X-T)` landed exactly on the body); `joints3d_25`'s joint order
and left/right split recovered via bone-length invariance for topology,
then a real back-to-camera frame to fix left/right unambiguously.

Ran a real validation sweep (s03, 7 exercises, all 4 cameras fused,
~6,800 frames): standing exercises landed in the same 5–7° range as
Panoptic; squat/pushup showed real, larger error (10.7–13.3° mean).

**Found and fixed a real bug — in the validation tool, not the pipeline.**
Squat/pushup "coverage" collapsed to ~50% with a suspicious exact-
complementary pattern across joints. Investigated properly: ruled out A3's
threshold (only 2% of frames trigger it), ruled out genuine confidence
dropout (a faithful replay showed continuously healthy confidence, after
fixing a shared-ByteTrack-instance bug in the replay itself), ruled out
Re-ID restarts. Actual cause: `src/output.py`'s `_downsample_series` runs
an independent ~30fps sampling clock per joint, so one ordinary transient
gap in one joint permanently shifts that joint's output timestamps out of
frame-grid alignment with every other joint's — the validation script's
shared per-frame join manufactured a false anti-correlation out of
harmless phase drift. Fixed by scoring each joint independently against
its own nearest GT frame: coverage went from 50–56% to 92–100% while every
error number stayed byte-identical, confirming the error figures were
trustworthy the whole time.

### 2026-08-06/07 — Product strategy docs + Fit3D full-utilization batch

Between this and the prior session, C2 (`CAPTURE_PROTOCOL.md`) was done,
C4 (Sussex floor plan) was dropped as no longer the target (`ab2d908`),
and `FIT3D_UTILIZATION_PLAN.md` was written (`de2a3e7`) — the plan this
session's batch work executes.

**Thread 1 — Product strategy.** User requested a strategic plan for
productizing the validated pipeline (subscription, camera-based personal
training, plan builder, video library), explicitly via the `planner` and
`gan-planner` agents. Ran both in parallel (`planner` was cut off by a
connection error after reading docs, resumed via `SendMessage` to the same
agent rather than a fresh spawn). Wrote **`PRODUCT_SPEC.md`** (from
`gan-planner` — personas including a deliberate "Remote Coach/Reviewer"
human-in-the-loop role needed to keep the "no human trainer" pitch honest,
MVP/v1/v2+ tables, 7-sprint plan) and **`PRODUCT_ROADMAP.md`** (from
`planner` — a Phase F–L continuation of `ROADMAP.md`, every claim traced to
a specific file/line, 4 "XL" risks + 21 named risks, an explicit "what an
MVP can/cannot honestly promise" section). Built a PDF
(`Joule_Coach_Strategy.pdf`) rendering both docs via headless Edge (Chrome
refused to run headless with an existing session open). User reported
overlapping text; diagnosed by actually rendering pages to PNG and reading
them (`pymupdf`) — two real CSS bugs (a global `h1` page-break rule
matching the cover page's title, and an `overflow:hidden` interfering with
print pagination) plus a structural rewrite of the cover/divider layout to
plain block flow (can't overlap by construction). Re-verified every page
type before calling it done (34 pages).

**Thread 2 — Fit3D full-utilization batch.** The batch job
(`tools/validate_fit3d_batch.py`, PID 1921) was already running at session
start. Monitored to 100% (224/224 clips, zero failures), ~7h20m
wall-clock. Ran a live demo for the user on completed footage
(`pipeline.py --dashboard --visualise`, s03 squat, 8/8 reps correctly
counted with real per-rep coaching feedback). Ran the two dependent
analysis scripts once the batch finished:
- **Track A** (`batch_report.json`): mean 10.1° / median 6.2° across all
  8 subjects × 28 exercises (~1.16M joint-frame samples) — consistent with
  the 1-subject pass, now statistically solid. **s10 flagged as an
  unexplained outlier** (13.0° mean vs. 5.8° median elsewhere).
- **Track B** (`domain_shift_report.json`): classifier domain-shift
  confirmed severe at full scale — 0% accuracy on press/raise/situp,
  *confidently* wrong (e.g. press→"pullup" 88% of the time at 0.68 avg
  confidence), not low-confidence hedging. Diagnostic only per the
  validation-license constraint (no fine-tuning on this data).
- **Track C** (`rig_geometry.json`): Fit3D's real 4-camera rig is bimodal
  (~47°/~132–133° adjacent gaps), **0 of 32 gaps** inside
  `CAMERA_PLACEMENT.md`'s recommended 60–90° band, yet still triangulated
  at the same 10.1° mean — evidence the 60–90° guidance is a good default,
  not a hard cutoff.

Propagated the two most externally-relevant findings to `STATUS.md`
(updated Fit3D headline to 10.1°/6.2°, added classifier domain-shift as an
honest limitation) and `CAMERA_PLACEMENT.md` (added the Track C caveat to
rule 4 directly). Phase C effectively closed except M3GYM (user submitting
independently).

### 2026-08-10 — Track B diagnosis and fix (taxonomy + last-window bug)

User asked which Fit3D batch results were "bad and disappointing" — Track
B's 0% on press/raise/situp. Also added `Joule_Coach_End_Product.pdf` (a
long-term end-goal doc the user prepared independently) to the repo,
committed and pushed (`c62f439`).

User supplied the Fit3D paper (Fieraru et al., "AIFit," CVPR'21) and asked
for a real diagnosis. Reading it prompted the right question: was the
Fit3D exercise→class mapping actually validated, or assumed?
(`FIT3D_UTILIZATION_PLAN.md` had already flagged it as "a first-pass
judgment call, not authoritative.")

**Diagnosed empirically**: loaded `models/exercise_clf.npz` directly,
computed per-feature logit contributions on a real misclassified press
clip (`s03/dumbbell_overhead_shoulder_press`, predicted `pullup` at 0.83).
`trunk_lean_mean` was the largest driver toward the wrong answer. Traced
the real cause: RepCount's `press` class is **bench press** (lying,
chest-driven); Fit3D's mapped `press` exercises are **standing overhead
presses** (shoulder-driven) — a different real exercise never trained
under that label. Same root cause for `raise` (different-plane shoulder
isolation) and `situp` (`standing_ab_twists` is a standing rotation, an
already-flagged weak match). These three were reporting 0% because the
test was invalid, not because the model failed to generalize.

**A second, unrelated, real bug found along the way**: re-testing squat/
pushup (genuinely matched classes) by computing features over each track's
*whole* `angle_series` scored much better than the numbers already on
disk (squat ~75% this way vs. 25% on disk). Traced to
`src/camera.py`/`src/fusion.py`: the live pipeline re-classifies every
`CLASSIFY_INTERVAL_SECONDS` (2s) on a trailing 6s window, and
`pd['exercise_class']` was being *overwritten* each call — so the value
baked into a track's final JSON was whichever ~6s window happened to be
last (often a rest pause or transition), not representative of the whole
set. Fixed with a confidence-weighted vote across every periodic call
(`_record_classification`, shared by `camera.py` and `fusion.py`).

Validated both fixes without re-running the 7-hour batch, by recomputing
classification from the already-stored `angle_series` in the 224 existing
pipeline JSONs. Result: **squat 8/8 (100%), pushup 14/16 (88%), overall
22/24 (92%)** on genuinely-matched classes — up from 25%/62%/44%.
Independently validated the aggregation fix on RepCount itself (the
classifier's actual licensed domain) using 133 cached benchmark JSONs, no
new runs: improves 6 of 7 classes, overall 58%→62% (77/133→83/133). One
mild regression (squat 71%→59%, 2 videos both flipping between two
low-confidence guesses on genuinely ambiguous clips — not a behavior
regression under the product's "don't be confidently wrong" standard).
Net win on RepCount too, not just Fit3D — a general robustness fix, not
something tuned to Fit3D's quirks (which would have violated the
validation-license-only constraint). Open items reported honestly:
out-of-taxonomy negative controls now skew `pullup` 52%/0.59 avg conf
(below the "concentrated" reporting threshold, a real mild bias);
`hinge`/`lunge`/`curl`/`row` remain structurally unreachable regardless of
this fix; the two RepCount squat regressions weren't root-caused further.
Committed `01d99de`.

### 2026-08-11 — Confidence-gated abstention + confined heuristic fallback

Same-session continuation. User asked how to improve the two remaining
gaps: `hinge`/`lunge`/`curl`/`row` unreachable, and the out-of-taxonomy
`pullup` bias.

**First design attempt failed its own validation gate and was not
shipped** — worth recording why. Calibrated a per-window confidence
threshold (0.5) on RepCount's confidence distribution (correct: 0.68
median; incorrect: 0.45 median — looked like a clean separation), gated
each `classify()` call individually. Track-level validation caught the
problem: **overall accuracy dropped 62%→53%**, monotonically worse at
every threshold from 0.30 up. Root cause: the vote-aggregation from the
prior day's fix already does real denoising across every window; gating
individual windows *before* aggregation throws away evidence the vote
needs — "hard but correct" classes sit in the same confidence band as
wrong/OOD calls, so no single per-window threshold separates them. Margin
(top1−top2 gap) tried too, same monotonic harm.

**Second design: gate the FINAL aggregated answer, not individual
votes.** Every window still contributes to the confidence sum/count
exactly as before; only the *published* `exercise_class` is withheld
(`'unknown'`) when the leader's aggregate confidence is below
`FINAL_CONFIDENCE_GATE`. Swept 0.0–0.8: 0.40 converts many wrong answers
to honest `'unknown'` at a small cost in correct-but-cautious ones (18
wrong caught for 6 correct withheld, out of 133), chosen over 0.35 after
comparing both (0.40 costs 3 more RepCount points, all safe
correct→unknown, for real curl-recognition capability 0.35 barely
provided). Confirmed `'unknown'` is a safe downstream state
(`src/form.py`'s `TRUNK_LEAN_LIMIT` has a deliberately generous
`'unknown': 60.0` fallback, not a crash).

Layered the heuristic fallback on top, **confined to only override an
unconfident trained-model result when the heuristic has a clear
plurality (`MIN_HEURISTIC_VOTES=3`) among classes the trained model has no
output slot for at all** (`hinge`/`lunge`/`curl`/`row`) — never competing
with real evidence on the 7 trained classes. Verified the RepCount overall
count is bit-for-bit identical with/without the fallback (77/133 either
way) — it never fires on genuine RepCount footage.

**Final shipped numbers** (`FINAL_CONFIDENCE_GATE=0.40`):

| | RepCount (133 tracks) | Fit3D matched (squat/pushup) | Fit3D fallback (hinge/lunge/curl/row) | Fit3D OOS bias |
|---|---|---|---|---|
| Baseline (no gate) | 62% (83/133) | 92% | 0% (unreachable) | pullup 52% |
| Gate 0.40 | 58% (77/133), 20 now honest `unknown` | 92% (unchanged) | 21% overall — curl 41%, row 8%, hinge/lunge 0% | pullup 43%, 16% now honest `unknown` |

Reported honestly: `hinge`/`lunge` essentially unrecovered at this point
(mostly `unknown` now instead of wrong — improved honesty, not actual
recognition — this changed for `lunge` the next day, see below). `curl`
was the one real coverage win at this point. RepCount's raw accuracy drops
4 points, a genuine tradeoff accepted because lost tracks become a safe
generic fallback rather than wrong answers — flagged as a judgment call
worth revisiting. Committed `b3ecfda`.

### 2026-08-11 (continued) — Phase C follow-through: s10 root-cause, camera-count sweep

User asked how to improve Phase C specifically. Clarified Phase C is
de-risking work, not the product itself, then did the two pieces of real
unblocked work still open in it (M3GYM access is the only blocked item,
needs the user).

**s10 outlier, root-caused.** Broke `batch_report.json` down by exercise
and joint. Two distinct causes: (1) `walk_the_box` has a severe, isolated
right-side tracking dropout (`right_elbow` n=45 valid frames vs.
~1000–2200 elsewhere — a visibility/occlusion signature, not a
triangulation bug); (2) a separate pattern across six other elevated
exercises where `left_hip` is consistently the worst joint *without* a
sample-count collapse — a subject-specific tracking/landmark bias, exact
cause not pinned down further (would need frame-level video inspection).
Neither threatens the 10.1° headline figure.

**Camera-count/angle sensitivity sweep** (the stretch goal
`FIT3D_UTILIZATION_PLAN.md` flagged but never ran). Built
`tools/validate_fit3d_camsweep.py`, ran all 6 two-camera pairs + 4
three-camera triples on s03/squat, spot-checked best/worst pair on s03/
pushup. Result: 3-of-4 barely matters regardless of which camera drops
(10.10–11.77° vs. 10.7° baseline); 2-of-4 varies enormously —
cross-referenced against `rig_geometry.json`'s actual pairwise convergence
angles: pairs at 47–133° convergence score 7.7–11.8° (several beat the
4-camera baseline), pairs at ~180° (near-opposite cameras) score
16.5°/18.2°, confirmed worse on pushup too — textbook stereo-triangulation
degenerate-case geometry, now measured directly on this project's own rig.
Folded into `CAMERA_PLACEMENT.md` as a new 2-camera-specific convergence
rule (distinct from the existing 60–90° adjacent-gap guidance for 3+
cameras).

**Near-miss worth recording**: re-deriving the 4-of-4 baseline for
comparison overwrote a previously force-committed small `report.json` (a
1-subject/7-exercise pilot artifact) — the re-run only asked for one
exercise, silently collapsing the file. Caught via `git status`/`git diff`
before committing, restored with `git checkout --`. Lesson: check `git
status` before re-running anything with `--out` pointed at a directory
that might contain previously force-committed files, not just before
destructive git commands.

### 2026-08-12 — Recover lunge heuristic; investigate and reject hinge fix (commit `248adea`)

Follow-up to the confidence-gating work: `classify_heuristic()` previously
had **no code path that could ever return `'lunge'`** at all — a prior
deliberate call judged left/right hip ROM asymmetry too unreliable from a
side-on camera. Re-examined empirically now that Fit3D's
`dumbbell_reverse_lunge` tracks (all 8 subjects, validation-only) were
available: hip ROM asymmetry turned out to be a clean, consistent signal
there (0.55–0.85 across every subject, vs. 0.01–0.33 for squat/deadlift).

Naively applied to RepCount's real single-camera footage it produced false
positives two distinct ways: (1) a fully-occluded hip landmark reads as
`rom=0.0`, which a raw ratio misreads as *maximum* asymmetry (found on a
real squat clip with 0 valid `right_hip` samples) — guarded with
`MIN_HIP_ROM_FOR_ASYM` (both sides must exceed 1° ROM before the ratio is
trusted); (2) a couple of already-known-noisy bench-press clips
(foreshortened bent-leg bracing) crossed a low threshold too — guarded by
sweeping the threshold against RepCount's 149 licensed tracks as the
regression check. **`LUNGE_HIP_ASYM_THRESHOLD = 0.72`** is the lowest
threshold with zero RepCount false positives and zero tracks flipped from
baseline, while recovering **6/8 Fit3D lunge tracks (0/8 before)**.
Shipped in `src/exercise_classifier.py`.

`hinge` was investigated the same way (hip:knee ROM ratio) and
**rejected**: real sit-up tracks are also hip-flexion-dominant and
knee-static, producing the same high ratio as a real deadlift — every
threshold tested (1.4–2.2) that recovered real deadlift tracks also
misclassified real RepCount sit-ups as `'hinge'`. A genuine feature-space
overlap, not noise — no threshold on this feature separates them safely.
Left as the pre-existing knee<25 rule; `hinge`/`row` recognition still
needs labeled training data (RepCount has none; Fit3D is validation-only),
not a heuristic. `FIT3D_UTILIZATION_PLAN.md`, `ROADMAP.md`, `STATUS.md`
updated with the finding; committed and pushed.

## What's on disk, not committed

As of the latest session, working tree is **clean** — `git status` shows
nothing outstanding. Real datasets remain on disk, all gitignored and
re-acquirable/regenerable rather than committed: `test_videos/panoptic/`
+ `panoptic_pose2/`, `test_videos/repcount/videos/` (1.4GB) +
`bench_results/*.json` (51MB, except the committed `report.json`),
`Fit3D/` (~44GB), `validation_results_fit3d/` (per-subject outputs, plus
the small committed aggregate `report.json`s), `validation_results_fit3d_camsweep*/`
(sweep outputs, `sweep_summary.json` still an open "arguably worth
force-committing" item nobody has acted on). `results/demo_squat_s03/`
(~19MB annotated demo video, disk-only, easily regenerable).

## What's next

1. **Phase D (real gym footage)** is the actual next milestone — still
   blocked on camera/gym access, unchanged across every session in this
   log. Everything in Phase C exists to de-risk this first real capture,
   not replace it.
2. **M3GYM access** is the one remaining blocked Phase C item — needs the
   user to submit [the form](https://forms.gle/stJZgHaji7KNa5t7A)
   (academic email/affiliation/purpose required), then days for approval.
3. **`hinge`/`row` recognition** is still genuinely unsolved — needs
   either a labeled dataset containing these exact movements or real gym
   footage (Phase D).
4. **s10's `left_hip` bias pattern** wasn't root-caused past "consistent
   across six exercises, not occlusion" — would need frame-level video
   inspection to go further.
5. **Out-of-taxonomy `pullup` bias** (43% at last measurement, down from
   52% but still the modal wrong answer) is a real, mild, unresolved
   pattern worth watching if the classifier's scope ever expands.
6. The product strategy docs (`PRODUCT_SPEC.md`/`PRODUCT_ROADMAP.md`/the
   two PDFs) are planning deliverables for the human team, committed but
   not yet actioned — no engineering work against Phase F onward has
   started.
7. `validation_results_fit3d_camsweep/sweep_summary.json` and the Fit3D
   batch's own small aggregate reports remain candidates for force-commit
   as auditable artifacts (matching the `report.json` pattern used
   elsewhere) — flagged repeatedly, not yet actioned either way.

## Repo hygiene

Working tree fully pushed to `origin/main` as of this handover (commit
`248adea`, "Recover lunge heuristic recognition; investigate and reject
hinge fix"). No uncommitted code changes outstanding. `.venv/`, model
files, and all real datasets (`test_videos/`, `Fit3D/`,
`validation_results_fit3d*/`) are gitignored and machine-local/disk-only —
a fresh clone starts from this file's description plus needs its own
environment setup (see "Environment" above) to actually run anything.
