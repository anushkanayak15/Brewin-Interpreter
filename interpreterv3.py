# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import Type, Value, create_value, get_printable, UserObject, create_user_object, create_val
#FOR STRUCTS
#new class in new type file for user objects. this class has type and value. the value is a dict to hold fields 
#have a check of exsisting user objects. because student can call person. user defined func goes through all the structs and calls create user
#creating a struct, setting the fields
class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}
    PRIM_TYPES = {"int", "bool", "string"} 
    VALID_FUNCTION_RETURN_TYPES = {"int", "string", "bool", "void"}


    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.default_user_types = {}
        self.valid_user_types_names= []
        self.user_types_fields= {}
        self.__setup_ops()
        
        #print("DEBUG: Initialized default_user_types")

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        
        # Set up user-defined types (structs) from AST
        self.__set_up_user_defined_types(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.__call_func_aux("main", [])
    
    def __set_up_user_defined_types(self, ast):
        """
        Sets up user-defined structures (structs) from the abstract syntax tree (AST).
        """
        # Check if there are any structs defined in the AST
        if  ast.get("structs")==[]:  # Returns an empty list if "structs" is not found
            return
        # Iterate through each struct definition in the AST
        for type_def in ast.get("structs"):
            # Extract the struct's name and its list of fields
            type_name = type_def.get("name")
            fields = type_def.get("fields")  # Returns an empty list if "fields" is not found
            # Check for duplicate struct definitions
            if type_name in self.default_user_types:
                super().error(
                    ErrorType.NAME_ERROR, f"Duplicate definition for type {type_name}"
                )
            # Add the struct name to the list of valid user-defined types
            self.valid_user_types_names.append(type_name)
            # Create the UserObject for the struct
            result = create_user_object(type_name, fields, self.valid_user_types_names)
            if result is False:
                super().error(
                    ErrorType.TYPE_ERROR, f"Unknown field type in struct creation"
                )
            # Store the created UserObject and its fields
            self.default_user_types[type_name] = result
            self.user_types_fields[type_name] = {}
            # Populate field metadata for the struct
            for field in fields:
                field_name = field.get("name")
                field_type = field.get("var_type")
                self.user_types_fields[type_name][field_name] = field_type



    def __set_up_function_table(self, ast):
        # validate the parameter types and return type for each function before execution
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            # Store parameter and return types for type checking
            param_types = [arg.get("var_type") for arg in func_def.get("args")]
            return_type = func_def.get("return_type")
            
            for param_type in param_types:
                # Check if the parameter type is a valid primitive type or a defined user-defined type
                if param_type not in [Type.INT, Type.BOOL, Type.STRING] and param_type not in self.default_user_types:
                    super().error(ErrorType.TYPE_ERROR, f"Invalid type {param_type} in parameters")

            # Check if the return type is a valid primitive type or a defined user-defined type
            if return_type not in [Type.INT, Type.BOOL, Type.STRING, Type.VOID] and return_type not in self.default_user_types:
                super().error(ErrorType.TYPE_ERROR, f"Invalid return type {return_type} for function {func_name}")
            
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def
            
    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements, default_return =None):
        self.env.push_block()
        for statement in statements:
            # if self.trace_output:
            #     print(statement, default_return)
            status, return_val = self.__run_statement(statement, default_return)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, default_return)

    def __run_statement(self, statement, default_return):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement)
        elif statement.elem_type == "=":
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement, default_return)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)

        return (status, return_val)
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        # TO DO RETURN TYPE VOID
        # enforce type consistency during function calls
        #actual  arg tpes must match the expected formal arg type
        #  return type of the function must align with the specified return type
        # handle coercion when passing parameters
        
        if func_name == "print":
           self.__call_print(actual_args)
           return 
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        return_type = func_ast.get("return_type")
        
        #print(f"Invoking function '{func_name}' with return type '{return_type}'")  # Debug
        
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.copy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            arg_type = formal_ast.get("var_type")
            # Coerce if passing an int to a bool parameter
            
            if arg_type == Type.BOOL and result.type() == Type.INT:
                #print("in call func aux before param coerce to bool")
                result = self.__coerce_to_bool(result)
            
            # # Validate argument type
            # if result.type() != arg_type:
            #     if result.type() not in self.default_user_types or result.type() != arg_type:
            #         super().error(
            #             ErrorType.TYPE_ERROR,
            #             f"Type mismatch for argument {arg_name} in function {func_name}",
            #         )
            if result.type() != arg_type:
                # Allow `nil` for user-defined struct types
                if result.type() == Type.NIL and arg_type in self.default_user_types:
                    # Preserve the type signature for the `nil` value
                    result = Value(arg_type, None)
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Type mismatch for argument {arg_name} in function {func_name}: "
                        f"expected {arg_type}, got {result.type()}",
                    )

            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
            self.env.create(arg_name, value)
        # Set up a default return value
        #default_return = None #fix this now
        if return_type == Type.VOID:
            default_return = Value(Type.VOID)
        elif return_type == Type.INT:
            default_return = Value(Type.INT, 0)  # Default value for int
        elif return_type == Type.STRING:
            default_return = Value(Type.STRING, "")  # Default value for string
        elif return_type == Type.BOOL:
            default_return = Value(Type.BOOL, False)  # Default value for bool
        elif return_type in self.default_user_types:
        # Struct types return nil by default
            default_return = Value(Type.NIL, return_type)
        else:
            # Raise an error for unsupported return types
            super().error(ErrorType.TYPE_ERROR, f"Unsupported return type: {return_type}")

        # Execute function body
        _, return_val = self.__run_statements(func_ast.get("statements"), default_return)
        self.env.pop_func()
        #print(f"Function '{func_name}' is a void function with return type '{return_type}'")
        #print(f"Return value: {return_val} (type: {return_val.type() if return_val is not None else 'None'})")
            
        # Ensure a default value for non-void functions if no return was explicitly provided
        if return_val is None:
            return_val = default_return
            #return_val = Value(return_type)  # Default to the type's default value
            
        # Coerce return value if function return type is bool and return_val is int
        if return_type == Type.BOOL and return_val.type() == Type.INT:
            return_val = self.__coerce_to_bool(return_val)
        
        if return_val.type() != return_type:
            # Allow nil as a valid return value for user-defined structs
            if return_val.type() == Type.NIL and return_type in self.default_user_types:
                return return_val  # No error, nil is valid for struct types
            
            # If it's not nil or doesn't match the user-defined struct, raise an error
            if return_val.type() not in self.default_user_types or return_val.type() != return_type:
                super().error(ErrorType.TYPE_ERROR, "Return type mismatch")


        
        return return_val
        # if return_type== Type.VOID:
        #     return
        # else: 
        #     return return_val
#try to get a fefault_return that returns a value object setting the value with its defualt using the default func in typeval2
#pass that default returnr to run statements and then run statement in which we pass that to do return. in do return we use that
# it either has an expression node or not. if it has an expression node and return type is none then we raise an error
    
    # def __call_print(self, args):
    #     #if it is printable then we print. if is fields of an object then you can print you cant print the object itself
    #     # if it is not printable raise an error and check that you cant print void. 
    #     output = ""
    #     for arg in args:
    #         result = self.__eval_expr(arg) 
    #         printable_result = get_printable(result)

    #     # If the value is void or non-printable, raise an error
    #         if printable_result is None:
    #             super().error(ErrorType.TYPE_ERROR, "Cannot print void or non-printable value.")

    #         output += printable_result
    #     super().output(output)
    
    def __call_print(self, args):
        """
        Handles the print function by evaluating expressions and printing their values.
        Properly handles void values, user-defined structures, and nil.
        """
        output = []
        
        for arg in args:
            # Evaluate the expression
            result = self.__eval_expr(arg)
            
            # Handle void values: cannot be printed
            if result.type() == Type.VOID:
                super().error(ErrorType.TYPE_ERROR, "Cannot print void value.")
            
            # Handle user-defined structures
            if result.type() in self.default_user_types and result.value() == None: #I WILL HAVE TO CHANGE THIS

                output.append("nil")

            elif result.type() in self.default_user_types or result.type() == Type.NIL:
                # Print "nil" if the value is nil (uninitialized)
                
                if result.type() == Type.NIL: 
                    output.append("nil")
                else:
                    # Raise an error if attempting to print the entire structure
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Cannot print entire user-defined structure of type {result.type()}. Access specific fields instead."
                    )
            else:
                # Get printable representation for primitive types
                printable_result = get_printable(result)
                #print(printable_result)
                # If the value is non-printable, raise an error
                if printable_result is None:
                    super().error(ErrorType.TYPE_ERROR, "Cannot print non-printable value.")

                output.append(printable_result)
        
        # Join all outputs with a space and send to the output stream
        super().output("".join(output))


    def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    # Modify __assign to handle int to bool coercion by checking the current type via EnvironmentManager
    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))

        if "." in var_name:
            fields = var_name.split(".")
            obj = self.env.get(fields[0])  # Get the base object

            # Handle base object nil or missing errors
            if obj is None:
                super().error(ErrorType.NAME_ERROR, f"Variable '{fields[0]}' not found")
            if obj.type() not in self.user_types_fields:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot access fields of a non-struct type '{obj.type()}'"
                )
            if obj.type() == Type.NIL:
                super().error(ErrorType.FAULT_ERROR, f"Variable '{fields[0]}' is nil")

            # Extract the UserObject from the Value
            obj = obj.value() #THIS OBJECT SH

            fields.pop(0)  # Remove the base object from the field chain
            while len(fields) > 0:
                field = fields.pop(0)
                # Validate object before accessing its fields
                if obj is None :
                #if obj is None    or obj.name is None
                    super().error(ErrorType.FAULT_ERROR, f"Field chain leads to nil or uninitialized object")

                if field not in self.user_types_fields[obj.name]: #this is causing error
                    super().error(ErrorType.NAME_ERROR, f"Field '{field}' not found in struct '{obj.name}'")
                
                field_type = self.user_types_fields[obj.name][field]

                if len(fields) == 0:  # If this is the last field
                    if field_type in self.PRIM_TYPES:
                        # Handle type coercion for primitive types
                        if field_type == Type.BOOL and value_obj.type() == Type.INT:
                            value_obj = self.__coerce_to_bool(value_obj)
                        if field_type != value_obj.type():
                            super().error(
                                ErrorType.TYPE_ERROR,
                                f"Type mismatch: cannot assign {value_obj.type()} to {field_type} in field '{field}'"
                            )
                    elif field_type in self.user_types_fields:  # Handle nested user-defined struct types
                        if value_obj.type() != field_type and value_obj.type() != Type.NIL:
                            super().error(
                                ErrorType.TYPE_ERROR,
                                f"Type mismatch: cannot assign {value_obj.type()} to {field_type} in field '{field}'"
                            )
                    else:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f"Unknown field type '{field_type}' in struct '{obj.name}'"
                        )

                    # Assign the value to the field using `set_val`
                    if not obj.set_val(field, value_obj, self.valid_user_types_names):
                        super().error(ErrorType.NAME_ERROR, f"Failed to assign value to field '{field}'")
                    return

                # Move to the next nested object
                obj = obj.get_val(field)
                if obj is None or obj.type() == Type.NIL:
                    super().error(ErrorType.FAULT_ERROR, f"Field '{field}' is nil or uninitialized")

                # Extract the UserObject from the nested Value
                obj = obj.value()

        else:
            # If no dot operator, handle simple variable assignment
            current_value_obj = self.env.get(var_name)

            # Check if the variable exists
            if current_value_obj is None:
                super().error(ErrorType.NAME_ERROR, f"Undefined variable '{var_name}' in assignment")

            # Handle primitive type assignments
            if current_value_obj.type() in self.PRIM_TYPES:
                # Allow coercion for bool: int -> bool
                if current_value_obj.type() == Type.BOOL and value_obj.type() == Type.INT:
                    value_obj = self.__coerce_to_bool(value_obj)
                # Ensure types match after coercion
                if current_value_obj.type() != value_obj.type():
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Type mismatch: cannot assign {value_obj.type()} to {current_value_obj.type()} in '{var_name}'",
                    )
            self.env.set(var_name, value_obj)
    
    
    def __var_def(self, var_ast):
        # initialize with default values and validate type
        var_name = var_ast.get("name")
        var_type = var_ast.get("var_type")

        # Check if the variable type is valid
        if var_type not in [Type.INT, Type.BOOL, Type.STRING] and var_type not in self.default_user_types:
            super().error(ErrorType.TYPE_ERROR, f"Invalid type {var_type} for variable {var_name}")
        
        # Set default value based on type
        default_value = Value(var_type)
        #print(f"Creating variable '{var_name}' with type '{var_type}' and default value '{default_value}'") 
        
        if not self.env.create(var_name, default_value):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            # Handle dotted variable names (field access)
            if "." in var_name:
                fields = var_name.split(".")
                obj = self.env.get(fields[0])  # Get the base object
                print(obj)
                # Handle base object nil or missing errors
                if obj is None: # TO DO
                    super().error(ErrorType.NAME_ERROR, f"Variable '{fields[0]}' not found")
                if obj.type() == Type.NIL:
                    super().error(ErrorType.FAULT_ERROR, f"Variable '{fields[0]}' is nil")
                # Check if the base object is a primitive type
                if obj.type() in self.PRIM_TYPES:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Cannot access fields on a primitive type '{obj.type()}'"
                    )
                # Extract the UserObject from the Value
                obj = obj.value()

                fields.pop(0)  # Remove the base object from the field chain
                while len(fields) > 0:
                    field = fields.pop(0)
                    
                    
                    if field not in self.user_types_fields[obj.name]:
                        super().error(ErrorType.NAME_ERROR, f"Field '{field}' not found in struct '{obj.name}'")

                    # Get the value of the current field
                    obj = obj.get_val(field)
                    if obj is None:
                        super().error(ErrorType.NAME_ERROR, f"Field '{field}' not found")
                    if obj.type() == Type.NIL and len(fields) > 0:
                        super().error(ErrorType.FAULT_ERROR, f"Field '{field}' is nil or uninitialized")

                    # If there are more fields, ensure the value is a UserObject
                    if len(fields) > 0:
                        if not isinstance(obj.value(), UserObject):
                            super().error(ErrorType.TYPE_ERROR, f"Field '{field}' is not a struct type")
                        obj = obj.value()  # Move to the next UserObject

                # Return the resolved field value
                return obj

            # Handle simple variable access
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable '{var_name}' not found")
            return val
        
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        
        if expr_ast.elem_type == "new":  # New struct instance
            struct_name = expr_ast.dict.get("var_type")  # Access the structure type from the 'var_type' key
            if struct_name not in self.user_types_fields:
                super().error(ErrorType.TYPE_ERROR, f"Undefined struct type {struct_name}")
            # Transform self.user_types_fields[struct_name] into the expected list format
            fields = [{"name": field_name, "var_type": field_type} 
                    for field_name, field_type in self.user_types_fields[struct_name].items()]
            new_instance = create_user_object(struct_name, fields, self.valid_user_types_names)
            if not new_instance:
                super().error(ErrorType.TYPE_ERROR, f"Failed to create instance of struct type {struct_name}")
            # Return the instance wrapped in a Value object
            return Value(struct_name, new_instance)


    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
#WHEN TYPE IS IN THE USER DEFINED TYPE AND THE VALUE IS NONE AND THE OTHER OPERATOR TYPE IS NIL IT SHOULD ALLOW == AND =!
        # Check if any operand is of type 'void'
        if left_value_obj.type() == Type.VOID or right_value_obj.type() == Type.VOID:
            super().error(ErrorType.TYPE_ERROR, "Cannot perform operations on 'void' type")

        
        #print(f"DEBUG: Evaluating operation {arith_ast.elem_type} with types {left_value_obj.type()} and {right_value_obj.type()}")
        # Coerce both operands to boolean if the operation is logical (&& or ||)
        if arith_ast.elem_type in {"&&", "||"}:
            left_value_obj = self.__coerce_to_bool(left_value_obj)
            right_value_obj = self.__coerce_to_bool(right_value_obj)
        
        # Also handle coercion for equality comparisons, allowing int-to-bool comparison
        elif arith_ast.elem_type in {"==", "!="}:
            # Handle int-to-bool coercion
            if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
                left_value_obj = self.__coerce_to_bool(left_value_obj)
            elif left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT:
                right_value_obj = self.__coerce_to_bool(right_value_obj)
            if left_value_obj.type() in self.default_user_types.keys() and right_value_obj.type() in self.default_user_types.keys():
                if left_value_obj.type() != right_value_obj.type():
                    super().error(ErrorType.TYPE_ERROR, "Cannot compare structs of different types.")
            if left_value_obj.type() in self.default_user_types.keys() or right_value_obj.type() in self.default_user_types.keys():
                if left_value_obj.type() == Type.NIL or  right_value_obj.type()== Type.NIL:
                    if left_value_obj.type() == Type.NIL and right_value_obj.type() in self.default_user_types.keys() and right_value_obj.value() == None:
                        if arith_ast.elem_type in {"=="}:
                            return Value(Type.BOOL, True)
                        else:
                            return Value(Type.BOOL, False)
                    elif right_value_obj.type() == Type.NIL and left_value_obj.type() in self.default_user_types.keys() and left_value_obj.value() == None:
                        if arith_ast.elem_type in {"=="}:
                            return Value(Type.BOOL, True)
                        else:
                            return Value(Type.BOOL, False)
                
                if left_value_obj.type() != right_value_obj.type():
                    return Value(Type.BOOL, False)
                if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
                    left_value_obj = self.__coerce_to_bool(left_value_obj)
                elif left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT:
                    right_value_obj = self.__coerce_to_bool(right_value_obj)
                

        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        #f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        f = self.op_to_lambda[left_value_obj.type()].get(arith_ast.elem_type)
        if f is None:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        return f(left_value_obj, right_value_obj)
    

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        # Coerce int to bool for NOT operation
        if arith_ast.elem_type == Interpreter.NOT_NODE and value_obj.type() == Type.INT:
            value_obj = self.__coerce_to_bool(value_obj)
        
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        

    def __do_if(self, if_ast):
        #print("in if block")
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        # Coerce if condition is int
        result = self.__coerce_to_bool(result)
        #print("type:", result.type(), "value:", result.value())

        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_for(self, for_ast):
        init_ast = for_ast.get("init") 
        cond_ast = for_ast.get("condition")
        update_ast = for_ast.get("update") 

        if init_ast:
            #print(f"Initializing for-loop: {init_ast}")
            self.__run_statement(init_ast, Interpreter.NIL_VALUE)  # TO DO CHECK HOW JENNIFER INITIALIZES IT HERE
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
            run_for = self.__coerce_to_bool(run_for)  # Coerce if condition is int
            #print(f"Loop condition evaluated to: {run_for.value()}")
            if run_for.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val
                if update_ast:
                    self.__run_statement(update_ast, Interpreter.NIL_VALUE)
                #self.__run_statement(update_ast,None)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast, default_type):
        #TO DO COULD BE SOURCE OF ERROR FOR DEFAULT_TYPE IS NONE
        expr_ast = return_ast.get("expression")
        #func_return_type = self.env.get("current_return_type")
        # Void function should not return a value
        # Ensure default_type is valid
        #print("default type in do return")
       # print(default_type)
        print(default_type)
        if default_type is None:
            super().error(ErrorType.TYPE_ERROR, "Return type is undefined")
        # TO DO:
        if default_type == Type.VOID:
            if expr_ast is not None:
                super().error(ErrorType.TYPE_ERROR, "Void function cannot return a value")
            return (ExecStatus.RETURN, None)
        if expr_ast is None:
            #print("Void return statement encountered")
            #return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
            if default_type == Type.VOID:
                return (ExecStatus.RETURN, None)
            return (ExecStatus.RETURN, default_type)
        
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        # Coerce if function return type is bool and return value is int
        if default_type == Type.VOID:
            func_return_type = Type.VOID  # Explicitly set the function return type to void
        else:
            func_return_type = default_type.type()  # Access the type from the Value object if not void#wont work when default return is void. add an if before this
        #because if it is void it is just string. right now if we try to access the type it assumes it ias an object. 
        #if default type is void funcreturntype is void
        #print(f"DEBUG: func_return_type = {func_return_type}")
        if func_return_type == Type.BOOL and value_obj.type() == Type.INT:
            value_obj = self.__coerce_to_bool(value_obj)
        
        if default_type.type() == Type.NIL:
            # Allow `nil` for user-defined struct types
            if default_type.value() in self.user_types_fields and value_obj.type() == Type.NIL:
                # Ensure the returned `nil` matches the expected struct type
                return (ExecStatus.RETURN, value_obj)
            elif default_type.value() != value_obj.type():
                super().error(ErrorType.TYPE_ERROR, "Return type mismatch")

        elif default_type != Type.VOID and default_type.type() != value_obj.type(): #THIS IS THE SOURCE OF ERROR
            #print(f"DEBUG: Type mismatch - Expected: {default_type}, Found: {value_obj.type()}")
            super().error(ErrorType.TYPE_ERROR, "Return type mismatch") #handle void case and structs

        return (ExecStatus.RETURN, value_obj)
    
    # Helper function to coerce an integer to a boolean
    def __coerce_to_bool(self, value):
        if value.type() == Type.INT:
            return Value(Type.BOOL, value.value() != 0)
        return value
        
def main():
    program = """
struct circle{
  r: int;
}

struct square {
  s: int;
}


func main(): void{
  var c: circle;
  var s: square;

  s = new square;
  c = new circle;
  print(c == s);
}

/*
*OUT*
ErrorType.TYPE_ERROR
*OUT*
*/




       """


    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()
