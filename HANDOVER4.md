# Handover 4 — Joule

Session date: 2026-08-03 (same day as `HANDOVER2.md`/`HANDOVER3.md`, third
continuation). Read `HANDOVER3.md` first — this picks up immediately after
it closed Phase A on synthetic/local validation alone. This session found
that a teammate had pushed the real CMU Panoptic dataset to the repo, used
it to run the real before/after validation that A1/A3 were still missing,
and it changed the story materially: found and fixed a real bug, then found
and fixed a real design flaw, both only visible with real data.

## What happened this session, in order

1. User reported the CMU Panoptic dataset had been pushed to GitHub and
   asked for it to be verified before pulling — not trusted on filename
   match alone.
2. Verified it thoroughly via `git show` (without pulling) before touching
   anything: calibration.json's camera-panel structure (31 HD cams on panel
   0, VGA panels 1–20, 10 Kinects on panel 50) matches real Panoptic exactly;
   ground-truth `body3DScene_*.json` has the correct `joints19`/
   `univTime`/`hd_29_97` schema; extracted a sample video and confirmed real
   playable 1920×1080 footage at 29.97fps, non-blank pixels, exact
   documented frame count; `panoptic_pose2/validation.log` reproduces the
   already-published Phase 8 figures (6.1° mean, 4.0° median, right-elbow
   39% coverage) exactly. Concluded genuine, pulled it (`697046c`).
3. Ran a real before/after: created a git worktree at the pre-A1 commit
   (`35af8b7`), copied the dataset + model files in, ran
   `tools/validate_panoptic.py` on `test_videos/panoptic/` (5 real cameras,
   101 frames) at that baseline, then again at current HEAD.
4. **Found a real, previously-undetected A1-shaped bug in the baseline**:
   the pre-A1 code fragmented this real capture's single subject into 2
   person identities — camera 8's view scored only 0.73 cosine similarity
   on its single first embedding sample (just under the 0.75 threshold),
   silently enrolling as phantom `person_2` and invisibly reducing "5-view
   fusion" to 4 views. Current (post-A1) code correctly resolves all 5
   views to one `person_1` (sims 0.87–1.00). This is real, on-camera
   confirmation A1 fixes a bug that was actually present in this project's
   own reference clip, not just a hypothetical scenario.
5. **Found a real side effect of A1**: `REID_LOCK_WINDOW_SECONDS` (3.0s)
   consumes most of this specific clip's very short duration (101 frames /
   ~3.4s) before identity resolves at all (locks in ~frame 60), leaving only
   41/101 frames with any output — vs. the old code's 101/101. Not a
   product bug (real sets last far longer than 3s) but means this
   particular clip can't cleanly isolate A1/A2's accuracy impact anymore.
6. **Found A3's 6px threshold measurably too tight on real data**: 100% of
   frames with resolved identity (41/41) failed it and fell back to 2D,
   dragging the aggregate accuracy from 3.7°→6.3° mean (a scoring artifact
   of comparing degraded 2D angles against 3D ground truth, not a real
   triangulation regression).
7. Diagnosed the root cause precisely rather than just picking a bigger
   number: the naive all-views DLT `cross_view_consistent()` deliberately
   uses (no outlier-view dropping) has reprojection error that inherently
   *grows with camera count* even for a genuine match, since it's the max
   error across every contributing view. Measured real per-joint max-error
   p95 by view count on the real footage: 2v=6.7px, 3v=15.4px, 4v=45.0px,
   5v=78.3px.
8. **Tried and rejected outlier-view dropping** (mirroring
   `triangulate_skeleton`'s own best-pair retry) as the fix: tested against
   a synthetic single-wrong-of-5-views mismatch and it passed cleanly in
   100% of cases — dropping the one bad view leaves the other 4 looking
   perfectly consistent, silently defeating the exact thing this check
   exists to catch. Confirmed not to use this approach.
9. Derived a **view-count-scaled threshold** instead
   (`CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS` in `src/triangulation.py`: 2v=9px,
   3v=20px, 4v=30px, 5v=90px) from the real noise data above plus a
   synthetic mismatch-error sweep (adversarial worst-case *and*
   randomized-direction trials, using the real 5-camera rig geometry, at
   realistic 40cm–2m separation). Caught and fixed a units bug in my own
   analysis along the way — the rig is in **centimeters**, not meters
   (confirmed via camera-to-origin distance ≈349 units ≈3.5m); an earlier
   sweep using 0.4–2.0 as "meters" was actually testing sub-centimeter
   separations and produced meaningless near-zero mismatch errors.
10. Re-ran the real Panoptic sequence with the fix: **0/41 frames now fall
    back to 2D** (down from 41/41); mean error for those frames improved
    6.3°→5.2° (remaining gap to the 3.7° baseline is expected — a different,
    smaller 41-frame subset per finding #5, not a fusion defect).
    Re-verified all 4 existing synthetic A3 unit tests still pass unchanged.
11. Surfaced two narrow, **accepted** residual limits that no threshold
    closes, and asked the user which way to lean where they trade off
    against each other:
    - **2 cameras**: inherent 1-DOF epipolar ambiguity, already known when
      6px was first chosen — a synthetic axis-aligned mismatch can measure
      as low as 0.6px. Not new, not worsened.
    - **4 cameras specifically**: a narrow, unlucky camera/direction
      alignment can produce a mismatch measuring *below* real noise's own
      p95 at that view count (33.5px adversarial floor vs. 45.0px noise
      p95) — no single number is both safe against noise and airtight
      against that alignment. User chose to favor catching the mismatch
      (30px, at the adversarial floor) over maximizing pass-rate, matching
      the project's own stated conservative-matching philosophy
      (`src/session.py`: "mis-attribution is the worst failure mode").
      Realistic (non-adversarial) 4-camera mismatches still measure ~108px+
      at the 5th percentile — this is a narrow, deliberately-accepted edge
      case, not a general weakness at 4 cameras.
12. Fixed one small, unrelated pre-existing bug found while using the
    dataset: `tools/validate_panoptic.py` wasn't zero-padding camera IDs in
    video filenames (`cam_0.mp4` instead of `cam_00.mp4`), which breaks any
    camera ID under 10. Verified the fix (hid/restored the workaround files,
    confirmed identical results via the correct filenames).
13. Updated `ROADMAP.md`'s A1 and A3 entries in place with the full real
    validation detail, and updated Phase A's exit-criteria line to state
    Phase A is now fully closed on real data, not just synthetic/local
    validation.

## Key files touched this session

- `src/triangulation.py` — `cross_view_consistent()` redesigned from a flat
  `CONSISTENCY_MAX_REPROJ_PX` (6.0) to `CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS`
  (a per-view-count dict) plus `_threshold_for_n_views()`. `max_reproj_px`
  is still an optional override parameter for callers/tests that want one
  flat value.
- `tools/validate_panoptic.py` — one-line zero-padding fix
  (`f'cam_{c}.mp4'` → `f'cam_{c:02d}.mp4'`).
- `ROADMAP.md` — A1 and A3 entries rewritten with real-data findings; Phase
  A exit-criteria line updated.
- `test_videos/panoptic/` and `test_videos/panoptic_pose2/` — pulled from
  `697046c` (a teammate's push), gitignored, not touched by this session's
  own commits.

## Validation scripts (scratchpad only, not committed — matches this
## project's existing convention of not keeping a `tests/` directory)

All in this session's scratchpad:
- `a4_stress_tests.py` — from the earlier same-day A4 work (see
  `HANDOVER3.md`), unrelated to this session's Panoptic work.
- `a3_reproj_distribution.py` — extracts the real per-joint max-reproj-error
  distribution from the real 5-camera Panoptic footage.
- `a3_frame_level_sim.py` — simulates `cross_view_consistent`'s actual
  frame-level pass/fail decision across threshold candidates, with and
  without outlier-view dropping.
- `a3_mismatch_check.py` — first mismatch-sensitivity test (before the units
  bug was caught), still valid as the source of the "1-of-5-views wrong"
  and "2-of-5-views wrong" synthetic results quoted in `ROADMAP.md`.
- `a3_scaled_threshold_derive.py` / `a3_scaled_v2.py` — superseded by v3
  (contain the meters/centimeters units bug — kept only for the record of
  how the bug was caught, don't reuse).
- `a3_scaled_v3.py` — the corrected (centimeter-unit) derivation that
  produced the final `CONSISTENCY_MAX_REPROJ_PX_BY_VIEWS` values.
- `test_a3_epipolar.py` and `test_provisional.py` / `test_a2_margin_staleness.py`
  — copied forward from the original session's (different scratchpad
  folder, `06ee2956-...`) test files; still exist on disk there if needed
  again, but that folder is a different session's temp dir and may not
  persist indefinitely.
- `pre_A1_baseline` worktree — created and removed within this session
  (`git worktree remove --force`); not left behind.

## Repo hygiene

`src/triangulation.py`, `tools/validate_panoptic.py`, `ROADMAP.md`, and this
file are the only changes pending commit as of writing. `test_videos/` is
gitignored and was not touched by any commit from this session (the dataset
itself arrived via a separate, already-pushed commit `697046c` before this
session started working with it).

## What's next

Phase A is now fully closed, including real-data validation. Next up per
`ROADMAP.md`: **Phase B** (repro/doc hygiene — mostly done already earlier
today, B1 remains blocked on missing artifact files) and **Phase C**
(footage-prep track: camera-placement doc, capture protocol, Fit3D/M3GYM
registration forms), both unblocked, no dependency on footage, can run in
parallel or either order.
