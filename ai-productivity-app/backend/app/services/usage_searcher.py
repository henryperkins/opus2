# backend/app/services/usage_searcher.py
import jedi
from typing import List, Dict
import logging
import os

logger = logging.getLogger(__name__)

class UsageSearcher:
    """Find usages of symbols using static analysis."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        try:
            self.jedi_project = jedi.Project(path=self.project_path)
        except Exception as e:
            logger.error(f"Failed to initialize Jedi project at {self.project_path}: {e}")
            self.jedi_project = None

    def find_usages(self, file_path: str, line: int, column: int, limit: int = 50) -> List[Dict]:
        """Find all references to a symbol at a given location."""
        if not self.jedi_project:
            return []

        full_file_path = os.path.join(self.project_path, file_path)
        
        try:
            with open(full_file_path, 'r') as f:
                source_code = f.read()

            script = jedi.Script(code=source_code, path=full_file_path, project=self.jedi_project)
            references = script.get_references(line=line, column=column)

            results = []
            for ref in references[:limit]:
                # Read a snippet of the line for context
                line_content = ref.get_line_code().strip()

                results.append({
                    "type": "usage",
                    "score": 1.0,
                    "content": line_content,
                    "metadata": {
                        "file_path": ref.module_path,
                        "line_number": ref.line,
                        "column": ref.column,
                        "symbol_name": ref.name,
                    }
                })
            return results
        except Exception as e:
            logger.error(f"Error finding usages with Jedi: {e}")
            return []