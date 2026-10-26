"""Step 8 tests: increase/decrease, +=, imports, new G-codes, scanner fixes."""
import sys, os, tempfile, shutil
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter, RuntimeError_
from security import SecurityAnalyzer, SecurityError
from stdlib import build_stdlib

PASS="\033[32m✓\033[0m"; FAIL="\033[31m✗\033[0m"; results=[]
def test(name, fn):
    try: fn(); results.append((True,name)); print(f"  {PASS}  {name}")
    except Exception as e: results.append((False,name)); print(f"  {FAIL}  {name}  →  {type(e).__name__}: {e}")

def run(src, base=None):
    out=[]; tree=Parser(Lexer(src).tokenize()).parse()
    i=Interpreter(output_fn=out.append); build_stdlib(i.globals, output_fn=out.append)
    if base: i.base_dir=base
    i.run(tree); return out

def issues(src):
    tree=Parser(Lexer(src).tokenize()).parse()
    return [(i.code,i.level) for i in SecurityAnalyzer(strict=False).analyze(tree)]

print("\n── Step 8: Upgrade Tests ────────────────────────────\n")

def t1(): assert run('app T\n    set x to 1\n    increase x by 5\n    say x\n') == ['6']
test("increase x by 5", t1)
def t2(): assert run('app T\n    set x to 10\n    decrease x by 3\n    say x\n') == ['7']
test("decrease x by 3", t2)
def t3(): assert run('app T\n    set x to 0\n    increase x\n    increase x\n    say x\n') == ['2']
test("increase x  (defaults to 1)", t3)
def t4(): assert run('app T\n    set x to 2\n    x += 3\n    x *= 4\n    say x\n') == ['20']
test("x += 3 and x *= 4", t4)
def t5(): assert run('app T\n    set n to 10\n    n -= 4\n    n /= 2\n    say n\n') == ['3']
test("x -= and x /=", t5)
def t6():
    assert run('app T\n    set i to 0\n    repeat while i is less than 3\n        increase i\n    say i\n') == ['3']
test("increase inside a loop", t6)

def t7():
    d=tempfile.mkdtemp()
    try:
        os.makedirs(d+"/lib")
        open(d+"/lib/h.grd","w").write('app H\n    define hi for n\n        give back "Hi " + n\n')
        assert run('app T\n    use "lib/h.grd"\n    say hi("Guardian")\n', base=d) == ['Hi Guardian']
    finally: shutil.rmtree(d)
test('use "lib/h.grd" imports functions', t7)

def t8():
    d=tempfile.mkdtemp()
    try:
        open(d+"/h.grd","w").write('app H\n    say "loaded"\n')
        out=run('app T\n    use "h.grd"\n    use "h.grd"\n', base=d)
        assert out==['loaded'], out
    finally: shutil.rmtree(d)
test("module loads only once", t8)

def t9():
    d=tempfile.mkdtemp()
    try:
        try: run('app T\n    use "../evil.grd"\n', base=d); assert False
        except RuntimeError_ as e: assert "escapes" in str(e)
    finally: shutil.rmtree(d)
test("import outside project folder → blocked at runtime", t9)

def t10():
    d=tempfile.mkdtemp()
    try:
        open(d+"/bad.grd","w").write('app B\n    set password to "x"\n')
        try: run('app T\n    use "bad.grd"\n', base=d); assert False
        except RuntimeError_ as e: assert "security scan" in str(e)
    finally: shutil.rmtree(d)
test("imported module with a vulnerability → refused", t10)

def t11(): assert ("G503","ERROR") in issues('app T\n    use "../x.grd"\n')
test("G503 — import outside project", t11)
def t12(): assert ("G501","ERROR") in issues('app T\n    set f to ask "File: "\n    read_file("data/" + f)\n')
test("G501 — path traversal via concat", t12)
def t13(): assert ("G501","WARN") in issues('app T\n    set f to ask "File: "\n    read_file(f)\n')
test("G501 — raw input as path (warn)", t13)
def t14(): assert not any(c=="G501" for c,_ in issues('app T\n    read_file("notes.txt")\n'))
test("G501 — fixed path is safe", t14)
def t15(): assert ("G502","WARN") in issues('app T\n    set token to ask "Token: "\n    say token\n')
test("G502 — printing a secret", t15)
def t16(): assert not any(c=="G502" for c,_ in issues('app T\n    say "hello"\n'))
test("G502 — normal say is safe", t16)

# scanner gap fixes
def t17(): assert ("G101","ERROR") in issues('app T\n    set u to ask "u: "\n    db.query("SELECT * FROM t WHERE n = \'{u}\'")\n')
test("G101 — SQL injection via {interpolation}", t17)
def t18(): assert ("G103","ERROR") in issues('app T\n    try\n        set password to "abc"\n    handle e\n        say e\n')
test("vulnerability inside try block is now caught", t18)
def t19(): assert ("G401","ERROR") in issues('app T\n    try\n        say 1 / 0\n    handle e\n        say e\n    always\n        say "x"\n')
test("G401 inside try block caught", t19)
test("parameterized query still not flagged as G101", lambda: (_ for _ in ()).throw(AssertionError("G101 false positive")) if ("G101","ERROR") in issues('app T\n    set u to ask "u: "\n    db.query("SELECT 1 WHERE n = ?", u)\n') else None)

passed=sum(ok for ok,_ in results); total=len(results)
print(f"\n── Results: {passed}/{total} passed ─────────────────────────\n")
sys.exit(0 if passed==total else 1)
