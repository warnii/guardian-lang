"""
guardian/environment.py
Variable scope + call stack for the Guardian interpreter.

Each function call pushes a new Environment onto the chain.
Lookup walks up the chain (inner → outer → global).
"""
from __future__ import annotations


class EnvironmentError(Exception):
    pass


class Environment:
    """
    A single scope frame.

    env = Environment()                 # global
    child = Environment(parent=env)     # function / block scope
    """

    def __init__(self, parent: Environment | None = None, name: str = "global"):
        self._store: dict[str, object] = {}
        self._parent = parent
        self.name = name          # useful for debugging / tracebacks

    # ── Read ──────────────────────────────────────────────────────────────

    def get(self, name: str) -> object:
        if name in self._store:
            return self._store[name]
        if self._parent:
            return self._parent.get(name)
        raise EnvironmentError(f"variable '{name}' is not defined")

    def has(self, name: str) -> bool:
        if name in self._store:
            return True
        return self._parent.has(name) if self._parent else False

    # ── Write ─────────────────────────────────────────────────────────────

    def set(self, name: str, value: object) -> None:
        """
        Assign in the nearest scope that already owns this name,
        or create it in the current scope (first assignment = declaration).
        """
        if name in self._store:
            self._store[name] = value
        elif self._parent and self._parent.has(name):
            self._parent.set(name, value)
        else:
            self._store[name] = value

    def set_local(self, name: str, value: object) -> None:
        """Force-create in this scope (used for function parameters)."""
        self._store[name] = value

    def set_global(self, name: str, value: object) -> None:
        """Write to the top-level global scope."""
        if self._parent is None:
            self._store[name] = value
        else:
            self._parent.set_global(name, value)

    # ── Debug ─────────────────────────────────────────────────────────────

    def dump(self, indent: int = 0) -> str:
        pad = "  " * indent
        lines = [f"{pad}[{self.name}]"]
        for k, v in self._store.items():
            lines.append(f"{pad}  {k} = {v!r}")
        if self._parent:
            lines.append(self._parent.dump(indent + 1))
        return "\n".join(lines)

    def __repr__(self):
        return f"<Env '{self.name}' vars={list(self._store.keys())}>"
