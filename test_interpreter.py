"""
guardian/test_interpreter.py
Tests for Step 3: Interpreter — runs Guardian programs end-to-end.
Run with:  python test_interpreter.py
"""
import sys
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter, RuntimeError_

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


def run(src, inputs=None):
    """Run Guardian source, return list of printed lines."""
    _input_iter = iter(inputs or [])
    output = []
    tokens = Lexer(src).tokenize()
    tree   = Parser(tokens).parse()
    interp = Interpreter(output_fn=lambda s: output.append(s))
    # patch 'ask' builtin to pull from inputs list
    interp.globals.set_local('ask', lambda prompt="": next(_input_iter, ""))
    interp.run(tree)
    return output


print("\n── Step 3: Interpreter Tests ────────────────────────\n")

# ── Literals & output ─────────────────────────────────────────────────────

def t1():
    out = run('app T\n    say "Hello, World!"\n')
    assert out == ["Hello, World!"]
test('say string literal', t1)

def t2():
    out = run('app T\n    say 42\n')
    assert out == ["42"]
test('say integer', t2)

def t3():
    out = run('app T\n    say true\n')
    assert out == ["true"]
test('say boolean', t3)

def t4():
    out = run('app T\n    say null\n')
    assert out == ["null"]
test('say null', t4)

# ── Variables ──────────────────────────────────────────────────────────────

def t5():
    out = run('app T\n    set x to 10\n    say x\n')
    assert out == ["10"]
test('set x to 10  →  say x', t5)

def t6():
    out = run('app T\n    x = 7\n    say x\n')
    assert out == ["7"]
test('classic x = 7  →  say x', t6)

def t7():
    out = run('app T\n    set a to 3\n    set b to 4\n    say a + b\n')
    assert out == ["7"]
test('set a + b  →  7', t7)

# ── Arithmetic ─────────────────────────────────────────────────────────────

def t8():
    out = run('app T\n    say 2 + 3 * 4\n')
    assert out == ["14"]   # 2 + (3*4)
test('precedence: 2 + 3 * 4 = 14', t8)

def t9():
    out = run('app T\n    say 10 / 4\n')
    assert out == ["2.5"]
test('division: 10 / 4 = 2.5', t9)

def t10():
    out = run('app T\n    say 2 ** 8\n')
    assert out == ["256"]
test('power: 2 ** 8 = 256', t10)

def t11():
    out = run('app T\n    say 10 % 3\n')
    assert out == ["1"]
test('modulo: 10 % 3 = 1', t11)

# ── String concatenation ────────────────────────────────────────────────────

def t12():
    out = run('app T\n    set name to "Guardian"\n    say "Hello " + name\n')
    assert out == ["Hello Guardian"]
test('string concat with variable', t12)

def t13():
    out = run('app T\n    say "Count: " + 5\n')
    assert out == ["Count: 5"]
test('string + number auto-converts', t13)

# ── Comparisons (natural language) ────────────────────────────────────────

def t14():
    out = run('app T\n    set x to 10\n    if x is greater than 5\n        say "big"\n')
    assert out == ["big"]
test('x is greater than 5  →  big', t14)

def t15():
    out = run('app T\n    set x to 3\n    if x is less than 5\n        say "small"\n')
    assert out == ["small"]
test('x is less than 5  →  small', t15)

def t16():
    out = run('app T\n    set x to 5\n    if x is 5\n        say "five"\n')
    assert out == ["five"]
test('x is 5  →  five', t16)

def t17():
    out = run('app T\n    set x to 4\n    if x is not 5\n        say "not five"\n')
    assert out == ["not five"]
test('x is not 5  →  not five', t17)

def t18():
    out = run('app T\n    set x to 5\n    if x is at least 5\n        say "yes"\n')
    assert out == ["yes"]
test('x is at least 5  →  yes', t18)

def t19():
    out = run('app T\n    set x to 4\n    if x is at most 5\n        say "yes"\n')
    assert out == ["yes"]
test('x is at most 5  →  yes', t19)

# ── if / otherwise ────────────────────────────────────────────────────────

def t20():
    out = run('app T\n    set x to 2\n    if x is greater than 5\n        say "big"\n    otherwise\n        say "small"\n')
    assert out == ["small"]
test('if / otherwise  →  small', t20)

def t21():
    out = run('app T\n    set x to 10\n    if x is greater than 20\n        say "huge"\n    otherwise if x is greater than 5\n        say "medium"\n    otherwise\n        say "small"\n')
    assert out == ["medium"]
test('if / otherwise if / otherwise chain', t21)

# ── repeat while ──────────────────────────────────────────────────────────

def t22():
    out = run('app T\n    set i to 1\n    repeat while i is at most 3\n        say i\n        set i to i + 1\n')
    assert out == ["1","2","3"]
test('repeat while  →  counts 1 2 3', t22)

def t23():
    out = run('app T\n    set i to 0\n    repeat while i is less than 5\n        set i to i + 1\n        if i is 3\n            stop\n    say i\n')
    assert out == ["3"]
test('stop (break) exits loop at 3', t23)

def t24():
    out = run('app T\n    set i to 0\n    repeat while i is less than 5\n        set i to i + 1\n        if i is 3\n            skip\n        say i\n')
    assert out == ["1","2","4","5"]
test('skip (continue) skips 3', t24)

# ── for each ──────────────────────────────────────────────────────────────

def t25():
    out = run('app T\n    for each n in range(3)\n        say n\n')
    assert out == ["0","1","2"]
test('for each n in range(3)', t25)

def t26():
    src = 'app T\n    set fruits to list("apple","banana","mango")\n    for each f in fruits\n        say f\n'
    out = run(src)
    assert out == ["apple","banana","mango"]
test('for each in list', t26)

# ── define / give back ────────────────────────────────────────────────────

def t27():
    src = 'app T\n    define greet for name\n        say "Hi " + name\n    greet("Guardian")\n'
    out = run(src)
    assert out == ["Hi Guardian"]
test('define greet for name  →  Hi Guardian', t27)

def t28():
    src = 'app T\n    define add for a, b\n        give back a + b\n    set result to add(3, 4)\n    say result\n'
    out = run(src)
    assert out == ["7"]
test('define add  →  give back a + b  →  7', t28)

def t29():
    src = 'app T\n    define fact for n\n        if n is at most 1\n            give back 1\n        give back n * fact(n - 1)\n    say fact(5)\n'
    out = run(src)
    assert out == ["120"]
test('recursive factorial fact(5) = 120', t29)

# ── ask (input) ────────────────────────────────────────────────────────────

def t30():
    src = 'app T\n    set name to ask "Your name: "\n    say "Hello " + name\n'
    out = run(src, inputs=["Hoysal"])
    assert out == ["Hello Hoysal"]
test('ask prompt  →  Hello Hoysal', t30)

# ── Built-ins ──────────────────────────────────────────────────────────────

def t31():
    out = run('app T\n    say length("Guardian")\n')
    assert out == ["8"]
test('built-in length("Guardian") = 8', t31)

def t32():
    out = run('app T\n    say abs(-42)\n')
    assert out == ["42"]
test('built-in abs(-42) = 42', t32)

def t33():
    out = run('app T\n    say max(3, 7)\n')
    assert out == ["7"]
test('built-in max(3,7) = 7', t33)

def t34():
    out = run('app T\n    say round(3.567, 2)\n')
    assert out == ["3.57"]
test('built-in round(3.567, 2) = 3.57', t34)

# ── Error handling ──────────────────────────────────────────────────────────

def t35():
    try:
        run('app T\n    say undefined_var\n')
        assert False,"should raise"
    except RuntimeError_ as e:
        assert "not defined" in str(e)
test("undefined variable  →  RuntimeError", t35)

def t36():
    try:
        run('app T\n    say 1 / 0\n')
        assert False,"should raise"
    except RuntimeError_ as e:
        assert "division by zero" in str(e)
test("division by zero  →  RuntimeError", t36)

# ── Scope ─────────────────────────────────────────────────────────────────

def t37():
    src = 'app T\n    set x to 1\n    define bump for n\n        give back n + 1\n    set x to bump(x)\n    say x\n'
    out = run(src)
    assert out == ["2"]
test('function does not pollute outer scope', t37)

def t38():
    # closure: inner function sees outer variable
    src = 'app T\n    set prefix to "Hello"\n    define greet for name\n        say prefix + " " + name\n    greet("World")\n'
    out = run(src)
    assert out == ["Hello World"]
test('closure: inner func sees outer variable', t38)

# ── Real Guardian program ───────────────────────────────────────────────────

def t39():
    src = '''app FizzBuzz
    set i to 1
    repeat while i is at most 15
        if i % 3 == 0 and i % 5 == 0
            say "FizzBuzz"
        otherwise if i % 3 == 0
            say "Fizz"
        otherwise if i % 5 == 0
            say "Buzz"
        otherwise
            say i
        set i to i + 1
'''
    out = run(src)
    expected = ["1","2","Fizz","4","Buzz","Fizz","7","8","Fizz","Buzz",
                "11","Fizz","13","14","FizzBuzz"]
    assert out == expected, f"got {out}"
test('FizzBuzz 1–15', t39)

def t40():
    src = '''app Grader
    define grade for score
        if score is at least 90
            give back "A"
        otherwise if score is at least 80
            give back "B"
        otherwise if score is at least 70
            give back "C"
        otherwise
            give back "F"
    say grade(95)
    say grade(82)
    say grade(71)
    say grade(55)
'''
    out = run(src)
    assert out == ["A","B","C","F"]
test('Grade calculator A B C F', t40)

# ── Summary ────────────────────────────────────────────────────────────────

passed = sum(1 for ok,_ in results if ok)
total  = len(results)
print(f"\n── Results: {passed}/{total} passed ─────────────────────────\n")
if passed < total:
    sys.exit(1)
