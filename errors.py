"""
guardian/errors.py
Beautiful error formatting — shows the source line with a caret pointer.

  [LexError] line 3:12 — unrecognised character '@'

    3 │  set x to @value
                  ^

"""
from __future__ import annotations

RED   = "\033[31m"
AMBER = "\033[33m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def format_error(
    kind:    str,          # "LexError" / "ParseError" / "RuntimeError"
    message: str,
    source:  str,
    line:    int,
    col:     int,
) -> str:
    colour = RED if "Error" in kind else AMBER
    lines  = source.splitlines()

    out = [f"\n{colour}{BOLD}  [{kind}]{RESET} {message}\n"]

    # Show up to 2 lines of context before the error line
    start = max(0, line - 3)
    end   = min(len(lines), line + 1)

    for i in range(start, end):
        ln_num   = i + 1
        ln_text  = lines[i]
        marker   = f"{colour}▶{RESET}" if ln_num == line else " "
        out.append(f"  {marker} {DIM}{ln_num:>3}{RESET} │  {ln_text}")

        if ln_num == line:
            # caret pointing at the column
            spaces = " " * (col + 6)   # offset for line-number gutter
            out.append(f"  {spaces}{colour}^{RESET}")

    out.append("")
    return "\n".join(out)


def pretty_lex_error(e, source: str) -> str:
    return format_error("LexError", str(e).split("—")[-1].strip(),
                        source, e.line, e.col)

def pretty_parse_error(e, source: str) -> str:
    msg = str(e).split("—")[-1].split("(got")[0].strip()
    return format_error("ParseError", msg, source, e.token.line, e.token.col)

def pretty_runtime_error(e, source: str) -> str:
    msg = str(e).split("—")[-1].strip()
    return format_error("RuntimeError", msg, source, e.line, e.col)
