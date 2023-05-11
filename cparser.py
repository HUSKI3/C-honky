from sly import Parser
from sly.yacc import YaccProduction, YaccSymbol
import logging
from rich import print as pprint
from rich.syntax import Syntax
from lexer import ChLexer

ERROR_COUNT = 0

class ChParser(Parser):
    def __init__(self, filename) -> None:
        self.filename = filename
        super().__init__()

    def parse(self, tokens, task = None, progress = None, tasklen=100):
        '''
        Parse the given input tokens.
        '''
        lookahead = None                                  # Current lookahead symbol
        lookaheadstack = []                               # Stack of lookahead symbols
        actions = self._lrtable.lr_action                 # Local reference to action table (to avoid lookup on self.)
        goto    = self._lrtable.lr_goto                   # Local reference to goto table (to avoid lookup on self.)
        prod    = self._grammar.Productions               # Local reference to production list (to avoid lookup on self.)
        defaulted_states = self._lrtable.defaulted_states # Local reference to defaulted states
        pslice  = YaccProduction(None)                    # Production object passed to grammar rules
        errorcount = 0                                    # Used during error recovery

        # Set up the state and symbol stacks
        self.tokens = tokens
        self.statestack = statestack = []                 # Stack of parsing states
        self.symstack = symstack = []                     # Stack of grammar symbols
        pslice._stack = symstack                          # Associate the stack with the production
        self.restart()

        # Set up position tracking
        track_positions = False
        if not hasattr(self, '_line_positions'):
            self._line_positions = { }           # id: -> lineno
            self._index_positions = { }          # id: -> (start, end)

        errtoken   = None                                 # Err token
        while True:
            # Update our task
            if task and progress:
                progress.update(task, advance=tasklen)

            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer
            if self.state not in defaulted_states:
                if not lookahead:
                    if not lookaheadstack:
                        lookahead = next(tokens, None)  # Get the next token
                    else:
                        lookahead = lookaheadstack.pop()
                    if not lookahead:
                        lookahead = YaccSymbol()
                        lookahead.type = '$end'
                    
                # Check the action table
                ltype = lookahead.type
                t = actions[self.state].get(ltype)
            else:
                t = defaulted_states[self.state]

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    self.state = t

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount:
                        errorcount -= 1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    self.production = p = prod[-t]
                    pname = p.name
                    plen  = p.len
                    pslice._namemap = p.namemap

                    # Call the production function
                    pslice._slice = symstack[-plen:] if plen else []

                    sym = YaccSymbol()
                    sym.type = pname       
                    value = p.func(self, pslice)
                    if value is pslice:
                        value = (pname, *(s.value for s in pslice._slice))

                    sym.value = value
                        
                    # Record positions
                    if track_positions:
                        if plen:
                            sym.lineno = symstack[-plen].lineno
                            sym.index = symstack[-plen].index
                            sym.end = symstack[-1].end
                        else:
                            # A zero-length production  (what to put here?)
                            sym.lineno = None
                            sym.index = None
                            sym.end = None
                        self._line_positions[id(value)] = sym.lineno
                        self._index_positions[id(value)] = (sym.index, sym.end)
                            
                    if plen:
                        del symstack[-plen:]
                        del statestack[-plen:]

                    symstack.append(sym)
                    self.state = goto[statestack[-1]][pname]
                    statestack.append(self.state)
                    continue

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n, 'value', None)
                    return result

            if t is None:
                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = ERROR_COUNT
                    self.errorok = False
                    if lookahead.type == '$end':
                        errtoken = None               # End of file!
                    else:
                        errtoken = lookahead

                    tok = self.error(errtoken)
                    if tok:
                        # User must have done some kind of panic
                        # mode recovery on their own.  The
                        # returned token is the next lookahead
                        lookahead = tok
                        self.errorok = True
                        continue
                    else:
                        # If at EOF. We just return. Basically dead.
                        if not errtoken:
                            return
                else:
                    # Reset the error count.  Unsuccessful token shifted
                    errorcount = ERROR_COUNT

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    self.state = 0
                    # Nuke the lookahead stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue

                    # Create the error symbol for the first time and make it the new lookahead symbol
                    t = YaccSymbol()
                    t.type = 'error'

                    if hasattr(lookahead, 'lineno'):
                        t.lineno = lookahead.lineno
                    if hasattr(lookahead, 'index'):
                        t.index = lookahead.index
                    if hasattr(lookahead, 'end'):
                        t.end = lookahead.end
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    sym = symstack.pop()
                    statestack.pop()
                    self.state = statestack[-1]
                continue

            # Call an error function here
            raise RuntimeError('sly: internal parser error!!!\n')

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


#########################################################################################################

    @_("expression '(' function_arguments ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": p.function_arguments, "ID": p.expression},
            p.lineno,
        )

    @_("expression '(' empty ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": {}, "ID": p.expression},
            p.lineno,
        )

# NAMESPACED?
    @_("expression ':' ':' expression '(' function_arguments ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": p.function_arguments, "ID": p.expression1, "NAMESPACE": p.expression0},
            p.lineno,
        )

    @_("expression ':' ':' expression '(' empty ')'")
    def function_call(self, p):
        return (
            "FUNCTION_CALL",
            {"FUNCTION_ARGUMENTS": {}, "ID": p.expression1, "NAMESPACE": p.expression0},
            p.lineno,
        )


#########################################################################################################

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
    
    @_("GOTO ID")
    def function_call(self, p):
        return (
            "GOTO",
            {   
                "ID": p.ID,
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

    @_("'[' HEX ',' ID ']' '=' expression ';'")
    def variable_assignment(self, p):
        return (
            "ADVANCED_WRITE",
            {"ID": p.ID, "ADDR":p.HEX, "VALUE": p.expression},
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
    
    @_("ID '+' '+' ';'")
    def variable_assignment(self, p):
        return (
            "INCREMENT",
            {
                "VAR": p.ID
            },
            p.lineno,
        )
    
    @_("ID '-' '-' ';'")
    def variable_assignment(self, p):
        return (
            "DECREMENT",
            {
                "VAR": p.ID
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
    
    @_("'#' EMBED '[' ID ',' ID ']' string")
    def class_declaration(self, p):
        return ("EMBED", {"ID": p.ID0, "TO":p.ID1, "CODE": p.string}, p.lineno)

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

    @_("ID ID '=' '[' HEX ',' ID ']' ';'")
    def variable_assignment(self, p):
        return (
            "ADVANCED_READ",
            {"ID": p.ID1, "TYPE": p.ID0, "HOW":p.ID2, "ADDR":p.HEX},
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

    @_("'?' '!'")
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

    @_("'*' ID '=' expression ';'")
    def statement(self, p):
        return ("SET_PTR", {"ID": p.ID, "EXPRESSION": p.expression}, p.lineno)

    # Statment syntax END
    ###########################################################################
    # Expression START

    @_("ID ID")
    def expression(self, p):
        return ("TYPED", {"ID": p.ID1, "TYPE": p.ID0}, p.lineno)
    
    @_("ID ID '[' expression ']'")
    def expression(self, p):
        return ("TYPED_LEN", {"ID": p.ID1, "TYPE": p.ID0, "LEN": p.expression}, p.lineno)

    @_("ID '<' ID '>' ID '[' expression ']'")
    def expression(self, p):
        return ("TYPED_TYPED_LEN", {"ID": p.ID2, "TYPE": p.ID0, "SUBTYPE": p.ID1, "LEN": p.expression}, p.lineno)
    
    @_("'&' ID")
    def expression(self, p):
        return ("POINTER", {"ID": p.ID}, p.lineno)
    
    @_("'*' ID")
    def expression(self, p):
        return ("DEREF", {"ID": p.ID}, p.lineno)

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
        return ("XOR", p[0], p[2])

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

    @_("CHAR")
    def string(self, p):
        return ("CHAR", {"VALUE": p.CHAR[1:-1]})

    @_("FLOAT")
    def float(self, p):
        return ("FLOAT", {"VALUE": p.FLOAT})

    @_("TRUE")
    def bool(self, p):
        return ("BOOL", {"VALUE": p.TRUE})

    @_("FALSE")
    def bool(self, p):
        return ("BOOL", {"VALUE": p.FALSE})

    @_("'!' expression '?' ID")
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

    def error(self, p):
        if p:
            pprint(f"[red bold]Syntax error at line {p.lineno} [/red bold]")

            with open(self.filename, "r") as f:
                line_affected = f.readlines()[p.lineno]

            pretty = Syntax(
                line_affected,
                "Rust", 
                padding=1, 
                line_numbers=True
            )
            pprint(pretty)
            quit(1)
        else:
            print("Syntax error at EOF")