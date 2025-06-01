# backend/app/code_processing/language_detector.py
"""Language detection for code files based on extensions and content."""
from pathlib import Path
from typing import Optional
import re


class LanguageDetector:
    """Detect programming language from file extension and content."""

    # Extension to language mapping
    EXTENSION_MAP = {
        ".py": "python",
        ".pyw": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
    }

    # Common shebang patterns
    SHEBANG_PATTERNS = {
        r"python[23]?": "python",
        r"node": "javascript",
        r"tsx?": "typescript",
    }

    @classmethod
    def detect_from_filename(cls, filename: str) -> Optional[str]:
        """Detect language from file extension."""
        path = Path(filename)
        ext = path.suffix.lower()
        return cls.EXTENSION_MAP.get(ext)

    @classmethod
    def detect_from_content(cls, content: str) -> Optional[str]:
        """Detect language from file content (shebang, etc)."""
        if not content:
            return None

        lines = content.split("\n", 1)
        if not lines:
            return None

        first_line = lines[0].strip()

        # Check shebang
        if first_line.startswith("#!"):
            for pattern, language in cls.SHEBANG_PATTERNS.items():
                if re.search(pattern, first_line, re.IGNORECASE):
                    return language

        # Check for TypeScript/JSX specific patterns
        if "import React" in content or "from react" in content:
            return "javascript"
        if "interface " in content or "type " in content:
            if "<" in content and ">" in content:  # Likely TSX
                return "typescript"

        return None

    @classmethod
    def detect(cls, filename: str, content: Optional[str] = None) -> Optional[str]:
        """Detect language using both filename and content."""
        # Try filename first
        language = cls.detect_from_filename(filename)
        if language:
            return language

        # Try content if provided
        if content:
            return cls.detect_from_content(content)

        return None

    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if language is supported for parsing."""
        return language in {"python", "javascript", "typescript"}


def detect_language(filename: str, content: Optional[str] = None) -> Optional[str]:
    """Convenience function for language detection."""
    return LanguageDetector.detect(filename, content)
