"""
LLM prompt template for the **Writer** node.

The writer takes the analysis of code changes along with the current
README content and rewrites affected sections to keep the documentation
accurate.  An optional *error_feedback* section is included when the
tester found failures in a previous iteration.

When the README is empty or missing, a separate ``WRITER_INITIAL_README_PROMPT``
is used to generate a comprehensive README from scratch using the full repo context.
"""

WRITER_README_TEMPLATE: str = (
    "Use the following README section structure for all generated output:\n"
    "# <Project Title>\n"
    "## Description\n"
    "## Key Features\n"
    "## Architecture / Workflow\n"
    "## Installation\n"
    "## Configuration\n"
    "## Usage\n"
    "## API Reference\n"
    "## Examples\n"
    "## Testing\n"
    "## License\n"
    "If a section does not apply, omit it. Add the Examples section only when there are real screenshots, CLI examples, or UI examples to show.\n"
)

WRITER_SYSTEM_PROMPT: str = (
    "You are an expert technical writer.\n"
    "Your task is to update project documentation so it accurately reflects\n"
    "recent code changes.\n\n"
    "Rules:\n"
    "- Preserve the existing Markdown structure and formatting.\n"
    "- Update ONLY the sections affected by the code changes.\n"
    "- Fix outdated code examples so they compile and run.\n"
    "- Do NOT invent APIs, functions, or behaviours that do not exist.\n"
    "- Keep prose concise and developer-friendly.\n"
    "- Return the FULL, COMPLETE updated README content.\n"
    "- Ensure the README contains these core sections: Title, Description, Architecture/Workflow, Installation, Usage, Configuration, Testing, and License.\n"
    "- If the current README already has these sections, preserve the unmodified sections exactly.\n"
    "- Use the exact headings given in the README template when possible.\n"
    "- Do NOT output just a diff, and do NOT omit unmodified sections.\n"
    "- Do NOT wrap the output in markdown code fences.\n"
    f"{WRITER_README_TEMPLATE}"
)

WRITER_USER_PROMPT: str = (
    "Below is a structured analysis of recent code changes, the actual source code\n"
    "that was changed, and the current README.  Please return the updated README.\n\n"
    "--- CODE CHANGE ANALYSIS ---\n"
    "{analysis}\n"
    "--- END ANALYSIS ---\n\n"
    "--- RETRIEVED SOURCE CODE CONTEXT ---\n"
    "{retrieved_context}\n"
    "--- END SOURCE CODE CONTEXT ---\n\n"
    "--- CURRENT README ---\n"
    "{readme}\n"
    "--- END README ---"
)

WRITER_ERROR_FEEDBACK: str = (
    "\n\n⚠️  The documentation you produced in the previous attempt contained\n"
    "code examples that FAILED execution.  Here is the error output:\n\n"
    "--- ERROR OUTPUT ---\n"
    "{error_message}\n"
    "--- END ERROR OUTPUT ---\n\n"
    "Please fix the code examples so they run without errors."
)

# ── Initial README generation (empty/missing README) ───────────────────────

WRITER_INITIAL_SYSTEM_PROMPT: str = (
    "You are an expert technical writer.\n"
    "Your task is to generate a comprehensive README.md for a project from scratch.\n\n"
    "Rules:\n"
    "- Write a complete, professional README with proper Markdown formatting.\n"
    "- Use the following README section structure: project title, description, key features, architecture & workflow, installation, configuration, usage examples, API reference (if applicable), screenshots, testing, and license placeholder.\n"
    "- Code examples MUST be self-contained and runnable.\n"
    "  Define functions inline in the example rather than importing from project modules.\n"
    "  For instance, instead of `from calculator import add`, write:\n"
    "  ```python\n"
    "  def add(a, b):\n"
    "      return a + b\n"
    "  print(add(2, 3))  # Output: 5\n"
    "  ```\n"
    "- Do NOT invent features that don't exist in the source code.\n"
    "- Keep prose concise and developer-friendly.\n"
    "- Do NOT wrap the output in markdown code fences.\n"
    "- Return ONLY the README content.\n"
    f"{WRITER_README_TEMPLATE}"
)

WRITER_INITIAL_USER_PROMPT: str = (
    "Generate a comprehensive README.md for the following project.\n\n"
    "--- RECENT CODE CHANGES ---\n"
    "{diff}\n"
    "--- END CHANGES ---\n\n"
    "--- REPOSITORY CONTEXT ---\n"
    "{repo_summary}\n"
    "--- END CONTEXT ---"
)
