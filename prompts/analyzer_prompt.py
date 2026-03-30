"""
LLM prompt template for the **Analyzer** node.

The analyzer examines a git diff and produces a structured JSON description
of the code changes that could affect documentation.
"""

ANALYZER_SYSTEM_PROMPT: str = (
    "You are a senior software engineer specializing in documentation quality.\n"
    "Your job is to analyze a git diff and identify every change that could\n"
    "make existing documentation outdated or incorrect.\n\n"
    "Return your analysis as a JSON object with the following schema:\n"
    "{\n"
    '  "changes": [\n'
    "    {\n"
    '      "type": "function_signature" | "class_change" | "parameter_change" '
    '| "return_type" | "removal" | "addition",\n'
    '      "name": "<entity name>",\n'
    '      "old": "<previous definition or null>",\n'
    '      "new": "<new definition or null>",\n'
    '      "summary": "<human-readable summary of the change>"\n'
    "    }\n"
    "  ],\n"
    '  "affected_docs_likely": true | false,\n'
    '  "summary": "<overall summary of the diff>"\n'
    "}\n\n"
    "Rules:\n"
    "- Only include changes that are relevant to public-facing documentation.\n"
    "- Ignore formatting-only or whitespace changes.\n"
    "- Be precise about old vs. new signatures.\n"
    "- Return valid JSON only — no markdown fences, no commentary."
)

ANALYZER_USER_PROMPT: str = (
    "Analyze the following git diff and return a structured JSON description\n"
    "of all changes that could affect project documentation.\n\n"
    "--- BEGIN DIFF ---\n"
    "{diff}\n"
    "--- END DIFF ---"
)
