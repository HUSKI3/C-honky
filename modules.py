from exceptions import ModuleExceptions, TranspilerExceptions
from chonkytypes import String, Char, Int32, HexInt32, ID
from compiler import * # For the Compiler class autocomplete
from numba import jit

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
        return self.template.format(
                **arguments
            )

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
        ; {arg} is at {pos}
        ldr r11, {pos}
        ; load from {pos}
        ldr r0, $2
        jpr r2
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

            return ID(tree[1]['VALUE'][0])

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
            ; Set ret to r0
            ldr r11, {ret_pos}
            mov r20, r0
            ldr r0, $2
            jpr r1
            ; BODY
            {program}
            ; BODY END
            ; Load return position
            ldr r11, {ret_pos}
            ; load from return addr
            ldr r0, $2
            jpr r2
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

class VariableAssignMod(Module):
    name="VARIABLE_ASSIGNMENT"
    type = Module.MODULE_TYPES.SPECIAL_ACTION

    def __init__(self, compiler_instance):
        super().__init__()

        self.standard = """
        ; {option} for {var}
        ldr r11, {pos}
        ldr r20, {hex}{value}
        ldr r0, $2
        jpr r4
        """

        self.template = """
        ; VARIABLE_ASSIGNMENT
        {constructor}
        """

        self.compiler_instance = compiler_instance

    def __call__(self, tree, custom_pos=None, no_construct=False):
        # Override the standard call, this let's us feed it another parameter 
        self.custom_pos = custom_pos
        initial = super().__call__(tree, no_construct)
        return initial
    
    def proc_tree(self, tree):
        # Dependency
        resolution_module: Module = self.compiler_instance.get_action('RESOLUT')

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

        if vartype not in types:
            raise TranspilerExceptions.UnkownType(vartype)

        bitsize = types[vartype].size

        # Check if we have a position
        if self.custom_pos is not None:
            position = self.custom_pos
        else:
            # Calculate next position
            position = self.compiler_instance.allocate(bitsize)

        # Check type of construction
        if expr[0].lower() in types:
            # Assume standard value
            value = resolution_module(expr, no_construct=True)
            constructor = self.standard.format(
                var = var,
                pos = position,
                hex = '' if value.hex else '#',
                value = value.value,
                option = option
            )

            # Create variable inside the instance
            self.compiler_instance.create_variable(
                var,
                position,
                force = True if self.compiler_instance is not None else False
            )
        else:
            raise TranspilerExceptions.UnkownType(expr[0])

        return {'constructor': constructor}
    
    
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