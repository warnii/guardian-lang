# Guardian Programming Language

**Secure by Design. Safe by Default.**

Guardian is a security-first programming language that reads like natural English.
It catches vulnerabilities at compile time — SQL injection, command injection,
hardcoded secrets, and more — before a single line runs.

---

## Quick Start

```bash
python guardian.py run   hello.grd     # run a program
python guardian.py check myapp.grd    # security scan only
python guardian.py repl               # interactive shell
python guardian.py new myapp          # scaffold a project
python run_tests.py                   # 150 tests
```

---

## The Language

### Variables
```
set name to "Guardian"
set count to 0
set price to 9.99
set active to true
```

### Output & Input
```
say "Hello, World!"
say "Count: {count}"           # string interpolation

set name to ask "Your name: "
```

### Conditionals
```
if score is greater than 90
    say "A grade"
otherwise if score is greater than 80
    say "B grade"
otherwise
    say "Try again"
```

### Loops
```
set i to 1
repeat while i is at most 10
    say i
    set i to i + 1

for each fruit in fruits
    say fruit
```

### Functions
```
define greet for name
    give back "Hello, " + name

say greet("Hoysal")
```

### Dictionaries
```
set person to {"name": "Hoysal", "age": 20}
say person["name"]
set person["city"] to "Bangalore"
```

### Error Handling
```
try
    set result to 10 / n
handle err
    say "Error: " + err
always
    say "Done"
```

### File I/O
```
write_file("notes.txt", "Hello from Guardian")
set content to read_file("notes.txt")
say content
```

### Counting
```
increase count by 5
decrease count
count += 2            # symbolic form also works
```

### Modules
```
use "lib/helpers.grd"   # imports another Guardian file
use "crypto"            # verified built-in module
```
Imports stay inside the project folder, and every imported file is
security-scanned before it runs.

---

## Natural Language Operators

| Guardian                  | Meaning  |
|---------------------------|----------|
| `x is 5`                  | x == 5   |
| `x is not 5`              | x != 5   |
| `x is greater than 5`     | x > 5    |
| `x is less than 5`        | x < 5    |
| `x is at least 5`         | x >= 5   |
| `x is at most 5`          | x <= 5   |

---

## Security — G-Codes

Guardian scans your code **before** running it.

| Code | Level | Detects |
|------|-------|---------|
| G101 | ERROR | SQL injection via string concat |
| G102 | ERROR | Command injection in shell calls |
| G103 | ERROR | Hardcoded password / API key / token |
| G104 | WARN  | Unvalidated user input in sensitive call |
| G201 | ERROR | Unsafe / banned module |
| G301 | WARN  | Infinite loop with no exit |
| G401 | ERROR | Division by literal zero |
| G501 | ERROR/WARN | Path traversal — user input building a file path |
| G502 | WARN  | Printing a secret (password, token, key) |
| G503 | ERROR | Import reaching outside the project folder |
| G402 | WARN  | Unreachable code after return / stop |

**Example — Guardian refuses to compile this:**
```
app Unsafe
    set password to "hunter2"           # ← G103 ERROR
    set user to ask "Username: "
    db.query("SELECT * FROM " + user)   # ← G101 ERROR
    say 10 / 0                          # ← G401 ERROR
```

---

## Built-in Functions

| Category    | Functions |
|-------------|-----------|
| I/O         | `say`, `ask`, `read_file`, `write_file`, `append_file`, `file_exists` |
| Types       | `number`, `text`, `whole`, `boolean`, `type`, `is_null`, `is_text`, `is_number` |
| Math        | `abs`, `round`, `floor`, `ceiling`, `sqrt`, `max`, `min`, `sum`, `average`, `random` |
| Collections | `list`, `range`, `length`, `first`, `last`, `sort`, `reverse`, `unique`, `has`, `count` |
| Strings     | `upper`, `lower`, `trim`, `split`, `join`, `replace`, `contains`, `starts`, `ends` |
| Time        | `now`, `wait` |

---

## Project Structure

```
guardian/
  tokens.py          Token types + natural keyword map
  lexer.py           Source → tokens (handles f-strings, multi-word keywords)
  ast_nodes.py       21 AST node dataclasses
  parser.py          Recursive descent parser
  environment.py     Variable scope chain / call stack
  interpreter.py     AST executor
  security.py        Vulnerability scanner (G-codes)
  stdlib.py          40+ built-in functions
  errors.py          Pretty error messages with source highlighting
  guardian.py        CLI entry point
  run_tests.py       Master test runner (150 tests)
```

---

## Example Programs

- `demo.grd` — language feature showcase
- `examples/todo.grd` — todo list app
- `examples/calculator.grd` — expression calculator
- `examples/password_checker.grd` — secure password validator

---

*Built by Hoysal · BCA · Yenepoya Bengaluru Campus*
*Guardian Programming Language v1.0*
