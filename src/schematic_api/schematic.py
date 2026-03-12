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


    @classmethod  # metadata is type TemplateMetadata
    def new_sheet(cls, metadata, position: tuple[Number, Number]) -> Self:
        width = float(metadata.size_wh[0])
        height = float(metadata.size_wh[1])

        sheet = KiCadSexpNode.from_sexpdata([
            "sheet",
            ["at", position[0], position[1]],
            ["size", width, height],
            ["fields_autoplaced"],
            ["stroke",
                ["width", 0.1524],
                ["type", "solid"],
                ["color", 0, 0, 0, 0],
            ],
            ["fill", ["color", 0, 0, 0, 0.0]],
            ["uuid", uuid4()],
            ["property", "Sheet name", metadata.sheet_name,
                ["id", 0],
                ["at", position[0] + 2.0, position[1] - 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                ],
            ],
            ["property", "Sheet file", os.path.basename(metadata.sheet_file),
                ["id", 1],
                ["at", position[0] + 2.0, position[1] + 2.0, 0],
                ["effects",
                    ["font", ["size", 1.27, 1.27]],
                    ["justify", "left"],
                ],
            ],
        ])

        # Extra properties
        for k, v in metadata.properties.items():
            sheet.append(KiCadSexpNode.make_property(k, v, position, hide=True))

        return sheet


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
        sheet = self.new_sheet(metadata, position)

        def place_pins(pin_list, pos_x, pos_y, rotation, label_x_offset, justify_label):
            justify_pin = "right" if justify_label == "left" else "left"
            start_height = position[1] + (height - len(pin_list)  * 2.54)  / 2
            for i, pin in enumerate(pin_list):
                pos_y = start_height + i * 2.54
                x_end = pos_x + float(label_x_offset)
                sheet.append(KiCadSexpNode.make_pin(pin.name, pin.type, pos_x, pos_y, rotation, justify_pin))
                self.data.append(KiCadSexpNode.make_wire(pos_x, pos_y, x_end, pos_y))
                self.data.append(KiCadSexpNode.make_label(pin.net, x_end, pos_y, justify_label))

        place_pins(metadata.left_pins,  position[0],         position[1], 180, -net_wire_len_mm, "right")
        place_pins(metadata.right_pins, position[0] + width, position[1],   0,  net_wire_len_mm, "left")

        root_uuid = lambda x: x.get_child("uuid", max_depth=1).attributes[0]
        self.data.get_child("sheet_instances", max_depth=1).append([
            "path",
            f"/{root_uuid(self.data)}/{root_uuid(sheet)}",
            ["page", f"{page_for_instance}"]
        ])

        self.data.append(sheet)
        self.subsheets.append(schematic)
