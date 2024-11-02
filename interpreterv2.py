# Anushka Nayak (605977416)

# The Interpreter class initializes variables and prepares to run the program
# The run method serves as the starting point for executing a Brewin program, transforming it into an ast and executing the main function
# The interpreter verifies the existence of the main function and executes its statements in order
# The code distinguishes among variable definitions, assignments, and function calls, processing each type accordingly
# The evaluation mechanism addresses variables, constants, binary operations, and function calls, while ensuring accurate error handling


from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Interpreter(InterpreterBase):

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        #self.variables = {}  #Dictionary to store variable names and values 
        #self.functions = {}  #Dictionary to store function definitions so that we can call them in any order
# To implement lexical scoping, we will be using stack of stack of dictionaries. 
# Each scope stack will have its own dictionary to hold variable names and values
        self.scopes = [[]]  # Stack of stacks, each stack contains dictionaries for scopes
    def run(self, program):
        #This is the main method to start executing the program
        ast = parse_program(program) # Parse the program into an AST
        # print("parsed the program into AST:", ast)
        self.define_functions(ast)  #Define all functions in the program
        
        main_func = self.get_main_func(ast)# Retrieve the main function from the AST
        self.run_func(main_func) #Execute the main function
    
    def define_functions(self, ast):
        function_list = ast.get("functions")  # Get the list of functions from the program
        for func in function_list:
            func_name = func.get("name")
            if func_name in self.functions:
                super().error(ErrorType.NAME_ERROR, f"Function {func_name} defined more than once")
            self.functions[func_name] = func  # Store function definition


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

        return function_list[0] #Return the main function


    def run_func(self, func_node):
     # Execute the statements within a function node   
        statement_list = func_node.get('statements')
        # print("executing statements:", statement_list)
        self.scopes.append([{}])  # Push a new stack with a new dictionary for the function scope
        for statement in statement_list:
            self.run_statement(statement)
        self.scopes.pop() #pop the function after execution
    #Loop through each statement to process it
    
    def run_statement(self, statement_node):
        type = statement_node.elem_type

        if type =="vardef": # For variable definition
            self.do_definition(statement_node)

        elif type =="=": #For assignment
            self.do_assignment(statement_node)
        
        elif type =="fcall": # For function call 
            self.do_func_call(statement_node)

        elif type == "if":  # For if statements
            self.do_if(statement_node) #helper func for if statement

        elif type == "for":  # For for loops
            self.do_for(statement_node) #helper func for handling for statement

        elif type == "return":  # For return statements
            return self.do_return(statement_node)
        
        else:
           super().error(ErrorType.NAME_ERROR, f"Invalid statement")


    def do_definition(self, statement_node):

        var_name = statement_node.dict.get("name") # Get variable name from the dictionary

        # Check if the variable has already been defined
        var_name = statement_node.dict.get("name")  # Get variable name from the dictionary

        if var_name in self.scopes[-1][-1]:  # Check if the variable has already been defined in the current scope
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once")
        else:
            self.scopes[-1][-1][var_name] = None  # Initialize the variable in the current scope

        

    def do_assignment(self, statement_node):
        var_name = statement_node.dict.get("name")  # Get variable name from the dictionary  

        # Find the variable in the current stack or any outer stacks
        for scope in reversed(self.scopes):
            if var_name in scope[-1]:  # Check in the top dictionary of the current stack
                break
        else:
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")

        # Get the expression from the statement node
        expr_node = statement_node.dict.get("expression")

        # Evaluate the right-hand side expression and assign the value
        value = self.evaluate_expression(expr_node)
        scope[-1][var_name] = value  # Update the variable in the found scope

    def evaluate_expression(self, expr_node):
     # Evaluate different tpes of expression nodes
        if expr_node.elem_type == "var": # Evaluate variable node

            var_name = expr_node.dict.get("name")  # Access the variable name
            
            # Find the variable in the current stack or any outer stacks
            for scope in reversed(self.scopes):
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
            return None  # Represent nil as None (or a similar representation)

        #Evaluate binary operations (addition and subtraction)
        elif expr_node.elem_type in ['+', '-', '*', '/']:

            left_op = self.evaluate_expression(expr_node.dict.get("op1"))   # Get the first operand
            
            right_op = self.evaluate_expression(expr_node.dict.get("op2")) # Get the second operand
            # Handling nil values
        if left_op is None or right_op is None:
            super().error(ErrorType.TYPE_ERROR, "Cannot perform arithmetic operation with nil")

            # Need to check incompatible types before performing the operation
            if isinstance(left_op, str) or isinstance(right_op, str):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")

            # Perform the operation based on the operator
        

            if expr_node.elem_type == '+':
                return left_op + right_op
            elif expr_node.elem_type == '-':
                return left_op - right_op
            elif expr_node.elem_type == '*':
                return left_op * right_op
            elif expr_node.elem_type == '/':
                return left_op // right_op  # Integer division like python
        
        # Handling the comparisons check this implementation: 
        elif expr_node.elem_type in ['==', '!=', '<', '<=', '>', '>=']:  # Evaluate binary comparison operations
            left_op = self.evaluate_expression(expr_node.dict.get("op1"))
            right_op = self.evaluate_expression(expr_node.dict.get("op2"))

            # Handling nil values in comparisons
            if left_op is None and right_op is None:
                return expr_node.elem_type == '=='  # Both are nil, equal
            elif left_op is None or right_op is None:
                return expr_node.elem_type == '!='  # One is nil, the other is not

            # Type checking for comparisons
            if type(left_op) != type(right_op):
                if isinstance(left_op, (int, bool)) and isinstance(right_op, (int, bool)):
                    return left_op == right_op if expr_node.elem_type == '==' else left_op != right_op
                else:
                    super().error(ErrorType.TYPE_ERROR, "Incompatible types for comparison")

            if expr_node.elem_type == '==':
                return left_op == right_op
            elif expr_node.elem_type == '!=':
                return left_op != right_op
            elif expr_node.elem_type == '<':
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
            
            # Handling nil values in logical operations
            if left_op is None or right_op is None:
                super().error(ErrorType.TYPE_ERROR, "Cannot perform logical operation with nil")

            if not isinstance(left_op, bool) or not isinstance(right_op, bool):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for logical operation")

            return left_op and right_op if expr_node.elem_type == '&&' else left_op or right_op

        elif expr_node.elem_type == '!':  # Evaluate unary logical operation
            op = self.evaluate_expression(expr_node.dict.get("op1"))
            if op is None:
                super().error(ErrorType.TYPE_ERROR, "Invalid operation on nil value")

            if not isinstance(op, bool):
                super().error(ErrorType.TYPE_ERROR, "Invalid operation on non-boolean type")

            return not op

        # Evaluate function call expressions
        elif expr_node.elem_type == "fcall":

            function_name = expr_node.dict.get("name")

            args = expr_node.dict.get("args", [])

            #Handle print function (not allowed in expressions)
            if function_name == "print":

                super().error(ErrorType.NAME_ERROR, f"Function {function_name} is not allowed in expressions")

            #Only supporting inputi function calls
            
            elif function_name == "inputi":
                
                if len(args) > 1:  # Check for more than one argument
                    super().error(ErrorType.NAME_ERROR, "No inputi() function found that takes > 1 parameter")

                 # Handle the user_prompt if it exists
                if args:
                    user_prompt = self.evaluate_expression(args[0])  # Evaluate the user_prompt argument
                    super().output(user_prompt)  # Output the user_prompt to the screen

            # Get user input and convert to integer
                user_input = super().get_input()
                # print("result of operation:", result)
                return int(user_input)  # Return the integer value of the input
            
            # Handle the new inputs() function for string input
            elif function_name == "inputs":
                return self.handle_inputs(args)

        # Throw error for unsupported expression type
        super().error(ErrorType.TYPE_ERROR, f"Unsupported expression type: {expr_node.elem_type}")
    
    
    def do_func_call(self, statement_node):
        # Get the function name
        func_name = statement_node.dict.get("name")
        args = statement_node.dict.get("args", [])

        # Handle built-in print function
        if func_name == "print":
            return self.handle_print(statement_node)

        # Handle built-in inputi function
        elif func_name == "inputi":
            return self.handle_inputi(statement_node)

        # Check if the function is defined
        if func_name not in self.functions:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} was not found")

        # Retrieve the defined function
        def_func = self.functions[func_name]
        def_args = def_func.get('args', [])

        # Check for correct number of arguments
        if len(args) != len(def_args):
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} takes {len(def_args)} arguments but was called with {len(args)}")

        # Prepare a new local context for parameters
        local_vars = {}  # Initialize local_vars to store parameter values
        for i, arg in enumerate(args):
            local_vars[def_args[i].dict.get('name')] = self.evaluate_expression(arg)  # Pass by value

        # Execute the function with its local variable context
        statement_list = def_func.get('statements', [])
        for statement in statement_list:
            self.run_statement(statement, local_vars)


    def handle_print(self, statement_node):
       
        # Get arguments and evaluate them

        args = [self.evaluate_expression(arg) for arg in statement_node.dict.get('args', [])]

        
        output_str = ''.join(map(str, args))# Convert all arguments to strings and concatenate them
    #   print("output string to print:", output_str) 
        super().output(output_str)
        return None



    def handle_inputi(self, statement_node):
   
        user_prompt = statement_node.dict.get("args", [])
        
        # If a user_prompt is provided, evaluate it
        if len(user_prompt) > 0:
            prompt_str = self.evaluate_expression(user_prompt[0])
            super().output(prompt_str)

        # Get input from user
        user_input = super().get_input()
        # print("user input received:", user_input)
        
        return self.convert_to_integer(user_input)

#convert user input to an integer, handling potential errors
    def convert_to_integer(self, user_input):
        
        try:
            return int(user_input)  # Cast it to an integer
        
        except ValueError:
            super().error(ErrorType.TYPE_ERROR, "Input value is not an integer")
    
    def do_return(self, statement_node):

        if 'value' in statement_node.dict:

            return_value = self.evaluate_expression(statement_node.dict.get('value'))
            return return_value  #Return the evaluated value
        
        else:
            return None  # Default return value is nil
    
    def handle_inputs(self, args):
        # Handles string inputs from user
        if len(args) > 1:  # Check for more than one argument
            super().error(ErrorType.NAME_ERROR, "No inputs() function found that takes > 1 parameter")

        user_prompt = ''
        if args:
            user_prompt = self.evaluate_expression(args[0])
            super().output(user_prompt)  # Output the user prompt to the screen

        return super().get_input()  #Get string input and return it

    def do_if(self, statement_node):
        condition = self.evaluate_expression(statement_node.dict.get('condition'))

        if not isinstance(condition, bool):  # Ensure the condition evaluates to a boolean
            super().error(ErrorType.TYPE_ERROR, "Condition in if statement must be of bool type")

        statements = statement_node.dict.get('statements', [])
        else_stm = statement_node.dict.get('else_stm', None)

        if condition:  # If the condition is true, execute  if block
            for statement in statements:
                self.run_statement(statement)
        elif else_stm:  # If the condition is false & there are else statements, execute the else statements
            for statement in else_stm:
                self.run_statement(statement)
        return None


    def do_for(self, statement_node):
        self.do_assignment(statement_node.dict.get('init'))  #Execute the initialization statement

        while True:
            condition = self.evaluate_expression(statement_node.dict.get('condition'))

            if not isinstance(condition, bool):  #Ensure the condition evaluates to a boolean
                super().error(ErrorType.TYPE_ERROR, "Condition in loops must be of bool type")

            if not condition:  #if condition is false  exit the loop
                break

            statements = statement_node.dict.get('statements', [])
            for statement in statements:
                self.run_statement(statement)  # execute the statements within the loop
            
            self.do_assignment(statement_node.dict.get('update'))  #Execute the update statement
        return None


      
def main():
    # Sample Brewin program to test the interpreter
    program = """func foo() {
                    var x;
                    x = 5 + 6;
                    print("The sum is: ", x);
                 }

                 func main() {
                     foo();  // Call the foo function
                 }"""
    
    interpreter = Interpreter()  # Create an instance of the interpreter
    
    # Run the program
    interpreter.run(program)

if __name__ == "__main__":
    main()
