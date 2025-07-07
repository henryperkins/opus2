#!/usr/bin/env python3
"""
rename_to_md.py
---------------
Clone (optionally), sparsify, and convert selected source files to `.md`
while wrapping their contents in language-tagged code fences.

Usage examples
--------------

# Local directory, recurse:
    ./rename_to_md.py -d ./my-project -r

# Sparse-clone only two folders from GitHub, convert, recurse:
    ./rename_to_md.py -u https://github.com/henryperkins/opus2 \
        --include ai-productivity-app/backend/app \
        --include ai-productivity-app/frontend/src \
        -r

Key features
------------
* Sparse/partial clone via `git clone --filter=blob:none --sparse`.
* `--include` (repeatable)  choose exactly which sub-trees materialise.
* Fully respects *.gitignore* using `pathspec` if available; reasonable
  fallback (supports wildcards, dir patterns, negations).
* Binary/huge files (>100 kB or containing NUL) are skipped.
* Uses `shutil.copy2` + `unlink` to keep file metadata when renaming.
* Produces an “export” directory that is *not* a Git repo by default.

Requires Git ≥ 2.43 for sparse cone-mode.
"""

from __future__ import annotations

# stdlib
import argparse
import fnmatch
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable, List

# ---------------------------------------------------------------------------
# Optional dependency: pathspec for full .gitignore fidelity
# ---------------------------------------------------------------------------
try:
    import pathspec  # type: ignore
    _HAS_PATHSPEC = True
except ModuleNotFoundError:  # pragma: no cover
    _HAS_PATHSPEC = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("rename_to_md")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",  # treat JSX as JS for highlight-compat
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".log": "text",
    ".txt": "text",
    ".ini": "ini",
}

BINARY_SIZE_LIMIT = 100_000  # bytes

# ---------------------------------------------------------------------------
# .gitignore helpers
# ---------------------------------------------------------------------------


def _collect_gitignore_patterns(root: Path) -> List[str]:
    """Gather raw pattern lines from all .gitignore files under *root*."""
    patterns: List[str] = []
    for gitignore in root.rglob(".gitignore"):
        try:
            for line in gitignore.read_text("utf-8").splitlines():
                stripped = line.rstrip("\n")
                if stripped and not stripped.lstrip().startswith("#"):
                    patterns.append(stripped)
        except Exception:  # pragma: no cover
            continue
    return patterns


if _HAS_PATHSPEC:  # full fidelity -------------------------------------------------

    def build_ignore_spec(root: Path):
        patterns = _collect_gitignore_patterns(root)
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def is_ignored(path: Path, root: Path, ignore_spec) -> bool:
        try:
            rel = path.relative_to(root)
        except ValueError:  # pragma: no cover
            return False
        return ignore_spec.match_file(str(rel))

else:  # lightweight fallback -------------------------------------------------------

    _GLOB_RE = re.compile(r"[*?\[]")

    def _match_one(string: str, pattern: str) -> bool:
        # directory rule (ending slash) = prefix
        if pattern.endswith("/"):
            return string.startswith(pattern.rstrip("/"))
        if _GLOB_RE.search(pattern):
            return fnmatch.fnmatch(string, pattern)
        return string == pattern

    def build_ignore_spec(root: Path):
        raw = _collect_gitignore_patterns(root)
        positive: list[str] = []
        negative: list[str] = []
        for pat in raw:
            (negative if pat.startswith("!") else positive).append(pat.lstrip("!"))

        def _matches(path: Path) -> bool:
            rel = path.relative_to(root)
            s = str(rel)
            matched = any(_match_one(s, p) for p in positive)
            if matched and any(_match_one(s, n) for n in negative):
                matched = False
            return matched

        return _matches

    def is_ignored(path: Path, root: Path, ignore_spec) -> bool:
        return ignore_spec(path)


# ---------------------------------------------------------------------------
# Git helpers – sparse clone
# ---------------------------------------------------------------------------


def sparse_clone(
    url: str,
    dest: Path,
    includes: Iterable[str],
    ref: str | None,
    log: Callable[[str], None],
) -> bool:
    """
    Perform a depth-1, blob-free, sparse clone, then materialise *includes*.
    Returns True on success.
    """
    base_cmd = [
        "git",
        "clone",
        "--filter=blob:none",
        "--depth",
        "1",
        "--sparse",
    ]
    if ref:
        base_cmd += ["--branch", ref]
    base_cmd += [url, str(dest)]

    try:
        subprocess.run(base_cmd, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(
            ["git", "-C", str(dest), "sparse-checkout", "set", "--cone", *includes],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError as exc:
        log(f"sparse-clone failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Workspace preparation
# ---------------------------------------------------------------------------


def prepare_work_dir(
    source: str,
    *,
    is_url: bool,
    includes: List[str],
    ref: str | None,
    output: str | None,
    log: Callable[[str], None],
) -> Path | None:
    """Clone/prepare a working directory and return its path, or None on error."""
    if is_url:  # clone → tmp
        tmp = Path(tempfile.mkdtemp(prefix="rename_to_md_"))
        if not sparse_clone(source, tmp, includes, ref, log):
            return None
        src_dir = tmp
    else:
        src_dir = Path(source).expanduser().resolve()
        if not src_dir.is_dir():
            log(f"Error: '{src_dir}' is not a directory.")
            return None

    out_dir = (
        Path(output).expanduser().resolve()
        if output
        else src_dir.parent / f"{src_dir.name}_export"
    )
    if out_dir.exists():
        log(f"Removing existing '{out_dir}'.")
        shutil.rmtree(out_dir)

    shutil.copytree(
        src_dir,
        out_dir,
        ignore=shutil.ignore_patterns(".git*", ".hg*", ".svn*"),
        symlinks=True,
        dirs_exist_ok=False,
    )
    log(f"Working tree ready → '{out_dir}'.")
    return out_dir


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


def rename_and_wrap(
    directory: Path,
    *,
    recursive: bool,
    dry_run: bool,
    log: Callable[[str], None],
) -> None:
    """Rename & wrap supported files inside *directory*."""
    root = directory.resolve()
    if not root.is_dir():
        log(f"Error: '{root}' is not a directory.")
        return

    ignore_spec = build_ignore_spec(root)

    # Decide walker strategy
    if recursive:
        walker = os.walk(root)
    else:  # top-level only files
        files = [p.name for p in root.iterdir() if p.is_file()]
        walker = [(str(root), [], files)]

    for curr_root, dirs, files in walker:
        curr_root_path = Path(curr_root)

        # prune ignored dirs
        dirs[:] = [d for d in dirs if not is_ignored(curr_root_path / d, root, ignore_spec)]

        for fname in files:
            src = curr_root_path / fname
            if is_ignored(src, root, ignore_spec):
                log(f"skip (ignored)  {src}")
                continue
            if not src.is_file():
                continue

            ext = src.suffix.lower()
            if ext not in EXTENSIONS:
                continue

            dst = src.with_suffix(".md")
            if dst.exists():
                log(f"skip (exists)   {dst}")
                continue

            if dry_run:
                log(f"[DRY] would convert {src} → {dst.name}")
                continue

            # read + size/binary guard
            try:
                raw = src.read_bytes()
            except Exception as exc:
                log(f"read error      {src}: {exc}")
                continue

            if len(raw) > BINARY_SIZE_LIMIT or b"\x00" in raw:
                log(f"skip (binary/large) {src}")
                continue

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                for enc in ("latin-1", "cp1252", "iso-8859-1"):
                    try:
                        text = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    text = raw.decode("utf-8", errors="replace")

            # copy-then-unlink to preserve metadata
            shutil.copy2(src, dst)  # keeps mode/time
            src.unlink()

            fenced = f"```{EXTENSIONS[ext]}\n{text}\n```"
            dst.write_text(fenced, "utf-8")
            log(f"converted       {src} → {dst.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_cli() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Clone/sparsify (optional) and convert source files to fenced "
            "Markdown, respecting .gitignore."
        )
    )
    src_group = p.add_mutually_exclusive_group(required=True)
    src_group.add_argument("-d", "--directory", help="Local project directory")
    src_group.add_argument("-u", "--url", help="Git URL to sparse-clone")
    p.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory to include in sparse checkout (repeatable, default: backend & frontend/src)",
    )
    p.add_argument(
        "--ref",
        help="Branch, tag, or commit to checkout when cloning (default: repo default)",
    )
    p.add_argument(
        "-o",
        "--output",
        help="Destination directory (default: <source>_export)",
    )
    p.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into sub-directories",
    )
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    args = p.parse_args()

    includes = args.include or ["backend", "frontend/src"]

    work_dir = prepare_work_dir(
        args.directory or args.url,
        is_url=bool(args.url),
        includes=includes,
        ref=args.ref,
        output=args.output,
        log=logger.info,
    )
    if work_dir is None:
        sys.exit(1)

    rename_and_wrap(
        work_dir,
        recursive=args.recursive,
        dry_run=args.dry_run,
        log=logger.info,
    )


if __name__ == "__main__":
    run_cli()