"""
guardian/test_parser.py
Tests for Step 2: the Parser.
Run with:  python test_parser.py
"""

import sys
from lexer import Lexer
from parser import Parser, ParseError
from ast_nodes import *

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

results = []

def test(name, fn):
    try:
        fn()
        results.append((True, name))
        print(f"  {PASS}  {name}")
    except AssertionError as e:
        results.append((False, name))
        print(f"  {FAIL}  {name}  →  AssertionError: {e}")
    except Exception as e:
        results.append((False, name))
        print(f"  {FAIL}  {name}  →  {type(e).__name__}: {e}")


def parse(src):
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse()


print("\n── Step 2: Parser Tests ─────────────────────────────\n")

# 1. Minimal program
def t1():
    tree = parse("app Hello\n")
    assert isinstance(tree, Program)
    assert tree.name == "Hello"
    assert tree.body == []
test("Minimal program  →  Program node", t1)

# 2. Integer assignment
def t2():
    tree = parse("app T\n    x = 42\n")
    stmt = tree.body[0]
    assert isinstance(stmt, AssignStmt)
    assert stmt.name == "x"
    assert isinstance(stmt.value, IntLiteral)
    assert stmt.value.value == 42
test("Assignment  →  x = 42", t2)

# 3. Float assignment
def t3():
    tree = parse("app T\n    pi = 3.14\n")
    stmt = tree.body[0]
    assert isinstance(stmt.value, FloatLiteral)
    assert abs(stmt.value.value - 3.14) < 1e-9
test("Assignment  →  pi = 3.14", t3)

# 4. String assignment
def t4():
    tree = parse('app T\n    msg = "hello"\n')
    assert isinstance(tree.body[0].value, StringLiteral)
    assert tree.body[0].value.value == "hello"
test("Assignment  →  msg = \"hello\"", t4)

# 5. Boolean assignment
def t5():
    tree = parse("app T\n    flag = true\n")
    assert isinstance(tree.body[0].value, BoolLiteral)
    assert tree.body[0].value.value == True
test("Assignment  →  flag = true", t5)

# 6. Null assignment
def t6():
    tree = parse("app T\n    x = null\n")
    assert isinstance(tree.body[0].value, NullLiteral)
test("Assignment  →  x = null", t6)

# 7. Binary add
def t7():
    tree = parse("app T\n    z = 1 + 2\n")
    val = tree.body[0].value
    assert isinstance(val, BinOp)
    assert val.op == "+"
    assert isinstance(val.left,  IntLiteral)
    assert isinstance(val.right, IntLiteral)
test("BinOp  →  1 + 2", t7)

# 8. Operator precedence: * before +
def t8():
    tree = parse("app T\n    z = 1 + 2 * 3\n")
    val = tree.body[0].value
    # Should be  1 + (2 * 3)
    assert isinstance(val, BinOp)
    assert val.op == "+"
    assert isinstance(val.right, BinOp)
    assert val.right.op == "*"
test("Precedence  →  1 + 2 * 3  parses as  1 + (2*3)", t8)

# 9. Power right-associativity
def t9():
    tree = parse("app T\n    z = 2 ** 3 ** 2\n")
    val = tree.body[0].value
    # Should be  2 ** (3 ** 2)
    assert val.op == "**"
    assert isinstance(val.right, BinOp)
    assert val.right.op == "**"
test("Power  →  2**3**2  right-associative", t9)

# 10. Parenthesised expression
def t10():
    tree = parse("app T\n    z = (1 + 2) * 3\n")
    val = tree.body[0].value
    assert val.op == "*"
    assert isinstance(val.left, BinOp)
    assert val.left.op == "+"
test("Parens  →  (1 + 2) * 3", t10)

# 11. Unary minus
def t11():
    tree = parse("app T\n    z = -5\n")
    val = tree.body[0].value
    assert isinstance(val, UnaryOp)
    assert val.op == "-"
test("Unary minus  →  -5", t11)

# 12. not operator
def t12():
    tree = parse("app T\n    z = not true\n")
    val = tree.body[0].value
    assert isinstance(val, UnaryOp)
    assert val.op == "not"
test("Unary not  →  not true", t12)

# 13. Comparison
def t13():
    tree = parse("app T\n    z = x == 1\n")
    val = tree.body[0].value
    assert isinstance(val, BinOp)
    assert val.op == "=="
test("Comparison  →  x == 1", t13)

# 14. Logical and / or
def t14():
    tree = parse("app T\n    z = a and b or c\n")
    val = tree.body[0].value
    # or has lower precedence than and
    assert val.op == "or"
    assert val.left.op == "and"
test("Logical  →  a and b or c  →  (a and b) or c", t14)

# 15. Function call
def t15():
    tree = parse("app T\n    greet()\n")
    stmt = tree.body[0]
    assert isinstance(stmt, ExprStmt)
    assert isinstance(stmt.expr, CallExpr)
    assert isinstance(stmt.expr.callee, Identifier)
    assert stmt.expr.callee.name == "greet"
test("Call  →  greet()", t15)

# 16. Call with arguments
def t16():
    tree = parse('app T\n    add(1, 2)\n')
    call = tree.body[0].expr
    assert isinstance(call, CallExpr)
    assert len(call.args) == 2
test("Call  →  add(1, 2)  — two args", t16)

# 17. Member access
def t17():
    tree = parse("app T\n    x = db.name\n")
    val = tree.body[0].value
    assert isinstance(val, MemberAccess)
    assert val.member == "name"
test("MemberAccess  →  db.name", t17)

# 18. Method call  (member + call chained)
def t18():
    tree = parse('app T\n    db.connect("url")\n')
    stmt = tree.body[0].expr
    assert isinstance(stmt, CallExpr)
    assert isinstance(stmt.callee, MemberAccess)
    assert stmt.callee.member == "connect"
test("Method call  →  db.connect(\"url\")", t18)

# 19. Index access
def t19():
    tree = parse("app T\n    x = items[0]\n")
    val = tree.body[0].value
    assert isinstance(val, IndexAccess)
    assert isinstance(val.index, IntLiteral)
test("IndexAccess  →  items[0]", t19)

# 20. print statement
def t20():
    tree = parse('app T\n    say "hi"\n')
    stmt = tree.body[0]
    assert isinstance(stmt, PrintStmt)
    assert isinstance(stmt.value, StringLiteral)
test("PrintStmt  →  print(\"hi\")", t20)

# 21. if statement
def t21():
    src = "app T\n    if x == 1\n        y = 2\n"
    tree = parse(src)
    stmt = tree.body[0]
    assert isinstance(stmt, IfStmt)
    assert isinstance(stmt.condition, BinOp)
    assert isinstance(stmt.then_block, Block)
    assert stmt.else_block is None
test("IfStmt  →  if x == 1", t21)

# 22. if / else
def t22():
    src = "app T\n    if x == 1\n        y = 2\n    else\n        y = 3\n"
    tree = parse(src)
    stmt = tree.body[0]
    assert stmt.else_block is not None
    assert isinstance(stmt.else_block, Block)
test("IfStmt  →  if / else", t22)

# 23. while loop
def t23():
    src = "app T\n    while x > 0\n        x = x - 1\n"
    tree = parse(src)
    stmt = tree.body[0]
    assert isinstance(stmt, WhileStmt)
    assert isinstance(stmt.body, Block)
test("WhileStmt  →  while x > 0", t23)

# 24. for loop
def t24():
    src = "app T\n    for i in items\n        print(i)\n"
    tree = parse(src)
    stmt = tree.body[0]
    assert isinstance(stmt, ForStmt)
    assert stmt.var == "i"
test("ForStmt  →  for i in items", t24)

# 25. func definition
def t25():
    src = "app T\n    func greet(name)\n        print(name)\n"
    tree = parse(src)
    stmt = tree.body[0]
    assert isinstance(stmt, FuncDef)
    assert stmt.name == "greet"
    assert stmt.params == ["name"]
test("FuncDef  →  func greet(name)", t25)

# 26. return statement
def t26():
    src = "app T\n    func add(a, b)\n        return a + b\n"
    tree = parse(src)
    body = tree.body[0].body.statements
    ret = body[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BinOp)
test("ReturnStmt  →  return a + b", t26)

# 27. stop / continue
def t27():
    src = "app T\n    while true\n        stop\n"
    tree = parse(src)
    inner = tree.body[0].body.statements[0]
    assert isinstance(inner, BreakStmt)
test("BreakStmt inside while", t27)

# 28. require statement
def t28():
    src = 'app T\n    use "crypto"\n'
    tree = parse(src)
    stmt = tree.body[0]
    assert isinstance(stmt, RequireStmt)
    assert stmt.module == "crypto"
test("RequireStmt  →  require \"crypto\"", t28)

# 29. ParseError on missing app keyword
def t29():
    try:
        parse("x = 1\n")
        assert False, "should raise ParseError"
    except Exception as e:
        assert "ParseError" in type(e).__name__ or "expected APP" in str(e)
test("Missing 'app'  →  ParseError", t29)

# 30. Full Guardian snippet from the slides
def t30():
    src = '''app GuardianDemo
    set user to ask "Username"
    say "Welcome " + user
'''
    tree = parse(src)
    assert tree.name == "GuardianDemo"
    assert len(tree.body) == 2
    # first stmt: user = input(...)
    assign = tree.body[0]
    assert isinstance(assign, AssignStmt)
    assert assign.name == "user"
    # second stmt: print(...)
    assert isinstance(tree.body[1], PrintStmt)
test("Full Guardian slide snippet  →  correct AST", t30)

# ── Summary ───────────────────────────────────────────────────────────────
passed = sum(1 for ok, _ in results if ok)
total  = len(results)
print(f"\n── Results: {passed}/{total} passed ─────────────────────────\n")
if passed < total:
    sys.exit(1)
