# Handover 2 — Joule

Session date: 2026-08-03. Read this first if picking up the project after
`HANDOVER.md` (2026-07-29) — this session's work builds directly on top of
it and supersedes it as the "start here" document. `STATUS.md` is the
always-current done/left-to-do snapshot; `ROADMAP.md` is the phased
execution plan this session introduced and worked through; `DEVELOPMENT.md`
is the full dated technical log (phases 1–9, pre-dating this session).

## What happened this session, in order

1. Read all four existing docs (`STATUS.md`, `HANDOVER.md`, `README.md`,
   `DEVELOPMENT.md`) and reported project status to the user.
2. Ran an independent evaluation via the `planner` agent — not a rubber
   stamp of the project's own self-assessment, a critical review that
   cross-checked doc claims against actual code. Findings (full detail in
   `ROADMAP.md`'s "Why this revamp" section):
   - Architecture and phased approach are sound; keying exercise state to
     *person* not *tracker track* is the standout design decision.
   - **Re-ID and cross-view fusion association are the least-tested parts
     of the pipeline**, despite sitting directly under the core product
     promise (correct per-person attribution). Neither RepCount nor CMU
     Panoptic benchmarks stress these — RepCount is single-subject footage
     and the benchmark script itself only scores the largest track; Panoptic
     is a clean, occlusion-free dome with no equipment or mirrors.
   - Doc/repo gaps found: benchmark artifacts not committed (unreproducible
     from a fresh clone), README claims model weights are "already present"
     when they aren't, README's file layout section stale since Phase 4,
     `DEVELOPMENT.md` phase ordering stale, inconsistent Panoptic error
     figures across docs (~6° vs 3.7° — both correct, different sequences,
     but read as contradictory without context).
3. Wrote `ROADMAP.md` — a phased plan (A: harden before footage, B: repro/
   doc hygiene, C: footage-prep track, D: real footage validation, E: live
   deployment readiness, plus a lower-priority backlog) reordering the
   project's remaining work so foreseeable failure modes get hardened
   *before* the first real gym footage gets spent on them. Linked from
   `STATUS.md`. Committed and pushed (`35af8b7`).
4. **Git push access issue, diagnosed and fixed**: push failed with a 403
   from Git Credential Manager. Root cause: GCM had a stale/scope-limited
   cached token for the correct account (`MuhammadBilal2112`, confirmed a
   real contributor) — not a permissions problem. Fix: `cmdkey
   /delete:LegacyGeneric:target=git:https://github.com`, then `git push`
   again triggered a fresh browser login and succeeded. **If push 403s
   again, this is the first thing to try.**
5. **Set up a Python environment on this Windows machine** (there was none
   — `python`/`python3` on PATH were Windows Store stub aliases only):
   - Installed Python 3.11.9 via `winget install -e --id Python.Python.3.11`
   - Created a project-local venv: `C:\Users\aa3163\joule\.venv\`
     (gitignored — added `.venv/` to `.gitignore` this session)
   - Installed deps: `pip install -r requirements.txt torchvision` (note:
     `torchvision` is NOT in `requirements.txt` but is required by
     `src/reid.py`'s deep-feature embedding path — this is a real gap,
     unfixed, flagged for Phase B; `ultralytics` transitively pulls `torch`
     but not `torchvision`)
   - Downloaded `pose_landmarker_lite.task` (MediaPipe's primary pose
     backend model file — also not committed/auto-fetched, another Phase B
     gap) from
     `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task`
   - **Separately discovered, not fixed (out of scope this session)**: a
     pre-existing bug in `src/pose.py` — when the `mediapipe` *library* is
     importable but its `.task` model file is missing, the fallback logic
     never tries YOLOv8n-Pose (the `_YOLO_POSE_AVAILABLE` flag is only set
     inside `if not _MP_AVAILABLE:`, which is false whenever the mediapipe
     package itself imports fine). Net effect: a fresh install with
     mediapipe pip-installed but no model file silently gets **no pose
     estimator at all** rather than falling back. Worth a real fix, small
     scope, not yet done.
   - Downloaded one small public-domain test clip (Intel IoT Devkit's
     `sample-videos` repo, MIT-licensed, standard CV-testing asset) to
     `<scratchpad>/person_test.mp4` for real end-to-end validation — this
     is NOT in the repo (scratchpad only, outside the working directory).
6. Implemented and validated **Phase A1, A2, A3** of `ROADMAP.md` — see
   below for full detail per item. Did **not** get to A4 or A5.

## Phase A progress: 3 of 5 done

Corrected mid-session: Phase A has 5 items (A1–A5). **A1, A2, A3 are done.
A4 and A5 are not started.** Don't reintroduce this miscount next session.

### A1 — Re-ID identity locking (done, commit `e1fff84` code + `44d2b75` validation)

**Bug**: `src/camera.py` and `src/fusion.py` both bound a track's
`person_id` from a *single* embedding sample at track birth (in practice,
frame one) and never revisited it. One occluded/blurry birth crop
misattributed an entire set, since all exercise state is keyed by
`person_id`.

**Fix**: new `ProvisionalIdentity` class in `src/reid.py`. Buffers
`REID_LOCK_MIN_SAMPLES` (3) embedding samples or `REID_LOCK_WINDOW_SECONDS`
(3.0s) — whichever comes first — averages and re-normalises them, and calls
`gallery.identify()` exactly once on that average. Wired identically into
both `src/camera.py`'s `resolve_person()` and `src/fusion.py`'s per-view
loop (the latter reuses `camera.py`'s `_init_track()`, so one field addition
covered both call sites).

**Validated**:
- Unit tests against the real `ProvisionalIdentity`/`SessionGallery`
  classes: proved a bad first crop alone causes a spurious wrong-person
  enrollment under the old behaviour, while the buffered average correctly
  matches the true person.
- Real end-to-end pipeline run on the downloaded test clip: ByteTrack
  fragmented the one subject into 4 tracks; all 4 correctly consolidated
  into a single `person_1` via the new buffered-match path (one re-match
  logged at `sim 0.79`). Log evidence in this session's transcript.

**Still open**: the formal before/after Panoptic triangulation-accuracy
comparison from `hurricane_env` was never run — see "Panoptic access" below.

### A2 — Re-ID match confidence (done, commit `4b329fb`)

**Bug**: `src/session.py`'s `identify()` accepted any match clearing the
flat 0.75 cosine threshold, even when a second gallery candidate was nearly
as close — increasingly likely as the gallery grows (many gym members in
similar clothing).

**Fix**: `REID_MATCH_MARGIN` (0.05) — a match must beat the runner-up
candidate by this much or the track enrolls as new rather than guessing.
`REID_STALE_SECONDS` (30 min) — people not updated within that window are
excluded from match *candidacy* (but stay in the gallery dict for
check-in/dashboard listing) so an old embedding from early in a session
can't keep competing with recently-seen people.

**Validated**: 5 unit tests against the real `SessionGallery` class —
engineered ambiguous best-vs-second-best case (both candidates individually
clear the raw threshold, margin ≈ 0) correctly falls back to new enrollment;
a clearly-closer case still matches; a 31-minutes-stale person is excluded
from candidacy yet remains listed in `gallery.people()`. Regression-checked
against the same real test clip used for A1 — identical correct result.

### A3 — Epipolar check in fusion (done, commit `bcb699a`)

**Bug**: `src/fusion.py` associated the same person across camera views
*purely* by appearance embedding via the Re-ID gallery — no geometric check
at all, despite full camera calibration already being loaded. Two
similarly-dressed people at adjacent stations could merge into one
confident-looking but bogus 3D skeleton.

**Fix**: `cross_view_consistent()` in `src/triangulation.py`. Before
accepting a person's multi-view triangulation, independently re-checks
reprojection error per jointly-visible joint at a **tight 6px tolerance**
(`CONSISTENCY_MAX_REPROJ_PX`) — deliberately separate from
`triangulate_skeleton`'s own lenient 25px tolerance used for the accepted
skeleton output. If too few joints clear it, that frame falls back to
single-view 2D for that person (best-visibility view chosen) rather than
emit a bogus 3D skeleton, with a warning logged.

**Notable finding while building this**: the existing lenient 25px
tolerance is measurably too loose to catch cross-view mismatches on its
own — a synthetic two-different-people case still passed 11/17 joints at
25px. Root cause: with exactly 2 cameras, the epipolar constraint is only
1 degree of freedom per point (a wrong match just has to land near the
epipolar line, not at an exact point) — real disambiguation needs a much
tighter tolerance or 3+ cameras. This is why a separate, independently
tunable threshold was added rather than reusing the existing one.

**Validated**: 4 unit tests against the real triangulation code on a
synthetic 2-camera stereo rig: genuine single person (17/17 joints pass,
correctly judged consistent), fabricated cross-view mismatch (0/17 joints
pass at the 4px diagnostic level, correctly judged inconsistent), heavy
occlusion / too few jointly-visible joints (benefit of the doubt — judged
consistent, avoiding false rejection under normal occlusion), and realistic
~1.5px synthetic keypoint jitter on a genuine match (still 17/17, still
correctly judged consistent).

**Still open**: the 6px threshold is validated only on noise-free/lightly-
jittered *synthetic* data. Real camera calibration error, rolling shutter,
and real pose-estimation noise could push genuine matches closer to that
boundary than the synthetic test suggests — could be too tight (false-
rejecting real matches) or, less likely given the synthetic margin, still
too loose for some real adjacent-station scenarios. Needs a real multi-
camera run to confirm. Same Panoptic-access blocker as A1/A2.

## The Panoptic access problem (blocks final validation of A1/A2/A3)

`HANDOVER.md` (previous session) implied the CMU Panoptic download process
was "documented in `DEVELOPMENT.md`" — checked this session, **it is not**.
`tools/validate_panoptic.py` just takes a plain `dataset_dir` positional
argument; there's no embedded downloader, URL, or script anywhere in the
repo. Re-acquiring the specific validated sequence (`171204_pose2`, 3 views
+ calibration + mocap ground truth) is normally a multi-GB pull via CMU's
own `panoptic-toolbox` downloader, not a one-line `curl`. This is now
tracked as a Phase B gap in `ROADMAP.md` (fix the documentation) but doesn't
unblock the actual re-acquisition, which is a separate, heavier task.
**Next session: either locate the original download commands (check shell
history / notes on the Mac's `hurricane_env` if available) or budget time
for a fresh `panoptic-toolbox` pull.**

## Environment now available on this machine

This machine (`C:\Users\aa3163\joule`, Windows) previously had **no** Python
setup — the documented dev environment was Mac-only (`hurricane_env`,
conda). As of this session:

- Python 3.11.9 installed system-wide via winget
- Project venv at `C:\Users\aa3163\joule\.venv\` — activate via
  `.\.venv\Scripts\python.exe` (or `.\.venv\Scripts\Activate.ps1` in
  PowerShell)
- Installed: everything in `requirements.txt` (opencv-python, ultralytics,
  mediapipe, numpy, lapx) **plus `torchvision`** (needed by `src/reid.py`,
  missing from `requirements.txt` — real gap, see Phase B)
- Model files present in project root: `yolov8n.pt`, `yolov8n-pose.pt`
  (both ultralytics-auto-downloaded on first pipeline run),
  `pose_landmarker_lite.task` (manually fetched, see URL above) — all
  gitignored, not committed, present only on this machine's disk
- One small public-domain test clip at
  `<session scratchpad>\person_test.mp4` (NOT in the repo — scratchpad is
  session-specific and will not persist to next session; re-download from
  `https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4`
  if needed again)
- No Panoptic data, no real gym footage, no calibrated multi-camera rig on
  this machine — see the Panoptic access problem above

## What's next

Immediate continuation, in order:

1. **A4 — Depth/tempo stress tests on existing assets.** Not started.
   Two cheap synthetic tests: (a) retime a clip to ~5s/rep to check whether
   the 3-second adaptive window (`ADAPTIVE_WINDOW_SECONDS` in
   `src/config.py`) handles heavy-barbell tempo, not just the fast
   bodyweight reps RepCount is dominated by; (b) overlay occlusion
   rectangles over the lower body on a stock clip to observe angle-dropout
   behaviour (silent undercount vs. graceful degradation). Can use the
   `person_test.mp4`-style clip already validated as working this session,
   or a fresh one.
2. **A5 — Mirror-detection sanity check.** Not started. No current filter
   for mirror reflections producing phantom detections (which would also
   poison the Re-ID gallery). At minimum, needs a written finding (fix vs.
   placement-rule) even without a code change — exit criteria only asks
   for that much.
3. Once A4/A5 done, Phase A is fully closed — move to Phase B (repro/doc
   hygiene: commit small benchmark JSONs, fix README's stale claims and
   layout section, fix the `torchvision`-missing-from-requirements.txt gap,
   fix the pose.py YOLO-fallback bug found this session, reorder
   `DEVELOPMENT.md`) and Phase C (footage-prep track: camera-placement doc,
   capture protocol, submit Fit3D/M3GYM forms) — both have no dependency on
   footage and can run in any order/parallel.
4. Real Panoptic validation of A1/A2/A3's tuned thresholds, once footage
   access is resolved (see above).

## Commits this session (all pushed to `origin/main` as of end of session)

```
35af8b7  Add ROADMAP.md: phased plan hardening Re-ID/fusion before real footage
e1fff84  Phase A1: buffer early Re-ID samples instead of locking on the first crop
44d2b75  Validate Phase A1 end-to-end; ignore local venv
4b329fb  Phase A2: margin test + staleness exclusion for Re-ID matching
bcb699a  Phase A3: epipolar consistency check for cross-view fusion association
```

(This file's own commit will be the next one after `bcb699a`.)

## Repo hygiene

Working tree fully pushed to `origin/main` as of this handover. No
uncommitted code changes outstanding. `.venv/` and the fetched model files
are gitignored and machine-local only — a fresh clone on another machine
starts exactly where `HANDOVER.md` (2026-07-29) describes, plus needs its
own environment setup (see above) to actually run anything.
