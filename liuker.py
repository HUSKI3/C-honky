from sys import argv
from asm import Loader

if len(argv) < 2: 
    raise Exception("Usage: liuker.py <input> <output> <flags(Optional)> ")

flags = argv[-1]

l = Loader(
    argv[1],
    argv[2]
)

# Write debug
if "d" in flags.split():
    with open(str(argv[2]) + "_debug", "w+") as f: [f.write(f'{_}\n') for _ in l.complete]

# Write Processed
open(argv[2], 'wb+').write(l.Processed)