"""
guardian/test_security.py
Tests for Step 4: Security Analyzer.
Run with:  python test_security.py
"""
import sys
from lexer import Lexer
from parser import Parser
from security import SecurityAnalyzer, SecurityError, SecurityIssue

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
        print(f"  {FAIL}  {name}  →  {e}")
    except Exception as e:
        results.append((False, name))
        print(f"  {FAIL}  {name}  →  {type(e).__name__}: {e}")


def analyze(src, strict=True):
    tokens = Lexer(src).tokenize()
    tree   = Parser(tokens).parse()
    return SecurityAnalyzer(strict=strict).analyze(tree)

def codes(src, strict=False):
    return [i.code for i in analyze(src, strict=strict)]

def raises_error(src, expected_code):
    try:
        analyze(src, strict=True)
        return False
    except SecurityError as e:
        return any(i.code == expected_code for i in e.issues)


print("\n── Step 4: Security Analyzer Tests ─────────────────\n")

# ── G101: SQL Injection ───────────────────────────────────────────────────

def t1():
    src = '''app T
    set user to ask "Username: "
    db.query("SELECT * FROM users WHERE name = " + user)
'''
    assert raises_error(src, "G101")
test("G101 — SQL injection via + concat in query call", t1)

def t2():
    src = '''app T
    set user to ask "Username: "
    db.select("SELECT * FROM users WHERE id = " + user)
'''
    assert raises_error(src, "G101")
test("G101 — SQL injection via + concat in select call", t2)

def t3():
    # safe: parameterized — no concat
    src = '''app T
    set user to ask "Username: "
    db.query("SELECT * FROM users WHERE name = ?", user)
'''
    c = codes(src)
    assert "G101" not in c, f"false positive: {c}"
test("G101 — parameterized query is SAFE (no false positive)", t3)

def t4():
    # safe: only string literals, no user input
    src = '''app T
    db.query("SELECT * FROM users WHERE active = " + "1")
'''
    c = codes(src)
    assert "G101" not in c, f"false positive: {c}"
test("G101 — string-only concat is SAFE (no false positive)", t4)

# ── G102: Command Injection ───────────────────────────────────────────────

def t5():
    src = '''app T
    set path to ask "Enter path: "
    shell("ls " + path)
'''
    assert raises_error(src, "G102")
test("G102 — command injection in shell() call", t5)

def t6():
    src = '''app T
    set cmd to ask "Command: "
    exec("rm -rf " + cmd)
'''
    assert raises_error(src, "G102")
test("G102 — command injection in exec() call", t6)

def t7():
    # safe: no user input involved
    src = '''app T
    shell("ls /home")
'''
    c = codes(src)
    assert "G102" not in c, f"false positive: {c}"
test("G102 — hardcoded shell command is SAFE (no false positive)", t7)

# ── G103: Hardcoded Secrets ───────────────────────────────────────────────

def t8():
    src = '''app T
    set password to "abc123"
'''
    assert raises_error(src, "G103")
test("G103 — hardcoded password literal", t8)

def t9():
    src = '''app T
    set api_key to "sk-supersecret123"
'''
    assert raises_error(src, "G103")
test("G103 — hardcoded api_key literal", t9)

def t10():
    src = '''app T
    set token to "Bearer eyJhbGciOi..."
'''
    assert raises_error(src, "G103")
test("G103 — hardcoded token literal", t10)

def t11():
    # safe: password read from environment / user input
    src = '''app T
    set password to ask "Enter password: "
'''
    c = codes(src)
    assert "G103" not in c, f"false positive: {c}"
test("G103 — password from ask is SAFE (no false positive)", t11)

def t12():
    # safe: variable named 'key' but assigned a number
    src = '''app T
    set key to 42
'''
    c = codes(src)
    assert "G103" not in c, f"false positive: {c}"
test("G103 — non-string 'key' is SAFE (no false positive)", t12)

# ── G104: Unvalidated Input ───────────────────────────────────────────────

def t13():
    src = '''app T
    set user to ask "Username: "
    db.find(user)
'''
    c = codes(src, strict=False)
    assert "G104" in c, f"expected G104, got {c}"
test("G104 — raw ask result passed to db.find()", t13)

def t14():
    src = '''app T
    set cmd to ask "Command: "
    shell(cmd)
'''
    c = codes(src, strict=False)
    assert "G104" in c
test("G104 — raw ask result passed to shell()", t14)

# ── G201: Unsafe module ───────────────────────────────────────────────────

def t15():
    src = '''app T
    use "pickle"
'''
    assert raises_error(src, "G201")
test("G201 — unsafe module 'pickle'", t15)

def t16():
    src = '''app T
    use "os.system"
'''
    assert raises_error(src, "G201")
test("G201 — unsafe module 'os.system'", t16)

def t17():
    src = '''app T
    use "crypto"
'''
    c = codes(src)
    assert "G201" not in c
test("G201 — safe module 'crypto' passes (no false positive)", t17)

# ── G301: Infinite Loop ───────────────────────────────────────────────────

def t18():
    src = '''app T
    repeat while true
        say "forever"
'''
    c = codes(src, strict=False)
    assert "G301" in c
test("G301 — repeat while true with no stop", t18)

def t19():
    # safe: has a stop inside
    src = '''app T
    set i to 0
    repeat while true
        set i to i + 1
        if i is 5
            stop
'''
    c = codes(src)
    assert "G301" not in c
test("G301 — repeat while true WITH stop is SAFE (no false positive)", t19)

def t20():
    # safe: condition is a variable, not literal true
    src = '''app T
    set running to true
    repeat while running
        set running to false
'''
    c = codes(src)
    assert "G301" not in c
test("G301 — repeat while variable is SAFE (no false positive)", t20)

# ── G401: Division by Zero ────────────────────────────────────────────────

def t21():
    src = '''app T
    say 10 / 0
'''
    assert raises_error(src, "G401")
test("G401 — division by literal zero", t21)

def t22():
    src = '''app T
    set x to 5 / 0
'''
    assert raises_error(src, "G401")
test("G401 — assign with division by zero", t22)

def t23():
    # safe: divisor is a variable
    src = '''app T
    set n to 4
    say 10 / n
'''
    c = codes(src)
    assert "G401" not in c
test("G401 — division by variable is SAFE (no false positive)", t23)

# ── G402: Unreachable code ────────────────────────────────────────────────

def t24():
    src = '''app T
    define f for x
        give back x
        say "never runs"
'''
    c = codes(src, strict=False)
    assert "G402" in c
test("G402 — code after give back is unreachable", t24)

def t25():
    src = '''app T
    repeat while true
        stop
        say "never"
'''
    c = codes(src, strict=False)
    assert "G402" in c
test("G402 — code after stop is unreachable", t25)

# ── Clean programs — zero issues ──────────────────────────────────────────

def t26():
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
    issues = analyze(src)
    assert issues == [], f"expected no issues, got {[str(i) for i in issues]}"
test("Clean FizzBuzz — zero security issues", t26)

def t27():
    src = '''app Grader
    define grade for score
        if score is at least 90
            give back "A"
        otherwise if score is at least 80
            give back "B"
        otherwise
            give back "F"
    say grade(85)
'''
    issues = analyze(src)
    assert issues == [], f"expected no issues, got {issues}"
test("Clean grade function — zero security issues", t27)

def t28():
    src = '''app Safe
    set name to ask "Your name: "
    say "Hello " + name
'''
    issues = analyze(src)
    assert issues == [], f"expected no issues for plain say, got {issues}"
test("ask + say only — zero security issues", t28)

# ── Issue fields ──────────────────────────────────────────────────────────

def t29():
    src = '''app T
    set password to "hunter2"
'''
    try:
        analyze(src, strict=True)
    except SecurityError as e:
        issue = e.issues[0]
        assert issue.code    == "G103"
        assert issue.level   == "ERROR"
        assert issue.line    > 0
        assert issue.suggestion != ""
test("Issue object has code, level, line, suggestion", t29)

def t30():
    src = '''app T
    set password to "secret"
    say 10 / 0
'''
    try:
        analyze(src, strict=True)
        assert False
    except SecurityError as e:
        codes_found = {i.code for i in e.issues}
        assert "G103" in codes_found
        assert "G401" in codes_found
test("Multiple issues detected in one scan", t30)

# ── Taint tracking: aliases, containers, and function calls ────────────────

def t31():
    src = '''app T
    set user to ask "Input: "
    set alias to user
    shell("echo " + alias)
'''
    assert raises_error(src, "G102")
test("Taint — assignment alias reaches command sink", t31)

def t32():
    src = '''app T
    set user to ask "Input: "
    set values to {"name": user, "status": "safe"}
    db.query("SELECT " + values["name"])
'''
    assert raises_error(src, "G101")
test("Taint — tainted dictionary field reaches SQL sink", t32)

def t33():
    src = '''app T
    set user to ask "Input: "
    set values to {"name": user, "status": "safe"}
    db.query("SELECT " + values["status"])
'''
    assert "G101" not in codes(src), f"safe field was falsely flagged: {codes(src)}"
test("Taint — known-safe dictionary field avoids false positive", t33)

def t34():
    src = '''app T
    set user to ask "Input: "
    set values to list("safe", user)
    shell("echo " + values[1])
'''
    assert raises_error(src, "G102")
test("Taint — tainted list index reaches command sink", t34)

def t35():
    src = '''app T
    set user to ask "Input: "
    set values to list(user, "safe")
    shell("echo " + values[1])
'''
    assert "G102" not in codes(src), f"safe list index was falsely flagged: {codes(src)}"
test("Taint — known-safe list index avoids false positive", t35)

def t36():
    src = '''app T
    set user to ask "Input: "
    set values to {"name": "safe"}
    set values["name"] to user
    shell("echo " + values["name"])
'''
    assert raises_error(src, "G102")
test("Taint — indexed assignment updates dictionary field taint", t36)

def t37():
    src = '''app T
    define run for command
        shell("echo " + command)
    set user to ask "Input: "
    run(user)
'''
    assert raises_error(src, "G102")
test("Taint — tainted function argument reaches sink", t37)

def t38():
    src = '''app T
    define identity for value
        give back value
    set user to ask "Input: "
    set alias to identity(user)
    shell("echo " + alias)
'''
    assert raises_error(src, "G102")
test("Taint — function return preserves input taint", t38)

def t39():
    src = '''app T
    define run for command
        shell("echo " + command)
    run("ls")
'''
    assert "G102" not in codes(src), f"constant function argument was falsely flagged: {codes(src)}"
test("Taint — constant function argument avoids false positive", t39)

def t40():
    src = '''app T
    define execute for command
        shell("echo " + command)
    define relay for value
        execute(value)
    set user to ask "Input: "
    relay(user)
'''
    assert raises_error(src, "G102")
test("Taint — taint propagates through nested function calls", t40)

def t41():
    src = '''app T
    set raw to ask "Filename: "
    set alias to raw
    read_file("data/" + alias)
'''
    assert raises_error(src, "G501")
test("Taint — alias is detected in file path construction", t41)

# ── Summary ───────────────────────────────────────────────────────────────

passed = sum(1 for ok,_ in results if ok)
total  = len(results)
print(f"\n── Results: {passed}/{total} passed ─────────────────────────\n")
if passed < total:
    sys.exit(1)
