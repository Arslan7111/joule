"""
Gym workout video analysis pipeline.

Usage:
    python pipeline.py \\
        --sources rack1.mp4 pullup.mp4 \\
        --names   squat_rack_1 pullup_bar \\
        --exercises squat upper_body \\
        --output results/ --visualise

--names     Optional human-readable station label for each source (defaults to cam_0, cam_1 …)
--exercises One of: squat | upper_body | both  — per source (defaults to both)

If no --sources are supplied, a synthetic test video is generated so every
pipeline stage can be exercised without real footage.
"""

import argparse
import logging
import queue
import threading
from pathlib import Path

import cv2
import numpy as np

from src.camera import CameraProcessor
from src.output import write_merged_json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def _create_test_video(path: str, duration: int = 10, fps: int = 30) -> str:
    """
    Generate a simple synthetic video with a coloured rectangle moving up and
    down to simulate a person doing squats.  YOLO will not detect any persons
    in it, but every other pipeline stage (video I/O, JSON output, etc.) can
    be validated against it.
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(path, fourcc, fps, (640, 480))
    total = duration * fps
    for i in range(total):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        t = i / total
        # Rectangle bounces up and down twice
        y = int(40 + 160 * abs(np.sin(2 * np.pi * t * 2)))
        cv2.rectangle(frame, (200, y), (440, y + 360), (60, 160, 60), -1)
        cv2.putText(
            frame, f"Synthetic test  frame {i}/{total}",
            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2,
        )
        writer.write(frame)
    writer.release()
    logger.info(f"Synthetic test video written to {path}")
    return path


def _live_loop(
    threads: list[threading.Thread],
    display_queues: dict,
    stop_event: threading.Event,
) -> None:
    """
    Main-thread display loop.  Reads annotated frames from each camera's queue
    and calls cv2.imshow.  Runs until all camera threads finish or the user
    presses  q  (which stops processing immediately).
    """
    try:
        while any(t.is_alive() for t in threads):
            for cam_id, q in display_queues.items():
                try:
                    _, frame = q.get_nowait()
                    cv2.imshow(cam_id, frame)
                except queue.Empty:
                    pass
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("Live display: q pressed — stopping processing.")
                stop_event.set()
                break
    except KeyboardInterrupt:
        logger.info("Interrupted — stopping processing.")
        stop_event.set()

    for t in threads:
        t.join()
    cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Per-person rep counting and joint angle extraction from workout video.'
    )
    parser.add_argument(
        '--sources', nargs='+', default=[],
        help='Video file paths, RTSP/HTTP stream URLs, or webcam indices (one per camera)',
    )
    parser.add_argument(
        '--output', default='results/',
        help='Directory for JSON results and optional annotated videos',
    )
    parser.add_argument(
        '--names', nargs='+', default=[],
        help='Station label for each source (e.g. squat_rack_1 pullup_bar)',
    )
    parser.add_argument(
        '--exercises', nargs='+', default=[],
        choices=['squat', 'upper_body', 'both', 'auto'],
        metavar='EXERCISE',
        help='Exercise type per source: squat | upper_body | both | auto '
             '(auto = classify from movement; default: both)',
    )
    parser.add_argument(
        '--collect-hard', action='store_true',
        help='Save person crops where pose estimation failed or was '
             'low-confidence to <output>/hard_examples/ for later labelling',
    )
    parser.add_argument(
        '--no-reid', action='store_true',
        help='Disable session person re-identification',
    )
    parser.add_argument(
        '--fuse', metavar='RIG_NPZ', default=None,
        help='Treat ALL sources as synchronized views of ONE station and '
             'triangulate 3D (rig calibration .npz; see tools/calibrate.py)',
    )
    parser.add_argument(
        '--visualise', action='store_true',
        help='Render annotated MP4 for each camera source',
    )
    parser.add_argument(
        '--live', action='store_true',
        help='Show live annotated feed in a window while processing (press q to quit)',
    )
    parser.add_argument(
        '--dashboard', action='store_true',
        help='Serve live web dashboard (default port 5000)',
    )
    parser.add_argument(
        '--port', type=int, default=5000,
        help='Dashboard port (default 5000)',
    )
    args = parser.parse_args()

    if len(args.names) > len(args.sources):
        parser.error(f"{len(args.names)} names given for {len(args.sources)} sources.")
    if len(args.exercises) > len(args.sources):
        parser.error(f"{len(args.exercises)} exercises given for {len(args.sources)} sources.")
    if len(args.names) != len(set(args.names)):
        parser.error("Duplicate station names — each source needs a unique name "
                     "(results are written to <name>.json).")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = args.sources
    if not sources:
        logger.info("No --sources supplied.  Generating synthetic test video.")
        test_path = str(output_dir / 'test_video.mp4')
        sources = [_create_test_video(test_path)]

    for src in sources:
        if not str(src).lower().startswith(('rtsp://', 'http://', 'https://')) \
                and not str(src).isdigit() and not Path(src).exists():
            parser.error(f"Source not found: {src}")

    gallery = None
    if not args.no_reid:
        from src.session import SessionGallery
        gallery = SessionGallery()

    dashboard = None
    if args.dashboard:
        from src.dashboard import DashboardServer
        dashboard = DashboardServer(port=args.port, gallery=gallery)
        dashboard.start()

    # One shared queue per camera so the main thread can drive cv2.imshow.
    # macOS requires imshow on the main thread; queue size 2 keeps latency low.
    display_queues = {
        (args.names[i] if i < len(args.names) else f"cam_{i}"): queue.Queue(maxsize=2)
        for i in range(len(sources))
    } if args.live else {}

    stop_event = threading.Event()
    processors = []
    threads: list[threading.Thread] = []

    if args.fuse:
        from src.fusion import FusedCameraProcessor
        cam_id = args.names[0] if args.names else 'fused_station'
        exercise = args.exercises[0] if args.exercises else 'both'
        proc = FusedCameraProcessor(
            camera_id=cam_id,
            sources=sources,
            rig_path=args.fuse,
            output_dir=str(output_dir),
            visualise=args.visualise,
            exercise=exercise,
            display_queue=display_queues.get(cam_id),
            dashboard=dashboard,
            stop_event=stop_event,
            gallery=gallery,
        )
        processors.append(proc)
        threads.append(threading.Thread(target=proc.run, name=cam_id, daemon=False))
        sources = []          # all sources consumed by the fused station

    for i, src in enumerate(sources):
        cam_id = args.names[i] if i < len(args.names) else f"cam_{i}"
        exercise = args.exercises[i] if i < len(args.exercises) else 'both'
        proc = CameraProcessor(
            camera_id=cam_id,
            source=src,
            output_dir=str(output_dir),
            visualise=args.visualise,
            exercise=exercise,
            display_queue=display_queues.get(cam_id),
            dashboard=dashboard,
            stop_event=stop_event,
            collect_hard=args.collect_hard,
            gallery=gallery,
        )
        processors.append(proc)
        t = threading.Thread(target=proc.run, name=cam_id, daemon=False)
        threads.append(t)

    logger.info(f"Launching {len(threads)} camera thread(s)…")
    for t in threads:
        t.start()

    if args.live:
        logger.info("Live display active — press  q  to quit early.")
        _live_loop(threads, display_queues, stop_event)
    else:
        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            logger.info("Interrupted — stopping camera threads, writing partial results…")
            stop_event.set()
            for t in threads:
                t.join()

    camera_results = [p.result for p in processors if p.result is not None]
    write_merged_json(camera_results, str(output_dir))
    logger.info(f"All results written to {output_dir}/")


if __name__ == '__main__':
    main()
