from exceptions import ModuleExceptions, TranspilerExceptions
from modules import Module


from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
console = Console()
from rich import print as rprint

import inspect

import pprint
pprint = pprint.PrettyPrinter(indent=2).pprint

class Compiler:
    def __init__(
        self,
        tree,
        nextaddr = 0,
        variables = {}, #Dictlist(),
        functions = {},
        arguments = {},
        label_count = 0,
        bitdata_nextaddr = 0,
        namespace = 'main',
        bitstart = "0x10000000",
        bitdata  = "0x10200001"
    ) -> None:
        self.code = tree

        self.actions = {}

        self.variables: dict  = variables
        self.functions: dict  = functions
        self.arguments: dict  = arguments
        self.bitstart   = bitstart
        self.bitend     = None
        self.bitdata    = bitdata
        self.nextaddr   = nextaddr if nextaddr else int(bitstart, 0)
        self.bitdata_nextaddr = bitdata_nextaddr if bitdata_nextaddr else int(bitdata, 0)
        self.mode       = "standard"
        self.labelcounter = label_count
        self.namespace = namespace
        self.namespaces = {}
        self._modules = {}

        self.line = 1

        self.type_bit_length = {
            "char":1,
            "hex":2,
            "int8":2,
            "int16":3,
            "int32":4,
            "int":4,
            "list":1,
            "list_int":4
        }

        self.finished = []
        self.finished_funcs = []

        self.raw_modules = []

    def run(self):
        for action in self.code:
            if action[0] in self.actions:
                ret = self.actions[action[0]](action[1])
                if self.actions[action[0]].type == Module.MODULE_TYPES.SPECIAL_ACTION:
                    self.finished.append(ret)
                elif self.actions[action[0]].type == Module.MODULE_TYPES.SPECIAL_ACTION_FUNC:
                    self.finished_funcs.append(ret)
            else:
                raise TranspilerExceptions.UnknownActionReference(action[0])
            self.line += 1
    
    def new_instance(
        self,
        tree,
        nextaddr = 0,
        variables = {}, #Dictlist(),
        functions = {},
        arguments = {},
        label_count = 0,
        bitdata_nextaddr = 0,
        namespace = 'main',
        bitstart = "0x10000000",
        bitdata  = "0x10200001"
    ):
        instance = Compiler(
            tree,
            nextaddr,
            variables,
            functions,
            arguments,
            label_count,
            bitdata_nextaddr,
            namespace,
            bitstart,
            bitdata
        )

        # Modules and actions need to be recreated with a new scope

        instance.populate_modules_actions(
            self.raw_modules
        )

        #   instance.actions = self.actions
        #   instance._modules = self._modules

        return instance
    
    def populate_modules_actions(
        self,
        Modules: list[Module]
    ) -> None:
        self.raw_modules = Modules
        for module in Modules:
            modobj: Module = module(self)
            modobj.type = module.type
            if modobj.type == Module.MODULE_TYPES.FUNCTION:
                self.functions[module.name] = modobj
            else:
                self.actions[module.name] = modobj

            self._modules[module.name] = modobj
    
    def get_action(
        self,
        name
    ) -> Module:
        if name in self.actions:
            return self.actions[name]
        else:
            print(f"At {self.line}")
            raise TranspilerExceptions.ActionRequiredButNotFound(name, self.actions)
    
    def allocate(
        self,
        size
    ) -> hex:
        pos = self.nextaddr
        self.nextaddr += size
        return hex(pos)

    def sync(
        self,
        instance
    ):
        """
        Synchronize with the instance's values
        """
        self.nextaddr = instance.nextaddr
        self.bitdata_nextaddr = instance.bitdata_nextaddr

    def get_variable(
        self,
        name: str
    ) -> dict:
        if name in self.variables:
            return self.variables[name]
        else:
            print(f"At {self.line}")
            raise TranspilerExceptions.UnkownVar(name, self.variables)

    def create_variable(
        self,
        name: str, 
        pos: int,
        force = False
    ) -> None:
        if name in self.variables and not force:
            print(f"At {self.line}")
            raise TranspilerExceptions.VarExists(name)
        
        self.variables[name] = {
                "pos": pos,
            }
    
    def create_function(
        self,
        name: str, 
        obj: object
    ) -> None:
        self.functions[name] = {
                "object": obj,
            }

    def pause(self):
        rprint("[yellow bold]Compilation paused. Press enter to continue[/yellow bold]")
        input()

    def guide(
        self
    ) -> None:
        '''
        Display a guide block for debugging
        '''
        print('\n')
        table = Table(title=f"Compiler object of {self}")

        table.add_column("Module & Type", justify="right", style="cyan")
        table.add_column("Source", justify="right", style="green")
        table.add_column("Optimised [Bool/Code]", justify="right", style="white")
        table.add_column("Valid", justify="right", style="white")
        table.add_column("ID", justify="right", style="white")
        
        for module in self._modules:
            module: Module = self._modules[module]
            source = Syntax(
                inspect.getsource(module.proc_tree),
                "Python", 
                padding=1, 
                line_numbers=True
            )
            if module.optimise is None:
                optimise = "Unoptimised"
            else:
                optimise = Syntax(
                    inspect.getsource(module.optimise),
                    "Python", 
                    padding=1, 
                    line_numbers=True
                )
            table.add_row(f"{module.name}\n\n[red]{module.type}[/red]", source, optimise, str(module.verify()), hex(id(module)))

        console.print(table)