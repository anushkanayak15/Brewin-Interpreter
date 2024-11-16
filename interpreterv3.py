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

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()
        self.default_user_types= {}
        self.valid_user_types_names= []
        self.user_types_fields= {}

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
            
            if result.type() != arg_type:
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch for argument {arg_name} in function {func_name}")
        
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        # Execute function body
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()
        #print(f"Function '{func_name}' is a void function with return type '{return_type}'")
        #print(f"Return value: {return_val} (type: {return_val.type() if return_val is not None else 'None'})")
        # Handle void function return type constraints

        # # Handle void functions
        # if return_type == Type.VOID:
        #     if return_val is not None:
        #         super().error(ErrorType.TYPE_ERROR, f"Void function '{func_name}' should not return a value")
        #     return None  # Void functions return nothing
        
        # Ensure a default value for non-void functions if no return was explicitly provided
        if return_val is None:
            default_value = Value(return_val)
            return_val = Value(default_value)  # Default to the type's default value
            
        # Coerce return value if function return type is bool and return_val is int
        if return_type == Type.BOOL and return_val.type() == Type.INT:
            return_val = self.__coerce_to_bool(return_val)
        
        
        return return_val
#try to get a fefault_return that returns a value object setting the value with its defualt using the default func in typeval2
#pass that default returnr to run statements and then run statement in which we pass that to do return. in do return we use that
# it either has an expression node or not. if it has an expression node and return type is none then we raise an error
    
    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        #return Interpreter.NIL_VALUE

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
        # If the variable name includes a dot operator
        if "." in assign_ast.get("name"):
            fields = assign_ast.get("name").split(".")  # Split by the dot operator
            object_name = fields[0]  # The first part is the base object
            field_chain = fields  # Remaining parts are the field chain

            # Retrieve the base object
            current_obj = self.env.get(object_name)

            # Check if the base object exists
            if current_obj is None:
                super().error(ErrorType.NAME_ERROR, f"Undefined variable '{object_name}' in assignment")

            # Traverse through the field chain
            for field_name in field_chain[:-1]:
                # Ensure the current object is of struct type
                if current_obj.type() not in self.default_user_types:
                    super().error(ErrorType.TYPE_ERROR, f"'{field_name}' is not a struct type")

                # Ensure the current object is not nil
                if current_obj.value() is None:
                    super().error(ErrorType.FAULT_ERROR, f"Accessing field '{field_name}' of a nil object")

                # Move to the next field in the chain
                current_obj = current_obj.value().get_val(field_name)

                # Ensure the next field exists
                if current_obj is None:
                    super().error(ErrorType.NAME_ERROR, f"Field '{field_name}' not found in the struct")

            # At the last field in the chain
            final_field_name = field_chain[-1]
            # Perform type checking
            field_type = self.user_types_fields[current_obj.type()][final_field_name]
            value_obj = self.__eval_expr(assign_ast.get("expression"))

            # Allow assigning nil to struct fields
            if field_type in self.default_user_types and value_obj.type() == Type.NIL:
                current_obj.value().set_val(final_field_name, value_obj)
                return

            # Ensure type compatibility
            if field_type == Type.BOOL and value_obj.type() == Type.INT:
                value_obj = self.__coerce_to_bool(value_obj)  # Coerce int -> bool
            if field_type != value_obj.type():
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Type mismatch: cannot assign {value_obj.type()} to {field_type} in field '{final_field_name}'",
                )

            # Set the value of the final field
            current_obj.value().set_val(final_field_name, value_obj)
            return
        
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        current_value_obj = self.env.get(var_name)  # Retrieve the current variable's Value object

        # Check if the variable exists
        if current_value_obj is None:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment")

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
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
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
            if struct_name not in self.default_user_types:  # Check if the struct type is valid
                super().error(ErrorType.TYPE_ERROR, f"Undefined struct type {struct_name}")
            # Create a new instance of the struct
            new_instance = create_user_object(struct_name, self.user_types_fields[struct_name], self.valid_user_types_names)
            # Return the instance wrapped in a Value object
            return Value(struct_name, new_instance)


    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        
        
        # Coerce both operands to boolean if the operation is logical (&& or ||)
        if arith_ast.elem_type in {"&&", "||"}:
            left_value_obj = self.__coerce_to_bool(left_value_obj)
            right_value_obj = self.__coerce_to_bool(right_value_obj)
        
        # Also handle coercion for equality comparisons, allowing int-to-bool comparison
        elif arith_ast.elem_type in {"==", "!="}:
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

        self.__run_statement(init_ast)  # initialize counter variable
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
            run_for = self.__coerce_to_bool(run_for)  # Coerce if condition is int
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
                self.__run_statement(update_ast)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast, default_type):
        #TO DO COULD BE SOURCE OF ERROR FOR DEFAULT_TYPE IS NONE
        expr_ast = return_ast.get("expression")
        #func_return_type = self.env.get("current_return_type")
        # Void function should not return a value
        # Ensure default_type is valid
        if default_type is None:
            super().error(ErrorType.TYPE_ERROR, "Return type is undefined")
        if default_type == Type.VOID and expr_ast is not None:
            super().error(ErrorType.TYPE_ERROR, "Void function cannot return a value")
        
        if expr_ast is None:
            #print("Void return statement encountered")
            #return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
            return (ExecStatus.RETURN, default_type)
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        # Coerce if function return type is bool and return value is int
        func_return_type = self.env.get("current_return_type")
        if func_return_type == Type.BOOL and value_obj.type() == Type.INT:
            value_obj = self.__coerce_to_bool(value_obj)
        
        if default_type() != value_obj.type():
            super().error(ErrorType.TYPE_ERROR, "Return type mismatch")

        return (ExecStatus.RETURN, value_obj)
    
    # Helper function to coerce an integer to a boolean
    def __coerce_to_bool(self, value):
        if value.type() == Type.INT:
            return Value(Type.BOOL, value.value() != 0)
        return value
        
def main():
    program = """
struct animal {
    name : string;
    noise : string;
    color : string;
    extinct : bool;
    ears: int; 
}
func main() : void {
   var pig : animal;
   var extinct : bool;
   extinct = make_pig(pig, 0);
   print(extinct);
}
func make_pig(a : animal, extinct : int) : bool{
  if (a == nil){
    print("making a pig");
    a = new animal;
  }
  a.extinct = extinct;
  return a.extinct;
}
                 """


    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()
