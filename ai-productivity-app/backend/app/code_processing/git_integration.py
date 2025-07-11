# backend/app/code_processing/git_integration.py
"""Git repository management for code ingestion."""
from pathlib import Path
import os
import tempfile
import stat
import shutil
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import git
import aiofiles
import fnmatch
import contextlib

logger = logging.getLogger(__name__)


class GitManager:
    """Manage git repository operations for code ingestion."""

    def __init__(self, base_path: str = "repos"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_token(url: str, token: str | None) -> str:
        """Embed *token* into HTTPS git URL if provided."""

        if token and url.startswith("https://"):
            # Avoid duplicating credentials if already present
            if "@" not in url.split("//", 1)[1]:
                return url.replace("https://", f"https://{token}@")
        return url

    @staticmethod
    @contextlib.contextmanager
    def _temp_ssh_key_env(key_material: str | None):  # noqa: D401 – CM helper
        """Context manager that writes *key_material* to a temp file and sets
        ``GIT_SSH_COMMAND`` to use it.  If *key_material* is *None* the context
        does nothing.
        """

        if key_material is None:
            # Nothing to do – behave as a no-op context manager
            yield None
            return

        # Write key to a secure temporary file
        with tempfile.NamedTemporaryFile(
            "w", delete=False, prefix="ssh_key_", suffix=".pem"
        ) as tmp:
            tmp.write(key_material)
            key_path = tmp.name

        # Restrict permissions (0600) – required by ssh
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        original_git_ssh_cmd = os.environ.get("GIT_SSH_COMMAND")
        os.environ["GIT_SSH_COMMAND"] = (
            f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"
        )

        try:
            yield key_path  # expose in case callers need it
        finally:
            # Restore previous env var
            if original_git_ssh_cmd is None:
                os.environ.pop("GIT_SSH_COMMAND", None)
            else:
                os.environ["GIT_SSH_COMMAND"] = original_git_ssh_cmd

            # Best-effort cleanup of the temporary key
            with contextlib.suppress(OSError):
                os.remove(key_path)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def clone_repository(
        self,
        repo_url: str,
        project_id: int,
        branch: str = "main",
        token: str | None = None,
        ssh_key: str | None = None,
        include_patterns: List[str] | None = None,
        exclude_patterns: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Clone a repository and return file list."""
        # Inject personal-access token for HTTPS URLs when provided ----------------

        repo_url = self._inject_token(repo_url, token)

        repo_name = self._extract_repo_name(repo_url)

        # Use a *job-specific* clone directory to avoid collisions between
        # concurrent import jobs targeting the same project / repository.
        # Falling back to a deterministic path when it is safe to do so will
        # speed up subsequent incremental syncs, but for the first
        # implementation we choose correctness over reuse.

        from uuid import uuid4

        repo_path = (
            self.base_path / f"project_{project_id}" / f"tmp_{uuid4().hex}" / repo_name
        )

        try:
            # Use provided SSH private key for the entire git operation block
            with self._temp_ssh_key_env(ssh_key):

                # ---------------------------------------------------------
                # Clone or update repository
                # ---------------------------------------------------------

                if repo_path.exists():
                    repo = await asyncio.to_thread(git.Repo, repo_path)
                    origin = await asyncio.to_thread(repo.remote, "origin")

                    # Fetch shallow history to keep clone small
                    await asyncio.to_thread(
                        origin.fetch, depth=1, prune=True, tags=False
                    )

                    # Checkout requested branch – fail loudly if missing
                    try:
                        await asyncio.to_thread(repo.git.checkout, branch)
                        await asyncio.to_thread(origin.pull)
                    except git.exc.GitCommandError as exc:
                        raise ValueError(
                            f"Branch '{branch}' not found in repository"
                        ) from exc
                else:
                    # New clone: first try with specified branch, then fall back
                    repo_path.parent.mkdir(parents=True, exist_ok=True)
                    # Try cloning with explicit branch; if that fails due to
                    # missing branch, surface error to caller instead of
                    # silently falling back.

                    try:
                        repo = await asyncio.to_thread(
                            git.Repo.clone_from,
                            repo_url,
                            repo_path,
                            branch=branch,
                            depth=1,
                        )
                    except git.exc.GitCommandError as exc:
                        raise ValueError(
                            f"Branch '{branch}' not found in repository"
                        ) from exc

                # ---------------------------------------------------------
                # Build file manifest
                # ---------------------------------------------------------

                files = await self._get_repo_files(
                    repo, repo_path, include_patterns, exclude_patterns
                )
                commit_sha = await asyncio.to_thread(lambda: repo.head.commit.hexsha)
                active_branch = await asyncio.to_thread(lambda: repo.active_branch.name)

                return {
                    "repo_path": str(repo_path),
                    "repo_name": repo_name,
                    "commit_sha": commit_sha,
                    "branch": active_branch,
                    "files": files,
                    "total_files": len(files),
                }

        except git.exc.GitError as e:
            logger.error("Git operation failed: %s", e)
            # Clean up on failure
            if repo_path.exists():
                await asyncio.to_thread(shutil.rmtree, repo_path, ignore_errors=True)
            raise

    async def _get_repo_files(
        self,
        repo: git.Repo,
        repo_path: Path,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> List[Dict]:
        """Get list of processable files from repository."""
        files = []

        # Get all files from git
        try:
            tree = await asyncio.to_thread(lambda: repo.head.commit.tree)

            # This loop can be long, run it in a thread
            def _traverse_and_collect():
                collected = []
                for item in tree.traverse():
                    if item.type == "blob":  # It's a file
                        file_path = str(item.path)

                        full_path = repo_path / file_path
                        if self._should_process_file(
                            file_path, full_path, include_patterns, exclude_patterns
                        ):
                            try:
                                stat = full_path.stat()
                                collected.append(
                                    {
                                        "path": file_path,
                                        "size": stat.st_size,
                                        "modified": datetime.fromtimestamp(
                                            stat.st_mtime
                                        ),
                                        "sha": item.binsha.hex(),
                                    }
                                )
                            except OSError as e:
                                logger.warning(
                                    "Failed to stat file %s: %s", file_path, e
                                )
                return collected

            files = await asyncio.to_thread(_traverse_and_collect)

        except git.exc.GitError as e:
            logger.error("Failed to traverse git tree: %s", e)

        return files

    def _should_process_file(
        self,
        file_path: str,
        full_path: Path,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> bool:
        """Check if file should be processed based on extension, path, and content."""

        # ------------------------------------------------------------------
        # 0. User-supplied include / exclude patterns
        # ------------------------------------------------------------------
        # Precedence rules (mirroring gitignore & ripgrep semantics):
        #   1. If a file matches *include_patterns* → always keep it.
        #   2. Otherwise, if it matches *exclude_patterns* → drop it.

        if include_patterns and any(
            fnmatch.fnmatch(file_path, p) for p in include_patterns
        ):
            return True

        if exclude_patterns and any(
            fnmatch.fnmatch(file_path, p) for p in exclude_patterns
        ):
            return False

        # 1. File size limit (e.g., 2 MB)
        try:
            if full_path.stat().st_size > 2 * 1024 * 1024:
                logger.warning("Skipping large file: %s", file_path)
                return False
        except OSError:
            return False  # Cannot stat, skip

        # 2. Binary file detection
        try:
            with open(full_path, "rb") as f:
                if b"\0" in f.read(8192):
                    logger.warning("Skipping binary file: %s", file_path)
                    return False
        except OSError:
            return False  # Cannot read, skip

        path = Path(file_path)

        # 3. Supported extensions
        extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".mjs",
            ".md",
            ".rst",
            ".txt",
        }

        # 4. Skip common non-code directories.
        # `path.parents` returns a sequence of Path objects, not their string
        # names, so previously an intersection against `skip_dirs` (a set of
        # strings) always evaluated to an empty set. That made the filter
        # ineffective and caused heavy traversal of huge folders (e.g.
        # `node_modules`). We now inspect the individual path *parts* instead.

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
            "tmp",
            "temp",
            ".vscode",
            ".idea",
        }

        # If any segment of the path matches a skipped directory, exclude it.
        if any(segment in skip_dirs for segment in path.parts):
            return False

        # 5. Skip hidden *directories* (".git", ".idea" …) but allow
        # individual dot-files such as `.env.example` that users often want
        # indexed for context.

        if any(part.startswith(".") for part in path.parts[:-1]):
            return False

        # 6. Check extension
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

        MAX_BYTES = 2 * 1024 * 1024  # 2 MB safety cap

        try:
            async with aiofiles.open(full_path, "rb") as f:
                data = await f.read(MAX_BYTES + 1)
        except OSError as exc:
            logger.warning("Failed to read file %s: %s", full_path, exc)
            raise

        if len(data) > MAX_BYTES:
            raise ValueError("File too large to display")

        # Attempt UTF-8 first, then latin-1 fallback
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")

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
