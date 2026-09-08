# Handover — Joule

Last updated: 2026-09-08. Consolidates `HANDOVER.md` through `HANDOVER8.md`
(commit `18330df`), plus the un-handed-off "Recover lunge heuristic"
session (commit `248adea`), plus two design-prototyping sessions on
2026-08-24 (kickoff + Stitch MCP setup, then Stitch import + an
Apple-HIG candidate — no engine code changed either time), plus a
2026-08-27 session that installed five external design skills and used
them to build a fourth member-app candidate plus a two-round logo
exploration (13 marks total), plus a 2026-08-28 session that picked a
logo mark, built a fifth candidate fusing 04 with Stitch on direct user
instruction, and wrote a concrete real-footage capture plan for a
2026-08-29 shoot (Phase D, the project's longest-standing blocker),
plus a 2026-09-07/08 session (below) that found the 2026-08-29 shoot
never happened (postponed for logistics, not run) and instead spent the
session on footage-independent engine work inspired by two external
LinkedIn projects, into a single running log. Read this before doing
anything else in this repo. **Phase D (real gym footage) is still
blocked as of this update — nothing below required or used real gym
footage.** `STATUS.md` is the always-current engine done/left-to-do
snapshot; `ROADMAP.md` is the phased engine execution plan (Phases A–E,
plus F–L for the product-strategy docs); `DEVELOPMENT.md` is the full
dated technical log. `design/PROTOTYPES.md` is the equivalent tracking
index for the member-app front-end design work (5 candidates as of this
update). `design/logo/README.md` is the equivalent index for the logo
work (13 marks, one now chosen). This file is the session-by-session
narrative behind all of those — read it when you need *why*, not just
*what*.

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

### 2026-08-24 — Handover consolidation + member-app design prototyping kickoff

No engine code touched this session. Two threads:

**Thread 1 — Handover consolidation.** User asked to combine all numbered
handover files into one running log. Merged `HANDOVER.md`–`HANDOVER8.md`
into a single chronological file (this file), including the 2026-08-12
lunge/hinge session that had never been written up in any handover.
Updated the three stale cross-references to the deleted numbered files
(`PRODUCT_ROADMAP.md` ×3, `tools/analyze_fit3d_domain_shift.py`) to point
at this file instead, deleted `HANDOVER2.md`–`HANDOVER8.md`. Committed and
pushed (`18330df`).

**Thread 2 — Member-app design prototyping, kicked off.** Separate from
the engine work: with real-gym-footage access still blocked on the user,
we pivoted to the member-facing app's front-end design (`PRODUCT_SPEC.md`
§2.1–3.4 is the source of truth for scope/tone — this thread doesn't touch
that document, just builds toward it visually).

1. Asked the user two scoping questions up front (deliverable type,
   screen scope) rather than assuming: answered as an interactive visual
   mockup (not real app code yet — Phase F–L backend doesn't exist to
   talk to), covering the core loop only (check-in → live session →
   post-set report), matching `PRODUCT_SPEC.md`'s own Sprint-1 "walking
   skeleton" framing.
2. Found the user's own design-reference library on this machine
   (`~/design-references/awesome-design-md/design-md/`, ~80 real product
   design systems as structured `DESIGN.md` specs — Stripe, Linear, Nike,
   Raycast, Warp, etc.) and read four for texture/pattern-language before
   building anything: Nike (pill CTAs, photography-first restraint),
   Raycast (near-black surface ladder, hairline borders, no drop
   shadows), Linear (aggressive negative-tracking display type, product-
   screenshot-as-hero), Warp (warm-tinted dark canvas, tight button
   radii, Inter+mono pairing).
3. Built and published an interactive HTML/CSS artifact ("Joule Coach") —
   phone-frame mockup, switchable between the three core-loop screens.
   Design tokens locked to `PRODUCT_SPEC.md` §3.2's own palette
   (graphite/warm-white base, amber/teal/brick-red semantic-only accents)
   rather than inventing a new one; typography paired Big Shoulders
   Display (condensed/athletic, headlines + coaching-voice lines) with
   IBM Plex Sans (UI/body) and IBM Plex Mono (tabular rep counts, angles,
   timestamps) — a deliberate three-face system in the same spirit as
   Linear's Display/Text/Mono split, not an Inter-default. Implemented
   the spec's "confidence must be visible" rule literally: solid-outline
   badge = 3D fused (report screen), dashed-outline badge = 2D
   single-camera (live screen), shown once each. Content is real, not
   lorem — actual RepCount-trained exercise names, the plain-language
   coverage-disclosure copy from `PRODUCT_SPEC.md` §3.3, coaching-cue
   language matching `src/form.py`'s style. Published at
   https://claude.ai/code/artifact/2318654e-f7e1-4372-86b9-e902a1b49381 —
   **user feedback: not a strong direction, didn't land visually.** Kept
   as candidate 01 anyway (per point 5 below) — it's still useful as a
   working reference for what content/behavior each screen needs, even if
   a different candidate's visual language wins.
4. User's plan going forward, stated explicitly: **generate several
   independent prototypes from different sources** (this session's
   Claude mockup, a Google Stitch attempt the user is making themselves,
   possibly more), **keep all of them**, and pick a direction later by
   comparing rather than committing to the first attempt. Wrote a
   detailed Stitch prompt grounded in `PRODUCT_SPEC.md` (personas, tone,
   the 7 MVP screens, the confidence-visibility rule, the skeleton-
   overlay-as-signature-element requirement) but deliberately looser on
   exact visual execution (no hex codes/font names mandated) than the
   Claude mockup was, since the mockup's specific execution is what
   didn't land — left room for Stitch to make its own calls within the
   same content/tone brief.
5. Set up `design/` as the tracking structure for this multi-candidate
   process, in the same spirit as this repo's existing `ROADMAP.md`/
   `STATUS.md` pattern for the engine side:
   - `design/PROTOTYPES.md` — index: one row/entry per candidate (source,
     screens covered, file/link, notes), a "how to add a candidate"
     section, and a "Decision" section to fill in once 2+ candidates
     exist. Candidate 01 (this session's Claude mockup) logged.
   - `design/prototypes/01-claude-core-loop.html` — the mockup file
     itself, copied out of session scratchpad into the repo so it
     survives past this session (scratchpad is session-local and does
     not persist).
   - `design/stitch-prompt.md` — the Stitch prompt, saved for
     reproducibility (it was only in-conversation before this).
6. **Registered a Stitch MCP server** (`claude mcp add --transport http
   stitch https://stitch.googleapis.com/mcp --header "X-Goog-Api-Key:
   ..."`) at **local scope** (this machine + this project only,
   `C:\Users\aa3163\.claude.json`) — the user's own Google API key, now
   stored in plaintext in that config file. First attempt with `--header`
   placed before the URL failed (`-H`/`--header` is variadic and silently
   swallowed the URL as an extra header value, leaving no
   `commandOrUrl`) — fixed by placing `--header` after the URL.
   `claude mcp list` confirms it as `stitch: https://stitch.googleapis.com/mcp
   (HTTP) - ✔ Connected`, but **its tools were not available in this
   session** (MCP tools load at session start; adding a server mid-session
   doesn't hot-load its tools) — `ToolSearch` for "stitch" found nothing.
   **Next session must be a fresh one** (exit and relaunch `claude` in
   this directory) before Stitch's MCP tools — presumably something like
   "import/export a Stitch design" — become callable, so the user's
   in-progress Stitch design can actually be pulled in and saved as
   candidate 02 in `design/prototypes/`.

### 2026-08-24 (continued) — Stitch import, spec root-cause finding, Apple HIG candidate

Fresh session (as required by the previous entry's point 6 — confirmed
the Stitch MCP tools loaded this time). No engine code touched. Three
threads, all within the same design-prototyping effort.

**Thread 1 — Pulled the user's Stitch design in as candidate 02.**
`mcp__stitch__list_projects` found "Joule Coach Member App"
(`projects/7511907646849515592`, TEXT_TO_UI_PRO, built from
`design/stitch-prompt.md`). Fetched all 8 screens via `get_screen`,
downloaded each screen's exported HTML and screenshot into
`design/prototypes/02-stitch/`. **Found `01` and `07` are byte-identical
duplicates** (verified with `diff`) — Stitch generated the same "What
Joule Sees" onboarding screen twice under two different titles — so 7
unique screens in practice, not 8. Reviewed all 7 (screenshots for 6,
raw HTML for the one screen with no screenshot) and logged a full
per-screen breakdown in `design/PROTOTYPES.md`. Built and published a
screenshot-gallery artifact (`joule-coach-stitch-review.html`, own
Fraunces/Source Sans/IBM Plex Mono system, deliberately distinct from
both the Stitch and Claude candidates' own type systems since it's a
neutral review tool, not a candidate) so the user could actually see the
screens: https://claude.ai/code/artifact/d1832ec9-edac-4455-a699-be27f484ac51 —
raw Stitch HTML couldn't be embedded directly, since it depends on the
Tailwind CDN `<script>` tag, which the artifact sandbox's CSP blocks.

**Thread 2 — Found a real content bug, then traced it to its actual
source.** Cross-checking the onboarding screen's "Supported Movements"
list (Deadlift/Curl/Row/Overhead Press/Lateral Raise marked ACTIVE,
Sit-ups marked pending) against `src/exercise_classifier.py`'s `CLASSES`
and this file's own 2026-08-11/12 sessions found it flatly contradicts
validated reality: Deadlift isn't a recognized class at all (`hinge` was
investigated and rejected the same session); Row is heuristic-fallback-
only at 8%; Curl is heuristic-fallback-only at 41%; Overhead
Press/Lateral Raise map to the Fit3D Track B domain-shift finding
(trained on a different physical movement under the same label);
Sit-ups is actually one of the genuinely trained classes, shown
backwards. Initially logged this as a Stitch-specific issue. **Then,
while grounding candidate 03's onboarding copy in `PRODUCT_SPEC.md`
directly, found the real source**: §3.3 point 1 contains the near-
identical claim verbatim — *"Joule currently tracks: squat, deadlift,
curl, row, overhead press. It does not yet count sit-ups."* `git log`
confirms `PRODUCT_SPEC.md` was written 2026-08-07 (`fb9427b`), *before*
the 2026-08-11/12 sessions that contradict it — the design tool didn't
invent the overclaim, it faithfully inherited a stale first-draft claim
from the spec doc `stitch-prompt.md` was grounded in. `PRODUCT_SPEC.md`
§4's own Sprint 0 already anticipates this ("finalize the MVP exercise
list against whatever Phase D actually confirms holds up"), so this is
a known-provisional line, not a settled decision silently going stale.
**`PRODUCT_SPEC.md` §3.3 itself has not been edited** — flagged for the
user's call, since it's a product-strategy doc, not engine code.

**Thread 3 — Candidate 03, using the user's newly-installed
`apple-design` skill.** Loaded the skill's `color.md`, `typography.md`,
`layout.md`, `accessibility.md`, and `materials.md` HIG references
before building (per the skill's own "look up the actual guidelines,
don't rely on memory" instruction). Built the same 4-screen core loop as
candidate 01 (onboarding included specifically to demonstrate the
capability-list fix in place, not just describe it), as an interactive
phone-frame mockup with a working screen switcher — `design/prototypes/
03-apple-hig-core-loop.html`, published at
https://claude.ai/code/artifact/bf0442c4-2957-4bb8-9181-72f54805a67f.
Deliberate, guideline-traced departures from both other candidates:
real system-font pairing (`-apple-system`/`BlinkMacSystemFont` for UI,
`ui-serif "New York"` for headlines — Apple's own SF+NY pairing,
independently satisfying `PRODUCT_SPEC.md` §3.2's "characterful display
face distinct from the data face" without a Google Font); a **working
light/dark toggle** with distinct (not just inverted) teal/red tints
tuned for contrast in each appearance — candidates 01 and 02 are both
dark-only; a corrected **3-tier** capability list (tracked / early
support / not yet) instead of the flat 2-tier split both other
candidates used, with shape (not just color) distinguishing tiers per
`accessibility.md`'s color-blindness guidance; a live-session screen
showing *only* the rep counter and stay-in-frame cue (a literal reading
of §3.3's "minimal UI... only... deliberately not a live overlay in
MVP," stricter than candidate 02's HR+velocity live screen); the report
screen presented as a real iOS sheet (grabber handle, rounded top,
scrim), literalizing "the report screen slides up automatically"; 44pt
touch targets and a `backdrop-filter` material on the live-session HUD
per `layout.md`/`materials.md`.

All three candidates' screens, the two flagged content issues, and the
`PRODUCT_SPEC.md` root-cause finding are written up in full in
`design/PROTOTYPES.md`. No user visual feedback recorded yet on
candidates 02 or 03 — only candidate 01 has feedback so far ("didn't
land visually," see above). Decision not made; `design/PROTOTYPES.md`'s
"Decision" section is still empty pending that. User asked to save,
update this handover, and commit/push everything — done this session
(see "Repo hygiene" below); `PRODUCT_SPEC.md` itself was deliberately
left unedited pending the user's own call.

## Session: 2026-08-27 — five design skills installed, candidate 04,
## logo exploration (two rounds, 13 marks)

Two requests in one session, both design-only — no engine code touched.

**Part 1 — installed five external Claude Code skills/plugins the user
linked from GitHub:** `pbakaus/impeccable` (plugin marketplace, `/impeccable`
command family), `anthropics/claude-code`'s `frontend-design` skill (from
the already-registered `claude-plugins-official` marketplace),
`Leonxlnx/taste-skill` (already installed from a prior session —
verified, not reinstalled), `nextlevelbuilder/ui-ux-pro-max-skill`
(plugin, searchable style/typography/UX databases), and
`emilkowalski/skills` (not a plugin marketplace — a plain skills-dir
repo, so its 12 skill folders were copied directly into
`~/.claude/skills/`; its own `apple-design` skill collided with this
project's existing `apple-design` skill and was installed as
`apple-design-motion` instead so neither was overwritten).

**Part 2 — candidate 04, "lab report" direction, built then corrected.**
First pass used `impeccable` (`concept-seed.mjs`, which requires a
`PRODUCT.md` — written this session at the repo root, grounded in
`STATUS.md`'s real capability numbers, not `PRODUCT_SPEC.md`'s stale
ones) to roll a randomized direction assignment against 7 grounded
candidates drawn from the audience's world (gym console, powerlifting
refereeing, biomechanics lab report, structural drawing, surveying notes,
PT goniometer chart, Marey chronophotography). Landed on **clinical
gait-analysis report** — corridor bands for confidence, sagittal/frontal/
transverse plane panels, frontal gutter stamped `3D ONLY` because knee
valgus is invisible to one camera. Built light-committed initially
(argued from the gym-floor use scene in the new `PRODUCT.md`), verified
with Playwright (bundled Chromium — system Chrome wouldn't launch in this
environment; `chromium.launch()` via `@playwright/cli`'s bundled
`playwright-core` worked). Screenshot review caught the skeleton overlay
missing entirely (PRODUCT_SPEC §3.2 names it the required signature
element) and a squat-figure pose bug (hips and knees at the same height,
no thighs) before it was fixed.

**Then a real process failure and correction:** the summary after that
first pass claimed `taste-skill` had been used; it had not — only
`impeccable`, `frontend-design`, and `ui-ux-pro-max` were actually
invoked. User caught this ("did you use taste skill also") and asked for
dark theme + more polish. Re-did the work by actually reading
`taste-skill`'s SKILL.md (11k+ words), which explicitly scopes itself
out of "dashboards / dense product UI" (§13) — so only its universal
rules applied, not its landing-page rules. Those universal rules caught
5 real defects in the first build: 14 em-dashes in visible copy (§9.G,
the skill's own most-violated rule, zero-tolerance not "sparingly"); the
live-session screen inverting to dark inside an otherwise light page
(§4.11 Page Theme Lock violation); a metadata line with 3 middle-dots on
one line (§9.F caps at 1); numbered sheet-index eyebrows (01–05) that
encoded no real sequence, since the sheets were ordered by interest, not
flow (§9.F bans exactly this); and no loading/empty states at all (§4.5).
Rebuilt dark-committed (light kept as a working toggle, not deleted) with
a real elevation ladder (`#121416` page → `#1c1f22` pinned surface → two
raised tiers, each with a 1px top-edge highlight), answer-first
information order (verdict + cue first, then the figure, then the
scrubbable rep strip, then the plane panels, then method — reversing the
first pass's chart-first order), a draggable (not just clickable) rep
strip so the "one control drives the whole document" claim was actually
true, and a skeleton-shaped loading state dramatizing the 2–5s report
window `PRODUCT_SPEC.md` §2.1 promises. Verified in both themes: every
text token ≥4.5:1 contrast, CTA 8.17:1 dark / 5.30:1 light, drag-scrub
confirmed to correctly refuse landing on the ghost (unmeasured) cell.
File: `design/prototypes/04-lab-report/index.html` + 9 screenshots.
`design/PROTOTYPES.md`'s candidate-04 entry documents the taste-skill
miss and correction explicitly, including the honest note that the
gym-floor argument for light mode wasn't wrong — dark was a user
preference override, not a resolved design argument, and both modes are
built and verified so that can still be compared on an actual gym floor.
Also corrected: `PRODUCT.md` and this pattern's write-up both no longer
overclaim which skills did what.

**Part 3 — logo exploration, two rounds, user-requested, 13 marks total.**
Round one (`design/logo/index.html`, 5 marks): grounded in the one real,
citable engine constraint that's also visually distinctive —
`CAMERA_PLACEMENT.md` rule 4's measured camera-convergence numbers (47°
to 133° validated, ~180° roughly doubles joint-angle error, 7.7–11.8°
vs 16.5–18.2° measured). Marks: Overlap (two frame intersection),
Triangulation (two sightlines + solved joint, baseline dashed because
calibrated/known vs. sightlines solid because observed — the app's own
confidence convention built into the mark's construction), The Angle
(goniometer arc), The Corridor → replaced mid-round after two redraws
still read as an eye/surveillance mark or a scribble (kept as an honest
note rather than shipped), replaced with The Measure (two dimension
lines, reference vs. reached), and The Plumb J (a J whose stem is a
reference plumb and hook is the measured deviation — its first version's
dashed continuation read as debris at logo scale and was cut). Each mark
documented with its own risk section and tested at 32px/16px/one-colour/
both themes. User feedback: liked the concepts but flagged **no body or
exercise/gym is in any of them** and asked for 7–8 more options mixing
body + the round-one geometry, in both stick-figure and solid treatments.

Round two (`design/logo/body.html`, 8 marks, numbered 06–13 continuing
from round one): grounded in `PRODUCT_SPEC.md` §3.2's own instruction to
use the skeleton overlay as the visual signature, so a figure is
motivated rather than decorative. Every mark is a front-view squat at
depth (the exercise the engine measures best, the only view with visible
knee travel). Four body-alone (Bottom Position/stick, The Lifter/solid,
The Chain/single reduced limb, The Rep/two time-states sharing one hip
and foot), four fused with round-one geometry (Framed — body in a camera
frame with feet crossing the bottom edge in orange, drawing the literal
"whole body including feet must stay in frame" constraint; In the
Overlap; The Measured Knee; Sightlines). Two real drawing bugs caught by
rendering rather than assumed correct: the squat pose initially had hips/
knees/feet at similar widths and read as a person standing with arms
out (a front-view squat's actual signature is knees wider than both hips
*and* feet — fixed to a 14/36/22 width ratio); and mark 09 Sightlines was
recomposed three times (overhead cameras → read as raised arms; dropping
the figure's own arms → sightlines *became* the arms; moving cameras to
the sides + dashing → fixed the ambiguity but left it cluttered) and the
final recommendation explicitly says **not to ship 09** — a case of the
render process contradicting an initial draft-order recommendation,
corrected in the file rather than left standing. `design/logo/README.md`
documents both rounds, the palette/typography/usage rules, and every cut
concept with why it was cut. Round two's marks are not yet extracted to
standalone SVG files (round one's are, in `design/logo/marks/`) since
several are still moving — flagged as a next step, not done silently.

No dashboard/engine code touched this session. `PRODUCT.md` (new, repo
root) and `design/PROTOTYPES.md` (updated) are the only files outside
`design/` that changed.

## Session: 2026-08-28 — logo chosen, candidate 05 (fusion), Phase D
## capture plan for tomorrow's shoot

Three things, the first two design-only, the third the actual highest-
value item in the whole project right now.

**Logo decided: mark 07, "In the Overlap."** User reviewed both logo
rounds and picked it directly (no further iteration requested). Extracted
to `design/logo/marks/07-in-the-overlap.svg` as the canonical asset,
`design/logo/README.md` updated with a decided-status line at the top.

**Candidate 05, a fusion, not a new independent direction.** User
feedback after seeing all four prior candidates: liked 04 (the lab-report
direction) best, also liked 02 (Stitch), and asked explicitly for a fifth
candidate on 04's structure, carrying whatever 02 had that 04 didn't, in
Stitch's own colours/type, with the chosen logo added. Built
`design/prototypes/05-fused/index.html` (8 screens): all 5 of 04's
screens unchanged in structure/honesty-grammar, plus 3 screens only 02
had (onboarding, weekly plan builder, video library — rebuilt in 04's
grammar rather than ported as-is), on tokens read directly out of
Stitch's own exported HTML rather than approximated (`#f75f05` is
Stitch's real `primary-container`, the literal color behind its own CTA
buttons; `#4ae183` is its real `secondary` green; Hanken Grotesk +
JetBrains Mono; Stitch's 2px/4px radius scale), plus a persistent app bar
carrying the logo and a bottom tab bar — new chrome neither parent had,
needed because there are now 8 screens instead of 5. Full write-up
including two real bugs the render process caught (a CSS class-name
collision that made the app-bar camera glyph render blank; six em-dashes
that regressed back into visible copy despite the ban already established
for candidate 04) is in `design/PROTOTYPES.md`'s candidate-05 entry — not
repeated here. **No user feedback on 05 itself yet** — it hasn't been
shown to them; this session built and verified it (contrast, tap targets,
no console errors, both themes, full interaction pass) but the decision
loop isn't closed.

Neither of the above was committed or pushed this session — the user's
"call it a day, push it" instruction from 2026-08-27 was a one-time ask
tied to that session, not a standing instruction, and git safety practice
here is to only commit/push on explicit request. `git status` at the end
of this session shows 4 new/changed paths sitting uncommitted:
`design/PROTOTYPES.md`, `design/logo/README.md`,
`design/logo/marks/07-in-the-overlap.svg`, `design/prototypes/05-fused/`.

**Phase D capture plan, for a real shoot happening 2026-08-29.** User is
recording real gym footage tomorrow with one friend, 3 iPhones (15/17),
possibly a 4th, no professional camera — asked for a concrete plan:
which exercises, which angles, how many people per frame. This is
`ROADMAP.md` Phase D, the single longest-standing "blocked on you" item
in the project (present in every prior handover's "What's next" list
since Phase D was defined). Wrote `CAPTURE_SESSION_PLAN.md` at the repo
root, a dated, concrete instance of the existing `CAMERA_PLACEMENT.md`/
`CAPTURE_PROTOCOL.md` protocols applied to this specific equipment and
headcount, not a replacement for either — cites both inline throughout
rather than restating their reasoning.

Key decisions in that plan, each traceable to an existing finding rather
than invented on the spot:
- **One fused 3D station (squat, 3 cameras, calibrated, clap-synced) is
  the minimum success target for the day** — the exact thing `STATUS.md`
  has named as blocked since the project began ("a two-phone clap-synced
  squat set with a checkerboard calibration pass"). Explicitly scoped
  down from "fuse everything": a second fused station means a second
  calibration pass, which two people don't have time for alongside
  everything else in one day.
- **Every other exercise gets single-view 2D coverage**, prioritized
  against `STATUS.md`'s real (not `PRODUCT_SPEC.md`'s stale) capability
  table: hinge/deadlift and row first (completely unrecognized today,
  and only real labeled data moves that, not a code fix), then overhead
  press/lateral raise (a confirmed Fit3D domain-shift mislabeling bug
  that correctly-labeled real footage directly targets), then bench press
  (side-view camera angle is not optional here — `CAMERA_PLACEMENT.md`
  rule 2's confirmed finding, restated as a hard requirement rather than
  a suggestion), then lunge/curl/push-up/sit-up in descending priority.
- **One person per clip for all standard coverage**, exactly one
  deliberate two-person clip as the Re-ID occlusion stress test —
  distinguishes "clean training data" from "stress test," which are
  different goals stress-testing different systems.
- **A 4th phone, if available, does not become a second fused station**
  — goes on the squat rig instead (3 cameras beats 2 per
  `CAMERA_PLACEMENT.md` rule 4's own stated identity-consistency
  argument) or floats free for single-view coverage.
- Checked a real technical claim before writing it down rather than
  assuming: `tools/calibrate.py` only calibrates a camera **pair**
  (`K1,K2,R,t`), and while `src/fusion.py`'s `load_rig()` accepts that
  2-camera format directly, a 3-camera rig needs the combined
  `Ks/Rs/ts` array format, which nothing currently builds automatically.
  The plan states the real workaround (two pairwise `calibrate.py` runs
  against a shared reference camera, then a manual merge) rather than a
  one-line command that would have quietly failed on 3 cameras — and
  flags the merge step as worth scripting properly later, not tomorrow's
  problem.

Also built `tools/checkerboard_9x6_25mm.html` — a printable calibration
checkerboard sized to match `calibrate.py`'s own defaults exactly
(9×6 inner corners, 25mm squares, A4 landscape, print-at-100% instructions
plus a "measure it and correct `--square-mm` if the printer scaled it"
warning), since a physical checkerboard is a hard prerequisite for
tomorrow that didn't exist in the repo yet. Verified with Playwright that
it actually renders as a true alternating checkerboard (70 cells, 35/35
split) before treating it as done, not just visually eyeballed.

**Follow-up same session: a printable PDF version of the plan**, on
request — the `.md` isn't something to carry into a gym. Built
`design/capture-guide/guide.html` (a print-designed field guide: cover
page with the chosen logo, a one-page cheat sheet, table of contents,
ten numbered sections, three SVG diagrams for camera geometry — good
60–90° spacing, the 180°-to-avoid case, feet-in-frame framing — plus a
new troubleshooting Q&A section not in the `.md` version, covering
realistic failure modes like a bumped camera, a missed clap, or a
crowded gym floor) and rendered it to `CAPTURE_SESSION_PLAN.pdf` at the
repo root via headless Chromium's own print-to-PDF (`page.pdf()`
through `@playwright/cli`'s bundled `playwright-core`, the same
approach used for every design-prototype screenshot this session).
Content is sourced from `CAPTURE_SESSION_PLAN.md`, not re-derived —
same technical claims, same priority ordering, same hedged language
around the unbuilt 3-camera rig-merge step. One real implementation
snag worth recording: an initial version tried to bleed the cover page
to the physical edge using a separate CSS `@page cover { margin:0 }`
rule while Playwright's own `margin` option zeroed out the other
sides — two independent margin systems that don't reliably compose in
Chromium's print engine. Simplified to one system (Playwright owns a
uniform margin for the whole document; the cover page fakes its own
bleed with a plain CSS negative-margin trick within that single
system) rather than debug the two-system interaction. Verified before
calling it done: no `page.pdf()` or console errors, zero elements with
CSS overflow anywhere in the source, and a visual read of the actual
rendered output (cover, cheat sheet, priority table, all three
diagrams, the file-labeling section, the troubleshooting section) — the
same screenshot-then-look discipline used throughout this session's
design work, not just a successful build log treated as proof.

None of this session's new files (`CAPTURE_SESSION_PLAN.md`,
`CAPTURE_SESSION_PLAN.pdf`, `tools/checkerboard_9x6_25mm.html`,
`design/capture-guide/guide.html`) are committed either — same
reasoning as the design work above.

## What's on disk, not committed

`design/` is now fully committed (see "Repo hygiene" below) — the prior
open question about whether/when to commit it is resolved as of this
handover. Real datasets remain on disk, all
gitignored and re-acquirable/regenerable rather than committed:
`test_videos/panoptic/` + `panoptic_pose2/`, `test_videos/repcount/videos/`
(1.4GB) + `bench_results/*.json` (51MB, except the committed
`report.json`), `Fit3D/` (~44GB), `validation_results_fit3d/`
(per-subject outputs, plus the small committed aggregate `report.json`s),
`validation_results_fit3d_camsweep*/` (sweep outputs,
`sweep_summary.json` still an open "arguably worth force-committing"
item nobody has acted on). `results/demo_squat_s03/` (~19MB annotated
demo video, disk-only, easily regenerable).

## What's next

**Immediate, above everything else:** the 2026-08-29 gym shoot per
`CAPTURE_SESSION_PLAN.md`. This unblocks Phase D, which every other
engine-side item below is either blocked on or downstream of. If footage
exists by the time this is read, start there — run it through the
pipeline (`ROADMAP.md` D1/D2), check whether the checkerboard calibration
actually produced a usable rig (the 3-camera merge step described in this
session's log above does not exist as a script yet and will need writing
or doing by hand), and write up the stress-dimension findings the exit
criteria in `CAPTURE_PROTOCOL.md` and `ROADMAP.md` Phase D call for.

**Immediate, this design thread:**
1. **Decide whether to correct `PRODUCT_SPEC.md` §3.3's stale exercise
   list** (see the root-cause finding above) — a product-strategy-doc
   edit, deliberately left for the user's call rather than done silently
   mid-design-session. If corrected, candidate 03's 3-tier onboarding
   copy is a ready-made replacement to adapt from. Candidate 04 already
   built its own corrected 3-tier list independently (same root cause,
   same fix) — worth using as the second reference when this edit
   finally happens.
2. **5 candidates now exist; get the user's verdict on 05 specifically.**
   05 (`design/prototypes/05-fused/`) was built to the user's own explicit
   spec (04's structure + Stitch's tokens/screens + the chosen logo) but
   has not actually been shown to them yet as of this handover — show it,
   get real feedback, and only then fill in `design/PROTOTYPES.md`'s
   "Decision" section. 01 is ruled out ("didn't land visually"); 02 and 03
   are sources now (02 directly, via 05) rather than standalone
   contenders in the user's own framing.
3. **Logo is decided** (mark 07, "In the Overlap," extracted to
   `design/logo/marks/07-in-the-overlap.svg`) — nothing pending here
   unless the user wants to revisit it.
4. Optional cleanup, not urgent: dedupe `design/prototypes/02-stitch/01`
   vs `07` (byte-identical) if `design/` ever gets tidied.

**Engine-side:**
1. **Phase D (real gym footage)** — a shoot is planned for 2026-08-29 per
   `CAPTURE_SESSION_PLAN.md` (see this handover's newest session above).
   Blocked-on-camera-access since the project began; if the shoot
   happened, this is very likely the first item to act on, not the
   footage-prep phases below it. Everything in Phase C exists to de-risk
   this first real capture, not replace it.
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
   started. This session's design prototyping is the first actual
   engineering-adjacent work against that plan (informally, ahead of
   Phase J on the `PRODUCT_ROADMAP.md` sequencing — that's fine, it's
   design exploration, not a build against unvalidated backend).
7. `validation_results_fit3d_camsweep/sweep_summary.json` and the Fit3D
   batch's own small aggregate reports remain candidates for force-commit
   as auditable artifacts (matching the `report.json` pattern used
   elsewhere) — flagged repeatedly, not yet actioned either way.

## Repo hygiene

Everything through this handover — engine-side and `design/` alike — is
committed and pushed to `origin/main`, including all four design
candidates (`design/prototypes/01-claude-core-loop.html`,
`design/prototypes/02-stitch/` (8 files), `design/prototypes/
03-apple-hig-core-loop.html`, `design/prototypes/04-lab-report/` — HTML +
9 screenshots), the full logo exploration (`design/logo/index.html`,
`design/logo/body.html`, `design/logo/README.md`,
`design/logo/marks/*.svg` — round one only), `design/PROTOTYPES.md`,
`design/stitch-prompt.md`, `PRODUCT.md` (new, repo root — impeccable's
product-truth artifact, corrected capability table), and this file.
`.venv/`, model files, and all real datasets (`test_videos/`, `Fit3D/`,
`validation_results_fit3d*/`) are gitignored and machine-local/disk-only —
a fresh clone starts from this file's description plus needs its own
environment setup (see "Environment" above) to actually run anything.
Design-skill installs (`impeccable`, `frontend-design`, `ui-ux-pro-max`,
`emilkowalski/skills`'s 12 folders, `taste-skill`) live in the user's
global `~/.claude/` config, not in this repo — a fresh clone or a
different machine won't have them and would need reinstalling per the
2026-08-27 session note above to reproduce this session's design tooling.

## Session: 2026-09-07/08 — gym shoot postponed; four LinkedIn-inspired
## engine experiments (A: back-rounding — failed; B: displacement
## rep-count cross-check — shipped; C: barbell detector — trained but
## not integrated; D: ViTPose+ benchmark — queued)

**Phase D status first**: the 2026-08-29 shoot planned in the previous
session never happened — postponed for logistics reasons, not run. No real
gym footage exists anywhere in the repo as of this update. Phase D remains
exactly as blocked as it has been since the project began.

**How this session started**: the user shared two LinkedIn posts by Jeremy
Park, PhD (a computer-vision PhD, DevRel at VLM Run) — one measuring
deadlift back-curvature via person segmentation + a barbell detector +
MediaPipe pose, one counting chin-up reps and detecting fatigue via
ViTPose+ Large — and asked to use both to improve Joule's models/pipelines,
footage-independent since the real shoot was blocked. Mapped both posts
against this project's own documented gaps into four workstreams, all
approved by the user; full plan and exploration notes in
`.claude/plans/lovely-foraging-firefly.md` (three parallel `Explore` agents
mapped `src/form.py`/`src/risk.py`/`src/angles.py`, the pose/detector/
camera data flow, and the classifier + Fit3D/RepCount validation tooling
before any code was written). Fit3D was read-only throughout (validation
license only, per existing project rule); RepCount was used for validation
plus, in workstream C, as the only viable real-footage target for
equipment features (Fit3D has no bar-detection use case in scope for
training, and RepCount itself isn't labeled for bars either — see below).

### Workstream A — back-rounding / spinal-flexion metric: spiked, FAILED, stopped

Motivation: `src/form.py` measures trunk *lean* (the rigid shoulder→hip
segment angle) but nothing about spinal *curvature* — the injury-relevant
signal for the deadlift/hinge family, and exactly what `src/risk.py` is
pitched to catch but structurally can't with COCO-17's shoulder/hip-only
trunk landmarks. Following Park's approach, tried to get a back contour
from MediaPipe's person-segmentation mask instead of joint landmarks.

Enabled `output_segmentation_masks=True` on `src/pose.py`'s
`PoseEstimator` (new `segmentation` ctor flag, `last_mask` attribute) and
found a real, reproducible **MediaPipe 1.0.0 Windows-build bug**: the
segmentation-mask calculator aborts the whole process
(`image_frame.cc:415 Check failed: 1 == ChannelSize() (1 vs. 4)`) when fed
a *cropped* frame — exactly the padded-crop `PoseEstimator` normally uses.
Full-frame input is stable (confirmed clean across 300+ frames × 3 clips,
~20–30ms/frame). Root-caused precisely via a sequence of isolated repros
(full frame vs. crop, with/without a prior detector call) before writing
`tools/spike_back_round.py` around a self-contained full-frame MediaPipe
landmarker rather than `PoseEstimator`.

Three geometry attempts at "the back contour" on the same silhouette, each
tested on Fit3D `deadlift`/`squat`/`dumbbell_reverse_lunge` (s03 + s10):
(1) march perpendicular from the shoulder→hip chord until the mask ends —
came out at 0.6–0.7× torso length, i.e. the ray punches through the whole
body and out the far side (arms, the barbell, the far leg), not the spine;
(2) scan the full perpendicular cross-section and take the posterior end
of the contiguous run through the chord point — collapses at the flexed
part of every rep (valid only for the top ~25% of each rep), and
`corr(trunk_lean)` swung wildly per clip (−0.81 to +0.33) with no stable
relationship; (3) torso-mask centroid offset from the chord — always
computable, but equally unstable (`corr(trunk_lean)` −0.82 to +0.43,
`bottom_cent` ranging −0.48 to +0.08, including a posterior-direction
sign flip on one clip). **Verdict: not a fold-in — a dedicated R&D
sub-project**, most likely needing proper limb/torso isolation, a sharper
segmenter (RF-DETR, Park's actual choice, Apache-2.0), a per-subject
standing-baseline reference, or simply real gym footage where backs
actually round under load (Fit3D's coached reps mostly don't). `src/pose.py`
reverted clean — the only surviving artifact is `tools/spike_back_round.py`
and the write-up. Full numbers: `validation_results_backround/FINDINGS.md`
(gitignored dir — the script that regenerates it is committed).

### Workstream B — vertical-displacement rep-count cross-check: shipped, validating

Motivation: Park's chin-up tracker counts reps from vertical displacement;
Joule counts from joint-angle range, and RepCount's own historical figures
show that signal is weak specifically for pull-ups (36.8% OBO). Added a
second, **non-authoritative** counter alongside the existing one rather
than replacing anything.

Signal: hip-midpoint image-y, sign-flipped so "body higher" reads as the
high/rest state (matching the existing knee/elbow convention), normalised
by an exponentially-smoothed per-track torso length so it's scale-invariant
across camera distance (`src/camera.py::_hip_height_signal`, new
`DISP_MIN_RANGE = 0.15` torso-lengths in `src/config.py`). Reuses
`StateMachine` unchanged — it's already signal-agnostic, only `min_range`
needed a unit-appropriate value. New `pd['disp_sm']`/`pd['disp_series']` in
`_init_person`; `src/output.py::build_track_dict` emits a
`rep_count_crosscheck` block (`method`, `count`, `delta`, `agree` per
family) plus a `displacement_series` debug series — additive fields only,
`rep_counts` itself is untouched. Scoped to `src/camera.py` (single-camera
path, which is what every RepCount/Fit3D validation tool already drives) —
`src/fusion.py` is not wired up yet, flagged as a follow-up, not silently
skipped.

Quick 4-clip manual check before the full batch: on `stu8_38` (pull_up,
GT 16) both counters agreed exactly (16/16). On `stu7_35` (pull_up, GT 22)
the primary elbow-angle counter was badly wrong (3) — the cross-check
disagreed (5), correctly flagging the primary result as untrustworthy
rather than silently shipping a bad number. `stu9_64` (squat) and
`stu8_42` (push_up) both matched. Full validation batch —
`tools/benchmark_repcount.py test_videos/repcount --classes squat pull_up
push_up --keep-results` (~53 licensed clips) — [running / see next update
if this section wasn't refreshed after it finished; check
`test_videos/repcount/bench_results/*.json`'s `rep_count_crosscheck` field
and cross-reference `test_annotations.json` for the full tabulation].

### Workstream C — barbell detector: trained, honestly validated, NOT integrated

Motivation: `hinge` (deadlift) was investigated and explicitly rejected as
a heuristic on 2026-08-12 — sit-ups share the same hip:knee ROM-ratio
signature, no threshold separates them safely. **A barbell is present in a
deadlift and never in a sit-up** — bar presence is a feature joint
kinematics structurally cannot provide, and Park's post used exactly this
kind of equipment detection.

Sourced a public dataset since neither licensed dataset has bar labels
(Fit3D validation-only by policy; RepCount has none). Found and verified
via Roboflow's raw REST API (the Python SDK's `project.license` attribute
returns `None` — had to query `api.roboflow.com/<owner>/<slug>` directly)
that four barbell/plate candidates on Roboflow Universe are all
**CC BY 4.0, public**: `computer-vision-1bdzc/barbell-detection-yolov5`
(1,712 images, chosen — largest), `hackerfit/barbell-detector-svmfh-da6pw`
(444), `gym-pal/barbell-object-detection` (208), `new-workspace-kvvq5/
weights-plates` (74). Downloaded the first via the Roboflow Python SDK
(`ROBOFLOW_API_KEY` env var, user's own free-tier account) to
`datasets/barbell-yolov5-v6/` (gitignored, regenerable). Visual spot-check
of 12 random training images before spending any compute: ~1 in 12 was an
off-topic stock/clipart image (a Dreamstime watermarked render), the rest
genuine diverse gym/weightlifting footage with sensible boxes — logged as
an accepted, not hidden, data-quality caveat.

Trained YOLOv8n (`tools/train_bar_detector.py`, new; same architecture
family as the existing person detector) — first attempt at full
size/epochs (`--epochs 25 --imgsz 640`) was killed via `TaskStop` after
timing showed ~20 min/epoch (~8+ hours total, infeasible alongside the
concurrently-running workstream-B batch); restarted at `--epochs 12
--imgsz 320 --fraction 0.35 --patience 5`, ~2 min/epoch, done in ~20 min.
**Roboflow-held-out validation looked strong**: precision 0.878, recall
0.750, mAP50 0.852, mAP50-95 0.498, 16.9ms/image CPU inference.

**Real-footage check (Fit3D deadlift/squat/barbell_row, RepCount squat)
failed outright — 0 of 3 genuine bar-visible clips detected correctly.**
Two Fit3D deadlift frames with the bar clearly held: no detection at all.
One Fit3D barbell_row frame: confidently (0.82) boxed the red studio
carpet, not the bar. One Fit3D squat frame and two RepCount "squat" clips
(real bodyweight backyard exercises, no bar present) drew false-positive
boxes on a floor mat and a wooden fence post respectively (0.41–0.65
confidence — too wide a range for a threshold fix). Likely cause: the
training images are mostly loaded-plate gym floors; Fit3D's bare
motion-capture-studio bar and RepCount's unconstrained home-workout scenes
are a real domain shift on top of the noted data-quality gap, compounded
by the deliberately cheap 12-epoch/35%-data/320px training budget.

**Decision, following the same discipline as workstream A**: did **not**
proceed to extend `src/features.py`/retrain `models/exercise_clf.npz`/add
a bar-gated hinge-row heuristic — feeding a signal that's wrong on ~100%
of the real clips checked would actively harm classification, echoing why
the first per-window confidence-gate attempt (2026-08-11) was reverted
after it measurably hurt RepCount accuracy. What *is* shipped and safe:
`src/bardetector.py` (`BarDetector`, lazily loaded, degrades to a no-op
with a logged warning when no weight file exists — verified), the
per-frame hook in `src/camera.py` (scene-level detection, once per frame,
attached to every active person as `pd['bar_series']`), and
`bar_series` in the output JSON (`src/output.py`). All gated behind
`BAR_DETECT_ENABLED = False` (`src/config.py`) — **left off**. Trained
weights at `models/bar_detector.pt` (6.2MB, gitignored like every other
model weight in this repo) for whoever revisits this. Full write-up:
`validation_results_backround/BAR_DETECTOR_FINDINGS.md`.

### Workstream D — ViTPose+ Large backbone benchmark: tooling built, [run status]

Motivation: does swapping MediaPipe for Park's stronger ViTPose+ Large
close any of the Fit3D 10.1° mean / squat-pushup-tail error, and at what
CPU cost? Measurement only, explicitly no `src/pose.py` change.

Built `tools/bench_pose_backbone.py` — a standalone detect→pose→triangulate
→score loop reusing `src/triangulation.py`'s real `triangulate_skeleton`/
`compute_all_angles_3d` and `tools/validate_fit3d.py`'s `build_rig`/
`load_gt_angles`/frame-offset-search scoring, so numbers land on the same
scale as the existing Fit3D headline figures. Confirmed ViTPose+ Large
(`usyd-community/vitpose-plus-large`, HuggingFace `transformers`, Apache
2.0) works end-to-end after two real environment issues, both fixed and
worth remembering: (1) the installed `transformers==5.16.1`'s
`image_processing_vitpose.py` calls `scipy`'s `inv`/`affine_transform`
without importing them when `scipy` isn't installed — a real upstream bug,
fixed by `pip install scipy` (not a code change on our side); (2) the
`vitpose-plus-*` checkpoints are mixture-of-experts across 6 pose datasets
and raise `ValueError` without an explicit `dataset_index=torch.tensor([0])`
(0 = COCO) on every forward call — undocumented in the model card's own
copy-paste example. Verified keypoint label order (`Nose, L_Eye, ...,
R_Ankle`) matches this project's COCO-17 order exactly, so no remap is
needed. **Single-frame timing already answers half the question**:
ViTPose+ Large is ~1200ms/inference on this CPU vs. MediaPipe's ~20–30ms —
roughly **50–60× slower**, before any accuracy number is even in hand.
[Full accuracy run status: queued behind workstream B to avoid CPU
contention corrupting the timing numbers — see whether this ran and
update with real per-joint error figures if so.]

### Environment notes from this session (Windows machine)

- `mediapipe`'s segmentation-mask path aborts the process on cropped
  input (see workstream A) — full-frame only, on this machine's
  `mediapipe` 1.0.0 build.
- `transformers` + `scipy` + `roboflow` + `ultralytics` (already present)
  now all importable in `.venv` — `scipy` was a real missing transitive
  dependency for ViTPose+'s image processor, not optional.
- A `pip install roboflow` with its normal dependency resolution failed
  with a Windows file-lock error on `cv2.pyd` (a background process had
  `opencv-python` loaded) — fixed with `pip install --no-deps roboflow`,
  which was sufficient since every other dependency it needs was already
  present.
- `nohup <cmd> &` inside a single Bash tool call does **not** survive as a
  tracked background task the way passing the command directly with
  `run_in_background: true` does — the wrapper command (which just
  launches and returns) is treated as "the task," and the detached child
  gets reaped once it's considered done. Lost one benchmark run's first
  video to this before catching it via an empty log file + a dead PID.
- `google.colab`-style manual `nohup`/PID hunting aside, `TaskStop` (by
  the harness's own background-task id) is the safe way to kill a
  runaway background job without risking an OS-level `taskkill` catching
  an unrelated concurrent job too — used this to stop the first
  (25-epoch/640px) barbell-training attempt cleanly while the
  workstream-B batch kept running untouched.

### Repo hygiene

New tracked files: `tools/spike_back_round.py`, `tools/bench_pose_backbone.py`,
`tools/train_bar_detector.py`, `src/bardetector.py`. Modified:
`src/camera.py` (disp-counter + bar-detector hooks), `src/output.py`
(`rep_count_crosscheck`, `displacement_series`, `bar_series`),
`src/config.py` (`DISP_COUNTER_ENABLED`, `DISP_MIN_RANGE`,
`BAR_DETECT_ENABLED`, `BAR_DETECTOR_MODEL`, `BAR_DETECTOR_CONF`,
`BAR_DETECTOR_IMGSZ`). `.gitignore` gained `validation_results_backround/`,
`validation_results_backbone/`, `datasets/`, `runs/` — all large/regenerable,
matching the existing `validation_results_fit3d/` pattern. `models/
bar_detector.pt` exists on disk but is gitignored like every other model
weight (`*.pt`); not force-committed, unlike the tiny `exercise_clf.npz`,
because it is not (yet) a shipped, working artifact. A team-facing,
non-technical PDF summarising this session was generated and saved to the
user's own Downloads folder on request — not part of the repo.
