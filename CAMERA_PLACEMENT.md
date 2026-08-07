# Joule — Camera Placement Guide

Written 2026-08-05, before any real camera install, per `ROADMAP.md` Phase
C1. This is a prerequisite for good footage, not a follow-up — every rule
below traces back to a specific validated finding or measured limit in this
codebase (cited inline), not generic camera advice. Hand this to whoever
plans or walks the physical camera layout, at Sussex or any other site.

## 1. Every station: feet must stay in frame

Full body **including feet** must remain visible in every camera's frame,
for the whole set. This is not a nice-to-have — `src/pose.py`'s joint
angles and the rep state machine both degrade silently (not with an error)
when a foot leaves frame, and this is already a documented limitation
(`STATUS.md`). Frame wide enough, and mount high/far back enough, that a
full squat or lunge doesn't push a foot out of shot at the bottom of the
rep.

## 2. Bench/press stations need a side view, not head-on

Confirmed finding, not a hypothesis: bench press classification works
head-on, but rep *counting* is weak in that framing — the elbow angle
signal is too foreshortened and self-occluded from directly in front of the
bar. Any station where the primary limb motion runs toward/away from the
camera (bench press, overhead press) needs at least one camera at a genuine
side angle (roughly perpendicular to the plane of motion). A 45° angle is
not sufficient for this specific failure mode — it needs a true side-on
view.

## 3. No mirrors in any camera's frame

Hard rule, not a tuning knob. Confirmed by reading the pipeline
end-to-end (`src/detector.py`, `src/reid.py`, `src/session.py`): nothing in
the current system can distinguish a mirror reflection from a real person —
a reflection that clears the detector's confidence threshold is just
another tracked person. Depending on how Re-ID resolves it, a mirror in
frame either (a) contaminates the real person's rep-counting state with a
second, desynced angle stream, or (b) enrolls as a phantom second person
who appears to double every rep in the aggregate reporting. Both are worse
than losing the coverage a mirror-adjacent angle would have bought. If a
station is unavoidably near a mirror wall, frame it out entirely rather
than "mostly" out — there is no partial-credit dead-zone masking in the
pipeline yet (backlogged, not built).

## 4. 3D (fused) stations: 3+ cameras preferred over exactly 2, spaced 60–90°

- **Minimum 2 cameras** to triangulate at all (`src/triangulation.py`,
  DLT). But 2-camera stations have a known, accepted blind spot: the
  cross-view identity-consistency check (`cross_view_consistent()`) that
  guards against two different people merging into one bogus 3D skeleton
  has only 1 degree of freedom to work with at 2 views — a wrong match can
  measure as little as 0.6px of reprojection error, indistinguishable from
  ordinary pose-estimation noise. This is a real, documented residual limit
  (`ROADMAP.md` A3), not closable by tuning. **Prefer 3+ cameras per fused
  station wherever the site allows it** — the consistency check gets
  real teeth starting at 3 views.
- **Space cameras 60–90° apart** around the station. Too narrow (near-0°,
  cameras stacked close together) gives triangulation rays that are nearly
  parallel — poor depth precision even though calibration succeeds. Too
  wide (pushing toward 180°, cameras facing each other) causes more
  self-occlusion of the far side of the body and makes cross-view
  correspondence harder. 60–90° is the range that kept both the tuned
  5-camera Panoptic sequence (3.7° mean joint-angle error) and the
  less-favorable held-out 3-camera arc (6.1° mean, per `README.md`/
  `DEVELOPMENT.md` Phase 8) inside usable accuracy — the held-out
  sequence's worse number is attributed there to a less favorable arc, not
  camera count alone, which is the concrete evidence for spacing mattering
  more than raw camera count.
  **Caveat from a second real rig (`ROADMAP.md` Phase C3, Fit3D Track C):**
  Fit3D's own 4-camera studio rig is bimodal, not evenly spaced —
  adjacent-camera gaps cluster at ~47° and ~132–133°, with **0 of 32
  measured adjacent gaps falling inside this 60–90° band** — yet
  full-scale triangulation on that same rig still landed at 10.1° mean
  joint-angle error, in the same usable range as Panoptic's. Treat 60–90°
  as a good default, not a hard cutoff below/above which accuracy is known
  to collapse; both data points so far are controlled studio rigs, so a
  real gym floor (Phase D) is still the test that actually settles how
  tight this needs to be on site.
- **Elevate cameras** — synthetic testing (`README.md`) used ~2m elevated
  mounts and found single-view squat-depth error collapses from ~11° at the
  bottom of the rep to <1° once fused in 3D; ground-level or low mounts
  make the single-view fallback path (used whenever fewer than 2 views see
  a person, e.g. during setup/teardown of a set) noticeably worse, and gain
  the fused path nothing since 3D triangulation isn't sensitive to modest
  height differences between calibrated cameras the way single-view depth
  estimation is.

## 5. 2D-only zones: roughly 3–4 machines per camera

For stations that only need rep counting and 2D form angles (no 3D
fusion), one camera can reasonably cover about 3–4 adjacent machines,
provided every person in frame still satisfies rule 1 (feet visible) and
is large enough in the frame for the detector/pose model to track
reliably (`DETECTOR_CONF = 0.5` in `src/config.py` — don't frame so wide
that a person's bounding box gets marginal). If a zone has more than ~4
machines, split it across two cameras rather than one wide-angle camera
covering everything.

## 6. Give adjacent stations real physical separation

Session identity (Re-ID) matches purely on appearance embedding
(`src/session.py`, cosine similarity, `REID_MATCH_THRESHOLD = 0.75` with a
`REID_MATCH_MARGIN = 0.05` margin over the runner-up). Two people in
visually similar gym clothing standing close together — e.g. at neighboring
stations both partly visible in the same camera — raise the odds of an
ambiguous match, which under this project's deliberately conservative
matching philosophy means a new anonymous person enrolls rather than a
guessed match, fragmenting that person's session. This isn't a hard
distance rule (no on-site data yet to derive one), but the epipolar/Re-ID
tolerance work in `ROADMAP.md` A3 was tuned and tested at a 40cm–2m
person-separation scale — treat noticeably tighter spacing than that as a
risk factor when laying out stations that share a camera's field of view,
not just a fusion-accuracy concern.

## 7. Calibrate once, then don't touch the camera

3D stations are calibrated with `tools/calibrate.py` (checkerboard, both
cameras simultaneously) and the resulting rig `.npz` encodes each camera's
fixed pose. Any camera that gets bumped, refocused-by-moving, or
repositioned after calibration silently invalidates that rig — the
pipeline has no way to detect a moved camera on its own. If a mount isn't
rigid (tripod on a busy gym floor, easily knocked), plan to re-calibrate
before every capture session rather than assuming a one-time setup holds.

## 8. Lighting consistency across a station's cameras

Not yet measured on real footage (flagged here for awareness, not a hard
rule like 1–3 above): Re-ID's appearance embedding is sensitive to how a
person is lit, and A5's mirror analysis noted reflections tend to
mismatch partly *because* they're dimmer/differently lit than the real
subject. Cameras at the same station seeing the same person from different
angles should get reasonably matched exposure/white balance where the
venue's lighting allows it, to avoid a same-person, different-lighting
pair reading as a weaker Re-ID match than it should.

---

Cross-referenced from `ROADMAP.md` Phase C1. Next up in the same track:
C2 (structured capture protocol checklist) will assume this layout is
already in place when the camera holder shows up to film.
