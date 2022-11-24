from lexer import ChLexer
from parser import ChParser
import pprint
from main import Transpiler

from sys import argv

if len(argv) < 2: 
    raise Exception("Usage: chonky <input> <output>")

flags = argv[-1]

text = open(argv[1],"r").read()
lexer = ChLexer()
parser = ChParser()
pprint = pprint.PrettyPrinter(indent=2).pprint

for tok in lexer.tokenize(text):
    pprint(tok)

tree = parser.parse(lexer.tokenize(text))
t = Transpiler(tree)
t.run()
finished_asm = '\n'.join(t.fin)
finished_func_asm = '\n'.join(t.fin_funcs)

base = open("base.asm","r").read().format(code=finished_asm, func_code=finished_func_asm)

f =  open('out.asm', 'w')
for line in base.split('\n'):
    f.write(line.strip() + "\n")
f.close()

print("Variables:")
pprint(t.variables)


from asm import Loader
l = Loader(
    'out.asm',
    argv[2]
)

# Write debug
if "d" in flags.split():
    with open(str(argv[2]) + "_debug", "w+") as f: [f.write(f'{_}\n') for _ in l.complete]

# Write Processed
open(argv[2], 'wb+').write(l.Processed)

print(f"Build complete --> {argv[2]}")
