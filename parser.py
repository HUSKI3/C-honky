from sly import Parser
import logging
from lexer import ChLexer

class ChParser(Parser):
    tokens = ChLexer.tokens
    debugfile = "parser.out"
    log = logging.getLogger()
    log.setLevel(logging.ERROR)
    #syntax_error_obj = syntax_error()

    precedence = (
        ("left", EMPTY),
        ("left", ","),
        ("right", "="),
        ("left", "|"),
        ("left", "&"),
        ("left", EQEQ, NOT_EQEQ),
        ("left", EQ_LESS, EQ_GREATER, "<", ">"),
        ("left", "+", "-"),
        ("left", "*", "/", "%"),
        ("right", UMINUS, UPLUS),
        ("right", "!"),
        ("left", COLON_COLON),
    )

    # Program START
    @_("program statement")
    def program(self, p):
        return p.program + (p.statement,)

    @_("statement")
    def program(self, p):
        return (p.statement,)

    @_("empty")
    def program(self, p):
        return ()

    # Program END
    ###########################################################################
    # Statements START

    @_("function_declaration")
    def statement(self, p):
        return p.function_declaration + ()

    @_("class_declaration")
    def statement(self, p):
        return p.class_declaration

    @_("function_call_statement")
    def statement(self, p):
        return p.function_call_statement

    @_("class_attribute_assignment")
    def statement(self, p):
        return p.class_attribute_assignment

    @_("conditional")
    def statement(self, p):
        return p.conditional

    @_("while_loop")
    def statement(self, p):
        return p.while_loop

    @_("python_code_statement")
    def statement(self, p):
        return p.python_code_statement

    @_("variable_assignment")
    def statement(self, p):
        return p.variable_assignment

    @_("break_statement")
    def statement(self, p):
        return p.break_statement

    @_("for_loop")
    def statement(self, p):
        return p.for_loop

    @_("delete_statement")
    def statement(self, p):
        return p.delete_statement

    @_("return_statement")
    def statement(self, p):
        return p.return_statement

    @_("variable_operation")
    def statement(self, p):
        return p.variable_operation

    @_("import_statement")
    def statement(self, p):
        return p.import_statement


    @_("sandbox")
    def statement(self, p):
        return p.sandbox

    # Statements END
    ###########################################################################
    # Statment syntax START

    @_("LIMPORT expression ';'")
    def sandbox(self, p):
        return ("LIMPORT", {"EXPRESSION": p.expression}, p.lineno)

    @_("SANDBOX '{' program '}'")
    def sandbox(self, p):
        return ("SANDBOX", {"PROGRAM": p.program}, p.lineno)

    @_("function_call ';'")
    def function_call_statement(self, p):
        return p.function_call

    @_("python_code ';'")
    def python_code_statement(self, p):
        return p.python_code

    @_("BREAK ';'")
    def break_statement(self, p):
        return ("BREAK", p.lineno)
    
    @_("SKIP ';'")
    def break_statement(self, p):
        return ("SKIP", p.lineno)
    
    @_("DEBUG ';'")
    def break_statement(self, p):
        return ("DEBUG", p.lineno)

    @_("RETURN expression ';'")
    def return_statement(self, p):
        return ("RETURN", {"EXPRESSION": p.expression}, p.lineno)

    @_("expression '(' function_arguments ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": p.function_arguments, "ID": p.expression},
            p.lineno,
        )

    @_("expression '(' function_arguments ')' FARROW '{' program '}'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": p.function_arguments, "ID": p.expression,
             "ONCOMPLETE": p.program},
            p.lineno,
        )
    
    @_("'?' expression")
    def debug_call(self, p):
        return (
            "DEBUG_CALL",
            {"VALUE": {}},
            p.lineno,
        )

    @_("expression '(' empty ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": {}, "ID": p.expression},
            p.lineno,
        )
    
    @_("'#' ID expression")
    def function_call(self, p):
        return (
            "COMPILER",
            {   
                "KEY": p.ID,
                "VALUE": p.expression
            },
            p.lineno,
        )
    
    @_("'#' DEPENDS expression")
    def function_call(self, p):
        return (
            "DEPENDS",
            {
                "TO": p.expression
            },
            p.lineno,
        )
    
    @_("ID TARROW ID")
    def function_call(self, p):
        return (
            "NEWOBJECT",
            {
                "FROM": p.ID0, 
                "TO": p.ID1
            },
            p.lineno,
        )

    @_("'[' HEX ',' ID ']' '=' HEX ';'")
    def variable_assignment(self, p):
        return (
            "ADVANCED_WRITE",
            {"ID": p.ID, "ADDR":p.HEX0, "VALUE": p.HEX1},
            p.lineno,
        )
    
    @_("'<' ID '>' expression")
    def function_call(self, p):
        return (
            "TYPECONVERT",
            {
                "VAR": p.expression, 
                "TO": p.ID
            },
            p.lineno,
        )


    @_("expression '(' empty ')' FARROW '{' program '}'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {
                "FUNCTION_ARGUMENTS": {},
                "ID": p.expression,
                "ONCOMPLETE": p.program
            },
            p.lineno,
        )
    
    @_("'.' ENV '{' program '}'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            { 'FUNCTION_ARGUMENTS': {'POSITIONAL_ARGS': (('NULL', 'NULL'),)},
                "ID": ('ID', {'VALUE':'void'}),
                "ONCOMPLETE": p.program
            },
            p.lineno,
        )
    
    @_("'.' ENV FROM ID '{' program '}'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            { 'FUNCTION_ARGUMENTS': {'POSITIONAL_ARGS': (('NULL', 'NULL'),)},
                "ID": ('ID', {'VALUE':'void'}),
                "ONCOMPLETE": p.program,
                "ENV_FROM": p.ID
            },
            p.lineno,
        )

    @_("FUNC ID '(' function_arguments ')' expression '{' program '}'")
    def function_declaration(self, p):
        return (
            "FUNCTION_DECLARATION",
            {
                "FUNCTION_ARGUMENTS": p.function_arguments,
                "ID": p.ID,
                "PROGRAM": p.program,
                "RETURNS_TYPE": p.expression
            },
            p.lineno,
        )

    @_("FUNC ID COLON_COLON ID '(' function_arguments ')' '{' program '}' TARROW expression")
    def function_declaration(self, p):
        return (
            "FUNCTION_DECLARATION",
            {
                "FUNCTION_ARGUMENTS": p.function_arguments,
                "NAMESPACE": p.ID0,
                "ID": p.ID1,
                "PROGRAM": p.program,
                "RETURNS_TYPE": p.expression
            },
            p.lineno,
        )
    
    @_("FUNC ID COLON_COLON ID '(' empty ')' '{' program '}' TARROW expression")
    def function_declaration(self, p):
        return (
            "FUNCTION_DECLARATION",
            {"FUNCTION_ARGUMENTS": {}, "ID": p.ID1, "PROGRAM": p.program, "NAMESPACE": p.ID0,
                "RETURNS_TYPE": p.expression},
            p.lineno,
        )

    @_("FUNC ID '(' empty ')' expression '{' program '}'")
    def function_declaration(self, p):
        return (
            "FUNCTION_DECLARATION",
            {"FUNCTION_ARGUMENTS": {}, "ID": p.ID, "PROGRAM": p.program,
                "RETURNS_TYPE": p.expression},
            p.lineno,
        )

    @_("positional_args")
    def function_arguments(self, p):
        return {"POSITIONAL_ARGS": p.positional_args}

    @_("positional_args ',' kwargs")
    def function_arguments(self, p):
        return {"POSITIONAL_ARGS": p.positional_args, "KWARGS": p.kwargs}

    @_("kwargs")
    def function_arguments(self, p):
        return {"KWARGS": p.kwargs}

    @_("CLASS ID '{' program '}'")
    def class_declaration(self, p):
        return ("CLASS_DECLARATION", {"ID": p.ID, "PROGRAM": p.program}, p.lineno)

    @_("NAMESPACE ID '{' program '}'")
    def class_declaration(self, p):
        return ("CLASS_DECLARATION", {"ID": p.ID, "PROGRAM": p.program}, p.lineno)

    @_("'#' EMBED '[' ID ']' string")
    def class_declaration(self, p):
        return ("EMBED", {"ID": p.ID, "CODE": p.string}, p.lineno)

    @_("FOR expression IN expression '{' program '}'")
    def for_loop(self, p):
        return (
            "FOR",
            {
                "PROGRAM": p.program,
                "VARIABLE": p.expression0,
                "ITERABLE": p.expression1,
            },
            p.lineno,
        )
    
    @_("'!' FOR expression IN expression '{' program '}'")
    def for_loop(self, p):
        return (
            "FOR_COMP",
            {
                "PROGRAM": p.program,
                "VARIABLE": p.expression0,
                "ITERABLE": p.expression1,
            },
            p.lineno,
        )

    @_("WHILE '(' expression ')' '{' program '}'")
    def while_loop(self, p):
        return ("WHILE", {"PROGRAM": p.program, "CONDITION": p.expression}, p.lineno)

    @_("positional_args ',' expression")
    def positional_args(self, p):
        return p.positional_args + (p.expression,)

    @_("expression")
    def positional_args(self, p):
        return (p.expression,)

    @_("kwargs ',' id '=' expression")
    def kwargs(self, p):
        return p.kwargs + ({"ID": p.id, "EXPRESSION": p.expression},)

    @_("ID '=' expression")
    def kwargs(self, p):
        return ({"ID": p.ID, "EXPRESSION": p.expression},)

    
    @_("ID ID '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "VARIABLE_ASSIGNMENT",
            {"ID": p.ID1, "TYPE":p.ID0, "EXPRESSION": p.expression},
            p.lineno,
        )

    @_("ID '<' ID '>' ID '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "VARIABLE_ASSIGNMENT",
            {"ID": p.ID2, "TYPE":p.ID0, "SUBTYPE":p.ID1, "EXPRESSION": p.expression},
            p.lineno,
        )
    
    @_("ID '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "VARIABLE_REASSIGNMENT",
            {"ID": p.ID, "EXPRESSION": p.expression},
            p.lineno,
        )
    
    @_("'@' ID ID '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "VARIABLE_ASSIGNMENT",
            {"ID": p.ID1, "TYPE_CLASS":p.ID0, "EXPRESSION": p.expression},
            p.lineno,
        )


    @_("get_index '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "VARIABLE_REASSIGNMENT_AT_INDEX",
            {"ID": p.get_index, "EXPRESSION": p.expression},
            p.lineno,
        )

    @_("ID EQ_ADD expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.ID, "EXPRESSION": p.expression, "OPERATION": "ADD"},
            p.lineno,
        )

    @_("get_index EQ_ADD expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.get_index, "EXPRESSION": p.expression, "OPERATION": "ADD"},
            p.lineno,
        )

    @_("ID EQ_SUB expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.ID, "EXPRESSION": p.expression, "OPERATION": "SUB"},
            p.lineno,
        )

    @_("get_index EQ_SUB expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.get_index, "EXPRESSION": p.expression, "OPERATION": "SUB"},
            p.lineno,
        )

    @_("ID EQ_MUL expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.ID, "EXPRESSION": p.expression, "OPERATION": "MUL"},
            p.lineno,
        )

    @_("get_index EQ_MUL expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.get_index, "EXPRESSION": p.expression, "OPERATION": "MUL"},
            p.lineno,
        )

    @_("ID EQ_MOD expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.ID, "EXPRESSION": p.expression, "OPERATION": "MOD"},
            p.lineno,
        )

    @_("get_index EQ_MOD expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.get_index, "EXPRESSION": p.expression, "OPERATION": "MOD"},
            p.lineno,
        )

    @_("ID EQ_DIV expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.ID, "EXPRESSION": p.expression, "OPERATION": "DIV"},
            p.lineno,
        )

    @_("get_index EQ_DIV expression ';'")
    def variable_operation(self, p):
        return (
            "VARIABLE_OPERATION",
            {"ID": p.get_index, "EXPRESSION": p.expression, "OPERATION": "DIV"},
            p.lineno,
        )

    @_("class_attribute '=' expression ';'")
    def class_attribute_assignment(self, p):
        return (
            "CLASS_ATTRIBUTE_ASSIGNMENT",
            {"CLASS_ATTRIBUTE": p.class_attribute, "EXPRESSION": p.expression},
            p.lineno,
        )

    @_("if_statement")
    def conditional(self, p):
        return (
            "CONDITIONAL",
            {"IF": p.if_statement, "ELSE_IF": (
                None, None), "ELSE": (None, None)},
            p.if_statement[2],
        )

    @_("if_statement else_if_loop")
    def conditional(self, p):
        return (
            "CONDITIONAL",
            {"IF": p.if_statement, "ELSE_IF": p.else_if_loop,
                "ELSE": (None, None)},
            p.if_statement[2],
        )

    @_("if_statement else_if_loop else_statement")
    def conditional(self, p):
        return (
            "CONDITIONAL",
            {"IF": p.if_statement, "ELSE_IF": p.else_if_loop,
                "ELSE": p.else_statement},
            p.if_statement[2],
        )

    @_("if_statement else_statement")
    def conditional(self, p):
        return (
            "CONDITIONAL",
            {"IF": p.if_statement, "ELSE_IF": (
                None, None), "ELSE": p.else_statement},
            p.if_statement[2],
        )

    @_("IF '(' expression ')' '{' program '}'")
    def if_statement(self, p):
        return ("IF", {"CODE": p.program, "CONDITION": p.expression}, p.lineno)

    @_("else_if_loop else_if_statement")
    def else_if_loop(self, p):
        return p.else_if_loop + (p.else_if_statement,)

    @_("else_if_statement")
    def else_if_loop(self, p):
        return ("ELSE_IF", p.else_if_statement)

    @_("ELSE IF '(' expression ')' '{' program '}'")
    def else_if_statement(self, p):
        return ({"CODE": p.program, "CONDITION": p.expression}, p.lineno)

    @_("ELSE '{' program '}'")
    def else_statement(self, p):
        return ("ELSE", {"CODE": p.program}, p.lineno)

    @_("DEL ID ';'")
    def delete_statement(self, p):
        return ("DEL", {"ID": p.ID}, p.lineno)

    @_("IMPORT expression ';'")
    def import_statement(self, p):
        return ("IMPORT", {"EXPRESSION": p.expression}, p.lineno)

    @_("'.' GLOBAL ';'")
    def import_statement(self, p):
        return ("GLOBALS", {"VALUE":""}, p.lineno)
    
    @_("'.' SELFISH ';'")
    def import_statement(self, p):
        return ("SELFISH", {"VALUE":""}, p.lineno)

    # Statment syntax END
    ###########################################################################
    # Expression START

    @_("ID ID")
    def expression(self, p):
        return ("TYPED", {"ID": p.ID1, "TYPE": p.ID0}, p.lineno)
    
    @_("ID ID '[' expression ']'")
    def expression(self, p):
        return ("TYPED_LEN", {"ID": p.ID1, "TYPE": p.ID0, "LEN": p.expression}, p.lineno)
    
    @_("'&' ID")
    def expression(self, p):
        return ("POINTER", {"ID": p.ID}, p.lineno)
    
    @_("'*' ID")
    def expression(self, p):
        return ("RESOLVE", {"ID": p.ID}, p.lineno)

    @_("'-' expression %prec UMINUS")
    def expression(self, p):
        return ("NEG", p.expression)

    @_("'+' expression %prec UPLUS")
    def expression(self, p):
        return ("POS", p.expression)

    @_("expression '+' expression")
    def expression(self, p):
        return ("ADD", p[0], p[2])

    @_("expression '-' expression")
    def expression(self, p):
        return ("SUB", p[0], p[2])

    @_("expression '/' expression")
    def expression(self, p):
        return ("DIV", p[0], p[2])

    @_("expression '*' expression")
    def expression(self, p):
        return ("MUL", p[0], p[2])

    @_("expression '%' expression")
    def expression(self, p):
        return ("MOD", p[0], p[2])

    @_("expression EQEQ expression")
    def expression(self, p):
        return ("EQEQ", p[0], p[2])

    @_("expression NOT_EQEQ expression")
    def expression(self, p):
        return ("NOT_EQEQ", p[0], p[2])

    @_("expression EQ_LESS expression")
    def expression(self, p):
        return ("EQ_LESS", p[0], p[2])

    @_("expression EQ_GREATER expression")
    def expression(self, p):
        return ("EQ_GREATER", p[0], p[2])

    @_("expression '|' expression")
    def expression(self, p):
        return ("OR", p[0], p[2])
    
    @_("expression '^' expression")
    def expression(self, p):
        return ("OR", p[0], p[2])

    @_("expression '&' expression")
    def expression(self, p):
        return ("AND", p[0], p[2])

    @_("'!' expression")
    def expression(self, p):
        return ("NOT", p.expression)

    @_("expression '<' expression")
    def expression(self, p):
        return ("LESS", p[0], p[2])

    @_("expression '>' expression")
    def expression(self, p):
        return ("GREATER", p[0], p[2])
    
    @_("expression '<' '<' expression")
    def expression(self, p):
        return ("LEFT_SHIFT", p[0], p[3])
    
    @_("expression '>' '>' expression")
    def expression(self, p):
        return ("RIGHT_SHIFT", p[0], p[3])

    @_("'(' expression ')'")
    def expression(self, p):
        return p.expression

    @_("python_code")
    def expression(self, p):
        return p.python_code

    @_("function_call")
    def expression(self, p):
        return p.function_call

    @_("get_index")
    def expression(self, p):
        return p.get_index

    @_("null")
    def expression(self, p):
        return p.null

    @_("int")
    def expression(self, p):
        return p.int

    @_("hex")
    def expression(self, p):
        return p.hex

    @_("float")
    def expression(self, p):
        return p.float

    @_("bool")
    def expression(self, p):
        return p.bool

    @_("string")
    def expression(self, p):
        return p.string

    @_("id")
    def expression(self, p):
        return p.id

    @_("class_attribute")
    def expression(self, p):
        return p.class_attribute

    @_("_tuple")
    def expression(self, p):
        return p._tuple

    @_("_list")
    def expression(self, p):
        return p._list

    @_("_numpy")
    def expression(self, p):
        return p._numpy

    @_("assoc_array")
    def expression(self, p):
        return p.assoc_array

    # Expression END
    ###########################################################################
    # Intermediate expression START

    @_("NULL")
    def null(self, p):
        return ("NULL", "NULL")

    @_("expression '[' expression ']'")
    def get_index(self, p):
        return ("GET_INDEX", {"EXPRESSION": p.expression0, "INDEX": p.expression1}, p.lineno)

    @_("'{' positional_args '}'")
    def _tuple(self, p):
        return ("TUPLE", {"ITEMS": p.positional_args})

    @_("'{' positional_args ',' '}'")
    def _tuple(self, p):
        return ("TUPLE", {"ITEMS": p.positional_args})

    @_("'[' positional_args ']'")
    def _list(self, p):
        return ("LIST", {"ITEMS": p.positional_args})

    @_("'[' positional_args ',' ']'")
    def _list(self, p):
        return ("LIST", {"ITEMS": p.positional_args})

    @_("'(' items ')'")
    def _numpy(self, p):
        return ("NUMPY", {"ITEMS": p.items})

    @_("'(' items ',' ')'")
    def _numpy(self, p):
        return ("NUMPY", {"ITEMS": p.items})

    @_("'(' expression ',' ')'")
    def _numpy(self, p):
        return ("NUMPY", {"ITEMS": (p.expression,)})

    @_("'(' ')'")
    def _numpy(self, p):
        return ("NUMPY", {"ITEMS": ()})

    @_("'(' ',' ')'")
    def _numpy(self, p):
        return ("NUMPY", {"ITEMS": ()})

    @_("items ',' expression")
    def items(self, p):
        return p.items + (p.expression,)

    @_("expression ',' expression")
    def items(self, p):
        return (p.expression,)

    @_("INT")
    def int(self, p):
        return ("INT", {"VALUE": p.INT})

    @_("HEX")
    def hex(self, p):
        return ("HEX", {"VALUE": p.HEX})

    @_("STRING")
    def string(self, p):
        return ("STRING", {"VALUE": p.STRING[1:-1]})

    @_("FLOAT")
    def float(self, p):
        return ("FLOAT", {"VALUE": p.FLOAT})

    @_("TRUE")
    def bool(self, p):
        return ("BOOL", {"VALUE": p.TRUE})

    @_("FALSE")
    def bool(self, p):
        return ("BOOL", {"VALUE": p.FALSE})

    @_("expression COLON_COLON ID")
    def class_attribute(self, p):
        return ("CLASS_ATTRIBUTE", {"CLASS": p[0], "ATTRIBUTE": p[2]}, p.lineno)

    @_("ID")
    def id(self, p):
        return ("ID", {"VALUE": p.ID}, p.lineno)

    @_(r"'{' assoc_array_items '}'")
    def assoc_array(self, p):
        return ("ASSOC_ARRAY", {"ITEMS": p.assoc_array_items})

    @_("assoc_array_items ',' expression ':' expression")
    def assoc_array_items(self, p):
        return p.assoc_array_items + ((p.expression0, p.expression1),)

    @_("expression ':' expression")
    def assoc_array_items(self, p):
        return ((p.expression0, p.expression1),)

    @_("PYTHON_CODE")
    def python_code(self, p):
        return ("PYTHON_CODE", {"CODE": p.PYTHON_CODE[2:-1]})

    @_("PYTHON_CODE_EXEC")
    def python_code(self, p):
        return ("PYTHON_CODE_EXEC", {"CODE": p.PYTHON_CODE_EXEC[3:-1]})

    @_("%prec EMPTY")
    def empty(self, p):
        pass

    # Intermediate expression END
    ###########################################################################
    # Syntax error START