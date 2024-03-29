from exceptions import ModuleExceptions, TranspilerExceptions
from chonkytypes import String, Char, Int8, Pointer, Int32, HexInt32, ID, List
from compiler import * # For the Compiler class autocomplete
from numba import jit, njit

import pprint

from lexer import ChLexer
from cparser import ChParser
pprint = pprint.PrettyPrinter(indent=2).pprint
from rich.console import Console
from rich.syntax import Syntax
console = Console()

o_isinstance = isinstance

def isinstance(o1, o2):
    if o_isinstance(o1, HexInt32) and o2==Int32\
        or o_isinstance(o2, HexInt32) and o1==Int32:
        return True
    elif o_isinstance(o1, o2):
        return True
    else:
        return False

def rprint(data):
    console.print(
        Syntax(
            str(data),
            "Python", 
            padding=1, 
            line_numbers=True
        )
    )

class Module:
    BUILT_TYPE = str
    class MODULE_TYPES:
        '''
        FUNCTION -> Function module type
        ACTION   -> Internal action used in processing
        '''
        FUNCTION = "Function" 
        ACTION   = "Action"
        SPECIAL_ACTION = "Special Action"
        SPECIAL_ACTION_FUNC = "Special Action Function"

    def __init__(
        self,
        #type: MODULE_TYPES
    ):
        self.type = "Unknown"
        self.built = ""
        self.template = ""
        self.o1 = False
        self.o2 = False
        self.o3 = False

    def __call__(
        self,
        tree,
        no_construct = False,
        op: int = 1
    ):
        if op == 1:
            self.o1 = True
        elif op == 2:
            self.o2 = True
        elif op == 3:
            self.o3 = True

        _values = self.proc_tree(tree)
        self.override()
        if not no_construct:
            return self._constructor(_values)
        else:
            return _values
    
    # Future
    #def optimise(self): pass
    optimise = None

    # Future: Return true for now
    def verify(self): return True

    def override(self):
        """
        Warning: this should be used with caution since it bypasses the default build structure
        """
        pass

    # Implemented in module child
    def proc_tree(self, tree) -> dict: "Return a dict containing values processed from the tree"

    # Format assembly
    def _constructor(
        self,
        arguments: dict
    ) -> BUILT_TYPE:
        if arguments == None:
            raise ModuleExceptions.InvalidModuleConstruction(self)
        try:
            return self.template.format(
                    **arguments
                )
        except Exception:
            raise Exception(f"In '{self.name}' - Failed to unpack elements. Perhaps you need to set `no_construct` to True to avoid this module's construction?")

class PutCharMod(Module):
    name="putchar"
    type=Module.MODULE_TYPES.FUNCTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.compiler_instance = compiler_instance

        self.raw_template = '''
        ; load {arg}
        ldr r20, #{arg}
        '''

        self.var_template = '''
        ; load action cmemb
        ldr r1, .cmemb
        ; {arg} is at {pos}
        ldr r11, {pos}
        ; load from {pos}
        ldr r0, $2
        jpr r1
        '''

        self.template = '''
        ; PUTCHAR
        {method}
        
        ; output
        ldr r5, FFFF0000
        stb r20, r5
        '''
    
    def proc_tree(self, tree):
        #pprint(tree)
        # Resolve arguments
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')
        arguments = [resolution_module(arg, no_construct=True) for arg in tree]

        final = ""

        # 0 is the var or val
        varval = arguments[0]

        if isinstance(varval, ID):
            pos = self.compiler_instance.get_variable(varval.value)['pos']

            final = self.var_template.format(
                arg = varval.value,
                pos = pos
            )
        else:
            # Assume we are handling a raw value
            if isinstance(varval, Char):
                val = str(varval.value) # Raw value must be denoted as int
            else:
                raise Exception(f"[PUTCHAR] Invalid type supplied, Got: {type(varval)} Expected: 'Char()'")

            final = self.raw_template.format(arg = val)

        return {"method": final}
    
    @jit()
    def optimise(self):
        return 2+2

class ResolutionMod(Module):
    name="RESOLUT"
    type = Module.MODULE_TYPES.ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.compiler_instance = compiler_instance
    
    def proc_tree(self, tree):
        #pprint(tree)
        
        if tree[0] == 'STRING':
            if len(tree[1]['VALUE']) == 1:
                return Char(tree[1]['VALUE'])
            else:
                return List(
                    values = list(tree[1]['VALUE']),
                    type=Char
                )

        elif tree[0] == 'INT':
            return Int32(tree[1]['VALUE'])

        elif tree[0] == 'HEX':
            return HexInt32(tree[1]['VALUE'])

        elif tree[0] == 'CHAR':
            # if the actual type is string, there will be an array in place of the value
            if type(tree[1]['VALUE']) == tuple:
                return Char(tree[1]['VALUE'][0])
            else:
                return Char(tree[1]['VALUE'])
        
        elif tree[0] == 'ID':
            return ID(tree[1]['VALUE'])
        
        elif tree[0] == 'POINTER':
            return Pointer(tree[1]['ID'])

        raise Exception(f"[RESOLUT] Failed to match {tree} is '{tree[0]}' supported?")
    

class FunctionCallMod(Module):
    name="FUNCTION_CALL"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.standard = """
        ; Calling {func}
        ldr r0, $3
        ldr r23, .{func}
        jpr r23
        """

        self.template = """
        ; FUNCTION_CALL
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):
        #pprint(tree)
        
        namespace = None
        funcname = tree['ID'][1]['VALUE']
        arguments = tree['FUNCTION_ARGUMENTS']

        # console.log(f"[FunctionCallMod] {funcname}({arguments})")

        # Check if the function is defined already
        if funcname in self.compiler_instance.functions or "NAMESPACE" in tree:
            # elif funcname is in an namespaced instance
            if "NAMESPACE" in tree:
                namespace = tree["NAMESPACE"][1]['VALUE']

                if namespace not in self.compiler_instance.namespaces:
                    raise TranspilerExceptions.NamespaceNotFound(namespace, self.compiler_instance.namespaces)

                namespace_instance: Compiler = self.compiler_instance.namespaces[namespace]["object"]

                if funcname not in namespace_instance.functions:
                    print(self.compiler_instance.functions)
                    raise TranspilerExceptions.UnkownMethodReference(funcname)

                func = namespace_instance.functions[funcname]
                func_instance = namespace_instance.functions[funcname]['object']
                # Update instance locals
                # func_instance.variables = {**func_instance.variables, **self.compiler_instance.variables }
                # print(self.compiler_instance.namespace)

            else:
                # Check if the function is a builtin module
                func  = self.compiler_instance.functions[funcname]
                if isinstance(func, Module):
                    func: Module
                    # console.log(f"\tModule callback matched, requesting build (optimisation {'enabled' if func.optimise is not None else 'not available'})")

                    # Request build
                    built = func(arguments['POSITIONAL_ARGS'])
                    return {"built": built}
                else:
                    
                    # Get the function's compiler instance
                    func_instance: Compiler = self.compiler_instance.functions[funcname]['object']
                    # Update instance locals
                    func_instance.variables = {**func_instance.variables, **self.compiler_instance.variables }

            # Dependencies
            resolution_module: Module = func_instance.get_action('RESOLUT')
            reassign_module: VariableReAssignMod = func_instance.get_action('VARIABLE_REASSIGNMENT')
            assign_module: VariableAssignMod = func_instance.get_action('VARIABLE_ASSIGNMENT')


            if arguments:
                arguments = arguments['POSITIONAL_ARGS']

                # Process supplied arguments
                for i, arg in enumerate(func_instance.arguments):
                    try:
                        current_supplied_raw = arguments[i]
                    except IndexError:
                        print(f"IndexError at '{i}:{funcname}'. Arguments content:{arguments}. Exepcted:{func_instance.arguments.keys()}")

                        quit(1)
                    name = arg
                    argtype = func_instance.arguments[arg]['type']
                    pos  = func_instance.arguments[arg]['pos']

                    current_supplied = resolution_module(current_supplied_raw, no_construct=True)
                    
                    # # Debug
                    # print(current_supplied)
                    # print(name, argtype, pos)
                    # #

                    if isinstance(current_supplied, ID):
                        var_name = current_supplied.value
                        var_obj = self.compiler_instance.get_variable(var_name)
                        var_type = var_obj['type']

                        if type(var_type) != type(argtype):
                            raise TranspilerExceptions.TypeMissmatch(
                                name,
                                var_type,
                                argtype,
                                tree['ID'][-1]
                            )

                        if isinstance(var_type, List):
                            for i, item in enumerate(var_obj['object'].values):
                                # Construct new tree
                                new_tree = {
                                    'ID': f"{name}_{i}", 
                                    'EXPRESSION': item
                                    }

                                # Reassign value
                                new_value_for_var = reassign_module(
                                    new_tree,
                                    redirect=True
                                )

                                # Append to instance finals
                                self.compiler_instance.finished.append(
                                    new_value_for_var
                                )
                        else:
                            # Construct new tree
                            new_tree = {
                                'ID': name, 
                                'EXPRESSION': current_supplied_raw
                                }
                            if namespace is not None:
                                # Reassign value
                                new_value_for_var = reassign_module(
                                    new_tree,
                                    redirect=True,
                                    from_pos = var_obj['pos'],
                                    from_var = var_obj
                                )
                                # print(f"NAMESPACE {var_name} {var_obj['pos']} -> {name} {pos}")
                            else:
                                # Reassign value
                                new_value_for_var = reassign_module(
                                    new_tree,
                                    redirect=True
                                )
                            # print(new_value_for_var)

                            # Append to instance finals
                            self.compiler_instance.finished.append(
                                new_value_for_var
                            )
                    elif isinstance(current_supplied, List):
                        for i, item in enumerate(current_supplied.values):
                            # Construct new tree
                            new_tree = {
                                'ID': f"{name}_{i}", 
                                'EXPRESSION': (current_supplied.type.abbr_name.upper(), {'VALUE':item})
                                }
                            # Reassign value
                            new_value_for_var = reassign_module(
                                new_tree,
                                redirect=True
                            )

                            # Append to instance finals
                            self.compiler_instance.finished.append(
                                new_value_for_var
                            )
                    else:
                        # Check the type of the supplied argument
                        if not isinstance(current_supplied, argtype):
                            raise TranspilerExceptions.TypeMissmatch(
                                name,
                                current_supplied,
                                argtype,
                                tree['ID'][-1]
                            )
                        
                        # Hacky
                        if type(argtype) != str:
                            argtype = argtype.abbr_name
                        
                        # Construct new tree
                        new_tree = {
                            'ID': name, 
                            'EXPRESSION': (
                                argtype.upper(), 
                                {
                                    'VALUE': current_supplied.value
                                }
                                )
                            }

                        # Reassign value
                        new_value_for_var = reassign_module(
                            new_tree,
                            redirect=True
                        )

                        # Append to instance finals
                        self.compiler_instance.finished.append(
                            new_value_for_var
                        )
            
            built = self.standard.format(
                func = funcname
            )
        else:
            raise TranspilerExceptions.UnkownMethodReference(funcname)

        return {"built":built}

class FunctionDecMod(Module):
    name="FUNCTION_DECLARATION"
    type = Module.MODULE_TYPES.SPECIAL_ACTION_FUNC

    def __init__(self, compiler_instance):
        super().__init__()

        self.func_template = """
        ; FUNCTION {name} TAKES {items}
        .{name}
            ; set r1 action to lmemw
            ldr r1, .lmemw
            ; Set ret to r0
            ldr r11, {ret_pos}
            mov r20, r0
            ldr r0, $2
            jpr r1
            ; BODY
            {program}
            ; BODY END
            ; set r1 action to cmemw
            ldr r1, .cmemw
            ; Load return position
            ldr r11, {ret_pos}
            ; load from return addr
            ldr r0, $2
            jpr r1
            jpr r20
        ; END FUNCTION {name}
        """

        self.template = """
        ; FUNCTION_DECLARATION
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):

        line = tree['RETURNS_TYPE'][-1]

        funcname = tree['ID']
        arguments = tree['FUNCTION_ARGUMENTS']
        program  = tree['PROGRAM']
        returns  = tree['RETURNS_TYPE'][1]['VALUE']

        if arguments:
            arguments = arguments['POSITIONAL_ARGS']
        
        # console.log(f"[FunctionDecMod] {funcname}({arguments}) -> {returns}")

        # Need to process the program
        instance = self.compiler_instance.new_instance(
            tree = program,
            variables=self.compiler_instance.variables.copy(),
            functions=self.compiler_instance.functions.copy(),
            inherit=True
        )

        # Local dependency
        cvariable_module: Module = instance.get_action('VARIABLE_ASSIGNMENT')

        # Process variables that the function takes
        processed_arguments = {}
        var_asm = []
        
        if arguments:
            for arg in arguments:
                # Hype
                name = arg[1]['ID']
                type = arg[1]['TYPE']

                if type == 'list':
                    cur_var_asm = cvariable_module(
                        {
                            "ID": name,
                            "TYPE": type,
                            "EXPRESSION": (type.upper(), {"VALUE": "0"}),
                            "LEN": arg[1]['LEN'],
                            "SUBTYPE": arg[1]['SUBTYPE']
                        },
                        op = 2
                    )
                else:
                    cur_var_asm = cvariable_module(
                        {
                            "ID": name,
                            "TYPE": type,
                            "EXPRESSION": (type.upper(), {"VALUE": "0"})
                        }
                    )

                var_asm.append(cur_var_asm)
                var_dict = instance.get_variable(name)

                processed_arguments[name] = var_dict['pos']

                # Save arguments to our instance
                instance.arguments[name] = var_dict
                instance.variables[name] = var_dict

        # Run the instance
        instance.run()

        # Add our constructor to the parent instance
        for asm in var_asm:
            self.compiler_instance.finished.append(asm)

        body = instance.finished

        # Allocate an address to store our return addr
        position = instance.allocate(4)

        built = self.func_template.format(
            name = funcname,
            program = '\n\t\t'.join('\n'.join(body).split('\n')),
            ret_pos = position,
            items = processed_arguments
        )

        self.compiler_instance.create_function(
            funcname,
            instance,
            built
        )

        # Update our primary instance with the 
        # new instance's positions and values
        self.compiler_instance.sync(instance)

        return {"built": built}

class ConditionalMod(Module):
    name="CONDITIONAL"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.standard = """
        ; store jump locations
        ldr r17, ._if_end_{label}
        ldr r16, ._else_end_{label}
        {first}
        ; save value to first var
        mov r26, r20
        {second}
        ; save value to second var
        mov r30, r20
        {comparison}
        
        {code}
        
        ; Jump to ._else_end_{label} if code has been run
        ldr r17, ._if_end_{label}
        ldr r16, ._else_end_{label}
        jpr r16
        ._if_end_{label}
        {else_code}
        ldr r17, ._if_end_{label}
        ldr r16, ._else_end_{label}
        ._else_end_{label}
        """

        self.raw_val_template = '''
        ldr r20, {hex}{val}
        '''

        self.load_var_template = '''
        ; load action for r1 {action}
        ldr r1, .{action}
        ; store var addr
        ldr r11, {addr}
        ; load from var addr
        ldr r0, $2
        jpr r1
        '''

        self.template = """
        ; CONDITIONAL
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')

        if_condition = tree['IF'][1]['CONDITION']
        if_program = tree['IF'][1]['CODE']
        else_pr = None if tree["ELSE"][0] is None else tree["ELSE"]

        # Values are stored at 26 and 30

        conditionals = {
            'EQEQ': 'jprne r17, r26, r30',
            'NOT_EQEQ': 'jpre r17, r26, r30',
            'LESS': 'jprgt r17, r26, r30',
            'GREATER': 'jprlt r17, r26, r30'
        }

        # Resolve condition
        condition = conditionals[if_condition[0]]

        # Get a new label index
        label_index = self.compiler_instance.new_label()

        # Process first and second value
        first = resolution_module(if_condition[1], no_construct=True)
        second = resolution_module(if_condition[2], no_construct=True)

        def get_template(attr):
            if type(attr) == ID:
                attr: ID
                if attr.value not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(
                        attr.value,
                        self.compiler_instance.variables
                    )

                var = self.compiler_instance.get_variable(
                    attr.value
                )

                pos = var['pos']
                read_type = var['type']

                read_actions = {
                    0: 'cmemw',
                    1: 'cmemb',
                    2: 'cmemh',
                    4: 'cmemw'
                }

                template = self.load_var_template.format(
                    action = read_actions[read_type.size],
                    addr = pos
                )
            else:
                if type(attr) == Char:
                    template = self.raw_val_template.format(
                        val = attr.value,
                        hex = '#'
                    )
                else:
                    template = self.raw_val_template.format(
                        val = attr.value,
                        hex = '#'
                    )
            return template

        first_template = get_template(first)
        second_template = get_template(second)
        
        # Need to process the if program
        instance = self.compiler_instance.new_instance(
            tree = if_program,
            variables=self.compiler_instance.variables.copy(),
            functions=self.compiler_instance.functions.copy(),
            inherit=True
        )

        # Run our if program
        instance.run()

        # Syncronize instance
        self.compiler_instance.sync(instance)

        # If else exists
        if else_pr is not None:
            # Need to process the if program
            else_instance = self.compiler_instance.new_instance(
                tree = else_pr[1]['CODE'],
                variables=self.compiler_instance.variables.copy(),
                functions=self.compiler_instance.functions.copy(),
                inherit=True
            )

            # Run our if program
            else_instance.run()

            # Syncronize else_instance
            self.compiler_instance.sync(else_instance)
            else_code = ''.join(else_instance.finished)
        else:
            else_code = '\t\t; No else constructed'

        built = self.standard.format(
            first = first_template,
            second = second_template,
            label = label_index,
            comparison = condition,
            code = ''.join(instance.finished),
            else_code = else_code
        )

        return {"built": built}

class WhileMod(Module):
    name="WHILE"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.standard = """
        ; store jump locations
        ._while_start_{label}
        ldr r17, ._while_end_{label}
        ldr r16, ._while_start_{label}
        {first}
        ; save value to first var
        mov r26, r20
        {second}
        ; save value to second var
        mov r30, r20
        {comparison}
        
        {code}
        
        ; Jump to ._while_end_{label} if code has been run
        ldr r17, ._while_end_{label}
        ldr r16, ._while_start_{label}
        jpr r16
        ._while_end_{label}
        """

        self.raw_val_template = '''
        ldr r20, {hex}{val}
        '''

        self.load_var_template = '''
        ; load action for r1 {action}
        ldr r1, .{action}
        ; store var addr
        ldr r11, {addr}
        ; load from var addr
        ldr r0, $2
        jpr r1
        '''

        self.template = """
        ; CONDITIONAL
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')

        if_condition = tree['CONDITION']
        if_program = tree['PROGRAM']

        # Values are stored at 26 and 30

        conditionals = {
            'EQEQ': 'jprne r17, r26, r30',
            'NOT_EQEQ': 'jpre r17, r26, r30',
            'LESS': 'jprgt r17, r26, r30',
            'GREATER': 'jprlt r17, r26, r30'
        }

        # Resolve condition
        condition = conditionals[if_condition[0]]

        # Get a new label index
        label_index = self.compiler_instance.new_label()

        # Process first and second value
        first = resolution_module(if_condition[1], no_construct=True)
        second = resolution_module(if_condition[2], no_construct=True)

        def get_template(attr):
            if type(attr) == ID:
                attr: ID
                if attr.value not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(
                        attr.value,
                        self.compiler_instance.variables
                    )

                var = self.compiler_instance.get_variable(
                    attr.value
                )

                pos = var['pos']
                read_type = var['type']

                read_actions = {
                    1: 'cmemb',
                    2: 'cmemh',
                    4: 'cmemw'
                }

                template = self.load_var_template.format(
                    action = read_actions[read_type.size],
                    addr = pos
                )
            else:
                if type(attr) == Char:
                    template = self.raw_val_template.format(
                        val = attr.value,
                        hex = '#'
                    )
                else:
                    template = self.raw_val_template.format(
                        val = attr.value,
                        hex = '#'
                    )
            return template

        first_template = get_template(first)
        second_template = get_template(second)
        
        # Need to process the if program
        instance = self.compiler_instance.new_instance(
            tree = if_program,
            variables=self.compiler_instance.variables.copy(),
            functions=self.compiler_instance.functions.copy(),
            inherit=True
        )

        # Run our if program
        instance.run()

        # Syncronize instance
        self.compiler_instance.sync(instance)

        built = self.standard.format(
            first = first_template,
            second = second_template,
            label = label_index,
            comparison = condition,
            code = ''.join(instance.finished)
        )

        return {"built": built}

class ForLoopCompileTimeMod(Module):
    name="FOR_COMP"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.template = """
        ; CONDITIONAL
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')
        cvariable_module: Module = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')
        reassign_module: VariableReAssignMod = self.compiler_instance.get_action('VARIABLE_REASSIGNMENT')

        iterable = tree['ITERABLE']
        var      = tree['VARIABLE']
        program  = tree['PROGRAM']

        var_asm = cvariable_module(
            {
                "ID": var[1]['VALUE'],
                "TYPE": "int",
                "EXPRESSION": ("INT", {"VALUE": "0"})
            }
        )

        self.compiler_instance.finished.append(var_asm)

        iterable_id_obj  = resolution_module(iterable, True)
        iterable_name = iterable_id_obj.value
        iterable_dict = self.compiler_instance.get_variable(iterable_name)
        iterable_obj  = iterable_dict['object']
        iterable_len  = iterable_obj.length

        for x in range(iterable_len):
            # Construct new tree
            new_tree = {
                'ID': var[1]['VALUE'], 
                'EXPRESSION': ("INT", {"VALUE": str(x)})
                }
            # Reassign value
            new_value_for_var = reassign_module(
                new_tree,
                redirect=True
            )

            self.compiler_instance.finished.append(new_value_for_var)

            if program:
                self.compiler_instance.run(program)

        return {"built": "; built"}

class AdvancedWriteMod(Module):
    name="ADVANCED_WRITE"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.template = """
        ; ADVANCED WRITE
        {built}
        """

        self.var_template = '''
            ; Load from {addr} for var {var}
            ldr r11, {addr}
            ldr r0, $3
            ldr r2, .{read_action}
            jpr r2
            mov r{reg}, r20
            '''
        
        '''
        ldr r11, {var_addr}
        ldr r0, $3
        ldr r2, .{read_actions[var_type.size]}
        jpr r2
        '''
        
        self.value_template = '''
            ldr r{reg}, #{val}
            '''

        self.compiler_instance: Compiler = compiler_instance

    def proc_tree(self, tree) -> dict:
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')

        operations = {
                    "ADD": "add",
                    "SUB": "sub",
                    "MUL": "mult",
                    "DIV": "div",
                    "OR":  "or",
                    "XOR": "xor",
                    "AND": "and",
                    "RIGHT_SHIFT": "rsh",
                    "LEFT_SHIFT": "lsh"
                }

        addr = tree['ADDR']
        _type = tree['ID']
        value = tree['VALUE']

        read_actions = {
            1: 'cmemb',
            2: 'cmemh',
            4: 'cmemw'
        }

        if value[0] in operations:
            first  = value[1]
            second = value[2]

            operation = operations[value[0]]
        
            registers = [18, 19]

            # Resolve variables``
            first_res  = resolution_module(first, no_construct=True)
            second_res = resolution_module(second, no_construct=True)

            first_template  = ""
            second_template = ""

            if isinstance(first_res, ID):
                if first_res.value not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(first_res.value, self.compiler_instance.variables)
                var = self.compiler_instance.get_variable(first_res.value)
                var_type = var['type']
                read_action = read_actions[var_type.size]

                first_template = self.var_template.format(
                    addr = var['pos'],
                    var  = first_res.value,
                    read_action = read_action,
                    reg = registers[0]
                )
            elif isinstance(first_res, Int32) or isinstance(first_res, HexInt32):
                first_template = self.value_template.format(
                    reg = registers[0],
                    val = first_res.value
                )
            else:
                raise TranspilerExceptions.TypeMissmatch(first_res.value, first_res, Int32, tree[-1])
            

            if isinstance(second_res, ID):
                if second_res.value not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(second_res.value, self.compiler_instance.variables)
                var = self.compiler_instance.get_variable(second_res.value)
                var_type = var['type']
                read_action = read_actions[var_type.size]
                second_template = self.var_template.format(
                    addr = var['pos'],
                    var = second_res.value,
                    read_action = read_action,
                    reg = registers[1]
                )
            elif isinstance(second_res, Int32) or isinstance(second_res, HexInt32):
                second_template = self.value_template.format(
                    reg = registers[1],
                    val = second_res.value
                )
            else:
                raise TranspilerExceptions.TypeMissmatch(second_res.value, second_res, Int32, tree[-1])

            # print(first_template)
            # print(second_template)

            if operation in ['rsh', 'lsh']:
                if not \
                    (isinstance(second_res, Int32) or isinstance(second_res, HexInt32)) \
                    or \
                    (isinstance(first_res, Int32) or isinstance(first_res, HexInt32)):
                    raise Exception("Can't use variables in a shift")
                math_operation = f"{operation} r{registers[0]}, {second_res.value}"
            else:
                math_operation = f"{operation} r{registers[0]}, r{registers[1]}, r{registers[0]}"

            final_template = f'''
            {first_template}
            {second_template}
            {math_operation}
            ; Store the result
            mov r20, r{registers[0]}
            '''

            template = '''
            ; mathematical advanced write
            {final_template}
            ldr r14, {addr}
    
            {instr}
            '''

        else:
            final_template = ""
            value = resolution_module(value, no_construct=True)

            if isinstance(value, HexInt32):
                value = value.value
                final_template = f'''
                ldr r20, {value}
                '''

            elif isinstance(value, Int32):
                value = value.value
                final_template = f'''
                ldr r20, #{value}
                '''
            
            elif isinstance(value, ID):
                var_obj = self.compiler_instance.get_variable(value.value)
                var_addr = var_obj['pos']
                var_type = var_obj['type']

                final_template = f'''
                ldr r11, {var_addr}
                ldr r0, $3
                ldr r2, .{read_actions[var_type.size]}
                jpr r2
                '''
            
            else:
                raise TranspilerExceptions.TypeMissmatch(value, type(value).__name__, [HexInt32, Int32, ID], 0)

            template = '''
            {final_template}
            ldr r14, {addr}
            {instr}
            '''


        type_instrs = {
            'byte': 'stb r20, r14',
            'half': 'sth r20, r14',
            'word': 'stw r20, r14',
        }

        return {"built": template.format(
                val = value,
                instr = type_instrs[_type],
                addr = addr,
                final_template = final_template
            )}



class EmbedMod(Module):
    name="EMBED"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.template = """
        ; EMBED
        {built}
        """

        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree):

        built = ''

        if tree['ID'] == 'assembly':
            vars = {}
            for var in self.compiler_instance.variables:
                vars[var] = self.compiler_instance.variables[var]['pos']

            built = tree['CODE'][1]['VALUE'].format(**vars)
        elif tree['ID'] == 'ck':
            lexer = ChLexer()
            parser = ChParser(self.compiler_instance.filename)
            file = tree['CODE'][1]['VALUE']

            lexed_tokens = lexer.tokenize(
                open(file, "r").read()
            )
            tree = parser.parse(lexed_tokens)

            instance: Compiler = self.compiler_instance.new_instance(
                tree,
                inherit = True
            )

            instance.run()
            self.compiler_instance.sync(
                instance, 
                passthrough = True
            )
            # print("Compiler sync complete")
            built = f'; Included file {file}'

        else:
            raise TranspilerExceptions.NotImplemented()

        return {"built": built }

class ClassDeclarationMod(Module):
    name="CLASS_DECLARATION"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        self.compiler_instance: Compiler = compiler_instance
    
    def proc_tree(self, tree) -> dict:
        
        namespace_name = tree['ID']
        program = tree['PROGRAM']

        instance: Compiler = self.compiler_instance.new_instance(
            program,
            namespace=namespace_name,
            inherit=True
        )

        instance.run()

        self.compiler_instance.sync(instance, passthrough=True)
        self.compiler_instance.create_namespace(
            namespace_name,
            instance,
            program
        )

        return {"constructor":""}
    

class VariableAssignMod(Module):
    name="VARIABLE_ASSIGNMENT"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.standard = """
        ; {option} for {var} with {action}
        ldr r11, {pos}
        ldr r20, {hex}{value}
        ldr r1, .{action}
        ldr r0, $2
        jpr r1
        """

        self.standard_looped = """
        ; Store position 
        ldr r30, #{times}
        ldr r17, jump_back
        .jump_back
        ; {option} for {var} with {action}
        ldr r11, {pos}
        ldr r20, {hex}{value}
        ldr r1, .{action}
        ldr r0, $2
        jpr r1
        iadd r26, 1
        jprne r17, r26, r30
        """

        self.from_pos_with_var_offset = """
        ; Load offset from other var
        ldr r11, {offset_pos}
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1
        ldr r21, {array_addr}
        imult r20, {byte_length}
        add r20, r21, r20
        ; r20 = offset
        ; r20 is the register to load the value from
        mov r11, r20
        ldr r1, .{read_action}
        ldr 0, $2
        jpr r1
        ; {option} for {var} with {action}
        ldr r11, {pos}
        ldr r1, .{action}
        ldr r0, $2
        jpr r1
        """

        self.to_pos_with_value_offset_with_value = """
        ; Load offset from value
        ldr r20, {offset_hex}{offset_val}
        ldr r21, {array_addr}
        imult r20, {byte_length}
        add r20, r21, r20
        ; r20 is the register to load the value to
        mov r12, r20
        ; Set value
        ldr r20, {hex}{value}
        ; set value r12 -> r11 (Since r12 contains loc)
        mov r11, r12
        ldr r1, .{action}
        ldr 0, $2
        jpr r1
        """

        self.to_pos_with_var_offset_with_value = """
        ; Load offset from var {from_pos}
        ldr r11, {from_pos}
        ldr r1, .{from_action}
        ldr r0, $2
        jpr r1
        ldr r21, {array_addr}
        imult r20, {byte_length}
        add r20, r21, r20
        ; r20 is the register to load the value to
        mov r12, r20
        ; Set value
        ldr r20, {hex}{value}
        ; set value r12 -> r11 (Since r12 contains loc)
        mov r11, r12
        ldr r1, .{action}
        ldr 0, $2
        jpr r1
        """

        self.pointer = """
        ; pointer construction for {var}
        ldr r11, {pos}
        ldr r20, {value}
        stw r20, r11
        """

        self.deref = """
        ; deref for {var}
        ldr r11, {from_pos}
        ldw r20, r11
        mov r11, r20
        ldr r1, .{read_action}
        ldr r0, $2
        jpr r1
        ldr r11, {pos}
        ldr r1, .{load_action}
        ldr r0, $2
        jpr r1
        """

        self.from_pos = """
        ; load value from position {from_pos}
        ldr r11, {from_pos}
        ldr r1, .{from_action}
        ldr r0, $2
        jpr r1
        ; {option} for {var} with {action}
        ldr r11, {pos}
        ldr r1, .{action}
        ldr r0, $2
        jpr r1
        """

        self.math_var_template = '''
            ; Read from {addr} for var {var}
            ldr r1, .{read_action}
            ldr r11, {addr}
            ldr r0, $2
            jpr r1
            mov r{reg}, r20
            '''
        self.math_value_template = '''
            ldr r{reg}, #{val}
            '''

        self.template = """
        {constructor}
        """

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, from_pos=None, from_var=None, custom_pos=None, no_construct=False, no_add=False, op=1):
        # Override the standard call, this let's us feed it another parameter 
        self.custom_pos = custom_pos
        self.from_pos_flag = from_pos
        self.from_var = from_var
        self.no_add = no_add
        initial = super().__call__(tree, no_construct, op=op)
        return initial
    
    def proc_tree(self, tree):
        # Dependencies
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')
        cvariable_module: Module = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')

        # Create a pause deligate
        pause = self.compiler_instance.pause        

        # Set our option
        option = "standard construction"

        if self.custom_pos is not None:
            option = "custom position"
        if self.from_pos is not None:
            option += " from pos"

        expr = tree['EXPRESSION']
        var  = tree['ID']
        vartype = tree['TYPE']

        types = {
            'int': Int32,
            'int8': Int8,
            'hex': HexInt32,
            'char': Char
        }

        special_types = {
            'list': List,
            'id': ID,
            'pointer': None,
            'deref': None
        }

        maths = {
            "ADD": "add",
            "SUB": "sub",
            "MUL": "mult",
            "DIV": "div",
            "OR":  "or",
            "XOR": "xor",
            "AND": "and",
            "RIGHT_SHIFT": "rsh",
            "LEFT_SHIFT": "lsh"
        }

        load_to_mem_actions = {
            0: 'lmemw',
            1: 'lmemb',
            2: 'lmemh',
            4: 'lmemw'
        }

        read_from_mem_actions = {
            0: 'cmemw',
            1: 'cmemb',
            2: 'cmemh',
            4: 'cmemw'
        }
        

        if vartype.lower() not in types and vartype.lower() not in special_types:
            raise TranspilerExceptions.UnkownType(vartype)
        
        constructor = '; constructor empty?'

        # Check type of construction
        if 'SPECIAL' in tree:
            # Get value we are setting the element to
            final_value = resolution_module(tree['EXPRESSION'], no_construct=True)

            if isinstance(final_value, Char):
                value_hex = '#'
            elif isinstance(final_value, Int32):
                value_hex = '#'
            # elif isinstance(final_value, ID):
            # print(final_value)
            # self.compiler_instance.pause()
            
            # TODO: Add hex value
            
            value = final_value.value

            # Get offset value
            offset_value = tree['INDEX']
            ld_from_var = False
            
            if offset_value[0] == 'INT':
                offset_hex = '#'
                offset_value = offset_value[1]['VALUE']
            elif offset_value[0] == 'ID':
                ld_from_var = True
                offset_value_pos = self.compiler_instance.get_variable(offset_value[1]['VALUE'])['pos']
                offset_bytelength = self.compiler_instance.get_variable(offset_value[1]['VALUE'])['object'].size 
                offset_ld_action = read_from_mem_actions[offset_bytelength] 
            else:
                offset_hex = ''

            # Get array var
            array_var_name = tree['ID']
            array_var_dict = self.compiler_instance.get_variable(array_var_name)
            
            # Get array pos
            array_addr = array_var_dict['pos']

            # Get array type from the object
            array_obj = array_var_dict['object']
            array_type = array_obj.type

            # Set length
            byte_length = array_type.size

            # Set load action
            load_action = load_to_mem_actions[byte_length]

            if not ld_from_var:
                constructor = self.to_pos_with_value_offset_with_value.format(
                    offset_hex = offset_hex,
                    offset_val = offset_value,
                    array_addr = array_addr,
                    byte_length = byte_length,
                    action = load_action,
                    hex = value_hex,
                    value = value
                )
            else:
                constructor = self.to_pos_with_var_offset_with_value.format(
                    from_pos = offset_value_pos,
                    from_action = offset_ld_action,
                    array_addr = array_addr,
                    byte_length = byte_length,
                    action = load_action,
                    hex = value_hex,
                    value = value
                )

        elif expr[0].lower() in types:
            # Assume standard construction
            bitsize = types[vartype].size
    
            # Set action
            action = load_to_mem_actions[bitsize]
    
            # Check if we have a position
            if self.custom_pos is not None:
                position = self.custom_pos
            else:
                # Calculate next position
                position = self.compiler_instance.allocate(bitsize)

            # Assume standard value
            value = resolution_module(expr, no_construct=True)
            constructor = self.standard.format(
                var = var,
                pos = position,
                hex = '' if value.hex else '#',
                value = value.value,
                option = option,
                action = action
            )

            # Create variable inside the instance
            if not self.no_add:
                self.compiler_instance.create_variable(
                    var,
                    position,
                    type = types[expr[0].lower()],
                    obj = value,
                    force = True if self.compiler_instance is not None else False
                )
        elif vartype in special_types or expr[0].lower() in special_types:
            # Check the construction method we may need
            if vartype == 'id' or expr[0].lower() == 'id':

                # If we have set a from_var in the call
                # then we should manually set the object here
                # This is useful for when the var is out of scope
                # Specifically, when it's in the parent scope
                if self.from_var:
                    from_var = self.from_var
                else:
                    from_var_obj = resolution_module(expr, no_construct=True)
                    from_var = self.compiler_instance.get_variable(from_var_obj.value)
                from_var_pos = from_var['pos']

                # Set bitsize
                bitsize = from_var['type'].size
    
                # Set load and read action
                load_action = load_to_mem_actions[bitsize]
                read_action = read_from_mem_actions[bitsize]

                # Check if we have a position
                if self.custom_pos is not None:
                    position = self.custom_pos
                else:
                    # Calculate next position
                    position = self.compiler_instance.allocate(bitsize)
                
                if self.from_pos_flag is not None:
                    from_var_pos = self.from_pos_flag

                constructor = self.from_pos.format(
                    var = var,
                    pos = position,
                    option = option,
                    action = load_action,
                    from_pos = from_var_pos,
                    from_action = read_action
                )

                # Create variable inside the instance
                if not self.no_add:
                    self.compiler_instance.create_variable(
                        var,
                        position,
                        type = from_var['type'],
                        obj = from_var['type'],
                        force = True if self.compiler_instance is not None else False
                    )

            if vartype == 'list':
                # Check items
                if 'ITEMS' in expr[1]:
                    items = expr[1]['ITEMS']
                elif 'LEN' in tree:
                    items = []
                    for _ in range(int(tree['LEN'][1]['VALUE'])):
                        items.append((tree['SUBTYPE'].upper(), {'VALUE': '\x00'}))
                elif expr[0] == 'STRING': # Convert values to items
                    items = []
                    for letter in expr[1]['VALUE']:
                        items.append(
                            ('CHAR', {'VALUE': letter})
                        )
                else:
                    items = []
                    for _ in range(10):
                        items.append(('INT', {'VALUE': '0'}))

                if 'SUBTYPE' not in tree:
                    console.print(f"[bold yellow]WARNING: The var '{var}' is using automatic list-type declarations. It's recommended to specify the type.[/bold yellow]")
                    self.compiler_instance.warn()
                    check_against = items[0][0]
                else:
                    check_against = tree['SUBTYPE'].upper()
                bitsize = types[check_against.lower()].size

                # Check that all types are the same!
                if not VariableAssignMod.optimise([list(x) for x in items], check_against):
                    raise Exception(f"Not all types are equal in the items: {items}\nExpected: {check_against}")
                
                # Set initial position
                initial_position = hex(self.compiler_instance.nextaddr)

                # Create a "fake" variable for each value in list
                final_asm_items = []
                
                for i, item in enumerate(items):
                    item_tree = {
                        'EXPRESSION': item, 
                        'ID': f'{var}_{i}', 
                        'TYPE': item[0].lower()
                    }
                    if self.o2:
                        # self.standard_looped.format()
                        # pass
                        position = self.compiler_instance.allocate(bitsize)
                        self.compiler_instance.create_variable(
                            f'{var}_{i}',
                            position,
                            type = types[check_against.lower()],
                            obj = types[check_against.lower()],
                            force = True if self.compiler_instance is not None else False
                        )
                    else:
                        asm = cvariable_module(item_tree)
                        final_asm_items.append(asm)

                # Get first index and save it to a new var
                if not self.no_add:
                    self.compiler_instance.create_variable(
                        var,
                        initial_position,
                        List,
                        List(items, types[check_against.lower()])
                    )
                    constructor = f"{''.join(final_asm_items)}\n\t\t; List contents above"

            elif expr[0].lower() == 'pointer':
                # pprint(tree)

                if tree['TYPE'] not in ('int', 'int32'):
                    raise TranspilerExceptions.TypeMissmatch(var, tree['TYPE'], 'Int32', expr[-1])

                from_var = self.compiler_instance.get_variable(expr[1]['ID'])

                # Set bitsize
                bitsize = from_var["type"].size

                # Check if we have a position
                if self.custom_pos is not None:
                    position = self.custom_pos
                else:
                    # Calculate next position
                    position = self.compiler_instance.allocate(bitsize)

                constructor = self.pointer.format(
                    var = var,
                    pos = position,
                    value = from_var['pos'],
                )

                # Create variable inside the instance
                if not self.no_add:
                    self.compiler_instance.create_variable(
                        var,
                        position,
                        type = from_var['type'],
                        obj = from_var['type'],
                        force = True if self.compiler_instance is not None else False
                    )
            elif expr[0].lower() == 'deref':
                # pprint(tree)

                from_var = self.compiler_instance.get_variable(expr[1]['ID'])

                # Set bitsize
                bitsize = from_var["type"].size

                # Check if we have a position
                if self.custom_pos is not None:
                    position = self.custom_pos
                else:
                    # Calculate next position
                    position = self.compiler_instance.allocate(bitsize)

                constructor = self.deref.format(
                    var = var,
                    pos = position,
                    from_pos = from_var['pos'],
                    load_action = load_to_mem_actions[from_var['type'].size],
                    read_action = read_from_mem_actions[from_var['type'].size]
                )

                # Create variable inside the instance
                if not self.no_add:
                    self.compiler_instance.create_variable(
                        var,
                        position,
                        type = types[vartype],
                        obj = types[vartype],
                        force = True if self.compiler_instance is not None else False
                    )

        elif expr[0] == 'GET_INDEX':

            list_id_obj = resolution_module(expr[1]['EXPRESSION'], no_construct=True)
            list_id = list_id_obj.value

            list_var = self.compiler_instance.get_variable(list_id)

            index_var = resolution_module(expr[1]['INDEX'], no_construct=True)
            
            if isinstance(index_var, ID):
                index_var_name = index_var.value
                index_var_obj = self.compiler_instance.get_variable(index_var_name)
                list_first_index_pos = list_var['pos']
                list_type = list_var['object'].type
                list_item_length = list_type.size

                # Set bitsize
                bitsize = list_var['object'].type.size

                # Check if we have a position
                if self.custom_pos is not None:
                    position = self.custom_pos
                else:
                    # Calculate next position
                    position = self.compiler_instance.allocate(bitsize)

                # Set load and read action
                load_action = load_to_mem_actions[bitsize]
                read_action = read_from_mem_actions[bitsize]

                constructor = self.from_pos_with_var_offset.format(
                        var = var,
                        pos = position,
                        offset_pos = index_var_obj['pos'],
                        option = option,
                        action = load_action,
                        read_action = read_action,
                        array_addr=list_first_index_pos, 
                        byte_length=bitsize
                    )

            else:
                index = index_var.value

                list_first_index_pos = int(list_var['pos'], 16)
                list_type = list_var['object'].type
                list_item_length = list_type.size

                offset = index * list_item_length
                pos_with_offset = hex(list_first_index_pos + offset)

                # Set bitsize
                bitsize = list_var['object'].type.size

                # Check if we have a position
                if self.custom_pos is not None:
                    position = self.custom_pos
                else:
                    # Calculate next position
                    position = self.compiler_instance.allocate(bitsize)

                # Set load and read action
                load_action = load_to_mem_actions[bitsize]
                read_action = read_from_mem_actions[bitsize]

                constructor = self.from_pos.format(
                        var = var,
                        pos = position,
                        option = option,
                        action = load_action,
                        from_pos = pos_with_offset,
                        from_action = read_action
                    )

            # Create variable inside the instance
            if not self.no_add:
                self.compiler_instance.create_variable(
                    var,
                    position,
                    type = list_type,
                    obj = list_type,
                    force = True if self.compiler_instance is not None else False
                )
        elif expr[0] in maths:
            first  = tree['EXPRESSION'][1]
            first_id = first[1]['VALUE']
            second = tree['EXPRESSION'][2]
            second_id = second[1]['VALUE']

            operator = maths[expr[0]]

            registers = [12,13]

            # ID
            # var

            # Set bitsize
            bitsize = types[vartype].size


            # Set load and read action
            load_action = load_to_mem_actions[bitsize]
            read_action = read_from_mem_actions[bitsize]

            # Check if we have a position
            if self.custom_pos is not None:
                position = self.custom_pos
            else:
                # Calculate next position
                position = self.compiler_instance.allocate(bitsize)

            # Check first and second if they are variables
            first_teplate = ""
            if first[0] == "ID": # Probably a variable's ID
                if first_id not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(first_id, self.variables)
                var = self.compiler_instance.get_variable(first_id)
                first_teplate = self.math_var_template.format(
                    addr = var['pos'],
                    var = first_id,
                    reg = registers[0],
                    read_action = read_action
                )
            else:
                if first[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(first, first[0], 'INT', first[-1])
                first_teplate = self.math_value_template.format(reg = registers[0], val = first[1]['VALUE'])

            second_teplate = ""
            if second[0] == "ID": # Probably a variable's ID
                if second_id not in self.compiler_instance.variables:
                    raise TranspilerExceptions.UnkownVar(second_id, self.variables)
                var = self.compiler_instance.get_variable(second_id)
                second_teplate = self.math_var_template.format(
                    addr = var['pos'],
                    var = second_id,
                    reg = registers[0],
                    read_action = read_action
                )
            else:
                if second[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(second, second[0], 'INT', second[-1])
                second_teplate = self.math_value_template.format(reg = registers[1], val = second[1]['VALUE'])

            if operator in ['rsh', 'lsh']:
                if len(second) < 2:
                    raise Exception("Can't use variables in a shift")
                math_operation = f"{operator} r{registers[0]}, {second[1]}"
            else:
                math_operation = f"{operator} r{registers[0]}, r{registers[1]}, r{registers[0]}"


            constructor = f'''
            {first_teplate}
            {second_teplate}
            {math_operation}
            ; Store the result
            ldr r11, {position}
            mov r20, r{registers[0]}
            ldr r1, .{load_action}
            ldr r0, $2
            jpr r1
            '''
        else:
            raise TranspilerExceptions.UnkownType(expr[0])

        if not self.custom_pos and \
              not self.from_pos_flag:
            constructor = "\n; VARIABLE_ASSIGNMENT\n" + constructor
        else:
            constructor = "\n; VARIABLE_REASSIGNMENT\n" + constructor

        return {'constructor': constructor}
    
    @jit(looplift = True, forceobj=True)
    def optimise(nodes: list, check_against: str):
        x = 0
        while x != len(nodes):
            node: list = nodes[x]
            if node[0] != check_against:
                return False
            x += 1
        else:
            return True


class GotoMod(Module):
    name="GOTO"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.template_s = """
        ; a at {addr}
        ldr r11, {addr}

        ; read address from a
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1

        jpr r20
        """
        
        self.template = """
        ; GOTO
        {constructor}
        """

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, op=1):

        initial = super().__call__(tree, op=op)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # print(tree)

        var = tree['ID']

        var_dict = self.compiler_instance.get_variable(var)
        var_pos  = var_dict['pos']

        constructor = self.template_s.format(
            addr = var_pos
        )

        return {"constructor": constructor}

# TODO: Finish implementing Increment and Decrement
class IncrementMod(Module):
    name="INCREMENT"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        
        self.template = """
        ; INCREMENT
        {constructor}
        """

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, op=1):

        initial = super().__call__(tree, op=op)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # print(tree)

        var = tree['VAR']

        var_dict = self.compiler_instance.get_variable(var)
        var_pos  = var_dict['pos']
        var_type = var_dict['type']

        constructor = "; empty constructor"

        quit(1)

        print(constructor)
        return {"constructor": constructor}
    
class ValueAtPointerMod(Module):
    name="SET_PTR"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        
        self.template_to_val = """
        ; say b is at {addr}
        ldr r11, {addr}

        ; read value from r11
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1

        ; r20 now contains the correct addr
        ; so move r20 to r11
        mov r11, r20

        ; write to addr
        ldr r20, #{value}
        ldr r1, .{winst}
        ldr r0, $2
        jpr r1
        """

        self.template_ptr_to_ptr = """
        ; a at {addr}
        ldr r11, {addr}

        ; read address from a
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1

        mov r12, r20

        ; at {addr_from}
        ldr r11, {addr_from}

        ; read addr from b
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1

        ; read value from addr
        mov r11, r20
        ldr r1, .{rinst}
        ldr r0, $2
        jpr r1

        ; write to addr that we read from a
        mov r11, r12
        ldr r1, .{winst}
        ldr r0, $2
        jpr r1
        """

        self.template_to_var = """
        ; say b is at {addr}
        ldr r11, {addr}

        ; read value from r11
        ldr r1, .cmemw
        ldr r0, $2
        jpr r1

        ; r20 now contains the correct addr
        ; so move r20 to r11
        mov r12, r20

        ; read value from var
        ldr r11, {addr_from}
        ldr r1, .{rinst}
        ldr r0, $2
        jpr r1

        ; write to addr
        mov r11, r12
        ldr r1, .{winst}
        ldr r0, $2
        jpr r1
        """

        self.template = """
        ; SET_PTR
        {constructor}
        """

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, op=1):

        initial = super().__call__(tree, op=op)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # print(tree)

        ptr_var = tree['ID']
        expr    = tree['EXPRESSION']

        constructor = "; empty constructor"

        types = {
            'int': Int32,
            'int8': Int8,
            'hex': HexInt32,
            'char': Char,
            'id': ID
        }

        load_to_mem_actions = {
            0: 'lmemw',
            1: 'lmemb',
            2: 'lmemh',
            4: 'lmemw'
        }

        read_from_mem_actions = {
            0: 'cmemw',
            1: 'cmemb',
            2: 'cmemh',
            4: 'cmemw'
        }

        if expr[0].lower() in types:
            if expr[0].lower() == 'int' or expr[0].lower() == 'hex':
                value = types[expr[0].lower()](expr[1]['VALUE'])

                ptr_var_pos = self.compiler_instance.get_variable(ptr_var)['pos']

                # Set bitsize
                bitsize = value.size

                constructor = self.template_to_val.format(
                    addr  = ptr_var_pos,
                    value = value.value,
                    winst = load_to_mem_actions[bitsize]
                )

            elif expr[0].lower() == 'char':
                value = types[expr[0].lower()](expr[1]['VALUE'])

                ptr_var_pos = self.compiler_instance.get_variable(ptr_var)['pos']

                # Set bitsize
                bitsize = value.size

                constructor = self.template_to_val.format(
                    addr  = ptr_var_pos,
                    value = value.value,
                    winst = load_to_mem_actions[bitsize]
                )

            elif expr[0].lower() == 'id':
                value_raw = expr[1]['VALUE']
                value = self.compiler_instance.get_variable(value_raw)
                bitsize_val = value['type'].size

                ptr_var_pos = self.compiler_instance.get_variable(ptr_var)['pos']

                # Set bitsize
                bitsize = value['type'].size

                constructor = self.template_to_var.format(
                    addr  = ptr_var_pos,
                    addr_from  = value['pos'],
                    rinst = read_from_mem_actions[bitsize_val],
                    winst = load_to_mem_actions[bitsize]
                )

        elif expr[0].lower() == "deref":
            value_raw = expr[1]['ID']
            value = self.compiler_instance.get_variable(value_raw)
            bitsize_val = value['type'].size

            ptr_var_pos = self.compiler_instance.get_variable(ptr_var)['pos']

            # Set bitsize
            bitsize = value['type'].size

            constructor = self.template_ptr_to_ptr.format(
                addr = ptr_var_pos,
                addr_from = value['pos'],
                rinst = read_from_mem_actions[bitsize_val],
                winst = load_to_mem_actions[bitsize]
            )
        else:
            raise TranspilerExceptions.IncompleteDeclaration(tree)
        
        return {"constructor": constructor}
    
class VariableReAssignMod(Module):
    name="VARIABLE_REASSIGNMENT"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        
        self.template = "\t\t; Empty block. Reassignment uses the VariableAssignMod module, so check the above."

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, redirect=False, custom_pos=None, from_pos=None, from_var=None, op=1):
        # Override the standard call, this let's us feed it another parameter 
        self.redirect = redirect
        self.custom_pos = custom_pos
        self.from_pos = from_pos
        self.from_var = from_var
        initial = super().__call__(tree, op=op)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # Dependency
        assign_module: VariableAssignMod = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')

        # Get opts
        varname = tree['ID']

        # Check if our variable exists
        varpos = self.compiler_instance.get_variable(varname)['pos']

        # Reconstruct our tree to fit the assign variable module
        # Get type from variable
        vartype = self.compiler_instance.get_variable(varname)['type'].abbr_name

        # print("OTREE",tree)

        new_tree = {
            'ID': varname, 
            'TYPE': vartype, 
            'EXPRESSION':  tree['EXPRESSION']
        }
        # print("NTREE",new_tree)

        asm = assign_module(
            tree = new_tree,
            custom_pos = varpos,
            from_pos = self.from_pos,
            from_var = self.from_var
        )

        if self.redirect:
            self._internal = asm
        else:
            self.compiler_instance.finished.append(asm)

        return {}

class VariableReAssignAtIndexMod(Module):
    name="VARIABLE_REASSIGNMENT_AT_INDEX"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        
        self.template = "\t\t; Empty block. Reassignment uses the VariableAssignMod module, so check the above."

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, redirect=False, op=1):
        # Override the standard call, this let's us feed it another parameter 
        self.redirect = redirect
        initial = super().__call__(tree, op=op)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # Dependency
        assign_module: VariableAssignMod = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')

        # Get opts
        varname = tree['ID'][1]['EXPRESSION'][1]['VALUE']
        expression = tree['EXPRESSION']

        # Check if our variable exists
        varpos = self.compiler_instance.get_variable(varname)['pos']

        # Reconstruct our tree to fit the assign variable module
        new_tree = {
            'ID': varname, 
            'TYPE': tree['EXPRESSION'][0].lower(), 
            'EXPRESSION':  expression,
            'INDEX': tree['ID'][1]['INDEX'],
            'SPECIAL': 'TO_ELEMENT'
        }

        asm = assign_module(
            tree = new_tree,
            custom_pos = varpos
        )

        if self.redirect:
            self._internal = asm
        else:
            self.compiler_instance.finished.append(asm)


        return {}