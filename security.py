"""
guardian/security.py
Step 4 — Guardian Security Analyzer.

Walks the AST *before* execution and emits G-codes.
ERROR-level issues halt the program (Guardian never ships vulnerable code).
WARN-level issues print a warning but allow execution.

G-code reference
────────────────
  G101  SQL injection via string concatenation in a query call
  G102  Command injection via string concatenation in a shell/exec call
  G103  Hardcoded secret — password/key/token assigned a string literal
  G104  Unvalidated user input passed directly into a sensitive operation
  G201  Unsafe module — flagged as dangerous
  G301  Possible infinite loop — repeat while true with no stop
  G401  Division by literal zero
  G402  Unreachable code after give back / stop / skip
"""

from __future__ import annotations
from dataclasses import dataclass
from ast_nodes import *


# ── Issue model ───────────────────────────────────────────────────────────

@dataclass
class SecurityIssue:
    code:       str    # e.g. "G101"
    level:      str    # "ERROR" or "WARN"
    message:    str
    suggestion: str
    line:       int
    col:        int

    def __str__(self):
        icon = "✗" if self.level == "ERROR" else "⚠"
        return (
            f"  {icon}  [{self.code}] {self.level}  line {self.line}:{self.col}\n"
            f"     {self.message}\n"
            f"     → {self.suggestion}"
        )


class SecurityError(Exception):
    """Raised when one or more ERROR-level issues are found."""
    def __init__(self, issues: list[SecurityIssue]):
        self.issues = issues
        count = len(issues)
        super().__init__(
            f"\n\n{'='*55}\n"
            f"  Guardian Security Analysis — {count} issue(s) found\n"
            f"{'='*55}\n"
            + "\n\n".join(str(i) for i in issues)
            + f"\n{'='*55}\n"
            "  Compilation terminated. Fix all errors before running.\n"
            f"{'='*55}"
        )


# ── Names that signal sensitive operations ────────────────────────────────

_DB_METHODS     = {'query','select','execute','find','where','insert','update','delete','run'}
_SHELL_NAMES    = {'shell','exec','system','run','cmd','execute','subprocess','popen'}
_SECRET_NAMES   = {'password','passwd','secret','api_key','apikey','token','key',
                   'credentials','private_key','auth','access_token'}
_FILE_FUNCS     = {'read_file','write_file','append_file','delete_file','lines_of'}
_UNSAFE_MODULES = {'pickle','marshal','ctypes','subprocess','os.system'}


# ── Analyzer ──────────────────────────────────────────────────────────────

class SecurityAnalyzer:
    """
    Usage:
        analyzer = SecurityAnalyzer()
        analyzer.analyze(program)   # raises SecurityError if ERRORs found
    """

    def __init__(self, strict: bool = True):
        self.strict = strict   # if False, ERROR → WARN (demo/learning mode)
        self._issues: list[SecurityIssue] = []
        self._input_vars: set[str] = set()   # tracks variables from 'ask'

    def analyze(self, program: Program) -> list[SecurityIssue]:
        self._issues.clear()
        self._input_vars.clear()
        self._scan_block(program.body)

        errors = [i for i in self._issues if i.level == "ERROR"]
        if errors and self.strict:
            raise SecurityError(errors)
        return self._issues

    # ── Block / statement scanner ─────────────────────────────────────────

    def _scan_block(self, stmts: list) -> None:
        after_exit = False
        for stmt in stmts:
            if stmt is None:
                continue
            if after_exit:
                self._warn(
                    "G402", "WARN",
                    "Unreachable code after give back / stop / skip",
                    "Remove or restructure the unreachable statements",
                    stmt.line, stmt.col
                )
                break
            self._scan_stmt(stmt)
            if isinstance(stmt, (ReturnStmt, BreakStmt, ContinueStmt)):
                after_exit = True

    def _scan_stmt(self, node: Node) -> None:
        if isinstance(node, AssignStmt):    self._check_assign(node)
        elif isinstance(node, PrintStmt):
            self._check_print(node)
        elif isinstance(node, TryStmt):
            self._scan_block(node.body.statements)
            if node.handler:      self._scan_block(node.handler.statements)
            if node.always_block: self._scan_block(node.always_block.statements)
        elif isinstance(node, (IndexAssignStmt, MemberAssignStmt, AugAssignStmt)):
            self._scan_expr(node.value)
        elif isinstance(node, ExprStmt):    self._scan_expr(node.expr)
        elif isinstance(node, IfStmt):      self._check_if(node)
        elif isinstance(node, WhileStmt):   self._check_while(node)
        elif isinstance(node, ForStmt):     self._scan_block(node.body.statements)
        elif isinstance(node, FuncDef):     self._scan_block(node.body.statements)
        elif isinstance(node, ReturnStmt):
            if node.value: self._scan_expr(node.value)
        elif isinstance(node, RequireStmt): self._check_require(node)

    def _check_if(self, node: IfStmt) -> None:
        self._scan_expr(node.condition)
        self._scan_block(node.then_block.statements)
        if node.else_block:
            self._scan_block(node.else_block.statements)

    def _check_while(self, node: WhileStmt) -> None:
        self._scan_expr(node.condition)
        # G301 — infinite loop: repeat while true with no stop inside
        if isinstance(node.condition, BoolLiteral) and node.condition.value is True:
            if not self._block_has(node.body.statements, BreakStmt):
                self._warn(
                    "G301", "WARN",
                    "Possible infinite loop — 'repeat while true' has no 'stop'",
                    "Add a 'stop' statement or use a condition that can become false",
                    node.line, node.col
                )
        self._scan_block(node.body.statements)

    # ── Assignment checks ─────────────────────────────────────────────────

    def _check_assign(self, node: AssignStmt) -> None:
        name  = node.name.lower()
        value = node.value

        # Track variables that came from user input (ask)
        if self._is_input_call(value):
            self._input_vars.add(node.name)

        # G103 — hardcoded secret
        if name in _SECRET_NAMES and isinstance(value, StringLiteral):
            self._warn(
                "G103", "ERROR",
                f"Hardcoded secret — '{node.name}' is assigned a string literal",
                "Store secrets in environment variables or a secure vault, not in code",
                node.line, node.col
            )

        self._scan_expr(value)

    # ── Expression scanner ────────────────────────────────────────────────

    def _scan_expr(self, node: Node) -> None:
        if node is None:
            return
        if isinstance(node, CallExpr):
            self._check_call(node)
        elif isinstance(node, BinOp):
            # G401 — division by zero
            if node.op == '/' and isinstance(node.right, (IntLiteral, FloatLiteral)):
                if node.right.value == 0:
                    self._warn(
                        "G401", "ERROR",
                        "Division by literal zero",
                        "Check divisor before dividing, or use a non-zero literal",
                        node.line, node.col
                    )
            self._scan_expr(node.left)
            self._scan_expr(node.right)
        elif isinstance(node, UnaryOp):
            self._scan_expr(node.operand)
        elif isinstance(node, IndexAccess):
            self._scan_expr(node.obj)
            self._scan_expr(node.index)
        elif isinstance(node, MemberAccess):
            self._scan_expr(node.obj)

    def _check_call(self, node: CallExpr) -> None:
        # Resolve the function name and method name (if any)
        fn_name     = self._callee_name(node.callee)
        method_name = self._callee_method(node.callee)

        # G101 — SQL injection
        if method_name in _DB_METHODS:
            for arg in node.args:
                if self._contains_input_concat(arg):
                    self._warn(
                        "G101", "ERROR",
                        f"SQL injection risk — user input concatenated into '{method_name}' call",
                        "Use parameterized queries: db.query(sql, params) not string building",
                        node.line, node.col
                    )

        # G102 — command injection
        if fn_name in _SHELL_NAMES:
            for arg in node.args:
                if self._contains_input_concat(arg):
                    self._warn(
                        "G102", "ERROR",
                        f"Command injection risk — user input concatenated into '{fn_name}' call",
                        "Validate and sanitize all input before passing to shell commands",
                        node.line, node.col
                    )

        # G501 — path traversal: user input building a file path
        if fn_name in _FILE_FUNCS and node.args:
            path_arg = node.args[0]
            if self._contains_input_concat(path_arg):
                self._warn("G501", "ERROR",
                           f"Path traversal risk — user input builds the path in '{fn_name}'",
                           "Validate the name (no '..' or '/') or use a fixed folder + checked filename",
                           node.line, node.col)
            elif self._uses_raw_input(path_arg):
                self._warn("G501", "WARN",
                           f"User input used directly as a file path in '{fn_name}'",
                           "Check the path stays inside an allowed folder before opening it",
                           node.line, node.col)

        # G104 — unvalidated input in sensitive calls
        sensitive = _DB_METHODS | _SHELL_NAMES
        if (fn_name in sensitive or method_name in sensitive):
            for arg in node.args:
                if self._uses_raw_input(arg):
                    self._warn(
                        "G104", "WARN",
                        f"Unvalidated user input passed to '{fn_name or method_name}'",
                        "Validate/sanitize input before using it in sensitive operations",
                        node.line, node.col
                    )

        for arg in node.args:
            self._scan_expr(arg)

    def _check_print(self, node: PrintStmt) -> None:
        # G502 — printing a secret
        for name in self._identifiers_in(node.value):
            if name.lower() in _SECRET_NAMES:
                self._warn("G502", "WARN",
                           f"Secret '{name}' is being printed — it may leak into logs or screens",
                           "Never say secrets; print a masked value like '****' instead",
                           node.line, node.col)
                break
        self._scan_expr(node.value)

    def _identifiers_in(self, node) -> list:
        """All variable names used inside an expression (incl. {interpolation})."""
        if node is None: return []
        if isinstance(node, Identifier): return [node.name]
        if isinstance(node, BinOp):
            return self._identifiers_in(node.left) + self._identifiers_in(node.right)
        if isinstance(node, UnaryOp): return self._identifiers_in(node.operand)
        if isinstance(node, CallExpr):
            return [n for a in node.args for n in self._identifiers_in(a)]
        if isinstance(node, FString):
            names = []
            for p in node.parts:
                if isinstance(p, tuple):
                    try:
                        from lexer import Lexer
                        from tokens import TokenType
                        names += [t.value for t in Lexer(p[1]).tokenize()
                                  if t.type == TokenType.IDENTIFIER]
                    except Exception:
                        pass
            return names
        return []

    def _check_require(self, node: RequireStmt) -> None:
        # G503 — import escaping the project folder
        if node.module.startswith(("/", "\\")) or ".." in node.module:
            self._warn("G503", "ERROR",
                       f"Import '{node.module}' reaches outside the project folder",
                       "Keep modules inside your project and use relative paths like 'lib/x.grd'",
                       node.line, node.col)
        # G201 — unsafe module
        if node.module in _UNSAFE_MODULES:
            self._warn(
                "G201", "ERROR",
                f"Unsafe module '{node.module}' — known security risks",
                f"Use a vetted Guardian-safe alternative instead of '{node.module}'",
                node.line, node.col
            )

    # ── Pattern helpers ───────────────────────────────────────────────────

    def _contains_input_concat(self, node: Node) -> bool:
        """True if node is a + chain that mixes a string literal and user input."""
        if isinstance(node, FString):
            has_text = any(isinstance(p, str) and p.strip() for p in node.parts)
            return has_text and any(n in self._input_vars for n in self._identifiers_in(node))
        if not isinstance(node, BinOp) or node.op != '+':
            return False
        return (
            self._is_string_or_concat(node.left) and self._uses_raw_input(node.right)
            or
            self._is_string_or_concat(node.right) and self._uses_raw_input(node.left)
        )

    def _is_string_or_concat(self, node: Node) -> bool:
        if isinstance(node, StringLiteral): return True
        if isinstance(node, BinOp) and node.op == '+':
            return self._is_string_or_concat(node.left) or self._is_string_or_concat(node.right)
        return False

    def _uses_raw_input(self, node: Node) -> bool:
        """True if node is or contains a variable that came from 'ask'."""
        if isinstance(node, Identifier):
            return node.name in self._input_vars
        if isinstance(node, CallExpr) and self._is_input_call(node):
            return True
        if isinstance(node, BinOp):
            return self._uses_raw_input(node.left) or self._uses_raw_input(node.right)
        if isinstance(node, FString):
            return any(n in self._input_vars for n in self._identifiers_in(node))
        return False

    def _is_input_call(self, node: Node) -> bool:
        """True if node is a call to 'ask' or 'input'."""
        if not isinstance(node, CallExpr): return False
        name = self._callee_name(node.callee)
        return name in ('ask', 'input')

    def _callee_name(self, callee: Node) -> str:
        if isinstance(callee, Identifier):    return callee.name
        if isinstance(callee, MemberAccess):  return callee.member
        return ""

    def _callee_method(self, callee: Node) -> str:
        if isinstance(callee, MemberAccess): return callee.member
        return ""

    def _block_has(self, stmts: list, node_type) -> bool:
        """Recursively check if a block contains a node of the given type."""
        for s in stmts:
            if isinstance(s, node_type): return True
            if isinstance(s, IfStmt):
                if self._block_has(s.then_block.statements, node_type): return True
                if s.else_block and self._block_has(s.else_block.statements, node_type): return True
            if isinstance(s, WhileStmt):
                if self._block_has(s.body.statements, node_type): return True
        return False

    # ── Issue factory ─────────────────────────────────────────────────────

    def _warn(self, code, level, message, suggestion, line, col):
        self._issues.append(SecurityIssue(
            code=code, level=level, message=message,
            suggestion=suggestion, line=line, col=col
        ))
