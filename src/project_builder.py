from os import mkdir
from uuid import uuid4
from pathlib import Path

PROJECT_FOLDER = Path(__file__).parent.parent


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


def project_builder(project_name):
    mkdir(PROJECT_FOLDER / project_name)

    f_proj = open(PROJECT_FOLDER / project_name / f"{project_name}.kicad_pro", "x")
    f_proj.write(f'''{base_pro_text}''')

    f_proj = open(PROJECT_FOLDER / project_name / f"{project_name}.kicad_sch", "x")
    f_proj.write(f'''{base_sch_text}''')

    f_proj = open(PROJECT_FOLDER / project_name / f"{project_name}.kicad_pcb", "x")
    f_proj.write(f'''{base_pcb_text}''')
