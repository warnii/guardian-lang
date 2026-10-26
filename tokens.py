from enum import Enum, auto

class TokenType(Enum):
    # Literals
    INTEGER=auto(); FLOAT=auto(); STRING=auto(); BOOL=auto(); NULL=auto()
    IDENTIFIER=auto()

    # ── Natural language keywords (Guardian style) ──
    APP=auto()           # app
    SAY=auto()           # say          → print
    ASK=auto()           # ask          → input
    SET=auto()           # set          → assignment start
    TO=auto()            # to           → "set x to"
    GIVE_BACK=auto()     # give back    → return
    OTHERWISE=auto()     # otherwise    → else
    REPEAT=auto()        # repeat       → while prefix
    FOR_EACH=auto()      # for each     → for..in
    EACH=auto()          # each         (part of for each)
    DEFINE=auto()        # define       → func
    FOR=auto()           # for          (kept for compatibility)
    IN=auto()            # in
    STOP=auto()          # stop         → break
    SKIP=auto()          # skip         → continue
    USE=auto()           # use          → require (with verification)
    SECURE=auto()        # secure       → safe block marker
    TRY=auto()           # try
    HANDLE=auto()        # handle       → catch
    ALWAYS=auto()        # always       → finally


    # Still-valid classic keywords (can mix styles)
    IF=auto(); WHILE=auto(); RETURN=auto(); FUNC=auto()

    # Multi-word comparison tokens (lexer produces these)
    IS=auto()            # is           → ==  (or start of compound)
    IS_NOT=auto()        # is not       → !=
    IS_GREATER=auto()    # is greater than  → >
    IS_LESS=auto()       # is less than     → <
    IS_AT_LEAST=auto()   # is at least      → >=
    IS_AT_MOST=auto()    # is at most       → <=

    # Operators
    ASSIGN=auto(); PLUS=auto(); MINUS=auto(); STAR=auto(); SLASH=auto()
    PERCENT=auto(); POWER=auto()
    EQ=auto(); NEQ=auto(); LT=auto(); GT=auto(); LTE=auto(); GTE=auto()
    AND=auto(); OR=auto(); NOT=auto()

    # Delimiters
    LPAREN=auto(); RPAREN=auto(); LBRACE=auto(); RBRACE=auto()
    LBRACKET=auto(); RBRACKET=auto()
    COMMA=auto(); DOT=auto(); COLON=auto(); SEMICOLON=auto()
    NEWLINE=auto(); INDENT=auto(); DEDENT=auto()
    INCREASE=auto(); DECREASE=auto(); BY=auto()
    FSTRING=auto()        # f-string with {expr} interpolation
    EOF=auto(); ILLEGAL=auto()

# Single-word keywords → token type
KEYWORDS = {
    "app":TokenType.APP,
    "say":TokenType.SAY,
    "ask":TokenType.ASK,
    "set":TokenType.SET,
    "to":TokenType.TO,
    "otherwise":TokenType.OTHERWISE,
    "repeat":TokenType.REPEAT,
    "each":TokenType.EACH,
    "define":TokenType.DEFINE,
    "for":TokenType.FOR,
    "in":TokenType.IN,
    "stop":TokenType.STOP,
    "skip":TokenType.SKIP,
    "use":TokenType.USE,
    "secure":TokenType.SECURE,
    "try":     TokenType.TRY,
    "handle":  TokenType.HANDLE,
    "always":  TokenType.ALWAYS,
    "increase": TokenType.INCREASE,
    "decrease": TokenType.DECREASE,
    "by":       TokenType.BY,

    "if":TokenType.IF,
    "while":TokenType.WHILE,
    "return":TokenType.RETURN,
    "func":TokenType.FUNC,
    "is":TokenType.IS,        # may become compound — handled in lexer
    "and":TokenType.AND,
    "or":TokenType.OR,
    "not":TokenType.NOT,
    "true":TokenType.BOOL,
    "false":TokenType.BOOL,
    "null":TokenType.NULL,
    "give":TokenType.IDENTIFIER,   # "give" alone → resolved in lexer
    "back":TokenType.IDENTIFIER,   # "back" alone → resolved in lexer
    "greater":TokenType.IDENTIFIER,
    "less":TokenType.IDENTIFIER,
    "than":TokenType.IDENTIFIER,
    "at":TokenType.IDENTIFIER,
    "least":TokenType.IDENTIFIER,
    "most":TokenType.IDENTIFIER,
}

class Token:
    __slots__ = ("type","value","line","col")
    def __init__(self,type_,value,line,col):
        self.type=type_; self.value=value; self.line=line; self.col=col
    def __repr__(self):
        return f"Token({self.type.name},{self.value!r},{self.line}:{self.col})"
