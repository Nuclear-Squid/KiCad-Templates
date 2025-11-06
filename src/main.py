#!/usr/bin/env python3

import sys

from parser import LispCST


def main() -> None:
    if len(sys.argv) != 2:
        print("Please provide a single file to parse.")
        return

    file_path = sys.argv[1]
    with open(file_path, "r") as file:
        file_contents = file.read()
        file.close()

        lisp = LispCST.parse(file_contents)
        print(lisp)


if __name__ == "__main__":
    main()
