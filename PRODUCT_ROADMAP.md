# Joule — Productization Roadmap: Phase F Onward

Written 2026-08-06. **Status of this document: planning only.** Nothing
below has been built. It continues the phase-numbering convention of
`ROADMAP.md` (Phases A–E) and assumes Phases D and E are the prerequisite
gates they are described as there. It is a companion document to
`PRODUCT_SPEC.md` (the member/owner-facing product specification for the
same plan).

**Ground rule applied throughout**: every claim about "what exists today"
cites a file actually read in this codebase. Where the repo is silent,
that is said explicitly rather than assumed.

---

## Part 0 — Verified current state (the baseline this plan builds from)

This section exists so the gap analysis can't drift into fiction. Each
line is a fact traced to code or docs.

### 0.1 What the system is, structurally

`pipeline.py` is an argparse CLI. It builds one `CameraProcessor`
(`src/camera.py`) per `--sources` entry, each in a `threading.Thread`,
joins them all, then calls `write_merged_json`. The process lifetime *is*
the session lifetime. There is no service mode, no supervisor, no
scheduler, no restart path, no daemon.

`--fuse rig.npz` swaps in a single `FusedCameraProcessor` (`src/fusion.py`)
that reads all N sources in lockstep inside one thread and runs
detect+pose for every view sequentially in that same thread.

### 0.2 Where state lives

All per-person exercise state lives in a plain dict (`persons_data`) local
to `CameraProcessor.run()`. Angle history accumulates unbounded —
`pd['angles'][joint].append((timestamp, val))` runs per joint, per tracked
person, per frame. Nine joints × 30 fps means roughly a million tuples per
person per camera per hour, held in RAM for the life of the process.

Results are serialized exactly once, at the end of `run()`, via
`write_camera_json`. A crash mid-session loses the entire session.
`Ctrl+C`/`stop_event` does write partials, but an OOM, a segfault in a
native dependency, or a power cut does not.

### 0.3 The clock problem

Analysis timestamps are `timestamp = frame_idx / fps` — a source-relative
clock that starts at `0.0` (`src/camera.py`, identically in
`src/fusion.py`). Every rep timestamp, form window, and angle series in
the output JSON is on that clock. There is no wall-clock time, no date, and
no session identifier anywhere in the output.

Separately, `src/session.py` uses `time.time()` for `Person.last_seen` and
staleness. Identity and analysis already run on two different, unrelated
clocks.

### 0.4 Identity, precisely as built

`SessionGallery` (`src/session.py`) is an in-memory `dict[str, Person]`,
constructed fresh in `pipeline.py` on every invocation, with `self._counter`
restarting at zero — so `person_1` means a different human on every run.
Embeddings are never written to disk; `README.md` states this as a
deliberate property ("Embeddings live only in memory for the session —
nothing biometric is persisted") and `DEVELOPMENT.md` repeats it as a core
design decision.

The embedding itself (`src/reid.py`) is MobileNetV3-small ImageNet
features (576-d, `_DEEP_WEIGHT = 0.6`) concatenated with an HSV histogram
of the torso band. It is not a Re-ID-trained model, and by construction it
is heavily clothing-driven.

`REID_STALE_SECONDS = 1800` (30 min, `src/config.py`) excludes anyone not
seen recently from match candidacy. So even *within* one long run, a
member who lifts, leaves for 40 minutes, and returns enrolls as a
brand-new person.

`/checkin?person=person_1&name=Ahmed` calls `bind_name`, which sets a
string on the in-memory `Person`. That binding dies with the process.

### 0.5 The HTTP surface

`src/dashboard.py` runs a `http.server.BaseHTTPRequestHandler` bound to
`0.0.0.0`. It exposes: `GET /` (hardcoded HTML), `GET /snapshot/<cam_id>`
(live JPEG of the gym floor), `GET /data` (current reps/angles/state),
`GET /people` (every tracked identity), `GET /checkin?person=…&name=…`
(binds a member name). There is no authentication, no authorization, no
TLS, no rate limiting, and no audit log on any of these. `/checkin` is a
state-mutating GET.

`push_data` is keyed by `cam_id` alone, and `src/camera.py` explicitly
pushes only "the person with the most frames"; `src/fusion.py` picks the
largest bounding box. **The dashboard is structurally single-person-per-
camera.** It is an operator debug view, not a product surface.

Doc inconsistency worth noting: `README.md` documents `/people` and
`/checkin` on port 8080, but the dashboard's default is `--port 5000`.

### 0.6 What the system can actually count

Rep counting is driven by exactly two signals (`src/camera.py`, mirrored
in `src/fusion.py`): the knee average → `squat_sm`, and the elbow average
→ `upper_sm`. There is no third counter.

`CLASS_FAMILY` (`src/exercise_classifier.py`) routes `situp` and `cardio`
to family `'none'` — deliberately zero reps. `CLASSES` lists 12 labels,
but per `FIT3D_UTILIZATION_PLAN.md` and the Phase B1 verification in
`ROADMAP.md`, the trained model in `models/exercise_clf.npz` only ever
emits 7 (`cardio, press, pullup, pushup, raise, situp, squat`). `hinge`,
`lunge`, `curl`, `row` are heuristic-only and never appear as trained
output.

### 0.7 What "form score" actually measures

`src/form.py` starts at 100 and deducts on five rule-based checks. Its own
docstring says scores are "relative to the person's own set where possible
(median-based)." The depth check keys off `rep['valid']`, which
`src/state_machine.py` sets as `lowest <= self.depth_threshold`, where
`depth_threshold = lo + DEPTH_FRACTION * rng` over the person's *own last 3
seconds* of motion (`DEPTH_FRACTION = 0.25`).

**Today's form score is therefore largely self-referential, not a measure
of correctness against a standard.** The absolute path exists
(`src/signature.py` + reference signatures), but `models/` contains only
`exercise_clf.npz` — there is no `models/references/` directory in the
repo, and `ROADMAP.md` D3 records that the only reference test so far
scored a reference against its own source video.

### 0.8 Measured performance, and what is unmeasured

`FIT3D_UTILIZATION_PLAN.md` records the only real throughput number in the
repo: **~0.22 s of wall-clock processing per video frame** for a
4-camera fused run (detection + pose + triangulation), on the development
laptop, with a single subject in frame. That is roughly 4.5 processed
frames/second aggregate, ~1.1 fps per view, for one person.

Pose is top-down with `num_poses=1` (`src/pose.py`) — one MediaPipe
`detect()` call per detected person per frame. **Cost scales linearly with
the number of people in frame.**

MediaPipe is forced to the CPU delegate for a macOS-specific
PyTorch/Metal conflict. `README.md` says "Not an issue on Jetson," but
`ROADMAP.md` E2 is explicit that Jetson is "currently entirely unmeasured
on target hardware." `DEVELOPMENT.md`'s "2–4 cameras per Orin Nano at
reduced frame rates" is a stated estimate, not a measurement.

`src/config.py` records measured detection rates on heavily-occluded
two-person footage: **yolov8n@640 detected both people 30% of the time**
(yolov8s@640 51%, yolov8s@960 61%). The shipped default is yolov8n@640.

### 0.9 What is absent entirely

No database, no ORM, no web framework beyond `http.server`.
`requirements.txt` is six lines (opencv, ultralytics, mediapipe, numpy,
lapx, torchvision). No `tests/` directory (`ROADMAP.md` A4 states outright
that "no `tests/` convention exists in this repo"). No `.github/` CI. No
Dockerfile. No deployment manifests. No per-environment or per-site
configuration mechanism — `src/config.py` is module-level constants
imported at import time, global to the process.

### 0.10 Two pieces of live technical debt worth naming now

**(a) Per-joint timestamp drift in the output format.**
`_downsample_series` in `src/output.py` runs an independent sampling clock
per joint, keyed off that joint's own emitted timestamps:

```python
next_t = entries[0][0]
for ts, val in entries:
    if ts >= next_t - 1e-9:
        sampled.append(...)
        next_t = ts + interval
```

`ROADMAP.md` C3 and `HANDOVER.md` (2026-08-05 entry) document that one transient
single-frame confidence gap in one joint permanently shifts that joint's
output timestamps off the shared frame grid. The Fit3D validation tool was
fixed to score joints independently; **`src/output.py` itself was not
changed.** Any future consumer — a mobile app chart, an analytics
warehouse, a per-frame join in a DB — that buckets joints on a shared
timestamp will reproduce exactly the artifact that nearly got reported as
a pipeline bug.

**(b) Detector licensing.** `requirements.txt` pins `ultralytics>=8.2.0`
and `DETECTOR_MODEL = 'yolov8n.pt'`. Ultralytics YOLOv8 ships under
AGPL-3.0 with a separate commercial license offering. This needs counsel
review before anything ships commercially — flagged as an open legal
question, not a settled fact.

---

## Part 1 — Gap analysis: "validated pipeline" → "a gym can sell this"

Lift sizing: **S** = days, **M** = weeks, **L** = a quarter-ish with a
small team, **XL** = the thing that decides whether this is a product at
all.

### 1.1 The four biggest lifts, called out first

| # | Gap | Lift | Why it's the hard one |
|---|---|---|---|
| **1** | **Real-gym accuracy under crowding, occlusion, mirrors and equipment** | **XL** | Entirely unknown. Phase D has never run. The strongest adverse signal in the repo: the shipped detector caught both people only 30% of the time on heavily-occluded two-person footage (`src/config.py`). A commercial gym floor is dozens of people, machines, and mirror walls. |
| **2** | **Throughput on affordable edge hardware at real gym density** | **XL** | 0.22 s/frame for 4 views with *one* person, on a laptop. Pose cost is linear in people (`num_poses=1`, one call per person). A 15-person camera view is a different order of magnitude. Jetson numbers do not exist. |
| **3** | **Persistent per-member identity that holds for a 90-minute visit on a busy floor** | **XL** | Not "persist the gallery." The embedding is ImageNet features + clothing histogram; it will not match the same person next Tuesday in different clothes. The real problem is holding a *check-in-established* binding across an entire visit, through fragmentation, equipment occlusion, and 40 other similarly-dressed people, when `REID_STALE_SECONDS = 1800` already drops anyone gone 30 minutes. Mis-attribution is called "the worst failure mode" in `src/session.py` — as a product it also becomes a trust and billing failure. |
| **4** | **Privacy, consent, and biometric-regulation compliance** | **L, and non-negotiable** | The current system is legally clean precisely *because* it persists nothing. Every gap below that fixes a product problem — persistent identity, historical storage, video retention — actively destroys that property. This is the only gap where doing the engineering work *creates* the legal exposure. |

### 1.2 Multi-tenancy and per-gym data isolation

**Exists:** nothing. No concept of a gym, an organization, an account, or
a tenant anywhere in the codebase. `--names squat_rack_1` is a station
string used as a JSON filename.

**Needed:** a tenant as a first-class entity threaded through storage, API
authorization, model/config scoping, and the edge runtime's identity.
Camera calibration (`rig.npz`, today a local file path) and per-site
thresholds must become tenant-scoped managed records, not files on
someone's laptop.

**Non-obvious sub-gap:** `src/config.py` is global module state.
`DETECTOR_CONF`, `REID_MATCH_THRESHOLD`, `REID_MATCH_MARGIN`,
`TRUNK_LEAN_LIMIT`, `MIN_ANGLE_RANGE` will all need per-site tuning
(lighting, ceiling heights, clientele, equipment). Today changing any of
them is a code edit affecting every deployment simultaneously.
**Lift: M for config layering, L for full tenant isolation.**

### 1.3 Persistent per-member identity

**Exists:** in-memory session gallery, `/checkin` name binding that dies
with the process, `person_N` counter restarting each run.

**Needed:** a durable `member_id`, a `visit` concept, and a binding
between the two that survives process restarts and is auditable.

**Architectural warning, grounded in the code:** do not solve this by
persisting `SessionGallery` embeddings across visits. Two independent
reasons. Technically, the embedding is ImageNet-pretrained generic
features plus a clothing-color histogram, designed for *within-session*
matching, where `src/reid.py`'s own docstring assumes "clothing stays
constant." Legally, a persisted appearance template derived from a
person's body is precisely what biometric-identifier statutes are written
about; a session-scoped, never-written embedding is a far weaker
regulatory claim than a stored gallery. **Lift: L, and it is lift #3
above.**

### 1.4 Long-term historical storage

**Exists:** one JSON file per station per run, written once at process
exit, into whatever `--output` directory the operator typed. No session
ID, no timestamp in the filename — a second run into the same directory
silently overwrites the first.

**Needed:** a real database, plus a deliberate split of hot and cold data.
`OUTPUT_FPS = 30.0` means `angle_series` is emitted at full frame rate,
~9 joints × 30 Hz × session duration, per person. Reps and sets are small,
relational, and queried constantly; angle series are large, append-only,
and queried rarely. Putting both in the same store is a design error that
will be very expensive to undo. **Lift: M for schema/ingest, L including
migration/retention tooling.**

### 1.5 A real backend API

**Exists:** `src/dashboard.py`'s five unauthenticated `http.server`
endpoints.

**Needed:** an authenticated, versioned, documented API with tenant-scoped
authorization on every route; a separate ingest path for edge→cloud event
submission (device credentials, not user credentials); idempotency, since
edge devices will retry after network loss. **Lift: M** — conventional,
but everything else depends on it.

### 1.6 Mobile/web app backend needs

**Exists:** nothing. No user accounts, no auth, no sessions, no push
infrastructure.

**Needed:** account lifecycle, member↔gym membership records, auth (and
the app's check-in flow doubling as the identity-binding mechanism per
1.3), a read model shaped for app screens rather than for the pipeline's
convenience, offline tolerance, real-time delivery if in-workout feedback
is promised. **Lift: L** (large but low-risk).

### 1.7 Plan builder and adherence tracking

**Exists:** nothing. No plan, no schedule, no target, no goal concept.

**Needed:** a plan model (template → assigned plan → scheduled session →
prescribed exercise/sets/reps/load) and an adherence engine that
reconciles *prescribed* against *observed*.

**The hard part is not the schema — it's the epistemics.** Adherence is a
claim about what a member *didn't* do. The system's own documented
limitations mean non-detection is routinely not evidence of
non-performance: sit-ups deliberately count zero
(`CLASS_FAMILY['situp'] = 'none'`), bench press counting is weak head-on,
any station without camera coverage produces nothing, any set where feet
left frame degrades silently. An adherence feature that reports "you
skipped your prescribed sets" on that basis will generate false
accusations against paying members. The data model must distinguish
**observed-complete / observed-partial / not-observable / observed-
absent**, and only the last may ever drive a negative statement.
**Lift: M for the model; the observability-classification design is
genuinely subtle.**

### 1.8 Exercise video content library and delivery

**Exists:** nothing. `--visualise` writes annotated MP4s of *members* for
debugging; that is not a content library.

**Needed:** demo video production or licensing, a catalog keyed to the
same exercise taxonomy the classifier uses, transcoding/ABR, CDN delivery,
offline caching, captions/accessibility, localization if multi-market.
Taxonomy trap: the library will want dozens of exercises; the classifier
recognizes 7 trained classes. The catalog must be able to contain
exercises the pipeline cannot detect, clearly marked as such.
**Lift: S–M engineering; content production is a separate budget line.**

### 1.9 Notifications and reminders

**Exists:** nothing.

**Needed:** push infrastructure, per-user preferences and quiet hours, a
scheduling/trigger engine, delivery-attempt audit trail. Any notification
derived from adherence inherits 1.7's false-negative risk, now delivered
to the member's lock screen; any notification with form feedback is
health-adjacent personal data leaving the platform. **Lift: S–M.**

### 1.10 Billing and subscriptions

**Exists:** nothing.

**Needed:** likely two tiers — B2B (gym pays per site/camera/member) and
B2C (member subscription, possibly gym-collected). Plus proration,
dunning, tax, entitlement checks, and a clean answer to "the cameras were
down for three days." **Lift: M** (buy, don't build the processor).

### 1.11 Gym-operator admin dashboard

**Exists:** `src/dashboard.py` — one card per camera showing one person,
no auth, no history.

**Needed:** floor/camera health, per-camera coverage and drift status,
member roster and check-in state, aggregate utilization (often what the
operator actually buys), incident/alert view, consent/retention
administration. Must be role-scoped — gym staff should not have
unrestricted access to every member's body-mechanics history.
**Lift: M–L.**

### 1.12 Camera install and fleet operations across sites

**Exists:** `CAMERA_PLACEMENT.md` (evidence-traced install guide),
`CAPTURE_PROTOCOL.md`, `tools/calibrate.py` for a two-camera checkerboard
pass producing a local `.npz`.

**Needed:** a site-survey workflow, an install/commissioning app that
validates each camera against the `CAMERA_PLACEMENT.md` rules *at install
time* (feet-in-frame check, mirror check, spacing check), calibration as a
managed versioned artifact rather than a file, and — critically —
**automatic calibration-drift detection.** `CAMERA_PLACEMENT.md` rule 7
states plainly that a bumped camera "silently invalidates that rig — the
pipeline has no way to detect a moved camera on its own." Also needed:
remote device fleet management (inventory, OTA updates, staged rollout,
rollback, remote logs). **Lift: L, and consistently underestimated.**

### 1.13 Model-serving and inference infrastructure

**Exists:** models loaded in-process per thread.

**Needed:** measured capacity on real target hardware (Phase E2, never
run), a decision on GPU delegate / TensorRT / quantization for Jetson, an
answer to the linear-in-people pose cost (batch crops, or a bottom-up
multi-person model), frame-drop and back-pressure policy under load, model
versioning with per-site pinning and rollback.

**Also needed: a licensing decision on the training data.**
`DEVELOPMENT.md` states Fit3D and M3GYM are "academic-only licenses —
validation OK, shipped-model training not." The currently-shipped
`models/exercise_clf.npz` was trained on the RepCount train split
(Phase 9); RepCount came from a public HF mirror with no access blocker,
but its terms need confirming before commercial deployment.
**Lift: XL (this is lift #2).**

### 1.14 Privacy, consent, and compliance

**Exists:** exactly one relevant property, and it's a good one — nothing
biometric is persisted, embeddings are session-only, no video is retained
by default.

**Needed, and each item erodes that property:**

- **Consent capture and withdrawal** — per member, versioned, timestamped,
  revocable, enforced downstream. Plus the *bystander* problem: guests,
  staff, cleaners, contractors, minors who appear in frame and never
  consented. The current pipeline silently enrolls anyone above
  `DETECTOR_CONF` as `person_N`.
- **Video retention and deletion policy** — default should be that raw
  frames never leave the edge device and are never written. Any clip
  retention offered (dispute resolution) needs explicit opt-in, a hard
  short TTL, encryption at rest, access logging.
- **Biometric-specific statutes.** BIPA (Illinois) requires written notice
  and consent before collecting a biometric identifier, a published
  retention/destruction schedule, and carries a private right of action —
  the single most expensive US exposure. Texas CUBI and Washington's
  biometric law are similar. GDPR/UK GDPR treat biometric data processed
  to uniquely identify a person as special-category (Art. 9), needing an
  Art. 9 condition on top of a lawful basis; systematic large-scale
  monitoring of a publicly accessible area triggers a mandatory DPIA
  (Art. 35). Children's-data regimes apply if minors are members.
- **Data-subject rights** — access, portability, erasure, including
  erasure propagating to derived analytics and any model trained on
  member footage. If member footage ever feeds `training_data/`
  (`ROADMAP.md` D4 proposes exactly this), erasure becomes a
  model-retraining obligation.
- **Health-data positioning.** `src/risk.py` emits fatigue,
  ROM-degradation, tempo-collapse and asymmetry signals with a
  `risk_level`. `STATUS.md` and `src/risk.py` both state these are
  training-load indicators, not medical claims — that framing must
  survive contact with marketing and terms of service.
- **Signage, transparency, and a DPIA/PIA** per site.

**Lift: L, and it gates go-live — this cannot be retrofitted.**

### 1.15 Monitoring, alerting, and on-call

**Exists:** `logging.basicConfig(level=logging.INFO)` to stdout, a
progress log every 300 frames, some `logger.warning` calls on lost tracks
and cross-view inconsistency.

**Needed:** structured logs shipped off-device; metrics (frames processed,
dropped, detections/frame, identity-resolution rate, Re-ID enrollment
rate, triangulation-fallback rate, per-stage latency); product-quality
alerts, not just liveness (camera dark, camera moved, identity
fragmentation spiking, a station producing zero reps during business
hours); SLOs; incident response and on-call; a status/comms path for
operators. **Lift: M–L.**

### 1.16 Engineering hygiene prerequisites

No automated test suite (validation scripts for A1–A4 were deliberately
kept in scratchpads and never committed, per `ROADMAP.md`), no CI, no
reproducible packaging/containerization, no secrets management, no
environments (dev/staging/prod), no release process. **Lift: M.**

---

## Part 2 — Phased engineering roadmap

Sequencing principle, consistent with how Phases A–D were reasoned about
in `ROADMAP.md`: **do the work that has no external dependency first, and
do not spend an irreplaceable input (a pilot gym's goodwill and its
members' trust) on foreseeable failures.** A failed pilot is more
expensive than a delayed one.

```
Phase D (real footage validation)  ──┐
Phase E (RTSP sync, Jetson, kiosk) ──┤
                                     │
Phase F (persistence & identity spine)  ─┐  no gym required,
Phase G (privacy & governance gate)     ─┤  start in parallel now
Phase L (model/coverage expansion)      ─┘  (continuous)
                 │
                 ▼
        Phase H (always-on floor runtime)   ← absorbs E1/E2
                 │
                 ▼
        Phase I (backend API + operator console + PILOT GYM)  ← absorbs E3
                 │
                 ▼
        Phase J (member app: plans, adherence, content)
                 │
                 ▼
        Phase K (multi-tenant scale-out, billing, fleet ops, SRE)
```

Phase G is drawn parallel to F but is a **hard gate on H**: no real
member's body may be processed under a commercial arrangement before G's
minimum set lands.

### Phase F — Persistence and identity spine

**Goal:** make one pipeline run durable, wall-clocked, crash-survivable,
and attributable to a stable member — without changing any CV behaviour.

**Why here:** every later phase reads from this. It needs no gym, no
hardware, and no footage — it can start today against `test_videos/` and
Fit3D clips. Doing it before the pilot means the pilot generates real data
instead of throwaway JSON.

**Prerequisites:** none.

- **F1. Wall-clock time base.** Add an absolute session start time and
  carry `wall_time = session_start + frame_idx/fps` alongside the existing
  relative clock. Do not remove the relative clock — `src/state_machine.py`,
  `src/form.py`, and the validation tooling all depend on it. Reconcile
  with `src/session.py`'s independent `time.time()` usage.
- **F2. Session, visit, and person as durable records.** Introduce
  `session_id`, `visit_id`, `member_id`. Stop deriving output filenames
  from `--names` alone (today a re-run silently overwrites).
- **F3. Incremental event emission.** Replace "one JSON at process exit"
  with an append-only event stream: `person_observed`, `identity_bound`,
  `set_started`, `rep_completed`, `set_ended`, `risk_assessed`,
  `camera_health`. Write locally first (durable spool), ship second. The
  single most valuable structural change in the phase — decouples
  analysis from delivery and makes crash recovery possible.
- **F4. Bounded memory.** Cap or window the in-RAM `pd['angles']`
  accumulation so an 8-hour run doesn't grow monotonically. `src/form.py`
  and the classifier only ever read trailing windows
  (`CLASSIFY_WINDOW_SECONDS = 6.0`, per-rep `[t0, t1]` windows), so a
  bounded ring buffer plus streamed-out cold history is
  behaviour-preserving. **Verify against `src/signature.py` and
  `src/risk.py` before implementing** — `assess_track` operates over the
  whole set.
- **F5. Storage layer.** Relational store for members, visits, sessions,
  sets, reps, form scores, risk assessments (small, queried constantly).
  Separate object/time-series store for angle series (large, append-only,
  rarely read). Tenant column on every table from day one.
- **F6. Fix the per-joint downsample drift.** `_downsample_series` in
  `src/output.py` — emit on a shared frame grid with explicit nulls,
  rather than a per-joint independent clock. This bug already produced a
  false finding once (`ROADMAP.md` C3). Re-run Panoptic and Fit3D
  validations afterward to confirm error figures are unchanged.
- **F7. Identity binding model.** Two layers, explicitly separated:
  - *Durable layer:* `member_id`, established by an **authenticated
    check-in event** (QR scan, app NFC/BLE, kiosk tap), not by appearance.
  - *Ephemeral layer:* the existing `SessionGallery`, rescoped to a visit,
    binding tracklets → `visit_person`. Add a
    `bind_visit_person_to_member(visit_person_id, member_id, evidence)`
    operation recording *how* the binding was made and its confidence.
  - **Persist no embeddings across visits.** Both the technically honest
    choice (clothing-dominated embedding) and the compliance-cheap one.
  - Make **unattributed people first-class**: guests, staff, and
    non-consenting bystanders need a defined disposition.
- **F8. Test and CI foundation.** Create `tests/`. Recover the A1–A4
  validation scripts from scratchpad history if possible, or rewrite them.
  Add CI running unit tests plus a smoke run of `pipeline.py`.

**Exit criteria:**
1. A pipeline run killed with `SIGKILL` at minute 20 of a 30-minute clip
   loses at most the last N seconds of data; everything before is
   queryable from the database.
2. Two runs against the same output target no longer overwrite each other;
   every rep is retrievable by `(member_id, visit_id, timestamp)` in
   absolute wall-clock terms.
3. An 8-hour continuous run shows flat, not growing, resident memory.
4. Panoptic and Fit3D validation figures re-run post-F6 are unchanged
   within noise (proving F didn't touch CV behaviour).
5. `tests/` exists, CI is green, and the A1/A2/A3 identity/fusion
   assertions run automatically.

### Phase G — Privacy, consent, and data governance gate

**Goal:** establish the legal and ethical envelope *before* any real
member's body is processed under a commercial arrangement.

**Why here:** the current system's compliance posture is good only
because it stores nothing. Phase F deliberately destroys that. G must
close behind it — retrofitting consent onto collected data is not
possible.

**Prerequisites:** F5/F7 designs (not necessarily their implementation).

- **G1. Data inventory and flow map.** Every category the system produces
  (raw frames, crops, embeddings, keypoints, joint angles, reps, form
  scores, risk signals, names): where produced, stored, how long, who can
  read it, how it's deleted.
- **G2. Legal review and jurisdiction scoping.** Which markets. Whether
  appearance embeddings and skeletal keypoints constitute biometric
  identifiers in each. GDPR Art. 9 analysis and lawful basis. DPIA for the
  pilot site. BIPA/CUBI applicability if US. Minors policy.
- **G3. Consent lifecycle, engineered.** Versioned consent records; a
  machine-readable consent state the edge runtime enforces at processing
  time (not just at reporting time); working withdrawal that stops future
  processing and triggers deletion; a bystander/non-member policy with
  signage.
- **G4. Retention and deletion, implemented and tested.** Default: **raw
  video never persisted, never leaves the edge device.** Per-category
  TTLs. An erasure job that provably removes a member from the relational
  store, angle-series store, backups, logs, and any derived training set.
  Test it by actually deleting a test member and auditing.
- **G5. Access control and audit.** Role-scoped access — gym staff,
  member, support, engineer. Every access to member-level body data
  logged. Gym staff must not have unrestricted access to every member's
  biomechanics history.
- **G6. Kill the unauthenticated surface.** `src/dashboard.py` must not
  exist in any deployment, even a "temporary" pilot. Either bind
  loopback-only behind an authenticated proxy, or replace it outright in
  Phase I.
- **G7. Product-claim boundaries.** Written, agreed with legal, binding on
  marketing: `src/risk.py` outputs are training-load indicators, not
  injury prediction or medical advice; form scores are guidance, not
  certification; the supported-exercise list is explicit; adherence is
  evidence-of-observation, never evidence-of-absence.
- **G8. Training-data provenance policy.** `ROADMAP.md` D4 proposes
  feeding real footage back into `training_data/` — the right ML instinct
  and a compliance landmine. Decide now: separate consent for training
  use, opt-out honoured, a documented position on erasure vs. a trained
  model. Confirm the license position on `models/exercise_clf.npz`.

**Exit criteria:**
1. Signed-off DPIA/PIA for the pilot site, and a written legal opinion on
   biometric-identifier status in the target jurisdiction.
2. Consent capture, enforcement, and withdrawal work end-to-end on a test
   member, demonstrated.
3. An erasure request removes a test member from every store including
   backups and derived sets, verified by audit query.
4. No unauthenticated network endpoint exposes member data or gym-floor
   imagery in any environment.
5. Retention TTLs enforced by an automated job, not policy documents.
6. Public-facing claims reviewed against G7 and the `STATUS.md`
   limitations list.

### Phase H — The always-on floor runtime

**Goal:** convert the CLI batch script into a supervised, long-running,
self-healing service that runs a gym floor for a full trading day
unattended, on hardware someone will actually buy.

**Why here:** the pilot cannot happen without it. Absorbs `ROADMAP.md` E1
(RTSP timestamp sync) and E2 (Jetson port and throughput).

**Prerequisites:** Phase D findings, F1–F4, E1/E2.

- **H1. Service lifecycle.** Replace "start threads → join → write JSON →
  exit" with a supervised process: config-driven camera set, health
  endpoint, graceful reload, per-camera restart on failure without killing
  the floor, a spool that survives restarts.
- **H2. RTSP ingest and timestamp sync (E1).** `src/fusion.py`'s docstring
  is explicit: "Live RTSP streams need timestamp alignment upstream; not
  handled here yet." A single dropped frame on one live stream permanently
  desynchronizes a fused station with no error raised. Needs real
  timestamp-based alignment, reconnection with backoff, and a defined
  behaviour when a view falls behind.
- **H3. Jetson port and honest capacity measurement (E2).** Revisit the
  CPU-delegate forcing in `src/pose.py` (its rationale is a macOS
  PyTorch/Metal conflict, irrelevant on Jetson). Evaluate GPU delegate,
  TensorRT, quantization. Then **measure, do not estimate**: frames/
  second/camera at 1, 3, 5, 10, 15 people in frame; the resulting
  cameras-per-device number; the accuracy cost of every throughput knob.
- **H4. Address the linear-in-people pose cost.** Dominant scaling term on
  a busy floor. Evaluate batching crops through one inference call,
  reducing pose rate for people not in an active set, and a bottom-up
  multi-person model. A genuine research-flavoured sub-project.
- **H5. Back-pressure and degradation policy.** Define what the system
  drops first when it can't keep up, and make the choice explicit and
  observable: frame rate before accuracy, 3D fusion before 2D counting,
  visualization before analysis.
- **H6. Per-site and per-camera configuration.** Break `src/config.py`'s
  global constants into a layered resolution (defaults → tenant → site →
  camera), loaded at runtime.
- **H7. Calibration as a managed artifact + drift detection.** Move rig
  calibration off local `.npz` paths into versioned, site-scoped records.
  A candidate signal: a sustained rise in `cross_view_consistent()`
  rejection rate at a fused station is exactly what a bumped camera looks
  like, and `src/fusion.py` already logs that event.
- **H8. Observability.** Structured logs off-device; the metrics listed in
  1.15; per-camera health heartbeat.

**Exit criteria:**
1. Eight continuous hours of unattended operation on target hardware
   against live RTSP feeds, with a documented, measured cameras-per-device
   figure at realistic occupancy.
2. Pulling one camera's network cable: that camera recovers automatically,
   others unaffected, the gap is visible in monitoring.
3. Fused-station accuracy on live RTSP within a stated tolerance of the
   same scene from pre-synchronized recordings.
4. Killing the service mid-day loses at most N seconds and auto-resumes.
5. Nudging a calibrated camera raises a drift alert without a human
   noticing first.
6. Back-pressure behaviour under 2× overload is documented, observable,
   matches the H5 policy.

### Phase I — Backend API, operator console, and the pilot gym

**Goal:** one real gym, real members, real money-adjacent operation. The
first honest test of the product thesis.

**Prerequisites:** F, G (mandatory), H. Absorbs E3 (kiosk/QR check-in).

- **I1. Control-plane API.** Authenticated, versioned, tenant-scoped.
  Device credentials for edge event ingest (idempotent, retry-safe,
  replay-resistant); user credentials for reads.
- **I2. Check-in as the identity anchor (E3).** Replace the current GET
  endpoint with an authenticated flow producing a signed check-in event
  (`member_id`, timestamp, location). Solve the association problem: which
  `visit_person` is this member? Options, increasing robustness — a
  spatial+temporal gate, member-confirmed in-app disambiguation, dedicated
  entry-camera framing. **This binding is lift #3 and deserves dedicated
  design time.** Define and measure a mis-binding rate; treat mis-binding
  as a P1 incident class.
- **I3. Operator console.** Replaces `src/dashboard.py`: floor/camera
  health, calibration/drift status, check-in state, aggregate utilization,
  incident view, consent administration, role-scoped access.
- **I4. Member read API.** Session history, sets, reps, form scores,
  trends, shaped for app screens.
- **I5. Ground-truth accuracy audit.** The most important deliverable of
  this phase. Human observers manually count and label a statistically
  meaningful sample of real member sets at the pilot site; compare against
  system output; publish per-exercise, per-station, per-camera-
  configuration precision/recall. **This produces the number the product
  is allowed to promise.**
- **I6. Support and incident process.** A member says "these aren't my
  reps" — who can look, what can they see, how is it corrected and
  audited?

**Exit criteria:**
1. One gym live for 30 consecutive operating days.
2. A published, honest, per-exercise accuracy table from I5's
   human-ground-truth audit, including the exercises/conditions where the
   system does poorly.
3. Measured identity mis-attribution rate below an explicitly stated,
   pre-committed threshold.
4. Zero unauthenticated data-bearing endpoints; a passing external
   security review.
5. Gym operator can run the site day-to-day without engineering
   intervention.
6. A member exercises data access and erasure, end-to-end, successfully.

### Phase J — Member app: plans, adherence, and content

**Goal:** the founder's product vision, made real — automatic tracking,
right/wrong feedback with a score, a plan built in-app, adherence against
it, a demo-video library.

**Why here:** depends on I5's accuracy table. Building plan/adherence UX
before knowing the true per-exercise accuracy risks designing a feature
the pipeline cannot honestly support.

**Prerequisites:** Phase I, especially I5.

- **J1. App foundation.** Accounts, membership, auth, onboarding, offline
  tolerance.
- **J2. Automatic session view.** Sets, reps, per-rep form, trends across
  visits — must render *confidence and coverage*, not just numbers.
- **J3. Form feedback and the accuracy score.** Today's `src/form.py`
  score is self-referential (Part 0.7). Two honest options: present it as
  "consistency and control within your set," or complete the
  reference-signature path (`src/signature.py`, `tools/build_reference.py`,
  `ROADMAP.md` D3) for an absolute standard. **The second is required if
  the product promises "are you doing it right."** `src/config.py` itself
  warns that a reference from a different camera angle "reads perspective
  differences as form deviations" — real content-and-validation work, not
  a code change.
- **J4. Plan builder.** Templates and custom plans, exercise catalog
  aligned to the classifier taxonomy, unsupported-but-catalogued exercises
  clearly marked as self-logged.
- **J5. Adherence engine.** Reconcile prescribed vs observed using the
  four-state observability model from 1.7. Only `observed-absent` may
  drive a negative statement. Manual self-logging as the escape hatch for
  everything cameras can't see — a core part of an honest product, not a
  fallback.
- **J6. Content library.** Demo videos per catalog exercise,
  transcode/CDN/offline cache, deep-linked from form cues
  (`src/form.py`'s `CORRECTIVE_CUES` already map naturally onto "watch
  how").
- **J7. Notifications.** Reminders, session summaries, plan nudges, with
  quiet hours/preferences; adherence-derived messaging held to J5's
  evidentiary standard.
- **J8. Real-time vs per-session feedback decision.** Per-session is
  achievable now. Real-time in-workout coaching adds a latency budget, a
  delivery channel, and a UX question — treat as a separate, later,
  explicitly-scoped increment.

**Exit criteria:**
1. A pilot member can build a plan, train, and see accurate reps, form
   feedback, and adherence for that plan the same day.
2. Adherence never asserts non-performance for an exercise/station the
   system could not observe — verified by adversarial testing.
3. The form/accuracy score is either backed by a validated reference
   signature or worded to match what it actually measures.
4. Every catalog exercise has a demo video; every camera-untrackable
   exercise is visibly marked as self-logged.
5. Measured member retention/engagement over a defined pilot window, plus
   qualitative feedback on whether the coaching is genuinely useful.

### Phase K — Multi-tenant scale-out

**Goal:** gyms two through N, without engineering being in the loop for
each one.

**Prerequisites:** Phase I proven at one site, Phase J shipped.

- **K1. True multi-tenancy.** Tenant isolation enforced and *tested* (a
  cross-tenant read attempt must fail, in an automated test). Per-tenant
  configuration, models, catalogs, branding.
- **K2. Billing and subscriptions.** Per 1.10, including service-credit
  policy for camera downtime.
- **K3. Fleet operations.** Device inventory, OTA updates with staged
  rollout/rollback, remote diagnostics, spares/RMA, install-partner
  tooling.
- **K4. Site-survey and commissioning product.** Turn `CAMERA_PLACEMENT.md`
  and `CAPTURE_PROTOCOL.md` from documents a human follows into a guided
  workflow that *validates* compliance at install: feet-in-frame
  verification, mirror-in-frame detection, camera-spacing check,
  calibration capture and acceptance. The difference between a 10-site
  business and a 100-site one.
- **K5. SRE.** SLOs, on-call rotation, runbooks, incident review, status
  page, capacity planning.
- **K6. Per-site model/threshold adaptation.** New sites need tuning
  (lighting, ceiling heights, equipment, clientele) as a supported
  operation with a validation harness, not a code fork.

**Exit criteria:**
1. A new gym goes from contract to live using documented workflows, with
   a target commissioning time and no bespoke engineering.
2. Cross-tenant isolation verified by automated test and external
   penetration test.
3. Fleet update rolled out and rolled back across multiple sites without a
   member-visible incident.
4. On-call and SLOs operating with a reviewed incident history.
5. Billing reconciles cleanly, including a downtime-credit case.

### Phase L — Model and coverage expansion (continuous, parallel)

Not a sequential phase — a track that runs alongside F–K and feeds each.
Sourced directly from the existing `ROADMAP.md` backlog and `STATUS.md`
limitations.

- **L1. Hip-driven rep counter.** Already in the `ROADMAP.md` backlog.
  Unlocks sit-ups (currently `CLASS_FAMILY['situp'] = 'none'`) and
  improves hinge movements. Directly expands what the product can promise.
- **L2. Expand trained classifier coverage.** Currently 7 trained classes;
  `hinge`, `lunge`, `curl`, `row` are heuristic-only. Domain shift is a
  live concern — `FIT3D_UTILIZATION_PLAN.md` Track B records the trained
  classifier badly misclassifying Fit3D footage in a small sample, and
  correctly notes the fix **cannot** be Fit3D fine-tuning (academic
  license). Real gym footage from the pilot is the licensed path, subject
  to Phase G8.
- **L3. Reference signatures for absolute form scoring.** Prerequisite for
  J3's honest "accuracy score." Per-exercise, built from good-form
  footage, same-camera or 3D.
- **L4. Mirror dead-zone masking.** `ROADMAP.md` A5 explicitly backlogs a
  per-camera polygon mask as "a machine-enforced backstop for whenever the
  placement rule isn't followed perfectly." **After Phase H there is an
  installation** — given commercial gyms are mirror-walled, this likely
  graduates from backlog to requirement.
- **L5. Detector upgrade under real occlusion.** yolov8n@640 detects both
  people only 30% of the time on heavily-occluded two-person footage vs
  61% for yolov8s@960. Worth revisiting once H3's real hardware numbers
  are in hand. Also resolve the AGPL question from 0.10(b).
- **L6. 2-camera fused stations.** `ROADMAP.md` A3's accepted residual
  limit (1-DOF epipolar ambiguity at exactly 2 views) means 2-camera
  stations carry a real blind spot. `CAMERA_PLACEMENT.md` rule 4 already
  prefers 3+. Worth quantifying so sales knows what a 2-camera station can
  and cannot claim.

---

## Part 3 — Architecture recommendations

### 3.1 Target shape

Three tiers, with a deliberate boundary between them:

```
EDGE (one per gym site)
  Floor Runtime Service (evolved pipeline.py)
    ingest workers   -> RTSP + timestamped frames
    inference pool   -> detector + pose (shared, batched)
    analysis actors  -> per-person state (state_machine, form,
                         risk, classifier, fusion)
    visit gallery    -> src/session.py, visit-scoped
    emitter          -> durable local spool -> upload

  RAW FRAMES NEVER LEAVE THIS BOUNDARY
        |  events + skeletons only
        v
CONTROL PLANE (cloud, multi-tenant)
  Ingest API (device auth, idempotent)
  Core API   (user auth, tenant-scoped)
  Relational store: members, visits, sets, reps, plans, form
  Bulk store: angle series, skeletons
  Plan/adherence engine, notifications, billing, catalog
        |
        v
  Member app  |  Operator console  |  Content CDN
```

### 3.2 Decomposing `CameraProcessor.run()`

Today that one method owns capture, detection, Re-ID resolution, pose,
smoothing, angles, two state machines, classification, form scoring,
visualization, dashboard push, and JSON writing — as one 250-line loop
with all state in local dicts. A perfectly reasonable research script and
a poor service.

Split along the seams the code already implies:

1. **Ingest** — one worker per camera; owns `cv2.VideoCapture`,
   reconnection, and stamping each frame with a real time (H2). Emits
   `(camera_id, wall_time, frame)`.
2. **Inference** — a shared pool owning models rather than one
   `PersonDetectorTracker` + `PoseEstimator` per camera thread. This is
   where batching (H4) becomes possible; today's per-camera model
   instances make it impossible by construction. Constraint:
   `PersonDetectorTracker` explicitly holds per-camera tracker state
   (`persist=True`), so **tracker state must stay per-camera even if model
   weights are shared** — `HANDOVER.md` (2026-08-05 entry) records a bug
   caused by exactly this (a shared ByteTrack instance across 4 feeds
   corrupting tracker state).
3. **Analysis** — per-person stateful actors. The existing `_init_person()`
   dict is already effectively an actor's state; make it one, visit-scoped
   rather than process-scoped.
4. **Emission** — events out (F3), not a file at the end.

Keep `src/state_machine.py`, `src/angles.py`, `src/form.py`, `src/risk.py`,
`src/signature.py`, `src/triangulation.py` **untouched**. They are pure,
well-tested, and carry the project's validated behaviour. The refactor
should be entirely in the orchestration layer, with the Panoptic/Fit3D/
RepCount validations re-run as the regression gate.

### 3.3 Edge vs cloud inference: run inference at the edge

Recommendation: **edge**, with cloud reserved for aggregation, API, and
model distribution. Three grounded reasons, in order of weight:

1. **Compliance.** If raw frames never leave the site, the cloud never
   holds video of people's bodies, and the regulatory surface shrinks
   enormously — DPIA scope, breach exposure, cross-border transfer,
   BIPA/GDPR analysis all get materially simpler. It preserves the honest
   version of the property `README.md` currently claims. Retrofitting
   this later is impossible.
2. **Bandwidth.** `DEVELOPMENT.md` estimates ~20 cameras for full coverage
   of a university gym, ~10 for a 2D-only MVP. Ten to twenty 1080p streams
   is a sustained multi-tens-of-Mbps upstream commitment, 12+ hours a day,
   forever. Skeleton and event data is orders of magnitude smaller.
3. **Failure mode.** A gym with a flaky uplink still tracks workouts and
   syncs later. A cloud-inference design goes dark.

**The cost:** H3's unmeasured hardware envelope becomes the binding
constraint on the whole business model. If real Jetson throughput at real
occupancy means one device per 2 cameras rather than per 4, per-site
hardware cost roughly doubles. **This is why H3 is an exit-criteria-
bearing measurement, not a footnote.**

Narrow cloud-inference exceptions worth keeping open: a short-retention,
opt-in clip escrow for disputed sessions; offline reprocessing of
consented footage for model improvement (Phase L, gated by G8).

### 3.4 Identity across visits: bind at check-in, never persist embeddings

The single most consequential architectural call in the plan.

**Do not** persist `SessionGallery` embeddings between visits. Technically,
the embedding is ImageNet features plus a torso HSV histogram, explicitly
designed around "clothing stays constant" within a session. Legally, a
stored appearance template derived from a person's body is the archetype
of a regulated biometric identifier; the current session-only design is a
genuinely strong compliance position that should be preserved
deliberately, not lost by accident.

**Instead, three layers:**

| Layer | Scope | Mechanism | Persisted? |
|---|---|---|---|
| Tracklet | seconds–minutes | ByteTrack (`src/detector.py`) | No |
| Visit person | one visit | `SessionGallery` + `ProvisionalIdentity` (unchanged) | No (RAM only) |
| Member | forever | authenticated check-in → `bind(visit_person -> member_id)` | Yes (ID + binding record; no body data) |

Consequences to design for:
- `REID_STALE_SECONDS = 1800` means a member gone 40 minutes re-enrolls as
  a new `visit_person` — fine under this model, it just needs a
  re-binding path (app re-check-in, station-local tap).
- The binding event needs recorded evidence and confidence, and a
  correction path (I6). Mis-binding must be a monitored, alertable rate.
- Unbound `visit_person` records need a defined disposition.
- Every rep in the database should carry its binding provenance, so a
  disputed session can be adjudicated rather than argued.

### 3.5 Data model shape

- **Relational (hot):** tenant, gym, site, camera, station, calibration,
  member, membership, consent, visit, visit_person, binding, session, set,
  rep, form_score, risk_assessment, plan, plan_item, scheduled_session,
  adherence_record. Small rows, high query volume, tenant column on every
  table.
- **Bulk (cold):** angle series, 3D skeletons, valgus series. Written
  once, read rarely, TTL'd aggressively. Keyed by session; never joined
  per-frame in the relational store.
- **Event log:** the append-only stream from F3, source of truth for
  reconstruction and late-arriving edge data.

Two schema rules learned directly from this repo: **(a)** carry absolute
wall-clock time *and* the source-relative clock on every record — the
relative clock is what the validated algorithms use, the absolute one is
what the product needs; **(b)** do not model angle series as
joint-aligned frames until F6 lands, or the per-joint drift in
`src/output.py` will silently corrupt every downstream aggregate.

### 3.6 Configuration

`src/config.py` should become the *default layer* of a resolved
configuration (defaults → tenant → site → camera), loaded at runtime.
Keep current values as defaults verbatim so `tools/benchmark_repcount.py`,
`tools/validate_panoptic.py`, and `tools/validate_fit3d.py` remain
reproducible against published figures. Every resolved config should be
versioned and attached to the sessions it produced.

### 3.7 Model serving

Keep models in-process at the edge. The real work is H3/H4: delegate/
TensorRT, batching, and the linear-in-people pose cost. Add model
versioning with per-site pinning and rollback, and a validation harness
that runs the existing Panoptic/Fit3D/RepCount benchmarks against any
candidate model before it can be pinned anywhere — the project already has
unusually good benchmark infrastructure in `tools/`; turning it into an
automated model-acceptance gate is cheap and high-value.

---

## Part 4 — Key technical risks

Product-specific risks — physical space, real bodies, paying members —
not generic software risk.

### 4.1 Accuracy risks that constrain what an MVP may promise

**R1 — Rep-count accuracy is not yet a product number.** Current
authoritative benchmark (`ROADMAP.md` B1): RepCount Part-A, all 152
videos, **MAE 0.742, OBO 22.4%**; gym-core classes squat 44.4%,
front_raise 33.3%, pull_up 36.8%, push_up 31.2% OBO — uncontrolled internet
footage, not `CAMERA_PLACEMENT.md`-placed cameras. On the project's own
purpose-shot footage results were far better. Both facts are true, neither
is a product number. **Only Phase I5's human-ground-truth audit produces
the number marketing is allowed to use.**

**R2 — Bench press cannot be reliably counted head-on.** `STATUS.md`:
counting is weak, "needs a side camera angle, not a code fix";
`CAMERA_PLACEMENT.md` rule 2 adds that 45° is insufficient — needs a true
side-on view. One of the most-performed exercises in a commercial gym.

**R3 — Sit-ups and hip-driven movements count zero, by design.**
`CLASS_FAMILY['situp'] = 'none'`. Correct engineering choice, and a
product hole.

**R4 — Mirrors are a total blind spot, and commercial gyms are
mirror-walled.** `ROADMAP.md` A5: nothing in the pipeline can distinguish
a reflection from a person; two failure paths (contamination of a real
person's state, or a phantom identity double-counting reps).
`CAMERA_PLACEMENT.md` rule 3 makes "no mirrors in any camera's frame" a
hard rule with no partial credit. **This may be physically unsatisfiable
in a typical commercial free-weight area** — the highest-probability
physical-deployment surprise in this plan.

**R5 — Feet-in-frame is required and conflicts with crowded floors.**
Degradation is silent, not errored — plausible wrong numbers rather than a
flag.

**R6 — Crowding and occlusion.** yolov8n@640 detected both people only
30% of the time on heavily-occluded two-person footage. A commercial
floor is many-person occlusion continuously.

**R7 — Domain shift, three ways.** RepCount YouTube footage vs. Fit3D
studio footage (already recorded as a bad misclassification pattern in a
small sample) vs. a real gym vs. each site's own lighting/geometry. The
obvious fix (fine-tune on Fit3D) is license-blocked.

**R8 — Form scores are self-referential today.** A "form score of 82"
largely means "consistent with your own recent motion," not "82%
correct." The product vision promises right/wrong plus an accuracy score.

**R9 — 2-camera fused stations carry an unclosable blind spot.**
`ROADMAP.md` A3's accepted residual: at exactly 2 views a wrong cross-view
match can measure 0.6px — indistinguishable from noise. Not fixable by
tuning.

### 4.2 Identity, trust, and attribution risks

**R10 — Mis-attribution is now a trust failure, not just a data error.**
`src/session.py` already names it "the worst failure mode." As a product,
wrong attribution means a member sees someone else's workout, or their PR
is credited to a stranger. With billing attached, it becomes a dispute.

**R11 — Conservative matching produces fragmentation, which looks like
data loss.** A2's design deliberately enrolls a new anonymous person
rather than guess; in a crowded gym with similarly-dressed members, a
visit may fragment into several unbound records.

**R12 — Adherence tracking risks accusing paying members.** False
negatives are structurally guaranteed by R2–R6.

**R13 — Bystanders who never consented.** Guests, staff, cleaners,
contractors, minors — currently silently enrolled as `person_N`.

### 4.3 Platform, operational, and legal risks

**R14 — The unauthenticated HTTP surface.** `src/dashboard.py` binds
`0.0.0.0` and serves live gym-floor JPEGs, a full identity roster, and a
state-mutating `GET /checkin` with no auth, TLS, or audit. On a gym's flat
network, that is a live video feed of people exercising available to
anyone on the LAN.

**R15 — Biometric-regulation exposure.** BIPA's private right of action is
the highest single-cost risk; GDPR Art. 9 plus a mandatory Art. 35 DPIA
applies in Europe/UK. The current system is in a strong position precisely
because it persists nothing — Phase F is what creates the exposure.

**R16 — Health/injury claim creep.** `src/risk.py` emits `risk_level:
high` with signals named `fatigue_form_decline` and `chronic_asymmetry`.
Marketing pressure to call this "injury prevention" will be constant, and
crossing that line changes the regulatory and liability picture.

**R17 — Silent calibration drift.** A bumped camera invalidates the rig
with no automatic detection today. A gym floor bumps cameras.

**R18 — Data loss from the current durability model.** No DB, in-memory
unbounded state, one write at process exit. A crash at minute 80 of a
90-minute session loses the whole session — for a member, that's their
workout gone.

**R19 — Unknown unit economics until H3 measures throughput.** 0.22
s/frame for 4 views with one person is the only measurement in the repo;
pose is linear in people; Jetson is entirely unmeasured. This number
determines hardware cost per site, which determines whether the business
model works.

**R20 — Third-party licensing.** Ultralytics YOLOv8 (AGPL-3.0 with a
commercial option) is the shipped detector; training-data licenses need
confirming for the shipped classifier.

**R21 — No test suite, no CI, no packaging.** Everything in Phases F–K is
a refactor of validated behaviour, and there is currently no automated way
to prove the refactor didn't break it.

### 4.4 What an MVP can honestly promise

**Can promise (subject to I5 confirming at the site):**
- Automatic counting of squats and knee-driven lower-body work, and
  elbow-driven upper-body work, at properly placed, mirror-free,
  feet-in-frame stations.
- Per-set consistency and control feedback (tempo, symmetry, ROM
  consistency, trunk lean) with actionable coaching cues.
- Session history across visits, with per-set confidence and coverage
  shown.
- True 3D joint angles and knee valgus at 3+ camera fused stations.
- A plan builder, and adherence *for observed activity*, with self-logging
  for everything else.
- A demo-video library for the full exercise catalog.

**Must not promise at MVP:**
- Reliable bench-press counting without a true side camera (R2).
- Any sit-up or core-flexion counting (R3).
- Coverage of mirror-adjacent areas (R4).
- An absolute "correctness" percentage, until L3/J3 lands (R8).
- Injury prediction or any medical claim (R16).
- Adherence assertions about unobserved activity (R12).
- Any headline accuracy figure before I5 produces one (R1).

---

## Appendix — Files referenced

Docs read: `ROADMAP.md`, `STATUS.md`, `DEVELOPMENT.md`, `README.md`,
`CAMERA_PLACEMENT.md`, `FIT3D_UTILIZATION_PLAN.md`, `HANDOVER.md`.

Code read: `pipeline.py`, `requirements.txt`, and in `src/`: `camera.py`,
`fusion.py`, `session.py`, `reid.py`, `output.py`, `dashboard.py`,
`config.py`, `state_machine.py`, `form.py`, `risk.py`, `pose.py`,
`detector.py`, `exercise_classifier.py`.

Confirmed absent: `tests/`, `.github/`, `Dockerfile`, `docs/`,
`models/references/` (only `models/exercise_clf.npz` exists).

Files with specific outstanding defects named in this plan: `src/output.py`
(per-joint downsample clock drift, F6), `src/dashboard.py` (unauthenticated
surface, G6), `src/config.py` (global constants blocking per-site tuning,
H6).

No files were modified while researching this plan.
