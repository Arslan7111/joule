KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]

KEYPOINT_IDX = {name: i for i, name in enumerate(KEYPOINT_NAMES)}

# Standard 3-point joint angles (angle computed at the middle keypoint).
# left_shoulder / right_shoulder: arm elevation relative to torso.
ANGLE_DEFINITIONS = {
    'left_shoulder':  ('left_elbow',    'left_shoulder',  'left_hip'),
    'right_shoulder': ('right_elbow',   'right_shoulder', 'right_hip'),
    'left_elbow':     ('left_shoulder', 'left_elbow',     'left_wrist'),
    'right_elbow':    ('right_shoulder','right_elbow',    'right_wrist'),
    'left_hip':       ('left_shoulder', 'left_hip',       'left_knee'),
    'right_hip':      ('right_shoulder','right_hip',      'right_knee'),
    'left_knee':      ('left_hip',      'left_knee',      'left_ankle'),
    'right_knee':     ('right_hip',     'right_knee',     'right_ankle'),
}

# trunk_lean is computed separately (angle of shoulder–hip line from vertical).
# Wrist and ankle flexion cannot be computed from COCO-17 (no hand/foot keypoints).

# Which joints are biomechanically primary for each exercise type.
# All joints are always recorded; this field guides display and downstream analysis.
EXERCISE_ANGLES = {
    'squat': [
        'left_knee', 'right_knee',
        'left_hip', 'right_hip',
        'trunk_lean',
    ],
    'upper_body': [
        'left_elbow', 'right_elbow',
        'left_shoulder', 'right_shoulder',
        'trunk_lean',
    ],
    'both': [
        'left_shoulder', 'right_shoulder',
        'left_elbow', 'right_elbow',
        'left_hip', 'right_hip',
        'left_knee', 'right_knee',
        'trunk_lean',
    ],
}

# MediaPipe 33-landmark index → COCO-17 index
MP_TO_COCO = {
    0: 0,   # nose
    2: 1,   # left eye
    5: 2,   # right eye
    7: 3,   # left ear
    8: 4,   # right ear
    11: 5,  # left shoulder
    12: 6,  # right shoulder
    13: 7,  # left elbow
    14: 8,  # right elbow
    15: 9,  # left wrist
    16: 10, # right wrist
    23: 11, # left hip
    24: 12, # right hip
    25: 13, # left knee
    26: 14, # right knee
    27: 15, # left ankle
    28: 16, # right ankle
}

# COCO-17 skeleton connections for visualisation
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

# Fixed fallback thresholds — used until adaptive thresholds have enough data,
# or when adaptive mode is disabled.
TOP_THRESHOLD = 160.0
BOTTOM_THRESHOLD = 110.0
DEPTH_THRESHOLD = 100.0
HYSTERESIS_FRAMES = 2          # median smoothing already debounces; 2 keeps fast pulse reps countable

# Adaptive thresholds: each state machine learns the person's actual motion
# range (10th–90th percentile of the last ADAPTIVE_WINDOW_SECONDS of signal)
# and places thresholds at fractions of that range.  Camera angle and exercise
# style change the absolute angles a lot; the relative range is far more stable.
ADAPTIVE_THRESHOLDS = True
ADAPTIVE_WINDOW_SECONDS = 3.0  # short window re-learns quickly when rep amplitude changes (drop sets)
MIN_ANGLE_RANGE = 12.0        # deg of observed motion required before counting reps
TOP_FRACTION = 0.70           # top threshold    = lo + 0.70 * range
BOTTOM_FRACTION = 0.35        # bottom threshold = lo + 0.35 * range
DEPTH_FRACTION = 0.25         # valid-rep depth  = lo + 0.25 * range

# Median filter width (frames) applied to the angle signal before rep counting.
# Kills single-frame keypoint flicker without adding meaningful latency.
SMOOTHING_WINDOW = 5

OUTPUT_FPS = 30.0     # angle-series sampling in output JSON (30 = full rate)
BBOX_PADDING = 0.2
POSE_CONF_THRESHOLD = 0.5
LOST_TRACK_WARNING_SECONDS = 2.0
PROGRESS_LOG_FRAMES = 300          # log processing progress every N frames

# Automatic exercise classification (--exercises auto)
CLASSIFY_INTERVAL_SECONDS = 2.0    # re-classify each track this often
CLASSIFY_WINDOW_SECONDS = 6.0      # trailing window of angle data to classify on

# Locomotion rejection: walking/running produces long runs of fast uniform
# knee cycles that the rep counter would otherwise count as squats.
# Validated on treadmill footage (22 cycles @ 0.42s) vs drop sets (4 @ 0.6s):
# run length separates them cleanly.
LOCOMOTION_MAX_DURATION = 0.9      # s — a cycle faster than this is gait-like
LOCOMOTION_MAX_INTERVAL = 2.0      # s — gap between gait-like cycles (real sets pace ~3 s+)
LOCOMOTION_MIN_RUN = 6             # ≥ this many consecutive fast cycles = gait

# Person detection.  For reference, on heavily-occluded two-person footage
# the alternatives measured: yolov8n@640 30% both-detected, yolov8s@640 51%,
# yolov8s@960 61% (at 2–4× the compute, with more false positives at low conf).
DETECTOR_MODEL = 'yolov8n.pt'
DETECTOR_IMGSZ = 640
DETECTOR_CONF = 0.5

# Keep drawing a lost track's last box/skeleton for this many frames while
# ByteTrack's buffer keeps the ID alive.  0 disables coasting.
COAST_DISPLAY_FRAMES = 0

# A track must survive this many frames before it is drawn or enrolled in
# the Re-ID gallery.  1 = no probation.
MIN_TRACK_AGE_FRAMES = 1

# Person re-identification (session identity across frame exits and cameras)
REID_MATCH_THRESHOLD = 0.75    # cosine similarity to accept an identity match
REID_EMA_ALPHA = 0.10          # gallery embedding update rate
REID_SAMPLE_INTERVAL_SECONDS = 1.0   # extract an embedding this often per track

# Hard-example collection (--collect-hard): save crops where pose estimation
# failed or was low-confidence, for later labelling / fine-tuning.
HARD_EXAMPLE_CONF = 0.35           # mean keypoint visibility below this = hard
HARD_EXAMPLE_MIN_GAP_SECONDS = 1.0 # per-track throttle
HARD_EXAMPLE_MAX_PER_CAMERA = 300
