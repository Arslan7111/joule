"""Track C of `FIT3D_UTILIZATION_PLAN.md`: extract Fit3D's real 4-camera rig
geometry from calibration data and compare it against `CAMERA_PLACEMENT.md`
rule 4 (3+ cameras preferred over exactly 2, spaced 60-90 degrees apart,
~2m elevation) -- a second, independently-built real rig to check that
guidance against, on top of CMU Panoptic's dome and this project's own
reasoning.

Small, cheap, standalone -- does not depend on the Track A batch run.
Reuses the extrinsics-convention finding already verified in
`tools/validate_fit3d.py` (`extrinsics.T` is the camera CENTER in world
coordinates, not `P = K[R|t]`'s `t` -- no inversion needed here since we
want the center directly).

Confirmed before trusting any number below (see inline checks / commit):
- Calibration is identical across all of one subject's exercises (one
  fixed rig per capture session) but varies slightly subject-to-subject
  (same physical rig, re-set/re-calibrated each session) -- so each of the
  8 subjects is treated as an independent geometry sample, not 1 rig
  measured 8 times redundantly.
- Fit3D's world is Z-up with the floor at Z=0 (verified against
  `joints3d_25` ankle/toe joints landing at Z~0.03-0.05 in a real frame).

Usage:
    python tools/analyze_fit3d_rig_geometry.py
"""

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_fit3d import ALL_CAMS, FIT3D_ROOT  # noqa: E402

REFERENCE_EXERCISE = 'squat'   # present for every subject; rig is fixed per subject anyway


def camera_centers(subject: str) -> np.ndarray:
    """(4, 3) array of camera centers in world coords, Fit3D cam order."""
    centers = []
    for cam in ALL_CAMS:
        cp = json.loads((FIT3D_ROOT / subject / 'camera_parameters' / cam /
                          f'{REFERENCE_EXERCISE}.json').read_text())
        centers.append(np.array(cp['extrinsics']['T'], dtype=np.float64).ravel())
    return np.stack(centers)


def analyze_subject(subject: str) -> dict:
    centers = camera_centers(subject)               # (4, 3): X, Y, Z (Z-up)
    horiz_center = centers[:, :2].mean(axis=0)       # approx station center (X, Y)
    rel = centers[:, :2] - horiz_center
    azimuths = np.degrees(np.arctan2(rel[:, 1], rel[:, 0])) % 360.0
    radii = np.linalg.norm(rel, axis=1)
    elevations = centers[:, 2]

    sorted_az = np.sort(azimuths)
    adjacent_gaps = np.diff(np.concatenate([sorted_az, sorted_az[:1] + 360.0]))

    pairwise = []
    for i, j in combinations(range(4), 2):
        diff = abs(azimuths[i] - azimuths[j]) % 360.0
        ang = min(diff, 360.0 - diff)
        dist = np.linalg.norm(centers[i] - centers[j])
        pairwise.append({'cams': (ALL_CAMS[i], ALL_CAMS[j]), 'angle_deg': float(ang),
                          'center_to_center_m': float(dist)})

    return {
        'subject': subject,
        'horiz_center': horiz_center.tolist(),
        'radii_m': radii.tolist(),
        'elevations_m': elevations.tolist(),
        'azimuths_deg': azimuths.tolist(),
        'adjacent_gaps_deg': adjacent_gaps.tolist(),
        'pairwise': pairwise,
    }


def main() -> None:
    subjects = sorted(p.name for p in FIT3D_ROOT.iterdir() if p.is_dir())
    per_subject = [analyze_subject(s) for s in subjects]

    all_adjacent_gaps = [g for r in per_subject for g in r['adjacent_gaps_deg']]
    all_pairwise_angles = [p['angle_deg'] for r in per_subject for p in r['pairwise']]
    all_elevations = [e for r in per_subject for e in r['elevations_m']]
    all_radii = [rr for r in per_subject for rr in r['radii_m']]

    print(f'{"subject":8s} {"adjacent gaps (deg, sorted)":36s} {"elev (m)":18s} {"radius (m)":18s}')
    for r in per_subject:
        gaps = ', '.join(f'{g:5.1f}' for g in sorted(r['adjacent_gaps_deg']))
        elevs = ', '.join(f'{e:4.2f}' for e in r['elevations_m'])
        radii = ', '.join(f'{rr:4.2f}' for rr in r['radii_m'])
        print(f'{r["subject"]:8s} [{gaps}]   [{elevs}]   [{radii}]')

    print(f'\n=== Pooled across {len(subjects)} subjects (independent rig samples) ===')
    print(f'Adjacent-camera angular gaps: min {min(all_adjacent_gaps):.1f} deg, '
          f'max {max(all_adjacent_gaps):.1f} deg, mean {np.mean(all_adjacent_gaps):.1f} deg')
    print(f'All pairwise camera-pair angles: min {min(all_pairwise_angles):.1f} deg, '
          f'max {max(all_pairwise_angles):.1f} deg, mean {np.mean(all_pairwise_angles):.1f} deg')
    print(f'Elevation: min {min(all_elevations):.2f} m, max {max(all_elevations):.2f} m, '
          f'mean {np.mean(all_elevations):.2f} m')
    print(f'Radius (camera to station center): min {min(all_radii):.2f} m, '
          f'max {max(all_radii):.2f} m, mean {np.mean(all_radii):.2f} m')

    in_range = sum(1 for g in all_adjacent_gaps if 60.0 <= g <= 90.0)
    print(f'\nAdjacent gaps inside CAMERA_PLACEMENT.md\'s 60-90 deg band: '
          f'{in_range}/{len(all_adjacent_gaps)}')
    print('Camera count: 4 per station (satisfies "3+ preferred over exactly 2").')

    out = {
        'reference_exercise': REFERENCE_EXERCISE,
        'per_subject': per_subject,
        'pooled': {
            'adjacent_gaps_deg': {'min': min(all_adjacent_gaps), 'max': max(all_adjacent_gaps),
                                   'mean': float(np.mean(all_adjacent_gaps))},
            'pairwise_angles_deg': {'min': min(all_pairwise_angles), 'max': max(all_pairwise_angles),
                                     'mean': float(np.mean(all_pairwise_angles))},
            'elevation_m': {'min': min(all_elevations), 'max': max(all_elevations),
                             'mean': float(np.mean(all_elevations))},
            'radius_m': {'min': min(all_radii), 'max': max(all_radii),
                          'mean': float(np.mean(all_radii))},
            'adjacent_gaps_in_60_90_band': f'{in_range}/{len(all_adjacent_gaps)}',
        },
    }
    out_path = PROJECT_ROOT / 'validation_results_fit3d' / 'rig_geometry.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f'\nreport -> {out_path}')


if __name__ == '__main__':
    main()
