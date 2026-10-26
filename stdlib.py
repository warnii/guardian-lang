"""
guardian/stdlib.py
Step 5 — Guardian Standard Library.
All built-ins available in every Guardian program.
Injected into the global Environment before execution.
"""
from __future__ import annotations
import math, random, time as _time


def _guardian_print(output_fn):
    """say — already wired in interpreter, kept here for reference."""
    return output_fn


def build_stdlib(env, output_fn=print, input_fn=input) -> None:
    """Register every built-in into an Environment."""
    fns = {
        # ── I/O ──────────────────────────────────────────────────────────
        "say":      lambda v="": output_fn(str(v) if not isinstance(v, bool) else ("true" if v else "false")),
        "ask":      lambda prompt="": input_fn(str(prompt)),

        # ── Type conversions ──────────────────────────────────────────────
        "number":   lambda v: int(v) if str(v).lstrip("-").isdigit() else float(v),
        "whole":    lambda v: int(float(v)),
        "decimal":  lambda v: float(v),
        "text":     lambda v: ("true" if v is True else "false" if v is False
                               else "null" if v is None else str(v)),
        "boolean":  lambda v: bool(v),

        # ── String ────────────────────────────────────────────────────────
        "length":   lambda v: len(v),
        "upper":    lambda s: str(s).upper(),
        "lower":    lambda s: str(s).lower(),
        "trim":     lambda s: str(s).strip(),
        "split":    lambda s, sep=" ": str(s).split(sep),
        "join":     lambda lst, sep="": sep.join(str(x) for x in lst),
        "replace":  lambda s, old, new: str(s).replace(old, new),
        "contains": lambda s, sub: sub in str(s),
        "starts":   lambda s, prefix: str(s).startswith(prefix),
        "ends":     lambda s, suffix: str(s).endswith(suffix),
        "repeat_text": lambda s, n: str(s) * int(n),

        # ── Collections ───────────────────────────────────────────────────
        "list":     lambda *args: list(args),
        "range":    lambda start, stop=None, step=1: (
                        list(range(int(start), int(stop), int(step)))
                        if stop is not None else list(range(int(start)))
                    ),
        "empty":    lambda: [],
        "add_to":   lambda lst, item: [*lst, item],
        "remove_from": lambda lst, item: [x for x in lst if x != item],
        "first":    lambda lst: lst[0] if lst else None,
        "last":     lambda lst: lst[-1] if lst else None,
        "reverse":  lambda lst: list(reversed(lst)),
        "sort":     lambda lst: sorted(lst),
        "unique":   lambda lst: list(dict.fromkeys(lst)),
        "count":    lambda lst, v: lst.count(v),
        "has":      lambda lst, v: v in lst,
        "flat":     lambda lst: [x for sub in lst for x in (sub if isinstance(sub, list) else [sub])],

        # ── Math ──────────────────────────────────────────────────────────
        "abs":      lambda v: abs(v),
        "round":    lambda v, d=0: round(float(v), int(d)),
        "floor":    lambda v: math.floor(v),
        "ceiling":  lambda v: math.ceil(v),
        "sqrt":     lambda v: math.sqrt(v),
        "power":    lambda base, exp: base ** exp,
        "max":      lambda a, b=None: (max(a) if b is None and hasattr(a, '__iter__') else max(a, b)),
        "min":      lambda a, b=None: (min(a) if b is None and hasattr(a, '__iter__') else min(a, b)),
        "sum":      lambda lst: sum(lst),
        "average":  lambda lst: sum(lst) / len(lst) if lst else 0,
        "random":   lambda: random.random(),
        "pick":     lambda lst: random.choice(lst) if lst else None,
        "shuffle":  lambda lst: (random.shuffle(lst) or lst),

        # ── Checks / guards ───────────────────────────────────────────────
        "is_null":  lambda v: v is None,
        "is_text":  lambda v: isinstance(v, str),
        "is_number":lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "is_list":  lambda v: isinstance(v, list),
        "is_bool":  lambda v: isinstance(v, bool),
        "type":     lambda v: (
                        "null" if v is None else
                        "bool" if isinstance(v, bool) else
                        "number" if isinstance(v, (int, float)) else
                        "text" if isinstance(v, str) else
                        "list" if isinstance(v, list) else "unknown"
                    ),

        # ── Time ──────────────────────────────────────────────────────────
        "now":      lambda: int(_time.time()),
        "wait":     lambda secs: _time.sleep(float(secs)),

        # ── File I/O ──────────────────────────────────────────────────────
        "read_file":    lambda path: open(str(path)).read(),
        "write_file":   lambda path, content: (open(str(path),'w').write(str(content)), None)[1],
        "append_file":  lambda path, content: (open(str(path),'a').write(str(content)), None)[1],
        "file_exists":  lambda path: __import__('os').path.exists(str(path)),
        "lines_of":     lambda path: open(str(path)).read().splitlines(),
        "delete_file":  lambda path: __import__('os').remove(str(path)),

        # ── Utility ───────────────────────────────────────────────────────
        "print":    lambda v="": output_fn(str(v)),  # classic alias
    }
    for name, fn in fns.items():
        env.set_local(name, fn)
