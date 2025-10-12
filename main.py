def test(x: string) -> float:
    return "string: " + x

def main():
    print(   "Hello from kicad-templates!")
    print(test('test to make sure the CI works well'))


if __name__ == "__main__":
    main()
