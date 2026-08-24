# Google Stitch prompt — Joule Coach member app

Written 2026-08-24, for candidate 02 in `PROTOTYPES.md`. Paste directly
into Stitch.

```
PRODUCT

Joule Coach — a camera-based personal trainer for gyms. Members check in
at a kiosk, and gym-mounted cameras (already computer-vision-validated:
rep counting, joint angles, form scoring, 3D pose fusion) turn every set
into an automatic report — no phone held up, no manual logging. Members
also get an in-app plan builder with adherence tracking verified against
what the cameras actually observed, and a demo-video library for correct
form. Pitch: gyms differentiate without hiring more personal trainers;
members get an honest coach that only ever tells them what it actually
measured.

Design a mobile app (iOS-style, portrait) for the MEMBER-facing side.

WHO USES IT

- New/anxious member: never had a trainer, wants reassurance they won't
  hurt themselves, will abandon at the first moment the app feels
  confidently wrong.
- Committed self-directed member: wants structure and real proof they
  stuck to their plan, not their own guesswork.
- Advanced member: wants raw joint-angle data, trends over months, no
  dumbing down.

TONE — the most important instruction in this brief

"Calibrated confidence, not hype." This is a strength coach, not a
gamified fitness app. The single biggest risk is the app looking more
certain than it is — a member told "perfect form!" on a rep it wasn't
sure about, who then gets hurt, is the failure mode that kills trust.

- No fake precision ("form score: 94.7%") — plain-language tiers instead.
- No stock gym photography, no purple/blue AI-gradient hero sections, no
  cutesy streak-shaming notifications.
- Feels like the UI on a piece of real athletic equipment (think a
  Technogym console, or Strava's data density) — not a consumer
  lifestyle app trying to look "modern."
- Direct, specific, occasionally warm. Never cutesy about safety.

THE ONE SIGNATURE VISUAL ELEMENT

The app's real output is a skeleton/joint-angle overlay — literal stick-
figure pose data with joint markers. Use a stylized version of this as
the app's actual visual identity: on the post-set report, in video-
library thumbnails, even as a loading state. This is the one thing a
copycat fitness app can't fake, because it's literally the product's
real output — don't replace it with a generic icon or illustration.

CONFIDENCE MUST BE VISIBLE, EVERYWHERE

Every score, count, or alert needs a lightweight, consistent visual
signal for how sure the system is — e.g. solid vs. dashed outline, or
a filled vs. hollow indicator, for "two+ cameras agreed" (high
confidence) vs. "single camera estimate" (lower confidence) vs. "not
enough data" (greyed out / withheld). Never show these as equally
certain.

SCREENS TO DESIGN

1. Onboarding — plain-language coverage disclosure up front: "Joule
   currently tracks: squat, deadlift, bicep curl, row, overhead press,
   lateral raise. It does not yet count sit-ups. Bench press is
   supported only at marked stations." Not buried legalese — an actual
   onboarding card.
2. Kiosk check-in confirmation — member taps a QR/badge, gets a
   confirmation within a few seconds, sees today's station.
3. Live session (mid-set) — deliberately minimal, NOT a live form
   overlay (real-time scoring isn't proven reliable yet, so don't
   design promises the product can't back up). Just: a large glanceable
   rep counter, current exercise, and a "stay in frame" cue for when
   the member's feet/body leave the camera's view.
4. Post-set report (the hero screen) — appears seconds after a set
   ends. The skeleton overlay for the single worst-scoring rep,
   annotated with the specific deviation (e.g. "left knee tracking
   inward on reps 5–6"), compared against a reference. A rep-by-rep
   strip below, color-coded by validity/confidence. A plain-language
   one-line summary. Exactly one or two coaching cues — ideally one
   thing to fix and one thing done well, not a wall of feedback. One
   clear next action (e.g. "watch the 40-second fix-it demo").
5. Weekly plan builder — drag exercises from a supported-exercise
   library onto a calendar-week grid. Exercises the cameras can't yet
   track are visibly greyed out with why, not hidden.
6. Adherence / progress view — "planned vs. actually detected" per
   week. Must visibly distinguish "you did less than planned" from
   "we couldn't observe it" (camera outage, unsupported station) — a
   false "you skipped it" is treated as a worse failure than being
   generous.
7. Exercise video library — short reference-vs-common-mistakes clips,
   organized by movement pattern (squat, hinge, press, pull, curl), not
   muscle-group marketing copy. Grid of thumbnails using the skeleton-
   overlay visual motif.

STYLE DIRECTION (a starting point, not a mandate — go where the brief
above leads you)

Dark, equipment-console mood over bright/gamified. A restrained palette:
one neutral dark base, one warm light-mode base, and 2–3 accent colors
used only for specific meanings (an "actionable coaching cue" color, a
"confirmed good" color, and a "flag/risk" color) — not decorative. Data-
heavy screens (report, progress) should feel dense and legible, more
like a cockpit instrument than a lifestyle app; in-the-moment gym-floor
screens (check-in, live session) should be airy and readable at a glance
mid-workout. Typography should make numbers (rep counts, angles,
timestamps) feel like real instrument readouts — tabular, precise —
while coaching language feels human and distinct from raw data.
```
