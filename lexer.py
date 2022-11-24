from sly import Lexer

class ChLexer(Lexer):
    tokens = {
        ID,
        FLOAT,
        INT,
        HEX,
        FUNC,
        CLASS,
        ARRAY,
        NAMESPACE,
        STRING,
        EQ_GREATER,
        EQ_LESS,
        EQEQ,
        PYTHON_CODE,
        COLON_COLON,
        IF,
        ELSE,
        TRUE,
        FALSE,
        NOT_EQEQ,
        WHILE,
        BREAK,
        SKIP,
        FOR,
        IN,
        DEL,
        RETURN,
        NULL,
        EQ_ADD,
        EQ_SUB,
        EQ_MUL,
        EQ_DIV,
        EQ_MOD,
        IMPORT,
        LIMPORT,
        SANDBOX,
        FARROW,
        TARROW,
        LET,
        TELSE,
        PYTHON_CODE_EXEC,
        OF,
        GLOBAL,
        DEFINE,
        DEBUG,
        DEPENDS,
        SELFISH,
        ENV,
        FROM,
        EMBED
    }
    literals = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "|",
        "&",
        "!",
        ">",
        "<",
        "=",
        "(",
        ")",
        "{",
        "}",
        ";",
        ",",
        ":",
        "[",
        "]",
        "\\",
        ".",
        "?",
        "^",
        "#",
        "_",
        "@"
    }

    ignore = " \t"
    ignore_comment_slash = r"//.*"

    HEX = r"0[xX][0-9a-fA-F]+"

    FLOAT = r"\d*\.\d+"
    INT = r"\d+"

    PYTHON_CODE = r"\$`[.\W\w]*?`"
    PYTHON_CODE_EXEC = r"\$e`[.\W\w]*?`"
    STRING = r'"[\s\S]*?"' #r"(\".*?(?<!\\)(\\\\)*\"|'.*?(?<!\\)(\\\\)*')"
    ID = r"(--[a-zA-Z_]([a-zA-Z0-9_]|!)*--|[a-zA-Z_]([a-zA-Z0-9_]|!)*)"
    ID["func"] = FUNC
    ID["class"] = CLASS
    ID["namespace"] = NAMESPACE
    ID["break"] = BREAK
    ID["skip"] = SKIP
    ID["true"] = TRUE
    ID["false"] = FALSE
    ID["while"] = WHILE
    ID["for"] = FOR
    ID["in"] = IN
    ID["if"] = IF
    ID["else"] = ELSE
    ID["del"] = DEL
    ID["null"] = NULL
    ID["return"] = RETURN
    ID["import"] = IMPORT
    ID["limport"] = LIMPORT
    ID["sandbox"] = SANDBOX
    ID["let"] = LET
    ID["of"] = OF
    ID["globals"] = GLOBAL
    ID["define"] = DEFINE
    ID["depends"] = DEPENDS
    ID["debugThis"] = DEBUG
    ID["selfish"] = SELFISH
    ID["env"] = ENV
    ID["from"] = FROM
    ID["embed"] = EMBED

    TARROW = r'->'
    FARROW = r'\=\=>'
    TELSE = r'\|\|'
    EQEQ = "=="
    NOT_EQEQ = r"!="
    EQ_GREATER = r"=>"
    EQ_LESS = r"=<"
    EQ_ADD = r"\+="
    EQ_SUB = r"-="
    EQ_MUL = r"\*="
    EQ_DIV = r"/="
    EQ_MOD = r"%="

    @_(r"\n+")
    def ignore_newline(self, t):
        self.lineno += len(t.value)