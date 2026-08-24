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

### 02 — (reserved) Google Stitch

In progress, per the prompt drafted in this session (see conversation —
not yet copied into a standalone doc). Add the entry here once it's
ready: what screens it covers, the file/link, and first impressions.

## Decision

Not made yet. Revisit once 2+ candidates exist — compare against
`PRODUCT_SPEC.md` §3 (tone/visual identity direction) and the actual
screen requirements in §2.1, not just aesthetic preference.
