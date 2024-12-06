from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"

class LazyValue:
    def __init__(self, expr_func):
        self.expr_func = expr_func  # A closure that represents the expression
        self.cached_value = None   # Cache for the evaluated value
        self.evaluating = False 
        
        self.evaluated = False     # Flag to track if it has been evaluated
    def value(self):
       
        if self.evaluated:
            # print(f"DEBUG: Returning cached value: {self.cached_value}")
            return self.cached_value
        
        if self.evaluating:
            raise RuntimeError("Circular dependency detected during LazyValue evaluation")
        # print("DEBUG: Evaluating LazyValue...")
        
        try:
            self.evaluating = True
            # print("DEBUG: Evaluating LazyValue...")
            self.cached_value = self.expr_func()  # Evaluate and cache the result
            self.evaluated = True
            # print(f"DEBUG: LazyValue evaluated: {self.cached_value}")
        except Exception as e:
            # print(f"DEBUG: LazyValue evaluation failed: {e}")
            raise e
        finally:
            self.evaluating = False  # Reset evaluating flag
        return self.cached_value
    def iseval(self):
        """
        Check if the value has been evaluated.
        :return: True if evaluated, False otherwise.
        """
        return self.evaluated

# Represents a value, which has a type and its value

#takes in lambda func and evaluated which is the flag- jen
class Value:
    def __init__(self, type, value=None):
        self.t = type
        self.v = value

    def value(self):
        return self.v

    def type(self):
        return self.t


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
    # Evaluate the LazyValue if necessary
    if isinstance(val, LazyValue):
        val = val.value()  # Evaluate and get the cached result

    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None
