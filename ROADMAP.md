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

- **A1. Re-ID identity locking.** ✅ Implemented, ⚠️ not yet run/validated.
  `src/session.py` / `src/reid.py` used to bind a person's identity from a
  single embedding at track birth and never revisit it — one bad occluded
  crop misattributed an entire set. Fixed via `ProvisionalIdentity`
  (`src/reid.py`): buffers `REID_LOCK_MIN_SAMPLES` (3) embedding samples or
  `REID_LOCK_WINDOW_SECONDS` (3.0s), whichever comes first, averages and
  re-normalises them, and matches the gallery once on that average — applied
  identically in `src/camera.py` (`resolve_person`) and `src/fusion.py`
  (both previously called `gallery.identify()` on the very first sample).
  **Not yet validated**: this machine has no Python env or `test_videos/`
  assets (deleted per disk policy, per HANDOVER.md) — needs the
  before/after Panoptic run from `hurricane_env` on the dev Mac before this
  item can be marked done against its exit criteria.
- **A2. Re-ID match confidence.** Replace the flat 0.75 threshold with a
  margin test (best match vs. second-best) so an ambiguous match enrolls a
  new anonymous person instead of guessing; add gallery time-decay so stale
  embeddings from earlier in the session stop competing with current ones.
- **A3. Epipolar check in fusion.** `src/fusion.py` currently associates
  views by appearance similarity alone despite calibration already being
  loaded. Add an epipolar consistency check so two similarly-dressed people
  at adjacent stations can't silently merge into one 3D skeleton. Test
  against the existing Panoptic sequence (multi-person frames if available,
  otherwise a synthetic two-skeleton merge test).
- **A4. Depth/tempo stress tests on existing assets.** Two cheap synthetic
  tests before real footage exposes these for real: (a) retime a
  Panoptic/stock clip to ~5s/rep to check the 3-second adaptive window
  against heavy-barbell tempo, not just fast bodyweight reps; (b) overlay
  occluding rectangles over the lower body on a stock clip to observe
  angle-dropout behaviour (silent undercount vs. graceful degradation).
- **A5. Mirror-detection sanity check.** No current filter for mirror
  reflections producing phantom detections. At minimum, scope the failure
  mode on an available clip with a mirror in frame and decide whether a
  code fix or a "no mirrors in frame" placement rule is the right answer.

Exit criteria: A1–A3 shipped with a before/after test on Panoptic showing
the fix actually changes behaviour (not just a code diff); A4–A5 produce a
short written finding even if the answer is "acceptable as-is."

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
