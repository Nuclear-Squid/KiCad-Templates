from dataclasses import dataclass, fields
import os
from pathlib import Path
import shutil
from typing import Self, TYPE_CHECKING
from uuid import uuid4

from kicad_sexp import KiCadSexpNode
from schematic_api.hierarchical_object import HierarchicalObject
# from schematic_api.templates import TemplateMetadata

Number = int | float

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


    @classmethod
    def new_sheet(cls, sheet_name, sheet_file, w, h, x, y) -> Self:
        return KiCadSexpNode.from_sexpdata([
            "sheet",
            ["at", x, y],
            ["size", w, h],
            ["fields_autoplaced"],
            ["stroke",
                ["width", 0.1524],
                ["type", "solid"],
                ["color", 0, 0, 0, 0],
            ],
            ["fill", ["color", 0, 0, 0, 0.0]],
            ["uuid", uuid4()],
            ["property", "Sheet name", sheet_name,
                ["id", 0],
                ["at", x + 2.0, y - 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                ],
            ],
            ["property", "Sheet file", os.path.basename(sheet_file),
                ["id", 1],
                ["at", x + 2.0, y + 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                ],
            ],
        ])


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
        schematic: Self,
        metadata, # type = TemplateMetadata,
        position: tuple[Number, Number],
        page_for_instance: str = "2",
        net_wire_len_mm: float = 5.0,    # length of wire from pin to net label
    ):
        w = float(metadata.size_wh[0])
        h = float(metadata.size_wh[1])

        x_left  = position[0]
        x_right = position[0] + w
        y_top   = position[1]
        y_bot   = position[1] + h

        props = metadata.properties or {}

        left_pins  = metadata.left_pins
        right_pins = metadata.right_pins

        #   2) Builds the block (sheet ...)
        sheet = self.new_sheet(
            metadata.sheet_name,
            metadata.sheet_file,
            w,
            h,
            position[0],
            position[1]
        )

        # Extra properties
        for k, v in props.items():
            sheet.append(KiCadSexpNode.make_property(k, v, position, hide=True))

        pin_indexes_left  = range(len(left_pins))
        pin_indexes_right = range(len(right_pins))

        start_height_left  = position[1] + (h - len(left_pins)  * 2.54)  / 2
        start_height_right = position[1] + (h - len(right_pins) * 2.54) / 2

        ys_left  = map(lambda x: x * 2.54 + start_height_left,  pin_indexes_left)
        ys_right = map(lambda x: x * 2.54 + start_height_right, pin_indexes_right)

        # Left: angle 180
        for pin, y in zip(left_pins, ys_left):
            x_end = x_left - float(net_wire_len_mm)
            sheet.append(KiCadSexpNode.make_pin(pin.name, pin.type, x_left, y))
            self.data.append(KiCadSexpNode.make_wire(x_left, y, x_end, y))
            self.data.append(KiCadSexpNode.make_label(pin.net, x_end, y, "right"))

        # Right: angle 0
        for p, y in zip(right_pins, ys_right):
            x_end = x_right + float(net_wire_len_mm)
            sheet.append(KiCadSexpNode.make_pin(pin.name, pin.type, x_right, y))
            self.data.append(KiCadSexpNode.make_wire(x_right, y, x_end, y))
            self.data.append(KiCadSexpNode.make_label(pin.net, x_end, y, "left"))


        # # ---- Inserção do sheet ----
        # self.data.append_sexp(sheet)
        self.data.append(sheet)

        #   4) sheet_instances
        root_uuid = self.data.get_child("uuid", max_depth=1).attributes[0]
        si = self.data.get_child("sheet_instances", max_depth=1)

        has_root = False
        for path in self.data.iter_children_with_name("path"):
            if path.attributes[0] == "/":
                has_root = True
                break

        if not has_root:
            si.append(["path", "/", ["page", "1"]])

        # Corrigido: path de folha filha deve incluir root_uuid
        si.append([
            "path",
            f"/{root_uuid}/{sheet.get_child("uuid")}",
            ["page", f"{page_for_instance}"]
        ])

        self.subsheets.append(schematic)

        return
