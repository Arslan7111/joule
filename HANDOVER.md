# Handover — Joule

Last updated: 2026-07-29. Read this before doing anything else in this repo.

## What this is

Gym computer-vision pipeline: per-person rep counting, joint angles, exercise
classification, form scoring, injury-risk signals, session Re-ID, and
multi-camera 3D triangulation, from gym camera footage. Target hardware:
NVIDIA Jetson Orin Nano; developed and validated on Apple Silicon
(`hurricane_env`, Python 3.10). Repo:
https://github.com/Arslan7111/joule (private). Usage: `README.md`.
Full dated technical log: `DEVELOPMENT.md`. Quick-reference summary:
`STATUS.md` (this file is the closing-session version of that).

## Current state: all 9 build phases done, externally validated, nothing running

Everything below is committed and pushed as of this handover
(commit `7b46aa9`). No background jobs are in flight.

### What's built
Detection (YOLOv8n) → ByteTrack → Re-ID gallery (MobileNetV3 + color hist,
`/checkin` endpoint) → MediaPipe pose → 9 joint angles → adaptive per-person
rep counting → exercise classification (heuristic + **trained** NumPy
logreg) → form scoring with coaching cues + reference-signature scoring
(AIFit-style) → set-level injury-risk signals → JSON/dashboard/video output.
Optional: 2+ calibrated cameras → DLT triangulation → true 3D angles + knee
valgus; `--fuse rig.npz` runs N synchronized sources as one live 3D station.

### What's been validated (the news since the last handover-worthy point)
- **RepCount Part-A** (152 real YouTube workout videos, published dataset,
  no footage of our own needed): our zero-shot adaptive counter is
  competitive with TransRAC (CVPR'22, trained on this data) — see
  `STATUS.md`/`DEVELOPMENT.md` Phase 8 for exact numbers.
- **CMU Panoptic held-out sequence**: 3D triangulation validated against
  motion capture on a second, untuned sequence — ~6° mean joint-angle error
  through the real `--fuse` CLI end to end.
- **Exercise classifier trained** on 280 labeled RepCount videos
  (`models/exercise_clf.npz`, 6 KB, committed). Full 152-video
  re-benchmark: every gym-core class (squat, front raise, pull-up,
  push-up) improved over the heuristic rules. Bench press: classification
  fixed, but counting stays weak when filmed head-on — foreshortened
  elbow signal, a camera-angle problem not a code problem.
- Two ideas ported from the AIFit paper (`src/signature.py`): automatic
  active/passive joint mining, and trainer-reference form scoring with a
  strictness knob (`CRITIC_DELTA`) — self-consistency tested, not yet
  used on real footage.

**Never verified — do this first when picking the project back up:**
- Anything on real gym footage. Every number above comes from public
  datasets (RepCount, CMU Panoptic) or stock clips — none of it has run
  on a phone filmed at an actual gym.
- The reference-signature scoring against a real trainer's set (only
  tested self-consistently against its own source video).
- Live multi-camera fusion on anything other than pre-synced recordings
  (Panoptic, or clap-aligned phone clips) — no RTSP timestamp sync exists.
- Multi-camera fusion beyond 3 cameras, or camera spacing narrower/wider
  than what Panoptic happened to provide.

## Known caveats to resolve before/while doing the above

1. **System `git` is broken on this Mac** (no Xcode Command Line Tools
   confirmed installed). A working `git` exists at `/opt/miniconda3/bin/git`
   (conda, v2.51.0) — use that for all git operations in this repo until
   CLT is installed. (Same caveat exists in the travel-planner repo on
   this machine — not fixed there either.)
2. **Disk space policy**: this laptop runs low on space. Dataset videos
   (RepCount, Panoptic) are deleted immediately after each validation run —
   annotations, result JSONs, and reports are kept (tiny) and the videos
   re-download in minutes from the HuggingFace mirror
   (`momo321654/RepCountA-videos`) or the Panoptic dome URL pattern
   (both documented in `DEVELOPMENT.md`). `training_data/` (119 MB,
   gitignored) is the one exception kept around — regenerating it costs
   ~3 hours of pipeline processing.
3. **Bench press needs a side-on camera**, not head-on, per the
   classifier finding above — worth remembering when planning camera
   placement at the actual gym, not just a training-data curiosity.
4. **Fit3D / M3GYM datasets are registration-gated and academic-license-only**
   ([fit3d.imar.ro](https://fit3d.imar.ro/) account,
   [M3GYM form](https://forms.gle/stJZgHaji7KNa5t7A)) — fine for further
   validation, not for training anything that would ship commercially.
   Neither form has been submitted yet as of this handover.

## Suggested next session's first moves

1. **Film real gym footage** — still the single highest-value next step,
   unchanged from prior planning. Phone clips of real exercises (validates
   everything above under real conditions, doubles as classifier training
   data), plus a two-phone clap-synced squat set with a checkerboard
   calibration pass for the first real-world 3D fusion run. Full body
   **including feet** in every frame on every camera — confirmed as a hard
   requirement three separate times already.
2. Once any good-form footage exists, build a real trainer reference
   signature (`tools/build_reference.py`) and see whether the deviation
   cues it produces are actually useful coaching, not just self-consistent.
3. If pursuing the Sussex gym specifically: get the floor plan for the
   camera layout plan, and submit the Fit3D/M3GYM forms now since approval
   takes days.
4. Only after real footage exists: RTSP timestamp sync, Jetson port.

## Repo hygiene

Working tree fully pushed to `origin/main` as of this handover (commit
`7b46aa9`, "Add STATUS.md"). Local `.claude/settings.json` /
`settings.local.json` permission-list updates from this session are
committed alongside this file — no other local-only changes exist.
