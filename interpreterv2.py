# Anushka Nayak (605977416)

from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
class Return(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value

class Interpreter(InterpreterBase): # change here for scoping

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
# To implement lexical scoping, we will be using stack of stack of dictionaries
# Each scope stack will have its own dictionary to hold variable names and values
        self.scopes = []  
        self.functions = {}  #Dictionary to store function
        #self.declared_vars = []  
        #self.early_return_flag = False
   
    def run(self, program):
        #This is the main method to start executing the program
        ast = parse_program(program) # Parse the program into an AST
        # print("parsed the program into AST:", ast)
        self.define_functions(ast)  #Define all functions in the program
        main_func = self.get_main_func(ast)#Retrieve the main function from the AST
        self.run_func(main_func) #Execute the main function
   
    def define_functions(self, ast):
        function_list = ast.get("functions")
        for func in function_list:
            func_name = func.get("name")
            arg_count = len(func.dict.get("args", []))  # Count the number of arguments
            #print(f"Defining function: {func_name} with {arg_count} args")
            # Create a unique key for the function based on its name and number of arguments
            key = f"{func_name}_{arg_count}"
            if key in self.functions:
                super().error(ErrorType.NAME_ERROR, f"Function {func_name} already defined with {arg_count} arguments")
            self.functions[key] = func  # Store the function definition with the unique key
           
    def get_main_func(self, ast):
        function_list = ast.get("functions") #To get the list of functions from the program
        #  Check if there are functions and if the main function is present
        if len(function_list) < 1: #When no functions are there
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
        #Look for the main function specifically  trhought looping
        for func in function_list:
            if func.get('name') == 'main':
               # print("found main function:", func)
                return func
        # This error is raised  when no main function is found
        super().error(ErrorType.NAME_ERROR, "No main() function was found")
        #return function_list[0] #Return the main function


    def run_func(self, func_node):
        func_scope = {}  # Create a new scope for function param
        self.scopes.append(func_scope)  
        param_list = func_node.dict.get("params", [])
        for param in param_list:
            param_name = param.get("name")
            self.scopes[-1][param_name] = None  


        statement_list = func_node.dict.get("statements", [])
        #self.early_return_flag = False
        try:
            for statement in statement_list:
                self.run_statement(statement)
        except Return as ret:
            return ret.value  # Capture the return value
        finally:
            self.scopes.pop()
    #Loop through each statement to process it
   
    def run_statement(self, statement_node):
        type = statement_node.elem_type
        if type =="vardef": # For variable definition
            self.do_definition(statement_node)
        elif type =="=": #For assignment
            self.do_assignment(statement_node)
        elif type == "fcall":
            func_name = statement_node.dict.get("name")
            args = statement_node.dict.get("args", [])
            return self.do_func_call(func_name, args)
        elif type == "if":  # For if statements
            self.do_if(statement_node) #helper func for if statement
        elif type == "for":  # For for loops
            self.do_for(statement_node) #helper func for handling for statement
        elif type == "return":  # For return statements
            return self.do_return(statement_node)      
        else:
           super().error(ErrorType.NAME_ERROR, f"Invalid statement")

    def do_definition(self, statement_node):
        var_name = statement_node.dict.get("name")  # Get variable name from the dictionary

        if var_name in self.scopes[-1]:
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} already defined in this scope")

        # # Check in the current top dictionary of the stack for duplicates
        # if var_name in self.scopes[-1][-1]:  
        #     super().error(ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}")


        # Add the variable to the current scope and initialize it to None
       
        self.scopes[-1][var_name] = None
   
    def do_assignment(self, statement_node):
        var_name = statement_node.dict.get("name")
        value = self.evaluate_expression(statement_node.dict.get("expression"))
        for scope in reversed(self.scopes):
            if var_name in scope:
                scope[var_name] = value
                return
        self.scopes[-1][var_name] = value
        

    def evaluate_expression(self, expr_node):
     # Evaluate different tpes of expression nodes
        if expr_node.elem_type == "var": # Evaluate variable node
            var_name = expr_node.dict.get("name")  # Access the variable name
           
            for scope in reversed(self.scopes):
                if var_name in scope:
                    return scope[var_name]
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")

        #Evaluate constant nodes for integers
        elif expr_node.elem_type == "int":
            #print("evaluating integer constant:", expr_node.dict.get("val"))
            return expr_node.dict.get("val")  # Access the integer value
        #Evaluate constant nodes for strings
        elif expr_node.elem_type == "string":
            # print("evaluating string constant:", expr_node.dict.get("val"))
            return expr_node.dict.get("val")  # Access the string value
        elif expr_node.elem_type == "bool":  # Evaluate constant nodes for booleans
            return expr_node.dict.get("val")  # Access the boolean value
        elif expr_node.elem_type == "nil":  # Handling for nil
            return expr_node.dict.get("val")
       
        # Unary negation
        elif expr_node.elem_type == "neg":  
            op1 = expr_node.dict.get("op1")
            operand = self.evaluate_expression(op1)     
            if type(operand) is not int:
                super().error(ErrorType.TYPE_ERROR, "Negation operator expects an integer")  
            return -operand 

        #Evaluate binary operations 
        elif expr_node.elem_type in ['+', '-', '*', '/']:
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))   # Get the first operand
            right_op = self.evaluate_expression(expr_node.dict.get("op2")) # Get the second operand
           
            # Handling nil values
            if left_op is None or right_op is None:
                super().error(ErrorType.TYPE_ERROR, "Cannot perform arithmetic operation with nil")
            #  string concatenation
            if isinstance(left_op, str) and isinstance(right_op, str):
                return left_op + right_op
            # Ensure compatible types for operations
            if isinstance(left_op, bool) or isinstance(right_op, bool):
                super().error(ErrorType.TYPE_ERROR, "Cannot perform arithmetic operations with booleans")
            if not isinstance(left_op, (int, str)) or not isinstance(right_op, (int, str)):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")

            # Ensure compatible types for arithmetic operations
            if not isinstance(left_op, (int, bool)) or not isinstance(right_op, (int, bool)):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")

            # Convert booleans to integers if necessary for arithmetic
            left_op = left_op if isinstance(left_op, int) else int(left_op)
            right_op = right_op if isinstance(right_op, int) else int(right_op)


            # Perform the operation based on the operator
       
            if expr_node.elem_type == '+':
                return left_op + right_op
            elif expr_node.elem_type == '-':
                return left_op - right_op
            elif expr_node.elem_type == '*':
                return left_op * right_op
            elif expr_node.elem_type == '/':
                if right_op == 0:  
                    super().error(ErrorType.TYPE_ERROR, "Division by zero is not allowed")
                return left_op // right_op
           
        elif expr_node.elem_type == "fcall":
            function_name = expr_node.dict.get("name")
            args = expr_node.dict.get("args", [])
            return self.do_func_call(function_name, args)
       
        # Handling the comparisons check this implementation:
        elif expr_node.elem_type in ['==', '!=']:
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))
            # If the types of left_op and right_op are not equal, return False for == and !=
            if type(left_op) != type(right_op):
                if expr_node.elem_type in ['==']:
                    return False  
                else:
                    return True
            # comparisons for equality and inequality across different types
            if expr_node.elem_type == '==':
                return left_op == right_op
            elif expr_node.elem_type == '!=':
                return left_op != right_op


        elif expr_node.elem_type in ['<', '<=', '>', '>=']:  # Evaluate binary comparison operations
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))
           
            # Check if left_op is an integer; if not, raise an error
            if not isinstance(left_op, int):
                super().error(ErrorType.TYPE_ERROR, "Left operand must be an integer for comparison")

            # Check if right_op is an integer; if not, raise an error
            if not isinstance(right_op, int):
                super().error(ErrorType.TYPE_ERROR, "Right operand must be an integer for comparison")

            # Handling nil values in comparisons
            if left_op is None and right_op is None:
                return expr_node.elem_type == '=='  
            elif left_op is None or right_op is None:
                return expr_node.elem_type == '!='  
            
            else: 
                if expr_node.elem_type == '<':
                    return left_op < right_op
                elif expr_node.elem_type == '<=':
                    return left_op <= right_op
                elif expr_node.elem_type == '>':
                    return left_op > right_op
                elif expr_node.elem_type == '>=':
                    return left_op >= right_op

        elif expr_node.elem_type in ['&&', '||']:    # Eval logical binary operations
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))

            if not isinstance(left_op, bool) or not isinstance(right_op, bool):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for logical operation")

            return left_op and right_op if expr_node.elem_type == '&&' else left_op or right_op

        elif expr_node.elem_type == '!':  #Eval unary logical operation
            op = self.evaluate_expression(expr_node.dict.get("op1"))

            if not isinstance(op, bool):
                super().error(ErrorType.TYPE_ERROR, "Invalid operation on non-boolean type")
            return not op

        # Eval function call expressions
        elif expr_node.elem_type == "fcall":  # Evaluate function call expressions
            function_name = expr_node.dict.get("name")
            args = expr_node.dict.get("args", [])
            return self.do_func_call(function_name, args)  # Pass the function name and args

        super().error(ErrorType.TYPE_ERROR, f"Unsupported expression type: {expr_node.elem_type}")
   
    #     self.scopes.pop()  # Remove the function scope after execution
    def do_func_call(self, func_name, args):
        if func_name == "print":
            self.handle_print(args)  
            return None
        if func_name == "inputs":
            return self.handle_inputs(args)
       
        if func_name == "inputi":
            return self.handle_inputi(args)
        arg_count = len(args)  
        key = f"{func_name}_{arg_count}"  
        if key not in self.functions:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} with {arg_count} arguments was not found")
        func_def = self.functions[key]
        func_scope = {}
        self.scopes.append(func_scope)

        for i, arg in enumerate(args):
            value = self.evaluate_expression(arg)
            param_name = func_def.dict.get('args', [])[i].dict.get('name')
            self.scopes[-1][param_name] = value

        return_value = None
        try:
            for statement in func_def.dict.get('statements', []):
                result = self.run_statement(statement)
                # If a return value is found in a statement, break early
                if result is not None:
                    return_value = result
                    break
        except Return as ret:
            return_value = ret.value
        finally:
            self.scopes.pop()
        return return_value if return_value is not None else None
    
    def handle_print(self, args):
        #Function to handle function call nodes, print, and input
        evaluated_args = [self.evaluate_expression(arg) for arg in args]
        output_str = ''
        for arg in evaluated_args:
            if isinstance(arg, bool):
                output_str += 'true' if arg else 'false'
            else:
                output_str += str(arg)  # Convert other types to string
        super().output(output_str)

    def handle_inputi(self, statement_node):
    # Check if statement_node is indeed a list (which it seems to be)
        if isinstance(statement_node, list):
            args = statement_node  # Assuming statement_node is a list of arguments
        else:
            args = statement_node.dict.get("args", [])
       
        # If a user prompt is provided, evaluate it
        if len(args) > 0:
            prompt_str = self.evaluate_expression(args[0])  # Evaluate the first argument as the prompt
            super().output(prompt_str)
        # Get input from user
        user_input = super().get_input()
        return self.convert_to_integer(user_input)  # Convert and return the user input
    
    def handle_inputs(self, statement_node):
        if isinstance(statement_node, list):
            args = statement_node  #Assuming statement_node is a list of arguments
        else:
            args = statement_node.dict.get("args", [])
        user_inputs = [] #Initialize a list to collect user inputs
        for arg in args:
            prompt_str = self.evaluate_expression(arg)  
            super().output(prompt_str)  
            user_input = super().get_input()  
            user_inputs.append(user_input) 

        return user_inputs 

#convert user input to an integer, handling potential errors
    def convert_to_integer(self, user_input):
       
        try:
            return int(user_input)  # Cast it to an integer
       
        except ValueError:
            super().error(ErrorType.TYPE_ERROR, "Input value is not an integer")
   
    def do_return(self, statement_node):
        if 'value' in statement_node.dict:
            return_value = self.evaluate_expression(statement_node.dict.get('value'))
            #self.early_return_flag = True
            #self.scopes.pop()  # Clean up current function's scope before returning
            #return return_value  # Return the evaluated value
        else:
            return_value = None
        raise Return(return_value)
        #self.scopes.pop()  # Clean up current function's scope before returning
        #return None  # Default return value is nil
   
    
    def do_if(self, statement_node):
        # Evaluate the condition of the if statement
        condition = self.evaluate_expression(statement_node.dict.get('condition'))
        #Ensure the condition evaluates to a boolean
        if not isinstance(condition, bool):
            super().error(ErrorType.TYPE_ERROR, "Condition in if statement must be of bool type")
        #the statements for the "if" and "else" blocks
        if_statements = statement_node.dict.get('statements', [])
        else_statements = statement_node.dict.get('else_stm', [])
        # Create a local scope for `if` and `else` blocks
        self.scopes.append({})
        try:
            if condition:
                for statement in if_statements:
                    result = self.run_statement(statement)
                    if result is not None:
                        return result
            elif else_statements:
                for statement in else_statements:
                    result = self.run_statement(statement)
                    if result is not None:
                        return result
        finally:
            self.scopes.pop()  # Ensure the `if` block scope is popped
        return None

    def do_for(self, statement_node):
        self.do_assignment(statement_node.dict.get('init'))

        # Loop until the condition is False
        while True:
            condition = self.evaluate_expression(statement_node.dict.get('condition'))
            if not isinstance(condition, bool):  #Ensure the condition evaluates to a boolean
                super().error(ErrorType.TYPE_ERROR, "Condition in for loop must be of bool type")
            if not condition: #Exit the loop if the condition is False
                break

            # Execute the loop body
            self.scopes.append({})  
            try:
                for statement in statement_node.dict.get('statements', []):
                    self.run_statement(statement)
            except Return as ret:
                self.scopes.pop()  
                raise ret
            self.scopes.pop()  
            # Execute the update statement
            self.do_assignment(statement_node.dict.get('update'))
        
def main():
    program = """

func main() {
  if (5 > "hi") {
    print("wow");
  }
}
                 """


    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()
