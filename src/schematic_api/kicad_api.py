import sexpdata
from sexpdata import loads, dumps, Symbol
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from shutil import copy
from pathlib import Path
import re
import os
import glob
import uuid
import pprint
from copy import deepcopy

from schematic_api.hierarchical_object import HierarchicalObject  # Ajoute cette ligne


PROJECT_FOLDER = Path(__file__).parent.parent.parent
Sexp = Union[Symbol, str, int, float, List["Sexp"]]


@dataclass
class InstantiatedSubsystem:
    # Represents one concrete copy of a reusable subsystem inside a project.
    dev_name: str
    sheet_name: str
    sheet_file: Path
    pcb_file: Path | None
    at_xy: list[float]
    size_wh: list[float]
    properties: dict | None = None
    pins: list | None = None
    schematic_data: list[Any] = field(default_factory=list)
    reference_map: dict[str, str] = field(default_factory=dict)
    schematic_uuid_map: dict[str, str] = field(default_factory=dict)
    symbol_reference_map: dict[str, str] = field(default_factory=dict)


def _format_sexp_kicad(data, indent=0) -> str:
    """
    Formate une S-expression selon le style exact de KiCad :
    - Tabs pour indentation
    - Les atomes simples sur la même ligne
    - Les sous-listes indentées
    - Pas de parenthèses isolées sur des lignes vides
    """
    TAB = "\t"

    def fmt_atom(x):
        if isinstance(x, Symbol):
            return str(x)
        if isinstance(x, str):
            # Supprimer d’éventuels guillemets d’enrobage
            raw = x.strip()
            if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
                raw = raw[1:-1]
            # Échapper les backslashes et guillemets
            raw = raw.replace("\\", "\\\\").replace('"', '\\"')
            # Retourner la chaîne entre guillemets
            return f'"{raw}"'
        return str(x)

    if isinstance(data, (list, tuple)):
        if not data:
            return "()"

        # Si la liste contient uniquement des atomes => inline
        if all(not isinstance(x, (list, tuple)) for x in data):
            return f"({' '.join(fmt_atom(x) for x in data)})"

        # Sinon, on gère indentation
        out = "("
        first_line_atoms = []

        for x in data:
            if isinstance(x, (list, tuple)):
                # sous-liste → saute une ligne
                if first_line_atoms:
                    out += " ".join(fmt_atom(a) for a in first_line_atoms)
                    first_line_atoms = []
                out += "\n" + (TAB * (indent + 1)) + \
                    _format_sexp_kicad(x, indent + 1)
            else:
                first_line_atoms.append(x)

        # Si on a accumulé des atomes à la fin
        if first_line_atoms:
            out += " " + " ".join(fmt_atom(a) for a in first_line_atoms)

        out += "\n" + (TAB * indent) + ")"
        return out

    # Cas atome seul
    return fmt_atom(data)


class KiCadLibrary:
    """Classe pour gérer les bibliothèques de symboles (.kicad_sym) et d'empreintes (.pretty)."""

    '''
    @staticmethod
    @staticmethod
    def import_symbol_library(lib_path: str) -> Dict[str, Dict[str, List]]:
        """Importe une bibliothèque de symboles (.kicad_sym) ou un dossier de bibliothèques."""
        libraries = {}
        if os.path.isdir(lib_path):
            # Charger tous les fichiers .kicad_sym dans le dossier
            for sym_file in glob.glob(os.path.join(lib_path, "*.kicad_sym")):
                with open(sym_file, 'r', encoding='utf-8') as f:
                    lib_data = loads(f.read())
                    lib_name = os.path.basename(sym_file).replace(".kicad_sym", "")
                    libraries[lib_name] = KiCadLibrary._extract_symbols(lib_data)
        else:
            # Charger un fichier .kicad_sym spécifique
            with open(lib_path, 'r', encoding='utf-8') as f:
                lib_data = loads(f.read())
                lib_name = os.path.basename(lib_path).replace(".kicad_sym", "")
                libraries[lib_name] = KiCadLibrary._extract_symbols(lib_data)
        return libraries
    '''

    def _format_sexp(self, data, indent=0) -> str:
        return _format_sexp_kicad(data, indent)

    # @staticmethod
    def extract_symbols(self, lib_path: str, lib_prefix: str, ref: str) -> str:
        """Extrait tous les symboles d'un fichier .kicad_sym et les retourne sous forme de S-Expressions."""
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_data = loads(f.read())

        # symbols = {}
        for item in lib_data:
            if isinstance(item, list) and item and item[0] == Symbol("symbol"):
                symbol_name = str(item[1])
                if symbol_name == ref:
                    item[1] = f'"{lib_prefix}:{ref}"'
                    return self._format_sexp(item)
        return ""

    @staticmethod
    def extract_all_symbols(lib_path: str) -> Dict[str, List]:
        """Extrait tous les symboles d'un fichier .kicad_sym et les retourne sous forme de S-Expressions."""
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_data = loads(f.read())

        symbols = {}
        for item in lib_data:
            if isinstance(item, list) and item and item[0] == Symbol("symbol"):
                symbol_name = str(item[1])
                symbols[symbol_name] = item

        return symbols

    @staticmethod
    def print_symbols(symbols: Dict[str, List]) -> None:
        """Affiche les S-Expressions des symboles extraits."""
        for symbol_name, symbol_data in symbols.items():
            print(f"Symbole : {symbol_name}")
            print(dumps(symbol_data))
            print("\n" + "=" * 50 + "\n")

    @staticmethod
    def export_symbol_library(symbols: List[Dict], output_path: str) -> None:
        """Exporte une bibliothèque de symboles (.kicad_sym)."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dumps([symbol["data"] for symbol in symbols]))

    @staticmethod
    def import_footprint_library(lib_dir: str) -> Dict[str, List[Dict]]:
        """Importe une bibliothèque d'empreintes (.pretty)."""
        footprints = {}
        for fp_file in glob.glob(os.path.join(lib_dir, "*.kicad_mod")):
            with open(fp_file, "r", encoding="utf-8") as f:
                fp_data = loads(f.read())
                fp_name = os.path.basename(fp_file).replace(".kicad_mod", "")
                footprints[fp_name] = fp_data
        return footprints

    @staticmethod
    def export_footprint_library(footprints: Dict[str, List], output_dir: str) -> None:
        """Exporte une bibliothèque d'empreintes (.pretty)."""
        os.makedirs(output_dir, exist_ok=True)
        for fp_name, fp_data in footprints.items():
            with open(
                os.path.join(output_dir, f"{fp_name}.kicad_mod"), "w", encoding="utf-8"
            ) as f:
                f.write(dumps(fp_data))


class KiCadSchematic:
    """Classe pour manipuler les fichiers schématiques KiCad (.kicad_sch)."""

    def __init__(self, file_path: Optional[str] = None):
        self.data: Union[List, Dict] = []
        self.libraries: Dict[str, List[Dict]] = {}
        if file_path:
            self.import_schematic(file_path)

    def _ensure_root_uuid(self) -> str:
        """Garante que o schematic tenha um uuid de raiz ( (uuid "...") ) e devolve o valor."""
        for elem in self.data:
            if isinstance(elem, list) and elem and elem[0] == Symbol("uuid"):
                return str(elem[1]).strip('"')

        new_uid = str(uuid.uuid4())
        # insere logo após o cabeçalho (kicad_sch ...)
        # self.data é [Symbol('kicad_sch'), (version ...), (generator ...), ...]
        self.data.insert(1, [Symbol("uuid"), f'"{new_uid}"'])
        return new_uid

    def _ensure_section(self, name: str):
        """Garante que exista uma seção (name ...) e retorna a própria lista."""
        for elem in self.data:
            if isinstance(elem, list) and elem and elem[0] == Symbol(name):
                return elem
        section = [Symbol(name)]
        self.data.append(section)
        return section

    def add_hierarchical_sheet(
        self,
        # attrs: sheet_name, sheet_file, at_xy, size_wh, properties, pins
        project_path,
        object,
        page_for_instance: str = "2",
        pin_margin_mm: float = 2.0,      # pin margin from top/bottom edges
        min_delta_mm: float = 1.0,       # minimum spacing between pins on the same side
        net_wire_len_mm: float = 5.0,    # length of wire from pin to net label
        equal_two_sides: bool = False,   # enables equal distribution on both sides
        equal_spacing_mm: float = 2.54,  # spacing (mm) in equal_two_sides mode
    ):
        at_x, at_y = float(object.at_xy[0]), float(
            object.at_xy[1])   # (at X Y) — sem rotação
        w, h = float(object.size_wh[0]), float(object.size_wh[1])
        x_left = at_x
        x_right = at_x + w
        y_top = at_y
        y_bot = at_y + h

        props = object.properties or {}
        pins = object.pins or []

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
        sheet_uuid = str(uuid.uuid4())
        sheet = [
            Symbol("sheet"),
            [Symbol("at"), at_x, at_y],
            [Symbol("size"), w, h],
            [Symbol("fields_autoplaced")],
            [Symbol("stroke"),
                [Symbol("width"), 0.1524],
                [Symbol("type"), Symbol("solid")],
                [Symbol("color"), 0, 0, 0, 0],
             ],
            [Symbol("fill"), [Symbol("color"), 0, 0, 0, 0.0]],
            [Symbol("uuid"), f'"{sheet_uuid}"'],
            [Symbol("property"), '"Sheet name"', f'"{object.sheet_name}"',
                [Symbol("id"), 0],
                [Symbol("at"), at_x + 2.0, at_y - 2.0, 0],
                [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("left")],
                 ],
             ],
            [Symbol("property"), '"Sheet file"', f'"{os.path.basename(object.sheet_file)}"',
                [Symbol("id"), 1],
                [Symbol("at"), at_x + 2.0, at_y + 2.0, 0],
                [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("left")],
                 ],
             ],
        ]

        # Extra properties
        prop_id = 2
        for k, v in props.items():
            sheet.append(
                [Symbol("property"), f'"{k}"', f'"{v}"',
                 [Symbol("id"), prop_id],
                 [Symbol("at"), at_x, at_y, 0],
                 [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("hide"), Symbol("yes")],
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
            pin_uuid = str(uuid.uuid4())
            sheet.append(
                [Symbol("pin"), f'"{name}"', Symbol(ptype),
                 [Symbol("at"), x_left, y, 180.0],
                 [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("left")],
                  ],
                 [Symbol("uuid"), f'"{pin_uuid}"']]
            )
            left_pin_positions.append((p, (x_left, y)))

        # Right: angle 0
        for p, y in zip(right_pins, ys_right):
            name = p.get("name", "OUT")
            ptype = p.get("type", "output")
            pin_uuid = str(uuid.uuid4())
            sheet.append(
                [Symbol("pin"), f'"{name}"', Symbol(ptype),
                 [Symbol("at"), x_right, y, 0.0],
                 [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("right")],
                  ],
                 [Symbol("uuid"), f'"{pin_uuid}"']]
            )
            right_pin_positions.append((p, (x_right, y)))

        # ---- Inserção do sheet ----
        insert_idx = len(self.data) - 1
        if insert_idx < 0:
            insert_idx = 0
        self.data.insert(insert_idx, sheet)

        #   4) sheet_instances
        root_uuid = self._ensure_root_uuid()
        si = self._ensure_section("sheet_instances")

        has_root = any(
            isinstance(e, list) and e and e[0] == Symbol(
                "path") and str(e[1]).strip('"') == "/"
            for e in si[1:]
        )
        if not has_root:
            si.append([Symbol("path"), "/", [Symbol("page"), "1"]])

        # Corrigido: path de folha filha deve incluir root_uuid
        si.append([Symbol("path"), f"/{root_uuid}/{sheet_uuid}",
                  [Symbol("page"), str(page_for_instance)]])

        #   5) NET LABELS (optional): create wires + labels for pin nets
        def _add_wire(x1, y1, x2, y2):
            self.data.append(
                [Symbol("wire"),
                 [Symbol("pts"), [Symbol("xy"), x1, y1],
                  [Symbol("xy"), x2, y2]],
                 [Symbol("stroke"), [Symbol("width"), 0], [
                     Symbol("type"), Symbol("default")]],
                 [Symbol("uuid"), f'"{uuid.uuid4()}"']]
            )

        def _add_label(name, x, y, justify_sym):
            self.data.append(
                [Symbol("label"), f'"{name}"',
                 [Symbol("at"), x, y, 0],
                 [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol(justify_sym)]
                  ],
                 [Symbol("uuid"), f'"{uuid.uuid4()}"']]
            )

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

        return {"sheet_uuid": sheet_uuid, "root_uuid": root_uuid}

    def add_hierarchical_sheets(
        self,
        project_path: Path,
        objects,                          # list of HierarchicalObjects
        # initial position (top-left) for placement
        origin_xy=(50.0, 50.0),
        # row for horizontal breaks, column for vertical breaks (not implemented)
        flow="row",
        # max width before line break (only for flow=row)
        max_row_width_mm=180.0,
        # gap horizontal = max(h_gap_factor * w_obj, min_hgap)
        h_gap_factor=0.5,
        # gap vertical   = max(v_gap_factor * h_row, min_vgap)
        v_gap_factor=0.8,
        min_hgap=4.0,                     # minimum gaps (mm) para legibilidade
        min_vgap=6.0,
        page_for_instance_start=2,
        pin_margin_mm=2.0,                # used on add_hierarchical_sheet
        min_delta_mm=1.0,                 # used on add_hierarchical_sheet
    ):
        """
        Adds several hierarchical sheets arranged automatically.
        Returns metadata [{object, sheet_uuid, at_xy, size_wh, page}, ...].
        """
        placed = []
        cursor_x, cursor_y = float(origin_xy[0]), float(origin_xy[1])
        row_height = 0.0
        row_left_edge = cursor_x
        page_num = int(page_for_instance_start)

        def _hgap(w):  # gap proportional to object width
            # return max(h_gap_factor * float(w), float(min_hgap))
            return 25  # constant value for better spacing

        def _vgap(h):  # gap proportional to row height
            # return max(v_gap_factor * float(h), float(min_vgap))
            return 10  # constant value for better spacing
        for obj in objects:
            w = float(obj.size_wh[0])
            h = float(obj.size_wh[1])

            # line break when exceeding max row width
            if flow == "row" and (cursor_x > row_left_edge) and (cursor_x + w > row_left_edge + float(max_row_width_mm)):
                # next line
                cursor_x = row_left_edge
                cursor_y = cursor_y + row_height + _vgap(row_height)
                row_height = 0.0

            # places block
            obj.at_xy = [cursor_x, cursor_y]
            meta = self.add_hierarchical_sheet(
                project_path,
                object=obj,
                page_for_instance=str(page_num),
                pin_margin_mm=pin_margin_mm,
                min_delta_mm=min_delta_mm,
                equal_two_sides=True,
            )
            placed.append({
                "object": obj,
                "sheet_uuid": meta.get("sheet_uuid"),
                "root_uuid": meta.get("root_uuid"),
                "at_xy": tuple(obj.at_xy),
                "size_wh": tuple(obj.size_wh),
                "page": page_num
            })

            # fowards cursor
            cursor_x += w + _hgap(w)
            row_height = max(row_height, h)
            page_num += 1

        return placed

    def _format_sexp(self, data, indent=0) -> str:
        return _format_sexp_kicad(data, indent)

    def import_schematic(self, file_path: str) -> None:
        """Importe un fichier schématique KiCad."""
        with open(file_path, "r", encoding="utf-8") as f:
            self.data = loads(f.read())

    def export_schematic(self, output_path: str) -> None:
        """Exporte le schématique vers un fichier, avec un formatage lisible."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self._format_sexp(self.data))

    def add_component(
        self,
        symbol_data: str,
        ref: str,
        value: str,
        footprint: str,
        at: list,
        project_name: str = "project",
    ):
        """
        Transforme un symbole de librairie en composant schématique complet.
        """
        try:
            lib_symbol = loads(symbol_data)
        except Exception as e:
            print(f"Erreur parsing symbole: {e}")
            return

        # 1️⃣ Vérifier si la section (lib_symbols ...) existe
        lib_symbols_idx = next(
            (
                i
                for i, elem in enumerate(self.data)
                if isinstance(elem, list) and elem and elem[0] == Symbol("lib_symbols")
            ),
            None,
        )

        if lib_symbols_idx is not None:
            lib_section = self.data[lib_symbols_idx]

        # Extraire le nom du symbole lib (ex: "Device:R")
        lib_name = None
        if (
            isinstance(lib_symbol, list)
            and len(lib_symbol) > 1
            and isinstance(lib_symbol[1], str)
        ):
            lib_name = lib_symbol[1].strip('"')  # "Device:R"

            # 2️⃣ Vérifier si ce lib_name est déjà dans la section
            already_in_lib = False
            print(lib_name)
            if lib_name:
                for entry in lib_section[1:]:
                    if (
                        isinstance(entry, list)
                        and len(entry) > 1
                        and entry[0] == Symbol("symbol")
                        and entry[1] == lib_name
                    ):
                        already_in_lib = True
                        break

            # 3️⃣ Si pas présent, on l’ajoute au début de (lib_symbols ...)
            if not already_in_lib:
                print(
                    f"➕ Ajout du symbole '{lib_name}' dans la section (lib_symbols)")
                try:
                    lib_symbol_ast = loads(symbol_data)
                    lib_section.insert(1, lib_symbol_ast)
                except Exception as e:
                    print(f"Erreur lors de l'ajout du symbole lib: {e}")
        else:
            print("⚠️ Pas de section (lib_symbols) trouvée dans le schéma.")

        # 1️⃣ Récupérer le UUID global du schéma
        global_uuid = None
        for elem in self.data:
            if isinstance(elem, list) and elem and elem[0] == Symbol("uuid"):
                global_uuid = elem[1].strip('"')
                # print("GLOBAL UUID",global_uuid)
                break

        # Nom du symbole (ex: Device:R)
        lib_name = None
        if (
            isinstance(lib_symbol, list)
            and len(lib_symbol) > 1
            and isinstance(lib_symbol[1], str)
        ):
            lib_name = lib_symbol[1].strip('"')

        # Commence un nouveau composant schématique
        component = [
            Symbol("symbol"),
            [Symbol("lib_id"), f'"{lib_name}"'],
            [Symbol("at"), float(at[0]), float(at[1]), 0],
            [Symbol("unit"), 1],
            [Symbol("exclude_from_sim"), Symbol("no")],
            [Symbol("in_bom"), Symbol("yes")],
            [Symbol("on_board"), Symbol("yes")],
            [Symbol("dnp"), Symbol("no")],
            [Symbol("fields_autoplaced"), Symbol("yes")],
            [Symbol("uuid"), f'"{uuid.uuid4()}"'],
        ]

        # --- Extraire les propriétés principales du symbole lib ---
        for prop in lib_symbol:
            if isinstance(prop, list) and prop and prop[0] == Symbol("property"):
                name = prop[1].strip('"')

                if name == "Reference":
                    # Position du label ref relative au point d'insertion
                    component.append(
                        [
                            Symbol("property"),
                            '"Reference"',
                            f'"{ref}"',
                            [Symbol("at"), float(at[0]) + 2.54,
                             float(at[1]) - 1.27, 0],
                            [
                                Symbol("effects"),
                                [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                                [Symbol("justify"), Symbol("left")],
                            ],
                        ]
                    )

                elif name == "Value":
                    component.append(
                        [
                            Symbol("property"),
                            '"Value"',
                            f'"{value}"',
                            [Symbol("at"), float(at[0]) + 2.54,
                             float(at[1]) + 1.27, 0],
                            [
                                Symbol("effects"),
                                [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                                [Symbol("justify"), Symbol("left")],
                            ],
                        ]
                    )

                elif name == "Footprint":
                    component.append(
                        [
                            Symbol("property"),
                            '"Footprint"',
                            f'"{footprint}"',
                            [Symbol("at"), float(at[0]) -
                             1.778, float(at[1]), 90],
                            [
                                Symbol("effects"),
                                [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                                [Symbol("hide"), Symbol("yes")],
                            ],
                        ]
                    )

                else:
                    # Copier les autres propriétés (Datasheet, Description, etc.)
                    if name not in (
                        "Reference",
                        "Value",
                        "Footprint",
                        "Datasheet",
                        "Description",
                    ):
                        continue
                    else:
                        component.append(prop)

        # --- Transformer les sous-symboles en vrais pins KiCad ---
        for sub in lib_symbol:
            if isinstance(sub, list) and sub and sub[0] == Symbol("symbol"):
                for item in sub:
                    if isinstance(item, list) and item and item[0] == Symbol("pin"):
                        # Extraire le numéro de pin
                        num = None
                        for elt in item:
                            if isinstance(elt, list) and elt[0] == Symbol("number"):
                                num = elt[1].strip('"')
                        if num:
                            component.append(
                                [
                                    Symbol("pin"),
                                    f'"{num}"',
                                    [Symbol("uuid"), f'"{uuid.uuid4()}"'],
                                ]
                            )

        # --- Ajouter les instances ---
        component.append(
            [
                Symbol("instances"),
                [
                    Symbol("project"),
                    f'"{project_name}"',
                    [
                        Symbol("path"),
                        f'"/{global_uuid}"',
                        [Symbol("reference"), f'"{ref}"'],
                        [Symbol("unit"), 1],
                    ],
                ],
            ]
        )

        # Trouver où insérer avant la fin (on insère avant le dernier élément)
        insert_index = len(self.data) - 2
        # 🔹 Insérer avant la fin
        self.data.insert(insert_index, component)

    def transform_library_symbol_to_schematic(
        self, lib_symbol: List, ref: str, value: str, at: List[float]
    ) -> List:
        """
        Transforme un symbole de bibliothèque en composant de schématique.
        Args:
            lib_symbol: S-Expression du symbole extrait de la bibliothèque
            ref: Référence du composant (ex: "R1")
            value: Valeur du composant (ex: "1k")
            at: Position [x, y]
        Returns:
            S-Expression du composant prêt pour le schématique
        """
        # Extraire le nom du symbole (ex: "R")
        symbol_name = (
            str(lib_symbol[1]) if isinstance(
                lib_symbol[1], Symbol) else lib_symbol[1]
        )

        # Créer la structure du composant pour le schématique
        component = [
            Symbol("symbol"),
            [Symbol("lib_id"), f'"Device:{symbol_name}"'],
            [Symbol("at"), *at, 0],  # Position et rotation
            [Symbol("unit"), 1],
            [Symbol("in_bom"), Symbol("yes")],
            [Symbol("on_board"), Symbol("yes")],
            [Symbol("dnp"), Symbol("no")],
            [Symbol("fields_autoplaced"), Symbol("yes")],
            [Symbol("uuid"), f'"{uuid.uuid4()}"'],  # UUID aléatoire
            # Propriété Reference
            [
                Symbol("property"),
                '"Reference"',
                f'"{ref}"',
                [Symbol("at"), at[0] + 2.032, at[1], 90],
                [
                    Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), "1.27", "1.27"]],
                    [Symbol("justify"), Symbol("left")],
                ],
            ],
            # Propriété Value
            [
                Symbol("property"),
                '"Value"',
                f'"{value}"',
                [Symbol("at"), at[0] + 2.032, at[1] + 2.54, 90],
                [
                    Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("left")],
                ],
            ],
            # Propriété Footprint (cachée)
            [
                Symbol("property"),
                '"Footprint"',
                '""',
                [Symbol("at"), at[0] - 1.778, at[1], 90],
                [
                    Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("hide"), Symbol("yes")],
                ],
            ],
            # Autres propriétés (cachées)
            [
                Symbol("property"),
                '"Datasheet"',
                '"~"',
                [Symbol("at"), at[0], at[1], 0],
                [
                    Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("hide"), Symbol("yes")],
                ],
            ],
            # Pins (simplifiés)
            [Symbol("pin"), '"1"', [Symbol("uuid"), f'"{uuid.uuid4()}"']],
            [Symbol("pin"), '"2"', [Symbol("uuid"), f'"{uuid.uuid4()}"']],
            # Instances (pour le projet)
            [
                Symbol("instances"),
                [
                    Symbol("project"),
                    '"test_python"',
                    [
                        Symbol("path"),
                        f'"/{uuid.uuid4()}"',
                        [Symbol("reference"), f'"{ref}"'],
                        [Symbol("unit"), 1],
                    ],
                ],
            ],
        ]

        return component

    def remove_component(self, ref: str) -> bool:
        """Supprime un composant du schématique par sa référence."""
        for i, item in enumerate(self.data):
            if isinstance(item, list) and item and item[0] == Symbol("symbol"):
                for subitem in item:
                    if (
                        isinstance(subitem, list)
                        and subitem
                        and subitem[0] == Symbol(ref)
                    ):
                        del self.data[i]
                        return True
        return False

    def add_wire(self, start: List[float], end: List[float]) -> None:
        """Ajoute un fil (connexion) entre deux points."""
        wire = [
            Symbol("wire"),
            [Symbol("pts"), [Symbol("xy"), *start], [Symbol("xy"), *end]],
        ]
        self.data.append(wire)

    def get_components(self) -> List[Dict]:
        """Retourne la liste des composants du schématique."""
        components = []
        for item in self.data:
            if isinstance(item, list) and item and item[0] == Symbol("symbol"):
                ref = str(item[1][0][0])
                value = str(item[3][1]) if len(item) > 3 else "Unknown"
                components.append({"ref": ref, "value": value})
        return components

    #    def load_symbol_library(self, lib_path: str, lib_name: str) -> None:
    #        """Charge une bibliothèque de symboles dans le schématique."""
    #       self.libraries[lib_name] = KiCadLibrary.import_symbol_library(lib_path)
    #

    def get_symbol_from_library(
        self, lib_name: str, symbol_name: str
    ) -> Optional[List]:
        """Récupère un symbole depuis une bibliothèque chargée."""
        if lib_name in self.libraries and symbol_name in self.libraries[lib_name]:
            return self.libraries[lib_name][symbol_name]
        return None


class KiCadPCB:
    """Classe pour manipuler les fichiers PCB KiCad (.kicad_pcb)."""

    def __init__(self, file_path: Optional[str] = None):
        self.data: Union[List, Dict] = []
        self.footprint_libraries: Dict[str, Dict] = {}
        if file_path:
            self.import_pcb(file_path)

    def import_pcb(self, file_path: str) -> None:
        """Importe un fichier PCB KiCad."""
        with open(file_path, "r", encoding="utf-8") as f:
            self.data = loads(f.read())

    def _format_sexp(self, data, indent=0) -> str:
        return _format_sexp_kicad(data, indent)

    def export_pcb(self, output_path: str) -> None:
        """Exporte le PCB vers un fichier, avec un formatage lisible."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self._format_sexp(self.data))

    def get_footprints(self) -> List[Dict]:
        """Retourne la liste des empreintes (footprints) du PCB."""
        footprints = []
        for item in self.data:
            if isinstance(item, list) and item and item[0] == Symbol("footprint"):
                ref = str(item[1][0])
                footprint = str(item[1][1])
                footprints.append({"ref": ref, "footprint": footprint})
        return footprints

    def load_footprint_library(self, lib_dir: str, lib_name: str) -> None:
        """Charge une bibliothèque d'empreintes dans le PCB."""
        self.footprint_libraries[lib_name] = KiCadLibrary.import_footprint_library(
            lib_dir
        )

    def get_footprint_from_library(
        self, lib_name: str, footprint_name: str
    ) -> Optional[Dict]:
        """Récupère une empreinte depuis une bibliothèque chargée."""
        if lib_name in self.footprint_libraries:
            return self.footprint_libraries[lib_name].get(footprint_name)
        return None


class KiCadAPI:
    """Classe principale pour interagir avec les fichiers KiCad."""

    def __init__(self):
        self.schematic = None
        self.pcb = None

    def _build_unique_name(self, base_name: str, occurrence: int) -> str:
        return base_name if occurrence == 1 else f"{base_name}_{occurrence}"

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

    def _get_symbol_uuid(self, symbol_node: list[Any]) -> str | None:
        for child in symbol_node:
            if (
                isinstance(child, list)
                and child
                and child[0] == Symbol("uuid")
                and len(child) > 1
                and isinstance(child[1], str)
            ):
                return child[1].strip('"')
        return None

    def _get_symbol_unit(self, symbol_node: list[Any]) -> int:
        for child in symbol_node:
            if (
                isinstance(child, list)
                and child
                and child[0] == Symbol("unit")
                and len(child) > 1
                and isinstance(child[1], (int, float))
            ):
                return int(child[1])
        return 1

    def _set_symbol_instances(
        self,
        symbol_node: list[Any],
        project_name: str,
        instance_path: str,
        reference: str,
    ) -> None:
        # Rewrite the instances block so the cloned sheet points to its new path.
        unit = self._get_symbol_unit(symbol_node)
        instances_block = [
            Symbol("instances"),
            [
                Symbol("project"),
                project_name,
                [
                    Symbol("path"),
                    instance_path,
                    [Symbol("reference"), reference],
                    [Symbol("unit"), unit],
                ],
            ],
        ]

        for i, child in enumerate(symbol_node):
            if isinstance(child, list) and child and child[0] == Symbol("instances"):
                symbol_node[i] = instances_block
                return

        symbol_node.append(instances_block)

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

    def _instantiate_subsystem(
        self,
        template: HierarchicalObject,
        project_path: Path,
        occurrence: int,
        ref_counters: dict[str, int],
    ) -> InstantiatedSubsystem:
        # Build a per-instance copy of the subsystem with unique filenames,
        # fresh UUIDs, and an annotation map we can later reuse for the PCB.
        source_sheet = Path(template.sheet_file)
        sheet_name = self._build_unique_name(template.sheet_name, occurrence)
        sheet_filename = self._build_unique_name(source_sheet.stem, occurrence) + source_sheet.suffix
        target_sheet = project_path / sheet_filename

        schematic_source = loads(source_sheet.read_text(encoding="utf-8"))
        source_symbols = [
            node for node in schematic_source
            if isinstance(node, list) and node and node[0] == Symbol("symbol")
        ]
        units_by_reference: dict[str, set[int]] = {}
        for source_node in source_symbols:
            original_ref = self._get_symbol_reference(source_node)
            if not original_ref:
                continue
            units_by_reference.setdefault(original_ref, set()).add(
                self._get_symbol_unit(source_node))
        multi_unit_refs = {
            ref for ref, units in units_by_reference.items() if len(units) > 1
        }
        schematic_data, schematic_uuid_map = self._clone_with_new_uuids(
            schematic_source)
        cloned_symbols = [
            node for node in schematic_data
            if isinstance(node, list) and node and node[0] == Symbol("symbol")
        ]

        instance_ref_map: dict[str, str] = {}
        symbol_reference_map: dict[str, str] = {}
        for source_node, cloned_node in zip(source_symbols, cloned_symbols):
            node = cloned_node
            original_ref = self._get_symbol_reference(node)
            if not original_ref:
                continue

            if original_ref in multi_unit_refs:
                new_ref = instance_ref_map.get(original_ref)
            else:
                new_ref = None

            if new_ref is None:
                new_ref = self._allocate_reference(original_ref, ref_counters)
                instance_ref_map.setdefault(original_ref, new_ref)

            # Update the schematic symbol itself and remember the UUID -> ref link
            # so the PCB can rename the matching footprint later.
            ref_property = self._get_property_node(node, "Reference")
            if ref_property is not None:
                ref_property[2] = new_ref

            source_symbol_uuid = self._get_symbol_uuid(source_node)
            if source_symbol_uuid:
                symbol_reference_map[source_symbol_uuid] = new_ref

        pcb_file = Path(template.pcb_file) if template.pcb_file is not None else None
        return InstantiatedSubsystem(
            dev_name=template.dev_name,
            sheet_name=sheet_name,
            sheet_file=target_sheet,
            pcb_file=pcb_file,
            at_xy=list(template.at_xy),
            size_wh=list(template.size_wh),
            properties=deepcopy(template.properties),
            pins=deepcopy(template.pins),
            schematic_data=schematic_data,
            reference_map=instance_ref_map,
            schematic_uuid_map=schematic_uuid_map,
            symbol_reference_map=symbol_reference_map,
        )

    def _instantiate_subsystems(
        self,
        project_path: Path,
        templates: list[HierarchicalObject],
    ) -> list[InstantiatedSubsystem]:
        # Repeated templates become independent instances with stable numbering.
        ref_counters: dict[str, int] = {}
        occurrences: dict[str, int] = {}
        instances = []

        for template in templates:
            key = str(Path(template.sheet_file))
            occurrences[key] = occurrences.get(key, 0) + 1
            instances.append(
                self._instantiate_subsystem(
                    template=template,
                    project_path=project_path,
                    occurrence=occurrences[key],
                    ref_counters=ref_counters,
                )
            )

        return instances

    def _write_instantiated_schematic(
        self,
        instance: InstantiatedSubsystem,
        project_name: str,
        root_uuid: str,
        sheet_uuid: str,
    ) -> None:
        # Persist the cloned child schematic after patching its instance path.
        instance_path = f"/{root_uuid}/{sheet_uuid}"
        schematic_data = deepcopy(instance.schematic_data)

        for node in schematic_data:
            if not (isinstance(node, list) and node and node[0] == Symbol("symbol")):
                continue

            reference = self._get_symbol_reference(node)
            if not reference:
                continue

            self._set_symbol_instances(
                symbol_node=node,
                project_name=project_name,
                instance_path=instance_path,
                reference=reference,
            )

        with open(instance.sheet_file, "w", encoding="utf-8") as schematic_file:
            schematic_file.write(_format_sexp_kicad(schematic_data))

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

    def _remap_net_name(
        self,
        net_name: str,
        instance: InstantiatedSubsystem,
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

    def _prepare_instance_pcb(
        self,
        instance: InstantiatedSubsystem,
        sheet_uuid: str,
    ) -> Sexp:
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

    def _next_project_net_id(self, pcb_data: list[Any]) -> int:
        # Imported PCB chunks reuse net IDs, so each append needs a new range.
        max_net_id = 0
        for item in pcb_data:
            if (
                isinstance(item, list)
                and item
                and item[0] == Symbol("net")
                and len(item) > 1
                and isinstance(item[1], int)
            ):
                max_net_id = max(max_net_id, int(item[1]))
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

    def add_multiple_designs(self, project_path, design_instances: List[dict[str, Any]], space_x=9.5, space_y=5.5, max_x=285, max_y=198, cursor_x0=25, cursor_y0=25):
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
            instance = placed["object"]
            if instance.pcb_file is None:
                continue

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

    def add_pcb(
        self,
        project_path: Path,
        pcb_data: Sexp,
    ) -> None:
        # Merge a prepared PCB fragment into the project while normalizing net IDs.
        project_pcb_path = project_path / f"{project_path.name}.kicad_pcb"
        project_pcb_data = loads(project_pcb_path.read_text(encoding="utf-8"))

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

        project_pcb_data += useful_pcb_data

        with open(project_pcb_path, "w", encoding="utf-8") as pcb_file:
            pcb_file.write(_format_sexp_kicad(project_pcb_data))

    def project_creation(
        self,
        project_name: str,
        template_list: list[HierarchicalObject],
    ) -> KiCadSchematic:
        # Project setup
        project_builder(project_name)

        project_path = PROJECT_FOLDER / project_name

        # dependencies
        copy(PROJECT_FOLDER/'src'/'lib-table_templates' /
             'fp-lib-table', project_path / 'fp-lib-table')
        copy(PROJECT_FOLDER/'src'/'lib-table_templates' /
             'sym-lib-table', project_path / 'sym-lib-table')
        self.schematic = KiCadSchematic(
            f'{PROJECT_FOLDER}/{project_name}/{project_name}.kicad_sch')

        # Instantiate every requested template first so schematic and PCB
        # generation share the same annotation and UUID mapping.
        instantiated_templates = self._instantiate_subsystems(
            project_path, template_list)

        placed_instances = self.schematic.add_hierarchical_sheets(
            project_path,
            instantiated_templates,
            origin_xy=(33, 20),
            max_row_width_mm=200,   # controla quantos cabem por linha
            h_gap_factor=0.8,       # gap horizontal proporcional ao tamanho
            v_gap_factor=1.0,       # gap vertical proporcional à altura
            page_for_instance_start=10   # evita conflito com páginas anteriores
        )

        for placed in placed_instances:
            self._write_instantiated_schematic(
                instance=placed["object"],
                project_name=project_name,
                root_uuid=placed["root_uuid"],
                sheet_uuid=placed["sheet_uuid"],
            )

        pcb_instances = [
            placed for placed in placed_instances
            if placed["object"].pcb_file is not None
        ]
        if pcb_instances:
            self.add_multiple_designs(project_path, pcb_instances)

        self.schematic.export_schematic(
            f'{PROJECT_FOLDER}/{project_name}/{project_name}.kicad_sch')

        return self.schematic

    def load_schematic(self, file_path: str) -> KiCadSchematic:
        """Charge un fichier schématique."""
        self.schematic = KiCadSchematic(file_path)
        return self.schematic

    def load_pcb(self, file_path: str) -> KiCadPCB:
        """Charge un fichier PCB."""
        self.pcb = KiCadPCB(file_path)
        return self.pcb

    def create_schematic(self) -> KiCadSchematic:
        """Crée un nouveau schématique vide."""
        self.schematic = KiCadSchematic()
        return self.schematic

    def create_pcb(self) -> KiCadPCB:
        """Crée un nouveau PCB vide."""
        self.pcb = KiCadPCB()
        return self.pcb
