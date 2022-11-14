from . import LangProc

@LangProc
class Lang:
    instructions = {}

    def instruction(function, **kwargs):
        function._lang_instance = {
            "name"  : function.__name__,
            "bound" : kwargs.get('bound'),
            "compo" : kwargs.get('compound')
        } 
        return function

    @instruction
    def add(ra, rb, rc):
        return [
            0x00, ra, rb, rc
        ]
        
    @instruction
    def iadd(ra, rb):
        d = int(rb, base=16)
        # d = int(rb, base=16)
        #print([
        #    0x30, ra, (int(hex(d), 16) >> 8) & 0xff, int(hex(d), 16) & 0xff
        #])
        #input()
        return [
            0x30, ra, (int(hex(d), 16) >> 8) & 0xff, int(hex(d), 16) & 0xff
        ]
    
    @instruction
    def sub(ra, rb, rc):
        return [
            0x01, ra, rb, rc
        ]
    
    @instruction
    def isub(ra, rb):
        return [
            0x31, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]

    @instruction
    def mult(ra, rb, rc):
        return [
            0x02, ra, rb, rc
        ]
    
    @instruction
    def imult(ra, rb):
        return [
            0x32, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]

    @instruction
    def div(ra, rb, rc):
        return [
            0x03, ra, rb, rc
        ]
    
    @instruction
    def idiv(ra, rb):
        return [
            0x33, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]
    
    @instruction
    def aand(ra, rb, rc):
        '?and'
        return [
            0x04, ra, rb, rc
        ]
    
    @instruction
    def iand(ra, rb):
        return [
            0x34, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]
    
    @instruction
    def oor(ra, rb, rc):
        '?or'
        return [
            0x05, ra, rb, rc
        ]
    
    @instruction
    def ior(ra, rb):
        return [
            0x35, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]
    
    @instruction
    def xor(ra, rb, rc):
        return [
            0x06, ra, rb, rc
        ]
    
    @instruction
    def ixor(ra, rb):
        return [
            0x36, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]
    
    @instruction
    def nnot(ra, rb, rc):
        '?not'
        return [
            0x07, ra, rb, rc
        ]
    
    @instruction
    def inot(ra, rb):
        return [
            0x37, ra, (int(hex(int(rb, base=16)), 16) >> 8) & 0xff, int(hex(int(rb, base=16)), 16) & 0xff
        ]
    
    @instruction
    def lsh(ra, rb, labels):
        d = labels[rb[1:]] if (not rb.isdigit() and rb[0] == '.') else int(rb, base=16)
        return [
            0x08, ra, (d >> 8) & 0xff, d & 0xff
        ]
    
    @instruction
    def rsh(ra, rb, labels):
        d = labels[rb[1:]] if (not rb.isdigit() and rb[0] == '.') else int(rb, base=16)
        return [
            0x09, ra, (d >> 8) & 0xff, d & 0xff
        ]
    
    @instruction
    def ldru(ra, rb, labels):
        d = labels[rb[1:]] if (not rb.isdigit() and rb[0] == '.') else int(rb, base=16)
        return [
            0x10, ra, (d >> 8) & 0xff, d & 0xff
        ]
    
    @instruction
    def ldrl(ra, rb, labels):
        d = labels[rb[1:]] if (not rb.isdigit() and rb[0] == '.') else int(rb, base=16)
        return [
            0x11, ra, (d >> 8) & 0xff, d & 0xff
        ]
    
    @instruction
    def ldw(ra, rb):
        return [
            0x12, ra, 0x00, rb
        ]
    
    @instruction
    def ldh(ra, rb):
        return [
            0x13, ra, 0x00, rb
        ]
    
    @instruction
    def ldb(ra, rb):
        return [
            0x14, ra, 0x00, rb
        ]
    
    @instruction
    def stw(ra, rb):
        return [
            0x15, ra, 0x00, rb
        ]
    
    @instruction
    def sth(ra, rb):
        return [
            0x16, ra, 0x00, rb
        ]
    
    @instruction
    def stb(ra, rb):
        return [
            0x17, ra, 0x00, rb
        ]

    @instruction
    def jpr(ra):
        if not ra.startswith('r'):
            raise Exception("JPR only takes a register value!")
        return [
            0x18, ra, 0x00, 0x00
        ]

    @instruction
    def jpre(ra, rb, rc):
        return [
            0x19, ra, rb, rc
        ]
    
    @instruction
    def jprne(ra, rb, rc):
        return [
            0x20, ra, rb, rc
        ]

    @instruction
    def jprgt(ra, rb, rc):
        return [
            0x21, ra, rb, rc
        ]
    
    @instruction
    def jprlt(ra, rb, rc):
        return [
            0x22, ra, rb, rc
        ]
    
    @instruction
    def mov(ra, rb):
        return [
            0x23, ra, rb, 0x00
        ]
    
    @instruction
    def ldr(ra, rb, labels):
        d = labels[rb[1:]] if (not rb.isdigit() and rb[0] == '.') else int(rb, base=16)
        ldrl = [
            0x11, ra, (d >> 8) & 0xff, d & 0xff
        ]
        d >>= 16
        ldru = [
            0x10, ra, (d >> 8) & 0xff, d & 0xff
        ]
        #print(ldru, ldrl)
        return ldru + ldrl