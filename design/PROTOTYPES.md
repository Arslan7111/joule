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

Logo exploration is a separate track, indexed in `design/logo/README.md`
(13 marks across two rounds as of 2026-08-27) rather than in this file.

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
| 04 | Claude, 5 design skills (2026-08-27) | Post-set report, movement picker, live session, station check-in, week/adherence (5) | `prototypes/04-lab-report/index.html` |

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

### 04 — Claude, five design skills, "lab report"

Built 2026-08-27. Five screens, standalone HTML, no build step.
Screenshots alongside the file (`desk-*.png`, `mobile-*.png`).
**Dark-committed**, with a working light mode behind the toggle.

Skills, and honestly which did what. First pass used `impeccable`
(pbakaus) for the concept seed and craft floor, `frontend-design`
(Anthropic) for the departure from the category default,
`ui-ux-pro-max` (nextlevelbuilder) for the typography database, and Emil
Kowalski's `emil-design-eng` for the motion rules. **`taste-skill`
(Leonxlnx) was not used in the first pass** despite being claimed;
applied properly in a second pass, which forced the dark rebuild below.

`taste-skill` §13 declares itself out of scope for "dashboards / dense
product UI", which this report screen is, so only its universal rules
were applied. Those rules caught five real defects in the first pass:

- **§9.G em-dash ban** (the skill calls it its most-violated tell):
  14 em-dashes in visible copy. All removed, including the one in the
  ghost cell, now a drawn 1px mark rather than a dash character.
- **§4.11 Page Theme Lock**: the live-session screen inverted to dark
  inside an otherwise light page. Resolved by going dark throughout.
- **§9.F middle-dot rationing** (max 1 per line): `SET 3 OF 4 · 80 KG ·
  09:41 · RACK 3` carried three. Now one per line everywhere.
- **§9.F no section-number eyebrows**: the sheet index was numbered
  01 to 05, but ordered by interest rather than by the actual flow, so
  the numbers encoded nothing true. Numbers dropped.
- **§4.5 interactive state cycles**: no loading or empty states existed.
  Added a skeleton read-state whose shapes match the final layout, with
  a live counter, dramatizing the 2 to 5 second window §2.1 promises.

Second-pass changes beyond the skill audit:

- **Answer-first information design.** The report now opens with the
  verdict and the coaching cue, then the figure as proof, then the
  scrubbable rep strip, then the plane panels, then the method. The
  first pass opened with charts and made the reader hunt for the finding.
- **A real elevation ladder** rather than one flat ground: `#121416`
  page, `#1c1f22` (the spec's pinned dark surface) for the device,
  two raised tiers above it, and a 1px top-edge highlight on every
  raised surface so panels read as stacked material.
- **The rep strip is now draggable**, not click-only, which is what the
  "one control drives the whole document" claim actually required.
  Verified: dragging across it moves the figure, all three plane traces
  and every readout continuously, and correctly refuses to land on the
  ghost cell.

**Direction: a clinical gait-analysis report**, not a fitness dashboard.
Chosen via impeccable's `concept-seed` (seed `32a412bb`), which assigns a
randomised index into your own ranked list specifically to break the
model's ranking rut — it landed on candidate 3 of 7. The seven grounded
candidates were drawn from the audience's world: gym equipment console
(the brief's own literal picture), powerlifting meet refereeing,
**biomechanics lab report**, structural engineering drawing, surveying
field notes, PT goniometer chart, Marey chronophotography.

Why the assignment holds up rather than merely being obeyed:
- The **shaded normative corridor** is already the scientific convention
  for exactly this product's hardest design problem — `PRODUCT_SPEC.md`
  §3.1's "every screen that shows a score must carry a visible confidence
  signal." A trace inside the corridor is a good rep; a trace leaving it
  is the deviation, located exactly. No invented "form score: 94.7%".
- **Sagittal / frontal / transverse panels** make the layout itself argue
  the unique mechanism. The frontal panel's gutter is stamped `3D ONLY`
  because knee valgus is physically invisible to a single camera — the
  one thing a phone-based competitor cannot reproduce.
- **Appearance: dark committed, light available.** The first pass shipped
  light-committed, arguing from the use scene in `PRODUCT.md` (a brightly
  lit gym floor, read at arm's length). The user overrode that: dark is
  the preference, so dark is now the designed-for mode and light is a
  fully-built alternative behind the toggle. Worth noting the argument
  for light still stands on the gym floor, so this is a preference call
  rather than a settled one, and both modes are verified at AA.

Deliberate departures:
- **`PRODUCT_SPEC.md` §3.2's pinned palette is honoured exactly**
  (`#f4f2ee` / `#1c1f22` / amber `#f5a623` / teal `#2a9d8f` / brick
  `#c0392b`), but amber and teal are used as *marks only* — they fail
  4.5:1 as text on paper, so darkened variants (`#8a5a06`, `#1d6f66`)
  carry the same signal in type. Same semantics, contrast held.
- **Zero border-radius anywhere in the UI**, every line a 1px rule, and
  states rendered as printed marks rather than filled chips.
- **Type: Archivo** (variable width + weight, tabular figures) for all
  measurement, **Petrona** for the clinician's-interpretation prose only.
  Deliberately avoids IBM Plex / JetBrains Mono / Big Shoulders / SF+NY
  already spent on candidates 01–03, and the Space Grotesk / Space Mono
  defaults.
- **The skeleton is restored to first-class status** per §3.2's
  "visual identity signature" requirement — a front-view figure at the
  deepest point, with a teal plumb showing where the knee should track
  and an amber dimension line measuring the actual gap. It implements
  §3.3's "worst rep annotated with the deviation, next to the reference
  signature for comparison" literally. The same quantity appears at three
  scales: figure, frontal panel, rep-strip cell.
- **Honest absence is drawn, not omitted.** Attempt 9 (feet left the
  calibrated volume) occupies a dotted ghost cell in the rep strip;
  Thursday's camera outage is a dotted ghost bar excluded from averages
  in both directions; the dead camera at check-in uses the same grammar.
- **Not-yet-supported movements are ruled through**, not greyed out.
- Motion is one authored moment: the three plane traces draw themselves
  in on arrival, staggered 70ms. Scrubbing the rep strip is instant —
  per Emil Kowalski's frequency rule, a control used tens of times per
  session should not animate. `prefers-reduced-motion` respected.

**Capability list is the corrected one** (`STATUS.md`, not the stale
§3.3/§6): squat and push-up tracked; curl, lunge and bench press as
"early support" with their real recall figures; deadlift, row, overhead
press and sit-up struck through with reasons. Also see `PRODUCT.md` at
the repo root, written this session as impeccable's product-truth
artifact — it carries the capability table and marks §3.3/§6 as stale.

No user feedback recorded yet.

## Decision

Not made yet. Revisit once 2+ candidates exist — compare against
`PRODUCT_SPEC.md` §3 (tone/visual identity direction) and the actual
screen requirements in §2.1, not just aesthetic preference.
