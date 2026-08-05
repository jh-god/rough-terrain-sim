#!/usr/bin/env python3
"""Convert the bundled Poly Haven boulder USDC assets into Gazebo OBJ files.

Usage:
    python3 -m pip install usd-core
    python3 tools/boulder_usdc_to_obj.py
    python3 tools/boulder_usdc_to_obj.py boulder_01
"""

from argparse import ArgumentParser
from array import array
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "namaqualand_boulder_02": {
        "source": REPOSITORY_ROOT
        / "models/namaqualand_boulder_02/namaqualand_boulder_02_4k.usdc",
        "output": REPOSITORY_ROOT
        / "models/namaqualand_boulder_02/meshes/namaqualand_boulder_02.obj",
        "diffuse": "../textures/namaqualand_boulder_02_diff_4k.jpg",
    },
    "boulder_01": {
        "source": REPOSITORY_ROOT / "models/boulder_01/boulder_01_4k.usdc",
        "output": REPOSITORY_ROOT / "models/boulder_01/meshes/boulder_01.obj",
        "diffuse": "../textures/boulder_01_diff_4k.jpg",
    },
}


def parse_arguments():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "assets",
        nargs="*",
        default=None,
        metavar="ASSET",
        help=(
            "assets to convert; omit to convert both (choices: "
            + ", ".join(sorted(ASSETS))
            + ")"
        ),
    )
    arguments = parser.parse_args()
    unknown = set(arguments.assets or []) - ASSETS.keys()
    if unknown:
        parser.error(f"unknown asset(s): {', '.join(sorted(unknown))}")
    return arguments


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
    meshes = [
        usd_geom.Mesh(prim)
        for prim in stage.Traverse()
        if prim.IsA(usd_geom.Mesh)
    ]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh in {source}, found {len(meshes)}")

    mesh = meshes[0]
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    normals = mesh.GetNormalsAttr().Get()
    texture_coordinates = (
        usd_geom.PrimvarsAPI(mesh).GetPrimvar("st").ComputeFlattened()
    )
    if not points or not counts or not indices:
        raise RuntimeError(f"the USD mesh has no geometry: {source}")
    if len(normals) != len(indices) or len(texture_coordinates) != len(indices):
        raise RuntimeError(f"expected face-varying normals and UVs: {source}")
    return points, counts, indices, normals, texture_coordinates


def face_offsets(counts):
    offsets = array("I", [0])
    total = 0
    for count in counts:
        total += count
        offsets.append(total)
    return offsets


def write_obj(asset_name, config, mesh_data):
    points, counts, indices, normals, texture_coordinates = mesh_data
    offsets = face_offsets(counts)
    output = config["output"]
    material_output = output.with_suffix(".mtl")
    temporary_obj = output.with_name(output.name + ".tmp")
    temporary_mtl = material_output.with_name(material_output.name + ".tmp")
    output.parent.mkdir(parents=True, exist_ok=True)

    material = f"""newmtl {asset_name}
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd {config['diffuse']}
"""
    triangle_count = 0
    try:
        temporary_mtl.write_text(material, encoding="utf-8")
        with temporary_obj.open("w", encoding="utf-8") as obj:
            obj.write(f"# Converted from {config['source'].name} for Gazebo Fortress\n")
            obj.write(f"mtllib {material_output.name}\n")
            for x, y, z in points:
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for u, v in texture_coordinates:
                obj.write(f"vt {u:.6f} {v:.6f}\n")
            for x, y, z in normals:
                obj.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")

            obj.write(f"usemtl {asset_name}\n")
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

    print(f"{asset_name}: {len(points):,} points, {triangle_count:,} triangles")
    print(f"Wrote: {output}")


def main():
    arguments = parse_arguments()
    usd, usd_geom = load_usd_modules()
    asset_names = arguments.assets or sorted(ASSETS)
    for asset_name in asset_names:
        config = ASSETS[asset_name]
        write_obj(
            asset_name,
            config,
            load_mesh(config["source"], usd, usd_geom),
        )


if __name__ == "__main__":
    main()
