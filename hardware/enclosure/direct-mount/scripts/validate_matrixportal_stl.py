#!/usr/bin/env python3
"""Reject a MatrixPortal carrier STL that is disconnected or floats above z=0."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path


def read_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    triangles = []
    vertices = []
    with path.open(encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            fields = raw.strip().split()
            if not fields or fields[0] != "vertex":
                continue
            if len(fields) != 4:
                raise ValueError(f"invalid vertex record in {path}: {raw.rstrip()}")
            vertices.append(tuple(round(float(value), 6) for value in fields[1:]))
            if len(vertices) == 3:
                triangles.append(tuple(vertices))
                vertices = []
    if vertices:
        raise ValueError(f"incomplete triangle at end of {path}")
    if not triangles:
        raise ValueError(f"no triangles found in {path}")
    return triangles


def connected_components(triangles):
    edge_to_triangles = defaultdict(list)
    for index, triangle in enumerate(triangles):
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge_to_triangles[tuple(sorted((first, second)))].append(index)

    neighbours = [set() for _ in triangles]
    for indices in edge_to_triangles.values():
        for index in indices:
            neighbours[index].update(other for other in indices if other != index)

    seen = set()
    components = []
    for start in range(len(triangles)):
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        component = []
        while queue:
            index = queue.popleft()
            component.append(index)
            for neighbour in neighbours[index]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        components.append(component)
    return components


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stl", type=Path)
    args = parser.parse_args()
    triangles = read_triangles(args.stl)
    components = connected_components(triangles)
    z_values = [vertex[2] for triangle in triangles for vertex in triangle]
    minimum_z = min(z_values)
    maximum_z = max(z_values)

    print(f"{args.stl}: triangles={len(triangles)} components={len(components)}")
    print(f"z bounds: {minimum_z:.6f}..{maximum_z:.6f}")
    if len(components) != 1:
        raise SystemExit("FAIL: expected exactly one connected component")
    if abs(minimum_z) > 1e-6:
        raise SystemExit("FAIL: carrier geometry does not reach the z=0 support plane")
    print("PASS: one connected shell reaches z=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
