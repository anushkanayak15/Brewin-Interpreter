from env_v1 import EnvironmentManager
from type_valuev1 import Type, Value, create_value, get_printable
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program

class Interpreter(InterpreterBase):
    # Binary and Unary operations
    BINARY_OPERATORS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}
    UNARY_OPERATORS = {"neg", "!"}

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.global_stack = []
        self.__initialize_operations()

    # Function to run the program after parsing into an AST
    def run(self, program):
        ast = parse_program(program)
        self.__create_function_table(ast)
        main_function = self.__retrieve_function("main", 0)
        
        main_environment = EnvironmentManager()
        self.global_stack.append([main_environment])
        
        self.__execute_statements(main_function.get("statements"))

    # Function to store function definitions for future lookups
    def __create_function_table(self, ast):
        self.func_table = {}
        for func_def in ast.get("functions"):
            self.func_table[(func_def.get("name"), len(func_def.get("args")))] = func_def

    def __retrieve_function(self, name, num_args):
        if (name, num_args) not in self.func_table:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.func_table[(name, num_args)]

    # Execute statements sequentially, handling different types of nodes
    def __execute_statements(self, statements):
        for statement in statements:
            if self.trace_output:
                print(statement)
            match statement.elem_type:
                case InterpreterBase.FCALL_NODE:
                    self.__invoke_function(statement)
                case "=":
                    self.__assign(statement)
                case InterpreterBase.VAR_DEF_NODE:
                    self.__define_variable(statement)
                case InterpreterBase.RETURN_NODE:
                    return_expression = statement.get("expression")
                    return self.__evaluate_expression(return_expression) if return_expression else Value(Type.NIL, None)
                case InterpreterBase.IF_NODE:
                    self.__process_if(statement)
                case InterpreterBase.FOR_NODE:
                    self.__process_for(statement)

    # Function call handler
    def __invoke_function(self, call_node):
        func_name = call_node.get("name")
        if func_name in ["print", "inputi", "inputs"]:
            return self.__built_in_function(call_node)
        if (func_name, len(call_node.get("args"))) in self.func_table:
            func_def = self.func_table[(func_name, len(call_node.get("args")))]
            parameter_env = EnvironmentManager()
            self.__map_args_to_params(func_def.get("args"), call_node.get("args"), parameter_env)
            
            func_scope = [parameter_env, EnvironmentManager()]
            self.global_stack.append(func_scope)
            return_value = self.__execute_function_body(func_def.get("statements"))
            self.global_stack.pop()
            return return_value if return_value else Value(Type.NIL, None)
        else:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")

    def __built_in_function(self, call_ast):
        func_name = call_ast.get("name")
        if func_name == "print":
            output = ''.join(get_printable(self.__evaluate_expression(arg)) for arg in call_ast.get("args"))
            super().output(output)
        elif func_name in ["inputi", "inputs"]:
            inp = super().get_input()
            return Value(Type.INT, int(inp) if func_name == "inputi" else inp)

    # Assignment operation handler
    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value = self.__evaluate_expression(assign_ast.get("expression"))
        for env in reversed(self.global_stack[-1]):
            if env.set(var_name, value):
                return
        super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment")

    # Helper for defining variables in the current scope
    def __define_variable(self, var_ast):
        var_name = var_ast.get("name")
        if not self.global_stack[-1][-1].create(var_name, Value(Type.INT, 0)):
            super().error(ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}")

    # Evaluates expressions and handles different node types
    def __evaluate_expression(self, expr_ast):
        match expr_ast.elem_type:
            case InterpreterBase.INT_NODE:
                return Value(Type.INT, expr_ast.get("val"))
            case InterpreterBase.STRING_NODE:
                return Value(Type.STRING, expr_ast.get("val"))
            case InterpreterBase.BOOL_NODE:
                return Value(Type.BOOL, expr_ast.get("val"))
            case InterpreterBase.NIL_NODE:
                return Value(Type.NIL, None)
            case InterpreterBase.VAR_NODE:
                return self.__get_variable_value(expr_ast.get("name"))
            case InterpreterBase.FCALL_NODE:
                return self.__invoke_function(expr_ast)
            case op if op in self.BINARY_OPERATORS or op in self.UNARY_OPERATORS:
                return self.__evaluate_operator(expr_ast)

    # Helper for retrieving variable values from the environment stack
    def __get_variable_value(self, var_name):
        for env in reversed(self.global_stack[-1]):
            if env.get(var_name):
                return env.get(var_name)
        super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")

    # Evaluate binary and unary operations
    def __evaluate_operator(self, op_node):
        if op_node.elem_type in self.UNARY_OPERATORS:
            operand = self.__evaluate_expression(op_node.get("op1"))
            return self.op_to_lambda[operand.type()][op_node.elem_type](operand)
        left = self.__evaluate_expression(op_node.get("op1"))
        right = self.__evaluate_expression(op_node.get("op2"))
        if left.type() != right.type():
            super().error(ErrorType.TYPE_ERROR, f"Incompatible types for {op_node.elem_type} operation")
        return self.op_to_lambda[left.type()][op_node.elem_type](left, right)

    # Initializes mappings of operators to their implementations
    def __initialize_operations(self):
        self.op_to_lambda = {
            Type.INT: {
                "+": lambda x, y: Value(Type.INT, x.value() + y.value()),
                "-": lambda x, y: Value(Type.INT, x.value() - y.value()),
                "*": lambda x, y: Value(Type.INT, x.value() * y.value()),
                "/": lambda x, y: Value(Type.INT, x.value() // y.value()),
                "neg": lambda x: Value(Type.INT, -x.value()),
                "==": lambda x, y: Value(Type.BOOL, x.value() == y.value()),
                "!=": lambda x, y: Value(Type.BOOL, x.value() != y.value()),
            },
            Type.STRING: {
                "+": lambda x, y: Value(Type.STRING, x.value() + y.value()),
                "==": lambda x, y: Value(Type.BOOL, x.value() == y.value()),
                "!=": lambda x, y: Value(Type.BOOL, x.value() != y.value()),
            },
            Type.BOOL: {
                "==": lambda x, y: Value(Type.BOOL, x.value() == y.value()),
                "!=": lambda x, y: Value(Type.BOOL, x.value() != y.value()),
                "&&": lambda x, y: Value(Type.BOOL, x.value() & y.value()),
                "||": lambda x, y: Value(Type.BOOL, x.value() | y.value()),
                "!": lambda x: Value(Type.BOOL, not x.value()),
            },
            Type.NIL: {
                "==": lambda x, y: Value(Type.BOOL, x.value() == y.value()),
                "!=": lambda x, y: Value(Type.BOOL, x.value() != y.value()),
            },
        }

def main():
    interpreter = Interpreter()
    with open("./test.br", "r") as f:
        program_code = f.read()
    interpreter.run(program_code)

if __name__ == "__main__":
    main()
