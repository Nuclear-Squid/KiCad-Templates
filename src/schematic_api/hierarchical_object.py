import os
from pathlib import Path
from textwrap import dedent
from typing import Self

import yaml


class HierarchicalObject:
    def __init__(
        self,
        dev_name: str,
        sheet_name: str,
        sheet_file: str,
        pcb_file: str | None,
        at_xy,
        size_wh,
        properties=None,
        pins=None,
    ):
        self.dev_name = dev_name
        self.sheet_name = sheet_name
        self.sheet_file = sheet_file
        self.pcb_file = pcb_file
        self.at_xy = at_xy
        self.size_wh = size_wh
        self.properties = properties
        self.pins = pins

    def __str__(self):
        return dedent(f"""
            Hierarchical sheet "{self.sheet_name}" ({self.dev_name})
              - path = {self.sheet_file} | {self.pcb_file}
              - position = {self.at_xy}
              - size = {self.size_wh}
              - properties = {self.properties}
              - pins = {self.pins}
        """)

    @classmethod
    def load_from_yaml(cls, path_to_yaml_metadata: Path) -> Self | None:
        with open(path_to_yaml_metadata, "r") as yaml_metadata:
            meta = yaml.safe_load(yaml_metadata)

            pcb_file = meta.get('pcb_file', None)
            if pcb_file is not None:
                pcb_file = path_to_yaml_metadata.parent / pcb_file

            return cls(
                dev_name=os.path.basename(path_to_yaml_metadata.parent),
                sheet_name=meta["sheet_name"],
                sheet_file=path_to_yaml_metadata.parent / meta["sheet_file"],
                pcb_file=pcb_file,
                at_xy=meta["at_xy"],
                size_wh=meta["size_wh"],
                properties=meta["properties"],
                pins=meta["pins"],
            )
        return None
