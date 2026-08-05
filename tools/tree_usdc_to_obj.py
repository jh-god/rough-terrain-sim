#!/usr/bin/env python3
"""Convert Poly Haven's Tree Small 02 USD into a reduced Gazebo OBJ.

The source tree contains very dense leaf geometry.  This converter always keeps
the trunk and branches, while retaining a deterministic percentage of complete
leaf components.  The default is 30 percent.

Usage:
    python3 -m pip install usd-core
    python3 tools/tree_usdc_to_obj.py
    python3 tools/tree_usdc_to_obj.py --leaf-keep-ratio 0.50
"""

from argparse import ArgumentParser, ArgumentTypeError
from array import array
import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "models/tree/tree_small_02_4k.usdc"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "models/tree/meshes/tree_small_02.obj"
DEFAULT_LEAF_KEEP_RATIO = 0.30

MATERIAL_NAMES = {
    "tree_small_02_branches": "branches",
    "tree_small_02_leaves": "leaves",
    "tree_small_02_trunk": "trunk",
}

MATERIAL_FILE = """newmtl branches
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd ../textures/tree_small_02_branch_diff_4k.png
map_Bump ../textures/tree_small_02_branch_nor_gl_4k.png

newmtl leaves
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd ../textures/tree_small_02_leaves_diff_4k.png
map_d ../textures/tree_small_02_leaves_alpha_4k.png
map_Bump ../textures/tree_small_02_leaves_nor_gl_4k.png

newmtl trunk
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd ../textures/tree_small_02_diff_4k.jpg
"""


def ratio(value):
    """Validate a command-line ratio in the inclusive range [0, 1]."""
    try:
        parsed = float(value)
    except ValueError as error:
        raise ArgumentTypeError("must be a number between 0 and 1") from error
    if not 0.0 <= parsed <= 1.0:
        raise ArgumentTypeError("must be between 0 and 1")
    return parsed


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
    parser.add_argument(
        "--leaf-keep-ratio",
        type=ratio,
        default=DEFAULT_LEAF_KEEP_RATIO,
        help="fraction of complete leaf components to retain (default: 0.30)",
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


def find_first_mesh(stage, usd_geom):
    for prim in stage.Traverse():
        if prim.IsA(usd_geom.Mesh):
            return usd_geom.Mesh(prim)
    raise RuntimeError("the USD file does not contain a mesh")


def collect_mesh_data(source, usd, usd_geom):
    stage = usd.Stage.Open(str(source))
    if stage is None:
        raise RuntimeError(f"could not open USD file: {source}")

    mesh = find_first_mesh(stage, usd_geom)
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

    subsets = {
        subset.GetPrim().GetName(): subset.GetIndicesAttr().Get()
        for subset in usd_geom.Subset.GetAllGeomSubsets(mesh)
    }
    missing = MATERIAL_NAMES.keys() - subsets.keys()
    if missing:
        raise RuntimeError(f"missing expected geometry subsets: {sorted(missing)}")

    return points, counts, indices, normals, texture_coordinates, subsets


def build_face_offsets(counts):
    offsets = array("I", [0])
    total = 0
    for count in counts:
        total += count
        offsets.append(total)
    return offsets


def select_leaf_faces(leaf_faces, offsets, indices, keep_ratio):
    """Select whole connected leaves using a repeatable hash of each component."""
    parent = array("I", range(len(leaf_faces)))

    def find(item):
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != item:
            next_item = parent[item]
            parent[item] = root
            item = next_item
        return root

    def union(left, right):
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    vertex_owner = {}
    for local_face, face in enumerate(leaf_faces):
        begin, end = offsets[face], offsets[face + 1]
        for point_index in indices[begin:end]:
            owner = vertex_owner.setdefault(point_index, local_face)
            union(local_face, owner)

    roots = {find(local_face) for local_face in range(len(leaf_faces))}
    threshold = int(keep_ratio * (1 << 32))
    selected_roots = {
        root
        for root in roots
        if ((root * 2654435761) & 0xFFFFFFFF) < threshold
    }
    selected_faces = [
        face
        for local_face, face in enumerate(leaf_faces)
        if find(local_face) in selected_roots
    ]
    return selected_faces, len(roots), len(selected_roots)


def select_faces(subsets, offsets, indices, keep_ratio):
    selected_leaves, leaf_count, selected_leaf_count = select_leaf_faces(
        subsets["tree_small_02_leaves"], offsets, indices, keep_ratio
    )
    selected = [
        (face, "branches") for face in subsets["tree_small_02_branches"]
    ]
    selected.extend((face, "leaves") for face in selected_leaves)
    selected.extend((face, "trunk") for face in subsets["tree_small_02_trunk"])
    selected.sort(key=lambda item: item[0])
    return selected, leaf_count, selected_leaf_count


def write_obj(
    output,
    points,
    indices,
    normals,
    texture_coordinates,
    offsets,
    selected,
):
    used_points = sorted(
        {
            point_index
            for face, _ in selected
            for point_index in indices[offsets[face] : offsets[face + 1]]
        }
    )
    point_map = {source: target + 1 for target, source in enumerate(used_points)}

    # Use an integer array instead of a Python dict: the source has more than
    # four million face corners, so this saves a substantial amount of memory.
    corner_map = array("I", [0]) * len(indices)
    next_corner = 1
    for face, _ in selected:
        for corner in range(offsets[face], offsets[face + 1]):
            corner_map[corner] = next_corner
            next_corner += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    material_output = output.with_suffix(".mtl")
    temporary_obj = output.with_name(output.name + ".tmp")
    temporary_mtl = material_output.with_name(material_output.name + ".tmp")

    triangle_count = 0
    try:
        temporary_mtl.write_text(MATERIAL_FILE, encoding="utf-8")
        with temporary_obj.open("w", encoding="utf-8") as obj:
            obj.write("# Reduced from tree_small_02_4k.usdc for Gazebo Fortress\n")
            obj.write(f"mtllib {material_output.name}\n")

            for source_index in used_points:
                x, y, z = points[source_index]
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")

            for face, _ in selected:
                for corner in range(offsets[face], offsets[face + 1]):
                    u, v = texture_coordinates[corner]
                    obj.write(f"vt {u:.6f} {v:.6f}\n")

            for face, _ in selected:
                for corner in range(offsets[face], offsets[face + 1]):
                    x, y, z = normals[corner]
                    obj.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")

            current_material = None
            for face, material in selected:
                if material != current_material:
                    obj.write(f"usemtl {material}\n")
                    current_material = material

                corners = range(offsets[face], offsets[face + 1])
                corners = list(corners)
                for triangle in range(1, len(corners) - 1):
                    triangle_corners = (
                        corners[0],
                        corners[triangle],
                        corners[triangle + 1],
                    )
                    references = [
                        f"{point_map[indices[corner]]}/"
                        f"{corner_map[corner]}/{corner_map[corner]}"
                        for corner in triangle_corners
                    ]
                    obj.write("f " + " ".join(references) + "\n")
                    triangle_count += 1

        os.replace(temporary_mtl, material_output)
        os.replace(temporary_obj, output)
    finally:
        temporary_obj.unlink(missing_ok=True)
        temporary_mtl.unlink(missing_ok=True)

    return len(used_points), triangle_count


def main():
    arguments = parse_arguments()
    usd, usd_geom = load_usd_modules()
    data = collect_mesh_data(arguments.source, usd, usd_geom)
    points, counts, indices, normals, texture_coordinates, subsets = data
    offsets = build_face_offsets(counts)
    selected, total_leaves, selected_leaves = select_faces(
        subsets, offsets, indices, arguments.leaf_keep_ratio
    )
    vertex_count, triangle_count = write_obj(
        arguments.output,
        points,
        indices,
        normals,
        texture_coordinates,
        offsets,
        selected,
    )

    print(f"Leaf ratio: {arguments.leaf_keep_ratio:.1%}")
    print(f"Leaf components: {selected_leaves:,} / {total_leaves:,}")
    print(f"Selected source faces: {len(selected):,}")
    print(f"OBJ vertices: {vertex_count:,}")
    print(f"OBJ triangles: {triangle_count:,}")
    print(f"Wrote: {arguments.output}")
    print(f"Wrote: {arguments.output.with_suffix('.mtl')}")


if __name__ == "__main__":
    main()
