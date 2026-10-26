from __future__ import annotations
from tokens import Token, TokenType, KEYWORDS

class LexError(Exception):
    def __init__(self, msg, line, col):
        super().__init__(f"[LexError] {line}:{col} — {msg}")
        self.line=line; self.col=col

class Lexer:
    def __init__(self, source):
        self.source=source; self.pos=0; self.line=1; self.col=1
        self.tokens=[]; self._indent_stack=[0]

    def tokenize(self):
        self._process_all_lines()
        self._flush_dedents()
        self._add(TokenType.EOF, None)
        return self.tokens

    def _process_all_lines(self):
        while self.pos < len(self.source):
            if self._at_line_start(): self._handle_indent()
            ch = self._peek()
            if ch is None: break
            if ch in (' ', '\t'): self._advance()
            elif ch == '\n': self._handle_newline()
            elif ch == '#': self._skip_comment()
            elif ch in ('"', "'"): self._read_string(ch)
            elif ch.isdigit(): self._read_number()
            elif ch.isalpha() or ch == '_': self._read_word()
            elif ch == '*':
                if self._peek_next() == '*': self._add(TokenType.POWER,'**',advance=2)
                else: self._add(TokenType.STAR,'*',advance=1)
            elif ch == '=':
                if self._peek_next() == '=': self._add(TokenType.EQ,'==',advance=2)
                else: self._add(TokenType.ASSIGN,'=',advance=1)
            elif ch == '!':
                if self._peek_next() == '=': self._add(TokenType.NEQ,'!=',advance=2)
                else: raise LexError("unexpected '!'",self.line,self.col)
            elif ch == '<':
                if self._peek_next() == '=': self._add(TokenType.LTE,'<=',advance=2)
                else: self._add(TokenType.LT,'<',advance=1)
            elif ch == '>':
                if self._peek_next() == '=': self._add(TokenType.GTE,'>=',advance=2)
                else: self._add(TokenType.GT,'>',advance=1)
            else:
                sym={'+':TokenType.PLUS,'-':TokenType.MINUS,'/':TokenType.SLASH,
                     '%':TokenType.PERCENT,'(':TokenType.LPAREN,')':TokenType.RPAREN,
                     '{':TokenType.LBRACE,'}':TokenType.RBRACE,'[':TokenType.LBRACKET,
                     ']':TokenType.RBRACKET,',':TokenType.COMMA,'.':TokenType.DOT,
                     ':':TokenType.COLON,';':TokenType.SEMICOLON}
                if ch in sym: self._add(sym[ch],ch,advance=1)
                else: raise LexError(f"unrecognised character {ch!r}",self.line,self.col)

    # ── Multi-word keyword resolution ─────────────────────────────────────
    def _read_word(self):
        """Read a word and resolve multi-word natural language keywords."""
        line, col = self.line, self.col
        start = self.pos
        while self._peek() and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()
        word = self.source[start:self.pos]

        # ── "give back" → GIVE_BACK ──────────────────────────────────────
        if word == 'give':
            rest = self._peek_word()
            if rest == 'back':
                self._consume_word()
                self.tokens.append(Token(TokenType.GIVE_BACK,'give back',line,col))
                return

        # ── "for each" → FOR_EACH ────────────────────────────────────────
        if word == 'for':
            rest = self._peek_word()
            if rest == 'each':
                self._consume_word()
                self.tokens.append(Token(TokenType.FOR_EACH,'for each',line,col))
                return

        # ── "is [not|greater than|less than|at least|at most]" ───────────
        if word == 'is':
            rest = self._peek_word()
            if rest == 'not':
                self._consume_word()
                self.tokens.append(Token(TokenType.IS_NOT,'is not',line,col))
                return
            if rest == 'greater':
                self._consume_word()
                than = self._peek_word()
                if than == 'than': self._consume_word()
                self.tokens.append(Token(TokenType.IS_GREATER,'is greater than',line,col))
                return
            if rest == 'less':
                self._consume_word()
                than = self._peek_word()
                if than == 'than': self._consume_word()
                self.tokens.append(Token(TokenType.IS_LESS,'is less than',line,col))
                return
            if rest == 'at':
                self._consume_word()
                degree = self._peek_word()
                if degree == 'least':
                    self._consume_word()
                    self.tokens.append(Token(TokenType.IS_AT_LEAST,'is at least',line,col))
                elif degree == 'most':
                    self._consume_word()
                    self.tokens.append(Token(TokenType.IS_AT_MOST,'is at most',line,col))
                else:
                    self.tokens.append(Token(TokenType.IS,'is',line,col))
                return
            # plain "is" → equality
            self.tokens.append(Token(TokenType.IS,'is',line,col))
            return

        # ── standard keyword or identifier ───────────────────────────────
        if word in KEYWORDS:
            tt = KEYWORDS[word]
            val = (word == 'true') if tt == TokenType.BOOL else word
            self.tokens.append(Token(tt,val,line,col))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER,word,line,col))

    def _peek_word(self):
        """Look at the next non-space word without consuming it."""
        i = self.pos
        while i < len(self.source) and self.source[i] == ' ': i += 1
        start = i
        while i < len(self.source) and (self.source[i].isalnum() or self.source[i]=='_'): i += 1
        return self.source[start:i] if i > start else ''

    def _consume_word(self):
        """Skip spaces then consume the next word."""
        while self._peek() == ' ': self._advance()
        while self._peek() and (self._peek().isalnum() or self._peek()=='_'): self._advance()

    # ── Indentation ────────────────────────────────────────────────────────
    def _at_line_start(self):
        return not self.tokens or self.tokens[-1].type == TokenType.NEWLINE

    def _handle_indent(self):
        indent=0
        while self.pos < len(self.source) and self.source[self.pos] in (' ','\t'):
            indent = ((indent//4)+1)*4 if self.source[self.pos]=='\t' else indent+1
            self.pos+=1; self.col+=1
        ch=self._peek()
        if ch in (None,'\n','#'): return
        cur=self._indent_stack[-1]
        if indent > cur:
            self._indent_stack.append(indent)
            self._add(TokenType.INDENT,indent)
        elif indent < cur:
            while self._indent_stack[-1] > indent:
                self._indent_stack.pop()
                self._add(TokenType.DEDENT,self._indent_stack[-1])
            if self._indent_stack[-1] != indent:
                raise LexError("indentation mismatch",self.line,self.col)

    def _flush_dedents(self):
        while len(self._indent_stack) > 1:
            self._indent_stack.pop()
            self._add(TokenType.DEDENT,self._indent_stack[-1])

    def _handle_newline(self):
        if self.tokens and self.tokens[-1].type != TokenType.NEWLINE:
            self._add(TokenType.NEWLINE,'\n')
        self._advance(); self.line+=1; self.col=1

    def _skip_comment(self):
        while self._peek() not in (None,'\n'): self._advance()

    def _read_string(self, quote):
        """
        Read a string literal.
        If it contains {expr} interpolation → emit FSTRING token with parts list.
        Plain string → emit STRING token as before.
        """
        line,col=self.line,self.col; self._advance()
        parts=[]      # list of str | sub-source snippets
        buf=[]
        has_interp=False

        while True:
            ch=self._peek()
            if ch is None: raise LexError("unterminated string",line,col)
            if ch==quote: self._advance(); break
            if ch=='\\':
                self._advance(); esc=self._peek()
                escs={'n':'\n','t':'\t','\\':'\\','\'':'\'','"':'"','{':'{','}':'}'}
                if esc in escs: buf.append(escs[esc]); self._advance()
                else: raise LexError(f"unknown escape \\{esc}",self.line,self.col)
            elif ch=='{':
                # start of interpolation {expr}
                has_interp=True
                if buf: parts.append(''.join(buf)); buf=[]
                self._advance()   # consume '{'
                expr_src=[]
                depth=1
                while self._peek() is not None and depth>0:
                    c=self._peek()
                    if c=='{': depth+=1
                    elif c=='}': depth-=1
                    if depth>0: expr_src.append(c)
                    self._advance()
                parts.append(('expr',''.join(expr_src)))
            else:
                buf.append(ch); self._advance()

        if buf: parts.append(''.join(buf))

        if has_interp:
            self.tokens.append(Token(TokenType.FSTRING, parts, line, col))
        else:
            text=''.join(p for p in parts if isinstance(p,str))
            self.tokens.append(Token(TokenType.STRING, text, line, col))

    def _read_number(self):
        line,col=self.line,self.col; start=self.pos
        while self._peek() and self._peek().isdigit(): self._advance()
        if self._peek()=='.' and self._peek_next() and self._peek_next().isdigit():
            self._advance()
            while self._peek() and self._peek().isdigit(): self._advance()
            self.tokens.append(Token(TokenType.FLOAT,float(self.source[start:self.pos]),line,col))
        else:
            self.tokens.append(Token(TokenType.INTEGER,int(self.source[start:self.pos]),line,col))

    def _peek(self, offset=0):
        i=self.pos+offset
        return self.source[i] if i < len(self.source) else None
    def _peek_next(self): return self._peek(1)
    def _advance(self):
        ch=self.source[self.pos]; self.pos+=1; self.col+=1; return ch
    def _add(self,ttype,value,advance=0):
        self.tokens.append(Token(ttype,value,self.line,self.col))
        for _ in range(advance): self._advance()
