import os
from pathlib import Path

import click

from kicad_api import KiCadAPI, KiCadLibrary
import templates

PROJECT_FOLDER = Path(__file__).parent.parent
SUBSYSTEM_FOLDER = PROJECT_FOLDER / "subsystems"

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
@click.argument("project_name")
@click.argument("template_names", nargs=-1)
def new(project_name: str, template_names: tuple[str, ...]):
    api = KiCadAPI()
    lib = KiCadLibrary()

    subsystems = templates.load_templates(SUBSYSTEM_FOLDER)

    blocks = []
    for name in template_names:
        t = templates.find_template(name, subsystems)
        if t is None:
            click.echo(
                click.style("Error: ", fg="red") + f"Could not find template '{name}'"
            )
            return
        blocks.append(t)

    # Charger un schématique
    schematic = api.load_schematic("test_python.kicad_sch")

    # Block placement
    placed = schematic.add_hierarchical_sheets(
        blocks,
        origin_xy=(33, 20),
        max_row_width_mm=200,  # controla quantos cabem por linha
        h_gap_factor=0.8,  # gap horizontal proporcional ao tamanho
        v_gap_factor=1.0,  # gap vertical proporcional à altura
        page_for_instance_start=10,  # evita conflito com páginas anteriores
    )

    print("SHEETS PLACED:")
    for p in placed:
        print(p)

    schematic.export_schematic("test_python.kicad_sch")

    print("File generated: test_python.kicad_sch")


if __name__ == "__main__":
    cli()
