"""
LangGraph workflow state definition.

Defines the ``GhostwriterState`` TypedDict that flows through every node
in the documentation-update graph.
"""

from __future__ import annotations

from typing import Any, TypedDict


class GhostwriterState(TypedDict, total=False):
    """State carried across the LangGraph workflow.

    Attributes:
        repo_path:        Local filesystem path to the cloned repository.
        diff:             Unified diff between base and head commits.
        analysis:         JSON string produced by the analyzer LLM.
        original_readme:  Original README content before modification.
        updated_readme:   README content after the writer LLM rewrites it.
        code_blocks:      Python code snippets extracted from the updated README.
        test_results:     List of per-block execution results from the sandbox.
        error_message:    Concatenated error output when code blocks fail.
        retry_count:      Number of writer ↔ tester iterations so far.
        repo_summary:     Scanned repository context for initial README generation.
    """

    repo_path: str
    diff: str
    analysis: str
    original_readme: str
    updated_readme: str
    code_blocks: list[str]
    test_results: list[dict[str, Any]]
    error_message: str
    retry_count: int
    repo_summary: str
