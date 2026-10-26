"""guardian/test_lexer.py — Step 1: Lexer tests"""
import sys
from lexer import Lexer, LexError
from tokens import TokenType

PASS="\033[32m✓\033[0m"; FAIL="\033[31m✗\033[0m"
results=[]

def test(name,fn):
    try: fn(); results.append((True,name)); print(f"  {PASS}  {name}")
    except Exception as e: results.append((False,name)); print(f"  {FAIL}  {name}  →  {e}")

def types(src):
    return [t.type for t in Lexer(src).tokenize() if t.type!=TokenType.EOF]

print("\n── Step 1: Lexer Tests ──────────────────────────────\n")

test("Integer 42",              lambda: [assert_(t.value==42) for t in Lexer("42").tokenize() if t.type==TokenType.INTEGER][0] if True else None)

# Simpler approach
def t1():
    t=Lexer("42").tokenize(); assert t[0].type==TokenType.INTEGER; assert t[0].value==42
test("Integer literal → 42", t1)

def t2():
    t=Lexer("3.14").tokenize(); assert t[0].type==TokenType.FLOAT; assert abs(t[0].value-3.14)<1e-9
test("Float literal → 3.14", t2)

def t3():
    t=Lexer('"hello"').tokenize(); assert t[0].type==TokenType.STRING; assert t[0].value=="hello"
test("String literal → \"hello\"", t3)

def t4():
    t=Lexer(r'"a\nb"').tokenize(); assert t[0].value=="a\nb"
test("String escape \\n", t4)

def t5():
    t=Lexer("true").tokenize(); assert t[0].type==TokenType.BOOL; assert t[0].value==True
test("Boolean → true", t5)

def t6():
    t=Lexer("false").tokenize(); assert t[0].value==False
test("Boolean → false", t6)

def t7():
    assert TokenType.NULL in types("null")
test("Keyword → null", t7)

def t8():
    tt=types("say ask set to otherwise repeat define stop skip use")
    assert TokenType.SAY in tt; assert TokenType.ASK in tt; assert TokenType.SET in tt
    assert TokenType.OTHERWISE in tt; assert TokenType.REPEAT in tt
    assert TokenType.STOP in tt; assert TokenType.SKIP in tt
test("Natural language keywords", t8)

def t9():
    t=Lexer("give back").tokenize(); assert t[0].type==TokenType.GIVE_BACK
test("give back → GIVE_BACK", t9)

def t10():
    t=Lexer("for each").tokenize(); assert t[0].type==TokenType.FOR_EACH
test("for each → FOR_EACH", t10)

def t11():
    t=Lexer("is not").tokenize(); assert t[0].type==TokenType.IS_NOT
test("is not → IS_NOT", t11)

def t12():
    t=Lexer("is greater than").tokenize(); assert t[0].type==TokenType.IS_GREATER
test("is greater than → IS_GREATER", t12)

def t13():
    t=Lexer("is less than").tokenize(); assert t[0].type==TokenType.IS_LESS
test("is less than → IS_LESS", t13)

def t14():
    t=Lexer("is at least").tokenize(); assert t[0].type==TokenType.IS_AT_LEAST
test("is at least → IS_AT_LEAST", t14)

def t15():
    t=Lexer("is at most").tokenize(); assert t[0].type==TokenType.IS_AT_MOST
test("is at most → IS_AT_MOST", t15)

def t16():
    tt=types("+ - * / % **")
    for tp in [TokenType.PLUS,TokenType.MINUS,TokenType.STAR,TokenType.SLASH,TokenType.PERCENT,TokenType.POWER]:
        assert tp in tt
test("Arithmetic operators", t16)

def t17():
    tt=types("== != < > <= >=")
    for tp in [TokenType.EQ,TokenType.NEQ,TokenType.LT,TokenType.GT,TokenType.LTE,TokenType.GTE]:
        assert tp in tt
test("Comparison operators", t17)

def t18():
    t=Lexer("x = 1").tokenize(); assert TokenType.ASSIGN in [tok.type for tok in t]
    t2=Lexer("x == 1").tokenize(); assert TokenType.EQ in [tok.type for tok in t2]
test("= vs == distinct", t18)

def t19():
    tt=types("and or not"); assert TokenType.AND in tt; assert TokenType.OR in tt; assert TokenType.NOT in tt
test("Logical operators and or not", t19)

def t20():
    tt=types("( ) [ ] , . : ;")
    for tp in [TokenType.LPAREN,TokenType.RPAREN,TokenType.LBRACKET,TokenType.RBRACKET,
               TokenType.COMMA,TokenType.DOT,TokenType.COLON,TokenType.SEMICOLON]:
        assert tp in tt
test("Delimiter tokens", t20)

def t21():
    t=Lexer("myVar").tokenize(); assert t[0].type==TokenType.IDENTIFIER; assert t[0].value=="myVar"
test("Identifier", t21)

def t22():
    tt=types("42 # comment"); assert TokenType.INTEGER in tt
    assert len([x for x in tt if x!=TokenType.NEWLINE])==1
test("Comment skipped", t22)

def t23():
    src="x = 1\ny = 2\n"; tt=types(src); assert tt.count(TokenType.ASSIGN)==2
test("Multi-line NEWLINE tokens", t23)

def t24():
    src="if x\n    y = 1\n"; tt=types(src); assert TokenType.INDENT in tt
test("Indent → INDENT token", t24)

def t25():
    src="if x\n    y=1\nz=2\n"; tt=types(src); assert TokenType.DEDENT in tt
test("Block close → DEDENT token", t25)

def t26():
    src='app T\n    say "Hello"\n'; tt=types(src)
    assert TokenType.APP in tt; assert TokenType.SAY in tt; assert TokenType.STRING in tt
test("Guardian app + say snippet", t26)

def t27():
    try: Lexer("x = @").tokenize(); assert False
    except LexError as e: assert "unrecognised" in str(e)
test("Illegal char → LexError", t27)

def t28():
    try: Lexer('"no end').tokenize(); assert False
    except LexError: pass
test("Unterminated string → LexError", t28)

def t29():
    toks=[t for t in Lexer("x = 1\ny = 2").tokenize() if t.type==TokenType.IDENTIFIER]
    assert toks[0].line==1; assert toks[1].line==2
test("Line tracking across newlines", t29)

def t30():
    # f-string interpolation
    t=Lexer('"Hello {name}!"').tokenize()
    assert t[0].type==TokenType.FSTRING
    assert any(isinstance(p,tuple) and p[0]=='expr' for p in t[0].value)
test("F-string {expr} → FSTRING token", t30)

# Fix: remove the bad first test (duplicate)
results.pop(0)

passed=sum(1 for ok,_ in results if ok); total=len(results)
print(f"\n── Results: {passed}/{total} passed ─────────────────────────\n")
if passed<total: sys.exit(1)
