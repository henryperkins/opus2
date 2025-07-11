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
            commits = list(
                self.repo.iter_commits(all=True, max_count=limit * 5, paths=None)
            )

            results = []
            for commit in commits:
                if query.lower() in commit.message.lower():
                    results.append(
                        {
                            "type": "git_commit",
                            "score": 1.0,  # Simple scoring, can be improved
                            "content": commit.message,
                            "metadata": {
                                "commit_hash": commit.hexsha,
                                "author": commit.author.name,
                                "date": commit.committed_datetime.isoformat(),
                                "files_changed": list(commit.stats.files.keys()),
                            },
                        }
                    )
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
            blame_entries = self.repo.blame(rev="HEAD", file=file_path)
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
            return [
                {
                    "type": "git_blame",
                    "score": 1.0,
                    "content": f"Line {line_number} in {file_path} was last changed by {commit.author.name} in commit {commit.hexsha[:7]}.\n\nCommit Message:\n{commit.message}",
                    "metadata": {
                        "file_path": file_path,
                        "line_number": line_number,
                        "commit_hash": commit.hexsha,
                        "author": commit.author.name,
                        "date": commit.committed_datetime.isoformat(),
                    },
                }
            ]
        except Exception as e:
            logger.error(f"Error getting git blame for {file_path}:{line_number}: {e}")
            return []
