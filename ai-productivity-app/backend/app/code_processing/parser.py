# backend/app/code_processing/parser.py
# flake8: noqa
"""Tree-sitter based code parser

The *real* implementation relies on the ``tree_sitter`` Python bindings which
need a native extension compiled at build-time.  In certain environments – for
instance during CI where the full build tool-chain is not available – this
dependency may be missing which caused the whole FastAPI application to fail
at import time (see `ModuleNotFoundError: No module named 'tree_sitter'`).

To make the service *robust* we now try to import :pymod:`tree_sitter` and fall
back to a **no-op stub** when the library cannot be loaded.  The stub preserves
the public API of :class:`CodeParser` but always returns empty results.
This keeps non-critical features (code upload & parsing) functional while
allowing the rest of the application to start up and be tested.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

# ----------------------------------------------------------------------------
# Optional tree-sitter import
# ----------------------------------------------------------------------------

try:
    import tree_sitter  # type: ignore
    from tree_sitter import Language, Parser, Node  # type: ignore

    _TREE_SITTER_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover – environment without the dep
    tree_sitter = None  # type: ignore
    Language = Parser = Node = None  # type: ignore
    _TREE_SITTER_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Public facing parser class (real implementation if possible, otherwise stub)
# =============================================================================


if _TREE_SITTER_AVAILABLE:  # -------------------------------------------------

    class CodeParser:
        """Parse code using tree-sitter for multiple languages."""

        def __init__(self) -> None:
            self.parsers: dict[str, Parser] = {}
            self.languages: dict[str, Language] = {}
            self._load_languages()

        # ------------------------------------------------------------------
        # Internal helpers
        # ------------------------------------------------------------------

        def _load_languages(self) -> None:
            """Ensure compiled tree-sitter language bundle is present and load it.

            If the shared object does not yet exist we try to compile it
            (best-effort) when the installed *tree_sitter* version still provides
            ``Language.build_library``.  This makes local development and CI
            environments resilient even when the Docker build stage has not run.
            """

            lib_path = os.path.join(os.path.dirname(__file__), "..", "..", "build", "languages.so")
            os.makedirs(os.path.dirname(lib_path), exist_ok=True)

            # ------------------------------------------------------------------
            # Build the grammar bundle on-the-fly when missing
            # ------------------------------------------------------------------
            grammar_paths = [
                "build/tree-sitter/python",
                "build/tree-sitter/javascript",
                "build/tree-sitter/typescript/typescript",
                "build/tree-sitter/typescript/tsx",
            ]
            # Keep only grammars that actually exist on the filesystem to avoid
            # FileNotFoundError inside ``Language.build_library``.
            grammar_paths = [p for p in grammar_paths if os.path.exists(p)]
            if not grammar_paths:
                logger.warning(
                    "No tree-sitter grammar sources found – CodeParser will "
                    "operate in *stub* mode for code parsing"
                )
                return
            if not os.path.exists(lib_path) and hasattr(Language, "build_library"):
                try:
                    Language.build_library(lib_path, grammar_paths)
                    logger.info("Compiled tree-sitter grammars → %s", lib_path)
                except Exception:  # pragma: no cover
                    logger.exception("Failed to compile tree-sitter grammars")
            # ------------------------------------------------------------------
            # Abort when the shared library is still missing after the build
            # attempt so that downstream loading does not raise an OSError.
            # ------------------------------------------------------------------
            if not os.path.exists(lib_path):
                logger.warning("Tree-sitter languages not found at %s", lib_path)
                return

            try:
                # tree_sitter v0.20 removed Language.build_library. Compile
                # only when the helper exists (≤0.19).  On newer versions we
                # assume the shared object has been built during the Docker
                # build stage or supplied via an external volume.

                if hasattr(Language, "build_library") and grammar_paths:
                    Language.build_library(lib_path, grammar_paths)

                self.languages = {
                    "python": Language(lib_path, "python"),
                    "javascript": Language(lib_path, "javascript"),
                    "typescript": Language(lib_path, "typescript"),
                    "tsx": Language(lib_path, "tsx"),
                }
            except Exception:  # pragma: no cover – wide net, just log
                logger.exception("Failed to load tree-sitter languages")

        # ------------------------------------------------------------------
        # Public API
        # ------------------------------------------------------------------

        def parse_file(self, content: str, language: str) -> Dict[str, Any]:  # noqa: D401
            """Return a structured representation of *content*.

            When the requested *language* is not supported an error message is
            embedded inside the returned dictionary instead of raising.
            """

            if language not in self.languages:
                return {
                    "symbols": [],
                    "imports": [],
                    "tree": None,
                    "error": f"Language {language} not supported",
                }

            if language not in self.parsers:
                parser = Parser()
                parser.set_language(self.languages[language])
                self.parsers[language] = parser

            parser = self.parsers[language]

            try:
                tree = parser.parse(content.encode())
                return {
                    "symbols": self._extract_symbols(tree, language, content),
                    "imports": self._extract_imports(tree, language, content),
                    "tree": tree,
                    "error": None,
                }
            except Exception as exc:  # pragma: no cover
                logger.exception("Parse error for %s", language)
                return {"symbols": [], "imports": [], "tree": None, "error": str(exc)}

        # ------------------------------------------------------------------
        # AST visitors (internal)
        # ------------------------------------------------------------------

        def _extract_symbols(self, tree: tree_sitter.Tree, language: str, content: str) -> List[Dict]:
            symbols: list[dict[str, Any]] = []

            symbol_types: dict[str, dict[str, str]] = {
                "python": {
                    "function_definition": "function",
                    "class_definition": "class",
                    "decorated_definition": "decorated",
                },
                "javascript": {
                    "function_declaration": "function",
                    "class_declaration": "class",
                    "method_definition": "method",
                    "arrow_function": "arrow_function",
                    "function": "function",
                },
                "typescript": {
                    "function_declaration": "function",
                    "class_declaration": "class",
                    "method_definition": "method",
                    "interface_declaration": "interface",
                    "type_alias_declaration": "type",
                },
                "tsx": {
                    "function_declaration": "function",
                    "class_declaration": "class",
                    "method_definition": "method",
                    "interface_declaration": "interface",
                    "jsx_element": "component",
                },
            }

            types_to_extract = symbol_types.get(language, {})

            def traverse(node: Node) -> None:  # noqa: WPS430 (nested)
                if node.type in types_to_extract:
                    name_node: Node | None = None

                    if language == "python":
                        for child in node.children:
                            if child.type == "identifier":
                                name_node = child
                                break
                    else:
                        for child in node.children:
                            if child.type in ("identifier", "property_identifier"):
                                name_node = child
                                break

                    if name_node:
                        symbol: dict[str, Any] = {
                            "name": content[name_node.start_byte : name_node.end_byte],
                            "type": types_to_extract[node.type],
                            "start_line": node.start_point[0],
                            "end_line": node.end_point[0],
                            "start_byte": node.start_byte,
                            "end_byte": node.end_byte,
                        }

                        if node.type == "class_definition":
                            for child in node.children:
                                if child.type == "argument_list":
                                    symbol["bases"] = self._extract_bases(child, content)

                        symbols.append(symbol)

                for child in node.children:
                    traverse(child)

            traverse(tree.root_node)
            return symbols

        def _extract_imports(self, tree: tree_sitter.Tree, language: str, content: str) -> List[Dict]:
            imports: list[dict[str, Any]] = []

            import_types: dict[str, list[str]] = {
                "python": ["import_statement", "import_from_statement"],
                "javascript": ["import_statement", "import_clause"],
                "typescript": ["import_statement", "import_clause"],
                "tsx": ["import_statement", "import_clause"],
            }

            types_to_extract = import_types.get(language, [])

            def traverse(node: Node) -> None:  # noqa: WPS430 (nested)
                if node.type in types_to_extract:
                    import_text = content[node.start_byte : node.end_byte]

                    import_info: dict[str, Any] = {
                        "statement": import_text,
                        "line": node.start_point[0],
                        "type": node.type,
                    }

                    if language == "python":
                        for child in node.children:
                            if child.type in ("dotted_name", "module"):
                                import_info["module"] = content[child.start_byte : child.end_byte]
                                break
                    else:
                        for child in node.children:
                            if child.type == "string":
                                import_info["module"] = (
                                    content[child.start_byte : child.end_byte].strip("\"'")
                                )
                                break

                    imports.append(import_info)

                for child in node.children:
                    traverse(child)

            traverse(tree.root_node)
            return imports

        def _extract_bases(self, arg_list_node: Node, content: str) -> List[str]:
            bases: list[str] = []
            for child in arg_list_node.children:
                if child.type in ("identifier", "attribute"):
                    bases.append(content[child.start_byte : child.end_byte])
            return bases


else:  # ---------------------------------------------------------------------

    class CodeParser:  # noqa: D401
        """Stub replacement when *tree_sitter* is unavailable.

        The class exposes *the same* public API but returns empty structures so
        that dependent code continues to work.  A single warning is emitted
        during import to aid troubleshooting.
        """

        def __init__(self) -> None:  # noqa: D401
            logger.warning(
                "tree_sitter Python bindings are not available – "
                "CodeParser will operate in *stub* mode."
            )

        def parse_file(self, content: str, language: str) -> Dict[str, Any]:  # noqa: D401
            return {
                "symbols": [],
                "imports": [],
                "tree": None,
                "error": "tree_sitter not installed",
            }
