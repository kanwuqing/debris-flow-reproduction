"""Minimal ESRI shapefile reader (polygons + points) and planar geometry helpers.

Only what this reproduction needs, so that no ``gdal``/``geopandas``/``pyshp``
dependency is required:

* ``read_shp`` decodes shape records (``Null``=0, ``Point``=1, ``Polygon``=5).
* ``polygon_area_centroid`` uses the shoelace formula.
* ``point_in_polygon`` is a ray-casting test with the boundary counted as inside.

The catchment polygons are stored in WGS84 / UTM zone 48N (see the shipped
``.prj``), but the coordinates in the file are **geographic degrees**, which is
why areas are taken from the ``Area`` column of the ``.dbf`` instead of being
recomputed here.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field


@dataclass
class Shape:
    index: int
    shape_type: int
    bbox: tuple[float, float, float, float] | None = None
    points: list[tuple[float, float]] = field(default_factory=list)
    parts: list[int] = field(default_factory=list)

    @property
    def rings(self) -> list[list[tuple[float, float]]]:
        if not self.parts:
            return [self.points] if self.points else []
        bounds = list(self.parts) + [len(self.points)]
        return [self.points[bounds[i] : bounds[i + 1]] for i in range(len(self.parts))]


def read_shp(path: str) -> list[Shape]:
    """Decode every record of a ``.shp`` file."""
    with open(path, "rb") as fh:
        blob = fh.read()

    if len(blob) < 100:
        return []

    shapes: list[Shape] = []
    pos = 100  # 100-byte header
    index = 0
    while pos + 8 <= len(blob):
        _rec_num, content_len = struct.unpack_from(">ii", blob, pos)
        pos += 8
        end = pos + content_len * 2
        if end > len(blob):
            break
        (shape_type,) = struct.unpack_from("<i", blob, pos)
        shape = Shape(index=index, shape_type=shape_type)
        index += 1

        if shape_type == 1:  # Point
            x, y = struct.unpack_from("<dd", blob, pos + 4)
            shape.points = [(x, y)]
            shape.bbox = (x, y, x, y)
        elif shape_type in (3, 5):  # PolyLine / Polygon
            bbox = struct.unpack_from("<4d", blob, pos + 4)
            (n_parts,) = struct.unpack_from("<i", blob, pos + 36)
            (n_points,) = struct.unpack_from("<i", blob, pos + 40)
            parts = list(struct.unpack_from(f"<{n_parts}i", blob, pos + 44))
            pts_off = pos + 44 + 4 * n_parts
            coords = struct.unpack_from(f"<{2 * n_points}d", blob, pts_off)
            shape.bbox = bbox
            shape.parts = parts
            shape.points = [(coords[2 * i], coords[2 * i + 1]) for i in range(n_points)]

        shapes.append(shape)
        pos = end
    return shapes


def ring_area_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Signed area and centroid of one ring (shoelace formula)."""
    if len(ring) < 3:
        return 0.0, 0.0, 0.0
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-15:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / n, sum(ys) / n
    return a, cx / (6 * a), cy / (6 * a)


def polygon_area_centroid(shape: Shape) -> tuple[float, float, float]:
    """Total signed area and area-weighted centroid across all rings of a shape."""
    total_a = 0.0
    wx = wy = 0.0
    for ring in shape.rings:
        a, cx, cy = ring_area_centroid(ring)
        total_a += a
        wx += a * cx
        wy += a * cy
    if abs(total_a) < 1e-15:
        pts = shape.points
        if not pts:
            return 0.0, float("nan"), float("nan")
        return 0.0, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return total_a, wx / total_a, wy / total_a


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    """Ray casting; points on the edge are treated as inside."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        # on-segment check
        cross = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
        if abs(cross) < 1e-12 and min(x0, x1) - 1e-12 <= x <= max(x0, x1) + 1e-12 \
                and min(y0, y1) - 1e-12 <= y <= max(y0, y1) + 1e-12:
            return True
        if (y0 > y) != (y1 > y):
            x_at = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < x_at:
                inside = not inside
    return inside


def point_in_shape(x: float, y: float, shape: Shape) -> bool:
    """Even-odd test over all rings (holes are handled by the parity flip)."""
    hits = 0
    for ring in shape.rings:
        if point_in_ring(x, y, ring):
            hits += 1
    return hits % 2 == 1