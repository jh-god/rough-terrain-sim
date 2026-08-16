"""Generate reproducible 1024 x 1024 16-bit rough-terrain heightmaps."""

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image

from rough_terrain_sim.generate_heightmap import (
    IMAGE_SIZE,
    generate_normalized_heightmap,
)


def generate_heightmap_16bit(
    seed: int,
    width_m: float,
    height_m: float,
    max_elevation_m: float,
    roughness: float,
    smoothing_sigma: float,
) -> np.ndarray:
    """Return a deterministic 1024 x 1024 uint16 heightmap."""
    normalized = generate_normalized_heightmap(
        seed,
        width_m,
        height_m,
        max_elevation_m,
        roughness,
        smoothing_sigma,
    )
    return np.rint(normalized * 65535.0).astype(np.uint16)


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--seed', required=True, type=int,
        help='Random seed for reproducibility.',
    )
    parser.add_argument(
        '--width-m', type=float, default=50.0,
        help='Terrain width in metres.',
    )
    parser.add_argument(
        '--height-m', type=float, default=50.0,
        help='Terrain height in metres.',
    )
    parser.add_argument(
        '--max-elevation-m', type=float, default=3.17,
        help=(
            'Intended terrain elevation represented by white (65535); '
            'keep the terrain model SDF height range in sync.'
        ),
    )
    parser.add_argument(
        '--roughness', type=float, default=0.55,
        help='Feature detail from 0.0 (smooth) to 1.0 (rough).',
    )
    parser.add_argument(
        '--smoothing-sigma', type=float, default=0.35,
        help=(
            'Gaussian smoothing sigma in metres; '
            'use 0 for no extra smoothing.'
        ),
    )
    parser.add_argument(
        '--output', type=Path, default=Path('rough_terrain_16bit.png'),
        help='Output 16-bit grayscale PNG path.',
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> None:
    args = parse_arguments(arguments)
    heightmap = generate_heightmap_16bit(
        args.seed,
        args.width_m,
        args.height_m,
        args.max_elevation_m,
        args.roughness,
        args.smoothing_sigma,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(heightmap, mode='I;16').save(args.output, format='PNG')
    print(
        f'Wrote {args.output} ({IMAGE_SIZE}x{IMAGE_SIZE}, 16-bit grayscale): '
        f'{args.width_m:g} m x {args.height_m:g} m, '
        f'0.0 to {args.max_elevation_m:g} m, seed={args.seed}'
    )


if __name__ == '__main__':
    main()
