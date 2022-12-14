from exceptions import ModuleExceptions, TranspilerExceptions
from chonkytypes import String, Char, Int32, HexInt32, ID, List
from compiler import * # For the Compiler class autocomplete
from numba import jit, njit

import pprint
pprint = pprint.PrettyPrinter(indent=2).pprint
from rich.console import Console
from rich.syntax import Syntax
console = Console()

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

    def __call__(
        self,
        tree,
        no_construct = False
    ):
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
            raise Exception("Failed to unpack elements. Perhaps you need to set `no_construct` to True to avoid this module's construction?")

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
        
        funcname = tree['ID'][1]['VALUE']
        arguments = tree['FUNCTION_ARGUMENTS']

        console.log(f"[FunctionCallMod] {funcname}({arguments})")

        # Check if the function is defined already
        if funcname in self.compiler_instance.functions:
            func  = self.compiler_instance.functions[funcname]

            # Check if the function is a builtin module
            if isinstance(func, Module):
                func: Module
                # console.log(f"\tModule callback matched, requesting build (optimisation {'enabled' if func.optimise is not None else 'not available'})")

                # Request build
                built = func(arguments['POSITIONAL_ARGS'])
            elif funcname in self.compiler_instance.functions:
                # Get the function's compiler instance
                func_instance: Compiler = self.compiler_instance.functions[funcname]['object']

                # Dependencies
                resolution_module: Module = func_instance.get_action('RESOLUT')
                reassign_module: VariableReAssignMod = func_instance.get_action('VARIABLE_REASSIGNMENT')


                if arguments:
                    arguments = arguments['POSITIONAL_ARGS']

                    # Process supplied arguments
                    for i, arg in enumerate(func_instance.arguments):
                        current_supplied_raw = arguments[i]
                        name = arg
                        argtype = func_instance.arguments[arg]['type']
                        pos  = func_instance.arguments[arg]['pos']

                        current_supplied = resolution_module(current_supplied_raw, no_construct=True)
                        
                        # # Debug
                        # print(current_supplied)
                        # print(name, argtype, pos)
                        # #

                        if isinstance(current_supplied, ID):
                            raise Exception("Not Implemented")
                        else:
                            # Check the type of the supplied argument
                            if type(current_supplied).abbr_name != argtype:
                                raise TranspilerExceptions.TypeMissmatch(
                                    name,
                                    current_supplied,
                                    argtype,
                                    tree['ID'][-1]
                                )
                            
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
            # elif funcname is in an namespaced instance

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
        
        console.log(f"[FunctionDecMod] {funcname}({arguments}) -> {returns}")

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

                cur_var_asm = cvariable_module(
                    {
                        "ID": name,
                        "TYPE": type,
                        "EXPRESSION": (type.upper(), {"VALUE": "0"})
                    }
                )
                var_asm.append(cur_var_asm)
                pos = instance.get_variable(name)['pos']

                processed_arguments[name] = pos

                # Save arguments to our instance
                instance.arguments[name] = {'pos': pos, 'type': type}
                instance.variables[name] = {'pos': pos, 'type': type}

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
            instance
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
        ldr r20, {val}
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
                    1: 'cmemb',
                    2: 'cmemh',
                    4: 'cmemw'
                }

                template = self.load_var_template.format(
                    action = read_actions[read_type.size],
                    addr = pos
                )
            else:
                template = self.raw_val_template.format(
                    val = attr.value
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

        self.template = """
        ; VARIABLE_ASSIGNMENT
        {constructor}
        """

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, custom_pos=None, no_construct=False, no_add=False):
        # Override the standard call, this let's us feed it another parameter 
        self.custom_pos = custom_pos
        self.no_add = no_add
        initial = super().__call__(tree, no_construct)
        return initial
    
    def proc_tree(self, tree):
        # Dependencies
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')
        cvariable_module: Module = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')

        # Set our option
        option = "standard construction"

        if self.custom_pos is not None:
            option = "custom position"

        expr = tree['EXPRESSION']
        var  = tree['ID']
        vartype = tree['TYPE']

        types = {
            'int': Int32,
            'hex': HexInt32,
            'char': Char
        }

        special_types = {
            'list': List,
            'id': ID,
            'pointer': None,
            'deref': None
        }

        load_to_mem_actions = {
            1: 'lmemb',
            2: 'lmemh',
            4: 'lmemw'
        }

        read_from_mem_actions = {
            1: 'cmemb',
            2: 'cmemh',
            4: 'cmemw'
        }

        if vartype.lower() not in types and vartype.lower() not in special_types:
            raise TranspilerExceptions.UnkownType(vartype)

        # Check type of construction
        if expr[0].lower() in types:
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
                pprint(tree)

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
                # Set items
                items = expr[1]['ITEMS']

                if 'SUBTYPE' not in tree:
                    console.print(f"[bold yellow]WARNING: the var {var} is using legacy list declarations. It's recommended to specify the type [/bold yellow]")
                    self.compiler_instance.warn()
                    check_against = items[0][0]
                else:
                    check_against = tree['SUBTYPE'].upper()

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
                    asm = cvariable_module(item_tree)
                    #print(f"Created -> {var}_{i}")
                    final_asm_items.append(asm)

                # Get first index and save it to a new var
                self.compiler_instance.create_variable(
                    var,
                    initial_position,
                    vartype,
                    List(items, types[check_against.lower()])
                )
                constructor = f"{''.join(final_asm_items)}\n\t\t; List contents above"
            elif expr[0].lower() == 'pointer':
                pprint(tree)

                from_var = self.compiler_instance.get_variable(expr[1]['ID'])

                # Set bitsize
                bitsize = 4

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
                pprint(tree)

                from_var = self.compiler_instance.get_variable(expr[1]['ID'])

                # Set bitsize
                bitsize = 4

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
                        type = from_var['type'],
                        obj = from_var['type'],
                        force = True if self.compiler_instance is not None else False
                    )


        elif expr[0] == 'GET_INDEX':

            list_id_obj = resolution_module(expr[1]['EXPRESSION'], no_construct=True)
            list_id = list_id_obj.value

            list_var = self.compiler_instance.get_variable(list_id)
            print(list_var)

            index = resolution_module(expr[1]['INDEX'], no_construct=True).value

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

        else:
            raise TranspilerExceptions.UnkownType(expr[0])

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
    
    
class VariableReAssignMod(Module):
    name="VARIABLE_REASSIGNMENT"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()
        
        self.template = "\t\t; Empty block. Reassignment uses the VariableAssignMod module, so check the above."

        self._internal = ""

        self.compiler_instance: Compiler = compiler_instance

    def __call__(self, tree, redirect=False):
        # Override the standard call, this let's us feed it another parameter 
        self.redirect = redirect
        initial = super().__call__(tree)
        return self._internal + initial
    
    def proc_tree(self, tree):
        # Dependency
        assign_module: VariableAssignMod = self.compiler_instance.get_action('VARIABLE_ASSIGNMENT')

        # Get opts
        varname = tree['ID']

        # Check if our variable exists
        varpos = self.compiler_instance.get_variable(varname)['pos']

        # Reconstruct our tree to fit the assign variable module
        new_tree = {
            'ID': varname, 
            'TYPE': tree['EXPRESSION'][0].lower(), 
            'EXPRESSION':  tree['EXPRESSION']
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