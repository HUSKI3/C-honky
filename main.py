from lexer import ChLexer
from parser import ChParser
from compiler import Compiler
from exceptions import *
from modules import (
    Module,
    PutCharMod,
    FunctionCallMod,
    ResolutionMod,
    VariableAssignMod,
    FunctionDecMod,
    VariableReAssignMod,
    ConditionalMod,
    ForLoopCompileTimeMod,
    EmbedMod,
    VariableReAssignAtIndexMod,
    ClassDeclarationMod,
    WhileMod,
    AdvancedWriteMod
)

import pprint
pprint = pprint.PrettyPrinter(indent=2).pprint

### Rich definitions ###
std_print = print
from rich import print
from rich.console import Console
console = Console()
from rich.progress import Progress
from rich.traceback import install
from rich.syntax import Syntax
install()
########################

### Args proc ###
from sys import argv
flags = ''
if len(argv) < 1: 
    raise Exception("Usage: chonky <input>")
if len(argv) >= 4:
    flags = argv[3]
#################

### Read file ###
text = open(argv[1],"r").read()
#################

### Construct tree ###
lexer = ChLexer()
parser = ChParser()
######################

### Tasks ###

# Works only on functions that support tasks
def construct_task(
    progress, 
    task,
    target,
    *args,
    tasklen = 100
):
    def _run_task():
        return target(
            *args,
            task = task,
            progress = progress,
            tasklen = tasklen
        )
    return _run_task

with Progress(
    refresh_per_second = 100
) as total_progress:
    # Lex 
    lex = total_progress.add_task("Lex...", total=100)
    lexed_tokens = lexer.tokenize(text)
    # Increases time it takes, but makes it possible to track tree building
    lexed_len    = len(list(lexer.tokenize(text)))
    total_progress.update(lex, advance=100)

    # Build tree task
    build_tree = total_progress.add_task("Building tree...", total=1000)
    build_tree_task = construct_task(
        total_progress,
        build_tree,
        parser.parse,
        lexed_tokens,
        tasklen = lexed_len
    )

    tree = build_tree_task()
    # Force finish
    total_progress.update(build_tree, advance=1000)

    # Build root node
    root_compiler_instance = Compiler(
        tree, flags = flags
    )
    root_compiler_instance.populate_modules_actions([
        PutCharMod,
        FunctionCallMod,
        ResolutionMod,
        VariableAssignMod,
        FunctionDecMod,
        VariableReAssignMod,
        ConditionalMod,
        ForLoopCompileTimeMod,
        EmbedMod,
        VariableReAssignAtIndexMod,
        ClassDeclarationMod,
        WhileMod,
        AdvancedWriteMod
    ])


print(f"\n[bold green]Tree complete, compiling...[/bold green]")

failed = False

try:
    root_compiler_instance.run()
except TranspilerExceptions.UnknownActionReference as e:
    root_compiler_instance.guide()
    console.print_exception()
    print(f"[bold]Possible actions:[/bold]\n{root_compiler_instance.actions}")
    failed = True

if failed:
    print(f"\n[bold red]Assembly build failed :cross_mark: [/bold red]")
    quit()
else:
    print(f"\n[bold green]Assembly build complete :heavy_check_mark: [/bold green]")
    final_asm = '\n'.join(root_compiler_instance.finished)
    # final_asm_pretty = Syntax(
    #                 final_asm,
    #                 "Asm", 
    #                 padding=1, 
    #                 line_numbers=True
    #             )
    # print(final_asm_pretty)
    final_func_asm = '\n'.join(root_compiler_instance.finished_funcs)
    # final_asm_pretty = Syntax(
    #                 "$ FUNCTIONS" + final_func_asm,
    #                 "Asm", 
    #                 padding=1, 
    #                 line_numbers=True
    #             )
    # print(final_asm_pretty)



# Once we are done put everything together
base = open("base.asm","r").read().format(code=final_asm, func_code=final_func_asm)
# Write
open('out.asm', 'w+').write(base)
#############

# # Assemble -- OUTDATED
# from asm import Loader
# l = Loader(
#     'out.asm',
#     argv[2]
# )
# open(argv[2], 'wb+').write(l.Processed)
# print(f"\n[bold green]Binary build complete with {root_compiler_instance.warnings} warnings :heavy_check_mark: [/bold green]")