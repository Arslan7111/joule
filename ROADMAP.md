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
  **Still open**: the formal before/after Panoptic triangulation-accuracy
  comparison from `hurricane_env` has not been run (Panoptic re-acquisition
  is a separate, heavier multi-GB pull via the CMU panoptic-toolbox — no
  download URL/script is actually preserved in this repo despite
  HANDOVER.md implying one is documented; flagged as a `DEVELOPMENT.md` gap
  worth fixing under Phase B).
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
  **Still open**: the 6px threshold is only validated on noise-free/
  lightly-jittered synthetic data — real camera calibration error, rolling
  shutter, and real pose-estimation noise could push genuine matches
  closer to that boundary than the synthetic test suggests. Needs a real
  run against Panoptic or real multi-camera footage to confirm 6px isn't
  too tight (false-rejecting real matches) or too loose (still missing
  realistic adjacent-station mismatches) — same Panoptic-access blocker as
  A1/A2's validation gap.
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
exit criteria met for all of A1–A5** — real-footage validation of A1–A3's
tuned thresholds remains open pending Panoptic/real-camera access (see
below), which does not block moving to Phase B/C.

## Phase B — Reproducibility & doc hygiene (no footage required, parallel with A)

Low effort, currently makes every headline number in the docs unverifiable
from a fresh clone.

- **B1.** Commit the small (non-video) benchmark artifacts —
  `bench_results/report.json`-equivalent and the Panoptic validation JSON —
  so the RepCount/Panoptic numbers in STATUS.md/DEVELOPMENT.md are
  auditable, not just asserted.
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

- **C1. Camera-placement doc.** Write this now, not after filming — it's a
  prerequisite for good footage, not a follow-up. Cover: bench-press side-view
  requirement (confirmed head-on counting is weak), feet-in-frame-on-every-camera
  rule, mirror avoidance, 60–90° spacing for 3D stations, ~3–4 machines per 2D
  camera.
- **C2. Structured capture protocol.** A short checklist for the first real
  shoot: per exercise, one side view + one 45° view; feet in frame; a
  deliberate two-person-crossing clip (Re-ID stress test); a clip with a
  mirror in frame (Phase A5 stress test); a slow heavy-set clip (tempo
  stress test); a two-phone clap-synced squat set with checkerboard
  calibration for the first real 3D fusion run.
- **C3. Submit Fit3D and M3GYM registration forms now.** Pure latency cost
  (days to approve), zero blocker to submitting today. M3GYM in particular
  is the only realistic path to scoring Re-ID against ground-truth subject
  IDs before real gym footage exists.
- **C4. Sussex gym floor plan** (if that deployment is still the target) —
  request it now so the camera layout plan isn't blocked later.

Exit criteria: C1–C2 are documents ready to hand to whoever holds the
camera; C3–C4 are submitted/requested, not necessarily approved yet.

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
