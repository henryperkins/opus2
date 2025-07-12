#!/usr/bin/env python3
"""
Remove all docstrings and #-comments from a Python source file.

Usage:
    python strip_comments.py <input.py> <output.py>
"""

from __future__ import annotations
import ast, io, sys, tokenize, textwrap
from pathlib import Path
from typing import Final

class _DocstringStripper(ast.NodeTransformer):
    def visit_FunctionDef(self, node):      # functions & methods
        self.generic_visit(node)
        if (isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: E305
    def visit_ClassDef(self, node):             # classes
        self.generic_visit(node)
        if (isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body.pop(0)
        return node

def _strip_docstrings(src: str) -> str:
    tree = ast.parse(src)
    if (isinstance(tree.body[0], ast.Expr)        # module-level docstring
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        tree.body.pop(0)
    tree = _DocstringStripper().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)

def _strip_hash_comments(src: str) -> str:
    out: list[str] = []
    tok_gen = tokenize.generate_tokens(io.StringIO(src).readline)
    for tok_type, tok_str, *_ in tok_gen:
        if tok_type == tokenize.COMMENT:
            continue
        out.append(tok_str)
    return tokenize.untokenize(out)

def main(inp: str, outp: str) -> None:
    raw = Path(inp).read_text(encoding="utf-8")
    no_docs = _strip_docstrings(raw)
    clean = _strip_hash_comments(no_docs)
    Path(outp).write_text(clean, encoding="utf-8")
    print(f"Stripped file written → {outp}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: strip_comments.py <input.py> <output.py>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
