#!/usr/bin/env python3
"""Convert Poly Haven's Tree Stump 01 USDC into a Gazebo-friendly OBJ.

Usage:
    python3 -m pip install usd-core
    python3 tools/stump_usdc_to_obj.py
"""

from argparse import ArgumentParser
from array import array
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "models/tree_stump/tree_stump_01_4k.usdc"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "models/tree_stump/meshes/tree_stump_01.obj"

MATERIAL_FILE = """newmtl tree_stump
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd ../textures/tree_stump_01_diff_4k.jpg
"""


def parse_arguments():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"input USD/USDC file (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output OBJ file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def load_usd_modules():
    try:
        from pxr import Usd, UsdGeom
    except ImportError as error:
        raise SystemExit(
            "The Pixar USD Python module is required. "
            "Install it with: python3 -m pip install usd-core"
        ) from error
    return Usd, UsdGeom


def load_mesh(source, usd, usd_geom):
    stage = usd.Stage.Open(str(source))
    if stage is None:
        raise RuntimeError(f"could not open USD file: {source}")

    meshes = [usd_geom.Mesh(prim) for prim in stage.Traverse()
              if prim.IsA(usd_geom.Mesh)]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh, found {len(meshes)}")

    mesh = meshes[0]
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    normals = mesh.GetNormalsAttr().Get()
    texture_coordinates = (
        usd_geom.PrimvarsAPI(mesh).GetPrimvar("st").ComputeFlattened()
    )

    if not points or not counts or not indices:
        raise RuntimeError("the USD mesh has no geometry")
    if len(normals) != len(indices) or len(texture_coordinates) != len(indices):
        raise RuntimeError("expected face-varying normals and st coordinates")
    return points, counts, indices, normals, texture_coordinates


def build_face_offsets(counts):
    offsets = array("I", [0])
    total = 0
    for count in counts:
        total += count
        offsets.append(total)
    return offsets


def write_obj(output, points, counts, indices, normals, texture_coordinates):
    offsets = build_face_offsets(counts)
    material_output = output.with_suffix(".mtl")
    temporary_obj = output.with_name(output.name + ".tmp")
    temporary_mtl = material_output.with_name(material_output.name + ".tmp")
    output.parent.mkdir(parents=True, exist_ok=True)

    triangle_count = 0
    try:
        temporary_mtl.write_text(MATERIAL_FILE, encoding="utf-8")
        with temporary_obj.open("w", encoding="utf-8") as obj:
            obj.write("# Converted from tree_stump_01_4k.usdc for Gazebo Fortress\n")
            obj.write(f"mtllib {material_output.name}\n")

            for x, y, z in points:
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for u, v in texture_coordinates:
                obj.write(f"vt {u:.6f} {v:.6f}\n")
            for x, y, z in normals:
                obj.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")

            obj.write("usemtl tree_stump\n")
            for face, count in enumerate(counts):
                begin = offsets[face]
                corners = list(range(begin, begin + count))
                for triangle in range(1, count - 1):
                    triangle_corners = (
                        corners[0],
                        corners[triangle],
                        corners[triangle + 1],
                    )
                    references = [
                        f"{indices[corner] + 1}/{corner + 1}/{corner + 1}"
                        for corner in triangle_corners
                    ]
                    obj.write("f " + " ".join(references) + "\n")
                    triangle_count += 1

        os.replace(temporary_mtl, material_output)
        os.replace(temporary_obj, output)
    finally:
        temporary_obj.unlink(missing_ok=True)
        temporary_mtl.unlink(missing_ok=True)

    return triangle_count


def main():
    arguments = parse_arguments()
    usd, usd_geom = load_usd_modules()
    mesh_data = load_mesh(arguments.source, usd, usd_geom)
    triangle_count = write_obj(arguments.output, *mesh_data)
    print(f"OBJ points: {len(mesh_data[0]):,}")
    print(f"OBJ triangles: {triangle_count:,}")
    print(f"Wrote: {arguments.output}")
    print(f"Wrote: {arguments.output.with_suffix('.mtl')}")


if __name__ == "__main__":
    main()
