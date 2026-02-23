from kicad_api import KiCadAPI, KiCadLibrary
from hierarchical_object import HierarchicalObject
from templates import SCH_Templates
from project_builder import project_builder

# Initialiser l'API
api = KiCadAPI()
lib = KiCadLibrary()


schematic = api.project_creation()
