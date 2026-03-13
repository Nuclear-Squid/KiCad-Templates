from copy import deepcopy
from os.path import basename
from pathlib import Path

import click
import sexpdata

from kicad_sexp import KiCadSexpNode
from templates import Template
from project import KiCadProject
from schematic import KiCadSchematic

def error(msg):
    click.echo(click.style("Error: ", fg="red") + msg)

# Define a group for all of our CLI commands
@click.group()
def cli():
    pass


# List available templates
@cli.command()
def list():
    print(
        "Available templates are:",
        *Template.list_templates(KiCadProject.template_folders),
        sep="\n  - "
    )


# Create new project with specified templates
@cli.command()
@click.argument("project_path", type=Path)
@click.argument("template_names", nargs=-1)
def new(project_path: Path, template_names: tuple[str, ...]):
    # # TODO: limit project name to valid characters and length for KiCad
    project_name = basename(project_path)
    for character in project_name:
        if not character.isalnum() and character not in ('-', '_'):
            error("le nom du projet ne doit contenir que des lettres, chiffres, tirets ou underscores.")
            return

    templates = Template.get_templates(template_names, KiCadProject.template_folders)

    project = KiCadProject(project_path)
    project.schematic.add_hierarchical_sheets(templates)
    project.write_to_disk()

    print(f"Successfully created project '{project_name}'")


if __name__ == "__main__":
    cli()
