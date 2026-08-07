# Handover 7 — Joule

Session date: 2026-08-06/07. Read `HANDOVER6.md` first for the Phase C1 /
single-subject Fit3D context this picks up from. Note: between HANDOVER6
and this session, an untracked-by-any-handover session did C2
(`CAPTURE_PROTOCOL.md`), dropped C4 (Sussex floor plan no longer the
target — commit `ab2d908`), and wrote `FIT3D_UTILIZATION_PLAN.md`
(commit `de2a3e7`), which is the plan this session's Fit3D batch work
executes. This session had two unrelated threads: (1) a new,
forward-looking productization strategy deliverable, and (2) finishing
the Fit3D full-utilization batch validation that was already running in
the background when the session started.

## Thread 1 — Post-validation product strategy (new scope, not in `ROADMAP.md`'s A–E phases)

The user asked for a strategic plan for turning the validated pipeline
into an actual "smart gym" product (subscription, camera-based personal
training, in-app plan builder with adherence tracking, exercise video
library) — explicitly requesting the `planner` and `gan-planner`
agents/skills be used.

1. Ran both agents in parallel. `gan-planner` completed cleanly on the
   first pass. `planner` was cut off mid-run by a connection error after
   only reading the docs — resumed via `SendMessage` to the same agent
   (not a fresh spawn) and it completed the full deliverable on retry.
2. Wrote both outputs to the repo as new top-level docs, matching this
   project's existing convention of committing planning docs
   (`ROADMAP.md`-style):
   - **`PRODUCT_SPEC.md`** (from `gan-planner`) — personas (including a
     deliberately-added "Remote Coach/Reviewer" human-in-the-loop role,
     needed to make the "no human trainer" pitch honest given the
     engine's real gaps), MVP/v1/v2+ feature tables, design direction,
     a 7-sprint plan from "pipeline validated" to "multi-site," and
     evaluation criteria.
   - **`PRODUCT_ROADMAP.md`** (from `planner`) — a Phase F–L continuation
     of `ROADMAP.md`'s existing phase lettering. Every claim traces to a
     specific file/line actually read in this codebase (e.g. `src/
     dashboard.py`'s unauthenticated `0.0.0.0` HTTP surface, `src/
     reid.py`'s session-only embedding design, the measured 0.22s/frame
     4-camera throughput). Flags 4 "XL" risks (real-gym accuracy,
     edge-hardware throughput, cross-visit identity, biometric-data
     compliance) and 21 named technical/legal risks, with an explicit
     "what an MVP can and cannot honestly promise" section.
3. User asked to verify both complete and produce a presentable PDF.
   Built a Python script (`build_pdf.py`, scratchpad-only, not committed)
   that renders both `.md` files via `markdown` + a print stylesheet into
   one HTML doc with a cover page, TOC, and an executive summary I wrote
   to bridge the two parts, then converts to PDF via headless Microsoft
   Edge (`msedge --headless=new --print-to-pdf` — plain Chrome refused to
   run headless because an existing Chrome session was already open and
   intercepted the launch; Edge doesn't have that problem). Saved as
   `Joule_Coach_Strategy.pdf` in the repo root.
4. **User reported overlapping text on the first PDF.** Diagnosed by
   actually rendering pages to PNG with `pymupdf` (`pip install pymupdf`)
   and reading them — not guessed. Root causes, both real CSS bugs, not
   guesswork:
   - A global `h1 { page-break-before: always }` rule (meant for section
     headers deep in the document) was also matching the cover page's
     `<h1 class="title">`, silently splitting the cover's content across
     two pages and colliding with the table of contents.
   - A defensively-added `overflow: hidden` on the cover container was
     interfering with Chromium's print pagination, clipping content
     rather than flowing it.
   - Also replaced the cover/part-divider layout's fragile
     fixed-height-flexbox-with-`justify-content:space-between` pattern
     with plain block flow + padding, which is structurally unable to
     overlap (no absolute positioning, no negative margins) regardless of
     exact spacing — the more defensible fix, not just patching the two
     bugs found.
   - Re-rendered and visually re-verified every distinct page type (cover,
     TOC, executive summary with its ASCII sequencing diagram, a
     part-divider transition, dense tables, code-heavy technical
     sections, the final appendix) before calling it done. 34 pages,
     clean throughout.

## Thread 2 — Fit3D full-utilization batch (Tracks A/B/C)

**Important context**: the batch job (PID 1921, `.venv` python) was
**already running** when this session started — launched in whatever
session actually executed step 1 of `FIT3D_UTILIZATION_PLAN.md`'s "Plan
for tomorrow." This session's role was monitoring it to completion and
then running the two dependent analysis scripts that hadn't been run
against the finished data yet.

1. Checked progress repeatedly over the session as the user asked for
   updates: 52% → 76% → 83% → **100% (224/224 clips, zero failures/empty/
   missing)**, finishing around 02:38, roughly 7h20m wall-clock from a
   19:14 start, using the batch driver's resumability + modest
   parallelism across subjects (`tools/validate_fit3d_batch.py`).
2. Along the way, ran a live demo for the user on a completed subject's
   footage (s03 squat, one camera, chosen specifically because s03 was
   already fully processed by the batch — no read contention) via
   `pipeline.py --dashboard --visualise`. Result: 8/8 reps counted
   correctly with real per-rep coaching feedback (tempo, trunk lean,
   L/R asymmetry, ROM). Output in `results/demo_squat_s03/`
   (gitignored, disk-only).
3. Once the batch finished, ran the two Track B/C scripts that consume
   its output — `tools/analyze_fit3d_domain_shift.py` and `tools/
   analyze_fit3d_rig_geometry.py`. Both had stale output from before the
   full batch existed; both regenerated fresh, real findings:
   - **Track A (batch_report.json)**: mean 10.1° / median 6.2° across all
     8 subjects × 28 exercises, ~1.16M joint-frame samples — consistent
     with the original 1-subject pass but now statistically solid.
     **s10 flagged as an unexplained outlier** (13.0° mean, normal 5.8°
     median — a fatter error tail on some subset, not root-caused yet).
   - **Track B (domain_shift_report.json)**: classifier domain-shift
     confirmed severe at full scale, worse than the small sample
     suggested — 0% accuracy on press/raise/situp, confidently wrong
     (e.g. press → "pullup" 88% of the time at 0.68 avg confidence), not
     just low-confidence hedging. Out-of-taxonomy negative controls
     scatter with no dominant wrong answer — a good calibration signal.
     Diagnostic only, per the existing Fit3D validation-license
     constraint (no fine-tuning on this data).
   - **Track C (rig_geometry.json)**: Fit3D's real 4-camera rig is
     bimodal (~47°/~132–133° adjacent gaps), **0 of 32 gaps** inside
     `CAMERA_PLACEMENT.md`'s recommended 60–90° band, yet still
     triangulated at the same 10.1° mean as the rest of the dataset —
     evidence the 60–90° guidance is a good default, not a hard cutoff.
4. Documented all three tracks' results in `ROADMAP.md` Phase C3 (new
   dated subsection, matching the existing evidence-traced style), then
   propagated the two most externally-relevant findings outward:
   - `STATUS.md` — updated the Fit3D headline number from the old
     1-subject figures to the full-scale 10.1°/6.2°, and added the
     classifier domain-shift finding as a new honest limitation.
   - `CAMERA_PLACEMENT.md` — added the Track C caveat to rule 4's 60–90°
     spacing guidance directly, so whoever plans a real install sees it
     in context rather than only in `ROADMAP.md`'s narrative.

## Phase C status (per `ROADMAP.md`)

- **C1, C2**: done (prior session, not this one).
- **C3**: Fit3D half now complete at full dataset scale across all three
  planned tracks (was previously 1 subject / 7 exercises). M3GYM still
  pending, user submitting independently.
- **C4**: dropped (prior session).
- Phase C is now effectively closed except M3GYM access, which is
  outside this project's control.

## What's on disk, not committed

- `PRODUCT_SPEC.md`, `PRODUCT_ROADMAP.md`, `Joule_Coach_Strategy.pdf` —
  new this session, untracked. `ROADMAP.md`, `STATUS.md`,
  `CAMERA_PLACEMENT.md` — modified, unstaged.
- `tools/analyze_fit3d_domain_shift.py`, `tools/
  analyze_fit3d_rig_geometry.py`, `tools/validate_fit3d_batch.py` — were
  already untracked at session start (written in the prior, un-handed-off
  session); still untracked now.
- `validation_results_fit3d/` — fully gitignored as a whole directory
  (unlike the earlier single-subject pass, where `report.json` was
  force-committed as a small auditable artifact). The three fresh
  aggregate reports are small and arguably worth the same force-commit
  treatment: `batch_report.json` (484K), `domain_shift_report.json` (4K),
  `rig_geometry.json` (16K). Not force-committed this session — nobody
  asked for it, flagging as a clear next step instead of assuming it.
- `results/demo_squat_s03/` — gitignored, disk-only, ~19MB including the
  annotated MP4. Fine to delete if disk space matters; easily
  regenerable from the same Fit3D clip.
- `build_pdf.py` and intermediate Chrome/Edge profile dirs — scratchpad
  only, not part of the repo, already cleaned up.

## What's next

- **Commit decision needed**: none of this session's file changes are
  committed yet (docs edits, new product docs, PDF, or the three tools/
  scripts). Ask before committing/pushing, per this project's standing
  git-safety norms — nothing here was auto-committed.
- The s10 outlier in Track A (13.0° mean vs. a 8.7–10.2° range elsewhere)
  is a loose thread — worth a targeted look at which specific
  exercises/frames drive it before treating the full-scale Fit3D number
  as fully understood, though it doesn't change the headline figure's
  validity.
- Phase D (real gym footage) remains the actual next major milestone and
  is still blocked on camera/gym access — everything in Phase C,
  including this session's full-scale Fit3D work, exists to de-risk that
  first real capture session, not replace it.
- The product strategy docs (`PRODUCT_SPEC.md` / `PRODUCT_ROADMAP.md` /
  the PDF) are a planning deliverable for the human team, not yet
  actioned — no engineering work against Phase F onward has started.
