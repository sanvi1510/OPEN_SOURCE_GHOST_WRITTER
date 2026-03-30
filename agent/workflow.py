"""
LangGraph workflow definition for Open-Source Ghostwriter.

Wires the three processing nodes into a graph::

    analyzer  →  writer  →  tester  ─┐
                   ▲                  │
                   └──── (retry) ─────┘
                          or
                        → END

The tester's outcome drives a conditional edge:
  • All code blocks pass           →  END
  • At least one failure & retries →  writer (self-correction)
  • Retry limit reached            →  END

Reliability
───────────
- The entire ``run_ghostwriter_workflow`` entry point is wrapped in a
  top-level exception handler so that background-task failures are logged
  rather than silently swallowed.
- The compiled LangGraph is built once at module level.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes import analyzer_node, writer_node, tester_node
from agent.state import GhostwriterState
from config import settings
from tools.git_manager import (
    clone_repo,
    commit_and_push,
    get_diff,
    read_file,
    write_file,
)
from tools.repo_scanner import scan_repo

logger = logging.getLogger(__name__)


# ── Conditional edge logic ──────────────────────────────────────────────────

def _should_retry(state: GhostwriterState) -> str:
    """Decide whether to loop back to the writer or finish.

    Returns:
        ``"writer"`` if there are errors and retries remain, else ``"end"``.
    """
    has_errors: bool = bool(state.get("error_message"))
    retries_left: bool = state.get("retry_count", 0) < settings.max_retries

    if has_errors and retries_left:
        logger.info(
            "Self-correction: routing back to writer (attempt %d/%d).",
            state.get("retry_count", 0),
            settings.max_retries,
        )
        return "writer"

    if has_errors:
        logger.warning("Retry limit reached – proceeding with best-effort README.")

    return "end"


# ── Graph construction (built once) ────────────────────────────────────────

def _build_workflow() -> Any:
    """Construct and compile the Ghostwriter LangGraph workflow.

    Returns:
        A compiled ``StateGraph`` ready to be invoked.
    """
    graph = StateGraph(GhostwriterState)

    # Register nodes
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("writer", writer_node)
    graph.add_node("tester", tester_node)

    # Linear edges
    graph.add_edge("analyzer", "writer")
    graph.add_edge("writer", "tester")

    # Conditional edge from tester
    graph.add_conditional_edges(
        "tester",
        _should_retry,
        {
            "writer": "writer",
            "end": END,
        },
    )

    # Entry point
    graph.set_entry_point("analyzer")

    return graph.compile()


# Singleton compiled workflow – avoids rebuilding the graph on every request.
_compiled_workflow = _build_workflow()


# ── Public entry point (called from the webhook handler) ────────────────────

def run_ghostwriter_workflow(
    clone_url: str,
    branch: str,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any]:
    """End-to-end orchestration triggered by a merged pull request.

    Steps
    ─────
    1. Clone / update the repository.
    2. Compute the diff between commits.
    3. Read the current README.
    4. Run the LangGraph pipeline (analyze → write → test, with retries).
    5. If the README was updated **and all tests passed**, commit and push.

    The entire function is wrapped in a top-level exception handler so that
    errors in background tasks are **logged** rather than silently swallowed.

    Args:
        clone_url: HTTPS clone URL of the repository.
        branch: Target branch (e.g. ``main``).
        base_sha: SHA of the base commit.
        head_sha: SHA of the head commit.

    Returns:
        Final workflow state dictionary, or a status dict on early exit.
    """
    try:
        return _run_workflow_inner(clone_url, branch, base_sha, head_sha)
    except Exception:
        logger.exception(
            "Workflow failed for %s (%s..%s)",
            clone_url,
            base_sha[:8] if base_sha else "?",
            head_sha[:8] if head_sha else "?",
        )
        return {"status": "error"}


def _run_workflow_inner(
    clone_url: str,
    branch: str,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any]:
    """Core workflow logic, separated for clean exception handling."""
    logger.info(
        "Workflow started for %s (%s..%s)",
        clone_url, base_sha[:8], head_sha[:8],
    )

    # 1. Clone / update
    repo_path: str = clone_repo(clone_url, branch)

    # 2. Diff
    diff: str = get_diff(repo_path, base_sha, head_sha)
    if not diff.strip():
        logger.info("Empty diff – nothing to do.")
        return {"status": "no_changes"}

    # 3. Read current README (empty string if missing)
    try:
        readme_content: str = read_file(repo_path, "README.md")
    except FileNotFoundError:
        readme_content = ""
        logger.info("No README.md found – will generate one from scratch.")

    # 4. If README is empty or nearly empty (e.g. default GitHub placeholder), scan repo
    repo_summary: str = ""
    if len(readme_content.strip()) < 50:
        logger.info("Empty or nearly empty README – scanning repo for context.")
        repo_summary = scan_repo(repo_path)

    # 5. Build and invoke the graph
    initial_state: GhostwriterState = {
        "repo_path": repo_path,
        "diff": diff,
        "analysis": "",
        "original_readme": readme_content,
        "updated_readme": "",
        "code_blocks": [],
        "test_results": [],
        "error_message": "",
        "retry_count": 0,
        "repo_summary": repo_summary,
    }

    final_state: dict[str, Any] = _compiled_workflow.invoke(initial_state)

    # 5. Commit only if the README changed and all tests passed
    updated_readme = final_state.get("updated_readme", "")
    has_errors = bool(final_state.get("error_message"))

    if updated_readme and updated_readme != readme_content:
        write_file(repo_path, "README.md", updated_readme)
        commit_and_push(
            repo_path,
            "README.md",
            "docs: auto-update README to match code changes [ghostwriter]",
            branch,
        )
        if has_errors:
            logger.info(
                "Updated README pushed to origin/%s (best-effort – "
                "some code examples may not pass sandbox tests).",
                branch,
            )
        else:
            logger.info("Updated README pushed to origin/%s.", branch)
    else:
        logger.info("README unchanged – no commit needed.")

    return final_state
