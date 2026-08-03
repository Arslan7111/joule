# Handover 3 — Joule

Session date: 2026-08-03 (continuation of the same day as `HANDOVER2.md`).
Read `HANDOVER2.md` first for full A1–A3 detail and the Panoptic-access
problem; this session closes out the rest of Phase A on top of it.

## What happened this session

Continued directly from `HANDOVER2.md`'s "what's next": Phase A had A1–A3
done, A4–A5 not started. This session did **A4 and A5**, closing Phase A.

### A4 — Depth/tempo stress tests (done, written finding, no code change)

No rep-bearing footage exists on this machine — the one local clip from the
previous session (`person_test.mp4`) is a walking/bicycle-detection test
asset with no exercise reps in it, and retiming it wouldn't produce a
meaningful angle signal. Instead of blocking on footage, drove the real
`src/state_machine.py` `StateMachine` directly with synthetic squat-shaped
angle signals — this is a more direct test of the exact thing the roadmap
was worried about (the 3-second adaptive window vs. tempo, and `angle=None`
dropout handling) than a real clip would give, since it isolates the
component from pose-estimation noise as a confound.

Script: this session's scratchpad, `a4_stress_tests.py` (not committed — no
`tests/` directory convention exists in this repo; matches how A1–A3's
validation scripts were handled last session).

**Tempo** (8-rep sets at 1.5s / 3.0s / 5.0s / 8.0s per rep): all four
tempos counted every rep correctly, right depth and validity, even at 8s/rep
where the 3-second window can't see even half a cycle at once. Reason
worked out from the code: the adaptive window uses 10th/90th-percentile
range over its trailing samples, and a cosine-shaped rep signal spends most
of its time (near-zero velocity) at the top/bottom extremes regardless of
period — so the trailing window keeps recapturing values close to the true
range even without seeing a full cycle.

**Occlusion** (`angle=None` for 1.0s mid-rep, 6.0s spanning ~2 rep-periods,
and 4.5s at 5s/rep tempo): zero false or extra reps in every case; exactly
the rep(s) physically inside the blackout went uncounted (graceful
undercount, not corruption); counting resumed immediately once fresh
variance reappeared after the gap, with no extra re-warm-up delay and no
corrupted depth/validity on the first post-occlusion rep.

**Caveat**: idealised smooth waveform, not real noisy pose output. Real
keypoint jitter is a separate, already-mitigated concern (`SMOOTHING_WINDOW`
median filter) — this test didn't need to re-check it.

**Verdict: acceptable as-is, no code change.**

### A5 — Mirror-detection sanity check (done, written finding, no code change)

No mirror-containing clip exists on this machine either, so this is a
code-grounded analysis, not an observed run. Read `src/detector.py` (plain
2D YOLO person detector — no depth or geometric cue at all) and
`src/reid.py` / `src/session.py` (identity match is pure cosine similarity
on appearance) to confirm: **nothing in the pipeline can distinguish a
mirror reflection from a real person.** A reflection that clears
`DETECTOR_CONF` is just another tracked person.

Two failure paths depending what Re-ID then does with it:

1. **Matches the real person** → both tracks resolve to the same
   `person_id`, and `camera.py`'s per-frame loop calls that person's *one*
   shared `StateMachine.update()` from both tracks in the same iteration —
   the state machine has no concept that these are the same instant from
   two sources, so a reflection's (often distorted/oblique) angle reading
   gets interleaved into the same median-filter buffer and adaptive history
   as the real body's reading. Not proven to flip a rep count outright
   (`HYSTERESIS_FRAMES`=2 should absorb a single interleaved outlier) but a
   real, code-confirmed contamination path.
2. **Doesn't match** (plausible — reflections are typically dimmer, edge-
   cropped, and oblique, which lowers cosine similarity) → enrolls as a
   phantom new person who appears to perform the same exercise in perfect
   sync with the real person: inflated headcount and every real rep
   double-counted under a second identity. Given Re-ID matching is
   deliberately conservative (A2's margin+threshold), this path is probably
   the more likely of the two in practice — and the more consequential.

**Recommendation: placement rule, not a code fix.** Reliably telling a
reflection from a real person needs depth or a calibrated per-camera
exclusion zone, neither justified before a real installation exists to
calibrate against — and "no mirrors in frame" is already planned
independently in Phase C1's camera-placement doc. Added one cheap follow-up
to the backlog for whenever real camera installs exist: a static per-camera
polygon dead-zone mask (drop detections whose bbox centroid falls inside a
manually marked mirror region) as a machine-enforced backstop for when the
placement rule isn't followed perfectly.

## Phase A status: closed

A1–A5 all done. `ROADMAP.md` updated in place with full detail for A4/A5
(same style as A1–A3). Real-footage validation of A1/A2/A3's tuned
thresholds against Panoptic remains the one open item, tracked as before —
see `HANDOVER2.md`'s "Panoptic access problem" section, unchanged this
session (did not attempt re-acquisition; still a separate multi-GB pull via
CMU's `panoptic-toolbox`, no download script preserved in this repo).

## Environment

Unchanged from `HANDOVER2.md` — the Windows Python 3.11 venv
(`C:\Users\aa3163\joule\.venv\`), model files, and everything else described
there are still present on this machine and were reused as-is this session.
The old session's scratchpad clip (`person_test.mp4`) was copied into this
session's own scratchpad for reference; still not part of the repo.

## What's next

1. **Phase B (repro/doc hygiene)** and **Phase C (footage prep)** — both
   fully unblocked now that Phase A is closed, no dependency on footage,
   can run in parallel or either order. See `ROADMAP.md` for the full item
   lists (B1–B5, C1–C4). Specific known gaps from `HANDOVER2.md` worth
   folding into Phase B: `torchvision` missing from `requirements.txt`, and
   the `src/pose.py` YOLO-fallback bug (mediapipe pip-installed but no
   `.task` file silently yields no pose estimator at all).
2. Real Panoptic validation of A1/A2/A3's tuned thresholds, once footage
   access is resolved (unchanged blocker from last session).

## Commits this session

(This file's own commit, plus the `ROADMAP.md` update for A4/A5, are the
next commits after `32be0ac`.)

## Repo hygiene

No uncommitted code changes beyond this handover and the `ROADMAP.md`
update. `.venv/` and model files remain gitignored and machine-local only.
