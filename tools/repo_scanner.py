"""
Repository scanner for Open-Source Ghostwriter.

Scans a cloned repository's file tree and reads key source files to build
a context summary for the LLM when generating a README from scratch.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Directories to skip during scanning.
_IGNORE_DIRS: set[str] = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info", ".idea", ".vscode",
}

# Key project-metadata files to always read (if they exist).
_KEY_FILES: list[str] = [
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "requirements.txt",
    "Makefile",
    "package.json",
    "Cargo.toml",
    "go.mod",
]

# Extensions considered "source code" for reading.
_SOURCE_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".rb", ".c", ".cpp", ".h", ".cs",
}

# Limits to avoid blowing up LLM context.
_MAX_SOURCE_FILES: int = 10
_MAX_LINES_PER_FILE: int = 200
_MAX_TOTAL_CHARS: int = 30_000


def _should_ignore_dir(name: str) -> bool:
    """Check if a directory name should be skipped."""
    return name in _IGNORE_DIRS or name.startswith(".")


def _build_tree(repo_path: str) -> list[str]:
    """Walk the repo and build a visual file tree (relative paths)."""
    tree_lines: list[str] = []
    root = Path(repo_path)

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out ignored directories in-place so os.walk skips them.
        dirnames[:] = [
            d for d in sorted(dirnames) if not _should_ignore_dir(d)
        ]

        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts)

        for fname in sorted(filenames):
            indent = "│   " * depth
            tree_lines.append(f"{indent}├── {fname}")

    return tree_lines


def _read_file_safe(path: Path, max_lines: int = _MAX_LINES_PER_FILE) -> Optional[str]:
    """Read a file, returning at most *max_lines* lines. Returns None on error."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines])
            content += f"\n\n[... truncated, {len(lines) - max_lines} more lines ...]"
            return content
        return "\n".join(lines)
    except Exception:
        return None


def scan_repo(repo_path: str) -> str:
    """Scan a repository and produce a context summary for the LLM.

    The summary includes:
    1. A file/directory tree.
    2. Contents of key project-metadata files.
    3. Contents of up to ``_MAX_SOURCE_FILES`` source files.

    Args:
        repo_path: Absolute path to the cloned repository.

    Returns:
        A formatted string suitable for inclusion in an LLM prompt.
    """
    root = Path(repo_path)
    sections: list[str] = []
    total_chars = 0

    # ── 1. File tree ────────────────────────────────────────────────────
    tree_lines = _build_tree(repo_path)
    tree_section = "PROJECT STRUCTURE:\n" + "\n".join(tree_lines[:100])
    if len(tree_lines) > 100:
        tree_section += f"\n[... {len(tree_lines) - 100} more files ...]"
    sections.append(tree_section)
    total_chars += len(tree_section)

    # ── 2. Key metadata files ───────────────────────────────────────────
    key_contents: list[str] = []
    for fname in _KEY_FILES:
        fpath = root / fname
        if fpath.is_file():
            content = _read_file_safe(fpath, max_lines=50)
            if content:
                block = f"--- {fname} ---\n{content}\n--- END {fname} ---"
                key_contents.append(block)
                total_chars += len(block)

    if key_contents:
        sections.append("KEY PROJECT FILES:\n" + "\n\n".join(key_contents))

    # ── 3. Source files ─────────────────────────────────────────────────
    source_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in sorted(dirnames) if not _should_ignore_dir(d)
        ]
        for fname in sorted(filenames):
            if Path(fname).suffix in _SOURCE_EXTENSIONS:
                source_files.append(Path(dirpath) / fname)

    source_contents: list[str] = []
    files_read = 0

    for fpath in source_files:
        if files_read >= _MAX_SOURCE_FILES:
            break
        if total_chars >= _MAX_TOTAL_CHARS:
            break

        content = _read_file_safe(fpath)
        if content:
            rel = fpath.relative_to(root)
            block = f"--- {rel} ---\n{content}\n--- END {rel} ---"
            source_contents.append(block)
            total_chars += len(block)
            files_read += 1

    if source_contents:
        header = f"SOURCE FILES ({files_read}/{len(source_files)} files shown):\n"
        sections.append(header + "\n\n".join(source_contents))

    summary = "\n\n".join(sections)
    logger.info(
        "Repo scan complete: %d files in tree, %d source files read, %d chars total",
        len(tree_lines), files_read, len(summary),
    )
    return summary
