# backend/app/code_processing/parser.py
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
            """Load compiled tree-sitter languages, if present on disk."""

            lib_path = os.path.join(os.path.dirname(__file__), "..", "..", "build", "languages.so")

            if not os.path.exists(lib_path):
                logger.warning("Tree-sitter languages not found at %s", lib_path)
                return

            try:
                Language.build_library(
                    lib_path,
                    [
                        "build/tree-sitter/python",
                        "build/tree-sitter/javascript",
                        "build/tree-sitter/typescript/typescript",
                        "build/tree-sitter/typescript/tsx",
                    ],
                )

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

import os
import logging

logger = logging.getLogger(__name__)


class CodeParser:
    """Parse code using tree-sitter for multiple languages."""

    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._load_languages()

    def _load_languages(self):
        """Load compiled tree-sitter languages."""
        # Path to compiled languages
        lib_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "build", "languages.so"
        )

        if not os.path.exists(lib_path):
            logger.warning(f"Tree-sitter languages not found at {lib_path}")
            return

        try:
            # Load languages
            Language.build_library(
                lib_path,
                [
                    "build/tree-sitter/python",
                    "build/tree-sitter/javascript",
                    "build/tree-sitter/typescript/typescript",
                    "build/tree-sitter/typescript/tsx",
                ],
            )

            self.languages = {
                "python": Language(lib_path, "python"),
                "javascript": Language(lib_path, "javascript"),
                "typescript": Language(lib_path, "typescript"),
                "tsx": Language(lib_path, "tsx"),
            }
        except Exception as e:
            logger.error(f"Failed to load tree-sitter languages: {e}")

    def parse_file(self, content: str, language: str) -> Dict[str, Any]:
        """Parse file and extract structured information."""
        if language not in self.languages:
            return {
                "symbols": [],
                "imports": [],
                "tree": None,
                "error": f"Language {language} not supported",
            }

        # Get or create parser
        if language not in self.parsers:
            parser = Parser()
            parser.set_language(self.languages[language])
            self.parsers[language] = parser

        parser = self.parsers[language]

        try:
            # Parse content
            tree = parser.parse(bytes(content, "utf8"))

            return {
                "symbols": self._extract_symbols(tree, language, content),
                "imports": self._extract_imports(tree, language, content),
                "tree": tree,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Parse error for {language}: {e}")
            return {"symbols": [], "imports": [], "tree": None, "error": str(e)}

    def _extract_symbols(
        self, tree: tree_sitter.Tree, language: str, content: str
    ) -> List[Dict]:
        """Extract functions, classes, methods from AST."""
        symbols = []

        # Language-specific node types
        symbol_types = {
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

        def traverse(node: Node):
            """Recursively traverse AST."""
            if node.type in types_to_extract:
                # Extract symbol name
                name_node = None

                if language == "python":
                    # For Python, name is direct child
                    for child in node.children:
                        if child.type == "identifier":
                            name_node = child
                            break
                else:
                    # For JS/TS, look for identifier or property_identifier
                    for child in node.children:
                        if child.type in ["identifier", "property_identifier"]:
                            name_node = child
                            break

                if name_node:
                    symbol = {
                        "name": content[name_node.start_byte : name_node.end_byte],
                        "type": types_to_extract[node.type],
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0],
                        "start_byte": node.start_byte,
                        "end_byte": node.end_byte,
                    }

                    # Extract additional metadata
                    if node.type == "class_definition":
                        # Check for inheritance
                        bases = []
                        for child in node.children:
                            if child.type == "argument_list":
                                bases = self._extract_bases(child, content)
                        symbol["bases"] = bases

                    symbols.append(symbol)

            # Continue traversal
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return symbols

    def _extract_imports(
        self, tree: tree_sitter.Tree, language: str, content: str
    ) -> List[Dict]:
        """Extract import statements."""
        imports = []

        import_types = {
            "python": ["import_statement", "import_from_statement"],
            "javascript": ["import_statement", "import_clause"],
            "typescript": ["import_statement", "import_clause"],
            "tsx": ["import_statement", "import_clause"],
        }

        types_to_extract = import_types.get(language, [])

        def traverse(node: Node):
            """Find all import nodes."""
            if node.type in types_to_extract:
                import_text = content[node.start_byte : node.end_byte]

                # Parse import details
                import_info = {
                    "statement": import_text,
                    "line": node.start_point[0],
                    "type": node.type,
                }

                # Extract module name
                if language == "python":
                    # Look for dotted_name or module
                    for child in node.children:
                        if child.type in ["dotted_name", "module"]:
                            import_info["module"] = content[
                                child.start_byte : child.end_byte
                            ]
                            break
                else:
                    # Look for string (module specifier)
                    for child in node.children:
                        if child.type == "string":
                            import_info["module"] = content[
                                child.start_byte : child.end_byte
                            ].strip("\"'")
                            break

                imports.append(import_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _extract_bases(self, arg_list_node: Node, content: str) -> List[str]:
        """Extract base classes from argument list."""
        bases = []
        for child in arg_list_node.children:
            if child.type in ["identifier", "attribute"]:
                bases.append(content[child.start_byte : child.end_byte])
        return bases
