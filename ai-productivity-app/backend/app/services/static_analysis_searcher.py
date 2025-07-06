# backend/app/services/static_analysis_searcher.py
import subprocess
import json
from typing import List, Dict
import logging
import os

logger = logging.getLogger(__name__)

class StaticAnalysisSearcher:
    """Runs static analysis tools and returns results."""

    def __init__(self, project_path: str):
        self.project_path = project_path

    def run_pylint(self, file_path: str) -> List[Dict]:
        """Run pylint on a specific file and parse the JSON output."""
        full_file_path = os.path.join(self.project_path, file_path)
        
        if not os.path.exists(full_file_path):
            return [{"type": "error", "score": 0, "content": f"File not found: {file_path}", "metadata": {}}]

        command = [
            "pylint",
            full_file_path,
            "--output-format=json"
        ]
        
        try:
            # Run from the project root so pylint can resolve imports correctly
            result = subprocess.run(command, capture_output=True, text=True, cwd=self.project_path)
            
            # Pylint exits with a non-zero code if issues are found, so we can't just check the return code.
            # We must attempt to parse stdout even if the command "fails".
            try:
                issues = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Pylint produced non-JSON output for {file_path}: {result.stdout or result.stderr}")
                return []

            results = []
            for issue in issues:
                results.append({
                    "type": f"lint_{issue['type']}",
                    "score": 0.8, # Can be adjusted based on issue severity
                    "content": f"[{issue['symbol']}] {issue['message']}",
                    "metadata": {
                        "file_path": issue['path'],
                        "line_number": issue['line'],
                        "column": issue['column'],
                        "message_id": issue['message-id'],
                    }
                })
            return results

        except FileNotFoundError:
            logger.error("pylint command not found. Is it installed in the environment?")
            return []
        except Exception as e:
            logger.error(f"Error running pylint on {file_path}: {e}")
            return []