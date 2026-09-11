"""
约束条件表达式。

语法（与知识库里现有 condition_expr 对齐）：
  $trait_id >= 120
  $a > 25 AND $b > 80
  $heading_days < 65
  NOT ($x <= 3)
  $flag = 'severe'

不执行 Python、不用 eval。缺绑定的 $变量时视为无法判定，约束不触发。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


class ExprError(ValueError):
    pass


@dataclass(frozen=True)
class Literal:
    value: float | str


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Compare:
    left: Var
    op: str
    right: Literal


@dataclass(frozen=True)
class Not:
    inner: "Node"


@dataclass(frozen=True)
class BoolOp:
    op: str  # AND / OR
    items: tuple["Node", ...]


Node = Union[Literal, Var, Compare, Not, BoolOp]


def referenced_ids(node: Node) -> list[str]:
    if isinstance(node, Var):
        return [node.name]
    if isinstance(node, Compare):
        return [node.left.name]
    if isinstance(node, Not):
        return referenced_ids(node.inner)
    if isinstance(node, BoolOp):
        names: list[str] = []
        for item in node.items:
            for n in referenced_ids(item):
                if n not in names:
                    names.append(n)
        return names
    return []


def parse(expr: str) -> Node:
    tokens = _tokenize(expr)
    if not tokens:
        raise ExprError("空表达式")
    parser = _Parser(tokens)
    node = parser.parse_or()
    if parser.i < len(tokens):
        raise ExprError(f"表达式末尾有多余记号: {tokens[parser.i]}")
    return node


def evaluate(node: Node, env: dict[str, Any]) -> bool:
    """env 缺变量时抛 KeyError，由调用方当成「无法判定」。"""
    if isinstance(node, Compare):
        if node.left.name not in env:
            raise KeyError(node.left.name)
        return _compare(env[node.left.name], node.op, node.right.value)
    if isinstance(node, Not):
        return not evaluate(node.inner, env)
    if isinstance(node, BoolOp):
        if node.op == "AND":
            return all(evaluate(item, env) for item in node.items)
        return any(evaluate(item, env) for item in node.items)
    raise ExprError(f"无法求值的节点: {type(node).__name__}")


def try_evaluate(expr: str, env: dict[str, Any]) -> tuple[bool, str]:
    """
    返回 (是否成立, 原因)。
    原因非空表示跳过：空表达式、语法错误、缺变量。
    """
    text = (expr or "").strip()
    if not text:
        return False, "empty"
    try:
        node = parse(text)
    except ExprError as e:
        return False, f"syntax:{e}"
    try:
        return evaluate(node, env), ""
    except KeyError as e:
        return False, f"unbound:{e.args[0]}"


def _compare(left: Any, op: str, right: Any) -> bool:
    if op in ("=", "=="):
        return left == right
    if op == "!=":
        return left != right
    try:
        lv = float(left)
        rv = float(right)
    except (TypeError, ValueError):
        return False
    if op == ">":
        return lv > rv
    if op == ">=":
        return lv >= rv
    if op == "<":
        return lv < rv
    if op == "<=":
        return lv <= rv
    raise ExprError(f"未知比较符: {op}")


def _tokenize(expr: str) -> list[tuple[str, str]]:
    s = expr.strip()
    i = 0
    out: list[tuple[str, str]] = []
    n = len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if s.startswith(">=", i) or s.startswith("<=", i) or s.startswith("!=", i) or s.startswith("==", i):
            out.append(("op", s[i : i + 2]))
            i += 2
            continue
        if ch in "><=":
            out.append(("op", ch))
            i += 1
            continue
        if ch in "()":
            out.append(("paren", ch))
            i += 1
            continue
        if ch in "'\"":
            j = i + 1
            while j < n and s[j] != ch:
                j += 1
            if j >= n:
                raise ExprError("字符串未闭合")
            out.append(("string", s[i + 1 : j]))
            i = j + 1
            continue
        if ch == "$":
            j = i + 1
            if j >= n or not (s[j].isalpha() or s[j] == "_"):
                raise ExprError("$ 后需要标识符")
            j += 1
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            out.append(("var", s[i + 1 : j]))
            i = j
            continue
        if (
            ch.isdigit()
            or (ch == "." and i + 1 < n and s[i + 1].isdigit())
            or (ch == "-" and i + 1 < n and (s[i + 1].isdigit() or s[i + 1] == "."))
        ):
            j = i + 1 if ch == "-" else i
            if j < n and s[j] == ".":
                j += 1
            while j < n and s[j].isdigit():
                j += 1
            if j < n and s[j] == ".":
                j += 1
                while j < n and s[j].isdigit():
                    j += 1
            out.append(("number", s[i:j]))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            word = s[i:j].upper()
            if word in ("AND", "OR", "NOT"):
                out.append(("kw", word))
            else:
                raise ExprError(f"未知关键字: {s[i:j]}")
            i = j
            continue
        raise ExprError(f"非法字符: {ch}")
    return out


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> tuple[str, str] | None:
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def eat(self, kind: str | None = None, value: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ExprError("表达式不完整")
        if kind and tok[0] != kind:
            raise ExprError(f"期望 {kind}，得到 {tok}")
        if value and tok[1] != value:
            raise ExprError(f"期望 {value}，得到 {tok[1]}")
        self.i += 1
        return tok

    def parse_or(self) -> Node:
        items = [self.parse_and()]
        while self.peek() == ("kw", "OR"):
            self.eat("kw", "OR")
            items.append(self.parse_and())
        if len(items) == 1:
            return items[0]
        return BoolOp("OR", tuple(items))

    def parse_and(self) -> Node:
        items = [self.parse_not()]
        while self.peek() == ("kw", "AND"):
            self.eat("kw", "AND")
            items.append(self.parse_not())
        if len(items) == 1:
            return items[0]
        return BoolOp("AND", tuple(items))

    def parse_not(self) -> Node:
        if self.peek() == ("kw", "NOT"):
            self.eat("kw", "NOT")
            return Not(self.parse_not())
        return self.parse_atom()

    def parse_atom(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise ExprError("表达式不完整")
        if tok == ("paren", "("):
            self.eat("paren", "(")
            node = self.parse_or()
            self.eat("paren", ")")
            return node
        if tok[0] != "var":
            raise ExprError("比较左侧必须是 $变量")
        name = self.eat("var")[1]
        op = self.eat("op")[1]
        rhs = self.peek()
        if rhs is None:
            raise ExprError("比较缺少右值")
        if rhs[0] == "number":
            self.eat("number")
            value: float | str = float(rhs[1])
        elif rhs[0] == "string":
            self.eat("string")
            value = rhs[1]
        else:
            raise ExprError("比较右值必须是数字或字符串")
        return Compare(Var(name), op, Literal(value))
