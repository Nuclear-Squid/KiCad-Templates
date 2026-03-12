from dataclasses import dataclass, fields
import os
from pathlib import Path
import shutil
from typing import Self, TYPE_CHECKING
from uuid import uuid4

from kicad_sexp import KiCadSexpNode
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
    def new_sheet(cls, sheet_name, sheet_file, width, height, x, y) -> Self:
        return KiCadSexpNode.from_sexpdata([
            "sheet",
            ["at", x, y],
            ["size", width, height],
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
        width = float(metadata.size_wh[0])
        height = float(metadata.size_wh[1])

        sheet = self.new_sheet(
            metadata.sheet_name,
            metadata.sheet_file,
            width,
            height,
            position[0],
            position[1]
        )

        # Extra properties
        for k, v in metadata.properties.items():
            sheet.append(KiCadSexpNode.make_property(k, v, position, hide=True))

        def place_pins(pin_list, pos_x, pos_y, label_x_offset):
            start_height = position[1] + (height - len(pin_list)  * 2.54)  / 2
            for i, pin in enumerate(pin_list):
                pos_y = start_height + i * 2.54
                x_end = pos_x + float(label_x_offset)
                sheet.append(KiCadSexpNode.make_pin(pin.name, pin.type, pos_x, pos_y))
                self.data.append(KiCadSexpNode.make_wire(pos_x, pos_y, x_end, pos_y))
                self.data.append(KiCadSexpNode.make_label(pin.net, x_end, pos_y, "right"))

        place_pins(metadata.left_pins,  position[0], position[1], -net_wire_len_mm)
        place_pins(metadata.right_pins, position[0] + width, position[1],  net_wire_len_mm)

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
