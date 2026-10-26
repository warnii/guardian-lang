#!/usr/bin/env python3
"""
guardian/guardian.py
Guardian CLI entry point.

Usage:
    python guardian.py run   hello.grd
    python guardian.py check hello.grd    ← security scan only, no run
    python guardian.py repl               ← interactive shell

File extension: .grd  (Guardian source)
"""

from __future__ import annotations
import sys, os

from lexer       import Lexer,       LexError
from parser      import Parser,      ParseError
from interpreter import Interpreter, RuntimeError_
from security    import SecurityAnalyzer, SecurityError
from environment import Environment
from stdlib      import build_stdlib
from errors      import pretty_lex_error, pretty_parse_error, pretty_runtime_error

VERSION = "1.1.0"
CYAN  = "\033[36m"
GREEN = "\033[32m"
RED   = "\033[31m"
AMBER = "\033[33m"
DIM   = "\033[2m"
BOLD  = "\033[1m"
RESET = "\033[0m"

BANNER = f"""
{CYAN}{BOLD}  ██████╗   ██╗   ██ ╗  █████╗  ██████╗  ██████╗ ██╗ █████╗   ███╗   ██╗{RESET}
{CYAN}{BOLD}  ██╔════╝  ██║   ██ ║██╔══██╗ ██╔══██╗ ██╔══██╗ ██║ ██╔══██╗ ████╗  ██║{RESET}
{CYAN}{BOLD}  ██║  ███╗ ██║   ██ ║███████║ ██████╔╝ ██║  ██║ ██║ ███████║ ██╔██╗ ██║{RESET}
{CYAN}{BOLD}  ██║   ██║ ██║   ██ ║██╔══██║ ██╔══██╗ ██║  ██║ ██║ ██╔══██║ ██║╚██╗██║{RESET}
{CYAN}{BOLD}  ╚██████╔╝ ╚██████╔╝ ██║  ██║ ██║  ██║ ██████╔╝ ██║ ██║  ██║ ██║ ╚████║{RESET}
{CYAN}{BOLD}   ╚═════╝   ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═════╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═══╝{RESET}
{DIM}  Programming Language v{VERSION} — secure by design · safe by default{RESET}
"""


def _pipeline(source: str, filename: str = "<input>",
              run: bool = True, strict: bool = True) -> bool:
    """
    Full pipeline: lex → parse → security check → (optionally) interpret.
    Returns True on success.
    """
    # ── 1. Lex ────────────────────────────────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
    except LexError as e:
        print(pretty_lex_error(e, source))
        return False

    # ── 2. Parse ──────────────────────────────────────────────────────────
    try:
        tree = Parser(tokens).parse()
    except ParseError as e:
        print(pretty_parse_error(e, source))
        return False

    # ── 3. Security Scan ──────────────────────────────────────────────────
    try:
        issues = SecurityAnalyzer(strict=strict).analyze(tree)
        if issues:
            for iss in issues:
                colour = RED if iss.level == "ERROR" else AMBER
                print(f"{colour}{iss}{RESET}")
    except SecurityError as e:
        print(f"\n{RED}{BOLD}{e}{RESET}\n")
        return False

    if not run:
        if not issues:
            print(f"{GREEN}✓  No security issues found in {filename}{RESET}")
        return True

    # ── 4. Execute ────────────────────────────────────────────────────────
    try:
        env = Environment(name="global")
        build_stdlib(env)
        interp = Interpreter()
        interp.globals = env
        build_stdlib(interp.globals)
        interp.base_dir = (os.path.dirname(os.path.abspath(filename))
                           if filename != "<input>" else os.getcwd())
        interp.run(tree)
        return True
    except RuntimeError_ as e:
        print(f"\n{RED}✗ Runtime error{RESET}")
        print(f"  {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n{DIM}interrupted{RESET}")
        return False


def cmd_run(args):
    if not args:
        print(f"{RED}Usage: guardian run <file.grd>{RESET}")
        sys.exit(1)
    path = args[0]
    if not os.path.exists(path):
        print(f"{RED}File not found: {path}{RESET}")
        sys.exit(1)
    source = open(path).read()
    ok = _pipeline(source, filename=path, run=True)
    sys.exit(0 if ok else 1)


def cmd_check(args):
    if not args:
        print(f"{RED}Usage: guardian check <file.grd>{RESET}")
        sys.exit(1)
    path = args[0]
    source = open(path).read()
    print(f"{DIM}Scanning {path}...{RESET}")
    ok = _pipeline(source, filename=path, run=False)
    sys.exit(0 if ok else 1)


def cmd_new(args):
    if not args:
        print(f"{RED}Usage: guardian new <project-name>{RESET}")
        sys.exit(1)
    name = args[0]
    if os.path.exists(name):
        print(f"{RED}'{name}' already exists{RESET}")
        sys.exit(1)
    os.makedirs(os.path.join(name, "lib"))
    app = "".join(w.capitalize() for w in name.replace("-", "_").split("_")) or "App"
    open(os.path.join(name, "main.grd"), "w").write(
        f'app {app}\n\n    use "lib/helpers.grd"\n\n    say greet("{app}")\n')
    open(os.path.join(name, "lib", "helpers.grd"), "w").write(
        'app Helpers\n\n    define greet for name\n        give back "Hello from {name}!"\n')
    print(f"{GREEN}✓ Created {name}/{RESET}  →  cd {name} && guardian run main.grd")


def cmd_repl():
    print(BANNER)
    print(f"  {DIM}Type Guardian code line by line.")
    print(f"  End a block with a blank line. Type 'exit' to quit.{RESET}\n")

    env = Environment(name="global")
    build_stdlib(env)
    interp = Interpreter()
    interp.globals = env
    build_stdlib(interp.globals)

    buf = []
    while True:
        try:
            prompt = "... " if buf else "grd> "
            line   = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}goodbye{RESET}")
            break

        if line.strip() in ("exit", "quit"):
            print(f"{DIM}goodbye{RESET}")
            break

        buf.append(line)

        # Empty line = end of block, try to run
        if line.strip() == "" or (buf and not line.startswith(" ")):
            src = "app REPL\n" + "\n".join("    " + l for l in buf if l.strip()) + "\n"
            buf.clear()
            if src.strip() == "app REPL":
                continue
            try:
                tokens = Lexer(src).tokenize()
                tree   = Parser(tokens).parse()
                SecurityAnalyzer(strict=False).analyze(tree)
                interp.run(tree)
            except (LexError, ParseError) as e:
                print(f"{RED}{e}{RESET}")
            except SecurityError as e:
                print(f"{RED}{e}{RESET}")
            except RuntimeError_ as e:
                print(f"{RED}{e}{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(BANNER)
        print("  Commands:")
        print(f"    {CYAN}guardian run   <file.grd>{RESET}   run a Guardian program")
        print(f"    {CYAN}guardian check <file.grd>{RESET}   security scan only")
        print(f"    {CYAN}guardian repl{RESET}               interactive shell")
        print(f"    {CYAN}guardian new   <name>{RESET}       scaffold a project")
        return

    cmd = args[0]
    rest = args[1:]
    if   cmd == "run":   cmd_run(rest)
    elif cmd == "check": cmd_check(rest)
    elif cmd == "repl":  cmd_repl()
    elif cmd == "new":   cmd_new(rest)
    elif cmd in ("version", "--version"): print(f"Guardian {VERSION}")
    else:
        print(f"{RED}Unknown command: {cmd}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:          # e.g. `guardian run x.grd | head`
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
