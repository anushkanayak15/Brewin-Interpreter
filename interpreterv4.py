
# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v4 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev4 import Type, LazyValue, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        captured_env = self.env.copy()
        self.__call_func_aux("main", [],captured_env)

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
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

    def __run_statements(self, statements,captured_env=None):
        if captured_env is None:
            captured_env = self.env.copy()
        self.env.push_block()
        for statement in statements:
            # if self.trace_output:
            #     print(statement)
            status, return_val = self.__run_statement(statement, captured_env)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement,captured_env):
        if captured_env is None:
            captured_env = self.env.copy()
        status = ExecStatus.CONTINUE
        return_val = None
        # Handle try catch block
        if statement.elem_type == InterpreterBase.TRY_NODE:
            status, return_val = self.__do_try(statement)
        # elif statement.elem_type == InterpreterBase.CATCH_NODE:
        # # Catch nodes only appear in try blocks
        #     raise Exception("Catch nodes are not standalone statements")  
        elif statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement,captured_env)
        elif statement.elem_type == "=":
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)
        elif statement.elem_type == InterpreterBase.RAISE_NODE:  # Handle raise
            self.__do_raise(statement)
        else:
            raise Exception(f"Error Unrecognized statement type: {statement.elem_type}")

        return (status, return_val)
    
    def __call_func(self, call_node,captured_env):
        if captured_env is None:
            captured_env = self.env.copy()
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args,captured_env)

    def __call_func_aux(self, func_name, actual_args,captured_env):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            #result = copy.copy(self.__eval_expr(actual_ast))
            #each ast should be wrapped in lazy val before added
            arg_name = formal_ast.get("name")
            args[arg_name] = LazyValue(lambda actual_ast = actual_ast: self.__eval_expr(actual_ast,captured_env)) # evaluated lazily
              # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()
        #return return_val
        return return_val.value() if isinstance(return_val, LazyValue) else return_val

    # def __call_print(self, args):
    #     output = ""
    #     for arg in args:
    #         result = self.__eval_expr(arg)  # result is a Value object
    #         output = output + get_printable(result)
    #     super().output(output)
    #     return Interpreter.NIL_VALUE
    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # Evaluate the expression
            if isinstance(result, LazyValue):
                result = result.value()  # Force evaluation if it's a LazyValue
            if not isinstance(result, Value):
                #  print(f"DEBUG: Invalid print argument of type {type(result)} with value {result}")
                raise TypeError("print expects a Value object.")
            output += get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE


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

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        expr = assign_ast.get("expression")
        # Debug: Evaluate the expression and log the result
        # evaluated_value = self.__eval_expr(expr)
        # print(f"DEBUG: Assigning to {var_name}: {evaluated_value}")

        # to do : create a copy of the environment which i then pass to the lambda
        # eval expr i pass captured environ 
        # need to make sure eval expr if there is a captured environ use that else leave it working as it is. 
        # need to ensure that ehenever this lambda func is created the environ at this current point is passed. 
        #so  if i have captured environ then i use that else use the curr environemnt

        # # Create a lazy expression for the assignment
        # lazy_expr = LazyValue(
        #     lambda: copy.copy(self.__eval_expr(expr))
            
        # )
        # Capture the current environment when creating the lazy expression
        captured_env = self.env.copy()

        # Create a lazy expression with the captured environment
        lazy_expr = LazyValue(lambda captured_env=captured_env: self.__eval_expr(expr, captured_env))
        # Set the lazy expression in the environment
        if not self.env.set(var_name, lazy_expr):
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
   
        # print(f"DEBUG: Created LazyValue for {var_name} with expression: {expr}")
        # Before setting the lazy expression, evaluate the current value of the variable
        # and check if it references itself.
        # evaluated_value = lazy_expr.value()  # Evaluate it now to capture the current state

        # if not self.env.set(var_name, Value(evaluated_value.type(), evaluated_value.value())):
        #     super().error(
        #         ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
        #     )
        # current_value = self.env.get(var_name)
        # if isinstance(current_value, LazyValue):
        #     current_value = current_value.value()
        # # print(f"DEBUG: Current value of {var_name}: {current_value}")
        # # Ensure the lazy value captures the evaluated current state safely
        # if not self.env.set(var_name, lazy_expr):
        #     super().error(
        #         ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
        #     )

        
    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        if not self.env.create(var_name, Interpreter.NIL_VALUE):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )
            # one potential thing add a captured environemnt in the func
    def __eval_expr(self, expr_ast,captured_env=None):
        
        try:
            if captured_env is None:
                captured_env = self.env.copy()
            if isinstance(expr_ast, LazyValue):
                result = expr_ast.value()
                return result
            #         result = expr_ast.value()
    #         print(f"DEBUG: Evaluating LazyValue for {expr_ast}: {result}")
    #         return result

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
                #var_value = self.env.get(var_name)
                var_value = captured_env.get(var_name)  
                    # print(f"DEBUG: Accessing variable {var_name}: {var_value}")

                if var_value is None:
                    super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                return var_value.value() if isinstance(var_value, LazyValue) else var_value
            if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
                return self.__call_func(expr_ast,captured_env)
            if expr_ast.elem_type in Interpreter.BIN_OPS:
                return self.__eval_op(expr_ast,captured_env)
            if expr_ast.elem_type == Interpreter.NEG_NODE:
                return self.__eval_unary(expr_ast, Type.INT, lambda x: -x,captured_env)
            if expr_ast.elem_type == Interpreter.NOT_NODE:
                return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x,captured_env)

            super().error(ErrorType.TYPE_ERROR, f"Unsupported expression type: {expr_ast.elem_type}")
        except Exception as e:
            raise e  

    def __eval_op(self, arith_ast,captured_env=None):
        if captured_env is None:
            captured_env = self.env.copy()
    # Evaluate the left operand
        left_value_obj = self.__eval_expr(arith_ast.get("op1"),captured_env)
        if isinstance(left_value_obj, LazyValue):
            left_value_obj = left_value_obj.value()  # Ensure LazyValue is evaluated

        # Short-circuiting for logical AND (&&)
        if arith_ast.elem_type == "&&":
            if left_value_obj.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR, "Left operand of && must be of type bool"
                )
            # Short-circuit: if the left operand is False, return False immediately
            if not left_value_obj.value():
                return Value(Type.BOOL, False)

            # Evaluate the right operand only if needed
            right_value_obj = self.__eval_expr(arith_ast.get("op2"),captured_env)
            
            if isinstance(right_value_obj, LazyValue):
                right_value_obj = right_value_obj.value()
            
            if right_value_obj.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR, "Right operand of && must be of type bool"
                )
            return Value(Type.BOOL, left_value_obj.value() and right_value_obj.value())

        # Short-circuiting for logical OR (||)
        if arith_ast.elem_type == "||":
            if left_value_obj.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR, "Left operand of || must be of type bool"
                )
            # Short-circuit: if the left operand is True, return True immediately
            if left_value_obj.value():
                return Value(Type.BOOL, True)

            # Evaluate the right operand only if needed
            right_value_obj = self.__eval_expr(arith_ast.get("op2"),captured_env)
            if isinstance(right_value_obj, LazyValue):
                right_value_obj = right_value_obj.value()
            if right_value_obj.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR, "Right operand of || must be of type bool"
                )
            return Value(Type.BOOL, left_value_obj.value() or right_value_obj.value())

        # Handle other operators (no short-circuiting required)
        right_value_obj = self.__eval_expr(arith_ast.get("op2"),captured_env)
        if isinstance(right_value_obj, LazyValue):
            right_value_obj = right_value_obj.value()
        
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
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        
        result=  f(left_value_obj, right_value_obj)
        # print(f"DEBUG: Result of operation {arith_ast.elem_type}: {result.value()}")
        return result
    
    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()
    
    def __handle_div_0(self,x,y):
        if y.value() == 0:
            raise Exception("div0")  # Raise division by 0 exception
        return Value(x.type(), x.value() // y.value())
    

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
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
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: self.__handle_div_0(x,y)

    def __do_if(self, if_ast):
        cond_ast = LazyValue(lambda: self.__eval_expr(if_ast.get("condition")))
        result = self.__eval_expr(cond_ast) 
        #result = self.__eval_expr(cond_ast).value()  # Force evaluation here
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
        cond_ast = LazyValue(lambda: self.__eval_expr(for_ast.get("condition")))
        update_ast = LazyValue(lambda: self.__run_statement(for_ast.get("update")))

        self.__run_statement(init_ast)  # initialize counter variable
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
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

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        # value_obj = copy.copy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, self.__eval_expr(expr_ast))
        # return should be handled lazily 
        #return (ExecStatus.RETURN, LazyValue(lambda: self.__eval_expr(expr_ast)))
    
    def __do_raise(self, raise_ast):
        #RAISE_NODE to invokes the __do_raise helper function
#The expression following the raise keyword must be evaluated eagerly
#Ensure the evaluated expression results in a STRING. If not, raise a TYPE_ERROR

        # Evaluate the exception type expression
        exception_expr = raise_ast.get("exception_type")
        exception_value = self.__eval_expr(exception_expr)  # Eager evaluation

        # Validate that the result is a string
        if exception_value.type() != Type.STRING:
            super().error(
                ErrorType.TYPE_ERROR,
                "The expression passed to `raise` must evaluate to a string."
            )

        # Raise an exception with the string value
        raise Exception(exception_value.value())
   
    def __do_try(self, try_ast):
        # The try node will help identify the statements inside the try block
        # Catch nodes will be used to match exception types
        # To handle variable shadowing, need to execute try block in a new scope
        # I fno exception then program cont but if raised,match with catch blocks to see which one
        # Tricky part: if no catch block in curr scope propogate outwards till it is caught
        try_stm = try_ast.get("statements")
        catch_nodes = try_ast.get("catchers")

        try:
            self.env.push_block()  # New scope for try
            status, return_val = self.__run_statements(try_stm)
            self.env.pop_block()
            return status, return_val  # If there are no exceptions then just return 
        except Exception as e:
            # Handle exceptions raised within the try block
            self.env.pop_block()  # Ensure try scope is cleaned up

            except_msg = str(e)
            for catch_node in catch_nodes:
                catch_type = catch_node.get("exception_type")
                if catch_type == except_msg:  # Match the exception type
                    self.env.push_block()  # New scope for the catch block
                    status, return_val = self.__run_statements(catch_node.get("statements"))
                    self.env.pop_block()
                    return status, return_val
            # If no matching catch block, propagate the exception
            raise e
  
def main():
    program = """
func main() {
  var x;
  x = foo(y);
  print("OK");
  print(x);  /* NAME_ERROR due to undefined y is deferred to this line */
}


/*
*OUT*
OK
ErrorType.NAME_ERROR
*OUT*
*/



   """


    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()
