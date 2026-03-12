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
    def from_path_to_folder(cls, path: Path) -> Self:
        metadata = TemplateMetadata.load_from_yaml(path / "meta.yaml")
        schematic = sch.KiCadSchematic(
            metadata.dev_name,
            KiCadSexpNode.read_from_file(metadata.sheet_file)
        )
        pcb = KiCadSexpNode.from_sexpdata(["pcb"])
        return cls(schematic, pcb, metadata)


    @classmethod
    def list_templates(cls, templates_folders: list[Path]) -> list[str]:
        result = []
        for folder in templates_folders:
            for path in folder.iterdir():
                # Check template is valid by trying to parse the metadata file
                template = TemplateMetadata.load_from_yaml(path / "meta.yaml")
                if template is None:
                    print(f"Warning: could not load template '{template}'")
                    continue
                result.append(path)
        return result


    @classmethod
    def get_template(cls, name: str, templates_folders: list[Path]) -> Self | None:
        for folder in templates_folders:
            for template in folder.iterdir():
                if basename(template) == name:
                    return cls.from_path_to_folder(template)
        return None


    @classmethod
    def get_templates(cls, template_names: list[str], templates_folders: list[Path]) -> list[Self]:
        result = []
        for name in template_names:
            template = cls.get_template(name, templates_folders)
            if template is None:
                print(f"Warning: could not find template '{name}'")
                continue

            result.append(template)

        return result
