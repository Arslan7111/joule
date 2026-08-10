# Handover 8 — Joule

Session date: 2026-08-10. Read `HANDOVER7.md` first for the Fit3D
full-utilization batch context this picks up from. Between HANDOVER7 and
this session, `fb9427b` committed everything HANDOVER7 left pending
(product docs, PDF, the three new `tools/` scripts, `ROADMAP.md`/
`STATUS.md`/`CAMERA_PLACEMENT.md` edits) — confirmed via `git show --stat`
before starting this session, so nothing was carried over as "still
uncommitted." This session had two threads: (1) adding a second
product-strategy PDF the user prepared independently, and (2) diagnosing
and fixing why Track B (classifier domain-shift) reported such bad
numbers.

## Thread 1 — `Joule_Coach_End_Product.pdf`

User provided an updated long-term end-goal document (prepared by them,
sourced from `Joule_Coach_Strategy.pdf` plus a fresh read of the repo at
commit `de2a3e7`) and asked for it to be copied into the repo and pushed.
Read it in full, copied to the repo root alongside the existing strategy
PDF, committed (`c62f439`), and pushed — this also carried along the
already-committed-but-unpushed `fb9427b` from the prior session, since the
local branch was 1 commit ahead of `origin/main` at session start.

## Thread 2 — Diagnosing and fixing Track B (classifier domain-shift)

User asked "which results were bad and disappointing" from the Fit3D
batch; Track B's 0% accuracy on press/raise/situp was the clear answer.
User then supplied the Fit3D paper (Fieraru et al., "AIFit," CVPR'21,
`Fieraru_2021_CVPR.pdf`) and asked me to read it, diagnose the failure,
and try to fix/improve it, taking the time needed.

**What the paper actually said, and why it mattered.** AIFit doesn't
classify exercises — it assumes the exercise label is already known per
video and compares a trainee's per-repetition angular signature against
an instructor's reference signature, using an active/passive
feature-energy split. That's a different task from this project's
classifier. But reading it prompted the right question: was this
project's Fit3D validation actually comparing like-for-like exercises
under each class label, or just assuming the mapping was right? It
wasn't fully checked before — `FIT3D_UTILIZATION_PLAN.md` had already
flagged the mapping table as "a first-pass judgment call, not
authoritative."

**Diagnosis, done empirically, not by inspection.** Loaded
`models/exercise_clf.npz` directly and computed per-feature logit
contributions on a real misclassified Fit3D press clip
(`s03/dumbbell_overhead_shoulder_press`, predicted `pullup` at 0.83
confidence). `trunk_lean_mean` was the single largest driver toward the
wrong answer. Traced why: RepCount's `press` class is **bench press**
(`benchpressing` in the annotations — lying, chest-driven). Fit3D's
exercises mapped to `press` (`dumbbell_overhead_shoulder_press`,
`neutral_overhead_shoulder_press`, `clean_and_press`) are **standing
overhead presses** — shoulder-driven, a different real exercise the
classifier was never trained on under that label. Same root cause for
`raise` (RepCount trained on `front_raise`; Fit3D's mapped exercises are
different-plane shoulder isolation moves) and `situp` (already flagged as
a weak match — `standing_ab_twists` is a standing rotation). These three
were reporting 0% because the test was invalid, not because the model
failed to generalize.

**A second, unrelated, real bug found along the way.** Re-testing the
genuinely-matched classes (squat, pushup) by computing features over each
track's *whole* `angle_series` scored much better than the numbers
already on disk (squat looked like ~75% this way vs. the original 25%).
Traced this to `src/camera.py`/`src/fusion.py`: the live pipeline
re-classifies every `CLASSIFY_INTERVAL_SECONDS` (2s) on a trailing
`CLASSIFY_WINDOW_SECONDS` (6s) window, and `pd['exercise_class']` was
being *overwritten* by each call — so the value baked into a track's
final JSON was whichever single ~6s window happened to be last before the
track ended (often a rest pause or transition), not a representative
sample of the whole set. Fixed with a confidence-weighted vote across
every periodic call (`src/camera.py::_record_classification`, used by
both `camera.py`'s single-view path and `fusion.py`'s fused path) —
accumulates `class -> summed confidence` and `class -> vote count`,
reports the running leader and its average confidence. Still fully live/
incremental (updates every 2s, doesn't need the track to finish), unlike
a whole-track-only approach.

**Validated both fixes without re-running the 7-hour Fit3D batch or any
new pipeline runs**, by recomputing classification from the already-
stored `angle_series` in the existing 224 pipeline output JSONs (this
data doesn't change — only how the periodic classifier calls get
aggregated into a final label does). Updated
`tools/analyze_fit3d_domain_shift.py`: corrected `EXERCISE_TO_CLASS` (
`press`/`raise`/`situp`-mapped exercises now `None`, i.e. out-of-scope
negative controls) and added `RECOMPUTE_CLASSIFICATION` (recomputes via
the real `_record_classification`/`ExerciseClassifier`, not the stale
stored field). Result: **squat 8/8 (100%), pushup 14/16 (88%), overall
22/24 (92%)** on the classes that are actually the same movement as
training — up from 25%/62%/44%.

**Independently validated the classification-aggregation fix (fix 2) on
RepCount itself** — the classifier's actual licensed training/eval
domain — using the 133 already-cached
`test_videos/repcount/bench_results/*.json` from the last full benchmark
run (again, no new pipeline runs, no new downloads). Improves 6 of 7
classes; overall 58%→62% (77/133 → 83/133 correct routing). One mild
regression: squat 71%→59%, 2 videos, both flipping between two low-
confidence (<0.4) guesses on genuinely ambiguous clips — not a behavior
regression under the product's own "don't be confidently wrong" standard.
This being a net win on RepCount too (not just Fit3D) is the important
signal: it's a general classification-robustness fix, not something
tuned to Fit3D's specific quirks — which would have been the wrong thing
to do given the validation-license-only constraint.

**What's still open, reported honestly rather than glossed over:**
- Out-of-taxonomy negative controls now skew `pullup` 52% of the time at
  0.59 avg confidence — below this script's 60% "concentrated" threshold,
  so it still prints as "scattered," but a real, mild bias worth watching,
  not a clean result.
- `hinge`/`lunge`/`curl`/`row` remain structurally unreachable by the
  trained model — its `CLASSES` output list doesn't include them at all,
  so real footage of those exercises will always be forced into one of
  the 7 trained classes regardless of anything fixed this session. Known,
  pre-existing, documented in `DEVELOPMENT.md` Phase 9 — not touched here.
- The two RepCount squat regressions weren't root-caused beyond "both
  land on a different low-confidence guess" — not investigated further
  since neither is a confident wrong answer.

## Files changed this session

- `Joule_Coach_End_Product.pdf` — added, committed, pushed (`c62f439`,
  before this session's second thread started).
- `src/camera.py` — added `_record_classification()`, added
  `_class_conf_sum`/`_class_conf_n` to `_init_person()`, updated the
  classification call site.
- `src/fusion.py` — imports and uses `_record_classification()` at its
  classification call site (same fix, fused-view path).
- `tools/analyze_fit3d_domain_shift.py` — corrected `EXERCISE_TO_CLASS`,
  added `RECOMPUTE_CLASSIFICATION`/`_recompute()` to reflect the fixed
  pipeline without a full re-run.
- `FIT3D_UTILIZATION_PLAN.md` — Track B addendum pointing to the
  correction (original plan text left intact as historical record).
- `ROADMAP.md` — Phase C3 Track B correction addendum, full writeup with
  both root causes, both fix validations (Fit3D and RepCount), and the
  honest remaining gaps.
- `STATUS.md` — updated the domain-shift limitation line to reflect the
  corrected picture.
- `validation_results_fit3d/domain_shift_report.json` — regenerated by
  re-running the corrected script (gitignored directory, disk-only).
- This file.

## What's on disk, not committed

Everything above except the PDF/push from earlier in the session. Per
this project's standing git-safety norms, nothing was committed —
waiting on the user before staging/committing/pushing.

## What's next

- Commit decision needed for this session's code + doc changes.
- The out-of-taxonomy `pullup` bias (52%/0.59 avg conf) is a loose thread
  worth a closer look if Track B gets revisited — not urgent, below the
  script's own "concentrated" threshold, but not fully clean either.
- `hinge`/`lunge`/`curl`/`row` coverage remains a real, separate product
  gap (Part C of `Joule_Coach_End_Product.pdf` already lists this kind of
  thing under "what an early version must not promise") — needs either
  RepCount retraining with those classes added to the trained model's
  output list, or real gym footage, neither of which happened this
  session.
- Phase D (real gym footage) is still the actual next milestone and is
  still blocked on camera/gym access, same as every prior handover.
