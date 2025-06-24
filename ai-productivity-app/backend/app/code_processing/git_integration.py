# backend/app/code_processing/git_integration.py
"""Git repository management for code ingestion."""
from pathlib import Path
import shutil
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import git
import aiofiles

logger = logging.getLogger(__name__)


class GitManager:
    """Manage git repository operations for code ingestion."""

    def __init__(self, base_path: str = "repos"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    async def clone_repository(
        self, repo_url: str, project_id: int, branch: str = "main"
    ) -> Dict[str, Any]:
        """Clone a repository and return file list."""
        repo_name = self._extract_repo_name(repo_url)
        repo_path = self.base_path / f"project_{project_id}" / repo_name

        try:
            # Clone or update
            if repo_path.exists():
                repo = git.Repo(repo_path)
                origin = repo.remote("origin")

                # Fetch and checkout branch
                await asyncio.to_thread(origin.fetch)

                # Try to checkout branch
                try:
                    repo.git.checkout(branch)
                    await asyncio.to_thread(origin.pull)
                except git.exc.GitCommandError:
                    # Branch doesn't exist, try main/master
                    for fallback in ["main", "master"]:
                        try:
                            repo.git.checkout(fallback)
                            await asyncio.to_thread(origin.pull)
                            branch = fallback
                            break
                        except git.exc.GitCommandError:
                            continue
            else:
                # New clone
                repo_path.parent.mkdir(parents=True, exist_ok=True)
                repo = await asyncio.to_thread(
                    git.Repo.clone_from, repo_url, repo_path, branch=branch
                )

            # Get file list
            files = await self._get_repo_files(repo, repo_path)

            return {
                "repo_path": str(repo_path),
                "repo_name": repo_name,
                "commit_sha": repo.head.commit.hexsha,
                "branch": repo.active_branch.name,
                "files": files,
                "total_files": len(files),
            }

        except git.exc.GitError as e:
            logger.error("Git operation failed: %s", e)
            # Clean up on failure
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)
            raise

    async def _get_repo_files(self, repo: git.Repo, repo_path: Path) -> List[Dict]:
        """Get list of processable files from repository."""
        files = []

        # Get all files from git
        try:
            tree = repo.head.commit.tree

            for item in tree.traverse():
                if item.type == "blob":  # It's a file
                    file_path = str(item.path)

                    if self._should_process_file(file_path):
                        full_path = repo_path / file_path

                        # Get file info
                        try:
                            stat = full_path.stat()
                            files.append(
                                {
                                    "path": file_path,
                                    "size": stat.st_size,
                                    "modified": datetime.fromtimestamp(stat.st_mtime),
                                    "sha": item.binsha.hex(),
                                }
                            )
                        except OSError as e:
                            logger.warning("Failed to stat file %s: %s", file_path, e)
        except git.exc.GitError as e:
            logger.error("Failed to traverse git tree: %s", e)

        return files

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on extension and path."""
        path = Path(file_path)

        # Supported extensions
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".mjs"}

        # Skip common non-code directories
        skip_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".pytest_cache",
            "venv",
            "env",
            ".env",
            "tmp",
            "temp",
            ".vscode",
            ".idea",
        }

        # Check path components
        path_parts = set(path.parts)
        if path_parts & skip_dirs:
            return False

        # Skip hidden files
        if any(part.startswith(".") for part in path.parts):
            return False

        # Check extension
        return path.suffix.lower() in extensions

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        # Remove .git suffix
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]

        # Extract name from URL
        parts = repo_url.rstrip("/").split("/")
        return parts[-1] if parts else "unknown"

    async def get_file_content(self, repo_path: str, file_path: str) -> str:
        """Get content of a specific file."""
        full_path = Path(repo_path) / file_path

        # Security check - ensure file is within repo
        try:
            full_path.resolve().relative_to(Path(repo_path).resolve())
        except ValueError:
            raise ValueError("File path outside repository") from None

        try:
            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            async with aiofiles.open(full_path, "r", encoding="latin-1") as f:
                return await f.read()

    async def get_file_diff(
        self, repo_path: str, file_path: str, from_commit: Optional[str] = None
    ) -> Optional[str]:
        """Get diff for a file since a specific commit."""
        repo = git.Repo(repo_path)

        try:
            if from_commit:
                diff = repo.git.diff(from_commit, "HEAD", "--", file_path)
            else:
                # Diff against empty tree (show all content)
                diff = repo.git.diff(
                    "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "HEAD", "--", file_path
                )

            return diff if diff else None
        except git.exc.GitError as e:
            logger.error("Failed to get diff: %s", e)
            return None

    def cleanup_repo(self, project_id: int, repo_name: str):
        """Remove repository directory."""
        repo_path = self.base_path / f"project_{project_id}" / repo_name

        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
