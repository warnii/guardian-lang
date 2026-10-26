#!/usr/bin/env python3
"""
guardian/run_tests.py
Master test runner — runs all Guardian test suites and reports total.

Usage:  python run_tests.py
"""
import subprocess, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("Step 1 · Lexer",       "test_lexer.py"),
    ("Step 2 · Parser",      "test_parser.py"),
    ("Step 3 · Interpreter", "test_interpreter.py"),
    ("Step 4 · Security",    "test_security.py"),
    ("Step 8 · Upgrades",    "test_upgrades.py"),
]

GREEN = "\033[32m"; RED = "\033[31m"; CYAN = "\033[36m"
BOLD  = "\033[1m";  DIM = "\033[2m";  RESET = "\033[0m"
AMBER = "\033[33m"

print(f"\n{CYAN}{BOLD}  Guardian Language — Full Test Suite{RESET}")
print(f"  {DIM}{'─'*44}{RESET}\n")

total_passed = total_tests = 0
failures = []
start = time.time()

for label, script in SUITES:
    t0  = time.time()
    res = subprocess.run(
        [sys.executable, os.path.join(HERE, script)],
        capture_output=True, text=True, cwd=HERE
    )
    elapsed = time.time() - t0
    out = res.stdout

    # Parse "Results: X/Y passed" from output
    passed = tests = 0
    for line in out.splitlines():
        if "Results:" in line and "passed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if "/" in p:
                    a, b = p.split("/")
                    passed, tests = int(a), int(b)

    total_passed += passed
    total_tests  += tests

    icon = f"{GREEN}✓{RESET}" if (tests and passed == tests) else f"{RED}✗{RESET}"
    bar_fill = int((passed / tests * 20)) if tests else 0
    bar  = f"{GREEN}{'█'*bar_fill}{DIM}{'░'*(20-bar_fill)}{RESET}"

    print(f"  {icon}  {label:<28} {bar}  {passed}/{tests}  {DIM}{elapsed:.2f}s{RESET}")

    if passed < tests or tests == 0:
        failures.append((label, out + res.stderr))

elapsed_total = time.time() - start
pct = int(total_passed / total_tests * 100) if total_tests else 0

print(f"\n  {DIM}{'─'*44}{RESET}")

if total_tests and total_passed == total_tests:
    print(f"  {GREEN}{BOLD}✓  {total_passed}/{total_tests} tests passed  ({pct}%)  in {elapsed_total:.2f}s{RESET}")
    print(f"  {DIM}All suites green.{RESET}\n")
else:
    missed = total_tests - total_passed
    print(f"  {RED}{BOLD}✗  {missed} failure(s)  —  {total_passed}/{total_tests} passed{RESET}")
    for label, out in failures:
        print(f"\n  {AMBER}── {label} failures ──{RESET}")
        for line in out.splitlines():
            if "✗" in line:
                print(f"    {line.strip()}")
    print()
    sys.exit(1)
