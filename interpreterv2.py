# Anushka Nayak (605977416)


# The Interpreter class initializes variables and prepares to run the program
# The run method serves as the starting point for executing a Brewin program, transforming it into an ast and executing the main function
# The interpreter verifies the existence of the main function and executes its statements in order
# The code distinguishes among variable definitions, assignments, and function calls, processing each type accordingly
# The evaluation mechanism addresses variables, constants, binary operations, and function calls, while ensuring accurate error handling




from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Interpreter(InterpreterBase): # change here for scoping




    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
# To implement lexical scoping, we will be using stack of stack of dictionaries.
# Each scope stack will have its own dictionary to hold variable names and values
        self.scopes = [[]]  # Stack of stacks, each stack contains dictionaries for scopes
        self.functions = {}  #Dictionary to store function
        #self.declared_vars = []  # List to track declared variables for the current scope
        self.early_return_flag = False
        self.return_value = None
   
    def run(self, program):
        #This is the main method to start executing the program
        ast = parse_program(program) # Parse the program into an AST
        # print("parsed the program into AST:", ast)
        self.define_functions(ast)  #Define all functions in the program
        main_func = self.get_main_func(ast)# Retrieve the main function from the AST
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


    # def run_func(self, func_node):
    #     self.scopes.append([{}])  # New scope for function parameters
    #     param_list = func_node.dict.get("params", [])
    #     for param in param_list:
    #         param_name = param.get("name")
    #         self.scopes[-1][-1][param_name] = None  # Initialize parameters


    #     statement_list = func_node.dict.get("statements", [])
    #     return_value = None
    #     for statement in statement_list:
    #         return_value = self.run_statement(statement)
    #         if return_value is not None:  # If a return value is encountered
    #             break


    #     self.scopes.pop()  # Clean up function body scope
    #     return return_value  # Return the captured return value


    def run_func(self, func_node):
        self.scopes.append([{}]) # Create a new scope for function param
        param_list = func_node.dict.get("params", [])
        for param in param_list:
            param_name = param.get("name")
            self.scopes[-1][-1][param_name] = None  # Initialize parameters


        statement_list = func_node.dict.get("statements", [])
        self.early_return_flag = False
        self.return_value = None
        for statement in statement_list:
            self.run_statement(statement)
            if self.early_return_flag:  #Check for early return
                break


        self.scopes.pop()  # Clean up function body scope
        return self.return_value  # Return the captured return value
   
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


        # Check if there is a current scope to define the variable
        if not self.scopes or not self.scopes[-1]:
            super().error(ErrorType.NAME_ERROR, "No current scope to define variable")


        # # Check in the current top dictionary of the stack for duplicates
        # if var_name in self.scopes[-1][-1]:  
        #     super().error(ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}")


        # Add the variable to the current scope and initialize it to None
       
        self.scopes[-1][-1][var_name] = None
   
       
    # def do_assignment(self, statement_node):
    #     var_name = statement_node.dict.get("name")
    #     value = self.evaluate_expression(statement_node.dict.get("expression"))


    #     # Check if there are any scopes available
    #     if not self.scopes:
    #         super().error(ErrorType.NAME_ERROR, "No scopes available for variable assignment")


    #     # Check all scopes for variable definition
    #     for inner_stack in reversed(self.scopes):
    #         if inner_stack and inner_stack[-1]:  # Check if the inner stack is not empty
    #             if var_name in inner_stack[-1]:  # Check in the current top dictionary of the current stack
    #                 inner_stack[-1][var_name] = value  # Update variable in the found scope
    #                 return


    #     super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")
    def do_assignment(self, statement_node):
        var_name = statement_node.dict.get("name")
        value = self.evaluate_expression(statement_node.dict.get("expression"))
        for scope_stack in reversed(self.scopes):
            if scope_stack:
                if var_name in scope_stack[-1]:
                    scope_stack[-1][var_name] = value
                    return
        self.scopes[-1][-1][var_name] = value

    def evaluate_expression(self, expr_node):
     # Evaluate different tpes of expression nodes
        if expr_node.elem_type == "var": # Evaluate variable node
            var_name = expr_node.dict.get("name")  # Access the variable name
           
            # Find the variable in the current stack or any outer stacks
            for scope in reversed(self.scopes):
                if scope and scope[-1]:  # Ensure scope and its top dictionary are not empty
                    if var_name in scope[-1]:  # Check in the top dictionary of the current stack
                        return scope[-1][var_name]
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
       
        # Evaluate unary negation
        elif expr_node.elem_type == "neg":  # Check for unary negation
            operand = self.evaluate_expression(expr_node.dict.get("op1"))  # Evaluate the operand
            if isinstance(operand, int):
                return -operand  # Return the negated value
            else:
                super().error(ErrorType.TYPE_ERROR, "Negation operator expects an integer")






        #Evaluate binary operations (addition and subtraction)
        elif expr_node.elem_type in ['+', '-', '*', '/']:
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))   # Get the first operand
            right_op = self.evaluate_expression(expr_node.dict.get("op2")) # Get the second operand
           
            # Handling nil values
            if left_op is None or right_op is None:
                super().error(ErrorType.TYPE_ERROR, "Cannot perform arithmetic operation with nil")
           
            # Allow string concatenation
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
                if right_op == 0:  # Prevent division by zero
                    super().error(ErrorType.TYPE_ERROR, "Division by zero is not allowed")
                return left_op // right_op
           
        elif expr_node.elem_type == "fcall":
            function_name = expr_node.dict.get("name")
            args = expr_node.dict.get("args", [])
            return self.do_func_call(function_name, args)
       
        # Handling the comparisons check this implementation:
        elif expr_node.elem_type in ['==', '!=', '<', '<=', '>', '>=']:  # Evaluate binary comparison operations
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))


            # If the types of left_op and right_op are not equal, return False for == and !=
            if type(left_op) != type(right_op):
                if expr_node.elem_type in ['==']:
                    return False  # Return False for equality and inequality comparisons
                else:
                    return True




                # Allow comparisons for equality and inequality across different types
            if expr_node.elem_type == '==':
                return left_op == right_op
            elif expr_node.elem_type == '!=':
                return left_op != right_op
           
            #     # Allow comparisons involving numbers and strings
            # if isinstance(left_op, str) and isinstance(right_op, (int, bool)):
            #     left_op = left_op == str(right_op)
            # elif isinstance(right_op, str) and isinstance(left_op, (int, bool)):
            #     right_op = str(right_op) == left_op


            if isinstance(left_op, str) or isinstance(right_op, str):
                super().error(ErrorType.TYPE_ERROR, "Comparisons with strings using <, <=, >, >= are not allowed")


         
            # Handling nil values in comparisons
            if left_op is None and right_op is None:
                return expr_node.elem_type == '=='  # Both are nil, equal
            elif left_op is None or right_op is None:
                return expr_node.elem_type == '!='  # One is nil, the other is not




            if type(left_op) != type(right_op):
                super().error(ErrorType.TYPE_ERROR, "Cannot compare values of different types with operators other than == or !=")
           
            if expr_node.elem_type == '<':
                return left_op < right_op
            elif expr_node.elem_type == '<=':
                return left_op <= right_op
            elif expr_node.elem_type == '>':
                return left_op > right_op
            elif expr_node.elem_type == '>=':
                return left_op >= right_op




        elif expr_node.elem_type in ['&&', '||']:  # Evaluate logical binary operations
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))




            if not isinstance(left_op, bool) or not isinstance(right_op, bool):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for logical operation")




            return left_op and right_op if expr_node.elem_type == '&&' else left_op or right_op




        elif expr_node.elem_type == '!':  # Evaluate unary logical operation
            op = self.evaluate_expression(expr_node.dict.get("op1"))


            if not isinstance(op, bool):
                super().error(ErrorType.TYPE_ERROR, "Invalid operation on non-boolean type")
            return not op




        # Evaluate function call expressions
        elif expr_node.elem_type == "fcall":  # Evaluate function call expressions
            function_name = expr_node.dict.get("name")
            args = expr_node.dict.get("args", [])
            return self.do_func_call(function_name, args)  # Pass the function name and args




        # Throw error for unsupported expression type
        super().error(ErrorType.TYPE_ERROR, f"Unsupported expression type: {expr_node.elem_type}")
   
   
    #     self.scopes.pop()  # Remove the function scope after execution
    def do_func_call(self, func_name, args):
        if func_name == "print":
            self.handle_print(args)  # Directly handle the print function
            return None
       
       
        if func_name == "inputs":
            return self.handle_inputs(args)
       
        if func_name == "inputi":
            return self.handle_inputi(args)
       
        arg_count = len(args)  # Get the number of arguments passed
        key = f"{func_name}_{arg_count}"  # Create the key for the overloaded function
        if key not in self.functions:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} with {arg_count} arguments was not found")


        def_func = self.functions[key]  # Retrieve the correct function definition
        def_args = def_func.dict.get('args', [])
        if len(args) != len(def_args):  # Check for correct number of arguments
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} takes {len(def_args)} arguments but was called with {len(args)}")
        func_scope = {}
        self.scopes.append([func_scope])# Create a new scope for function parameters
        for i, arg in enumerate(args):
            value = self.evaluate_expression(arg)  # Evaluate the argument expression
            param_name = def_args[i].dict.get('name')
            self.scopes[-1][-1][param_name] = value  # Assign the evaluated value to the parameter name


        statement_list = def_func.dict.get('statements', [])
        self.early_return_flag = False
        self.return_value = None  # Initialize return_value
       
        for statement in statement_list:
            self.run_statement(statement)  # Execute each statement in the function
            if self.early_return_flag:  # Check for early return
                break


        self.scopes.pop()  # Remove the function scope after execution
        return self.return_value if self.return_value is not None else None  # Return the captured return value




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




#convert user input to an integer, handling potential errors
    def convert_to_integer(self, user_input):
       
        try:
            return int(user_input)  # Cast it to an integer
       
        except ValueError:
            super().error(ErrorType.TYPE_ERROR, "Input value is not an integer")
   
    def do_return(self, statement_node):
        if 'value' in statement_node.dict:
            self.return_value = self.evaluate_expression(statement_node.dict.get('value'))
            #self.early_return_flag = True
            #self.scopes.pop()  # Clean up current function's scope before returning
            #return return_value  # Return the evaluated value
        else:
            self.return_value = None
        self.early_return_flag = True
        #self.scopes.pop()  # Clean up current function's scope before returning
        #return None  # Default return value is nil
   
    def handle_inputs(self, statement_node):
        if isinstance(statement_node, list):
            args = statement_node  # Assuming statement_node is a list of arguments
        else:
            args = statement_node.dict.get("args", [])
        user_inputs = []  # Initialize a list to collect user inputs
        for arg in args:
            prompt_str = self.evaluate_expression(arg)  # Evaluate each argument as a prompt
            super().output(prompt_str)  # Print the prompt to the user
            user_input = super().get_input()  # Get input from user
            user_inputs.append(user_input)  # Collect inputs

        return user_inputs  # Return the list of user inputs

   
    def do_if(self, statement_node):
        condition = self.evaluate_expression(statement_node.dict.get('condition'))
        if not isinstance(condition, bool):  # Ensure the condition evaluates to a boolean
            super().error(ErrorType.TYPE_ERROR, "Condition in if statement must be of bool type")
        block_scope = dict(self.scopes[-1][-1])
        # Create a new scope for the statements in the if block
        self.scopes.append([block_scope]) # Create a new dictionary for the new scope


        statements = statement_node.dict.get('statements', [])
        else_stm = statement_node.dict.get('else_stm', None)


        if condition:  # If the condition is true, execute if block
            for statement in statements:
                self.run_statement(statement)
                if self.early_return_flag:  # Exit if an early return occurred
                    break
        elif else_stm:  # If the condition is false & there are else statements, execute the else statements
            for statement in else_stm:
                self.run_statement(statement)
                if self.early_return_flag:  # Exit if an early return occurred
                    break


        self.scopes.pop()  # Remove the scope after executing the if statement

    def do_for(self, statement_node):
        self.do_assignment(statement_node.dict.get('init'))  #Execute the initialization statemen
        while True:
            condition = self.evaluate_expression(statement_node.dict.get('condition'))
            if not isinstance(condition, bool):  #Ensure the condition evaluates to a boolean
                super().error(ErrorType.TYPE_ERROR, "Condition in loops must be of bool type")
            if not condition:  #if condition is false  exit the loop
                break
            statements = statement_node.dict.get('statements', [])
            for statement in statements:
                self.run_statement(statement)  # execute the statements within the loop
                if self.early_return_flag:  # Exit if an early return occurred
                    break
            self.do_assignment(statement_node.dict.get('update'))  #Execute the update statement
             
def main():
    program = """


  func foo() {
 print(1);
}


func bar() {
 return nil;
}


func main() {
 var x;
 x = foo();
 if (x == nil) {
  print(2);
 }
 var y;
 y = bar();
 if (y == nil) {
  print(3);
 }
 
}

               """


    interpreter = Interpreter()
    interpreter.run(program)


if __name__ == "__main__":
    main()
