"""
Two-camera calibration from checkerboard footage.

Procedure (one-time per camera pair, redo if a camera is moved):

1. Print a checkerboard (default 9×6 inner corners, e.g. an A3 print).
2. Record it simultaneously with both cameras — move it around the shared
   view volume, tilting it, ~20–60 frames where both cameras see it fully.
3. Run:
       python tools/calibrate.py camA.mp4 camB.mp4 --square-mm 25 \
              --out calibration/pair_AB.npz

The output .npz contains K1, K2 (intrinsics), R, t (camera B pose relative
to camera A) — everything src/triangulation.py needs.  Camera A's frame is
the world frame (Z up assumed if camera A is level).
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

PATTERN = (9, 6)          # inner corners (columns, rows)


def _collect_corners(path: str, square_mm: float, every_n: int = 5):
    objp = np.zeros((PATTERN[0] * PATTERN[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:PATTERN[0], 0:PATTERN[1]].T.reshape(-1, 2)
    objp *= square_mm / 1000.0     # metres

    cap = cv2.VideoCapture(path)
    frames, corners_all, size = [], [], None
    i = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if i % every_n == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            size = gray.shape[::-1]
            found, corners = cv2.findChessboardCorners(gray, PATTERN, None)
            if found:
                corners = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3),
                )
                frames.append(i)
                corners_all.append(corners)
        i += 1
    cap.release()
    return frames, corners_all, objp, size


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('video_a')
    ap.add_argument('video_b')
    ap.add_argument('--square-mm', type=float, default=25.0,
                    help='Checkerboard square size in millimetres')
    ap.add_argument('--out', default='calibration/pair.npz')
    args = ap.parse_args()

    print("Detecting checkerboard in camera A…")
    fa, ca, objp, size_a = _collect_corners(args.video_a, args.square_mm)
    print(f"  {len(fa)} usable frames")
    print("Detecting checkerboard in camera B…")
    fb, cb, _, size_b = _collect_corners(args.video_b, args.square_mm)
    print(f"  {len(fb)} usable frames")

    # Keep only frames where BOTH cameras found the board
    common = sorted(set(fa) & set(fb))
    if len(common) < 10:
        raise SystemExit(
            f"Only {len(common)} frames seen by both cameras — need ≥10. "
            "Record again with the board visible to both."
        )
    ia = [fa.index(f) for f in common]
    ib = [fb.index(f) for f in common]
    pts_a = [ca[i] for i in ia]
    pts_b = [cb[i] for i in ib]
    obj = [objp] * len(common)
    print(f"{len(common)} frames common to both cameras")

    print("Calibrating intrinsics…")
    err_a, K1, d1, _, _ = cv2.calibrateCamera(obj, pts_a, size_a, None, None)
    err_b, K2, d2, _, _ = cv2.calibrateCamera(obj, pts_b, size_b, None, None)
    print(f"  camera A rms {err_a:.2f}px   camera B rms {err_b:.2f}px")

    print("Calibrating extrinsics (stereo)…")
    err_s, K1, d1, K2, d2, R, T, _, _ = cv2.stereoCalibrate(
        obj, pts_a, pts_b, K1, d1, K2, d2, size_a,
        flags=cv2.CALIB_FIX_INTRINSIC,
    )
    print(f"  stereo rms {err_s:.2f}px   baseline {np.linalg.norm(T):.2f} m")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, K1=K1, dist1=d1, K2=K2, dist2=d2, R=R, t=T.ravel(),
             image_size_a=size_a, image_size_b=size_b)
    print(f"Saved → {out}")
    print("Camera A is the world frame; feed both cameras' 2D keypoints to "
          "src.triangulation.triangulate_skeleton with these matrices.")


if __name__ == '__main__':
    main()
