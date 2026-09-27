"""Verify the shapefile decoding and check the coordinate system actually stored."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wenchuan import geometry as geo  # noqa: E402
from wenchuan import io as wio  # noqa: E402


for label, path in [
    ("catchments", os.path.join(wio.D1_DIR, "Debris_flow_catchment.shp")),
    ("dams", os.path.join(wio.D2_DIR, "Dataset2_damdata.shp")),
]:
    print("=" * 78)
    print(label, "->", os.path.basename(path))
    shapes = geo.read_shp(path)
    print("n_shapes:", len(shapes))
    types = {}
    for s in shapes:
        types[s.shape_type] = types.get(s.shape_type, 0) + 1
    print("shape types:", types)
    for s in shapes[:3]:
        print("  idx", s.index, "type", s.shape_type, "bbox", s.bbox,
              "n_points", len(s.points), "n_rings", len(s.rings))
    xs = [p[0] for s in shapes for p in s.points]
    ys = [p[1] for s in shapes for p in s.points]
    if xs:
        print("x range:", min(xs), max(xs))
        print("y range:", min(ys), max(ys))
    # area/centroid check
    if shapes and shapes[0].shape_type == 5:
        a, cx, cy = geo.polygon_area_centroid(shapes[0])
        print("first polygon shoelace area (deg^2):", a, "centroid:", (cx, cy))
