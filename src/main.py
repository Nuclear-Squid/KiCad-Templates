import os
from pathlib import Path

import click

from kicad_api import KiCadAPI, KiCadLibrary
from hierarchical_object import HierarchicalObject
from templates import SCH_Templates

PROJECT_FOLDER = Path(__file__).parent.parent
SUBSYSTEM_FOLDER = PROJECT_FOLDER / 'subsystems'

DEVICE_LIB_PATH = "/usr/share/kicad/symbols/Device.kicad_sym"  # Change it somehow

# Define a group for all of our CLI commands
@click.group()
def cli():
    pass


# List available templates
@cli.command()
def list():
    for path in SUBSYSTEM_FOLDER.iterdir():
        template_name = os.path.basename(path)
        click.echo(template_name)


# Create new project with specified templates
@cli.command()
@click.argument('project_name')
@click.argument('templates', nargs=-1)
def new(project_name: str, templates: tuple[str, ...]):
    api = KiCadAPI()
    lib = KiCadLibrary()

    blocks = []
    for t in templates:
        sheet = SCH_Templates.find_sheet_folder(t)
        if sheet is None:
            click.echo(f"Warning: could not find template '{t}'.")
        else:
            blocks.append(sheet)

    # Charger un schématique
    schematic = api.load_schematic("test_python.kicad_sch")

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


if __name__ == "__main__":
    cli()
