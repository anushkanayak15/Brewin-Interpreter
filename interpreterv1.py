#Anushka Nayak (605977416)
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Interpreter(InterpreterBase):

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.variables = {}  #Dictionary to store variable names and values 

    def run(self, program):
        #This is the main method to start executing the program
        ast = parse_program(program) # Parse the program into an AST

        
        main_func = self.get_main_func(ast)# Retrieve the main function from the AST
        self.run_func(main_func) #Execute the main function


    def get_main_func(self, ast):
        
        function_list = ast.get("functions") #To get the list of functions from the program
    
        #  Check if there are functions and if the main function is present
        if len(function_list) < 1: #When no functions are there
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
        
    
        #Look for the main function specifically  trhought looping
        for func in function_list:
            if func.get('name') == 'main':
                return func
    
        # This error is raised  when no main function is found
        super().error(ErrorType.NAME_ERROR, "No main() function was found")

        return function_list[0] #Return the main function


    def run_func(self, func_node):
     # Execute the statements within a function node   
        statement_list = func_node.get('statements')
        
        for statement in statement_list:
            self.run_statement(statement)
    #Loop through each statement to process it
    
    def run_statement(self, statement_node):
        type = statement_node.elem_type

        if type =="vardef": # For variable definition
            self.do_definition(statement_node)

        elif type =="=": #For assignment
            self.do_assignment(statement_node)
        
        elif type =="fcall": # For function call 
            self.do_func_call(statement_node)
        
        else:
           super().error(
               ErrorType.NAME_ERROR,
               f"Invalid statement",
           )


    def do_definition(self, statement_node):

        var_name = statement_node.dict.get("name") # Get variable name from the dictionary

        # Check if the variable has already been defined
        if var_name in self.variables:
            #If variable is defined more than once
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once")

        else:
            
            self.variables[var_name] =None # Initialize the variable in the dictionary with no value

        

    def do_assignment(self, statement_node):
    
        var_name = statement_node.dict.get("name") # Get variable name from the dictionary  
    # To check if the variable was defined

        if var_name not in self.variables:

            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")

        # Get the expression from the statement node
        expr_node = statement_node.dict.get("expression")

        # Evaluate the right-hand side expression and assign the value
        value = self.evaluate_expression(expr_node)
        
        self.variables[var_name] = value
    
    def evaluate_expression(self, expr_node):
     # Evaluate different tpes of expression nodes
        if expr_node.elem_type == "var": # Evaluate variable node

            var_name = expr_node.dict.get("name")  # Access the variable name
            
            if var_name not in self.variables: # CHeck if variable has been defined
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")
            
            return self.variables[var_name]

        #Evaluate constant nodes for integers
        elif expr_node.elem_type == "int":

            return expr_node.dict.get("val")  # Access the integer value

        #Evaluate constant nodes for strings
        elif expr_node.elem_type == "string":

            return expr_node.dict.get("val")  # Access the string value

        #Evaluate binary operations (addition and subtraction)
        elif expr_node.elem_type in ['+', '-']:

            left_op = self.evaluate_expression(expr_node.dict.get("op1"))   # Get the first operand
            
            right_op = self.evaluate_expression(expr_node.dict.get("op2")) # Get the second operand

            # Need to check incompatible types before performing the operation
            if isinstance(left_op, str) or isinstance(right_op, str):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")

            # Perform the operation based on the operator
        
            return left_op +right_op if expr_node.elem_type == '+' else left_op - right_op

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
                
                return int(user_input)  # Return the integer value of the input

        # Throw error for unsupported expression type
        super().error(ErrorType.TYPE_ERROR, f"Unsupported expression type: {expr_node.elem_type}")
    
    
    def do_func_call(self, statement_node):
        # Get the function name

        func_name = statement_node.dict.get('name')  

        if func_name == "print":
            self.handle_print(statement_node)

        elif func_name == "inputi":
            return self.handle_inputi(statement_node)
        
        else:
            # Throw error for nsupported function call
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} has not been defined")


    def handle_print(self, statement_node):
       
        # Get arguments and evaluate them

        args = [self.evaluate_expression(arg) for arg in statement_node.dict.get('args', [])]

        
        output_str = ''.join(map(str, args))# Convert all arguments to strings and concatenate them

        super().output(output_str)


    def handle_inputi(self, statement_node):
   
        user_prompt = statement_node.dict.get("args", [])
        
        # If a user_prompt is provided, evaluate it
        if len(user_prompt) > 0:
            prompt_str = self.evaluate_expression(user_prompt[0])
            super().output(prompt_str)

        # Get input from user
        user_input = super().get_input()
        return self.convert_to_integer(user_input)

#convert user input to an integer, handling potential errors
    def convert_to_integer(self, user_input):
        
        try:
            return int(user_input)  # Cast it to an integer
        
        except ValueError:
            super().error(ErrorType.TYPE_ERROR, "Input value is not an integer")

      
def main():
    
    program = """func main() {
                    var x;
                    x = 5 + 6;
                    print("The sum is: ", x);
                 }"""
    
   
    interpreter = Interpreter()
    
    interpreter.run(program)


if __name__ == "__main__":
    main()