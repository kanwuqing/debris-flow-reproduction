"""Static (event-independent) catchment features derived from the shapefile.

These features describe the catchment *form* only and are therefore safe to use
as predictors in the susceptibility model, where the label is derived from the
debris-flow event counts.  The polygon coordinates are stored in WGS84 / UTM
zone 48N metres (see ``Debris_flow_catchment.prj``), so areas and perimeters are
metric.

Derived quantities
------------------
``poly_area_km2``      shoelace area of the polygon (cross-check of the ``Area``
                       attribute in the ``.dbf``).
``poly_perimeter_km``  ring length.
``compactness``        4*pi*A / P^2  (1.0 = circle; smaller = more elongated).
``bbox_km``            bounding-box width / height and their aspect ratio.
``centroid_lon/lat``   polygon centroid converted back to WGS84 degrees.
``elev_proxy_*``       not available -- the archive ships no DEM, so no terrain
                       features are invented here.
"""

from __future__ import annotations

import math

from . import geometry as geo
from . import io as wio

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
UTM_K0 = 0.9996
UTM_LON0 = 105.0
UTM_FE = 500000.0
UTM_FN = 0.0


def utm_to_lonlat(easting: float, northing: float) -> tuple[float, float]:
    """Inverse transverse Mercator (WGS84, UTM zone 48N). Metres -> degrees."""
    e2 = WGS84_F * (2 - WGS84_F)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    x = easting - UTM_FE
    y = northing - UTM_FN
    m = y / UTM_K0
    mu = m / (
        WGS84_A
        * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256)
    )
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )
    sin_phi = math.sin(phi1)
    cos_phi = math.cos(phi1)
    tan_phi = math.tan(phi1)

    ep2 = e2 / (1 - e2)
    c1 = ep2 * cos_phi**2
    t1 = tan_phi**2
    n1 = WGS84_A / math.sqrt(1 - e2 * sin_phi**2)
    r1 = WGS84_A * (1 - e2) / (1 - e2 * sin_phi**2) ** 1.5
    d = x / (n1 * UTM_K0)

    lat = phi1 - (n1 * tan_phi / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
    )
    lon = (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
    ) / cos_phi
    return UTM_LON0 + math.degrees(lon), math.degrees(lat)


def catchment_polygon_features() -> list[dict]:
    """One record per catchment polygon, in shapefile record order."""
    shapes = geo.read_shp(wio.D1_DIR + "/Debris_flow_catchment.shp")
    catch = wio.load_catchments()

    rows: list[dict] = []
    for i, shape in enumerate(shapes):
        area_m2, cx, cy = geo.polygon_area_centroid(shape)
        perimeter_m = 0.0
        for ring in shape.rings:
            n = len(ring)
            for k in range(n):
                x0, y0 = ring[k]
                x1, y1 = ring[(k + 1) % n]
                perimeter_m += math.hypot(x1 - x0, y1 - y0)

        width_km = height_km = float("nan")
        if shape.bbox:
            width_km = (shape.bbox[2] - shape.bbox[0]) / 1000.0
            height_km = (shape.bbox[3] - shape.bbox[1]) / 1000.0

        lon, lat = (float("nan"), float("nan"))
        if cx == cx and cy == cy:
            lon, lat = utm_to_lonlat(cx, cy)

        area_km2 = abs(area_m2) / 1e6
        perim_km = perimeter_m / 1000.0
        compactness = (
            4 * math.pi * (abs(area_m2)) / (perimeter_m**2) if perimeter_m > 0 else float("nan")
        )

        rec = dict(catch.iloc[i].to_dict())
        rec.update(
            polygon_index=i,
            poly_area_km2=area_km2,
            poly_perimeter_km=perim_km,
            compactness=compactness,
            bbox_width_km=width_km,
            bbox_height_km=height_km,
            bbox_aspect=(width_km / height_km) if height_km else float("nan"),
            centroid_lon=lon,
            centroid_lat=lat,
        )
        rows.append(rec)
    return rows