from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Node:
    line:int=field(default=0,compare=False,repr=False)
    col:int=field(default=0,compare=False,repr=False)

@dataclass
class Program(Node):
    name:str=""; body:list=field(default_factory=list)
@dataclass
class Block(Node):
    statements:list=field(default_factory=list)
@dataclass
class AssignStmt(Node):
    name:str=""; value:Any=None
@dataclass
class AugAssignStmt(Node):
    name:str=""; op:str=""; value:Any=None
@dataclass
class IfStmt(Node):
    condition:Any=None; then_block:Any=None; else_block:Any=None
@dataclass
class WhileStmt(Node):
    condition:Any=None; body:Any=None
@dataclass
class ForStmt(Node):
    var:str=""; iterable:Any=None; body:Any=None
@dataclass
class FuncDef(Node):
    name:str=""; params:list=field(default_factory=list); body:Any=None
@dataclass
class ReturnStmt(Node):
    value:Any=None
@dataclass
class PrintStmt(Node):
    value:Any=None
@dataclass
class ExprStmt(Node):
    expr:Any=None
@dataclass
class BreakStmt(Node): pass
@dataclass
class ContinueStmt(Node): pass
@dataclass
class RequireStmt(Node):
    module:str=""

@dataclass
class IntLiteral(Node):
    value:int=0
    def __repr__(self): return f"Int({self.value})"
@dataclass
class FloatLiteral(Node):
    value:float=0.0
    def __repr__(self): return f"Float({self.value})"
@dataclass
class StringLiteral(Node):
    value:str=""
    def __repr__(self): return f"Str({self.value!r})"
@dataclass
class BoolLiteral(Node):
    value:bool=False
    def __repr__(self): return f"Bool({self.value})"
@dataclass
class NullLiteral(Node):
    def __repr__(self): return "Null"
@dataclass
class Identifier(Node):
    name:str=""
    def __repr__(self): return f"Id({self.name!r})"
@dataclass
class BinOp(Node):
    left:Any=None; op:str=""; right:Any=None
    def __repr__(self): return f"({self.left} {self.op} {self.right})"
@dataclass
class UnaryOp(Node):
    op:str=""; operand:Any=None
    def __repr__(self): return f"({self.op} {self.operand})"
@dataclass
class CallExpr(Node):
    callee:Any=None; args:list=field(default_factory=list)
    def __repr__(self): return f"Call({self.callee},{self.args})"
@dataclass
class MemberAccess(Node):
    obj:Any=None; member:str=""
    def __repr__(self): return f"({self.obj}.{self.member})"
@dataclass
class IndexAccess(Node):
    obj:Any=None; index:Any=None
    def __repr__(self): return f"({self.obj}[{self.index}])"

# ── Step 6 additions ──────────────────────────────────────────────────────

@dataclass
class DictLiteral(Node):
    """{"key": value, ...}  or  map("k": v, ...)"""
    pairs: list = field(default_factory=list)   # list of (key_node, value_node)
    def __repr__(self): return f"Dict({self.pairs})"

@dataclass
class TryStmt(Node):
    """
    try
        <body>
    handle <error_var>
        <handler>
    always          ← optional
        <finally_block>
    """
    body:          Any = None
    error_var:     str = "error"
    handler:       Any = None
    always_block:  Any = None

@dataclass
class FString(Node):
    """
    String interpolation: "Hello {name}, you are {age} years old"
    Stored as a list of parts — str or Node.
    """
    parts: list = field(default_factory=list)
    def __repr__(self): return f"FString({self.parts})"

@dataclass
class IndexAssignStmt(Node):
    """set obj[key] to value"""
    obj:   str  = ""
    index: Any  = None
    value: Any  = None

@dataclass
class MemberAssignStmt(Node):
    """set obj.member to value"""
    obj:    str = ""
    member: str = ""
    value:  Any = None
