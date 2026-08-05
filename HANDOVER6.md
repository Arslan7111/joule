# Handover 6 — Joule

Session date: 2026-08-05. Read `HANDOVER5.md` first — this picks up
immediately after it closed Phase A and Phase B, and covers the start of
Phase C (footage-prep track).

## What happened this session, in order

1. **C1 (camera-placement doc)**: written as `CAMERA_PLACEMENT.md`. Every
   rule traced to a specific validated finding already in this codebase
   rather than generic camera advice — feet-in-frame, the bench/press
   side-view requirement, hard mirror avoidance (A5), 3+ cameras preferred
   over exactly 2 for fused stations (ties to A3's accepted 2-camera
   epipolar-ambiguity limit) with 60–90° spacing, ~3–4 machines per 2D
   camera, physical station separation sized off A3's 40cm–2m test scale,
   and a calibration-rigidity warning. `ROADMAP.md`/`STATUS.md` updated to
   mark it done.
2. **C3 (Fit3D/M3GYM registration)**: asked the user for the identity
   details needed to actually submit the forms; user said they'd handle
   both themselves and to hold off. Set aside.
3. **User pointed out a `Fit3D/` folder already on disk** — the real
   dataset (8 train subjects × 47 exercises × 4 calibrated cameras,
   SMPLX-derived mocap-grade 3D ground truth), provided directly rather
   than through the `fit3d.imar.ro` registration flow C3 was written
   around. First action: added `Fit3D/` to `.gitignore` (~44GB, matches
   the existing `test_videos/` pattern) before it could land in a commit.
4. **Built `tools/validate_fit3d.py`** to use this for what it's uniquely
   good for — real gym exercises with mocap-grade GT, unlike CMU
   Panoptic's generic dome poses. Two things about Fit3D's raw format
   aren't documented and were reverse-engineered from the real data,
   verified rather than assumed (both detailed in the tool's own
   docstring and in `ROADMAP.md` Phase C3):
   - `camera_parameters` extrinsics' `T` is the camera *center* in world
     coordinates, not the standard `P = K[R|t]` translation — confirmed by
     projecting GT joints onto a real video frame (standard convention
     landed ~3000px off-frame; `X_cam = R@(X-T)` landed exactly on the
     real body).
   - `joints3d_25`'s joint order and left/right split — recovered via
     bone-length invariance (anatomically connected joints have ~0
     coefficient-of-variation distance across real frames) for topology,
     then a real frame with the subject's back to the camera (so
     image-left = anatomical left, unambiguous) to fix left vs. right.
5. **Ran a real validation sweep**: subject s03, 7 exercises, all 4
   cameras fused, ~6,800 frames. Standing/unencumbered exercises (curls,
   overhead press, lateral raise) landed in the same 5–7° range as the
   Panoptic figures, ~100% coverage. Squat/pushup showed real, larger
   error (10.7–13.3° mean, p95 up to 52°).
6. **Found and fixed a real bug — in the validation tool, not the
   pipeline.** The first pass showed squat/pushup "coverage" collapsing to
   ~50%, with a suspicious exact-complementary pattern (`left_shoulder`+
   `left_elbow` present precisely when every other joint was absent).
   Investigated properly instead of accepting it at face value: ruled out
   A3's cross-view-consistency threshold (only 2% of frames trigger it),
   ruled out genuine pose-confidence dropout (a faithful frame-by-frame
   replay of the real detector+pose+triangulate path showed continuously
   healthy confidence — first replay attempt had its own bug, a shared
   ByteTrack instance across 4 camera feeds corrupting tracker state,
   fixed by matching `src/fusion.py`'s real one-tracker-per-camera setup),
   and ruled out Re-ID track-id restarts (exactly one resolution event per
   camera for the whole clip, no re-acquisitions logged). Actual cause:
   `src/output.py`'s `_downsample_series` runs an independent ~30fps
   sampling clock per joint, so one ordinary transient 1-frame gap in one
   joint permanently shifts *that joint's* output timestamps out of
   frame-grid alignment with every other joint's (confirmed directly by
   diffing `left_hip` vs `left_elbow`'s raw output timestamps). The
   validation script's shared per-frame join manufactured a false
   anti-correlation out of that harmless phase drift. Fixed by scoring
   each joint independently against its own nearest GT frame; rescoring
   the *same* already-computed pipeline output changed coverage from
   50–56% to 92–100% while every error number (mean/median/p95/n) stayed
   byte-identical — confirming the error figures were trustworthy the
   whole time, only the coverage metric had been wrong.
7. Documented results in `ROADMAP.md` (full narrative under Phase C3,
   matching A1/A3's depth), `DEVELOPMENT.md` (validation table rows +
   updated the stale "Fit3D needs registration" note), `STATUS.md`
   (external validation list + blocked-on-you list, M3GYM now the only
   outstanding item there).

## Phase C status

- **C1**: done.
- **C2**: not started this session.
- **C3**: Fit3D half done, with real validation results exceeding the
  original "just get access" bar. M3GYM still pending — user submitting
  independently.
- **C4**: not started this session.

## What's on disk, not committed

- `Fit3D/` — the real dataset, ~44GB, gitignored (added this session,
  same disposition as `test_videos/`).
- `validation_results_fit3d/s03/` — per-exercise `rig.npz`/pipeline output
  JSONs/`merged.json` for all 7 exercises, plus `report.json` (the
  auditable summary — this one *is* committed, matching the B1 pattern
  for RepCount/Panoptic).

## What's next

C2 (structured capture protocol) and C4 (Sussex floor plan request) are
the remaining open Phase C items, both unblocked. M3GYM registration is
in the user's hands. Phase D (real footage validation) remains blocked on
camera/gym access, per `ROADMAP.md`'s sequencing — though Fit3D's squat/
pushup results already give a preview of what Phase D is likely to find:
the system handles clean, standing poses well and degrades gracefully
(not catastrophically) on harder, more self-occluded ones.
