from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Union, Any
import uuid

from sexpdata import loads, Symbol

from kicad_sexp import KiCadSexpNode
from templates import TemplateMetadata


Sexp = Union[Symbol, str, int, float, List["Sexp"]]

@dataclass
class KiCadPcb:
    data: KiCadSexpNode

    def _clone_with_new_uuids(
        self,
        node: Sexp,
        uuid_map: Optional[dict[str, str]] = None,
    ) -> tuple[Sexp, dict[str, str]]:
        # Clone the whole KiCad tree while regenerating every UUID once.
        if uuid_map is None:
            uuid_map = {}

        if isinstance(node, list):
            if node and node[0] == Symbol("uuid") and len(node) >= 2 and isinstance(node[1], str):
                old_uuid = node[1].strip('"')
                new_uuid = uuid_map.setdefault(old_uuid, str(uuid.uuid4()))
                return [node[0], new_uuid, *node[2:]], uuid_map

            cloned = []
            for child in node:
                cloned_child, uuid_map = self._clone_with_new_uuids(
                    child, uuid_map)
                cloned.append(cloned_child)
            return cloned, uuid_map

        return deepcopy(node), uuid_map

    def _replace_group_member_uuids(
        self,
        node: Sexp,
        uuid_map: dict[str, str],
    ) -> None:
        # KiCad groups store member UUIDs separately, so they need a second pass.
        if not isinstance(node, list):
            return

        if node and node[0] == Symbol("group"):
            for child in node[1:]:
                if isinstance(child, list) and child and child[0] == Symbol("members"):
                    for i in range(1, len(child)):
                        member_uuid = str(child[i]).strip('"')
                        if member_uuid in uuid_map:
                            child[i] = uuid_map[member_uuid]

        for child in node:
            if isinstance(child, list):
                self._replace_group_member_uuids(child, uuid_map)

    def _get_property_node(self, node: list[Any], property_name: str) -> list[Any] | None:
        # Utility to fetch a KiCad property entry by name.
        for child in node:
            if (
                isinstance(child, list)
                and child
                and child[0] == Symbol("property")
                and len(child) > 2
                and child[1] == property_name
            ):
                return child
        return None

    def _get_symbol_reference(self, symbol_node: list[Any]) -> str | None:
        prop = self._get_property_node(symbol_node, "Reference")
        if prop is not None and len(prop) > 2 and isinstance(prop[2], str):
            return prop[2]
        return None

    def _prepare_instance_pcb(
        self,
        instance: TemplateMetadata,
        sheet_uuid: str,
    ) -> Any:
        # Create a PCB clone that matches the already-annotated schematic copy.
        if instance.pcb_file is None:
            return []

        pcb_source = loads(instance.pcb_file.read_text(encoding="utf-8"))
        pcb_data, pcb_uuid_map = self._clone_with_new_uuids(pcb_source)
        self._replace_group_member_uuids(pcb_data, pcb_uuid_map)

        footprint_reference_map: dict[str, str] = {}
        for item in pcb_data:
            if not (isinstance(item, list) and item and item[0] == Symbol("footprint")):
                continue

            # Prefer matching footprints through the schematic symbol UUID stored
            # in the footprint path, because source templates may already have
            # inconsistent or duplicated textual references.
            ref_prop = self._get_property_node(item, "Reference")
            original_ref = str(ref_prop[2]) if ref_prop is not None and len(ref_prop) > 2 else None
            original_symbol_uuid = None
            for child in item[1:]:
                if isinstance(child, list) and child and child[0] == Symbol("path") and len(child) > 1:
                    path_parts = [part for part in str(child[1]).split("/") if part]
                    original_symbol_uuid = path_parts[-1] if path_parts else None
                    break

            resolved_ref = None
            if original_symbol_uuid is not None:
                resolved_ref = instance.symbol_reference_map.get(original_symbol_uuid)
            if resolved_ref is None and original_ref is not None:
                resolved_ref = instance.reference_map.get(original_ref, original_ref)
            if original_ref is not None and resolved_ref is not None:
                footprint_reference_map[original_ref] = resolved_ref

        for item in pcb_data:
            if not (isinstance(item, list) and item):
                continue

            # Rewrite both top-level nets and per-footprint metadata so each
            # imported instance is electrically isolated from the others.
            if item[0] == Symbol("net") and len(item) > 2 and isinstance(item[1], int):
                item[2] = self._remap_net_name(
                    str(item[2]), instance, footprint_reference_map)
                continue

            if item[0] != Symbol("footprint"):
                continue

            ref_prop = self._get_property_node(item, "Reference")
            if ref_prop is not None and len(ref_prop) > 2:
                original_ref = str(ref_prop[2])
                ref_prop[2] = footprint_reference_map.get(
                    original_ref,
                    instance.reference_map.get(original_ref, original_ref),
                )

            for child in item[1:]:
                if not (isinstance(child, list) and child):
                    continue

                if child[0] == Symbol("path") and len(child) > 1:
                    path_parts = [part for part in str(child[1]).split("/") if part]
                    symbol_uuid = path_parts[-1] if path_parts else ""
                    child[1] = f"/{sheet_uuid}/{instance.schematic_uuid_map.get(symbol_uuid, symbol_uuid)}"
                elif child[0] == Symbol("sheetname") and len(child) > 1:
                    child[1] = f"/{instance.sheet_name}/"
                elif child[0] == Symbol("sheetfile") and len(child) > 1:
                    child[1] = instance.sheet_file.name

        return pcb_data

    def _replace_reference_in_net_name(
        self,
        net_name: str,
        reference_map: dict[str, str],
    ) -> str:
        # KiCad often encodes the reference directly in local net names.
        patterns = [
            r"^(Net-\()(?P<ref>[^-()]+)(?P<suffix>-.*\))$",
            r"^(unconnected-\()(?P<ref>[^-()]+)(?P<suffix>-.*\))$",
        ]
        for pattern in patterns:
            match = re.match(pattern, net_name)
            if match:
                original_ref = match.group("ref")
                new_ref = reference_map.get(original_ref, original_ref)
                return f"{match.group(1)}{new_ref}{match.group('suffix')}"
        return net_name

    def _is_reference_based_net_name(self, net_name: str) -> bool:
        return any(
            re.match(pattern, net_name)
            for pattern in (
                r"^Net-\([^()]+\)$",
                r"^unconnected-\([^()]+\)$",
            )
        )

    def sym(self, x: Any) -> str | None:
        return str(x) if isinstance(x, Symbol) else None

    def is_num(self, x: Any) -> bool:
        return isinstance(x, (int, float))

    def add_xy(self, node: List[Sexp], i_x: int, i_y: int, dx: float, dy: float) -> None:
        node[i_x] = round(float(node[i_x]) + dx, 6)  # type: ignore[index]
        node[i_y] = round(float(node[i_y]) + dy, 6)  # type: ignore[index]

    def extracts_boundaries(self, tree: Sexp) -> List:
        limits = [float('inf'), -float('inf'), float('inf'),
                  -float('inf')]  # Left, right, up, down

        if not isinstance(tree, list):
            return

        for node in tree:

            temp_limits = [0, 0, 0, 0]
            abs_temp_limits = [0, 0, 0, 0]
            coordinates = [0, 0]  # x, y

            if not isinstance(node, list) or not node:
                continue
            if self.sym(node[0]) != "footprint":
                continue

            # Only direct children; only first top-level (at ...)
            for child in node[1:]:

                is_crtyrd = False
                if not isinstance(child, list) or not child:
                    continue
                if self.sym(child[0]) == "at" and (len(child) >= 3 and self.is_num(child[1]) and self.is_num(child[2])):
                    coordinates[0] = round(float(child[1]), 6)
                    coordinates[1] = round(float(child[2]), 6)

                if self.sym(child[0]) == "fp_rect" or self.sym(child[0]) == "fp_line":
                    for child_node in child:
                        if self.sym(child_node[0]) == "layer" and child_node[1] == "F.CrtYd":
                            is_crtyrd = True
                        if self.sym(child_node[0]) == "start":
                            temp_limits[0] = child_node[1]
                            temp_limits[2] = child_node[2]
                        if self.sym(child_node[0]) == "end":
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

        # returns limits, sizes[x, y] and coordinates
        return limits, [limits[1]-limits[0], limits[3]-limits[2]]

    def move_top_level_footprints(self, origin: Sexp, dx: float, dy: float) -> Sexp:

        if not isinstance(origin, list):
            return

        tree = deepcopy(origin)

        for node in tree:

            if not isinstance(node, list) or not node:
                continue
            if self.sym(node[0]) != "footprint":
                continue

            # Only direct children; only first top-level (at ...)
            for child in node[1:]:
                if not isinstance(child, list) or not child:
                    continue
                if self.sym(child[0]) == "at" and (len(child) >= 3 and self.is_num(child[1]) and self.is_num(child[2])):
                    self.add_xy(child, 1, 2, dx, dy)

        return tree

    def move_tracks_and_vias(self, tree: Sexp, dx: float, dy: float) -> None:
        """
        Recursively walk the whole tree and move:
        - segment: start/end
        - arc: start/mid/end
        - via: at
        """
        if not isinstance(tree, list):
            return

        head = self.sym(tree[0]) if tree else None

        if head == "segment":
            # Find (start x y) and (end x y) sublists
            for child in tree[1:]:
                if isinstance(child, list) and child:
                    h = self.sym(child[0])
                    if h in ("start", "end") and len(child) >= 3 and self.is_num(child[1]) and self.is_num(child[2]):
                        self.add_xy(child, 1, 2, dx, dy)

        elif head == "arc":
            # Find (start x y), (mid x y), (end x y)
            for child in tree[1:]:
                if isinstance(child, list) and child:
                    h = self.sym(child[0])
                    if h in ("start", "mid", "end") and len(child) >= 3 and self.is_num(child[1]) and self.is_num(child[2]):
                        self.add_xy(child, 1, 2, dx, dy)

        elif head == "via":
            # Find (at x y [..])
            for child in tree[1:]:
                if isinstance(child, list) and child and self.sym(child[0]) == "at":
                    if len(child) >= 3 and self.is_num(child[1]) and self.is_num(child[2]):
                        self.add_xy(child, 1, 2, dx, dy)
                    break

        # Recurse
        for child in tree:
            if isinstance(child, list):
                self.move_tracks_and_vias(child, dx, dy)

    def _next_project_net_id(self, pcb_data: KiCadSexpNode) -> int:
        # Imported PCB chunks reuse net IDs, so each append needs a new range.
        max_net_id = 0
        # for item in pcb_data:
        #     if (
        #         isinstance(item, list)
        #         and item
        #         and item[0] == Symbol("net")
        #         and len(item) > 1
        #         and isinstance(item[1], int)
        #     ):
        #         max_net_id = max(max_net_id, int(item[1]))
        for net in pcb_data.iter_children_with_name("net"):
            # if isinstance(net.attributes[1], int):
            max_net_id = max(max_net_id, int(net.attributes[0]))

        return max_net_id + 1

    def _remap_pcb_net_ids(
        self,
        pcb_data: Sexp,
        start_net_id: int,
    ) -> tuple[Sexp, int]:
        # Shift net IDs before merging so different subsystem copies stay disjoint.
        if not isinstance(pcb_data, list):
            return pcb_data, start_net_id

        net_id_map = {0: 0}
        net_name_map = {0: ""}
        next_net_id = start_net_id

        for item in pcb_data:
            if (
                isinstance(item, list)
                and item
                and item[0] == Symbol("net")
                and len(item) > 2
                and isinstance(item[1], int)
            ):
                old_id = int(item[1])
                if old_id == 0:
                    item[2] = ""
                    continue
                if old_id not in net_id_map:
                    net_id_map[old_id] = next_net_id
                    next_net_id += 1
                net_name_map[old_id] = str(item[2])
                item[1] = net_id_map[old_id]

        def _walk(node: Sexp) -> None:
            if not isinstance(node, list):
                return

            if node and node[0] == Symbol("net") and len(node) > 1 and isinstance(node[1], int):
                old_id = int(node[1])
                if old_id in net_id_map:
                    node[1] = net_id_map[old_id]
                    if len(node) > 2 and old_id in net_name_map:
                        node[2] = net_name_map[old_id]

            for child in node:
                if isinstance(child, list):
                    _walk(child)

        _walk(pcb_data)
        return pcb_data, next_net_id

    def _remap_net_name(
        self,
        net_name: str,
        instance: TemplateMetadata,
        footprint_reference_map: dict[str, str] | None = None,
    ) -> str:
        # Reference-based local nets keep their KiCad naming style,
        # while hierarchical labels are namespaced by sheet instance.
        if not net_name:
            return net_name

        reference_map = footprint_reference_map or instance.reference_map
        remapped = self._replace_reference_in_net_name(
            net_name, reference_map)
        if self._is_reference_based_net_name(net_name):
            return remapped

        suffix = net_name.lstrip("/")
        return f"/{instance.sheet_name}/{suffix}"

    def get_uuid(self, pcb_item) -> str | None:
        for attribute in pcb_item:
            if isinstance(attribute, list) and str(attribute[0]) == "uuid":
                return attribute[1]
        return None

    def group_pcb_items(self, pcb_data):
        uuids = []
        groups = []

        for item in pcb_data:
            if str(item[0]) == "group":
                groups.append(item)
            elif self.get_uuid(item) is not None:
                uuids.append(self.get_uuid(item))

        # HACK: Assume Groups have a consistent strcuture with in this order:
        # - "group" as Symbol
        # - empty string
        # - uuid attribute
        # - members attribute
        for group in groups:
            for member in group[3][1:]:
                # print(member)
                if member in uuids:
                    uuids.remove(member)
            uuids.append(group[2][1])

        if len(uuids) > 2:
            pcb_data.append([
                Symbol('group'),
                '',
                [Symbol('uuid'), str(uuid.uuid4())],
                [Symbol('members'), *uuids],
            ])

    def add_pcb(
        self,
        project_path: Path,
        pcb_data: Sexp,
    ) -> None:
        # Merge a prepared PCB fragment into the project while normalizing net IDs.
        # project_pcb_path = project_path / f"{project_path.name}.kicad_pcb"
        # project_pcb_data = loads(project_pcb_path.read_text(encoding="utf-8"))
        project_pcb_data = self.data

        pcb_data, _ = self._remap_pcb_net_ids(
            pcb_data, self._next_project_net_id(project_pcb_data))

        useful_symbols = ["net", "footprint", "segment", "arc", "via", "group"]
        useful_pcb_data = [
            item for item in pcb_data
            if (
                isinstance(item, list)
                and item
                and str(item[0]) in useful_symbols
                and not (item[0] == Symbol("net") and len(item) > 1 and item[1] == 0)
            )
        ]
        self.group_pcb_items(useful_pcb_data)

        # print(KiCadSexpNode.from_sexpdata(useful_pcb_data))
        # project_pcb_data += useful_pcb_data
        for item in useful_pcb_data:
            project_pcb_data.append(KiCadSexpNode.from_sexpdata(item))

        # with open(project_pcb_path, "w", encoding="utf-8") as pcb_file:
        #     pcb_file.write(_format_sexp_kicad(project_pcb_data))

    def add_multiple_designs(
        self,
        project_path,
        design_instances: Iterable[dict[str, Any]],
        space_x=9.5,
        space_y=5.5,
        max_x=285,
        max_y=198,
        cursor_x0=25,
        cursor_y0=25
    ):
        '''
        Takes prepared PCB instances, and, minding their limits, arranges them in the sheet.
        In a loop:
        1) Places a design and updates a cursor
        2) Moves the next design according to the cursor and stores the moved design into a variable
        3) Restarts the loop
        '''
        cursor = [cursor_x0, cursor_y0]

        line_height = 0

        for placed in design_instances:
            instance: TemplateMetadata = placed["object"].metadata

            # The PCB is prepared per instance first, then translated on the board.
            tree = self._prepare_instance_pcb(instance, placed["sheet_uuid"])
            if not tree:
                continue

            abs_lim, dimensions = self.extracts_boundaries(tree)

            center_coord = [(abs_lim[1]+abs_lim[0])/2,
                            (abs_lim[3]+abs_lim[2])/2]

            if dimensions[0] > max_x or dimensions[1] > max_y:
                raise ValueError(
                    f"Dimensions exceeded design limits in {instance.pcb_file}")

            if dimensions[0] > max_x - cursor[0]:  # Moves the cursor down one line
                if dimensions[1] > max_y - cursor[1]:
                    raise ValueError(
                        f"Dimensions exceeded design limits in {instance.pcb_file}")
                cursor[1] += line_height + space_y
                cursor[0] = cursor_x0
                line_height = 0

            # Adapts the vertical line difference
            if line_height < dimensions[1]:
                line_height = dimensions[1]

            dx = cursor[0] - center_coord[0]
            dy = cursor[1] - center_coord[1]
            moved_instance = self.move_top_level_footprints(
                tree, dx, dy)
            self.move_tracks_and_vias(moved_instance, dx, dy)
            self.add_pcb(project_path=project_path, pcb_data=moved_instance)

            cursor[0] += dimensions[0] + space_x
