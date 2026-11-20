"""Recompute Olympic Park tennis long-axis azimuth from OSM.

Public APIs do not publish court bearing. This script reads the Center Court
pitch polygon (OSM way 615723982) and prints the play-axis heading.
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request

WAY_ID = 615723982
QUERY = f"""
[out:json][timeout:40];
way({WAY_ID});
out geom;
"""


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def dist_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def main() -> None:
    payload = urllib.parse.urlencode({"data": QUERY}).encode("utf-8")
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=payload,
        method="POST",
        headers={
            "User-Agent": "TennisLab/1.0 (olympic-park-tennis-azimuth)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))
    geom = data["elements"][0]["geometry"]
    pts = [(p["lat"], p["lon"]) for p in geom]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    edges = []
    for i, start in enumerate(pts):
        end = pts[(i + 1) % len(pts)]
        edges.append((dist_m(*start, *end), bearing_deg(*start, *end)))
    long_edges = sorted(edges, reverse=True)[:2]
    bearings = [e[1] if e[1] < 180 else e[1] - 180 for e in long_edges]
    axis = sum(bearings) / len(bearings)
    heading = axis if 45 <= axis <= 135 else (axis + 180) % 360
    print("long edges m/brg", [(round(e[0], 1), round(e[1], 1)) for e in long_edges])
    print("play_heading_deg", round(heading))


if __name__ == "__main__":
    main()
