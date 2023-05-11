class String:
    '''
    Simple String type
    '''
    def __init__(self, value):
        self.value = value
        self.length = len(value)

class ID:
    '''
    Simple ID type
    '''
    def __init__(self, value):
        self.value = value
        self.length = len(value)

class Char:
    '''
    Simple Char type
    '''
    size = 1
    abbr_name = 'char'
    def __init__(self, value):
        self.value = ord(value) if type(value) == str else value
        self.length = value
        self.size = Char.size
        self.hex  = False

class Int8:
    '''
    Simple Int8 type
    '''
    size = 1
    abbr_name = 'int8'
    def __init__(self, value):
        self.value = int(value)
        self.length = value
        self.size = Int8.size
        self.hex = False

class Int32:
    '''
    Simple Int32 type
    '''
    size = 4
    abbr_name = 'int'
    def __init__(self, value):
        self.value = int(value, 16) if (type(value) == str and value[0:2] == "0x") else int(value)
        self.length = value
        self.size = Int32.size
        self.hex = False

class Pointer:
    '''
    Simple pointer type
    '''
    size = 4
    abbr_name = 'ptr'
    def __init__(self, value):
        ID.__init__(self, value)

class HexInt32:
    '''
    Simple Int32 type
    '''
    size = 4
    abbr_name = 'hex'
    def __init__(self, value):
        self.value = value
        self.length = len(value)
        self.size = Int32.size
        self.hex = True

class List:
    '''
    Simple static length list type
    '''
    size = 0
    abbr_name = 'list'
    def __init__(self, values, type):
        self.values = values
        self.length = len(values)
        self.size = List.size
        self.offset = 0
        self.type = type