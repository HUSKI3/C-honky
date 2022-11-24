from re import split 
from inspect import signature
from time import time
# from columnar import columnar
legacy_print = print
# --- Rich ---
# from rich import print
# from rich.prompt import Prompt
# from rich.progress import Progress, wrap_file
# from rich.console import Console as RConsole
# from rich.markdown import Markdown
# from rich.text import Text
# ------------
# console = RConsole()

class colours:
    '''
    Contains:
    reset,
    underline,
    cyan,
    blue,
    red
    '''
    reset = '\033[0;37;40m'
    underline = '\033[2;37;40m'
    cyan = '\033[1;36;40m'
    blue = '\033[1;34;40m'
    red = '\033[1;31;40m'



def LangProc(cls):
    for name, func in cls.__dict__.items():
        if hasattr(func, '_lang_instance'):
            if func.__doc__:
                cls.instructions[func.__doc__.strip('?')] = func
                if '!labels' in func.__doc__:
                    cls.instructions[name] = func
                    cls.instructions[name]._lang_instance["labels"] = True
            else:
                cls.instructions[name] = func
    return cls


#######################
### lang definition ###
from .rules import Lang
#######################

class Loader:
    def __init__(
            self,
            file: str,
            out:  str
        ) -> None:

        start = time()
        self.labels = {}
        #with console.status(f"Warming up language instructions", spinner="arc") as spin:
        self.lang = Lang()
        #print(self.lang.instructions)
        print("Instructions processed and ready")
        self.code = open(file, 'r').read()
        self.code = '\n'.join([_ if _.strip() and _[0] != ';' else '' for _ in self.code.split('\n')])
        self.complete = None
        self.parse_labels()
        self.Processed = self.translate(self.code)
        end = time()
        print(f"Done in {round(end - start)}s")
        #print(cm)
    
    def parse_labels(self, raw=False):
        lnum = 0
        for l in [_.strip() for _ in self.code.split('\n')]:
            if l:
                # Label
                if l[0] == '.':
                    self.labels[l[1:]] = lnum
                    #print(l, lnum)
                    continue
                if l[0:4] == 'ldr ':
                    lnum += 8
                    continue
                # Comment
                if l[0] == ';':
                    continue
                
                #print(l)
                lnum += 4

    def translate(self, code) -> bytearray:
        complete = []
        line = 0
        for index, inst in enumerate([_.strip() for _ in self.code.split('\n') if _.strip()]):
            if not inst:
                continue

            cur = split(r"[, ]+", inst) 
            
            if cur[0][0] == '.'\
                or cur[0][0] == ';':
                continue
            
            if cur[0] in self.lang.instructions:
                # Process next liner?
                #print(cur[-1])
                if cur[-1].startswith('$'):
                    total = 0
                    nextlinecount = int(cur[-1].replace('$','')) if cur[-1].replace('$','') != '' else 0
                    if nextlinecount:
                        # Read ahead
                        for inst in [_.strip() for _ in self.code.split('\n') if _.strip()][index:index+nextlinecount][1:]:
                            inst = split(r"[, ]+", inst) 
                            try:
                                if inst[0] == ';':
                                    print(inst, nextlinecount)
                                    print("Something really bad happened, failed to read ahead!")
                                    continue
                                func = self.lang.instructions[
                                    inst[0]
                                ]
                                if func._lang_instance["labels"] == True:
                                    inst.append(self.labels)
                                # Fuck it
                                for i, _ in enumerate(inst):
                                    #print(_)
                                    if isinstance(_, dict):
                                        continue
                                    if _ and _[0] == '$':
                                        inst[i] = "69"
                                    if _ and _[0] == '#':
                                        inst[i] = "69"
                                x = func(
                                    *inst[1:]
                                )
                            except TypeError as e:
                                print(f"{e} :: Failed to match required arguments for [{inst[0]}].\nGot: {inst[1:]}")
                                quit()
                            total += len(x)

                    cur[-1] = str(
                        hex(line + 8 + total)
                    )


                if cur[-1].startswith('#'):
                    num = int(cur[-1].replace('#','')) if cur[-1].replace('#','') != '' else 0
                    cur[-1] = str(
                        hex(num)
                    )
                    #print(hex(num), num)
                    #input()
                #print(line, cur)
                #input()
                try:
                    func = self.lang.instructions[
                        cur[0]
                    ]
                    if func._lang_instance["labels"] == True:
                        cur.append(self.labels)
                    x = func(
                        *cur[1:]
                    )
                except TypeError as e:
                    print(f"{e} :: Failed to match required arguments for [{cur[0]}].\nGot: {cur[1:]}")
                    quit()
                #print(colours.blue,f"[{line}]\t", colours.reset, '\t'.join([str(_) for _ in x]), '\t\t', ' '.join([str(_) for _ in cur]))
                #print(label, cur)
                #console.log(f"Created label data for {label.strip()}")
                line += len(x)
                complete = complete + x
            else:
                raise Exception(f"Unbound call {cur[0]}")
        complete = [int(c[1:]) if (type(c) != int and not c.isdigit() and c[0] == 'r') else int(c) for c in complete]
        # Debug?
        self.complete = complete
        return bytearray(complete)