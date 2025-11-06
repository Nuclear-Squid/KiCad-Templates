from typing import Self


def find_closing_bracket(input: str, openning_bracket: int) -> int | None:
    """Given an input string and the index of an oppening bracket, this
    function returns the index of the matching closing bracket, which is
    considered to be the first closing bracket at the same recursion level.
    (Returns `None` if the index given is not of a `(`, or if no matching
    bracket was found)
    """
    if input[openning_bracket] != "(":
        return None

    nested_brackets = 0
    for i, c in enumerate(input[openning_bracket + 1 :]):
        if c == "(":
            nested_brackets += 1
        if c == ")":
            if nested_brackets == 0:
                return openning_bracket + 1 + i
            else:
                nested_brackets -= 1

    return None


class LispCST:
    """This recursive class serves as a Concrete Syntax Tree representation of
    a Lisp code / description. In practice, this serves as an intermediate
    representation of the KiCad file format.
    """

    attributes: list[str]
    children: list[Self]

    def __init__(self, attributes, children):
        self.attributes = attributes
        self.children = children

    def __str__(self):
        return self.to_str()

    def to_str(self, indent_level=0):
        """Serialize the LispCST into a human-readable, indented string"""
        indent = "\t" * indent_level
        start = indent + "("
        for x in self.attributes:
            start += x + " "

        start = start[:-1]  # Remove trailing space

        if self.children == []:
            return start + ")"

        start += "\n"
        end = "\n" + indent + ")"
        middle = map(lambda x: x.to_str(indent_level + 1), self.children)

        return start + "\n".join(middle) + end

    @classmethod
    def parse(cls, input: str) -> Self | None:
        """Parse the contents of a Kicad file into a LispCST"""

        input = input.strip()
        end_of_expression = find_closing_bracket(input, 0)
        if end_of_expression is None:
            return None

        sub_expressions_bounds = []
        current_index = 1
        while True:
            start = input.find("(", current_index, end_of_expression)
            if start == -1:
                break

            end = find_closing_bracket(input, start)
            if end is None:
                return None

            sub_expressions_bounds.append((start, end + 1))
            current_index = end + 1

        if sub_expressions_bounds == []:
            attributes = input[1:-1].split()
            children = []
            return cls(attributes, children)

        else:
            attributes = input[1 : sub_expressions_bounds[0][0]].split()
            children = [
                cls.parse(input[start:end]) for (start, end) in sub_expressions_bounds
            ]
            start, end = sub_expressions_bounds[0]
            return cls(attributes, children)
