#!/usr/bin/env python
"""
rename_to_md.py

Rename source files to `.md`, wrap their contents in Markdown code-fences,
and obey every `.gitignore` rule in the repository tree.

Supported extensions  →  language tags:

    .py        python
    .ts/.tsx   typescript
    .js/.cjs   javascript
    .jsx       jsx
    .json      json
    .html      html
    .css       css
    .log       text
    .txt       text
    .ini       ini
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List

# ---------------------------------------------------------------------------
# Optional dependency: pathspec for full Git-style ignore handling
# ---------------------------------------------------------------------------

try:
    import pathspec  # type: ignore
    _HAS_PATHSPEC = True
except ModuleNotFoundError:  # pragma: no cover
    _HAS_PATHSPEC = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".cjs": "javascript",
    ".jsx": "jsx",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".log": "text",
    ".txt": "text",
    ".ini": "ini",
}


# ---------------------------------------------------------------------------
# .gitignore helpers
# ---------------------------------------------------------------------------

def _collect_gitignore_patterns(root: Path) -> List[str]:
    """Return every ignore line from all `.gitignore` files under *root*."""
    patterns: List[str] = []
    for gitignore in root.rglob(".gitignore"):
        try:
            patterns.extend(
                line.rstrip("\n") for line in gitignore.read_text(encoding="utf-8").splitlines()
                if line and not line.lstrip().startswith("#")
            )
        except Exception:  # pragma: no cover
            continue
    return patterns


if _HAS_PATHSPEC:
    def build_ignore_spec(root: Path):
        patterns = _collect_gitignore_patterns(root)
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
else:
    import fnmatch

    def build_ignore_spec(root: Path):
        """Minimal fallback ignoring – covers only simple wildcard lines."""
        patterns = _collect_gitignore_patterns(root)

        def _matches(path: Path) -> bool:
            s = str(path)
            b = path.name
            return any(fnmatch.fnmatch(s, p) or fnmatch.fnmatch(b, p) for p in patterns)

        return _matches


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def rename_and_wrap(
    directory: str | Path,
    *,
    recursive: bool,
    dry_run: bool,
    log: Callable[[str], None],
) -> None:
    """Rename & wrap all supported files in *directory*."""
    root = Path(directory).resolve()
    if not root.is_dir():
        log(f"Error: '{root}' is not a directory.")
        return

    ignore_spec = build_ignore_spec(root)

    def is_ignored(path: Path) -> bool:
        if _HAS_PATHSPEC:
            # pathspec expects paths relative to the root
            try:
                rel = path.relative_to(root)
            except ValueError:  # pragma: no cover
                return False
            return ignore_spec.match_file(str(rel))
        else:  # fallback callable
            return ignore_spec(path)

    walker = os.walk(root) if recursive else [(root, [], os.listdir(root))]
    for curr_root, dirs, files in walker:
        curr_root_path = Path(curr_root)

        # Prune ignored directories
        dirs[:] = [d for d in dirs if not is_ignored(curr_root_path / d)]

        for fname in files:
            src = curr_root_path / fname
            if is_ignored(src):
                log(f"Skipping '{src}' (ignored by .gitignore).")
                continue

            ext = src.suffix.lower()
            if ext not in EXTENSIONS:
                continue

            dst = src.with_suffix(".md")
            if dst.exists():
                log(f"Skipping '{src}' → '{dst.name}' already exists.")
                continue

            if dry_run:
                log(f"[DRY-RUN] Would rename '{src}' → '{dst}' and wrap contents.")
                continue

            # --- Rename then wrap ------------------------------------------
            src.rename(dst)
            log(f"Renamed '{src}' → '{dst}'")

            try:
                original_text = dst.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        original_text = dst.read_text(encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, read as binary and decode with error handling
                    original_text = dst.read_bytes().decode('utf-8', errors='replace')
            language = EXTENSIONS[ext]
            fenced = f"```{language}\n{original_text}\n```"

            dst.write_text(fenced, encoding="utf-8")
            log(f"Wrapped contents of '{dst}' in ```{language}``` fence.")


# ---------------------------------------------------------------------------
# GitHub cloning & directory-copy helpers
# ---------------------------------------------------------------------------

def clone_repo(url: str, dest: Path, log: Callable[[str], None]) -> bool:
    """Clone with GitHub CLI (`gh repo clone`)."""
    try:
        subprocess.run(["gh", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        log("Error: GitHub CLI ('gh') not found.")
        return False

    log(f"Cloning '{url}' → '{dest}' …")
    try:
        subprocess.run(["gh", "repo", "clone", url, str(dest)], check=True)
        return True
    except subprocess.CalledProcessError as exc:
        log(f"Clone failed: {exc}")
        return False


def prepare_work_dir(
    source: str,
    *,
    is_url: bool,
    output: str | None,
    log: Callable[[str], None],
) -> Path | None:
    """Return a working directory ready for renaming."""
    if is_url:
        tmp = Path(tempfile.mkdtemp())
        if not clone_repo(source, tmp, log):
            return None
        src_dir = tmp
    else:
        src_dir = Path(source).expanduser().resolve()
        if not src_dir.is_dir():
            log(f"Error: '{src_dir}' is not a directory.")
            return None

    out_dir = Path(output).expanduser().resolve() if output else src_dir.parent / f"{src_dir.name}_renamed"
    if out_dir.exists():
        log(f"Removing existing '{out_dir}'.")
        shutil.rmtree(out_dir)

    shutil.copytree(src_dir, out_dir)
    log(f"Copied working tree → '{out_dir}'.")
    return out_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_cli() -> None:
    p = argparse.ArgumentParser(
        description="Rename supported files to .md, wrap them in Markdown fences, "
                    "and fully respect all .gitignore rules."
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("-d", "--directory", help="Local directory to process")
    src.add_argument("-u", "--url", help="GitHub repository URL to clone and process")
    p.add_argument("-o", "--output", help="Destination directory (default: <source>_renamed)")
    p.add_argument("-r", "--recursive", action="store_true", help="Process sub-directories recursively")
    p.add_argument("--dry-run", action="store_true", help="Show actions without modifying anything")

    args = p.parse_args()
    log: Callable[[str], None] = print

    work_dir = prepare_work_dir(
        args.directory or args.url,
        is_url=bool(args.url),
        output=args.output,
        log=log,
    )
    if work_dir is None:
        sys.exit(1)

    rename_and_wrap(
        work_dir,
        recursive=args.recursive,
        dry_run=args.dry_run,
        log=log,
    )


if __name__ == "__main__":
    run_cli()
