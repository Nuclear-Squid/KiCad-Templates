from os import mkdir
from pathlib import Path
from shutil import copy
from uuid import uuid4

from schematic_api.kicad_api import KiCadSchematic
from schematic_api.hierarchical_object import HierarchicalObject  # Ajoute cette ligne

PROJECT_FOLDER = Path(__file__).parent.parent.parent


base_pcb_text = '''(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")
)'''

base_sch_text = f'''(kicad_sch
	(version 20250114)
	(generator "eeschema")
	(generator_version "9.0")
	(uuid {uuid4()})
	(paper "A4")
	(lib_symbols)
	(sheet_instances
		(path "/"
			(page "1")
		)
	)
	(embedded_fonts no)
)'''

base_pro_text = '''{
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
'''

fp_lib_table_text = '''
(fp_lib_table
 (lib(name "User")
  (type "KiCad")
  (uri "${KIPRJMOD}/../subsystems/mikrobus/mikrobus.pretty")
  (options "")
  (descr "Mikrobus Footprints"))
 )
'''

sym_lib_table_text = '''
(sym_lib_table
 (lib(name "Microbus")
  (type "KiCad")
  (uri "${KIPRJMOD}/../subsystems/mikrobus/MIKROE-4247.kicad_sym")
  (options "")
  (descr "Biblioteca de simbolos do usuario"))
 )
'''


def create_project(
    project_name: str,
    template_list: list[HierarchicalObject],
) -> KiCadSchematic:
    # creates a new project folder with the necessary files for KiCad
    project_path = PROJECT_FOLDER / project_name
    mkdir(project_path)

    def write_file(file_name, contents):
        with open(project_path / file_name, "x") as f:
            f.write(contents)

    write_file(f"{project_name}.kicad_pro", base_pro_text)
    write_file(f"{project_name}.kicad_sch", base_sch_text)
    write_file(f"{project_name}.kicad_pcb", base_pcb_text)
    write_file("fp-lib-table", fp_lib_table_text)
    write_file("sym-lib-table", sym_lib_table_text)

    schematic = KiCadSchematic(f'{PROJECT_FOLDER}/{project_name}/{project_name}.kicad_sch')

    schematic.add_hierarchical_sheets(
        project_path,
        template_list,
        origin_xy=(33, 20),
        max_row_width_mm=200,   # controla quantos cabem por linha
        h_gap_factor=0.8,       # gap horizontal proporcional ao tamanho
        v_gap_factor=1.0,       # gap vertical proporcional à altura
        page_for_instance_start=10   # evita conflito com páginas anteriores
    )

    schematic.export_schematic(f'{PROJECT_FOLDER}/{project_name}/{project_name}.kicad_sch')

    print(f"Project '{project_name}' created successfully")

    return schematic
