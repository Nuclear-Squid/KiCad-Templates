#!/usr/bin/env python3
"""
Move:
  1) ONLY the top-level (at x y [rot]) of each (footprint ...)
  2) Track geometry:
       (segment (start x y) (end x y) ...)
       (arc (start x y) (mid x y) (end x y) ...)   # if present
  3) Vias:
       (via (at x y ...) ...)

Does NOT move nested (at ...) inside footprints (pads, fp_text, primitives, etc.).

Usage:
  python3 move_board.py input.kicad_pcb output.kicad_pcb --dx 10 --dy -5

Dependency:
  pip install sexpdata
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, List, Union

from sexpdata import loads, dumps, Symbol  # type: ignore

Sexp = Union[Symbol, str, int, float, List["Sexp"]]


def sym(x: Any) -> str | None:
    return str(x) if isinstance(x, Symbol) else None


def is_num(x: Any) -> bool:
    return isinstance(x, (int, float))


def add_xy(node: List[Sexp], i_x: int, i_y: int, dx: float, dy: float) -> None:
    node[i_x] = round(float(node[i_x]) + dx, 6)  # type: ignore[index]
    node[i_y] = round(float(node[i_y]) + dy, 6)  # type: ignore[index]


def move_top_level_footprints(tree: Sexp, dx: float, dy: float) -> None:
    limits = [float('inf'), -float('inf'), float('inf'),
              -float('inf')]  # Left, right, up, down

    if not isinstance(tree, list):
        return

    for node in tree:

        temp_limits = [0, 0, 0, 0]
        abs_temp_limits = [0, 0, 0, 0]
        coordinates = [0, 0]

        if not isinstance(node, list) or not node:
            continue
        if sym(node[0]) != "footprint":
            continue

        # Only direct children; only first top-level (at ...)
        for child in node[1:]:

            is_crtyrd = False
            if not isinstance(child, list) or not child:
                continue
            if sym(child[0]) == "at" and (len(child) >= 3 and is_num(child[1]) and is_num(child[2])):
                add_xy(child, 1, 2, dx, dy)
                coordinates[0] = round(float(child[1]), 6)
                coordinates[1] = round(float(child[2]), 6)

            if sym(child[0]) == "fp_rect" or sym(child[0]) == "fp_line":
                for child_node in child:
                    if sym(child_node[0]) == "layer" and child_node[1] == "F.CrtYd":
                        is_crtyrd = True
                    if sym(child_node[0]) == "start":
                        temp_limits[0] = child_node[1]
                        temp_limits[2] = child_node[2]
                    if sym(child_node[0]) == "end":
                        temp_limits[1] = child_node[1]
                        temp_limits[3] = child_node[2]
            if is_crtyrd:
                abs_temp_limits[0] = temp_limits[0] + coordinates[0]
                abs_temp_limits[1] = temp_limits[1] + coordinates[0]
                abs_temp_limits[2] = temp_limits[2] + coordinates[1]
                abs_temp_limits[3] = temp_limits[3] + coordinates[1]

                limits[0] = min(abs_temp_limits[0], limits[0])
                limits[1] = max(abs_temp_limits[1], limits[1])
                limits[2] = min(abs_temp_limits[2], limits[2])
                limits[3] = max(abs_temp_limits[3], limits[3])


def move_tracks_and_vias(tree: Sexp, dx: float, dy: float) -> None:
    """
    Recursively walk the whole tree and move:
      - segment: start/end
      - arc: start/mid/end
      - via: at
    """
    if not isinstance(tree, list):
        return

    head = sym(tree[0]) if tree else None

    if head == "segment":
        # Find (start x y) and (end x y) sublists
        for child in tree[1:]:
            if isinstance(child, list) and child:
                h = sym(child[0])
                if h in ("start", "end") and len(child) >= 3 and is_num(child[1]) and is_num(child[2]):
                    add_xy(child, 1, 2, dx, dy)

    elif head == "arc":
        # Find (start x y), (mid x y), (end x y)
        for child in tree[1:]:
            if isinstance(child, list) and child:
                h = sym(child[0])
                if h in ("start", "mid", "end") and len(child) >= 3 and is_num(child[1]) and is_num(child[2]):
                    add_xy(child, 1, 2, dx, dy)

    elif head == "via":
        # Find (at x y [..])
        for child in tree[1:]:
            if isinstance(child, list) and child and sym(child[0]) == "at":
                if len(child) >= 3 and is_num(child[1]) and is_num(child[2]):
                    add_xy(child, 1, 2, dx, dy)
                break

    # Recurse
    for child in tree:
        if isinstance(child, list):
            move_tracks_and_vias(child, dx, dy)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--dx", type=float, required=True)
    ap.add_argument("--dy", type=float, required=True)
    args = ap.parse_args()

    text = args.input.read_text(encoding="utf-8")
    tree = loads(text)

    move_top_level_footprints(tree, args.dx, args.dy)
    move_tracks_and_vias(tree, args.dx, args.dy)

    # KiCad accepts the S-expression even if formatting changes.
    args.output.write_text(dumps(tree), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
