# Handover 5 — Joule

Session date: 2026-08-03/04 (same continuous day, fourth continuation).
Read `HANDOVER4.md` first — this picks up immediately after it closed
Phase A on real Panoptic data, and covers the rest of Phase B.

## What happened this session, in order

1. Moved to Phase B's one remaining open item, B1 (commit small benchmark
   artifacts so headline numbers are auditable, not just asserted).
2. **Panoptic half of B1**: already resolved as a side effect of Phase A's
   real-data validation work (`HANDOVER4.md`) — the genuine
   `validation_results/val.json` + `merged.json` produced while validating
   A1/A3's fixes was force-committed (small JSON/rig files only, despite the
   blanket `test_videos/` gitignore). Committed as `eb665b5`.
3. **RepCount half of B1**: scoped with the user first (small 37-video
   subset vs. full 152-video test set vs. skip) — chose the full 152-video
   set. Installed `huggingface_hub`, explored the actual file layout of the
   `momo321654/RepCountA-videos` public HF mirror (test videos live under a
   `test/` prefix, not the `videos/` folder `tools/benchmark_repcount.py`
   expects — downloaded into the correct local path), downloaded all 152
   test-split videos (1.4GB), and ran `tools/benchmark_repcount.py
   test_videos/repcount --keep-results` end to end (~50s/video, ~90 minutes
   total, run in the background with periodic progress checks via counting
   completed result files rather than polling process output, since the
   script only prints after each video's subprocess call returns).
4. **Result: ALL n=152, MAE 0.742, OBO 22.4%**; gym-core classes — squat
   44.4%, front_raise 33.3%, pull_up 36.8%, push_up 31.2% OBO.
5. **Verified the trained classifier was actually active**, not a silent
   fallback to heuristics, before trusting these numbers — `grep`'d every
   `classified=` value across all 152 videos and confirmed every single one
   was one of the trained model's 7 output classes (cardio, press, pullup,
   pushup, raise, situp, squat); none of the heuristic-only classes
   (lunge, hinge, curl, row) ever appeared. `models/exercise_clf.npz` is
   present, tracked, and loads without error.
6. **Explained why these numbers differ from the historical Phase 8/9
   figures in `DEVELOPMENT.md`** rather than either presenting them as a
   clean reproduction or panicking that something broke: A1's buffered
   Re-ID identity-lock (this same day's earlier Phase A work) changes
   exactly which frames/timespans get attributed to a track over a video's
   timeline, which shifts the classifier's feature windows and rep counts
   from whatever pre-hardening baseline the historical numbers were
   computed on. Not a regression — this run reflects the current codebase
   and is now the authoritative figure going forward.
7. Force-committed `report.json` (19KB) as the auditable artifact; left the
   1.4GB of source video and 51MB of per-video pipeline JSONs disk-only
   (gitignored, not committed) at the user's request, rather than deleting
   them immediately — freely re-downloadable from the public mirror if ever
   needed again.
8. Updated `ROADMAP.md`'s B1 entry (now closed, both halves) and added a
   contextualized row to `DEVELOPMENT.md`'s validation table for the fresh
   RepCount numbers, cross-referencing why they differ from the Phase 9 row
   above it rather than just replacing it silently.
9. Committed (`aac8bfc`) and pushed.

## Phase A and Phase B status: both fully closed

- **Phase A** (A1–A5): closed with real CMU Panoptic data — see
  `HANDOVER4.md` for the full detail (a real A1 bug found and confirmed
  fixed; A3's threshold redesigned from a flat 6px to a view-count-scaled
  lookup after real data proved it too tight).
- **Phase B** (B1–B5): fully closed. B2–B5 (doc hygiene, dependency/fallback
  bug fixes) were done earlier the same day (see the "Phase B: doc hygiene"
  commit, `2daf547`). B1 (this session) is the last piece.

## What's on disk, not committed

- `test_videos/repcount/videos/` — 152 real video files, 1.4GB, gitignored.
  Kept at user's request; safe to delete any time (`momo321654/
  RepCountA-videos` HF mirror is public, no re-acquisition friction like
  Panoptic).
- `test_videos/repcount/bench_results/*.json` (except `report.json`, which
  is committed) — 152 individual per-video pipeline output JSONs, 51MB,
  gitignored. Same disposition as the videos above.
- `test_videos/panoptic/` and `test_videos/panoptic_pose2/` — the real
  Panoptic dataset from `HANDOVER4.md`, still present, gitignored, untouched
  this session.

## What's next

**Phase C** (footage-prep track) is the next unblocked item per
`ROADMAP.md`: camera-placement doc (C1), structured capture protocol (C2),
Fit3D/M3GYM registration forms (C3 — per this session's conversation, not
yet actually submitted, still an open action item), Sussex gym floor plan
request (C4). No dependency on footage; can start immediately.

**Phase D** (real footage validation) remains blocked on an actual camera
and gym access, per the sequencing in `ROADMAP.md`.
