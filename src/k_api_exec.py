from kicad_api import KiCadAPI, KiCadLibrary
from hierarchical_object import HierarchicalObject
from templates import SCH_Templates

# Initialiser l'API
api = KiCadAPI()
lib = KiCadLibrary()

# Charger un schématique
schematic = api.load_schematic("test_python.kicad_sch")


device_lib_path = "/usr/share/kicad/symbols/Device.kicad_sym"  # Change it somehow

# Protoseed implementation
blocks = [SCH_Templates.CAN_BUFFER, SCH_Templates.CAPT_TEMP, SCH_Templates.BME680, SCH_Templates.ACC_MAG, SCH_Templates.MIKROBUS,]

# Block placement
placed = schematic.add_hierarchical_sheets(
    blocks,
    origin_xy = (33, 20),
    max_row_width_mm = 200,   # controla quantos cabem por linha
    h_gap_factor = 0.8,       # gap horizontal proporcional ao tamanho
    v_gap_factor = 1.0,       # gap vertical proporcional à altura
    page_for_instance_start = 10   # evita conflito com páginas anteriores
)

print("SHEETS PLACED:")
for p in placed:
    print(p)


schematic.export_schematic("test_python.kicad_sch")

print("File generated: test_python.kicad_sch")