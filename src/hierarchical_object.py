class HierarchicalObject:
    def __init__(self, sheet_name: str, sheet_file:str, at_xy, size_wh, properties = None, pins = None):
        self.sheet_name = sheet_name
        self.sheet_file = sheet_file
        self.at_xy = at_xy
        self.size_wh = size_wh
        self.properties = properties
        self.pins = pins

