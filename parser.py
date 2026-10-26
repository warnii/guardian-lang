from __future__ import annotations
from tokens import Token, TokenType
from ast_nodes import *

class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(f"[ParseError] {token.line}:{token.col} — {msg} (got {token.type.name} {token.value!r})")
        self.token=token

class Parser:
    def __init__(self, tokens):
        self.tokens=tokens; self.pos=0

    def parse(self):
        self._skip_newlines()
        app_tok=self._expect(TokenType.APP)
        name_tok=self._expect(TokenType.IDENTIFIER)
        self._skip_newlines()
        body = self._parse_block().statements if self._at(TokenType.INDENT) else []
        self._expect(TokenType.EOF)
        return Program(name=name_tok.value,body=body,line=app_tok.line,col=app_tok.col)

    def _parse_block(self):
        t=self._expect(TokenType.INDENT)
        stmts=self._parse_block_body()
        self._expect(TokenType.DEDENT)
        return Block(statements=stmts,line=t.line,col=t.col)

    def _parse_block_body(self):
        stmts=[]
        while not self._at(TokenType.DEDENT) and not self._at(TokenType.EOF):
            self._skip_newlines()
            if self._at(TokenType.DEDENT) or self._at(TokenType.EOF): break
            s=self._parse_statement()
            if s: stmts.append(s)
        return stmts

    def _parse_statement(self):
        tok=self._peek()
        if tok.type==TokenType.NEWLINE: self._advance(); return None

        # ── Natural language statements ───────────────────────────────────
        if tok.type==TokenType.SAY:     return self._parse_say()
        if tok.type==TokenType.SET:     return self._parse_set()
        if tok.type==TokenType.DEFINE:  return self._parse_define()
        if tok.type==TokenType.GIVE_BACK: return self._parse_give_back()
        if tok.type==TokenType.FOR_EACH:  return self._parse_for_each()
        if tok.type==TokenType.REPEAT:    return self._parse_repeat()
        if tok.type==TokenType.OTHERWISE: return self._parse_otherwise()
        if tok.type==TokenType.STOP:
            self._advance(); self._skip_newlines()
            return BreakStmt(line=tok.line,col=tok.col)
        if tok.type==TokenType.SKIP:
            self._advance(); self._skip_newlines()
            return ContinueStmt(line=tok.line,col=tok.col)
        if tok.type==TokenType.USE:    return self._parse_use()
        if tok.type==TokenType.SECURE: return self._parse_secure()
        if tok.type==TokenType.TRY: return self._parse_try()

        # ── Classic keywords (still valid) ────────────────────────────────
        if tok.type==TokenType.IF:     return self._parse_if()
        if tok.type==TokenType.WHILE:  return self._parse_while()
        if tok.type==TokenType.FOR:    return self._parse_for_classic()
        if tok.type==TokenType.FUNC:   return self._parse_func_def()
        if tok.type==TokenType.RETURN: return self._parse_return_classic()

        # ── Assignment: IDENTIFIER = expr ────────────────────────────────
        if tok.type in (TokenType.INCREASE, TokenType.DECREASE):
            return self._parse_step()
        if (tok.type==TokenType.IDENTIFIER
                and self._peek_at(1).type in (TokenType.PLUS,TokenType.MINUS,TokenType.STAR,TokenType.SLASH)
                and self._peek_at(2).type==TokenType.ASSIGN):
            name=self._advance(); op=self._advance().value; self._advance()
            val=self._parse_expr(); self._skip_newlines()
            return AugAssignStmt(name=name.value,op=op,value=val,line=name.line,col=name.col)
        if tok.type==TokenType.IDENTIFIER and self._peek_at(1).type==TokenType.ASSIGN:
            return self._parse_assign()

        return self._parse_expr_stmt()

    # ── Natural language statement parsers ───────────────────────────────

    def _parse_say(self):
        tok=self._expect(TokenType.SAY)
        # say "hello"  OR  say("hello")
        if self._at(TokenType.LPAREN):
            self._advance(); val=self._parse_expr(); self._expect(TokenType.RPAREN)
        else:
            val=self._parse_expr()
        self._skip_newlines()
        return PrintStmt(value=val,line=tok.line,col=tok.col)

    def _parse_set(self):
        """set x to <expr>  OR  set obj[key] to <expr>  OR  set obj.key to <expr>"""
        tok=self._expect(TokenType.SET)
        name=self._expect(TokenType.IDENTIFIER)
        # check for index: set obj[key] to val
        if self._at(TokenType.LBRACKET):
            self._advance()
            idx=self._parse_expr()
            self._expect(TokenType.RBRACKET)
            self._expect(TokenType.TO)
            val=self._parse_expr(); self._skip_newlines()
            return IndexAssignStmt(obj=name.value,index=idx,value=val,line=tok.line,col=tok.col)
        # check for member: set obj.key to val
        if self._at(TokenType.DOT):
            self._advance()
            member=self._expect(TokenType.IDENTIFIER)
            self._expect(TokenType.TO)
            val=self._parse_expr(); self._skip_newlines()
            return MemberAssignStmt(obj=name.value,member=member.value,value=val,line=tok.line,col=tok.col)
        self._expect(TokenType.TO)
        val=self._parse_expr(); self._skip_newlines()
        return AssignStmt(name=name.value,value=val,line=tok.line,col=tok.col)

    def _parse_define(self):
        """define greet for name, age  →  func"""
        tok=self._expect(TokenType.DEFINE)
        name=self._expect(TokenType.IDENTIFIER)
        params=[]
        if self._at(TokenType.FOR):
            self._advance()
            while self._at(TokenType.IDENTIFIER):
                params.append(self._advance().value)
                if self._at(TokenType.COMMA): self._advance()
        self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return FuncDef(name=name.value,params=params,body=body,line=tok.line,col=tok.col)

    def _parse_give_back(self):
        tok=self._expect(TokenType.GIVE_BACK)
        if self._at(TokenType.NEWLINE) or self._at(TokenType.EOF):
            self._skip_newlines(); return ReturnStmt(value=None,line=tok.line,col=tok.col)
        val=self._parse_expr(); self._skip_newlines()
        return ReturnStmt(value=val,line=tok.line,col=tok.col)

    def _parse_for_each(self):
        """for each item in list"""
        tok=self._expect(TokenType.FOR_EACH)
        var=self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.IN)
        iterable=self._parse_expr(); self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return ForStmt(var=var.value,iterable=iterable,body=body,line=tok.line,col=tok.col)

    def _parse_repeat(self):
        """repeat while <cond>  OR  repeat <n> times (future)"""
        tok=self._expect(TokenType.REPEAT)
        self._expect(TokenType.WHILE)
        cond=self._parse_expr(); self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return WhileStmt(condition=cond,body=body,line=tok.line,col=tok.col)

    def _parse_otherwise(self):
        """otherwise / otherwise if — standalone else branch"""
        tok=self._expect(TokenType.OTHERWISE)
        self._skip_newlines()
        # standalone 'otherwise' is an error outside if — parser handles at if level
        raise ParseError("'otherwise' must follow an if block",tok)

    def _parse_use(self):
        """use "module"  →  require with security verification"""
        tok=self._expect(TokenType.USE)
        mod=self._expect(TokenType.STRING); self._skip_newlines()
        return RequireStmt(module=mod.value,line=tok.line,col=tok.col)

    def _parse_secure(self):
        """secure  →  marks a block for extra security analysis"""
        tok=self._expect(TokenType.SECURE)
        self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        # Reuse FuncDef node shape as a named block — interpreter marks it secure
        return FuncDef(name='__secure__',params=[],body=body,line=tok.line,col=tok.col)

    # ── Classic parsers (still valid) ────────────────────────────────────

    def _parse_if(self):
        tok=self._expect(TokenType.IF)
        cond=self._parse_expr(); self._skip_newlines()
        then=self._parse_block(); self._skip_newlines()
        else_=None
        # 'otherwise' or 'otherwise if' or classic 'else'
        if self._at(TokenType.OTHERWISE):
            self._advance(); self._skip_newlines()
            if self._at(TokenType.IF):
                inner=self._parse_if()
                else_=Block(statements=[inner],line=inner.line,col=inner.col)
            else:
                else_=self._parse_block(); self._skip_newlines()
        elif self._at_keyword('else'):
            self._advance(); self._skip_newlines()
            else_=self._parse_block(); self._skip_newlines()
        return IfStmt(condition=cond,then_block=then,else_block=else_,line=tok.line,col=tok.col)

    def _parse_while(self):
        tok=self._expect(TokenType.WHILE)
        cond=self._parse_expr(); self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return WhileStmt(condition=cond,body=body,line=tok.line,col=tok.col)

    def _parse_for_classic(self):
        tok=self._expect(TokenType.FOR)
        var=self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.IN)
        iterable=self._parse_expr(); self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return ForStmt(var=var.value,iterable=iterable,body=body,line=tok.line,col=tok.col)

    def _parse_func_def(self):
        tok=self._expect(TokenType.FUNC)
        name=self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN); params=[]
        while not self._at(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENTIFIER).value)
            if self._at(TokenType.COMMA): self._advance()
        self._expect(TokenType.RPAREN); self._skip_newlines()
        body=self._parse_block(); self._skip_newlines()
        return FuncDef(name=name.value,params=params,body=body,line=tok.line,col=tok.col)

    def _parse_return_classic(self):
        tok=self._expect(TokenType.RETURN)
        if self._at(TokenType.NEWLINE) or self._at(TokenType.EOF):
            self._skip_newlines(); return ReturnStmt(value=None,line=tok.line,col=tok.col)
        val=self._parse_expr(); self._skip_newlines()
        return ReturnStmt(value=val,line=tok.line,col=tok.col)

    def _parse_assign(self):
        name=self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.ASSIGN)
        val=self._parse_expr(); self._skip_newlines()
        return AssignStmt(name=name.value,value=val,line=name.line,col=name.col)

    def _parse_expr_stmt(self):
        tok=self._peek(); expr=self._parse_expr(); self._skip_newlines()
        return ExprStmt(expr=expr,line=tok.line,col=tok.col)

    # ── Expression parsing ────────────────────────────────────────────────

    def _parse_expr(self): return self._parse_or()

    def _parse_or(self):
        left=self._parse_and()
        while self._at(TokenType.OR):
            tok=self._advance(); right=self._parse_and()
            left=BinOp(left=left,op='or',right=right,line=tok.line,col=tok.col)
        return left

    def _parse_and(self):
        left=self._parse_not()
        while self._at(TokenType.AND):
            tok=self._advance(); right=self._parse_not()
            left=BinOp(left=left,op='and',right=right,line=tok.line,col=tok.col)
        return left

    def _parse_not(self):
        if self._at(TokenType.NOT):
            tok=self._advance()
            return UnaryOp(op='not',operand=self._parse_not(),line=tok.line,col=tok.col)
        return self._parse_comparison()

    def _parse_comparison(self):
        # Natural comparisons map to operators
        NATURAL={
            TokenType.IS:          '==',
            TokenType.IS_NOT:      '!=',
            TokenType.IS_GREATER:  '>',
            TokenType.IS_LESS:     '<',
            TokenType.IS_AT_LEAST: '>=',
            TokenType.IS_AT_MOST:  '<=',
        }
        SYMBOLIC={
            TokenType.EQ:'==',TokenType.NEQ:'!=',
            TokenType.LT:'<',TokenType.GT:'>',
            TokenType.LTE:'<=',TokenType.GTE:'>=',
        }
        left=self._parse_addition()
        while self._peek().type in NATURAL or self._peek().type in SYMBOLIC:
            tok=self._advance()
            op=NATURAL.get(tok.type) or SYMBOLIC.get(tok.type)
            right=self._parse_addition()
            left=BinOp(left=left,op=op,right=right,line=tok.line,col=tok.col)
        return left

    def _parse_addition(self):
        left=self._parse_multiplication()
        while self._at(TokenType.PLUS) or self._at(TokenType.MINUS):
            tok=self._advance(); right=self._parse_multiplication()
            left=BinOp(left=left,op=tok.value,right=right,line=tok.line,col=tok.col)
        return left

    def _parse_multiplication(self):
        left=self._parse_power()
        while self._peek().type in(TokenType.STAR,TokenType.SLASH,TokenType.PERCENT):
            tok=self._advance(); right=self._parse_power()
            left=BinOp(left=left,op=tok.value,right=right,line=tok.line,col=tok.col)
        return left

    def _parse_power(self):
        base=self._parse_unary()
        if self._at(TokenType.POWER):
            tok=self._advance(); exp=self._parse_power()
            return BinOp(left=base,op='**',right=exp,line=tok.line,col=tok.col)
        return base

    def _parse_unary(self):
        if self._at(TokenType.MINUS):
            tok=self._advance()
            return UnaryOp(op='-',operand=self._parse_unary(),line=tok.line,col=tok.col)
        return self._parse_call_member()

    def _parse_call_member(self):
        node=self._parse_primary()
        while True:
            if self._at(TokenType.DOT):
                self._advance(); m=self._expect(TokenType.IDENTIFIER)
                node=MemberAccess(obj=node,member=m.value,line=m.line,col=m.col)
            elif self._at(TokenType.LPAREN):
                tok=self._advance(); args=[]
                while not self._at(TokenType.RPAREN):
                    args.append(self._parse_expr())
                    if self._at(TokenType.COMMA): self._advance()
                self._expect(TokenType.RPAREN)
                node=CallExpr(callee=node,args=args,line=tok.line,col=tok.col)
            elif self._at(TokenType.LBRACKET):
                tok=self._advance(); idx=self._parse_expr()
                self._expect(TokenType.RBRACKET)
                node=IndexAccess(obj=node,index=idx,line=tok.line,col=tok.col)
            else: break
        return node

    def _parse_primary(self):
        tok=self._peek()
        if tok.type==TokenType.INTEGER: self._advance(); return IntLiteral(value=tok.value,line=tok.line,col=tok.col)
        if tok.type==TokenType.FLOAT:   self._advance(); return FloatLiteral(value=tok.value,line=tok.line,col=tok.col)
        if tok.type==TokenType.STRING:  self._advance(); return StringLiteral(value=tok.value,line=tok.line,col=tok.col)
        if tok.type==TokenType.FSTRING: self._advance(); return FString(parts=tok.value,line=tok.line,col=tok.col)
        if tok.type==TokenType.BOOL:    self._advance(); return BoolLiteral(value=tok.value,line=tok.line,col=tok.col)
        if tok.type==TokenType.NULL:    self._advance(); return NullLiteral(line=tok.line,col=tok.col)
        if tok.type==TokenType.IDENTIFIER: self._advance(); return Identifier(name=tok.value,line=tok.line,col=tok.col)
        # 'ask' used as expression: set name to ask "..."
        if tok.type==TokenType.ASK:
            self._advance()
            if self._at(TokenType.LPAREN):
                self._advance(); prompt=self._parse_expr(); self._expect(TokenType.RPAREN)
            else:
                prompt=self._parse_expr()
            return CallExpr(callee=Identifier(name='ask',line=tok.line,col=tok.col),
                           args=[prompt],line=tok.line,col=tok.col)
        if tok.type==TokenType.LBRACE: return self._parse_dict()
        if tok.type==TokenType.LPAREN:
            self._advance(); expr=self._parse_expr(); self._expect(TokenType.RPAREN); return expr
        raise ParseError("unexpected token in expression",tok)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _peek(self,offset=0):
        i=self.pos+offset
        return self.tokens[i] if i<len(self.tokens) else self.tokens[-1]
    def _peek_at(self,offset): return self._peek(offset)
    def _advance(self):
        tok=self.tokens[self.pos]
        if self.pos<len(self.tokens)-1: self.pos+=1
        return tok
    def _at(self,tt): return self._peek().type==tt
    def _at_keyword(self,word): return self._peek().value==word
    def _expect(self,tt):
        tok=self._peek()
        if tok.type!=tt: raise ParseError(f"expected {tt.name}",tok)
        return self._advance()
    def _skip_newlines(self):
        while self._peek().type in(TokenType.NEWLINE,TokenType.SEMICOLON): self._advance()

    def _parse_step(self):
        """increase x by 5  |  decrease x by 2  |  increase x  (by 1)"""
        tok=self._advance()
        name=self._expect(TokenType.IDENTIFIER)
        if self._at(TokenType.BY):
            self._advance(); val=self._parse_expr()
        else:
            val=IntLiteral(value=1,line=tok.line,col=tok.col)
        self._skip_newlines()
        op='+' if tok.type==TokenType.INCREASE else '-'
        return AugAssignStmt(name=name.value,op=op,value=val,line=tok.line,col=tok.col)

    # ── Step 6: dict literal, try/handle/always, fstring ─────────────────

    def _parse_dict(self) -> DictLiteral:
        """{ key: value, key: value }"""
        tok = self._expect(TokenType.LBRACE)
        pairs = []
        while not self._at(TokenType.RBRACE):
            key = self._parse_expr()
            self._expect(TokenType.COLON)
            val = self._parse_expr()
            pairs.append((key, val))
            if self._at(TokenType.COMMA): self._advance()
        self._expect(TokenType.RBRACE)
        return DictLiteral(pairs=pairs, line=tok.line, col=tok.col)

    def _parse_try(self) -> TryStmt:
        """
        try
            <body>
        handle error
            <handler>
        always          ← optional
            <finally>
        """
        tok = self._expect(TokenType.TRY)
        self._skip_newlines()
        body = self._parse_block()
        self._skip_newlines()

        error_var = "error"
        handler   = None
        if self._at(TokenType.HANDLE):
            self._advance()
            if self._at(TokenType.IDENTIFIER):
                error_var = self._advance().value
            self._skip_newlines()
            handler = self._parse_block()
            self._skip_newlines()

        always_block = None
        if self._at(TokenType.ALWAYS):
            self._advance()
            self._skip_newlines()
            always_block = self._parse_block()
            self._skip_newlines()

        return TryStmt(body=body, error_var=error_var,
                       handler=handler, always_block=always_block,
                       line=tok.line, col=tok.col)
