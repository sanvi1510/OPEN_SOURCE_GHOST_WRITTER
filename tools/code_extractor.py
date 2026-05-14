"""
Code block extractor for Open-Source Ghostwriter.

Extracts fenced Python code blocks from Markdown text so they can be
executed in the sandbox for validation.
"""

from __future__ import annotations

import re
from typing import TypedDict


class CodeBlock(TypedDict):
    language: str
    code: str


_LANGUAGE_ALIASES: dict[str, str] = {
    "python": "python",
    "python3": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "node": "javascript",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "ruby": "ruby",
    "rb": "ruby",
    "go": "go",
    "golang": "go",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "rust": "rust",
    "php": "php",
    "kotlin": "kotlin",
    "scala": "scala",
    "csharp": "csharp",
    "c#": "csharp",
}

_CODE_BLOCK_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)


def _normalize_language(tag: str) -> str:
    tag = tag.strip().lower()
    return _LANGUAGE_ALIASES.get(tag, tag or "python")


def extract_code_blocks(markdown: str) -> list[CodeBlock]:
    """Return all fenced code blocks with language metadata."""
    blocks: list[CodeBlock] = []
    for tag, code in _CODE_BLOCK_RE.findall(markdown):
        language = _normalize_language(tag or "python")
        blocks.append({"language": language, "code": code.strip()})
    return blocks


def extract_python_blocks(markdown: str) -> list[str]:
    """Backward-compatible helper for Python-only extraction."""
    return [
        block["code"]
        for block in extract_code_blocks(markdown)
        if block["language"] == "python"
    ]
