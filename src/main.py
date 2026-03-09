import os
from pathlib import Path

import click
import sexpdata

from kicad_sexp import KiCadSexpNode
import schematic_api.templates as templates
from schematic_api.project import KiCadProject
from schematic_api.schematic import KiCadSchematic

PROJECT_FOLDER = Path(__file__).parent.parent
SUBSYSTEM_FOLDER = PROJECT_FOLDER / "subsystems"

DEVICE_LIB_PATH = "/usr/share/kicad/symbols/Device.kicad_sym"  # Change it somehow


def error(msg):
    click.echo(click.style("Error: ", fg="red") + msg)

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
    subsystems = templates.load_templates(SUBSYSTEM_FOLDER)

    # TODO: limit project name to valid characters and length for KiCad
    for character in project_name:
        if not character.isalnum() and character not in ('-', '_'):
            error("le nom du projet ne doit contenir que des lettres, chiffres, tirets ou underscores.")
            return

    blocks = []
    for name in template_names:
        t = templates.find_template(name, subsystems)
        if t is None:
            error(f"Could not find template '{name}'")
            return
        blocks.append(t)

    # print(blocks)

    # create_project(project_name, blocks)
    # KiCadProject(project_name).write_to_disk()
    # project = KiCadProject(project_name)
    # project.write_to_disk()


@cli.command()
def quick_test():
    data = KiCadSexpNode.read_from_file(SUBSYSTEM_FOLDER / 'can_buffer' / 'can_buffer.kicad_sch')
    sheet = KiCadSchematic("can_buffer", data, [])

    subsystems = templates.load_templates(SUBSYSTEM_FOLDER)
    can_buffer_meta = templates.find_template('can_buffer', subsystems)
    can_buffer_template = templates.Template.from_metadata(can_buffer_meta)

    project = KiCadProject(PROJECT_FOLDER / 'test')
    project.schematic.add_hierarchical_sheet(can_buffer_template)
    project.write_to_disk()

if __name__ == "__main__":
    cli()
