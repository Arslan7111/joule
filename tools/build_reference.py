"""Build a reference exercise signature from recorded good executions.

Run the pipeline on footage of a trainer (or your best member) performing an
exercise well, then point this tool at the result JSON(s):

    python tools/build_reference.py results/squat_rack_1.json \
        --exercise squat [--person person_1] [--critic 0.5 --dry-run]

Writes models/references/<exercise>.json.  On the next pipeline run, form
scoring compares every rep of that exercise against the reference and adds
deviation cues (src/signature.py); delete the file to turn it off.

--dry-run prints the mined signature (active/passive angles, per-entry
mean±std) without writing, so you can sanity-check what the reference learnt.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EXERCISE_ANGLES, REFERENCE_DIR   # noqa: E402
from src.signature import build_reference                # noqa: E402


def _pick_track(data: dict, person: str | None, family: str) -> dict | None:
    tracks = data.get('tracks', [])
    if person:
        tracks = [t for t in tracks if person in (t.get('person'), t.get('person_id'))]

    def n_good(t):
        return sum(
            1 for r in t.get('reps', {}).get(family, [])
            if r.get('valid') and not r.get('locomotion')
        )
    tracks = [t for t in tracks if n_good(t) > 0]
    return max(tracks, key=n_good) if tracks else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('results', nargs='+', type=Path,
                    help='pipeline result JSON(s) of good executions')
    ap.add_argument('--exercise', required=True,
                    help='exercise class the reference is for (squat, curl, ...)')
    ap.add_argument('--family', default=None, choices=['squat', 'upper_body'],
                    help='rep family to read reps from (default: squat for '
                         'squat/lunge/hinge, upper_body otherwise)')
    ap.add_argument('--person', default=None,
                    help='only use this person (person_id or checked-in name)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    family = args.family or (
        'squat' if args.exercise in ('squat', 'lunge', 'hinge') else 'upper_body'
    )

    recordings = []
    for path in args.results:
        data = json.loads(path.read_text())
        track = _pick_track(data, args.person, family)
        if track is None:
            print(f'{path}: no usable {family} reps — skipped')
            continue
        series = {
            joint: [(t, v) for t, v in entries]
            for joint, entries in track.get('angle_series', {}).items()
            if not joint.endswith('_valgus')
        }
        windows = [
            (r['start_timestamp'], r['timestamp'])
            for r in track['reps'][family]
            if r.get('valid') and not r.get('locomotion')
        ]
        recordings.append((series, windows))
        print(f"{path}: {track.get('person')} — {len(windows)} good reps")

    if not recordings:
        sys.exit('no usable recordings')

    # The rep-family primaries are always active; trunk_lean stays minable —
    # it is the classic passive form constraint.
    must_active = [
        j for j in EXERCISE_ANGLES.get(family, []) if j != 'trunk_lean'
    ]
    ref = build_reference(recordings, args.exercise, must_active=must_active)
    print(f"\nactive:  {', '.join(ref['active'])}")
    print(f"passive: {', '.join(ref['passive'])}")
    print(f"{ref['n_reps']} reps → {len(ref['entries'])} signature entries")
    for entry, s in sorted(ref['entries'].items()):
        print(f"  {entry:34s} {s['mean']:8.2f} ± {s['std']:.2f}")

    if args.dry_run:
        return
    out = PROJECT_ROOT / REFERENCE_DIR / f'{args.exercise}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ref, indent=1))
    print(f'\nreference -> {out}')


if __name__ == '__main__':
    main()
