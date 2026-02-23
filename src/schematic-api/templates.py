from pathlib import Path

from hierarchical_object import HierarchicalObject

def load_templates(templates_folder: Path) -> list[HierarchicalObject]:
    result = []
    for path in templates_folder.iterdir():
        template = HierarchicalObject.load_from_yaml(path / "meta.yaml")
        if template is None:
            print(f"Warning: could not load template '{template}'")
            continue

        result.append(template)
    return result


def find_template(name: str, templates: list[HierarchicalObject]) -> HierarchicalObject | None:
    for t in templates:
        if t.dev_name == name:
            return t
    return None
