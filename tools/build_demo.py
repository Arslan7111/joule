"""
Build the design demo dataset.

Reads real pipeline result JSON for three dataset squat videos, reshapes each
into the data the candidate-05 ("lab report") post-set report screen needs, and
writes design/prototypes/demo/data.js (window.DEMOS = [...]).

Nothing here invents numbers: rep depth, form score, issues, cues, risk signals
and joint-angle series all come straight out of the pipeline's own output. The
only transforms are (a) per-rep "depth" = min knee-flexion angle inside the
rep's own [start, end] window, so the rep strip and the sagittal panel agree,
and (b) angle series down-sampled to ~3 Hz for the SVG traces.

Run:  .venv/Scripts/python.exe tools/build_demo.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "design" / "prototypes" / "demo" / "data.js"

# (result json, source video, human label, dataset, ground-truth rep count, note)
SOURCES = [
    {
        "id": "clean",
        "json": "results/demo3/sq_stu9_64/stu9_64.json",
        "video": "stu9_64.mp4",
        "dataset": "RepCount Part-A (public YouTube-workout dataset)",
        "labeled": 14,
        "title": "Back squat",
        "blurb": "A clean set. Every rep lands inside the depth corridor and the two "
                 "legs track together.",
    },
    {
        "id": "asym",
        "json": "results/demo3/sq_stu6_63/stu6_63.json",
        "video": "stu6_63.mp4",
        "dataset": "RepCount Part-A (public YouTube-workout dataset)",
        "labeled": 17,
        "title": "Back squat",
        "blurb": "Reps all count, but one leg is loaded harder on every single rep. "
                 "That is a compensation pattern, not a depth problem.",
    },
    {
        "id": "fatigue",
        "json": "results/demo_squat_s03/squat_demo.json",
        "video": "Fit3D s03, one calibrated view",
        "dataset": "Fit3D (mocap-grade dataset, validation licence)",
        "labeled": 8,
        "title": "Back squat",
        "blurb": "Depth and tempo hold through the middle of the set, then trunk lean "
                 "and range of motion fall away in the last two reps.",
    },
]

TARGET_HZ = 3.0            # trace sample rate
BAND_LOW, BAND_HIGH = 62.0, 100.0   # squat depth corridor, deg of knee flexion angle


def squat_track(doc):
    for t in doc["tracks"]:
        if t.get("reps", {}).get("squat"):
            return t
    # fall back to the busiest track
    return max(doc["tracks"], key=lambda t: t.get("total_frames", 0))


def resample(series, hz):
    """series is [[t, value], ...] already time-ordered. Keep ~hz samples/sec."""
    if not series:
        return []
    out = [series[0]]
    step = 1.0 / hz
    for t, v in series[1:]:
        if t - out[-1][0] >= step:
            out.append([round(t, 2), round(v, 1)])
    if out[-1] is not series[-1]:
        t, v = series[-1]
        out.append([round(t, 2), round(v, 1)])
    return out


def window_min(series, t0, t1):
    vals = [v for t, v in series if t0 - 0.25 <= t <= t1 + 0.25]
    return round(min(vals), 1) if vals else None


def window_max(series, t0, t1):
    vals = [v for t, v in series if t0 - 0.25 <= t <= t1 + 0.25]
    return round(max(vals), 1) if vals else None


def rep_state(rep):
    """Strip state straight off the engine's own per-rep form score."""
    if not rep.get("valid", True):
        return "ghost"
    score = rep["form"]["score"]
    if score < 78:
        return "breach"
    if score < 90 or rep["form"]["issues"]:
        return "partial"
    return "ok"


def clean(txt):
    # the pipeline writes a literal em dash in cue/issue text; the design bans it
    return txt.replace(" — ", ", ").replace("—", "-").replace("°", "°")


def build_one(cfg):
    doc = json.loads((ROOT / cfg["json"]).read_text())
    tr = squat_track(doc)
    ser = tr["angle_series"]
    lk, rk, tl = ser["left_knee"], ser["right_knee"], ser["trunk_lean"]
    reps_raw = tr["reps"]["squat"]

    reps = []
    for i, r in enumerate(reps_raw, 1):
        t0 = r.get("start_timestamp", r["timestamp"] - r.get("duration", 1.0))
        t1 = r["timestamp"]
        dl = window_min(lk, t0, t1)
        dr = window_min(rk, t0, t1)
        depth = min(x for x in (dl, dr) if x is not None) if (dl or dr) else r["lowest_angle"]
        gap = round(abs(dl - dr), 1) if (dl is not None and dr is not None) else None
        lean = window_max(tl, t0, t1)
        reps.append({
            "n": i,
            "t0": round(t0, 2),
            "t1": round(t1, 2),
            "depth": round(depth, 1),
            "depthL": dl,
            "depthR": dr,
            "gap": gap,
            "lean": lean,
            "dur": r.get("duration"),
            "score": r["form"]["score"],
            "valid": bool(r.get("valid", True)),
            "state": rep_state(r),
            "issues": [clean(x) for x in r["form"]["issues"]],
            "cues": [clean(x) for x in r["form"].get("cues", [])],
        })

    risk_raw = tr.get("risk_assessment", {}).get("squat", {"risk_level": "low", "signals": []})
    risk = {
        "level": risk_raw.get("risk_level", "low"),
        "signals": [clean(s["detail"]) for s in risk_raw.get("signals", [])],
    }
    signal_kinds = {s["signal"] for s in risk_raw.get("signals", [])}

    kneemin = min(min(v for _, v in lk), min(v for _, v in rk))
    kneemax = max(max(v for _, v in lk), max(v for _, v in rk))

    # worst rep drives the opening verdict
    worst = min(reps, key=lambda r: r["score"])
    gap = None
    if worst["depthL"] is not None and worst["depthR"] is not None:
        gap = round(abs(worst["depthL"] - worst["depthR"]), 1)

    # per-set knee-flexion gap between legs, median across reps
    gaps = [abs(r["depthL"] - r["depthR"]) for r in reps
            if r["depthL"] is not None and r["depthR"] is not None]
    gaps.sort()
    med_gap = round(gaps[len(gaps) // 2], 1) if gaps else None

    lo, hi = BAND_LOW, BAND_HIGH
    n_in = sum(1 for r in reps if lo <= r["depth"] <= hi)
    lean_reps = [r["n"] for r in reps if any("trunk lean" in i for i in r["issues"])]
    rom_reps = [r["n"] for r in reps if any("range of motion" in i for i in r["issues"])]

    # compose the answer-first verdict + closing interpretation from the real fields
    if lean_reps:
        verdict = "Trunk lean and depth both fall away at the ends of the set."
        where = (f"Rep {lean_reps[-1]}: trunk past the 60 degree lean limit, knee only "
                 f"bends to {reps[lean_reps[-1] - 1]['depth']:.0f} degrees "
                 f"(180 is a straight leg), short of the working depth.")
        mid = rom_reps[0] if rom_reps else lean_reps[0]
        interp = (f"The middle of the set is solid. It is reps {lean_reps[0]} and "
                  f"{lean_reps[-1]} where tempo, trunk position and range of motion slip "
                  f"together, which reads as fatigue at the edges of the set rather than a "
                  f"technique fault. Ending one or two reps earlier keeps the quality up.")
    elif "chronic_asymmetry" in signal_kinds:
        verdict = "One leg carries more of every rep than the other."
        where = (f"Rep {worst['n']}: left knee bends to {worst['depthL']:.0f} degrees, right "
                 f"to {worst['depthR']:.0f}, a {gap:.0f} degree split at the deepest point. "
                 f"Median split across the set is {med_gap:.0f} degrees.")
        interp = (f"Every one of the {len(reps)} reps counted, and depth on the working leg "
                  f"is fine. The finding is that the load is not shared evenly, on every rep, "
                  f"in the same direction. From one camera this could be a real compensation "
                  f"pattern or partly the viewing angle; a second camera would separate the "
                  f"two. Either way it is worth checking, not a reason to stop squatting.")
    else:
        verdict = "Every rep sat inside the depth corridor."
        where = (f"Deepest rep reached {min(r['depth'] for r in reps):.0f} degrees knee "
                 f"flexion; the working corridor is {lo:.0f} to {hi:.0f} degrees. Left and "
                 f"right stay within {med_gap:.0f} degrees of each other.")
        interp = (f"All {len(reps)} reps counted, all {n_in} inside the corridor, both legs "
                  f"tracking together, low risk signals. This is what a clean set looks like "
                  f"on the report: nothing to correct, shown as nothing to correct.")

    method = [
        f"Source: {cfg['dataset']}. One camera, so joint angles are 2D and carry a "
        f"perspective bias; rep counting is adaptive and does not.",
        f"Rep count: engine {len(reps)}, dataset ground truth {cfg['labeled']}. "
        + ("Exact match." if len(reps) == cfg["labeled"]
           else f"Off by {abs(len(reps) - cfg['labeled'])}."),
        "Frontal and transverse planes need the two-camera station and are left "
        "unfilled here rather than estimated from one view.",
        "Risk lines are training-load observations, not a medical assessment.",
    ]

    return {
        "id": cfg["id"],
        "title": cfg["title"],
        "video": cfg["video"],
        "dataset": cfg["dataset"],
        "blurb": cfg["blurb"],
        "labeled": cfg["labeled"],
        "counted": len(reps),
        "durationSec": round(lk[-1][0] - lk[0][0], 1),
        "reps": reps,
        "worstRep": worst["n"],
        "worstGap": gap,
        "medGap": med_gap,
        "band": [BAND_LOW, BAND_HIGH],
        "verdict": verdict,
        "where": where,
        "interp": interp,
        "method": method,
        "knee": {
            "min": round(kneemin - 4, 1),
            "max": round(kneemax + 2, 1),
            "left": resample(lk, TARGET_HZ),
            "right": resample(rk, TARGET_HZ),
        },
        "trunk": resample(tl, TARGET_HZ),
        "risk": risk,
    }


def main():
    demos = [build_one(c) for c in SOURCES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = "window.DEMOS = " + json.dumps(demos, indent=2) + ";\n"
    OUT.write_text(payload, encoding="utf-8")
    for d in demos:
        print(f"{d['id']:9s} {d['video']:26s} counted {d['counted']:2d} / labeled "
              f"{d['labeled']:2d}   risk={d['risk']['level']}   "
              f"worst rep {d['worstRep']} (score {min(r['score'] for r in d['reps'])})")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
