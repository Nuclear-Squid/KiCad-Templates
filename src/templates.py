from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, fields, field
from os.path import basename
from pathlib import Path
import re
from typing import Self
from uuid import uuid4

import yaml

from kicad_sexp import KiCadSexpNode
import schematic as sch


@dataclass
class HierarchicalPin:
    name: str
    type: str
    net:  str


@dataclass
class TemplateMetadata:
    dev_name: str
    sheet_name: str
    sheet_file: Path
    pcb_file:   Path
    size_wh: tuple[float, float]
    properties: dict[str, str] = field(default_factory=dict)
    left_pins: list[HierarchicalPin] = field(default_factory=list)
    right_pins: list[HierarchicalPin] = field(default_factory=list)
    reference_map: dict[str, str] = field(default_factory=dict)
    schematic_uuid_map: dict[str, str] = field(default_factory=dict)
    symbol_reference_map: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load_from_yaml(cls, path_to_yaml_metadata: Path) -> Self | None:
        with open(path_to_yaml_metadata, "r") as yaml_metadata:
            meta = yaml.safe_load(yaml_metadata)

            unpack = lambda x: HierarchicalPin(**x)
            meta["left_pins"]  = list(map(unpack, meta.get("left_pins", [])))
            meta["right_pins"] = list(map(unpack, meta.get("right_pins", [])))
            meta["dev_name"]   = basename(path_to_yaml_metadata.parent)
            meta["sheet_file"] = path_to_yaml_metadata.parent / meta["sheet_file"]
            meta["pcb_file"]   = path_to_yaml_metadata.parent / meta["pcb_file"]

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
                result.append(basename(path))
        return result


    @classmethod
    def get_template(cls, name: str, templates_folders: list[Path]) -> Self | None:
        for folder in templates_folders:
            for template in folder.iterdir():
                if basename(template) == name:
                    return cls.from_path_to_folder(template)
        return None


    @classmethod
    def get_templates(cls, template_names: Iterable[str], templates_folders: list[Path]) -> list[Self]:
        result = []
        ref_counters = {}
        for name in template_names:
            template = cls.get_template(name, templates_folders)
            if template is None:
                print(f"Warning: could not find template '{name}'")
                continue

            template.fill_reference_maps(ref_counters)
            result.append(template)

        return result

    def _allocate_reference(
        self,
        original_ref: str,
        ref_counters: dict[str, int],
    ) -> str:
        # Keep numbering global per prefix so repeated subsystems never collide.
        match = re.match(r"^([^0-9]*?)(\d+)$", original_ref)
        if match:
            prefix, digits = match.groups()
            width = len(digits)
        else:
            prefix = original_ref
            width = 0

        ref_counters[prefix] = ref_counters.get(prefix, 0) + 1
        next_value = ref_counters[prefix]
        if width > 0:
            return f"{prefix}{str(next_value).zfill(width)}"
        return f"{prefix}{next_value}"

    def fill_reference_maps(self, ref_counters: dict[str, int]):
        # # Build a per-instance copy of the subsystem with unique filenames,
        # # fresh UUIDs, and an annotation map we can later reuse for the PCB.
        # source_sheet = Path(template.sheet_file)
        # sheet_name = self._build_unique_name(template.sheet_name, occurrence)
        # sheet_filename = self._build_unique_name(source_sheet.stem, occurrence) + source_sheet.suffix
        # target_sheet = project_path / sheet_filename

        # schematic_source = loads(source_sheet.read_text(encoding="utf-8"))
        # source_symbols = [
        #     node for node in schematic_source
        #     if isinstance(node, list) and node and node[0] == Symbol("symbol")
        # ]
        schematic_source = self.schematic.data
        source_symbols = list(schematic_source.iter_children_with_name("symbol", max_depth=1))

        units_by_reference: dict[str, set[int]] = {}
        for source_node in source_symbols:
            # original_ref = self._get_symbol_reference(source_node)
            original_ref = source_node.get_property("Reference").attributes[1]
            if not original_ref:
                continue

            ref_prefix, ref_num = split_reference(original_ref)
            units_by_reference.setdefault(original_ref, set()).add(ref_num)

        multi_unit_refs = {
            ref for ref, units in units_by_reference.items() if len(units) > 1
        }

        # schematic_data, schematic_uuid_map = self._clone_with_new_uuids(schematic_source)
        schematic_data = deepcopy(schematic_source)
        schematic_uuid_map = {}
        for id in schematic_data.iter_children_with_name("uuid"):
            new_uuid = uuid4()
            schematic_uuid_map[id.attributes[0]] = new_uuid
            id.attributes[0] = new_uuid

        # cloned_symbols = [
        #     node for node in schematic_data
        #     if isinstance(node, list) and node and node[0] == Symbol("symbol")
        # ]
        cloned_symbols = list(schematic_data.iter_children_with_name("symbol", max_depth=1))

        instance_ref_map: dict[str, str] = {}
        symbol_reference_map: dict[str, str] = {}

        # for node in cloned_symbols: print(node)

        for source_node, cloned_node in zip(source_symbols, cloned_symbols):
            node = cloned_node
            # original_ref = self._get_symbol_reference(node)
            original_ref = node.get_property("Reference").attributes[1]
            if not original_ref:
                continue

            if original_ref in multi_unit_refs:
                new_ref = instance_ref_map.get(original_ref)
            else:
                new_ref = self._allocate_reference(original_ref, ref_counters)
                instance_ref_map.setdefault(original_ref, new_ref)

            # # Update the schematic symbol itself and remember the UUID -> ref link
            # # so the PCB can rename the matching footprint later.
            # ref_property = self._get_property_node(node, "Reference")
            # if ref_property is not None:
            #     ref_property[2] = new_ref
            node.get_property("Reference").attributes[1] = new_ref

            # source_symbol_uuid = self._get_symbol_uuid(source_node)
            source_symbol_uuid = source_node.get_child("uuid").attributes[0]
            if source_symbol_uuid:
                symbol_reference_map[source_symbol_uuid] = new_ref

        self.metadata.reference_map = instance_ref_map
        self.metadata.schematic_uuid_map = schematic_uuid_map
        self.metadata.symbol_reference_map = symbol_reference_map

def split_reference(ref: str) -> tuple[str, int]:
    match = re.match(r"^([^0-9]*?)(\d+)$", ref)
    prefix, digits = match.groups()
    return prefix, int(digits)
