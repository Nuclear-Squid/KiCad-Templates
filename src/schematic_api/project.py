from dataclasses import dataclass, fields
import os
from pathlib import Path
from shutil import copy
import textwrap
from typing import Self, ClassVar

from kicad_sexp import KiCadSexpNode
from schematic_api.schematic import KiCadSchematic

PROJECT_FOLDER = Path(__file__).parent.parent.parent


@dataclass
class KiCadProject:
    project_path: Path
    schematic: KiCadSchematic
    pcb: KiCadSexpNode
    fp_lib_table: KiCadSexpNode
    sym_lib_table: KiCadSexpNode
    project_raw_json: str

    template_folders: ClassVar[list[Path]] = [ PROJECT_FOLDER / "subsystems" ]

    def __init__(self, project_path: Path):
        self.project_path = project_path
        project_name = os.path.basename(project_path)

        self.schematic = KiCadSchematic.new_empty(project_name)

        self.pcb = KiCadSexpNode.from_sexpdata([
            "kicad_pcb",
            ["version", 20241229],
            ["generator", "pcbnew"],
            ["generator_version", "9.0"],
        ])

        self.fp_lib_table = KiCadSexpNode.from_sexpdata([
            "fp_lib_table",
            ["lib",
                 ["name", "User"],
                 ["type", "KiCad"],
                 ["uri", "${KIPRJMOD}/../subsystems/mikrobus/mikrobus.pretty"],
                 ["options", ""],
                 ["descr", "Mikrobus Footprints"],
             ],
        ])

        self.sym_lib_table = KiCadSexpNode.from_sexpdata([
            "sym_lib_table",
            ["lib",
                 ["name", "Microbus"],
                 ["type", "KiCad"],
                 ["uri", "${KIPRJMOD}/../subsystems/mikrobus/MIKROE-4247.kicad_sym"],
                 ["options", ""],
                 ["descr", "Biblioteca de simbolos do usuario"],
             ],
        ])

        self.project_raw_json = textwrap.dedent('''
        {
          "board": {
            "design_settings": {
              "defaults": {},
              "diff_pair_dimensions": [],
              "drc_exclusions": [],
              "rules": {},
              "track_widths": [],
              "via_dimensions": []
            }
          },
          "boards": [],
          "libraries": {
            "pinned_footprint_libs": [],
            "pinned_symbol_libs": []
          },
          "meta": {
            "filename": "kicad.kicad_pro",
            "version": 1
          },
          "net_settings": {
            "classes": [],
            "meta": {
              "version": 0
            }
          },
          "pcbnew": {
            "page_layout_descr_file": ""
          },
          "sheets": [],
          "text_variables": {}
        }
        ''')

    def __str__(self):
        return ''.join(map(lambda field: f"{field.name}:\n{getattr(self, field.name)}\n\n", fields(self)))

    def __repr__(self):
        return self.__str__()

    def write_to_disk(self):
        project_name = os.path.basename(self.project_path)
        # project_path = PROJECT_FOLDER / self.project_name
        os.mkdir(self.project_path)

        with open(self.project_path / f"{project_name}.kicad_pro", "w", encoding="utf-8") as f:
            f.write(self.project_raw_json)

        # self.schematic.write_to_file(self.project_path / f"{project_name}.kicad_sch")
        self.schematic.write_to_disk(self.project_path)

        self.pcb.write_to_file(self.project_path / f"{project_name}.kicad_pcb")
        self.fp_lib_table.write_to_file(self.project_path / "fp-lib-table")
        self.sym_lib_table.write_to_file(self.project_path / "sym-lib-table")
