# Product Specification: Joule Coach — Camera-Native Personal Training for Smart Gyms

Written 2026-08-06. Expanded from the founder's one-line brief: "Smart gyms
where members don't need a human personal trainer — they pay a
subscription, and the gym's cameras + AI act as their personal trainer via
a companion app: real-time form/accuracy feedback per exercise, an in-app
workout plan builder with automatic adherence tracking, and a library of
sample/demo videos teaching correct exercise form."

This is a standalone strategic planning document for the human product/
engineering team. It is grounded in the current, real state of the
underlying Joule computer-vision engine (per `ROADMAP.md` / `STATUS.md` as
of 2026-08-06): component-level validation against RepCount, CMU Panoptic,
and Fit3D is done and credible; Phase D (real gym footage validation) is
the next engine milestone and has not yet run. The product plan below is
sequenced so the app can start being built in parallel with Phase D/E, but
its scope claims never outrun what the engine can actually promise on day
one. It is a companion document to `PRODUCT_ROADMAP.md` (the technical/
systems architecture side of the same plan).

---

## 1. Personas and Jobs-to-be-Done

### 1.1 Gym Member (primary persona) — three practical sub-segments

The "member" persona is not monolithic; the product needs to serve three
distinct relationships to the product honestly, especially because the
engine's coverage is exercise-specific and camera-layout-dependent at
launch.

**A. The New/Anxious Member** ("Never had a trainer, doesn't know if I'm
doing this right")
- JTBD: "Tell me, in the moment or right after, whether I'm about to hurt
  myself or waste my time, without the social cost of asking a stranger."
- Trust is the whole game for this segment — they will abandon at the
  first moment the app is confidently wrong.

**B. The Committed Self-Directed Member** ("I know the movements, I want
structure and proof I'm sticking to it")
- JTBD: "Build me a plan, hold me accountable to it with real data (not my
  own guesswork/self-report), and show me I'm progressing."
- This segment is the primary buyer of the adherence-tracking and
  analytics value proposition.

**C. The Data-Driven Advanced Member** ("I already train seriously, I want
the numbers")
- JTBD: "Give me joint-angle-level detail, asymmetry and fatigue trends
  over months, and let me export/compare — don't dumb this down."
- Lowest onboarding friction, highest expectation of accuracy and depth;
  also the segment most likely to notice and forgive known model
  limitations if the app is transparent about them.

### 1.2 Gym Owner/Operator (primary business persona)
- JTBD: "Differentiate my gym and justify a premium tier or higher price
  point, without hiring more PTs, while proving the system pays for itself
  in retention within a budget cycle."
- Secondary JTBD: "Know immediately if a camera goes down or a station is
  miscalibrated, before it silently degrades every member's experience for
  weeks."

### 1.3 Front-of-House / Floor Staff (supporting persona)
- JTBD: "When the app is wrong, confused, or a member is frustrated at the
  kiosk, give me a two-minute fix, not a support ticket queue."
- This role exists because a 100%-automated system with zero human backstop
  is where trust erodes fastest — floor staff are the manual override, not
  a redundant PT.

### 1.4 Remote Coach/Reviewer (premium, human-in-the-loop persona —
deliberately added)
- JTBD: "Let me spend my time on the 5% of cases that need a human —
  ambiguous form calls, injury-risk escalations, and plan customization
  for premium members — instead of watching every rep of every member."
- Why this role matters strategically: the brief promises members won't
  need "a human personal trainer," but the engine has real, named blind
  spots (sit-ups uncounted, bench press needs a side angle, mirrors are a
  blind spot, out-of-frame limbs break tracking). A lightweight
  human-review layer for premium tiers and for injury-risk escalations is
  what makes the "no human trainer needed" claim honest rather than
  reckless — it converts unhandled edge cases into a monetizable premium
  feature instead of a silent failure mode.

---

## 2. Feature Set (by persona, by priority)

Organizing principle: **MVP ships only what the engine has already
proven** (standing/unencumbered movements validated cleanly on Fit3D:
squat, deadlift, curls, rows, presses — squat carries a known larger error
band and should ship with a visible confidence caveat, not silence). Bench
press and sit-ups are explicitly *not* MVP claims. Mirrors are excluded by
installation rule, not by a feature.

### 2.1 MVP (Sprint 1–2 scope — "first pilot gym")

| # | Feature | Persona | Description & Acceptance Criteria |
|---|---|---|---|
| 1 | **QR/kiosk camera check-in** | Member, Staff | Member scans a personal QR code (or taps a phone-free kiosk badge) at a fixed check-in camera; system binds their name to a fresh Re-ID embedding for that visit (leverages the existing `/checkin` binding pattern). Acceptance: check-in confirmation appears within 3s; a failed match routes to a staff-assisted manual bind, never a silent misattribution. |
| 2 | **Guided session start ("what am I about to do")** | Member | Before a set, member selects the exercise from a *closed list* of currently-supported movements in-app (squat, deadlift, bicep curl, row, overhead press, lateral raise) — no free-text/open-world exercise entry in MVP, because the classifier's trained coverage is finite. Acceptance: unsupported exercises (e.g., sit-ups, bench press) are visibly labeled "Coming soon" in the picker, not hidden — sets expectations rather than producing a silent bad read. |
| 3 | **Post-set form report (near-real-time, not mid-rep live overlay)** | Member | Within 2–5 seconds of a set ending, member sees: rep count, per-rep depth/ROM validity, and a plain-language form score vs. the reference "good execution" signature, with the 1–2 biggest deviation cues (e.g., "knees tracking inward on reps 4–6"). Acceptance: every report explicitly states whether 3D (fused, higher-confidence) or 2D single-camera (lower-confidence) was used, never presented as equally certain. |
| 4 | **"Stay in frame" real-time cue** | Member | A simple, low-latency (not form-accuracy-dependent) in-gym signal — light/tone on an equipment-mounted indicator or a phone push — when the member's feet or body leave the calibrated camera volume mid-set, since full-body-including-feet-in-frame is a hard tracking requirement. Acceptance: this cue fires on frame-exit within one video frame's latency budget, independent of and faster than the form-scoring pipeline. |
| 5 | **Manual workout plan builder (template + custom)** | Member | Member assembles a weekly plan from a fixed library of supported exercises (sets/reps/target tempo). Acceptance: plan builder blocks adding unsupported exercises with an explanation, and flags any planned exercise whose home gym has no camera coverage for that station. |
| 6 | **Automatic adherence tracking** | Member, Owner | The app cross-references the member's plan against *actually-detected* sessions (check-in + classified exercise + counted reps), not self-report. Acceptance: a "planned vs. done" weekly view shows exact matches, partial completion (e.g., planned 4 sets, detected 3), and clearly separates "not detected" from "detected but below plan volume" — because a false "you skipped it" (e.g., camera outage, played it on an uncovered machine) is a worse failure than under-crediting silently. |
| 7 | **Exercise video library (curated demo set, matched to supported exercises only)** | Member | Short, side-by-side "reference vs. common mistakes" videos for exactly the exercises the engine currently scores. Acceptance: every video in the library maps 1:1 to an exercise the live-scoring system supports — no library entries for exercises the app can't yet evaluate, to avoid teaching a form the tracker can't confirm. |
| 8 | **Basic gym-operator dashboard** | Owner, Staff | Member roster, per-camera/per-station health (last-frame-received timestamp, calibration-drift warning), and today's session volume. Acceptance: a camera going dark for >2 minutes surfaces a dashboard alert and a staff push notification within that window. |
| 9 | **Subscription tier gating (technical, not just billing)** | Owner, Member | Base tier: check-in + tracking + reports + plan builder + adherence. Premium tier: adds Remote Coach/Reviewer escalation access and deeper analytics (Section 2.2/2.3). Acceptance: tier state gates feature visibility, not feature *accuracy* — every member, regardless of tier, gets an equally honest report on what was and wasn't measured. |
| 10 | **Session/plan reminders (notifications)** | Member | Push/SMS reminder for a planned session, and a same-day nudge if a planned session hasn't been detected by a configurable cutoff. Acceptance: nudges never claim a missed session with more confidence than the underlying detection actually has (e.g., must account for "camera outage" vs. "did not attend"). |

### 2.2 V1 (Sprint 3–4 scope — "pilot renewal / expansion")

| # | Feature | Persona | Description |
|---|---|---|---|
| 11 | **Injury-risk/fatigue alerts** | Member, Coach | Surfaces the engine's set-level signals (fatigue, ROM degradation, tempo collapse, asymmetry) as trend cards, not real-time medical claims. A sustained multi-session asymmetry or ROM-degradation trend routes to the Remote Coach queue for human review, not an automatic diagnosis. |
| 12 | **Bench press support (side-camera stations only)** | Member, Owner | Enabled *only* at stations physically installed with a side-camera angle, per the engine's confirmed head-on-counting weakness. The plan builder and video library unlock bench press only for members whose home gym has a qualifying station; other gyms see it correctly greyed out with the reason stated. |
| 13 | **Progress analytics dashboard** | Member | Multi-session trend charts: joint-angle-error trend, rep-volume trend, form-score trend per exercise, streaks. Segmented so the Advanced persona (1.1C) gets raw data export while the New/Anxious persona (1.1A) gets a simplified "you're improving" summary — same data, different framing per user preference. |
| 14 | **Remote Coach review queue & tooling** | Coach, Member (Premium) | A reviewer-facing queue of flagged sessions (low-confidence classifications, escalated risk signals, premium-tier plan-customization requests) with the original clip/skeleton overlay and the engine's own confidence scores, so a human spends time only where the model is uncertain, not on every session. |
| 15 | **Gym-operator usage & business analytics** | Owner | Station utilization heatmaps by hour, class of exercise, adherence rates across the membership base, churn-risk flags (members whose detected sessions have dropped off vs. their plan). |
| 16 | **Mirror/blind-spot install compliance tooling** | Owner, Staff | A guided camera-placement checklist tied directly to the engine's known mirror blind spot and feet-in-frame requirement (mirrors banned from any calibrated camera's field of view; a dashboard warning if a station's live feed frame includes an uncalibrated reflective surface, flagged for staff to physically re-aim or mask). |

### 2.3 V2+ (Sprint 5+ scope — "multi-site")

| # | Feature | Persona | Description |
|---|---|---|---|
| 17 | **Sit-up / floor-exercise counting** | Member | Ships only once the engine's hip-driven rep counter (currently a named backlog item, deliberately counting zero today) exists and is validated — the app must not promise this earlier. |
| 18 | **Multi-site operator console** | Owner (chains) | Cross-site benchmarking, fleet-wide camera health, per-site unit economics. |
| 19 | **Coach marketplace** | Coach, Member | Premium members can request a specific reviewer's ongoing oversight (paid add-on), turning the human-in-the-loop layer into incremental revenue rather than pure cost. |
| 20 | **Population-level injury-risk research view** | Owner, (opt-in) | Anonymized, aggregate trend reporting across a gym's membership for movement-pattern risk, useful to owners for equipment/programming decisions — strictly aggregate, opt-in, no individual medical claims. |
| 21 | **Self-serve gym onboarding & Jetson edge installer** | Owner | Reduces white-glove install dependency once E2 (Jetson port) lands — a guided calibration wizard replacing manual `tools/calibrate.py` runs. |

---

## 3. Design Direction

### 3.1 Tone

**Calibrated confidence, not hype.** This product's single biggest design
risk is overclaiming certainty it doesn't have — a member who's told
"perfect form!" on a rep the system was actually unsure about, and then
gets hurt, is the failure mode that kills trust and the business. Every
screen that shows a score, a count, or an alert should carry a visible,
low-friction confidence signal (not a scary disclaimer wall — a small,
consistent visual language: solid outline = high-confidence 3D fused read,
dashed outline = single-camera 2D estimate, greyed = not enough data). The
tone is closer to a sharp, honest strength coach than a gamified fitness
app — direct, specific, occasionally warm, never cutesy about safety.

**Explicit anti-patterns to avoid:**
- No "AI is always right" theater — no fake precision (e.g., "form score:
  94.7%") where the underlying error band doesn't support that precision.
  Round to bands or plain-language tiers instead.
- No generic stock-photo gym imagery; no gradient-mesh hero sections; no
  illustration-heavy empty states that feel like a SaaS landing page. This
  product lives on a gym floor and inside a locker-room five-minute glance
  — it should feel like a piece of athletic equipment's UI, not a
  consumer app trying to look "modern."
- No dark-pattern streak-shaming or guilt notifications for missed
  sessions — the adherence feature's credibility depends on being
  scrupulously fair.

### 3.2 Visual Identity

- **Color palette**: charcoal/graphite base (`#1c1f22` dark surface,
  `#f4f2ee` warm-white light surface — avoid pure white/pure black), a
  single confident accent — a saturated amber (`#f5a623`) reserved *only*
  for actionable coaching cues and alerts, and a cool teal (`#2a9d8f`)
  reserved *only* for "confirmed good" states (high-confidence match to
  reference form). No purple/blue AI-slop gradients. Risk/injury alerts
  use a restrained brick red (`#c0392b`), never neon.
- **Typography**: a workhorse grotesque for numbers and data (tabular
  figures) for all metrics/tables, paired with a slightly more
  characterful display face for headlines and coaching cues, so the
  "human coach voice" moments feel distinct from raw data.
- **Layout philosophy**: dense-but-legible dashboard for the member's
  progress view and the operator console (this is a data product, not a
  lifestyle app); airy, single-focus screens for the in-the-moment
  gym-floor flows (check-in, post-set report) where the member is
  mid-workout and needs one clear read at arm's length, not a dashboard.
- **Visual identity signature**: use the actual skeleton/joint-angle
  overlay as a first-class design element throughout — not hidden in a
  "technical" tab. A stylized, simplified skeleton line-drawing (derived
  from the real pose data, not a generic icon) becomes the app's visual
  signature on the report screen, the video library thumbnails, and even
  the loading state. This is the one piece of visual identity a copycat
  fitness app can't fake — it's literally the product's real output.
- **Inspiration**: the data density and typographic confidence of
  Strava's segment/effort screens; the calm, non-gamified tone of Oura's
  trend charts; the physical/architectural feel of a well-designed gym
  equipment console (Technogym's console UI).

### 3.3 Key Screens & Flows

**Onboarding / Check-in**
1. First-time: account creation, a short liability/limitations disclosure
   written in plain language ("Joule currently tracks: squat, deadlift,
   curl, row, overhead press. It does not yet count sit-ups. Bench press
   is supported only at marked stations.") — an actual onboarding card,
   not buried legalese, because setting the coverage boundary early
   prevents mid-session disappointment later.
2. A one-time reference photo/short clip capture for the Re-ID embedding,
   taken at the check-in kiosk with clear on-screen framing guides (also
   where "keep your full body including feet in frame" gets taught once,
   visually).
3. Every subsequent visit: QR/badge tap at the kiosk to bind the visit,
   confirmation within 3 seconds, and a staff-assisted manual bind
   fallback one tap away.

**Live Session View** (on the member's own phone, held or set aside)
- Pre-set: exercise picker (closed list, greys out unsupported items with
  the "why"), target sets/reps pulled from today's plan if one exists.
- During set: minimal UI — a large, glanceable rep counter and the
  "stay in frame" cue only. Deliberately *not* a live form-accuracy
  overlay in MVP, because true low-latency mid-rep scoring isn't
  validated yet — promising live corrective feedback the pipeline can't
  yet deliver at rep-speed would be the single most damaging overclaim
  this product could make. Upgraded to true live overlay in V1/V2 once
  Phase D/E latency work is validated on real hardware.
- Immediately post-set: the form report screen (Feature 3) slides up
  automatically.

**Post-Session Report**
- Hero element: the stylized skeleton overlay for the single worst-scoring
  rep of the set, annotated with the specific deviation, next to the
  reference signature for comparison.
- Below: rep-by-rep strip (color-coded by validity/confidence), then
  plain-language summary, then a single clear next-action ("watch the
  40-second row demo" or "logged, no action needed").

**Plan Builder**
- Calendar-week grid, drag exercises from the supported-exercise library
  onto days; each exercise card shows its own confidence/coverage badge.
  Templates pre-populate from supported exercises only, editable.

**Video Library**
- Grid organized by movement pattern (squat, hinge, press, pull,
  curl/isolation), not muscle-group marketing copy — each entry: reference
  clip with skeleton overlay, 2–3 common-mistake side-by-side clips, and a
  direct link to "try it now."

**Progress Dashboard**
- Persona-adaptive: New/Anxious members default to a simplified "this
  month" summary; Advanced members can toggle a "raw data" mode exposing
  per-joint angle trends and CSV export.

### 3.4 Physical Gym-Floor Experience
- **Entrance kiosk**: a wall-mounted tablet for QR/badge check-in and the
  one-time reference capture only — not a full-service kiosk.
- **Station-mounted indicator, not a screen, for MVP**: a small
  unobtrusive light/LED strip giving the in-frame/out-of-frame cue and a
  "recording active" state — cheap, low-latency, doesn't compete with the
  phone app for attention mid-set. A full equipment-mounted display is a
  V2+ consideration.
- **Staff exception panel**: a lightweight front-desk tool showing today's
  failed check-ins, dark cameras, and any ambiguous Re-ID match — the
  human backstop made concrete.

---

## 4. Sprint Plan — from "pipeline validated" to "multi-site product"

This plan assumes the engine team's own Phase D (real-footage validation)
and early Phase E (RTSP sync, Jetson port, kiosk integration) run in
parallel with, and gate, specific product sprints below — they are not
sequential blockers on everything, but Sprint 1's pilot cannot go live on
real members until Phase D's findings are in.

### Sprint 0 — Foundation (parallel with engine Phase D)
- **Goal**: de-risk the business and product assumptions while the engine
  team runs real-footage validation.
- **Scope**: pilot gym selection and contract; 8–12 structured interviews
  across all three member sub-segments plus gym owners on pricing
  tolerance and trust concerns; finalize the MVP exercise list against
  whatever Phase D actually confirms holds up on real gym footage (not
  just Fit3D); draft the plain-language coverage-limitations copy for
  onboarding; camera/station install plan for the pilot site using the
  existing `CAMERA_PLACEMENT.md` rules.
- **Definition of done**: signed pilot gym; Phase D findings reviewed and
  MVP exercise list locked; install plan approved.

### Sprint 1 — Walking Skeleton
- **Goal**: prove the minimum real loop works end to end for real members
  at the pilot gym: check in, do a supported lift, get an honest report.
- **Scope**: Features 1–4, 7 (subset — exercises the pilot's install
  supports), staff exception panel. No plan builder yet — plans are
  staff-assisted/manual. Single-camera or minimal fused stations only.
- **Definition of done**: 20+ real check-ins by real pilot members; staff
  shadow-validates a sample of app reports against their own judgment;
  zero silent misattributions.

### Sprint 2 — Plan & Adherence
- **Goal**: deliver the two pieces genuinely novel versus a plain
  form-feedback app — the plan builder and *verified* adherence tracking.
- **Scope**: Features 5, 6, 8, 9, 10; full curated video library for the
  confirmed exercise set.
- **Definition of done**: a cohort of pilot members runs a full planned
  week; adherence report cross-checked against a manual staff log, with a
  measured false-"missed"-session rate below an agreed threshold
  (Section 5).

### Sprint 3 — Risk, Analytics, Trust
- **Goal**: move from "does the loop work" to "does this feel like a real
  coach, not just a rep counter."
- **Scope**: Features 11, 13, 16; refine confidence-badge visual language
  across all existing screens based on Sprint 1–2 member feedback.
- **Definition of done**: member survey shows form-feedback and adherence
  features rated as trustworthy and useful; no unresolved mirror/blind-spot
  install issues at the pilot site.

### Sprint 4 — First Paying Pilot Gym Live
- **Goal**: convert the pilot from a validation exercise into a real,
  billed relationship.
- **Scope**: Feature 12 (if the pilot has a side-camera bench station),
  Feature 14 (Remote Coach queue, even one part-time reviewer), subscription
  billing turned on for real, operator dashboard (Feature 15 partial)
  presented to the owner as a renewal decision point.
- **Definition of done**: pilot gym owner signs a paid renewal; member
  subscription conversion rate and 60-day retention meet Section 5
  thresholds.

### Sprint 5 — Second Site & Hardening
- **Goal**: prove the product generalizes past one hand-tuned installation.
- **Scope**: full operator dashboard (Feature 15), a second pilot site with
  a different physical layout, RTSP live-stream support (depends on engine
  Phase E1), install-checklist tooling made self-guided (partial Feature 21).
- **Definition of done**: second site live with materially less
  white-glove engineering time than site one; cross-site camera-health
  monitoring from one console.

### Sprint 6 — Multi-Site Product
- **Goal**: ship the features that only make sense with more than one
  site's worth of data and revenue.
- **Scope**: Features 17–21 as the engine's backlog items land; multi-site
  operator console; coach marketplace as an incremental revenue line.
- **Definition of done**: a repeatable sales/install motion for a new gym
  site with documented cost/timeline, and positive per-site unit
  economics.

---

## 5. Evaluation Criteria (product-level, not engine-level)

The engine's own accuracy benchmarks (RepCount MAE, Panoptic/Fit3D
joint-angle error) are necessary but not sufficient — they say the
pipeline is technically accurate, not that the *product* is working.

### 5.1 Trust & Perceived Usefulness (member-facing)
- Post-report micro-survey, sampled after a meaningful fraction of
  sessions. Target: sustained majority-positive by end of Sprint 3,
  tracked per member sub-segment separately.
- **Leading indicator**: rate at which members re-open the post-set report
  screen after the first glance (a proxy for "I trust this enough to read
  it carefully").

### 5.2 Adherence-Tracking Accuracy vs. Ground Truth
- During Sprint 2's pilot cohort, run a parallel manual staff log and diff
  it against the app's automatic adherence record. Track separately: (a)
  false "session missed" rate (the costlier error — must be near-zero),
  and (b) false "session completed" rate. A false-missed rate above a low
  single-digit percentage should block Sprint 4's go-live.

### 5.3 Engagement & Retention
- Weekly active usage of the plan/report loop among subscribed members.
- 60- and 90-day member retention for app subscribers vs. the pilot gym's
  own historical baseline retention — the real business case rests on
  this delta.
- Churn-risk flag precision (Feature 15): of members flagged as at-risk,
  what fraction actually cancel vs. false alarms.

### 5.4 Gym-Operator Willingness to Renew / Expand
- Does the pilot gym owner convert from pilot to paid (Sprint 4 gate), and
  does a second, *independently sourced* gym sign on (Sprint 5 gate) — the
  second sale is the real test of whether this generalizes.
- Qualitative: does the owner use the operator dashboard unprompted, or
  does it sit unused.

### 5.5 Unit Economics per Site
- Install/hardware cost amortized against subscription revenue at
  realistic attach rates.
- Ongoing cost per site: compute (edge vs. cloud inference cost per
  member-session), Remote Coach staffing cost per flagged session,
  support/staff-exception load.
- Target: a defined payback period on install cost, validated with
  Sprint 4's real pilot numbers rather than assumed.

### 5.6 Safety & Failure-Mode Rate
- **Mirror/phantom-duplicate incident rate**: any real installation event
  where a mirror produced a duplicate tracked person or contaminated a
  real member's reading, post-install-checklist. Target near-zero.
- **Out-of-coverage silent failure rate**: any case where a member
  attempted an unsupported exercise and the app produced a confident-
  looking but wrong read instead of correctly declining/flagging it. Must
  be effectively zero — a design/gating bug, not an accuracy limitation.
- **Injury-risk alert precision/recall**, once enough Sprint 3+ data
  exists — always framed as directional, never clinical or medical-grade.

---

## 6. Honest Scope Boundary (restated as a single source of truth)

Because this is the section most likely to be quietly eroded under
launch-date pressure, it is restated plainly here:

- **Ships at MVP**: squat, deadlift, bicep curl, row, overhead press,
  lateral raise — standing/unencumbered movements, the set the engine has
  actually validated cleanly. Squat ships with a visibly wider confidence
  band than the others, not silently equal.
- **Does not ship at MVP, and the app must say so, not hide it**: sit-ups
  (engine counts zero today), bench press at any station without a
  physically installed side camera, any exercise where a mirror is in a
  calibrated camera's field of view (excluded by install rule, not
  detection), any session where the member's feet leave frame (flagged in
  real time via the station indicator, not silently mis-scored).
- **Real-time is redefined honestly as near-real-time**: mid-rep
  live-overlay coaching is a V2+ feature gated on Phase E latency work;
  MVP's "real-time feedback" promise is a same-set, immediately-post-rep
  report — still meaningfully faster and more specific than a human
  trainer glancing over occasionally.
