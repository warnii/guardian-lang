"""
guardian/interpreter.py
Step 3: walks the AST produced by the Parser and executes it.

Design
------
- visitor pattern: visit(node) dispatches to visit_<ClassName>
- control flow signals (Return, Break, Continue) use Python exceptions
  so they bubble up naturally through nested calls
- Guardian built-ins (say, ask, len, range, type…) live here
  until stdlib.py is added in Step 5
"""

from __future__ import annotations
from ast_nodes import *
from environment import Environment, EnvironmentError


# ── Control-flow signals ──────────────────────────────────────────────────

class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

class BreakSignal(Exception):    pass
class ContinueSignal(Exception): pass


# ── Runtime errors ────────────────────────────────────────────────────────

class RuntimeError_(Exception):
    def __init__(self, msg, line=0, col=0):
        super().__init__(f"[RuntimeError] line {line}:{col} — {msg}")
        self.line = line; self.col = col


# ── Guardian function (user-defined) ──────────────────────────────────────

class GuardianFunction:
    def __init__(self, node: FuncDef, closure: Environment):
        self.node    = node
        self.closure = closure

    def __repr__(self):
        return f"<func {self.node.name}({', '.join(self.node.params)})>"


# ── Interpreter ───────────────────────────────────────────────────────────

class Interpreter:
    """
    Usage:
        interp = Interpreter()
        interp.run(program_ast)
    """

    def __init__(self, output_fn=print):
        self.globals  = Environment(name="global")
        self.output   = output_fn    # swap to capture output in tests
        self._register_builtins()

    # ── Entry point ───────────────────────────────────────────────────────

    def run(self, program: Program) -> None:
        env = self.globals
        self._exec_block(program.body, env)

    # ── Visitor dispatch ──────────────────────────────────────────────────

    def visit(self, node: Node, env: Environment) -> object:
        method = f"visit_{type(node).__name__}"
        fn = getattr(self, method, self._unknown)
        return fn(node, env)

    def _unknown(self, node, env):
        raise RuntimeError_(f"no visitor for {type(node).__name__}", node.line, node.col)

    # ── Statement visitors ────────────────────────────────────────────────

    def visit_Program(self, node: Program, env: Environment):
        self._exec_block(node.body, env)

    def visit_AssignStmt(self, node: AssignStmt, env: Environment):
        value = self.visit(node.value, env)
        env.set(node.name, value)

    def visit_AugAssignStmt(self, node: AugAssignStmt, env: Environment):
        left  = env.get(node.name)
        right = self.visit(node.value, env)
        env.set(node.name, self._apply_op(left, node.op, right, node))

    def visit_PrintStmt(self, node: PrintStmt, env: Environment):
        value = self.visit(node.value, env)
        self.output(self._to_str(value))

    def visit_ExprStmt(self, node: ExprStmt, env: Environment):
        self.visit(node.expr, env)

    def visit_IfStmt(self, node: IfStmt, env: Environment):
        cond = self.visit(node.condition, env)
        if self._truthy(cond):
            self._exec_block(node.then_block.statements, env)
        elif node.else_block:
            self._exec_block(node.else_block.statements, env)

    def visit_WhileStmt(self, node: WhileStmt, env: Environment):
        while self._truthy(self.visit(node.condition, env)):
            try:
                self._exec_block(node.body.statements, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def visit_ForStmt(self, node: ForStmt, env: Environment):
        iterable = self.visit(node.iterable, env)
        if not hasattr(iterable, '__iter__'):
            raise RuntimeError_(f"'{self._to_str(iterable)}' is not iterable",
                                 node.line, node.col)
        for item in iterable:
            loop_env = Environment(parent=env, name="for-loop")
            loop_env.set_local(node.var, item)
            try:
                self._exec_block(node.body.statements, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def visit_FuncDef(self, node: FuncDef, env: Environment):
        # 'secure' blocks run immediately
        if node.name == '__secure__':
            self._exec_block(node.body.statements, env)
            return
        fn = GuardianFunction(node, closure=env)
        env.set(node.name, fn)

    def visit_ReturnStmt(self, node: ReturnStmt, env: Environment):
        value = self.visit(node.value, env) if node.value else None
        raise ReturnSignal(value)

    def visit_BreakStmt(self, node, env):    raise BreakSignal()
    def visit_ContinueStmt(self, node, env): raise ContinueSignal()

    def visit_RequireStmt(self, node: RequireStmt, env: Environment):
        import os
        mod = node.module
        if not mod.endswith(".grd"):
            env.set(mod, f"<module '{mod}'>")
            return
        base = os.path.realpath(getattr(self, "base_dir", os.getcwd()))
        path = os.path.realpath(os.path.join(base, mod))
        if os.path.commonpath([base, path]) != base:
            raise RuntimeError_(f"import '{mod}' escapes the project folder", node.line, node.col)
        if not os.path.isfile(path):
            raise RuntimeError_(f"module '{mod}' not found", node.line, node.col)
        loaded = self.__dict__.setdefault("_loaded", set())
        if path in loaded:
            return
        loaded.add(path)
        from lexer import Lexer
        from parser import Parser
        from security import SecurityAnalyzer, SecurityError
        try:
            tree = Parser(Lexer(open(path).read()).tokenize()).parse()
            SecurityAnalyzer(strict=True).analyze(tree)
        except SecurityError as e:
            raise RuntimeError_(f"module '{mod}' failed security scan:{e}", node.line, node.col)
        except Exception as e:
            raise RuntimeError_(f"module '{mod}' failed to load: {e}", node.line, node.col)
        self._exec_block(tree.body, self.globals)

    # ── Expression visitors ───────────────────────────────────────────────

    def visit_IntLiteral(self, node, env):    return node.value
    def visit_FloatLiteral(self, node, env):  return node.value
    def visit_StringLiteral(self, node, env): return node.value
    def visit_BoolLiteral(self, node, env):   return node.value
    def visit_NullLiteral(self, node, env):   return None

    def visit_Identifier(self, node: Identifier, env: Environment):
        # built-in names
        if node.name in self.globals._store:
            val = self.globals._store[node.name]
            if callable(val): return val
        try:
            return env.get(node.name)
        except EnvironmentError:
            raise RuntimeError_(f"variable '{node.name}' is not defined",
                                 node.line, node.col)

    def visit_BinOp(self, node: BinOp, env: Environment):
        # short-circuit logical ops
        if node.op == 'and':
            return self.visit(node.left, env) and self.visit(node.right, env)
        if node.op == 'or':
            return self.visit(node.left, env) or  self.visit(node.right, env)
        left  = self.visit(node.left,  env)
        right = self.visit(node.right, env)
        return self._apply_op(left, node.op, right, node)

    def visit_UnaryOp(self, node: UnaryOp, env: Environment):
        val = self.visit(node.operand, env)
        if node.op == '-':
            if isinstance(val, (int, float)): return -val
            raise RuntimeError_(f"cannot negate '{self._to_str(val)}'",
                                 node.line, node.col)
        if node.op == 'not':
            return not self._truthy(val)
        raise RuntimeError_(f"unknown unary op '{node.op}'", node.line, node.col)

    def visit_CallExpr(self, node: CallExpr, env: Environment):
        callee = self.visit(node.callee, env)
        args   = [self.visit(a, env) for a in node.args]

        # Python built-in (registered in _register_builtins)
        if callable(callee) and not isinstance(callee, GuardianFunction):
            return callee(*args)

        # Guardian user-defined function
        if isinstance(callee, GuardianFunction):
            return self._call_guardian_fn(callee, args, node)

        raise RuntimeError_(f"'{self._to_str(callee)}' is not callable",
                             node.line, node.col)

    def visit_MemberAccess(self, node: MemberAccess, env: Environment):
        obj = self.visit(node.obj, env)
        # list / string methods
        if isinstance(obj, list):
            methods = {
                'length': lambda: len(obj),
                'add':    lambda x: obj.append(x),
                'remove': lambda x: obj.remove(x),
                'first':  lambda: obj[0] if obj else None,
                'last':   lambda: obj[-1] if obj else None,
            }
            if node.member in methods:
                return methods[node.member]
        if isinstance(obj, dict):
            methods = {
                'get':     lambda k, d=None: obj.get(k, d),
                'has':     lambda k: k in obj,
                'keys':    lambda: list(obj.keys()),
                'values':  lambda: list(obj.values()),
                'remove':  lambda k: obj.pop(k, None),
                'length':  lambda: len(obj),
            }
            if node.member in methods:
                return methods[node.member]
            raise RuntimeError_(f"dict has no member '{node.member}'",node.line,node.col)
        if isinstance(obj, str):
            methods = {
                'length':  lambda: len(obj),
                'upper':   lambda: obj.upper(),
                'lower':   lambda: obj.lower(),
                'trim':    lambda: obj.strip(),
                'split':   lambda sep=" ": obj.split(sep),
                'contains':lambda s: s in obj,
            }
            if node.member in methods:
                return methods[node.member]
        raise RuntimeError_(f"'{self._to_str(obj)}' has no member '{node.member}'",
                             node.line, node.col)

    def visit_IndexAccess(self, node: IndexAccess, env: Environment):
        obj   = self.visit(node.obj,   env)
        index = self.visit(node.index, env)
        try:
            return obj[index]
        except (IndexError, KeyError, TypeError) as e:
            raise RuntimeError_(f"index error: {e}", node.line, node.col)

    # ── Function call helper ──────────────────────────────────────────────

    def _call_guardian_fn(self, fn: GuardianFunction,
                          args: list, node: Node) -> object:
        params = fn.node.params
        if len(args) != len(params):
            raise RuntimeError_(
                f"'{fn.node.name}' expects {len(params)} args, got {len(args)}",
                node.line, node.col)
        local = Environment(parent=fn.closure, name=fn.node.name)
        for p, a in zip(params, args):
            local.set_local(p, a)
        try:
            self._exec_block(fn.node.body.statements, local)
        except ReturnSignal as ret:
            return ret.value
        return None

    # ── Operator engine ───────────────────────────────────────────────────

    def _apply_op(self, left, op: str, right, node: Node) -> object:
        try:
            if op == '+':
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_str(left) + self._to_str(right)
                return left + right
            if op == '-':  return left - right
            if op == '*':  return left * right
            if op == '/':
                if right == 0:
                    raise RuntimeError_("division by zero", node.line, node.col)
                return left / right
            if op == '%':  return left % right
            if op == '**': return left ** right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<':  return left <  right
            if op == '>':  return left >  right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
        except TypeError as e:
            raise RuntimeError_(f"type error: {e}", node.line, node.col)
        raise RuntimeError_(f"unknown operator '{op}'", node.line, node.col)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _exec_block(self, stmts: list, env: Environment) -> None:
        for stmt in stmts:
            if stmt: self.visit(stmt, env)

    def _truthy(self, value) -> bool:
        if value is None:   return False
        if value is False:  return False
        if value == 0:      return False
        if value == "":     return False
        if isinstance(value, list) and len(value) == 0: return False
        return True

    def _to_str(self, value) -> str:
        if value is None:  return "null"
        if value is True:  return "true"
        if value is False: return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    # ── Built-in functions ────────────────────────────────────────────────

    def _register_builtins(self):
        builtins = {
            # I/O
            'ask':    lambda prompt="": input(self._to_str(prompt)),
            'say':    lambda v: self.output(self._to_str(v)),
            # Type conversions
            'number': lambda v: int(v) if str(v).isdigit() else float(v),
            'text':   lambda v: self._to_str(v),
            'whole':  lambda v: int(v),
            # Collections
            'list':   lambda *args: list(args),
            'length': lambda v: len(v),
            'range':  lambda start, stop=None, step=1: (
                list(range(start, stop, step)) if stop is not None
                else list(range(start))
            ),
            # Checks
            'type':   lambda v: type(v).__name__,
            'is_null':lambda v: v is None,
            # Math
            'max':    lambda a, b: a if a > b else b,
            'min':    lambda a, b: a if a < b else b,
            'abs':    lambda v: abs(v),
            'round':  lambda v, d=0: round(v, d),
        }
        for name, fn in builtins.items():
            self.globals.set_local(name, fn)

    # ── Step 6 visitors ───────────────────────────────────────────────────

    def visit_DictLiteral(self, node, env):
        result = {}
        for key_node, val_node in node.pairs:
            k = self.visit(key_node, env)
            v = self.visit(val_node, env)
            result[k] = v
        return result

    def visit_TryStmt(self, node, env):
        try:
            self._exec_block(node.body.statements, env)
        except (RuntimeError_, Exception) as e:
            if node.handler:
                h_env = Environment(parent=env, name="handle")
                h_env.set_local(node.error_var, str(e))
                self._exec_block(node.handler.statements, h_env)
        finally:
            if node.always_block:
                self._exec_block(node.always_block.statements, env)

    def visit_FString(self, node, env):
        """Evaluate each part and concatenate into one string."""
        result = []
        for part in node.parts:
            if isinstance(part, str):
                result.append(part)
            elif isinstance(part, tuple) and part[0] == 'expr':
                # re-lex + parse + evaluate the embedded expression
                from lexer import Lexer
                from parser import Parser as P
                src = part[1].strip()
                try:
                    toks  = Lexer(src).tokenize()
                    # wrap in a tiny program so parser works
                    # actually parse just the expression
                    expr_parser = P(toks)
                    expr_node   = expr_parser._parse_expr()
                    val = self.visit(expr_node, env)
                    result.append(self._to_str(val))
                except Exception:
                    result.append('{' + part[1] + '}')
        return ''.join(result)

    def visit_IndexAssignStmt(self, node, env):
        obj   = env.get(node.obj)
        index = self.visit(node.index, env)
        value = self.visit(node.value, env)
        try:
            obj[index] = value
        except (TypeError, KeyError) as e:
            raise RuntimeError_(f"cannot assign to index: {e}", node.line, node.col)

    def visit_MemberAssignStmt(self, node, env):
        obj   = env.get(node.obj)
        value = self.visit(node.value, env)
        if isinstance(obj, dict):
            obj[node.member] = value
        else:
            raise RuntimeError_(f"cannot set member on {type(obj).__name__}", node.line, node.col)
