from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"
    VOID = "void"


# Represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None):
        self.t = type
        #self.v = value
        self.v = value if value is not None else self.default_value(type)

    def value(self):
        return self.v

    def type(self):
        return self.t
    # if a function has a non-void return type but does not explicitly return a value,
    #  it should return a default value based on the return type
    def default_value(self, type):
        if type == Type.INT:
            return 0
        elif type == Type.BOOL:
            return False
        elif type == Type.STRING:
            return ""
        elif type == Type.VOID:
            return None
        
        return None


def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    else:
        raise ValueError("Unknown value type")


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None
