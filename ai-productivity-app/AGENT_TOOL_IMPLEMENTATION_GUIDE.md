# Agent Tool Implementation Guide

This guide provides detailed, step-by-step instructions to implement four new tools for the agentic RAG system. These tools will expand the agent's capabilities beyond code analysis to include Git history, code usages, documentation, and static analysis.

---

### High-Level Strategy

The implementation process for each tool follows a modular pattern:

1.  **Create a New Service:** For each new tool, create a dedicated service class in `backend/app/services/`. This encapsulates the logic for that tool, keeping the codebase clean and maintainable.
2.  **Define a Trigger:** Use the `StructuralSearch` service to define a new keyword prefix (e.g., `commit:`, `usages:`, `doc:`, `lint:`) that will act as a specific trigger to invoke your new tool.
3.  **Integrate into `HybridSearch`:** Modify the main `HybridSearch` service to recognize the new trigger and route the query to your new service. This makes the central agent "smarter" by allowing it to select the right tool for the job.
4.  **Return Standardized Results:** Ensure your new service returns data in the same format as the existing searchers: a list of dictionaries, where each dictionary contains `type`, `score`, `content`, and `metadata` keys. This ensures consistency and compatibility with the existing ranking and display logic.

---

## Tool 1: Git History Searcher

**Goal:** Allow the agent to search commit logs and `git blame` output to understand the history and intent behind code.

**Strategy:** Use the `GitPython` library to interact with the project's Git repository programmatically.

### Step-by-Step Implementation:

**1. Add Dependency:**
Add `GitPython` to the backend's requirements file.

**File:** `backend/requirements.txt`
```
# Add this line
GitPython>=3.1.0
```
After adding the line, reinstall dependencies to ensure it's available in the environment.

**2. Create the `GitHistorySearcher` Service:**
Create a new file to house the service logic.

**File:** `backend/app/services/git_history_searcher.py`
```python
# backend/app/services/git_history_searcher.py
import git
from typing import List, Dict, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class GitHistorySearcher:
    """Search git history, including commits and blame."""

    def __init__(self, project_path: str):
        try:
            # The project's git repository should be cloned here by ImportService
            self.repo = git.Repo(project_path)
        except git.exc.NoSuchPathError:
            logger.warning(f"No git repository found at {project_path}")
            self.repo = None
        except git.exc.InvalidGitRepositoryError:
            logger.warning(f"Invalid git repository at {project_path}")
            self.repo = None

    def search_commits(self, query: str, limit: int = 20) -> List[Dict]:
        """Search commit messages for a query."""
        if not self.repo:
            return []

        try:
            commits = list(self.repo.iter_commits(all=True, max_count=limit * 5, paths=None))
            
            results = []
            for commit in commits:
                if query.lower() in commit.message.lower():
                    results.append({
                        "type": "git_commit",
                        "score": 1.0, # Simple scoring, can be improved
                        "content": commit.message,
                        "metadata": {
                            "commit_hash": commit.hexsha,
                            "author": commit.author.name,
                            "date": commit.committed_datetime.isoformat(),
                            "files_changed": list(commit.stats.files.keys())
                        }
                    })
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Error searching commits: {e}")
            return []

    def get_blame(self, file_path: str, line_number: int) -> List[Dict]:
        """Get git blame information for a specific line."""
        if not self.repo:
            return []
        
        try:
            blame_entries = self.repo.blame(rev='HEAD', file=file_path)
            # Find the blame entry for the specific line
            target_entry = None
            current_line = 0
            for entry in blame_entries:
                if current_line + len(entry.lines) >= line_number:
                    target_entry = entry
                    break
                current_line += len(entry.lines)

            if not target_entry:
                return []

            commit = target_entry.commit
            return [{
                "type": "git_blame",
                "score": 1.0,
                "content": f"Line {line_number} in {file_path} was last changed by {commit.author.name} in commit {commit.hexsha[:7]}.\n\nCommit Message:\n{commit.message}",
                "metadata": {
                    "file_path": file_path,
                    "line_number": line_number,
                    "commit_hash": commit.hexsha,
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                }
            }]
        except Exception as e:
            logger.error(f"Error getting git blame for {file_path}:{line_number}: {e}")
            return []
```

**3. Integrate with `StructuralSearch` and `HybridSearch`:**

*   **Modify `StructuralSearch` (`backend/app/services/structural_search.py`):**
    Add new patterns to the `self.patterns` dictionary to recognize the `commit:` and `blame:` keywords.

    ```python
    # In StructuralSearch.__init__
    self.patterns = {
        # ... existing patterns
        "commit": re.compile(r"^commit:(.+)$", re.I),
        "blame": re.compile(r"^blame:(.+):(\d+)$", re.I),
        "file": re.compile(r"^file:(.+)$", re.I),
        # ... rest of the patterns
    }

    # In StructuralSearch._parse_query
    # ... inside the for loop
    if match:
        if pattern_name == "blame":
            return {
                "type": "blame",
                "file": match.group(1).strip(),
                "line": int(match.group(2))
            }
        elif pattern_name == "commit":
            return {"type": "commit", "term": match.group(1).strip()}
        # ... other elifs
    ```

*   **Modify `HybridSearch` (`backend/app/services/hybrid_search.py`):**
    Update the main search method to call the new service when the new keywords are detected.
    *Note: The instantiation of `GitHistorySearcher` needs access to the project's specific path on disk. This logic will need careful placement where `project_id` is available.*

    ```python
    # Add import at the top
    from app.services.git_history_searcher import GitHistorySearcher

    # In HybridSearch.search
    # ... after parsing filters
    
    # Check for special search types from structural parse
    structural_parsed = self.structural_search._parse_query(query)
    if structural_parsed:
        search_type = structural_parsed.get("type")
        # You'll need to instantiate the searcher with the correct project path
        # This is a simplified example assuming one project_id is primary
        project_repo_path = f"/data/git/{project_ids[0]}"

        if search_type == "commit":
            git_searcher = GitHistorySearcher(project_repo_path)
            return await git_searcher.search_commits(structural_parsed["term"], limit)
        if search_type == "blame":
            git_searcher = GitHistorySearcher(project_repo_path)
            return await git_searcher.get_blame(structural_parsed["file"], structural_parsed["line"])
        
        # Prioritize structural search for other specific queries
        search_types = ["structural"]

    # ... rest of the search logic
    ```

---

## Tool 2: Call Graph & Usage Searcher

**Goal:** Allow the agent to find all usages of a function or class to understand its impact and relationships.

**Strategy:** Use the `jedi` library, a powerful static analysis tool for Python. This implementation will focus on Python code first as a proof-of-concept.

### Step-by-Step Implementation:

**1. Add Dependency:**
Add `jedi` to `backend/requirements.txt`.

```
jedi>=0.18.0
```

**2. Create the `UsageSearcher` Service:**
Create a new file for the service.

**File:** `backend/app/services/usage_searcher.py`
```python
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
```

**3. Integration:**
This tool is more interactive than a simple search. It's best exposed as a dedicated API endpoint that can be called from the UI (e.g., when a user right-clicks a symbol).

*   **Create a new API Endpoint (in `backend/app/routers/code.py`):**

    ```python
    # backend/app/routers/code.py
    # Add imports
    from app.services.usage_searcher import UsageSearcher
    from pydantic import BaseModel

    class UsageRequest(BaseModel):
        file_path: str
        line: int
        column: int

    @router.post("/{project_id}/usages", response_model=List[Dict])
    async def find_symbol_usages(project_id: int, request: UsageRequest, db: Session = Depends(get_db)):
        # Logic to get project path from project_id
        project_path = f"/data/git/{project_id}" # Replace with actual lookup
        
        usage_searcher = UsageSearcher(project_path)
        results = usage_searcher.find_usages(
            file_path=request.file_path,
            line=request.line,
            column=request.column
        )
        return results
    ```

---

## Tool 3: Documentation & Knowledge Base Searcher

**Goal:** Allow the agent to specifically search within documentation files (e.g., `.md` files, or files in a `docs/` directory).

**Strategy:** This is the simplest tool to implement. We don't need a new service class. We can modify `HybridSearch` to apply a specific filter when a `doc:` keyword is detected.

### Step-by-Step Implementation:

**1. Modify `StructuralSearch`:**
Add a `doc:` keyword to the patterns.

**File:** `backend/app/services/structural_search.py`
```python
# In StructuralSearch.__init__
self.patterns = {
    # ...
    "doc": re.compile(r"^doc:(.+)$", re.I),
    "file": re.compile(r"^file:(.+)$", re.I),
    # ...
}

# In StructuralSearch._parse_query
# ... inside the for loop
if match:
    if pattern_name == "doc":
        return {"type": "doc", "term": match.group(1).strip()}
    # ... other elifs
```

**2. Modify `HybridSearch` to Handle the `doc` Filter:**
Update the main `search` method to recognize the `doc` type and apply a filter.

**File:** `backend/app/services/hybrid_search.py`
```python
# In HybridSearch.search
# ...

# Check for special search types from structural parse
structural_parsed = self.structural_search._parse_query(query)
if structural_parsed and structural_parsed.get("type") == "doc":
    # If it's a doc search, modify the query and add a filter
    query = structural_parsed["term"]
    if filters is None:
        filters = {}
    # This new filter key needs to be handled by the underlying searchers
    filters["file_path_pattern"] = "**/*.md" 
    # You could also filter by a docs directory: "docs/**/*"
    
    # Force only semantic and keyword search for docs
    search_types = ["semantic", "keyword"]

# ... rest of the search logic
```

**3. Update Underlying Searchers:**
You will need to ensure `_semantic_search` and `keyword_search` can handle this new `file_path_pattern` filter. This may require adding a `WHERE file_path LIKE ...` clause to their database queries or filtering results after retrieval.

---

## Tool 4: Static Analysis & Linter Searcher

**Goal:** Allow the agent to run a linter on a file on-demand and report the findings.

**Strategy:** Use Python's `subprocess` module to run `pylint` with a JSON output format, then parse the results into the standard format.

### Step-by-Step Implementation:

**1. Ensure Linters are Installed:**
Make sure `pylint` is in `backend/requirements.txt` or `backend/requirements-dev.txt` and is installed in the virtual environment where the backend runs.

**2. Create the `StaticAnalysisSearcher` Service:**
Create a new file for the service.

**File:** `backend/app/services/static_analysis_searcher.py`
```python
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
```

**3. Integration:**
This tool can be triggered via a keyword or exposed as a dedicated API endpoint.

*   **Add a `lint:` keyword to `StructuralSearch`** (following the pattern from previous tools).
*   **Modify `HybridSearch` to call the new service:**

    ```python
    # Add import at the top
    from app.services.static_analysis_searcher import StaticAnalysisSearcher

    # In HybridSearch.search
    # ...
    structural_parsed = self.structural_search._parse_query(query)
    if structural_parsed:
        search_type = structural_parsed.get("type")
        if search_type == "lint": # Assuming you add a "lint:path/to/file.py" pattern
            # This needs project context
            analysis_searcher = StaticAnalysisSearcher(f"/data/git/{project_ids[0]}")
            return await analysis_searcher.run_pylint(structural_parsed["term"])
        # ... other special searches
    ```

```