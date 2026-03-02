from os import mkdir
from pathlib import Path
from shutil import copy
from uuid import uuid4

from schematic_api.kicad_api import KiCadSchematic
from schematic_api.hierarchical_object import HierarchicalObject  # Ajoute cette ligne

PROJECT_FOLDER = Path(__file__).parent.parent.parent


base_pcb_text = ''' (kicad_pcb
	(version 20241229)
	(generator "pcbnew")
	(generator_version "9.0")
	(paper "A4")
	(layers
		(0 "F.Cu" signal)
		(2 "B.Cu" signal)
		(9 "F.Adhes" user "F.Adhesive")
		(11 "B.Adhes" user "B.Adhesive")
		(13 "F.Paste" user)
		(15 "B.Paste" user)
		(5 "F.SilkS" user "F.Silkscreen")
		(7 "B.SilkS" user "B.Silkscreen")
		(1 "F.Mask" user)
		(3 "B.Mask" user)
		(17 "Dwgs.User" user "User.Drawings")
		(19 "Cmts.User" user "User.Comments")
		(21 "Eco1.User" user "User.Eco1")
		(23 "Eco2.User" user "User.Eco2")
		(25 "Edge.Cuts" user)
		(27 "Margin" user)
		(31 "F.CrtYd" user "F.Courtyard")
		(29 "B.CrtYd" user "B.Courtyard")
		(35 "F.Fab" user)
		(33 "B.Fab" user)
		(39 "User.1" user)
		(41 "User.2" user)
		(43 "User.3" user)
		(45 "User.4" user)
	)
	(setup
		(pad_to_mask_clearance 0)
		(allow_soldermask_bridges_in_footprints no)
		(tenting front back)
		(pcbplotparams
			(layerselection 0x00000000_00000000_55555555_5755f5ff)
			(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
			(disableapertmacros no)
			(usegerberextensions no)
			(usegerberattributes yes)
			(usegerberadvancedattributes yes)
			(creategerberjobfile yes)
			(dashed_line_dash_ratio 12.000000)
			(dashed_line_gap_ratio 3.000000)
			(svgprecision 4)
			(plotframeref no)
			(mode 1)
			(useauxorigin no)
			(hpglpennumber 1)
			(hpglpenspeed 20)
			(hpglpendiameter 15.000000)
			(pdf_front_fp_property_popups yes)
			(pdf_back_fp_property_popups yes)
			(pdf_metadata yes)
			(pdf_single_document no)
			(dxfpolygonmode yes)
			(dxfimperialunits yes)
			(dxfusepcbnewfont yes)
			(psnegative no)
			(psa4output no)
			(plot_black_and_white yes)
			(sketchpadsonfab no)
			(plotpadnumbers no)
			(hidednponfab no)
			(sketchdnponfab yes)
			(crossoutdnponfab yes)
			(subtractmaskfromsilk no)
			(outputformat 1)
			(mirror no)
			(drillshape 1)
			(scaleselection 1)
			(outputdirectory "")
		)
	)
	(embedded_fonts no)
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
