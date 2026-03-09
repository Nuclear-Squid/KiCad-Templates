from collections.abc import Iterator
from dataclasses import dataclass
import itertools
import os
from pathlib import Path
import re
from typing import Self

import sexpdata

@dataclass
class KiCadSexpNode:
    name: str
    attributes: list[str | int]
    children: list[Self]

    def to_str(self, indent_level=0):
        def format_attribute(attr):
            if isinstance(attr, str):
                attr = attr.replace('"', '\\"').replace("\n", "\\n")
                if not re.compile('^[a-z_]+$').match(attr):
                    attr = f'"{attr}"'
            return f' {attr}'

        attributes = ''.join(map(format_attribute, self.attributes))
        children = ''.join(map(lambda x: f'\n{x.to_str(indent_level + 1)}', self.children))

        return f"{"  " * indent_level}({self.name}{attributes}{children})"

    def __str__(self):
        return self.to_str(indent_level=0)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def from_sexpdata(cls, input) -> Self:
        if isinstance(input, sexpdata.Symbol):
            return cls(str(input), [], [])
        elif isinstance(input, list):
            name = str(input.pop(0))
            attributes = list(filter(lambda x: not isinstance(x, list), input))
            children_inputs = filter(lambda x: isinstance(x, list), input)
            children = list(map(cls.from_sexpdata, children_inputs))
            return cls(name, attributes, children)
        else:
            raise TypeError(f"Unexpected type '{type(input)}' when initialising LispCST.")

    @classmethod
    def read_from_file(cls, file_path: Path) -> Self:
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.from_sexpdata(sexpdata.load(f))

    def write_to_file(self, file_path: Path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(self))


    def iter_children_with_name(
        self,
        symbol_name: str,
        max_depth: int = 2 ** 16
    ) -> Iterator[Self]:
        flatmap = lambda f, x: list(itertools.chain.from_iterable(map(f, x)))
        items_to_check = self.children
        while max_depth > 0 and len(items_to_check) > 0:
            for item in items_to_check:
                if item.name == symbol_name:
                    yield item

            max_depth -= 1
            items_to_check = flatmap(lambda x: x.children, items_to_check)


    def get_child(self, symbol_name: str, max_depth: int = 2 ** 16) -> Self | None:
        return next(self.iter_children_with_name(symbol_name, max_depth))
