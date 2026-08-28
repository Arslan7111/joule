# Capture Session Plan — 2026-08-29

Concrete plan for tomorrow's shoot: 2 people (you + one friend), 3 iPhones
(15/17), a possible 4th. This is **Phase D** (`ROADMAP.md`) — the single
highest-value, longest-blocked step in the whole project. Everything below
is a specific instance of `CAMERA_PLACEMENT.md` (where cameras go) and
`CAPTURE_PROTOCOL.md` (what to film) applied to your actual equipment and
headcount — read this file for *what to do tomorrow*, read those two for
*why*, cited inline below wherever it matters.

**Minimum success for the day, if nothing else happens:** one properly
calibrated, multi-camera, clap-synced squat set. That single clip closes
the exact gap `STATUS.md` has listed as "blocked on you" since the project
began. Everything past that is real bonus value, tiered below so you know
what to cut first if you run short on time or energy.

---

## Tonight, before you leave

- [ ] **Print the checkerboard**: `tools/checkerboard_9x6_25mm.html`. Open
  it in a browser, print landscape A4 at **100% / actual size**, not "fit
  to page." Measure one square with a ruler afterward — if it isn't 25mm,
  write down the real number, you'll need it tomorrow.
- [ ] **Mount the printed sheet on something rigid** — cardboard, a
  clipboard, a laptop lid. A board that bows kills corner detection.
- [ ] **Charge all phones to 100%.** A 3-camera calibration pass plus a
  full session of exercise clips is roughly 45–75 minutes of actual
  recording time once you add it up; screen-on filming drains fast.
- [ ] **Clear storage.** 1080p/30fps is roughly 130–200MB per minute of
  footage. Budget several GB free per phone.
- [ ] **Bring something to mount 3 phones rigidly** — tripods, phone
  clamps, or anything stable (a shelf, a stack of plates, gaffer tape to a
  fixed rack upright). This is not optional for the fused station: once
  calibrated, a camera that gets bumped silently invalidates the whole
  calibration and the pipeline has no way to detect it happened
  (`CAMERA_PLACEMENT.md` rule 7). A handheld phone cannot be one of the
  fused cameras at all.
- [ ] **Set every phone to: landscape orientation, standard Video mode
  (not Cinematic, not Portrait/Spatial), 1080p, default frame rate.**
  Landscape because every camera-placement rule below assumes it and
  nothing in the pipeline has been tested against portrait footage.
  Standard mode because Cinematic's synthetic depth blur is a confound
  you don't need. If your phone has a "Lock Camera" toggle for exposure/
  focus, use it — stops the camera hunting exposure mid-set.

---

## How the checkerboard actually works

Your phones each see the world flat — a 2D image with no built-in sense of
real distance. To combine two or three of them into one accurate 3D
measurement, the software needs to work out two things it doesn't know
yet: **each camera's own lens quirks** (its exact field of view, and how
much it subtly bends straight lines near the frame's edges — every lens
does this a little differently), and **exactly where the cameras sit
relative to each other** as real geometry, not an estimated angle.

A checkerboard solves both because it's the one object in the room with
**known, exact geometry** — every square is precisely the same size.
Shown to the cameras from many different distances and angles, the
software works backward from how that known pattern got distorted and
positioned in each frame to solve for both unknowns at once. A single
photo of the board can't do this — there isn't enough variation in one
view to solve for it. **That's the entire reason you move it around
instead of holding it still.**

**What to physically do:** cameras already mounted and recording, stand
roughly where the lifter will stand, hold the board flat facing generally
toward the cameras, and over 45–60 seconds move it through several
different positions **and** tilt it at a few of them — closer, farther,
left, right, then angled up/down/sideways. Move slowly; a blurred board
can't be detected in a frame at all, so a few clean sharp positions beat
many blurred ones. It doesn't need to look tidy — the only goal is real
variety, clearly visible, across the space where lifting will happen.

**How you'll know it worked:** `calibrate.py` prints how many frames it
detected the board in per camera, and needs at least 10 frames where two
cameras saw it at the same moment. An error like "only 4 frames seen by
both cameras" isn't mysterious — the pass was too fast, too short, or
spent too long somewhere only one camera could see it. Fix: record again,
a little slower, staying in the shared space.

**Printing it correctly, step by step:** open
`tools/checkerboard_9x6_25mm.html`, Ctrl+P (Cmd+P on Mac), set
**Orientation: Landscape**, **Paper size: A4**, and find the scale/fit
dropdown and set it to **"100%," "Actual size," or "None"** — never "Fit
to page" or "Shrink to fit," which is the default in most print dialogs
and exactly the setting that breaks this. Print, then measure one printed
square with a ruler; if it isn't 25mm, use the real measured number for
`--square-mm` tomorrow rather than 25. Mount on something stiff so it
can't bow.

---

## Why the exercise order below is what it is

`STATUS.md`'s honest capability table, restated as priority:

| Movement | Real state today | Value of real footage tomorrow |
|---|---|---|
| **Hinge / deadlift** | Not recognized at all. A heuristic was tried and explicitly rejected (shares a signature with sit-ups). | **Highest.** Only real labeled data moves this, not a code fix. |
| **Row** | Unrecognized, ~8%. | **Highest**, same reason. |
| **Overhead press / lateral raise** | Trained model exists but was mapped to the wrong physical movement during training (Fit3D domain-shift bug). | **High.** A correctly-labeled real clip directly targets that specific bug. |
| **Bench press** | Classification works; rep *counting* is confirmed weak head-on. | **High**, and this is the one exercise with an already-confirmed camera-angle requirement (side view, not negotiable — `CAMERA_PLACEMENT.md` rule 2). |
| **Reverse lunge** | Early support, recovered via a hip-ROM heuristic (6/8 on Fit3D). | Medium — more data solidifies a heuristic that already half-works. |
| **Bicep curl** | Early support, 41% recall. | Medium. |
| **Squat** | Tracked, wider error band, validated only on studio data (Panoptic, Fit3D) so far. | **The flagship 3D-fusion target** — real gym floor is the untested case. |
| **Push-up** | Tracked, 88% recall on RepCount. | Medium — the other exercise Fit3D found genuinely hard (10.7–13.3° error vs 5–7° standing), worth a real-floor check. |
| **Sit-up** | Classifier recognizes it; the rep *counter* deliberately counts zero (no hip-driven counter built yet). | Low today — a code gap, not a data gap. One token clip is still useful for whenever that counter exists. |

Squat is still the one exercise that gets the full 3D-fusion treatment
(three cameras, calibrated, clap-synced) — it's what `STATUS.md` names
specifically, it's the flagship movement across every design prototype,
and its error band is the one most worth closing with real data. Every
other exercise above gets **single-view 2D coverage**: full multi-camera
fusion for a second exercise would mean a second checkerboard pass and a
second fixed rig, which two people don't have time for in one day
alongside everything else. That's a deliberate scope cut, not an
oversight — matches `CAPTURE_PROTOCOL.md`'s own exit criteria ("every
checkbox ticked once is enough for the first session").

**With a 4th phone:** don't split into two 2-camera fused stations. Rule 4
is explicit that a 2-camera pair has a real, measured blind spot in its
identity-consistency check, and running two fused rigs at once means two
calibration passes and twice the setup for a 2-person crew. Put the 4th
phone on the squat rig too (3 is already better than 2 per rule 4) and
use whichever phone is spare for single-view coverage or handheld reframes
between exercises.

---

## How many people in one frame

**One, for every exercise-coverage clip.** Clean, single-person footage is
what the exercise classifier and rep counter actually train on — a second
person in frame is a confound for that specific goal, not a benefit.

**Exactly one deliberate clip with both of you in frame together**,
crossing/occluding each other's paths — that's the Re-ID stress test
`CAPTURE_PROTOCOL.md` calls out by name, testing session-identity logic
that clean single-person clips can't exercise at all. Do it once, label it
clearly, move on.

---

## Running order

### Phase 0 — Set up the squat rig (~20–30 min)

1. Mount 3 phones around the squat rack. Space them **60–90° apart** if
   you can (`CAMERA_PLACEMENT.md` rule 4). If the rack's physical
   surroundings won't allow that, the one thing to actively avoid is any
   **two of the three sitting close to directly opposite each other
   (~180°)** — that specific geometry measured roughly double the error
   of a good angle on Fit3D's own rig.
2. **Elevate them as much as is practical.** Synthetic testing found
   squat-depth error at the bottom of a rep collapses from ~11° to under
   1° once properly fused, and that gain is much stronger from elevated
   cameras. You don't need to hit exactly 2m — higher than eye level is
   the right direction to push toward given whatever you can rig up.
3. **Frame check, on all 3 phones, before recording anything real:**
   have one of you stand at the rack and squat once. Confirm **feet stay
   in every phone's frame at the bottom of the rep** — hard requirement,
   check it live on-screen, not after the fact.
4. **Check for mirrors** anywhere in any of the 3 frames. If the rack is
   near a mirror wall, reangle rather than "mostly" frame it out — there's
   no partial-credit handling for this in the pipeline.

### Phase 1 — Calibration pass (~10 min)

1. Start all 3 phones recording, as close to simultaneously as you can
   manage (a "3‑2‑1, go" called out loud is enough).
2. One person holds the printed checkerboard in the space where lifting
   will happen and moves it around for **45–60 seconds**: near, far,
   left, right, tilted — the goal is variety of position/angle, not
   holding it still. All 3 cameras need to see it fully for a good chunk
   of that.
3. Stop recording. **Do not move, bump, or re-aim any of the 3 phones for
   the rest of this fused block** — that invalidates everything after.
4. Copy the three clips off the phones immediately and name them clearly:
   `calib_camA.mov`, `calib_camB.mov`, `calib_camC.mov`. That's the actual
   job for tomorrow — the rest of this step is post-processing you (or I)
   can do afterward, described here so you know the raw footage is
   already sufficient for it:

   `tools/calibrate.py` only takes a camera **pair** and outputs
   `K1,K2,R,t` (camera B's pose relative to camera A). `src/fusion.py`'s
   `load_rig()` accepts that 2-camera format directly, but for 3 cameras
   it wants a combined file (`Ks`, `Rs`, `ts` — one pose per camera, all
   relative to one shared world frame), which nothing currently builds
   automatically. The real path: run `calibrate.py` twice, camera A as
   the shared reference both times —
   ```
   python tools/calibrate.py calib_camA.mov calib_camB.mov --square-mm 25 --out calibration/pair_AB.npz
   python tools/calibrate.py calib_camA.mov calib_camC.mov --square-mm 25 --out calibration/pair_AC.npz
   ```
   (adjust `--square-mm` if your ruler check tonight found a different
   number) — then merge `pair_AB.npz`'s `K1,K2,R,t` and `pair_AC.npz`'s
   `K2,R,t` into one `Ks=[K1,K2_AB,K2_AC], Rs=[I,R_AB,R_AC],
   ts=[0,t_AB,t_AC]` rig file by hand or a small script. That merge step
   doesn't exist yet as a tool — worth writing once rather than doing by
   hand every session, but not tomorrow's problem.

### Phase 2 — Fused squat sets (~20–30 min, cameras stay fixed)

For each lifter, in this order:

1. **A clean, correct-form set first, before any fatigue.** This doubles
   as the input `tools/build_reference.py` needs for a real trainer
   reference signature (`ROADMAP.md` D3) — the only test of that feature
   so far scored a reference against its own source video, so a genuinely
   separate good-form clip is real, new value.
2. **Then a normal working set** at real working weight.
3. If either of you has a set that's genuinely slow and heavy (5+ seconds
   a rep), that's a free stress-test tick (`CAPTURE_PROTOCOL.md`'s
   "one slow, heavy set" item) — no separate clip needed, just note which
   take it was.

Start/stop recording once per lifter (not per rep), **clap once, sharply,
in view of all 3 cameras, at the very start of every new recording** —
each stop/start resets timing, so a clap you did on an earlier take
doesn't cover a new one. Copy and label clips immediately:
`squat_<name>_clean.mov` / `squat_<name>_working.mov` × 3 cameras.

### Phase 3 — Single-view coverage, other exercises (remaining time)

Reposition one phone at a time (the mounted ones can come down now, or
use a spare 4th) and work down the priority table above. For each:

- Frame check for feet, same as Phase 0.
- **Bench press and overhead press/lateral raise specifically need a real
  side-on view for the pressing arm** — bench's is confirmed
  (`CAMERA_PLACEMENT.md` rule 2), overhead's isn't confirmed but the same
  foreshortening logic applies, so treat it the same way as a precaution.
- Hinge/deadlift and row: a side view is the strong recommendation here
  too, on the same reasoning, though this hasn't been measured yet the
  way bench has — it's inferred, not confirmed, and worth stating as such
  if you ever write up what you shot.
- One clean clip per exercise is enough; a second take is a bonus, not a
  requirement.
- Label each clip with the exercise name as you shoot it — matches this
  project's `training_data/<class>/` naming convention and makes it
  directly usable later rather than something to re-cut afterward.

### Phase 4 — Stress-test clips (~10–15 min, whichever camera is free)

One of each, per `CAPTURE_PROTOCOL.md`:

- [ ] Both of you crossing/occluding paths (the one deliberate two-person
  clip — see above).
- [ ] A mirror somewhere in frame, once, deliberately, clearly labeled so
  it never gets mistaken for a real station setup.
- [ ] One deliberate occlusion — step fully behind a machine or pillar
  mid-set, then continue.
- [ ] One walking or treadmill clip — cheap regression check.

### Phase 5 — Wrap-up (before you leave the gym)

- [ ] Copy every clip off both phones into a folder structure that keeps
  multi-camera takes grouped, separate from the pipeline's own
  `training_data/` (that folder is pipeline *output* — JSON — not a raw
  footage bucket). Suggested layout:
  ```
  captures/2026-08-29/
    calibration/    calib_camA.mov, calib_camB.mov, calib_camC.mov
    squat/          squat_<name>_clean_camA.mov, ...
    hinge/          hinge_<name>_camA.mov
    row/  ohp/  lateral_raise/  bench/  lunge/  curl/  pushup/  situp/
    stress/         occlusion.mov, mirror.mov, crossing.mov, walking.mov
  ```
- [ ] **Back up in two places before deleting anything off either phone**
  — laptop plus cloud, or two independent copies at minimum. This is
  hard-won data; treat it that way.

---

## After the shoot (not tomorrow's job, just so it's written down)

Per `ROADMAP.md` Phase D: run the full pipeline against the squat fusion
clip first (that's D1/D2 — does Re-ID hold up with real clothing and real
occlusion, does fusion behave on the deliberate mismatch case), build the
reference signature from the clean-form clips (D3), and feed anything the
classifier gets wrong back into `training_data/` for the next training
pass (D4). Exit criteria per the existing protocol: a written finding per
stress dimension — pass/fail and what broke, not just "it ran."
