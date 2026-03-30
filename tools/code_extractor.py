"""
Code block extractor for Open-Source Ghostwriter.

Extracts fenced Python code blocks from Markdown text so they can be
executed in the sandbox for validation.
"""

from __future__ import annotations

import re


# Matches ```python, ```py, or ```python3 fenced blocks.
# The negative lookahead (?!\\S) ensures we don't accidentally match
# languages that *start* with "py" (e.g. ``pyarrow``).
_PYTHON_BLOCK_RE = re.compile(
    r"```(?:python3?|py)(?!\S)\s*\n(.*?)```",
    re.DOTALL,
)


def extract_python_blocks(markdown: str) -> list[str]:
    """Return all Python fenced code blocks found in *markdown*.

    Captured block types: ``python``, ``python3``, ``py``.
    The returned strings contain just the code (no fence markers).

    Args:
        markdown: Raw Markdown text.

    Returns:
        List of Python code snippets (may be empty).
    """
    return [match.strip() for match in _PYTHON_BLOCK_RE.findall(markdown)]
