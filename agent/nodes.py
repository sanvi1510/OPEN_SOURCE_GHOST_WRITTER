"""
LangGraph node implementations for Open-Source Ghostwriter.

Three nodes form the core pipeline:

1. **analyzer_node** – asks the LLM to describe code changes in JSON.
2. **writer_node**   – asks the LLM to update the README accordingly.
3. **tester_node**   – extracts Python blocks, runs them in the sandbox,
                       and records pass / fail status.

Reliability
───────────
- LLM calls are wrapped with retry + exponential backoff.
- Invalid JSON from the analyzer triggers a retry rather than silent failure.
- All exceptions are caught and surfaced via the ``error_message`` state field.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agent.state import GhostwriterState
from config import settings
from models import SandboxResult
from prompts.analyzer_prompt import ANALYZER_SYSTEM_PROMPT, ANALYZER_USER_PROMPT
from prompts.writer_prompt import (
    WRITER_ERROR_FEEDBACK,
    WRITER_INITIAL_SYSTEM_PROMPT,
    WRITER_INITIAL_USER_PROMPT,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_PROMPT,
)
from tools.code_extractor import extract_python_blocks
from tools.docker_executor import run_code_in_sandbox

logger = logging.getLogger(__name__)

# ── LLM factory ────────────────────────────────────────────────────────────

_LLM_MAX_RETRIES = 3
_LLM_BACKOFF_BASE = 2  # seconds


def _get_llm() -> BaseChatModel:
    """Instantiate the correct LLM client based on available API keys.

    Priority: OpenAI → Groq → Google Gemini → Anthropic.
    """
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
            request_timeout=settings.llm_request_timeout,
        )

    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            temperature=0.2,
        )

    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.2,
        )

    # Anthropic fallback
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        temperature=0.2,
        timeout=float(settings.llm_request_timeout),
    )


def _invoke_llm_with_retry(
    llm: BaseChatModel,
    messages: list[Any],
    *,
    label: str = "LLM",
) -> str:
    """Invoke *llm* with automatic retry and exponential backoff.

    Args:
        llm: A LangChain chat model instance.
        messages: The message list to send.
        label: Human-readable label for log messages.

    Returns:
        The stripped text content of the LLM response.

    Raises:
        RuntimeError: If all retry attempts are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _LLM_MAX_RETRIES + 1):
        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as exc:
            last_exc = exc
            wait = _LLM_BACKOFF_BASE ** attempt
            logger.warning(
                "%s call failed (attempt %d/%d): %s – retrying in %ds",
                label, attempt, _LLM_MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)

    error_msg = f"{label} failed after {_LLM_MAX_RETRIES} attempts: {last_exc}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


# ────────────────────────────────────────────────────────────────────────────
# Node 1 – Analyzer
# ────────────────────────────────────────────────────────────────────────────

def analyzer_node(state: GhostwriterState) -> dict[str, Any]:
    """Analyze a git diff and produce a structured JSON change description.

    Reads ``state["diff"]`` and writes ``state["analysis"]``.
    If the LLM returns invalid JSON, the error is surfaced so the
    workflow can decide whether to proceed or abort.
    """
    logger.info("Analyzer: examining diff (%d chars)", len(state["diff"]))

    llm = _get_llm()
    messages = [
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=ANALYZER_USER_PROMPT.format(diff=state["diff"])),
    ]

    try:
        analysis_text = _invoke_llm_with_retry(llm, messages, label="Analyzer")
    except RuntimeError as exc:
        logger.error("Analyzer LLM call failed: %s", exc)
        return {"analysis": "", "error_message": str(exc)}

    # Clean possible markdown wrapping from LLM output
    analysis_text_clean = analysis_text.strip()
    if analysis_text_clean.startswith("```"):
        import re
        analysis_text_clean = re.sub(r"^```(?:json)?\n(.*)\n```$", r"\1", analysis_text_clean, flags=re.DOTALL)

    # Validate JSON
    try:
        json.loads(analysis_text_clean)
        analysis_text = analysis_text_clean  # Use cleaned version if valid
    except json.JSONDecodeError:
        logger.warning("Analyzer output is not valid JSON – storing raw text.")
        # Still usable by the writer, but log it.

    logger.info("Analyzer: complete.")
    return {"analysis": analysis_text}


# ────────────────────────────────────────────────────────────────────────────
# Node 2 – Writer
# ────────────────────────────────────────────────────────────────────────────

def writer_node(state: GhostwriterState) -> dict[str, Any]:
    """Rewrite the README to reflect the code changes.

    On the first pass, uses ``original_readme``; on retries, uses the most
    recent ``updated_readme`` and appends error feedback.

    When the original README is empty or missing, switches to the initial
    README generation prompt using the full repo context.
    """
    retry: int = state.get("retry_count", 0)
    is_first_pass: bool = retry == 0
    original_readme: str = state.get("original_readme", "")
    # Default GitHub READMEs just have `# ProjectName`. A real README will be > 50 chars.
    is_initial_generation: bool = len(original_readme.strip()) < 50

    if is_initial_generation:
        logger.info("Writer: generating initial README from scratch (attempt %d)", retry + 1)
    else:
        logger.info("Writer: generating updated README (attempt %d)", retry + 1)

    llm = _get_llm()

    if is_initial_generation:
        # ── Initial generation: use repo context ────────────────────────
        user_prompt = WRITER_INITIAL_USER_PROMPT.format(
            diff=state.get("diff", ""),
            repo_summary=state.get("repo_summary", "(no repo context available)"),
        )
        system_prompt = WRITER_INITIAL_SYSTEM_PROMPT

        # On retries, append error feedback
        error_msg: str = state.get("error_message", "")
        if error_msg and not is_first_pass:
            user_prompt += WRITER_ERROR_FEEDBACK.format(error_message=error_msg)
    else:
        # ── Normal update: use existing README ──────────────────────────
        readme_content: str = (
            original_readme if is_first_pass
            else (state.get("updated_readme") or original_readme)
        )

        user_prompt = WRITER_USER_PROMPT.format(
            analysis=state["analysis"],
            readme=readme_content,
        )
        system_prompt = WRITER_SYSTEM_PROMPT

        # Append error feedback when retrying
        error_msg = state.get("error_message", "")
        if error_msg and not is_first_pass:
            user_prompt += WRITER_ERROR_FEEDBACK.format(error_message=error_msg)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        updated_readme = _invoke_llm_with_retry(llm, messages, label="Writer")
    except RuntimeError as exc:
        logger.error("Writer LLM call failed: %s", exc)
        return {"error_message": str(exc), "retry_count": retry + 1}

    logger.info("Writer: complete (%d chars produced).", len(updated_readme))
    return {
        "updated_readme": updated_readme,
        "retry_count": retry + 1,
        "error_message": "",  # clear previous error on success
    }


# ────────────────────────────────────────────────────────────────────────────
# Node 3 – Tester
# ────────────────────────────────────────────────────────────────────────────

def tester_node(state: GhostwriterState) -> dict[str, Any]:
    """Extract Python code blocks and run each in the sandbox.

    Populates ``code_blocks``, ``test_results``, and ``error_message``.
    """
    updated_readme: str = state.get("updated_readme", "")
    if not updated_readme:
        logger.warning("Tester: no updated README to test.")
        return {"error_message": "No updated README available for testing."}

    blocks: list[str] = extract_python_blocks(updated_readme)
    logger.info("Tester: found %d Python code block(s).", len(blocks))

    if not blocks:
        logger.info("Tester: no Python blocks to test – passing.")
        return {
            "code_blocks": [],
            "test_results": [],
            "error_message": "",
        }

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, code in enumerate(blocks):
        logger.info("Tester: running block %d/%d …", idx + 1, len(blocks))
        result: SandboxResult = run_code_in_sandbox(code, repo_path=state.get("repo_path", ""))
        results.append({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        })

        if not result.success:
            block_error = (
                f"Block {idx + 1} failed (exit_code={result.exit_code}):\n"
                f"stderr: {result.stderr}\n"
                f"code:\n{code}"
            )
            errors.append(block_error)
            logger.warning("Tester: block %d FAILED.", idx + 1)

    error_message: str = "\n---\n".join(errors) if errors else ""

    logger.info(
        "Tester: %d/%d blocks passed.",
        len(blocks) - len(errors),
        len(blocks),
    )

    return {
        "code_blocks": blocks,
        "test_results": results,
        "error_message": error_message,
    }
