# Joule Coach — Design Prototypes

Tracking log for member-app front-end concepts. We're generating several
independent prototypes/wireframes from different sources (Claude, Google
Stitch, possibly others), keeping all of them, and picking a direction at
the end rather than committing to the first one. This file is the index —
one entry per candidate, updated as each one lands. Screens/scope are
scoped to `PRODUCT_SPEC.md`'s MVP feature set unless noted otherwise.

Source content for all candidates: `PRODUCT_SPEC.md` (personas, MVP
feature list, tone/anti-patterns, screen descriptions) and the engine
docs it's grounded in (`STATUS.md`, `CAMERA_PLACEMENT.md`).

## How to add a candidate

1. Save the file (HTML export, image export, whatever the tool produces)
   into `design/prototypes/`, named `NN-source-shortname.ext` (zero-padded
   sequence number, e.g. `02-stitch-core-loop.html` or
   `02-stitch-core-loop/` for a multi-file export).
2. Add a row to the table below and a short entry in "Candidates" with
   what it covers and any notes worth remembering when comparing later.
3. If it's a live design tool link rather than an exportable file (e.g. a
   Stitch project URL), record the URL in the entry instead — the file
   list is best-effort, not the source of truth.

## Candidates

| # | Source | Screens covered | File / link |
|---|---|---|---|
| 01 | Claude (this session, 2026-08-24) | Check-in, live session, post-set report | `prototypes/01-claude-core-loop.html` |
| 02 | Google Stitch (user, 2026-08-24) | Onboarding, kiosk check-in, weekly plan builder, live session, post-set report, video library, adherence/progress (7 unique) | `prototypes/02-stitch/01-08-*.html` |
| 03 | Claude, Apple HIG skill (this session, 2026-08-24) | Onboarding (corrected capability list), kiosk check-in, live session, post-set report | `prototypes/03-apple-hig-core-loop.html` |

### 01 — Claude, core loop

Interactive HTML mockup (phone-frame, switch between 3 screens). Dark
equipment-console direction: Big Shoulders Display + IBM Plex Sans/Mono,
graphite/warm-white palette per `PRODUCT_SPEC.md` §3.2, solid/dashed
confidence badges implementing the spec's "confidence must be visible"
rule, skeleton-overlay as the signature visual element on the report
screen. User feedback: not a strong direction — didn't land visually.
Kept as a candidate for the final comparison anyway, and as a reference
for what content/behavior each screen needs to show (real coaching-cue
language, coverage disclosure, rep-by-rep strip, etc.) regardless of
which visual direction wins.
Published artifact (view-only, not the saved file):
https://claude.ai/code/artifact/2318654e-f7e1-4372-86b9-e902a1b49381

### 02 — Google Stitch, full screen set

Pulled via the Stitch MCP server (`stitch` local-scope server registered
last session; its tools only became callable after a fresh session start,
per that session's handover note). User's Stitch project: "Joule Coach
Member App" (`projects/7511907646849515592`, TEXT_TO_UI_PRO, built from
`design/stitch-prompt.md`), 8 files exported as standalone HTML/Tailwind
files into `design/prototypes/02-stitch/` — **`01` and `07` are
byte-identical duplicates** (verified via `diff`; same "What Joule Sees"
capability-disclosure screen under two different Stitch-generated
titles), so 7 unique screens in practice:

- `01-onboarding-capability-disclosure.html` — "Onboarding: Capability
  Disclosure" (= `07`, kept both, dedupe later if `design/` gets cleaned up).
  "What Joule Sees" support-matrix card, active/pending exercise lists,
  "CALIBRATION STEP 1 OF 3" — see flagged content issue below.
- `02-kiosk-checkin-confirmation.html` — "Kiosk Check-in Confirmation".
  Green checkmark, timestamp, assigned station ("Squat Rack 4"),
  telemetry-sync status line, small kiosk→rack location diagram.
- `03-weekly-plan-builder.html` — "Weekly Plan Builder". Despite the name,
  reads as a movement-library/protocol picker: "Trackable Protocol" cards
  (Barbell Back Squat, Conventional Deadlift, Bench Press, each tagged
  Lower/Compound/Hinge/Upper/Push) plus a separate "Pending Validation"
  section (Sit-ups, Plank) shown struck-through/disabled — the inverse of
  `01`'s capability list (correctly marks sit-ups unvalidated here, but
  still lists Deadlift as trackable).
- `04-post-set-report-hero.html` — "Post-set Report (Hero)". Skeleton
  overlay with a highlighted joint + "KINEMATIC DEVIATION: Left knee
  tracking inward on reps 5-6" callout, a per-rep color-coded strip
  (green/pink good-vs-flagged reps), text analysis summary, "Watch 40s
  fix-it demo" CTA — closest screen to candidate 01's own report screen,
  good side-by-side comparison point.
- `05-exercise-video-library.html` — "Exercise Video Library". Filter
  chips (All/Squat/Hinge/Press), grouped by pattern family with video
  thumbnails + skeleton-icon previews (Bilateral/Front/Split
  Squat, Overhead Squat, Conventional/Romanian Deadlift, Strict
  Press/Bench Press) and item counts per group.
- `06-adherence-progress-view.html` — "Adherence & Progress View". "82%
  Weekly Target" headline stat, an explicit honesty note ("1 session
  unobserved due to camera maintenance, data excluded from kinematic
  averages" — good alignment with the spec's coverage-disclosure
  principle), a Detected/Planned/Unobserved bar chart Mon–Sun, Kinematic
  Fidelity 94.2%, Volume Load 12,450 KG.
- `08-live-session-mid-set.html` — "Live Session (Mid-set)". Minimal HUD
  over a (placeholder) camera feed: rec indicator/timer, exercise name +
  rep count large-format, HR + bar-velocity metric pair, "STAY IN FRAME"
  warning bar with a manual "Step Back" control.

Design system Stitch generated (named "Joule Coach" in its own
`DESIGN.md`, embedded in the project): dark mode, Hanken Grotesk
(headline/body) + JetBrains Mono (data readouts), instrument-orange
accent (`#F45D01`) + confidence-green (`#2ECC71`), flat/no-shadow tonal
layering, 1px hairline borders, `0.25rem` roundness, explicit
solid-vs-dashed skeleton-overlay stroke rule for tracking confidence —
covers more ground than the brief mandated (brief deliberately left exact
hex/fonts open, see `stitch-prompt.md`) and independently arrived at a
similar "confidence must be visible" solid/dashed convention to candidate
01, from the same `PRODUCT_SPEC.md` §3.3 rule rather than copying it.
Covers 7 screens vs. candidate 01's 3 — broader MVP surface (onboarding,
plan builder, video library, adherence view) not built in 01 yet.
No user visual-feedback recorded yet — first impressions still open.

**Flagged content issue (not visual):** `01`/`07`'s "Supported Movements"
list marks Deadlift, Bicep Curl, Row, Overhead Press, and Lateral Raise as
ACTIVE, and Sit-ups as "in development." `03-weekly-plan-builder` repeats
the same overclaim by listing "Conventional Deadlift" as a trackable
protocol item, while — inconsistently — correctly marking Sit-ups
unvalidated (the opposite of what `01`/`07` show).

**Root cause found (2026-08-24, same session): this isn't a Stitch
mistake.** `PRODUCT_SPEC.md` §3.3 point 1 itself contains the exact same
claim, verbatim in spirit: *"Joule currently tracks: squat, deadlift,
curl, row, overhead press. It does not yet count sit-ups."* — almost
certainly what `stitch-prompt.md` (grounded in `PRODUCT_SPEC.md`)
propagated into these screens. `git log` confirms `PRODUCT_SPEC.md` was
written 2026-08-07 (`fb9427b`), *before* the confidence-gating session
(2026-08-11) and the lunge-heuristic recovery (2026-08-12) that
established the numbers that contradict it: Deadlift isn't a recognized
class at all (`hinge` was investigated and explicitly rejected); Row is
heuristic-fallback-only at 8%; Curl is heuristic-fallback-only at 41%;
Overhead Press/Lateral Raise map to Fit3D's Track B domain-shift finding
(trained on a different physical movement under the same label); Sit-ups
is actually one of the genuinely trained classes. The spec itself already
anticipates this — §4 Sprint 0 says to "finalize the MVP exercise list
against whatever Phase D actually confirms holds up" — so this is a stale
first draft, not a settled decision. **`PRODUCT_SPEC.md` §3.3 should be
updated** so future design work (and any other consumer of that doc)
stops inheriting the same stale claim. Not done as part of this session —
flagging for the user's call on whether/when to edit the product-strategy
doc itself.

### 03 — Claude, Apple HIG skill

Built after the root-cause finding above, using the newly-installed
`apple-design` skill for guidance rather than a general visual pass — read
`color.md`, `typography.md`, `layout.md`, `accessibility.md`, and
`materials.md` from the skill's HIG reference set before building. Same
4-screen core loop as candidate 01 (onboarding added specifically to
demonstrate the capability-list fix in place, not just describe it) —
onboarding, kiosk check-in, live session, post-set report — as an
interactive phone-frame mockup with a working screen switcher.

Deliberate departures from both other candidates, each traced to a
specific guideline or spec line:
- **Real system-font pairing**, not a custom web-font stack: `-apple-system,
  BlinkMacSystemFont` for UI/data (resolves to actual San Francisco on
  Apple hardware) paired with `ui-serif, "New York"` for headlines/coaching
  copy — Apple's own SF+NY pairing, which independently satisfies
  `PRODUCT_SPEC.md` §3.2's "characterful display face distinct from the
  data face" requirement without reaching for a Google Font.
- **Both appearances actually work**, not just dark mode — a real
  light/dark toggle on the mockup, with distinct (not just inverted) teal
  and red tints per appearance to hold contrast in both, per
  `color.md`/`accessibility.md`'s "supply light and dark variants... test
  in both" guidance. Candidates 01 and 02 are both dark-only.
- **Corrected 3-tier capability list** (tracked / early support / not
  yet) instead of the flat 2-tier active/pending split both other
  candidates used — lets "developing" claims (curl, lunge) stay honest
  without collapsing into either "yes" or "no." Uses shape (filled
  check / dashed circle / slashed circle) alongside color, not color
  alone, per `accessibility.md`'s color-blindness guidance.
- **Live session screen shows only the rep counter and a stay-in-frame
  cue** — no HR, no bar velocity, no skeleton overlay — a literal reading
  of §3.3's "minimal UI... rep counter and 'stay in frame' cue *only*...
  deliberately not a live form-accuracy overlay in MVP," stricter than
  candidate 02's live screen (which shows HR + velocity).
- **Report screen presented as an iOS sheet** (grabber handle, rounded
  top corners, dimmed scrim) rather than a full screen, literalizing
  §3.3's "the form report screen slides up automatically."
- 44×44pt minimum touch targets throughout, inset (not full-bleed)
  buttons per `layout.md`'s mobile guidance, and a `backdrop-filter` blur
  material on the live-session HUD bars per `materials.md`.

No user feedback recorded yet.
Published artifact:
https://claude.ai/code/artifact/bf0442c4-2957-4bb8-9181-72f54805a67f

## Decision

Not made yet. Revisit once 2+ candidates exist — compare against
`PRODUCT_SPEC.md` §3 (tone/visual identity direction) and the actual
screen requirements in §2.1, not just aesthetic preference.
