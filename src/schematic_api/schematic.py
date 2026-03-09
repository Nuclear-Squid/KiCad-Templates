from dataclasses import dataclass, fields
import os
import shutil
from pathlib import Path
from typing import Self
from uuid import uuid4

from kicad_sexp import KiCadSexpNode
import schematic_api.templates as _template

@dataclass
class KiCadSchematic:
    name: str
    data: KiCadSexpNode
    subsheets: list[Self]

    def __str__(self):
        return ''.join(map(lambda field: f"{field.name}:\n{getattr(self, field.name)}\n\n", fields(self)))

    def __repr__(self):
        return self.__str__()


    @classmethod
    def new_empty(cls, name: str):
        data = KiCadSexpNode.from_sexpdata([
            'kicad_sch',
            ["version", 20250114],
            ["generator", "eeschema"],
            ["generator_version", "9.0"],
            ["uuid", uuid4()],
            ["paper", "A4"],
            ["lib_symbols"],
            ["sheet_instances",
                ["path", "/",
                    ["page", "1"],
                ],
            ],
            ["embedded_fonts", "no"],
        ])

        return cls(name, data, [])


    # @classmethod
    # def from_file(cls, )


    def write_to_disk(self, project_path: Path):
        project_name = os.path.basename(project_path)
        self.data.write_to_file(project_path / f"{self.name}.kicad_sch")
        for sheet in self.subsheets:
            if len(sheet.subsheets) == 0:
                sheet.data.write_to_file(project_path / f"{sheet.name}.kicad_sch")
            else:
                os.mkdir(project_path / sheet.name)
                sheet.write_to_disk(project_path / sheet.name)


    def add_hierarchical_sheet(
        self,
        # attrs: sheet_name, sheet_file, at_xy, size_wh, properties, pins
        template,
        page_for_instance: str = "2",
        pin_margin_mm: float = 2.0,      # pin margin from top/bottom edges
        min_delta_mm: float = 1.0,       # minimum spacing between pins on the same side
        net_wire_len_mm: float = 5.0,    # length of wire from pin to net label
        equal_two_sides: bool = False,   # enables equal distribution on both sides
        equal_spacing_mm: float = 2.54,  # spacing (mm) in equal_two_sides mode
    ):
        at_x, at_y = float(template.metadata.at_xy[0]), float(
            template.metadata.at_xy[1])   # (at X Y) — sem rotação
        w, h = float(template.metadata.size_wh[0]), float(template.metadata.size_wh[1])
        x_left = at_x
        x_right = at_x + w
        y_top = at_y
        y_bot = at_y + h

        props = template.metadata.properties or {}
        pins = template.metadata.pins or []

        # ---- Helper functions for pin placement based on type ----
        def _spread_ys(n: int) -> list:
            """
            Alocates n Ys equally spaced between top+margin and bottom-margin.
            """
            if n <= 0:
                return []
            usable = max(h - 2 * pin_margin_mm, 0.1)
            if n == 1:
                return [at_y + h / 2.0]
            bin_h = usable / n
            first_center = y_top + pin_margin_mm + bin_h / 2.0
            return [first_center + i * bin_h for i in range(n)]

        def _resolve_y_for_group(group: list) -> list:
            autos = _spread_ys(sum(1 for p in group if "y" not in p))
            auto_it = iter(autos)
            ys = []
            for p in group:
                ys.append(float(p["y"]) if "y" in p else next(auto_it))

            low = y_top + pin_margin_mm
            high = y_bot - pin_margin_mm
            if not ys:
                return ys

            ys[0] = min(max(ys[0], low), high)
            for i in range(1, len(ys)):
                target = max(ys[i], ys[i-1] + min_delta_mm)
                ys[i] = min(target, high)

            # if it overflows at bottom, shift up as much as possible
            if ys[-1] > high and len(ys) > 1:
                overflow = ys[-1] - high
                spread = ys[-1] - ys[0]
                min_needed = min_delta_mm * (len(ys) - 1)
                slack = max(spread - min_needed, 0.0)
                shift = min(overflow, slack)
                if shift > 0:
                    ys = [y - shift for y in ys]
                    ys[0] = max(ys[0], low)
                    for i in range(1, len(ys)):
                        ys[i] = max(ys[i], ys[i-1] + min_delta_mm)
                        ys[i] = min(ys[i], high)

            return ys

        # ---- Helper function for fixed spacing and centered (any type) ----
        def _equal_spread_centered(n: int, step_mm: float) -> list:
            """
            Ys equally spaced by step_mm, centered vertically in the block.
            If it doesn't fit, reduces step to fit.
            """
            if n <= 0:
                return []

            low = y_top + pin_margin_mm
            high = y_bot - pin_margin_mm
            usable_h = max(high - low, 0.1)

            step = float(step_mm) if step_mm and step_mm > 0 else (
                usable_h / max(n, 1))
            if n == 1:
                y = at_y + h / 2.0
                return [min(max(y, low), high)]

            total = step * (n - 1)

            # If it doesn't fit, compress step
            if total > usable_h:
                step = usable_h / (n - 1)
                total = step * (n - 1)

            y0 = (at_y + h / 2.0) - total / 2.0
            ys = [y0 + i * step for i in range(n)]

            ys = [min(max(y, low), high) for y in ys]
            for i in range(1, n):
                ys[i] = max(ys[i], ys[i-1] + min_delta_mm)
                ys[i] = min(ys[i], high)

            return ys

        #   1) Chose pin distribution method
        left_pins, right_pins = [], []

        if equal_two_sides:
            # Alternates pins left/right in order of definition
            for i, p in enumerate(pins):
                (left_pins if i % 2 == 0 else right_pins).append(p)

            ys_left = _equal_spread_centered(len(left_pins),  equal_spacing_mm)
            ys_right = _equal_spread_centered(
                len(right_pins), equal_spacing_mm)
        else:
            # alternates by type
            for p in pins:
                t = p.get("type", "input")
                if t in ("input", "power_in"):
                    left_pins.append(p)
                elif t in ("output", "power_out"):
                    right_pins.append(p)
                else:
                    (left_pins if p.get("side", "right")
                     == "left" else right_pins).append(p)

            ys_left = _resolve_y_for_group(left_pins)
            ys_right = _resolve_y_for_group(right_pins)

        #   2) Builds the block (sheet ...)
        sheet_uuid = str(uuid4())
        sheet = [
            "sheet",
            ["at", at_x, at_y],
            ["size", w, h],
            ["fields_autoplaced"],
            ["stroke",
                ["width", 0.1524],
                ["type", "solid"],
                ["color", 0, 0, 0, 0],
             ],
            ["fill", ["color", 0, 0, 0, 0.0]],
            ["uuid", f"{sheet_uuid}"],
            ["property", "Sheet name", f"{template.metadata.sheet_name}",
                ["id", 0],
                ["at", at_x + 2.0, at_y - 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                 ],
             ],
            ["property", "Sheet file", f"{os.path.basename(template.metadata.sheet_file)}",
                ["id", 1],
                ["at", at_x + 2.0, at_y + 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                 ],
             ],
        ]

        # Extra properties
        prop_id = 2
        for k, v in props.items():
            sheet.append(
                ["property", f"{k}", f"{v}",
                 ["id", prop_id],
                 ["at", at_x, at_y, 0],
                 ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["hide", "yes"],
                  ]]
            )
            prop_id += 1

        #   3) Pins
        left_pin_positions = []   # [(pin_dict, (x,y))]
        right_pin_positions = []  # [(pin_dict, (x,y))]

        # Left: angle 180
        for p, y in zip(left_pins, ys_left):
            name = p.get("name", "IN")
            ptype = p.get("type", "input")
            pin_uuid = str(uuid4())
            sheet.append(
                ["pin", f"{name}", ptype,
                 ["at", x_left, y, 180.0],
                 ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                  ],
                 ["uuid", f"{pin_uuid}"]]
            )
            left_pin_positions.append((p, (x_left, y)))

        # Right: angle 0
        for p, y in zip(right_pins, ys_right):
            name = p.get("name", "OUT")
            ptype = p.get("type", "output")
            pin_uuid = str(uuid4())
            sheet.append(
                ["pin", f"{name}", ptype,
                 ["at", x_right, y, 0.0],
                 ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "right"],
                  ],
                 ["uuid", f"{pin_uuid}"]]
            )
            right_pin_positions.append((p, (x_right, y)))

        # # ---- Inserção do sheet ----
        # insert_idx = len(self.data) - 1
        # if insert_idx < 0:
        #     insert_idx = 0
        # self.data.insert(insert_idx, sheet)
        self.data.children.append(KiCadSexpNode.from_sexpdata(sheet))

        #   4) sheet_instances
        # root_uuid = self._ensure_root_uuid()
        root_uuid = self.data.get_child("uuid", max_depth=1).attributes[0]

        # si = self._ensure_section("sheet_instances")
        si = self.data.get_child("sheet_instances", max_depth=1)

        # has_root = any(
        #     isinstance(e, list) and e and e[0] == Symbol("path") and str(e[1]) == '"/"' for e in si[1:]
        # )
        has_root = False
        for path in self.data.iter_children_with_name("path"):
            if path.attributes[0] == "/":
                has_root = True
                break

        if not has_root:
            si.children.append(KiCadSexpNode.from_sexpdata(["path", "/", ["page", "1"]]))

        # Corrigido: path de folha filha deve incluir root_uuid
        # si.append(["path", f'"/{root_uuid}/{sheet_uuid}"',
        #           ["page", f'"{page_for_instance}"']])
        si.children.append(KiCadSexpNode.from_sexpdata([
            "path",
            f"/{root_uuid}/{sheet_uuid}",
            ["page", f"{page_for_instance}"]
        ]))

        #   5) NET LABELS (optional): create wires + labels for pin nets
        def _add_wire(x1, y1, x2, y2):
            self.data.children.append(KiCadSexpNode.from_sexpdata(
                ["wire",
                 ["pts", ["xy", x1, y1],
                  ["xy", x2, y2]],
                 ["stroke", ["width", 0], [
                     "type", "default"]],
                 ["uuid", uuid4()]]
            ))

        def _add_label(name, x, y, justify_sym):
            self.data.children.append(KiCadSexpNode.from_sexpdata(
                ["label", name,
                 ["at", x, y, 0],
                 ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", justify_sym]
                  ],
                 ["uuid", uuid4()]]
            ))

        # Left: wire goes to x_left - net_wire_len_mm, label at end with justify right
        for p, (px, py) in left_pin_positions:
            net = p.get("net")
            if not net:
                continue
            x2 = px - float(net_wire_len_mm)
            y2 = py
            _add_wire(px, py, x2, y2)
            _add_label(str(net), x2, y2, "right")

        # Right: wire goes to x_right + net_wire_len_mm, label at end with justify left
        for p, (px, py) in right_pin_positions:
            net = p.get("net")
            if not net:
                continue
            x2 = px + float(net_wire_len_mm)
            y2 = py
            _add_wire(px, py, x2, y2)
            _add_label(str(net), x2, y2, "left")

        # 6) Copy the actual sheet file into the correct place
        # shutil.copy(
        #     template.metadata.sheet_file,
        #     project_path / os.path.basename(template.metadata.sheet_file)
        # )
        self.subsheets.append(template.schematic)

        # return {"sheet_uuid": sheet_uuid, "root_uuid": root_uuid}
        return
