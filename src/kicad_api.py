from sexpdata import loads, dumps, Symbol
from typing import Dict, List, Optional, Union
import os
import glob
import uuid

from hierarchical_object import HierarchicalObject  # Ajoute cette ligne


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
                out += "\n" + (TAB * (indent + 1)) + _format_sexp_kicad(x, indent + 1)
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
        object,                          # attrs: sheet_name, sheet_file, at_xy, size_wh, properties, pins
        page_for_instance: str = "2",
        pin_margin_mm: float = 2.0,      # margem topo/base para distribuição
        min_delta_mm: float = 1.0,       # espaçamento mínimo entre pinos do mesmo lado
        net_wire_len_mm: float = 5.0,    # comprimento do “rabicho” de fio até o net label
    ):
        at_x, at_y = float(object.at_xy[0]), float(object.at_xy[1])   # (at X Y) — sem rotação
        w, h       = float(object.size_wh[0]), float(object.size_wh[1])
        x_left     = at_x
        x_right    = at_x + w
        y_top      = at_y
        y_bot      = at_y + h

        props = object.properties or {}
        pins  = object.pins or []

        # ---- Agrupa por lado (inclui bidirectional) ----
        left_pins, right_pins = [], []
        for p in pins:
            t = p.get("type", "input")
            if t in ("input", "power_in"):
                left_pins.append(p)
            elif t in ("output", "power_out"):
                right_pins.append(p)
            else:
                (left_pins if p.get("side", "right") == "left" else right_pins).append(p)

        # ---- Helpers de distribuição centralizada ----
        def _spread_ys(n: int) -> list:
            """
            Distribui pinos centralizados:
            - Divide a faixa útil em 'n' bins iguais
            - Coloca cada pino no CENTRO de seu bin
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
            """Mistura Y explícito com Y automático centralizado + des-overlap e clamp."""
            autos = _spread_ys(sum(1 for p in group if "y" not in p))
            auto_it = iter(autos)
            ys = []
            for p in group:
                ys.append(float(p["y"]) if "y" in p else next(auto_it))

            low  = y_top + pin_margin_mm
            high = y_bot - pin_margin_mm
            if not ys:
                return ys
            ys[0] = min(max(ys[0], low), high)
            for i in range(1, len(ys)):
                target = max(ys[i], ys[i-1] + min_delta_mm)
                ys[i] = min(target, high)

            # Se acumulou no topo, recentra dentro do range possível
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

        ys_left  = _resolve_y_for_group(left_pins)
        ys_right = _resolve_y_for_group(right_pins)

        # ---- Monta o bloco (sheet ...) ----
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
            [Symbol("property"), '"Sheet file"', f'"{object.sheet_file}"',
                [Symbol("id"), 1],
                [Symbol("at"), at_x + 2.0, at_y + 2.0, 0],
                [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol("left")],
                ],
            ],
        ]

        # Propriedades extras
        prop_id = 2
        for k, v in (props.items()):
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

        # ---- Pinos esquerda (ângulo 180) ----
        left_pin_positions = []  # [(pin_dict, (x,y))]
        for p, y in zip(left_pins, ys_left):
            name  = p.get("name", "IN")
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

        # ---- Pinos direita (ângulo 0) ----
        right_pin_positions = []
        for p, y in zip(right_pins, ys_right):
            name  = p.get("name", "OUT")
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
        if insert_idx < 0: insert_idx = 0
        self.data.insert(insert_idx, sheet)

        # ---- sheet_instances ----
        root_uuid = self._ensure_root_uuid()
        si = self._ensure_section("sheet_instances")
        has_root = any(
            isinstance(e, list) and e and e[0] == Symbol("path") and str(e[1]) == '"/"'
            for e in si[1:]
        )
        if not has_root:
            si.append([Symbol("path"), '"/"', [Symbol("page"), '"1"']])
        si.append([Symbol("path"), f'"/{sheet_uuid}"', [Symbol("page"), f'"{page_for_instance}"']])

        # =====================================================================
        #   NET LABELS (opcionais): cria fios e labels para pinos com p["net"]
        # =====================================================================
        def _add_wire(x1, y1, x2, y2):
            self.data.append(
                [Symbol("wire"),
                [Symbol("pts"), [Symbol("xy"), x1, y1], [Symbol("xy"), x2, y2]],
                [Symbol("stroke"), [Symbol("width"), 0], [Symbol("type"), Symbol("default")]],
                [Symbol("uuid"), f'"{uuid.uuid4()}"']]
            )

        def _add_label(name, x, y, justify_sym):
            # KiCad 9: justify deve estar dentro de (effects ...)
            self.data.append(
                [Symbol("label"), f'"{name}"',
                [Symbol("at"), x, y, 0],
                [Symbol("effects"),
                    [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                    [Symbol("justify"), Symbol(justify_sym)]
                ],
                [Symbol("uuid"), f'"{uuid.uuid4()}"']]
            )
        

        # Esquerda: fio vai para x_left - net_wire_len_mm, label no fim com justify right
        for p, (px, py) in left_pin_positions:
            net = p.get("net")
            if not net:
                continue
            x2 = px - float(net_wire_len_mm)
            y2 = py
            _add_wire(px, py, x2, y2)
            _add_label(str(net), x2, y2, "right")

        # Direita: fio vai para x_right + net_wire_len_mm, label no fim com justify left
        for p, (px, py) in right_pin_positions:
            net = p.get("net")
            if not net:
                continue
            x2 = px + float(net_wire_len_mm)
            y2 = py
            _add_wire(px, py, x2, y2)
            _add_label(str(net), x2, y2, "left")

        return {"sheet_uuid": sheet_uuid}

    def add_hierarchical_sheets(
        self,
        objects,                          # lista de HierarchicalObject (ou objs compatíveis)
        origin_xy=(50.0, 50.0),           # canto superior-esquerdo inicial (mm)
        flow="row",                       # por enquanto: "row" (quebra por largura)
        max_row_width_mm=180.0,           # largura máxima da “linha” (mm) antes de quebrar
        h_gap_factor=0.5,                 # gap horizontal = max(h_gap_factor * w_obj, min_hgap)
        v_gap_factor=0.8,                 # gap vertical   = max(v_gap_factor * h_row, min_vgap)
        min_hgap=4.0,                     # gaps mínimos (mm) para legibilidade
        min_vgap=6.0,
        page_for_instance_start=2,        # numeração de páginas para sheet_instances
        pin_margin_mm=2.0,                # repassa para add_hierarchical_sheet
        min_delta_mm=1.0,                 # repassa para add_hierarchical_sheet
    ):
        """
        Adiciona vários hierarchical sheets e os distribui em linhas, com espaçamento
        proporcional ao tamanho. Calcula e injeta at_xy automaticamente.
        Retorna a lista de metadados [{object, sheet_uuid, at_xy, size_wh, page}, ...].
        """
        placed = []
        cursor_x, cursor_y = float(origin_xy[0]), float(origin_xy[1])
        row_height = 0.0
        row_left_edge = cursor_x
        page_num = int(page_for_instance_start)

        def _hgap(w):  # gap proporcional à largura do bloco
            #return max(h_gap_factor * float(w), float(min_hgap))
            return 25

        def _vgap(h):  # gap proporcional à maior altura da linha
            #return max(v_gap_factor * float(h), float(min_vgap))
            return 10
        for obj in objects:
            w = float(obj.size_wh[0])
            h = float(obj.size_wh[1])

            # quebra de linha se exceder a largura máxima
            if flow == "row" and (cursor_x > row_left_edge) and (cursor_x + w > row_left_edge + float(max_row_width_mm)):
                # próxima linha
                cursor_x = row_left_edge
                cursor_y = cursor_y + row_height + _vgap(row_height)
                row_height = 0.0

            # posiciona este bloco
            obj.at_xy = [cursor_x, cursor_y]
            meta = self.add_hierarchical_sheet(
                object=obj,
                page_for_instance=str(page_num),
                pin_margin_mm=pin_margin_mm,
                min_delta_mm=min_delta_mm
            )
            placed.append({
                "object": obj,
                "sheet_uuid": meta.get("sheet_uuid"),
                "at_xy": tuple(obj.at_xy),
                "size_wh": tuple(obj.size_wh),
                "page": page_num
            })

            # avança cursor na linha
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
                print(f"➕ Ajout du symbole '{lib_name}' dans la section (lib_symbols)")
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
                            [Symbol("at"), float(at[0]) + 2.54, float(at[1]) - 1.27, 0],
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
                            [Symbol("at"), float(at[0]) + 2.54, float(at[1]) + 1.27, 0],
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
                            [Symbol("at"), float(at[0]) - 1.778, float(at[1]), 90],
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
            str(lib_symbol[1]) if isinstance(lib_symbol[1], Symbol) else lib_symbol[1]
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

