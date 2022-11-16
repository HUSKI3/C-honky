import pprint

pprint = pprint.PrettyPrinter(indent=2).pprint

class Dictlist(dict):
    def __setitem__(self, key, value):
        try:
            self[key]
        except KeyError:
            super(Dictlist, self).__setitem__(key, [])
        self[key].append(value)

class TranspilerExceptions:
    class TypeMissmatch(Exception):
        def __init__(self, var, got, expected):
            Exception.__init__(self, f"For {var}, got: {got}, expected: {expected}")
    class Overflow(Exception):
        def __init__(self, var, got, expected):
            Exception.__init__(self, f"For {var}, got: {got}, value overflows the given size of {expected}")
    class UnkownVar(Exception):
        def __init__(self, var, vars):
            Exception.__init__(self, f"Got unknown '{var}'. Variables only contain: {vars()}")
    class InvalidIndexType(Exception):
        def __init__(self, type, types):
            Exception.__init__(self, f"Got type '{type}' for index. Supported types are: {types}")
    class OutOfBounds(Exception):
        def __init__(self, index, length):
            Exception.__init__(self, f"Index {index} is out of bounds. Array length is {length}")
    class UnauthorizedBitSet(Exception):
        def __init__(self):
            Exception.__init__(self, f"This program is not being built in the correct mode for setting the bit configuration.")
    class IncompleteDeclaration(Exception):
        def __init__(self, tree):
            Exception.__init__(self, f"The variable declaration does not contain any matched declaration method. Tree & constructor: {tree}")
    class UnknownActionReference(Exception):
        def __init__(self, act):
            Exception.__init__(self, f"Got unknown action '{act}'")
    class UnkownMethodReference(Exception):
        def __init__(self, func):
            Exception.__init__(self, f"Got unknwon function '{func}'")

class TranspilerWarnings:
    class ModesEnabled(Warning):
        def __init__(self, mode) -> None:
            print(f"\033[0;34;47mMode [{mode}] enabled for this program, it's not recommended to set a mode unless the program is a kernel or it's component\033[0m")
    class EmbededASMEnabled(Warning):
        def __init__(self) -> None:
            print(f"\033[0;34;47mEmbed [ASM] Using embedded asm, please be careful!\033[0m")

class Transpiler:
    def __init__(
            self,
            tree,
            nextaddr = 0,
            variables = {}, #Dictlist(),
            functions = {},
            arguments = {},
            label_count = 0,
        ) -> None:
        self.code = tree
        self.actions = {
            'VARIABLE_ASSIGNMENT': self.create_variable,
            'VARIABLE_REASSIGNMENT': self.reassign_variable,
            'DEBUG': self.debug,
            'FUNCTION_DECLARATION': self.dec_func,
            'FUNCTION_CALL': self.call_func,
            'COMPILER': self.compiler_eval,
            'RETURN': self.create_return_value,
            'CONDITIONAL': self.create_conditional_tree,
            'FOR_COMP': self.create_comp_for,
            'EMBED': self.create_embed,
            'VARIABLE_REASSIGNMENT_AT_INDEX': self.reassign_variable_at_index,
            'WHILE': self.create_dyn_while,
            'ADVANCED_WRITE': self.advanced_write,
            'INCREMENT': self.increment_var,
            'DECREMENT': self.decrement_var,
        }
        
        self.builtins = {
            "putchar": self.putchar
        }

        self.variables  = variables
        self.functions  = functions
        self.arguments  = arguments
        self.bitstart   = 10000000
        self.bitend     = None
        self.bitdata    = None
        self.nextaddr   = nextaddr
        self.mode       = "standard"
        self.labelcounter = label_count

        self.types = {
            "char":1,
            "int8":2,
            "int16":3,
            "int32":4,
            "int":4,
            "list":5,
            "list_int": 5
        }

        self.fin = []
        self.fin_funcs = []


    def run(self):
        for action in self.code:
            if action[0] in self.actions:
                self.actions[action[0]](action[1])
            else:
                raise TranspilerExceptions.UnknownActionReference(action[0])

    def debug(self, _):
        print(f"""
---= Debug =---
BitStart:\t{self.bitstart}
BitEnd: \t{self.bitend}
BitData:\t{self.bitdata}
NextAddr:\t{self.nextaddr}

Variable map:
""")
        pprint(self.variables)

    
    def putchar(self, args):
        _arg = self.evaluate(args['POSITIONAL_ARGS'][0])
        if type(_arg) != list:
            if _arg in self.variables:        
                pos = self.variables[_arg]['pos'] + self.bitstart
            else:
                raise TranspilerExceptions.UnkownVar(_arg, self.variables.keys)
        else:
            pos = _arg[1]

        #print(f"PUTCHAR ({_arg}) @ {pos}")
        
        self.fin.append(
            f'''
            ; {_arg} is at {pos}
            ldr r11, {pos}

            ; load from {pos}
            ldr r0, $2
            jpr r2
            
            ; output {_arg}
            ldr r5, FFFF0000
            stb r20, r5
            '''
            )

    def call_func(self, tree):
        _func = self.evaluate(tree['ID'])
        _args = tree['FUNCTION_ARGUMENTS']

        if _func in self.builtins:
            self.builtins[_func](_args)
        elif _func in self.functions:
            #print(_args)

            if _args:
                _args = _args['POSITIONAL_ARGS']

                for i, arg in enumerate(self.functions[_func]['instance'].arguments):
                    current = self.functions[_func]['instance'].arguments[arg]

                    if current['type'] == 'list':
                        l = self.evaluate(_args[i], unsafe=True)
                        if type(l) == str:
                            l = self.variables[l]['meta']
                            #pprint(l)
                        else:
                            l = l[1]
                        for ei, elem in enumerate(l):
                            #print(f'{arg}', self.bitstart + current['meta'][ei]['pos'], elem)
                            self.reassign_variable(
                                {
                                    'ID': 'X',
                                    'EXPRESSION': elem,
                                },
                                val = elem['val'],
                                unsafe = True,
                                addr = self.bitstart + current['meta'][ei]['pos']
                            )
                    else:
                        self.reassign_variable(
                            {
                                'ID': arg,
                                'EXPRESSION': _args[i],
                                },
                                addr = current['pos']
                        )


            self.fin.append(
                f'''
                ; Calling {_func}
                ldr r0, $3
                ldr r23, .{_func}
                jpr r23
                '''
            )
        else: raise TranspilerExceptions.UnkownMethodReference(_func)

    def create_return_value(self, tree):
        _value = self.evaluate(tree["EXPRESSION"])
        _type = _value[0]
        _value = _value[1]
        
        self.fin.append(f'''
        ; return type {_type} 
        ldr r24, #{_value}
        ''')

    def reassign_variable_at_index(self, tree):
        #pprint(tree)
        _pos = self.evaluate(tree['ID'])
        _value = self.evaluate(tree['EXPRESSION'])

        if _value[0] == 'CHAR':
            _value[1] = ord(_value[1])

        self.fin.append(
                f'''
                ldr r11, {_pos[1]}
                ldr r20, #{_value[1]}
                ldr r0, $2
                jpr r4
                '''
            )
    
    def increment_var(self, tree):
        print(tree)
        _var   = tree['VAR']

        if _var not in self.variables:
            raise TranspilerExceptions.UnkownVar(_var, self.variables.keys)
        
        addr = self.variables[_var]['pos'] + self.bitstart

        # get the var pos, load, add 1, write
        self.fin.append(f'''
        ; Load from {addr} for var {_var}
        ldr r11, {addr}
        ldr r0, $2
        jpr r2

        ; Add 1
        iadd r20, 1

        ; Store
        ldr r0, $2
        jpr r4
        ''')
    
    def decrement_var(self, tree):
        print(tree)
        _var   = tree['VAR']

        if _var not in self.variables:
            raise TranspilerExceptions.UnkownVar(_var, self.variables.keys)
        
        addr = self.variables[_var]['pos'] + self.bitstart

        # get the var pos, load, add 1, write
        self.fin.append(f'''
        ; Load from {addr} for var {_var}
        ldr r11, {addr}
        ldr r0, $2
        jpr r2

        ; Sub 1
        isub r20, 1

        ; Store
        ldr r0, $2
        jpr r4
        ''')
    
    def dec_func(self, tree):
        _name = tree["ID"]
        _items = {}

        if "POSITIONAL_ARGS" in tree["FUNCTION_ARGUMENTS"]:
            _args = tree["FUNCTION_ARGUMENTS"]["POSITIONAL_ARGS"]

            # Create variables for each!
            for i, item in enumerate(_args):
                t = self.evaluate(item)
                if 'LEN' in item[1]:
                    l = t[2]
                else: l = 20
                #print(t, item)

                if t[0] == 'list':
                    v = self.evaluate(('STRING', {'VALUE': ' '*l}))[1]
                    val = len(v)
                elif t[0] == 'list_int':
                    v = self.evaluate(('INT_ARRAY', {'VALUE': ' '*l}))[1]
                    val = len(v)
                else:
                    v = self.evaluate(('INT', {'VALUE': "0"}))[1]
                    val = v
                
                t = t[0]

                #print("TV:", t,v, item)

                _ = {
                    "name": item[1]['ID'],
                    "value": v, # Change value to something bigger later
                    "type": t
                }

                x = self.create_variable(custom_constructor = _)
                
                self.variables[item[1]['ID']] = {'meta': v, 'pos': x['pos'], 'type': t, 'val': val}
                _items[item[1]['ID']] = x


        _t = Transpiler(
            tree["PROGRAM"],
            nextaddr = self.nextaddr,
            variables = self.variables.copy(),
            functions = self.functions,
            arguments= _items,
            label_count = self.labelcounter 
        )

        # Overwrite default bit-values
        _t.run()
        # Set main nextaddr to _t nextaddr
        self.nextaddr = _t.nextaddr
        _program = '\n'.join(_t.fin)
        # _return_type = self.evaluate(tree["RETURNS_TYPE"])

        # We want to allocate the next address for the function
        #print('next addr', self.nextaddr)

        # Construct function wrap
        '''        
        ; Read below addr and offset by [] instr
        ; ldr r23, $1
        ; Store function addr
        ; Function [{name}]
        ; Get return value if it exists
        ; Then create_return_value
        ; Return value is at r24
        '''

        # Create variable with return addr
        _ = {
            "name": "ret",
            "value": 69, # something idk
            "type": "int"
        }

        x = self.create_variable(custom_constructor = _)

        base = '''
        ; FUNCTION {name} TAKES {_items}
        .{name}
            ; Set ret to r0
            ldr r11, {ret_pos}
            mov r20, r0
            ldr r0, $2
            jpr r4
            {program}
            ; Load return position
            ldr r11, {ret_pos}
            ; load from return addr
            ldr r0, $2
            jpr r2
            jpr r20
        ; END FUNCTION {name}
        '''

        self.fin_funcs.append(
            base.format(name = _name, program = _program, _items = _items, ret_pos=x['pos']+self.bitstart)
        )
        self.functions[_name] = {'tree':tree, 'instance': _t}

    def reassign_variable(
            self, 
            tree, 
            unsafe=False, 
            typ=None,
            val=None, 
            addr=None
        ):
        #pprint(tree)
        var_asign = False
        math = False
        operation = ''
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
        # Check for math shit here
        if type(tree['EXPRESSION']) == tuple and tree['EXPRESSION'][0] in operations.keys():
            math = True

            first  = tree['EXPRESSION'][1]
            second = tree['EXPRESSION'][2]
            operation = operations[tree['EXPRESSION'][0]]

        if not unsafe and not math:
            _var   = tree['ID']

            if _var not in self.variables:
                raise TranspilerExceptions.UnkownVar(_var, self.variables.keys)

            if type(self.evaluate(tree['EXPRESSION'])) == list:
                _type = self.evaluate(tree['EXPRESSION'])[0]
                _type = _type.upper()
                _value = self.evaluate(tree['EXPRESSION'])[1]
                if _type != self.variables[_var]['type'].upper():
                    print(tree['EXPRESSION'],self.evaluate(tree['EXPRESSION']))
                    raise TranspilerExceptions.TypeMissmatch(_var, _type, self.variables[_var]['type'])

                _pos = self.variables[_var]['pos']

            else:
                from_var = self.evaluate(tree['EXPRESSION'])
                #print(from_var)
                # Since we are assigning to another variable's value, we must have a different route
                if from_var not in self.variables:
                    raise TranspilerExceptions.UnkownVar(from_var, self.variables.keys)

                from_var_pos = self.variables[from_var]['pos']
                _type = self.variables[from_var]['type']
                n_var = _var
                _var = from_var
                _value = ''
                n_value = self.variables[from_var]['val']
                var_asign = True
                _pos = self.nextaddr
                self.nextaddr = _pos + round(40/8)

            # Process value?
            # We may need another function to process this
            if _type == 'CHAR':
                _value = ord(_value)

            if _type == 'list':
                self.variables[_var] = {'meta': _value, 'pos': _pos, 'type': _type, 'val': len(_value)}
            elif var_asign:
                self.variables[n_var] = {'meta': {}, 'pos': _pos, 'type': _type, 'val': n_value}
            else:
                self.variables[_var] = {'meta': {}, 'pos': _pos, 'type': _type, 'val': _value}
        elif unsafe:
            _var = 'x'
            _value = val
            _type = typ
        
            
        if math:
            _var   = tree['ID']

            if _var not in self.variables:
                raise TranspilerExceptions.UnkownVar(_var, self.variables.keys)

            _pos = self.variables[_var]['pos']

            registers = [12, 13]
            var_template = '''
            ; Load from {addr} for var {var}
            ldr r11, {addr}
            ldr r0, $2
            jpr r2
            mov r{reg}, r20
            '''
            value_template = '''
            ldr r{reg}, #{val}
            '''

            # Check first and second if they are variables
            first_teplate = ""
            first = self.evaluate(first)
            if type(first) == str: # Probably a variable's ID
                if first not in self.variables:
                    raise TranspilerExceptions.UnkownVar(first, self.variables.keys)
                var = self.variables[first]
                first_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = first,
                    reg = registers[0]
                )
            else:
                if first[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(first, first[0], 'INT')
                first_teplate = value_template.format(reg = registers[0], val = first[1])

            second_teplate = ""
            second = self.evaluate(second)
            if type(second) == str: # Probably a variable's ID
                if second not in self.variables:
                    raise TranspilerExceptions.UnkownVar(second, self.variables.keys)
                var = self.variables[second]
                second_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = second,
                    reg = registers[1]
                )
            else:
                if second[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(second, second[0], 'INT')
                second_teplate = value_template.format(reg = registers[1], val = second[1])

            if operation in ['rsh', 'lsh']:
                if len(second) < 2:
                    raise Exception("Can't use variables in a shift")
                math_operation = f"{operation} r{registers[0]}, {second[1]}"
            else:
                math_operation = f"{operation} r{registers[0]}, r{registers[1]}, r{registers[0]}"


            final_template = f'''
            {first_teplate}
            {second_teplate}

            {math_operation}

            ; Store the result
            ldr r11, {_pos+self.bitstart}
            mov r20, r{registers[0]}
            ldr r0, $2
            jpr r4
            '''
        
        if addr:
            _pos = addr
            
        if _pos > self.bitstart:
            _pos = _pos - self.bitstart

        if var_asign:
            self.fin.append(
                    f'''
                    ; {n_var} reassignment from {from_var} at {from_var_pos}
                    ldr r11, {from_var_pos+self.bitstart}
                    ldr r0, $2
                    jpr r2
                    ldr r11, {_pos+self.bitstart}
                    ldr r0, $2
                    jpr r4
                    '''
                )
        elif math:
            self.fin.append(final_template)
        else:
            self.fin.append(
                    f'''
                    ; {_var} reassignment to {_value}
                    ldr r11, {_pos+self.bitstart}
                    ldr r20, #{_value}
                    ldr r0, $2
                    jpr r4
                    '''
                )

    def create_comp_for(self, _):
        _iterable = _['ITERABLE']
        _var      = _['VARIABLE']
        _program  = _['PROGRAM']
        
        if _iterable[1]['VALUE'] not in self.variables:
            raise TranspilerExceptions.UnkownVar(_iterable[1]['VALUE'], self.variables.keys)

        _iterable = self.variables[_iterable[1]['VALUE']]

        _ = {
                "name": _var[1]['VALUE'],
                "value": 0,
                "type": 'INT'
            }
        
        index = self.create_variable(custom_constructor = _)

        self.variables[_var[1]['VALUE']] = {
                "pos":index['pos'],
                "val":index['val'],
                "type":'INT',
                "meta": {}
            }
        

        # Create a function with the program tree and execute it
        for x in range(_iterable['val']):
            self.reassign_variable(
                {'EXPRESSION': ('INT', {'VALUE': str(x)}), 'ID': _var[1]['VALUE']}
            )
            for action in _program:
                if action[0] in self.actions:
                    self.actions[action[0]](action[1])
                else:
                    raise TranspilerExceptions.UnknownActionReference(action[0])

            #pprint(self.variables)
        
        del self.variables[_var[1]['VALUE']]

    def create_variable(self, tree=None, custom_constructor={}, custom_pos=False):
        meta = {}
        math = False

        if tree:
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
            _var = tree['ID']
            _type = tree['TYPE']
            if type(tree['EXPRESSION']) == tuple and tree['EXPRESSION'][0] in operations.keys():
                math = True
                first  = tree['EXPRESSION'][1]
                second = tree['EXPRESSION'][2]

                operation = operations[tree['EXPRESSION'][0]]

                _value = ['int','MATH_OPERATION_PRECONSTRUCTOR']
                head_bitlength =  0
                value_bitlength = 32
            else:
                _value = self.evaluate(tree['EXPRESSION'])


        elif custom_constructor:
            _var = custom_constructor['name']
            _value = custom_constructor['value']
            _type = custom_constructor['type']
        
        else:
            raise TranspilerExceptions.IncompleteDeclaration((tree, custom_constructor))


        if None in [
            _var,
            _value,
            _type
        ]: raise Exception(f"Valid incomplete declaration resulted in null values. (_var, _value, _type) as {_var, _value, _type}")
            # TODO: Migrate to proper exception

        # Check if we are assigning to a var
        if tree and tree['EXPRESSION'][0] == 'ID':
            from_var = self.variables[_value]
            from_var_pos = from_var['pos']
            _type = from_var['type']
            _value = [_type,from_var['val']]
            if type(from_var['val']) in [str, int]:
                value_bitlength = len('{:032b}'.format(int(from_var['val'])))
            else: value_bitlength = 0

            _b_type = self.types[_type.lower()]
            head_bitlength = len('{:08b}'.format(_b_type))

        # If tree
        elif tree:
            if _value[0].lower() != _type.lower():
                raise TranspilerExceptions.TypeMissmatch(_var, _value[0], _type)

            # Calculate Value bitlength
            if _value[0] == 'INT' or _value[0] == 'CHAR':
                if _value[0] == 'CHAR':
                    _value[1] = ord(_value[1])
                value_bitlength = len('{:032b}'.format(int(_value[1])))
                if value_bitlength > 32:
                    raise TranspilerExceptions.Overflow(_var, [_value[0], len(value_bitlength)], 32)

            if _value[0] == 'list':
                # Get total bitlength
                _array_bits = [_["bitlen"] for _ in _value[1]]
                value_bitlength = 0 #sum(_array_bits)
                _b_type = self.types[_type.lower()]
                head_bitlength = len('{:08b}'.format(_b_type))
                # Update variable meta data with the references of it's contents
                meta = _value[1]
                # overwrite value
                # val in a list is the length of it
                _value[1] = len(_value[1])

            # Calculate Head bitlength
            if _type.lower() in self.types:
                _b_type = self.types[_type.lower()]
                _b_x = None # WIP
                head_bitlength = len('{:08b}'.format(_b_type))
        
        elif custom_constructor:
            # Calculate Value bitlength
            if _type == 'INT' or _type == 'CHAR':
                if _type == 'CHAR':
                    _value = ord(_value)
                value_bitlength = len('{:032b}'.format(int(_value)))
                if value_bitlength > 32:
                    raise TranspilerExceptions.Overflow(_var, [_type, len(value_bitlength)], 32)

            if _type == 'list' or _type == 'list_int':
                # Get total bitlength
                #_array_bits = [_["bitlen"] for _ in _value]
                value_bitlength = 0 #sum(_array_bits)
                _b_type = self.types[_type.lower()]
                head_bitlength = len('{:08b}'.format(_b_type))
                # Update variable meta data with the references of it's contents
                meta = _value
                # overwrite value
                # val in a list is the length of it
                #print(_value)
                _value = len(_value)

            # Calculate Head bitlength
            if _type.lower() in self.types:
                _b_type = self.types[_type.lower()]
                _b_x = None # WIP
                head_bitlength =  len('{:08b}'.format(_b_type))
                value_bitlength = len('{:032b}'.format(int(_value)))

        #pprint(custom_constructor)
        bitlength = value_bitlength + head_bitlength

        if type(_value) == list and len(_value) > 2 and type(_value[2]) == int:
            pos = _value[2]
        else:
            pos = self.nextaddr
            self.nextaddr = self.nextaddr + round(bitlength / 8)
        
        array_elem = False
        if type(_value) == list and len(_value) > 2 and _value[2] == 'ARRAY_ELEM':
            # Fuck me sideways, time to grab the value from the address
            load_from_addr_template = f'''
            ; Load value for {_var} from {_value[1]}
            ldr r11, {_value[1]}
            ldr r0, $2
            jpr r2
            mov r28, r20
            '''
            array_elem = True


        if custom_pos:
            pos = custom_pos

        if math:

            registers = [12, 13]
            var_template = '''
            ; Load from {addr} for var {var}
            ldr r11, {addr}
            ldr r0, $2
            jpr r2
            mov r{reg}, r20
            '''
            value_template = '''
            ldr r{reg}, #{val}
            '''
            value_template_bitwise = '''
             
            '''

            # Check first and second if they are variables
            first_teplate = ""
            first = self.evaluate(first)
            if type(first) == str: # Probably a variable's ID
                if first not in self.variables:
                    raise TranspilerExceptions.UnkownVar(first, self.variables.keys)
                var = self.variables[first]
                first_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = first,
                    reg = registers[0]
                )
            else:
                if first[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(first, first[0], 'INT')
                first_teplate = value_template.format(reg = registers[0], val = first[1])

            second_teplate = ""
            second = self.evaluate(second)
            if type(second) == str: # Probably a variable's ID
                if second not in self.variables:
                    raise TranspilerExceptions.UnkownVar(second, self.variables.keys)
                var = self.variables[second]
                second_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = second,
                    reg = registers[1]
                )
            else:
                if second[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(second, second[0], 'INT')
                second_teplate = value_template.format(reg = registers[1], val = second[1])

            if operation in ['rsh', 'lsh']:
                if len(second) < 2:
                    raise Exception("Can't use variables in a shift")
                math_operation = f"{operation} r{registers[0]}, {second[1]}"
            else:
                math_operation = f"{operation} r{registers[0]}, r{registers[1]}, r{registers[0]}"

            final_template = f'''
            {first_teplate}
            {second_teplate}

            {math_operation}

            ; Store the result
            mov r20, r{registers[0]}
            '''


        # Add to map, but check flags first
        if array_elem:
            self.variables[_var] = {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "meta": meta
            }
            self.fin.append(
                f'''
                {load_from_addr_template}
                ; standard construction for {_var}
                ldr r11, {pos+ self.bitstart}
                mov r20, r28
                ldr r0, $2
                jpr r4
                ldr r28, 0
                '''
            )
            return {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "bitlen": bitlength
            }
        elif math:
            self.variables[_var] = {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "meta": meta
            }
            print(f"({_var}) -> {_value}\nValue: {_value[1]}\nPosition: {pos} ({pos + self.bitstart})\nBitLength: {bitlength}\nNextAddr: {self.nextaddr}")
            self.fin.append(
                f'''
                ; math construction for {_var}
                {final_template}
                ldr r11, {pos + self.bitstart}
                ldr r0, $2
                jpr r4
                '''
            )
            return {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "bitlen": bitlength
            }
        elif tree:
            self.variables[_var] = {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "meta": meta
            }
            print(f"({_var}) -> {_value}\nValue: {_value[1]}\nPosition: {pos} ({pos + self.bitstart})\nBitLength: {bitlength}\nNextAddr: {self.nextaddr}")
            self.fin.append(
                f'''
                ; standard construction for {_var}
                ldr r11, {pos + self.bitstart}
                ldr r20, #{_value[1]}
                ldr r0, $2
                jpr r4
                '''
            )
            return {
                "pos":pos,
                "val":_value[1],
                "type":_value[0],
                "bitlen": bitlength
            }
        else:
            self.fin.append(
                f'''
                ; custom_constructor: {custom_pos} {custom_constructor}
                ldr r11, {pos + self.bitstart}
                ldr r20, #{_value}
                ldr r0, $2
                jpr r4
                '''
            )
            return {
                "pos":pos,
                "val":_value,
                "type":_type,
                "bitlen": bitlength,
                "meta": meta
            }
    
    def create_embed(self, tree):
        TranspilerWarnings.EmbededASMEnabled()
        # Convert variablers sdsds
        if tree['ID'] == 'assembly':
            _vars = {}
            for var in self.variables:
                _vars[var] = self.bitstart + self.variables[var]['pos']
                # print(_vars,self.variables[var])

            self.fin.append(tree['CODE'][1]['VALUE'].format(**_vars))
        elif tree['ID'] == 'lk':
            text = open(tree['CODE'][1]['VALUE'],"r").read()
            from parser import ChParser, ChLexer
            parser = ChParser()
            lexer = ChLexer()
            ttree = parser.parse(lexer.tokenize(text))
            _t = Transpiler(
                ttree,
                nextaddr = self.nextaddr,
                variables = self.variables,
                functions = self.functions,
                label_count = self.labelcounter 
            )

            # Overwrite default bit-values
            _t.run()
            # Set main nextaddr to _t nextaddr
            self.nextaddr = _t.nextaddr
            # Update functions
            self.functions = _t.functions
            _program = '\n'.join(_t.fin)
            self.fin.append(_program)
            self.fin_funcs = [*self.fin_funcs, *_t.fin_funcs]
        else:
            raise Exception(f"Unknown format for embed {tree['ID']}")
    

    def advanced_write(self, tree):
        #pprint(tree)
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

        if value[0] in operations:
            first  = value[1]
            second = value[2]
            print(value)
            operation = operations[value[0]]
        
            registers = [12, 13]
            var_template = '''
            ; Load from {addr} for var {var}
            ldr r11, {addr}
            ldr r0, $2
            jpr r2
            mov r{reg}, r20
            '''
            value_template = '''
            ldr r{reg}, #{val}
            '''

            # Check first and second if they are variables
            first_teplate = ""
            first = self.evaluate(first)
            if type(first) == str: # Probably a variable's ID
                if first not in self.variables:
                    raise TranspilerExceptions.UnkownVar(first, self.variables.keys)
                var = self.variables[first]
                first_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = first,
                    reg = registers[0]
                )
            else:
                if first[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(first, first[0], 'INT')
                first_teplate = value_template.format(reg = registers[0], val = first[1])

            second_teplate = ""
            second = self.evaluate(second)
            if type(second) == str: # Probably a variable's ID
                if second not in self.variables:
                    raise TranspilerExceptions.UnkownVar(second, self.variables.keys)
                var = self.variables[second]
                second_teplate = var_template.format(
                    addr = var['pos']+self.bitstart,
                    var = second,
                    reg = registers[1]
                )
            else:
                if second[0] != 'INT':
                    raise TranspilerExceptions.TypeMissmatch(second, second[0], 'INT')
                second_teplate = value_template.format(reg = registers[1], val = second[1])

            if operation in ['rsh', 'lsh']:
                if len(second) < 2:
                    raise Exception("Can't use variables in a shift")
                math_operation = f"{operation} r{registers[0]}, {second[1]}"
            else:
                math_operation = f"{operation} r{registers[0]}, r{registers[1]}, r{registers[0]}"

            final_template = f'''
            {first_teplate}
            {second_teplate}

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
            if value[0] == "HEX":
                value = value[1]["VALUE"]
                final_template = f'''
                ldr r20, {value}
                '''
            if value[0] == "INT":
                value = value[1]["VALUE"]
                final_template = f'''
                ldr r20, #{value}
                '''
            elif value[0] == "ID":
                varaddr = self.variables[self.evaluate(value)]['pos'] + self.bitstart
                final_template = f'''
                ldr r11, {varaddr}
                ldr r0, $2
                jpr r2
                '''
            template = '''
            {final_template}
            ldr r14, {addr}

            {instr}
            '''


        type_instrs = {
            'byte': 'stb r20, r14',
            'halfword': 'sth r20, r14',
            'word': 'stw r20, r14',
        }

        self.fin.append(
            template.format(
                val = value,
                instr = type_instrs[_type],
                addr = addr,
                final_template = final_template
            )
        )


    def eval_int(self, tree, unsafe):
        if 'VALUE' in tree:
            if tree['VALUE'].isdigit():
                return ['INT', int(tree['VALUE'])]
            else:
                raise TranspilerExceptions.TypeMissmatch(tree)
        else:
            print(f"Malformed tree, missing a VALUE")

    def eval_id(self, tree, unsafe):
        return tree['VALUE']
    
    def eval_str(self, tree, unsafe):
        val = tree['VALUE']
        if len(val) == 1:
            return ['CHAR', val]
        else:
            items = []
            for char in val:
                # In case we have empty chars left over, wipe them
                if val.strip() == '':
                    items.append(
                        ('STRING', {'VALUE': chr(0)})
                    )
                else:
                    items.append(
                        ('STRING', {'VALUE': char})
                    )
            char_tree = { 'ITEMS': items}
            return self.construct_list(char_tree)
    
    def eval_int_array(self, tree, unsafe):
        val = tree['VALUE']
        if len(val) == 1:
            return ['INT', val]
        else:
            items = []
            for char in val:
                # In case we have empty chars left over, wipe them
                if val.strip() == '':
                    items.append(
                        ('INT', {'VALUE': str(0)})
                    )
                else:
                    items.append(
                        ('INT', {'VALUE': char})
                    )
            char_tree = { 'ITEMS': items}
            return self.construct_list(char_tree)
    
    def eval_typed(self, tree, unsafe):
        return [tree['TYPE'], tree['ID']]
    
    def eval_typed_len(self, tree, unsafe):
        if tree['LEN'][0].upper() != 'INT':
            raise TranspilerExceptions.TypeMissmatch('index', tree['LEN'][0], 'INT')
        return [tree['TYPE'], tree['ID'], int(tree['LEN'][1]['VALUE'])]
    
    def construct_list(self, tree, unsafe=False):
        # print("TREE:",tree)

        # Allocate address for the head
        if not unsafe:
            addr = self.nextaddr
            self.nextaddr = addr + round(40/8)
        else:
            unsafe = addr

        _items = []
        # For each item we need to create a new variable, cycle with offset?
        for i, item in enumerate(tree["ITEMS"]):
            t, v = self.evaluate(item)
            #print("TV:", t,v)
            _ = {
                "name": f'{i}_arrayval',
                "value": v,
                "type": t
            }
            if not unsafe:
                x = self.create_variable(custom_constructor = _)
            else:
                x = self.create_variable(custom_constructor = _,
                custom_pos=unsafe+(5*i))
            _items.append(x)
        #quit()
        # Caclulate the size of above objects and create array object
        return ['list', _items, addr]

    def compiler_eval(self, tree):
        if tree['KEY'] == "mode":
            TranspilerWarnings.ModesEnabled(tree['VALUE'][1]['VALUE'])
        if self.mode != "kernel" and\
             tree['KEY'] in ["bitstart", "bitend", "bitdata"]:
             raise TranspilerExceptions.UnauthorizedBitSet()

        value = tree['VALUE'][1]['VALUE']
        if value.isdigit():
            value = int(value)

        setattr(self, tree['KEY'], value)

    def create_dyn_while(self, tree):
        #pprint(tree)
        # Build conditional template first
        # r17 is our location
        # r26 is our first variable
        # r30 is our second variable
        load_var_template = '''
        ; store var addr
        ldr r11, {var}

        ; load from var addr
        ldr r0, $2
        jpr r2
        '''
        raw_val_template = '''
        ldr r20, {val}
        '''
        template = '''
        ; store jump locations
        ldr r18, ._while_end_{label}
        ldr r15, ._while_start_{label}

        ._while_start_{label}

        {first}

        ; save value to first var
        mov r26, r20

        {second}

        ; save value to second var
        mov r30, r20

        {comparison}
        
        {code}
        jpr r15

        ._while_end_{label}
        
        ldr r26, #0
        '''

        # Create internal program
        _t = Transpiler(
            tree['PROGRAM'],
            nextaddr = self.nextaddr,
            variables = self.variables,
            functions = self.functions,
            arguments= {},
            label_count = self.labelcounter 
        )

        # Overwrite default bit-values
        _t.run()

        # Set main nextaddr to _t nextaddr
        self.nextaddr = _t.nextaddr
        _program = '\n'.join(_t.fin)

        # Update our variables
        self.variables = _t.variables

        # Get condition
        # Evaluate our condition
        _condition = tree['CONDITION']
        condition = self.resolve_comparisons(_condition[0])

        # Evaluate our variables
        first_var = self.evaluate(_condition[1])
        second_var = self.evaluate(_condition[2])

        if type(first_var) == str:
            # got a variable
            if first_var not in self.variables:
                raise TranspilerExceptions.UnkownVar(first_var, self.variables.keys)
            else: first_var_tree = load_var_template.format(
                var = self.bitstart +  self.variables[first_var]['pos']
            )
        else:
            first_var_tree = raw_val_template.format(
                val = first_var[1]
            )
        
        if type(second_var) == str:
            if second_var not in self.variables:
                raise TranspilerExceptions.UnkownVar(second_var, self.variables.keys)
            else: second_var_tree = load_var_template.format(
                var = self.bitstart +  self.variables[second_var]['pos']
            )
        else:
            second_var_tree = raw_val_template.format(
                val = second_var[1]
            )

        template = template.replace("r17","r18").format(
            code = _program,
            first = first_var_tree,
            second = second_var_tree,
            comparison = condition.replace("r17","r18"),
            label=self.labelcounter
        )
        #print(template)

        #quit()

        self.fin.append(template)
        self.labelcounter += 1

        #quit()

    def create_conditional_tree(self, tree, unsafe=False):
        _if = tree["IF"]
        _else = None if tree["ELSE"][0] is None else tree["ELSE"]
        _else_if = None if tree["ELSE_IF"][0] is None else tree["ELSE_IF"]

        # pprint(_if)

        # Build conditional template first
        # r27 is our location
        # r26 is our first variable
        # r30 is our second variable
        template = '''
        ; store jump locations
        ldr r17, ._if_end_{label}
        ldr r16, ._else_end_{label}

        ; store first addr
        ldr r11, {first}

        ; load from first addr
        ldr r0, $2
        jpr r2

        ; save value to first var
        mov r26, r20

        ; store second addr
        ldr r11, {second}

        ; load from second addr
        ldr r0, $2
        jpr r2

        ; save value to second var
        mov r30, r20

        {comparison}
        
        {code}
        
        ; Jump to ._else_end_{label} if code has been run
        jpr r16

        ._if_end_{label}

        {else_code}

        ._else_end_{label}
        ldr r26, #0
        '''

        # Create internal program
        _t = Transpiler(
            _if[1]['CODE'],
            nextaddr = self.nextaddr,
            variables = self.variables,
            functions = self.functions,
            arguments= {},
            label_count = self.labelcounter 
        )

        # Overwrite default bit-values
        _t.run()

        # Set main nextaddr to _t nextaddr
        self.nextaddr = _t.nextaddr
        _program = '\n'.join(_t.fin)

        # Update our variables
        self.variables = _t.variables

        # Evaluate our condition
        _condition = _if[1]['CONDITION']
        condition = self.resolve_comparisons(_condition[0])

        # Evaluate our variables
        first_var = self.evaluate(_condition[1])
        second_var = self.evaluate(_condition[2])
        
        if first_var not in self.variables:
            raise TranspilerExceptions.UnkownVar(first_var, self.variables.keys)
        else: first_var_tree = self.variables[first_var]

        if second_var not in self.variables:
            raise TranspilerExceptions.UnkownVar(second_var, self.variables.keys)
        else: second_var_tree = self.variables[second_var]

        # pprint(first_var_tree)

        _else_program = "; No else constructed"

        if _else:
            # Build else
            # Create internal program
            _t = Transpiler(
                _else[1]['CODE'],
                nextaddr = self.nextaddr,
                variables = self.variables,
                functions = self.functions,
                arguments= {},
                label_count = self.labelcounter 
            )

            # Overwrite default bit-values
            _t.run()

            # Set main nextaddr to _t nextaddr
            self.nextaddr = _t.nextaddr
            _else_program = '\n'.join(_t.fin)

            # Update our variables
            self.variables = _t.variables

        template = template.format(
            code = _program,
            first = self.bitstart + first_var_tree['pos'],
            second = self.bitstart + second_var_tree['pos'],
            comparison = condition,
            else_code = _else_program,
            label=self.labelcounter
        )
        #print(template)

        #quit()

        self.fin.append(template)
        self.labelcounter += 1
    
    def resolve_comparisons(self, cmp):
        comparisons = {
            'EQEQ': 'jprne r17, r26, r30',
            'NOT_EQEQ': 'jpre r17, r26, r30',
            'LESS': 'jprgt r17, r26, r30',
            'GREATER': 'jprlt r17, r26, r30'
        }
        return comparisons[cmp]
    

    def get_index(self, tree, unsafe=False):
        _source = tree['EXPRESSION'][1]['VALUE']
        _index  = tree['INDEX'][1]['VALUE']


        if tree['INDEX'][0] == 'ID' and _index in self.variables:
            _index = self.variables[_index]['val']
        elif tree['INDEX'][0] != 'INT':
            raise TranspilerExceptions.InvalidIndexType(tree['INDEX'][0], 'INT')
        if _source not in self.variables:
            raise TranspilerExceptions.UnkownVar(_source, self.variables.keys)

        _index = int(_index)

        if _index < 0 or _index > int(self.variables[_source]['val']):
            raise TranspilerExceptions.OutOfBounds(_index, self.variables[_source]['val'])

        # print(tree)
        #pprint(self.variables[_source]['meta'])

        type = self.variables[_source]['meta'][_index]['type']
        position = self.variables[_source]['meta'][_index]['pos'] + self.bitstart

        #print(_source)

        return [type, position, 'ARRAY_ELEM']

    def resolve_list_compiler(self, char_array):
        out = ""
        for x in char_array:
            out += chr(x['val'])
        return out

    def eval_hex(self, tree, unsafe):
        return ['INT', int(tree['VALUE'], 0)]


    def evaluate(self, tree, unsafe=False):
        acts = {
            'INT': self.eval_int,
            'STRING': self.eval_str,
            'ID': self.eval_id,
            'LIST': self.construct_list,
            'GET_INDEX': self.get_index,
            'TYPED': self.eval_typed,
            'TYPED_LEN': self.eval_typed_len,
            'INT_ARRAY': self.eval_int_array,
            'HEX': self.eval_hex
            #'ADD': self.eval_add
        }

        if tree[0] in acts:
            return acts[tree[0]](tree[1], unsafe)
        else:
            print(f"Unkown action during evaluation: {tree[0]}")
