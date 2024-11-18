from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"
    VOID = "void"
    STRUCT = "struct"


# Represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None):
        self.t = type
        #self.v = value
        self.v = value if value is not None else self.default_value(type)
    def __str__(self):
        if self.v is None:
            return "nil" if self.t != "string" else ""
        return str(self.v)
    
    def value(self):
        return self.v

    def type(self):
        return self.t
    # if a function has a non-void return type but does not explicitly return a value,
    #  it should return a default value based on the return type
    def default_value(self, type):
        if type == Type.INT:
            return Value(Type.INT, 0)
        elif type == Type.BOOL:
            return Value(Type.BOOL, False)
        elif type == Type.STRING:
            return Value(Type.STRING, "")
        elif type == Type.VOID:
            return None
        
        return None

#might need to modify this function to handle user objects
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


def get_printable(val): #TO DO
    if val == Type.VOID:
        return None
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    
    return None


#Each struct is stored in a global registry (UserObjectManager.defined_structs) with the struct name 
# as the key and a dictionary of fields and their types as the value
#Ensure no duplicate struct names exist
#Ensure all field types are valid (primitive types or previously defined structs)
# Struct variables are object references. When declared, they are initialized to nil
# They do not allocate memory for the fields until explicitly initialized with new
class UserObject:
    def __init__(self, name, fields, existing_user_types=[]):
        
        self.name = name
        self.v = {}

        for field in fields:
            field_name = field.get("name")
            field_type = field.get("var_type")
            if field_type not in ["int", "bool", "string"] and field_type not in existing_user_types:
                raise ValueError(f"Invalid field type '{field_type}' for field '{field_name}'.")

            # Initialize with default values based on type
            if field_type == "int":
                self.v[field_name] = Value(Type.INT, 0)
            elif field_type == "bool":
                self.v[field_name] = Value(Type.BOOL, False)
            elif field_type == "string":
                self.v[field_name] = Value(Type.STRING, "")
            else:  # user-defined struct types, default to None (nil)
                self.v[field_name] = Value(Type.NIL, None)

    def set_val(self, field_name, value, existing_user_types=[]):
        
        if field_name not in self.v:
            return False  
        # Retrieve the expected field type
        expected_type = self.v[field_name].type()
        #check for type mismatch
        if expected_type not in ["int", "bool", "string", "nil"] and expected_type not in existing_user_types:
            return False  
        if expected_type  in ["int", "bool", "string"]:
            if expected_type != value.type():
                return False 

        self.v[field_name] = value
        return True


    def get_val(self, field_name):
        return self.v.get(field_name, None)

    def get_all_val(self):
        return self.v

    def has_val(self): 
        return len(self.v) > 0

def create_user_object(name, values=[], existing_user_types=[]):
        
        #Create a user object based on the specified fields and existing user types.
        field_values = {}
        for field in values:
            field_name = field.get("name")
            field_type = field.get("var_type")
            # Validate the field type
            if field_type not in ["int", "bool", "string"] and field_type not in existing_user_types:
                return False
            # Initialize default values for primitive types
            if field_type == "int":
                field_values[field_name] = Value(Type.INT, 0)
            elif field_type == "bool":
                field_values[field_name] = Value(Type.BOOL, False)
            elif field_type == "string":
                field_values[field_name] = Value(Type.STRING, "")
            else:  #  user-defined struct types, default to nil
                #  user-defined struct types, default to nil
                if field_type == name:  # Handle self-referential field
                    field_values[field_name] = Value(Type.NIL, None)
                else:
                    field_values[field_name] = Value(Type.NIL, None)
        return UserObject(name, values, existing_user_types)


def create_val(val):
    
        #Create a Value object from the provided input value.

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
