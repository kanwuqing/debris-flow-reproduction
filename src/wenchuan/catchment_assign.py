"""Assign debris-flow events to catchments by point-in-polygon (authoritative).

The published tables identify the catchment only indirectly: the event table
carries a free-text gully name, while the catchment table carries a
``/``-joined list of gully names.  Pinyin spelling differs between the two
(e.g. event ``Ergou`` vs catchment ``Er``), so a name join leaves 19 of 186
events unassigned.

The catchment polygons ship as a shapefile, and every event carries a
coordinate pair, so the catchment is instead resolved geometrically:

1. convert the event's WGS84 degrees to UTM 48N metres (``utm_to_lonlat`` run
   in reverse),
2. test the point against every catchment ring (even-odd ray casting),
3. fall back to the nearest polygon centroid when a point falls just outside
   every polygon (coordinate rounding in the published CSV).

The name join is still computed and kept, so the report can quantify how often
the two disagree.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import geometry as geo
from . import io as wio
from .catchment_geom import WGS84_A, WGS84_F, UTM_FE, UTM_FN, UTM_K0, UTM_LON0


def lonlat_to_utm(lon: float, lat: float) -> tuple[float, float]:
    """Forward transverse Mercator (WGS84, UTM zone 48N). Degrees -> metres."""
    e2 = WGS84_F * (2 - WGS84_F)
    ep2 = e2 / (1 - e2)
    phi = math.radians(lat)
    lam = math.radians(lon - UTM_LON0)

    sin_phi, cos_phi, tan_phi = math.sin(phi), math.cos(phi), math.tan(phi)
    n = WGS84_A / math.sqrt(1 - e2 * sin_phi**2)
    t = tan_phi**2
    c = ep2 * cos_phi**2
    a = cos_phi * lam

    m = WGS84_A * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
        - (35 * e2**3 / 3072) * math.sin(6 * phi)
    )

    easting = UTM_FE + UTM_K0 * n * (
        a
        + (1 - t + c) * a**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * a**5 / 120
    )
    northing = UTM_FN + UTM_K0 * (
        m
        + n * tan_phi * (
            a**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * a**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * a**6 / 720
        )
    )
    return easting, northing


def load_catchment_shapes() -> tuple[list[geo.Shape], pd.DataFrame]:
    shapes = geo.read_shp(wio.D1_DIR + "/Debris_flow_catchment.shp")
    catch = wio.load_catchments()
    return shapes, catch


def _point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom <= 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distance_to_shape_m(x: float, y: float, shape: geo.Shape) -> float:
    """Shortest distance from a point to any ring of a polygon, in metres.

    Unlike a nearest-*centroid* rule this stays correct for elongated
    catchments, where the centroid can be far from the boundary an event
    actually sits next to.
    """
    best = float("inf")
    for ring in shape.rings:
        n = len(ring)
        if n < 2:
            continue
        for k in range(n):
            ax, ay = ring[k]
            bx, by = ring[(k + 1) % n]
            d = _point_segment_distance(x, y, ax, ay, bx, by)
            if d < best:
                best = d
    return best


def assign_catchments(events: pd.DataFrame) -> pd.DataFrame:
    """Return ``events`` with ``C_ID_geom``, ``geom_hit`` and ``centroid_dist_km``."""
    shapes, catch = load_catchment_shapes()
    names = catch["catchment_name"].to_numpy()
    cids = catch["C_ID"].to_numpy()

    centroids = []
    for shape in shapes:
        _a, cx, cy = geo.polygon_area_centroid(shape)
        centroids.append((cx, cy))

    out = events.copy()
    geom_cid: list[str | None] = []
    hit_kind: list[str] = []
    dist_km: list[float] = []

    for row in out.itertuples():
        lon, lat = row.lon, row.lat
        if not (lon == lon and lat == lat):
            geom_cid.append(None)
            hit_kind.append("no_coord")
            dist_km.append(float("nan"))
            continue
        x, y = lonlat_to_utm(float(lon), float(lat))

        found = None
        for i, shape in enumerate(shapes):
            if shape.bbox and not (
                shape.bbox[0] <= x <= shape.bbox[2] and shape.bbox[1] <= y <= shape.bbox[3]
            ):
                continue
            if geo.point_in_shape(x, y, shape):
                found = i
                break

        if found is not None:
            geom_cid.append(cids[found])
            hit_kind.append("inside")
            dist_km.append(0.0)
            continue

        # nearest-boundary fallback (metres -> km).  Events are recorded at the
        # gully mouth / deposition fan, which frequently lies just outside the
        # watershed polygon, so distance-to-boundary is the meaningful metric.
        best_i, best_d = None, float("inf")
        for i, shape in enumerate(shapes):
            d = distance_to_shape_m(x, y, shape)
            if d < best_d:
                best_i, best_d = i, d
        geom_cid.append(cids[best_i] if best_i is not None else None)
        hit_kind.append("nearest_boundary")
        dist_km.append(best_d / 1000.0)

    out["C_ID_geom"] = geom_cid
    out["geom_hit"] = hit_kind
    out["centroid_dist_km"] = dist_km
    out.attrs["catchment_names"] = dict(zip(cids, names))
    return out