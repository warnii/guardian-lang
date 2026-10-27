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
# Operations that preserve their input text/data; they are not sanitizers.
_TAINT_PRESERVING_BUILTINS = {
    'upper', 'lower', 'trim', 'split', 'join', 'replace', 'repeat_text',
    'list', 'add_to', 'remove_from', 'first', 'last', 'reverse', 'sort',
    'unique', 'flat', 'pick', 'shuffle',
}


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
        self._input_vars: set[str] = set()   # variables carrying untrusted input
        self._container_items: dict[str, set] = {}  # tainted direct keys/indices
        self._function_defs: dict[str, FuncDef] = {}
        self._tainted_params: dict[str, set[int]] = {}
        self._return_tainted_params: dict[str, set[int]] = {}

    def analyze(self, program: Program) -> list[SecurityIssue]:
        self._issues.clear()
        self._input_vars.clear()
        self._container_items.clear()
        self._function_defs.clear()
        self._tainted_params.clear()
        self._return_tainted_params.clear()
        self._collect_functions(program.body)
        self._summarize_function_returns()
        self._scan_block(program.body)

        # Re-scan only functions called with tainted arguments. This keeps an
        # ordinary constant argument from tainting every use of a parameter.
        processed: dict[str, frozenset[int]] = {}
        max_passes = max(1, sum(len(fn.params) for fn in self._function_defs.values()) + 1)
        for _ in range(max_passes):
            changed = False
            for name, fn in self._function_defs.items():
                indexes = frozenset(self._tainted_params.get(name, set()))
                if not indexes or processed.get(name) == indexes:
                    continue
                saved_vars = set(self._input_vars)
                saved_items = {key: set(value) for key, value in self._container_items.items()}
                for index in indexes:
                    if index < len(fn.params):
                        self._input_vars.add(fn.params[index])
                        self._container_items.pop(fn.params[index], None)
                self._scan_block(fn.body.statements)
                self._input_vars = saved_vars
                self._container_items = saved_items
                processed[name] = indexes
                changed = True
            current = {name: frozenset(indexes) for name, indexes in self._tainted_params.items() if indexes}
            if not changed and all(processed.get(name) == indexes for name, indexes in current.items()):
                break

        # Function re-scans may revisit existing sinks; emit each finding once.
        unique = []
        seen = set()
        for issue in self._issues:
            key = (issue.code, issue.level, issue.message, issue.suggestion, issue.line, issue.col)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        self._issues = unique

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
        elif isinstance(node, (IndexAssignStmt, MemberAssignStmt)):
            if isinstance(node, IndexAssignStmt):
                self._scan_expr(node.index)
                key = self._static_key(node.index)
            else:
                key = node.member
            self._scan_expr(node.value)
            items = self._container_items.setdefault(node.obj, set())
            if self._expr_is_tainted(node.value):
                items.add(key)
            elif key is not None and None not in items:
                items.discard(key)
                if not items:
                    self._container_items.pop(node.obj, None)
        elif isinstance(node, AugAssignStmt):
            self._scan_expr(node.value)
            if node.name in self._input_vars or self._expr_is_tainted(node.value):
                self._input_vars.add(node.name)
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

        # Track input through aliases and known list/dict elements. Reassigning
        # a variable to a known-safe value clears its previous taint.
        if isinstance(value, DictLiteral):
            tainted_keys = set()
            for key_node, item_value in value.pairs:
                if self._expr_is_tainted(item_value):
                    tainted_keys.add(self._static_key(key_node))
            self._container_items.pop(node.name, None)
            self._input_vars.discard(node.name)
            if tainted_keys:
                self._container_items[node.name] = tainted_keys
        elif isinstance(value, CallExpr) and self._callee_name(value.callee) == 'list':
            tainted_indexes = {index for index, item in enumerate(value.args)
                               if self._expr_is_tainted(item)}
            self._container_items.pop(node.name, None)
            self._input_vars.discard(node.name)
            if tainted_indexes:
                self._container_items[node.name] = tainted_indexes
        elif isinstance(value, Identifier) and value.name in self._container_items:
            self._container_items[node.name] = set(self._container_items[value.name])
            self._input_vars.discard(node.name)
        else:
            self._container_items.pop(node.name, None)
            if self._expr_is_tainted(value):
                self._input_vars.add(node.name)
            else:
                self._input_vars.discard(node.name)

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

        # Remember which user-defined parameters receive tainted arguments.
        if fn_name in self._function_defs:
            indexes = self._tainted_params.setdefault(fn_name, set())
            for index, arg in enumerate(node.args):
                if index < len(self._function_defs[fn_name].params) and self._expr_is_tainted(arg):
                    indexes.add(index)

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
        """True if untrusted data flows into this expression."""
        return self._expr_is_tainted(node)

    def _expr_is_tainted(self, node: Node, names=None) -> bool:
        """Conservative expression-level taint check with direct container keys."""
        tainted_names = self._input_vars if names is None else names
        if node is None:
            return False
        if isinstance(node, Identifier):
            return node.name in tainted_names
        if isinstance(node, (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral)):
            return False
        if isinstance(node, BinOp):
            return self._expr_is_tainted(node.left, tainted_names) or self._expr_is_tainted(node.right, tainted_names)
        if isinstance(node, UnaryOp):
            return self._expr_is_tainted(node.operand, tainted_names)
        if isinstance(node, FString):
            return any(name in tainted_names for name in self._identifiers_in(node))
        if isinstance(node, DictLiteral):
            return any(self._expr_is_tainted(value, tainted_names) for _, value in node.pairs)
        if isinstance(node, IndexAccess):
            if isinstance(node.obj, Identifier):
                if node.obj.name in tainted_names:
                    return True
                tainted_keys = self._container_items.get(node.obj.name, set())
                key = self._static_key(node.index)
                return bool(tainted_keys) and (None in tainted_keys or key is None or key in tainted_keys)
            return self._expr_is_tainted(node.obj, tainted_names)
        if isinstance(node, MemberAccess):
            if isinstance(node.obj, Identifier):
                if node.obj.name in tainted_names:
                    return True
                tainted_keys = self._container_items.get(node.obj.name, set())
                return bool(tainted_keys) and (None in tainted_keys or node.member in tainted_keys)
            return self._expr_is_tainted(node.obj, tainted_names)
        if isinstance(node, CallExpr):
            if self._is_input_call(node):
                return True
            fn_name = self._callee_name(node.callee)
            if fn_name in self._return_tainted_params:
                return any(index < len(node.args) and self._expr_is_tainted(node.args[index], tainted_names)
                           for index in self._return_tainted_params[fn_name])
            if fn_name in _TAINT_PRESERVING_BUILTINS:
                return any(self._expr_is_tainted(arg, tainted_names) for arg in node.args)
            return False
        return False

    def _static_key(self, node):
        """Return a literal list/dict key, or None for a dynamic key."""
        if isinstance(node, StringLiteral): return node.value
        if isinstance(node, IntLiteral): return node.value
        return None

    def _collect_functions(self, stmts: list) -> None:
        """Index named functions before scanning so callers may precede definitions."""
        for stmt in stmts:
            if isinstance(stmt, FuncDef):
                if stmt.name != '__secure__':
                    self._function_defs[stmt.name] = stmt
                    self._collect_functions(stmt.body.statements)
            elif isinstance(stmt, IfStmt):
                self._collect_functions(stmt.then_block.statements)
                if stmt.else_block: self._collect_functions(stmt.else_block.statements)
            elif isinstance(stmt, (WhileStmt, ForStmt)):
                self._collect_functions(stmt.body.statements)
            elif isinstance(stmt, TryStmt):
                self._collect_functions(stmt.body.statements)
                if stmt.handler: self._collect_functions(stmt.handler.statements)
                if stmt.always_block: self._collect_functions(stmt.always_block.statements)

    def _summarize_function_returns(self) -> None:
        """Find parameters that can reach a function's returned value."""
        self._return_tainted_params = {name: set() for name in self._function_defs}
        limit = max(1, sum(len(fn.params) for fn in self._function_defs.values()) + 1)
        for _ in range(limit):
            changed = False
            for name, fn in self._function_defs.items():
                for index, param in enumerate(fn.params):
                    if index not in self._return_tainted_params[name] and self._block_returns_tainted(fn.body.statements, {param}):
                        self._return_tainted_params[name].add(index)
                        changed = True
            if not changed: break

    def _block_returns_tainted(self, stmts: list, tainted: set[str]) -> bool:
        """Follow simple aliases and return expressions for a symbolic parameter."""
        returns_tainted = False
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                if self._expr_is_tainted(stmt.value, tainted): tainted.add(stmt.name)
                else: tainted.discard(stmt.name)
            elif isinstance(stmt, AugAssignStmt):
                if stmt.name in tainted or self._expr_is_tainted(stmt.value, tainted): tainted.add(stmt.name)
            elif isinstance(stmt, (IndexAssignStmt, MemberAssignStmt)):
                if self._expr_is_tainted(stmt.value, tainted): tainted.add(stmt.obj)
            elif isinstance(stmt, ReturnStmt):
                returns_tainted |= stmt.value is not None and self._expr_is_tainted(stmt.value, tainted)
            elif isinstance(stmt, IfStmt):
                left, right = set(tainted), set(tainted)
                returns_tainted |= self._block_returns_tainted(stmt.then_block.statements, left)
                if stmt.else_block:
                    returns_tainted |= self._block_returns_tainted(stmt.else_block.statements, right)
                tainted.update(left | right)
            elif isinstance(stmt, (WhileStmt, ForStmt)):
                nested = set(tainted)
                if isinstance(stmt, ForStmt) and self._expr_is_tainted(stmt.iterable, tainted): nested.add(stmt.var)
                returns_tainted |= self._block_returns_tainted(stmt.body.statements, nested)
                tainted.update(nested)
            elif isinstance(stmt, TryStmt):
                for block in (stmt.body, stmt.handler, stmt.always_block):
                    if block:
                        nested = set(tainted)
                        returns_tainted |= self._block_returns_tainted(block.statements, nested)
                        tainted.update(nested)
        return returns_tainted

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
