# PRODUCT.md — Joule Coach

Durable product truth for design work. Companion to `PRODUCT_SPEC.md`
(strategy, personas, sprint plan) and `STATUS.md` (engine ground truth).
Where this file and `PRODUCT_SPEC.md` disagree on what the engine can
actually do, **this file wins** — see "Capability truth" below.

## What it is

Joule Coach is camera-native personal training for smart gyms. The gym's
fixed, calibrated cameras watch a member lift; a computer-vision engine
counts reps, measures joint angles in 3D, and returns a form report
seconds after the set ends. Members pay a subscription instead of hiring
a personal trainer. There is no wearable, no phone-propping, no manual
logging — the room is the sensor.

## The unique mechanism

Multi-camera DLT triangulation produces **true 3D joint angles** from 2+
calibrated views — including frontal-plane knee valgus, which is
physically invisible to any single camera. Validated at 3.7° mean error
against CMU Panoptic mocap, 10.1° mean / 6.2° median across all 8 Fit3D
subjects × 28 exercises (224 clips, ~1.16M joint-frame samples).

That is the thing a competitor cannot fake: a phone app pointed at you
from one angle cannot see knee valgus at all.

## Audience and scene

Three member sub-segments (see `PRODUCT_SPEC.md` §1.1): the New/Anxious
member, the Committed Self-Directed member, the Data-Driven Advanced
member. Plus gym owner/operator, floor staff, and a premium remote
coach/reviewer.

**Physical scene — this drives the appearance decision.** A member reads
this screen on a gym floor: bright overhead fluorescent or LED light,
phone held at arm's length or propped on the floor, sweaty hands,
30 seconds between sets, heart rate elevated, reading glasses off. Then
again in a dim locker room five minutes later. Then again at home on the
couch that night, reviewing the week. It is read in bright ambient light
far more often than in dark.

## Capability truth (the honest list)

`PRODUCT_SPEC.md` §3.3 and §6 carry a **stale exercise list** written
2026-08-07, before the confidence-gating work (2026-08-11) and the lunge
heuristic recovery (2026-08-12) that contradict it. Root-caused and
documented in `design/PROTOTYPES.md`. The real state per `STATUS.md`:

| Movement | Real state | Ships as |
|---|---|---|
| Squat | Trained class, 100% on matched Fit3D; larger 3D angle error on self-occluded poses | **Tracked**, with a visibly wider confidence band |
| Push-up | Trained class, 88% | **Tracked** |
| Bicep curl | Heuristic fallback only, 0% → 41% after the confined fallback | **Early support** |
| Lunge | Recovered via hip-ROM-asymmetry heuristic, 0/8 → 6/8 on Fit3D | **Early support** |
| Bench press | Classification fixed; counting weak head-on, needs a side camera | **Early support, marked stations only** |
| Deadlift / hinge | Not a recognized class. Hip:knee ratio was tried and **explicitly rejected** — sit-ups share the signature | **Not yet** |
| Row | Unrecognized, ~8% | **Not yet** |
| Overhead press / lateral raise | Fit3D domain-shift: RepCount's `press`/`raise` are different physical movements under the same label | **Not yet** |
| Sit-ups | Genuinely a trained class, but the hip-driven rep counter does not exist — counts zero | **Not yet** |

Anything that claims Deadlift, Row, or Overhead Press is trackable is
reproducing the stale spec, not the engine.

## Hard constraints the design must carry

- **Full body including feet must stay in frame.** Tracking breaks
  otherwise. This is why the "stay in frame" cue exists.
- **Mirrors are excluded by installation rule**, not by detection.
- **No mid-rep live form overlay at MVP.** Real-time is honestly
  redefined as near-real-time: a report 2–5s after the set. Promising
  live corrective coaching is the single most damaging overclaim
  available to this product.
- **Every score, count, and alert carries a visible confidence signal.**
  Solid = high-confidence 3D fused read. Dashed = single-camera 2D
  estimate. Greyed = not enough data. A member told "perfect form" on a
  rep the system was unsure about, who then gets hurt, is the failure
  mode that kills the business.
- **Risk signals are training-load indicators, never medical claims.**
- **A false "you skipped it" is worse than under-crediting.** Camera
  outage must never render as member failure.

## Brand commitments (from `PRODUCT_SPEC.md` §3, binding)

- Tone: a sharp, honest strength coach. Direct, specific, occasionally
  warm, never cutesy about safety. Calibrated confidence, not hype.
- **Banned:** fake precision ("form score: 94.7%") where the error band
  does not support it; stock gym photography; gradient-mesh heroes;
  illustration-heavy SaaS empty states; streak-shaming or guilt
  notifications; purple/blue AI gradients; neon risk alerts.
- **Signature:** the real skeleton/joint-angle overlay is a first-class
  design element, not hidden in a technical tab. Derived from actual
  pose data, not a generic icon. This is the one piece of identity a
  copycat cannot fake — it is literally the product's output.
- Numbers get tabular figures. Coaching voice should read distinct from
  raw data.

## Prior design attempts (anti-reference)

Three candidates exist in `design/prototypes/`, all dark-only or nearly
so, all reaching for the same technical-console register:

1. **01 Claude** — Big Shoulders Display + IBM Plex, graphite/warm-white.
   User feedback: *did not land visually.*
2. **02 Stitch** — Hanken Grotesk + JetBrains Mono, `#F45D01` orange,
   flat tonal layering, hairline borders. No feedback yet.
3. **03 Apple HIG** — SF + New York, working light/dark, corrected 3-tier
   capability list, report-as-sheet. No feedback yet.

A fourth candidate that arrives at another near-black surface with a
mono data face and one saturated accent has not made a choice — it has
repeated the room's consensus three times over.

## Platform

Web prototype, phone viewport, standalone HTML (matches how candidates
01 and 03 ship — openable with no build step). Member app, not the
operator console.
