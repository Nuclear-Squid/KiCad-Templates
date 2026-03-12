from dataclasses import dataclass, fields, field
from os.path import basename
from pathlib import Path
from typing import Self

import yaml

from kicad_sexp import KiCadSexpNode
import schematic_api.schematic as sch


@dataclass
class HierarchicalPin:
    name: str
    type: type
    net: str


@dataclass
class TemplateMetadata:
    dev_name: str
    sheet_name: str
    sheet_file: Path
    size_wh: tuple[float, float]
    properties: dict[str, str] = field(default_factory=dict)
    left_pins: list[HierarchicalPin] = field(default_factory=list)
    right_pins: list[HierarchicalPin] = field(default_factory=list)

    @classmethod
    def load_from_yaml(cls, path_to_yaml_metadata: Path) -> Self | None:
        with open(path_to_yaml_metadata, "r") as yaml_metadata:
            meta = yaml.safe_load(yaml_metadata)

            unpack = lambda x: HierarchicalPin(**x)
            meta["left_pins"]  = list(map(unpack, meta.get("left_pins", [])))
            meta["right_pins"] = list(map(unpack, meta.get("right_pins", [])))
            meta["dev_name"]   = basename(path_to_yaml_metadata.parent)
            meta["sheet_file"] = path_to_yaml_metadata.parent / meta["sheet_file"]

            return cls(**meta)


@dataclass
class Template:
    schematic: sch.KiCadSchematic
    pcb: KiCadSexpNode
    metadata: TemplateMetadata

    @classmethod
    def from_metadata(cls, meta) -> Self:
        schematic_data = KiCadSexpNode.read_from_file(meta.sheet_file)
        schematic = sch.KiCadSchematic(meta.dev_name, schematic_data, [])
        pcb = KiCadSexpNode.from_sexpdata(["pcb"])

        return cls(schematic, pcb, meta)


def load_templates(templates_folder: Path) -> list[TemplateMetadata]:
    result = []
    for path in templates_folder.iterdir():
        template = TemplateMetadata.load_from_yaml(path / "meta.yaml")
        if template is None:
            print(f"Warning: could not load template '{template}'")
            continue

        result.append(template)
    return result


def find_template(name: str, templates: list[TemplateMetadata]) -> TemplateMetadata | None:
    for t in templates:
        if t.dev_name == name:
            return t
    return None
