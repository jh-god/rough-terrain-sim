"""Generate reproducible 1024 x 1024 grayscale rough-terrain heightmaps."""

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image


IMAGE_SIZE = 1024


def _smoothstep(values: np.ndarray) -> np.ndarray:
    """Use cubic interpolation so value-noise cell boundaries are smooth."""
    return values * values * (3.0 - 2.0 * values)


def _value_noise(
    generator: np.random.Generator,
    cells_x: int,
    cells_y: int,
) -> np.ndarray:
    """Create one smoothly interpolated value-noise octave."""
    lattice = generator.standard_normal((cells_y + 1, cells_x + 1))
    positions_x = np.linspace(0.0, float(cells_x), IMAGE_SIZE)
    positions_y = np.linspace(0.0, float(cells_y), IMAGE_SIZE)
    x0 = np.minimum(positions_x.astype(np.int32), cells_x - 1)
    y0 = np.minimum(positions_y.astype(np.int32), cells_y - 1)
    tx = _smoothstep(positions_x - x0)
    ty = _smoothstep(positions_y - y0)

    top = lattice[y0[:, None], x0[None, :]] * (1.0 - tx)
    top += lattice[y0[:, None], x0[None, :] + 1] * tx
    bottom = lattice[y0[:, None] + 1, x0[None, :]] * (1.0 - tx)
    bottom += lattice[y0[:, None] + 1, x0[None, :] + 1] * tx
    return top * (1.0 - ty[:, None]) + bottom * ty[:, None]


def _gaussian_blur(data: np.ndarray, sigma_y: float, sigma_x: float) -> np.ndarray:
    """Apply a separable Gaussian blur using NumPy only."""

    def blur_axis(values: np.ndarray, sigma: float, axis: int) -> np.ndarray:
        if sigma <= 0.0:
            return values
        radius = max(1, int(np.ceil(3.0 * sigma)))
        coordinates = np.arange(-radius, radius + 1, dtype=np.float64)
        kernel = np.exp(-0.5 * (coordinates / sigma) ** 2)
        kernel /= kernel.sum()
        padding = [(0, 0), (0, 0)]
        padding[axis] = (radius, radius)
        padded = np.pad(values, padding, mode='reflect')
        return np.apply_along_axis(
            lambda row: np.convolve(row, kernel, mode='valid'), axis, padded
        )

    return blur_axis(blur_axis(data, sigma_x, axis=1), sigma_y, axis=0)


def generate_normalized_heightmap(
    seed: int,
    width_m: float,
    height_m: float,
    max_elevation_m: float,
    roughness: float,
    smoothing_sigma: float,
) -> np.ndarray:
    """Return a deterministic normalized 1024 x 1024 heightmap.

    ``roughness`` is in [0, 1]. Higher values add more and smaller terrain
    features. ``smoothing_sigma`` is expressed in metres, not pixels.
    """
    if width_m <= 0.0 or height_m <= 0.0:
        raise ValueError('width_m and height_m must be greater than zero')
    if max_elevation_m <= 0.0:
        raise ValueError('max_elevation_m must be greater than zero')
    if not 0.0 <= roughness <= 1.0:
        raise ValueError('roughness must be in the range [0, 1]')
    if smoothing_sigma < 0.0:
        raise ValueError('smoothing_sigma must be zero or greater')

    generator = np.random.default_rng(seed)
    octave_count = 1 + int(round(roughness * 5.0))
    smallest_extent = min(width_m, height_m)
    base_feature_size_m = smallest_extent / (2.0 + 6.0 * roughness)
    terrain = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.float64)
    amplitude = 1.0
    persistence = 0.25 + 0.50 * roughness

    for octave in range(octave_count):
        frequency = 2**octave
        cells_x = max(1, int(np.ceil(width_m * frequency / base_feature_size_m)))
        cells_y = max(1, int(np.ceil(height_m * frequency / base_feature_size_m)))
        octave_noise = _value_noise(generator, cells_x, cells_y)
        octave_noise /= max(float(octave_noise.std()), np.finfo(np.float64).eps)
        terrain += amplitude * octave_noise
        amplitude *= persistence

    sigma_x_pixels = smoothing_sigma * (IMAGE_SIZE - 1) / width_m
    sigma_y_pixels = smoothing_sigma * (IMAGE_SIZE - 1) / height_m
    terrain = _gaussian_blur(terrain, sigma_y_pixels, sigma_x_pixels)

    minimum = float(terrain.min())
    extent = float(terrain.max()) - minimum
    if extent <= np.finfo(np.float64).eps:
        return np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.float64)
    return (terrain - minimum) / extent


def generate_heightmap(
    seed: int,
    width_m: float,
    height_m: float,
    max_elevation_m: float,
    roughness: float,
    smoothing_sigma: float,
) -> np.ndarray:
    """Return a deterministic 1024 x 1024 uint8 heightmap."""
    normalized = generate_normalized_heightmap(
        seed,
        width_m,
        height_m,
        max_elevation_m,
        roughness,
        smoothing_sigma,
    )
    return np.rint(normalized * 255.0).astype(np.uint8)


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', required=True, type=int, help='Random seed for reproducibility.')
    parser.add_argument('--width-m', type=float, default=20.0, help='Terrain width in metres.')
    parser.add_argument('--height-m', type=float, default=20.0, help='Terrain height in metres.')
    parser.add_argument(
        '--max-elevation-m', type=float, default=2.0,
        help='Maximum terrain elevation represented by white (255).',
    )
    parser.add_argument(
        '--roughness', type=float, default=0.55,
        help='Feature detail from 0.0 (smooth) to 1.0 (rough).',
    )
    parser.add_argument(
        '--smoothing-sigma', type=float, default=0.35,
        help='Gaussian smoothing sigma in metres; use 0 for no extra smoothing.',
    )
    parser.add_argument(
        '--output', type=Path, default=Path('rough_terrain.png'),
        help='Output grayscale PNG path.',
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> None:
    args = parse_arguments(arguments)
    heightmap = generate_heightmap(
        args.seed,
        args.width_m,
        args.height_m,
        args.max_elevation_m,
        args.roughness,
        args.smoothing_sigma,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(heightmap, mode='L').save(args.output, format='PNG')
    print(
        f'Wrote {args.output} ({IMAGE_SIZE}x{IMAGE_SIZE}, 8-bit grayscale): '
        f'{args.width_m:g} m x {args.height_m:g} m, '
        f'0.0 to {args.max_elevation_m:g} m, seed={args.seed}'
    )


if __name__ == '__main__':
    main()
