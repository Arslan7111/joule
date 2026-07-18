"""Benchmark rep counting against the RepCount Part-A test split.

Runs the full pipeline (detector -> pose -> adaptive rep counting, --exercises
auto) on each annotated video and scores predicted rep counts against ground
truth with the standard repetition-counting metrics: MAE (normalised by GT
count) and off-by-one accuracy (OBO).

Usage:
    python tools/benchmark_repcount.py test_videos/repcount \
        [--classes squat pull_up] [--limit N] [--keep-results]

Expects <dir>/test_annotations.json and <dir>/videos/<video_id>.mp4
(see test_videos/repcount/ - HF mirror momo321654/RepCountA-videos).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mirror annotation typos onto canonical class names
CANON = {
    'squant': 'squat',
    'pullups': 'pull_up',
    'pushups': 'push_up',
    'frontraise': 'front_raise',
    'benchpressing': 'bench_pressing',
    'jumpjacks': 'jump_jack',
}


def predicted_count(result_json: Path) -> tuple[int, str]:
    """Main person's rep count and classified exercise from a camera JSON."""
    data = json.loads(result_json.read_text())
    best = None
    for track in data.get('tracks', []):
        if best is None or track['total_frames'] > best['total_frames']:
            best = track
    if best is None:
        return 0, 'no_person'
    counts = best.get('rep_counts', {})
    n = max(counts.values()) if counts else 0
    return n, best.get('exercise_class', '?')


def run_video(video: Path, out_dir: Path) -> Path:
    cmd = [
        sys.executable, str(PROJECT_ROOT / 'pipeline.py'),
        '--sources', str(video),
        '--names', 'bench',
        '--exercises', 'auto',
        '--output', str(out_dir),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True,
                   cwd=PROJECT_ROOT)
    return out_dir / 'bench.json'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset_dir', type=Path)
    ap.add_argument('--classes', nargs='*', default=None,
                    help='canonical action types to include (default: all downloaded)')
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--keep-results', action='store_true',
                    help='keep per-video pipeline JSONs next to the report')
    args = ap.parse_args()

    anns = json.loads((args.dataset_dir / 'test_annotations.json').read_text())
    rows = []
    for a in anns:
        cls = CANON.get(a['action_type'], a['action_type'])
        if args.classes and cls not in args.classes:
            continue
        video = args.dataset_dir / 'videos' / f"{a['video_id']}.mp4"
        if not video.exists():
            continue
        rows.append((a['video_id'], cls, int(a['count']), video))
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        sys.exit('no matching videos found')

    results_dir = args.dataset_dir / 'bench_results'
    results_dir.mkdir(exist_ok=True)

    records = []
    for i, (vid, cls, gt, video) in enumerate(rows, 1):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                out = run_video(video, Path(tmp))
                pred, pred_cls = predicted_count(out)
                if args.keep_results:
                    shutil.copy(out, results_dir / f'{vid}.json')
            except subprocess.CalledProcessError as e:
                print(f'[{i}/{len(rows)}] {vid} PIPELINE ERROR: {e.stderr[-300:]}')
                continue
        err = pred - gt
        records.append({'video_id': vid, 'class': cls, 'gt': gt,
                        'pred': pred, 'pred_class': pred_cls, 'err': err})
        print(f'[{i}/{len(rows)}] {vid:14s} {cls:14s} gt={gt:3d} pred={pred:3d} '
              f'({err:+d})  classified={pred_cls}')

    if not records:
        sys.exit('no videos scored')

    def summarise(recs, label):
        mae = sum(abs(r['err']) / max(r['gt'], 1) for r in recs) / len(recs)
        obo = sum(abs(r['err']) <= 1 for r in recs) / len(recs)
        print(f'{label:16s} n={len(recs):3d}  MAE={mae:.3f}  OBO={obo:.1%}')

    print('\n=== RepCount Part-A benchmark ===')
    summarise(records, 'ALL')
    for cls in sorted({r['class'] for r in records}):
        summarise([r for r in records if r['class'] == cls], cls)

    report = results_dir / 'report.json'
    report.write_text(json.dumps(records, indent=1))
    print(f'\nper-video results -> {report}')


if __name__ == '__main__':
    main()
