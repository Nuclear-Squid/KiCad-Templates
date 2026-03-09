from dataclasses import dataclass, fields
from pathlib import Path
from typing import Self

from kicad_sexp import KiCadSexpNode
import schematic_api.schematic as sch
from schematic_api.hierarchical_object import HierarchicalObject

@dataclass
class Template:
    schematic: sch.KiCadSchematic
    pcb: KiCadSexpNode
    metadata: HierarchicalObject

    @classmethod
    def from_metadata(cls, meta) -> Self:
        schematic_data = KiCadSexpNode.read_from_file(meta.sheet_file)
        schematic = sch.KiCadSchematic(meta.dev_name, schematic_data, [])
        pcb = KiCadSexpNode.from_sexpdata(["pcb"])

        return cls(schematic, pcb, meta)


def load_templates(templates_folder: Path) -> list[HierarchicalObject]:
    result = []
    for path in templates_folder.iterdir():
        template = HierarchicalObject.load_from_yaml(path / "meta.yaml")
        if template is None:
            print(f"Warning: could not load template '{template}'")
            continue

        result.append(template)
    return result


def find_template(name: str, templates: list[HierarchicalObject]) -> HierarchicalObject | None:
    for t in templates:
        if t.dev_name == name:
            return t
    return None
