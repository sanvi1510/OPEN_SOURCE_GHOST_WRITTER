# Open-Source Ghostwriter
## Table of Contents
1. [Description](#description)
2. [Installation](#installation)
3. [Usage Examples](#usage-examples)
4. [API Reference](#api-reference)
5. [License](#license)

## Description
Open-Source Ghostwriter is an autonomous AI agent designed to detect and fix outdated documentation. It utilizes a LangGraph workflow to analyze code changes, rewrite documentation, and test the rewritten code.

## Installation
To install Open-Source Ghostwriter, follow these steps:
1. Clone the repository: `git clone https://github.com/your-repo/open-source-ghostwriter.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Set up the environment variables: create a `.env` file with the required settings (e.g., GitHub token, LLM API keys)

## Usage Examples
Here's an example of how to use Open-Source Ghostwriter:
```python
# Example usage of a simple Python function
def add(a, b):
    return a + b

result = add(2, 3)
print(result)  # Output: 5
```
Save this code in a file named `example.py`. Then, run it using `python example.py`. This will output `5`.

To trigger the Ghostwriter workflow, send a POST request to the `/webhook` endpoint with a valid GitHub webhook payload.

## API Reference
The Open-Source Ghostwriter API consists of a single endpoint:
* `/webhook`: receives GitHub webhook deliveries and triggers the documentation-update workflow

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

Note: The `ANALYZER_SYSTEM_PROMPT` has been updated to include 'in the repo' for signature precision. The updated prompt is:
```python
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
   
    "- Ignore formatting-only or whitespace changes.\n"
    "- Be precise about old vs. new signatures in the repo.\n"
    "- Return valid JSON only — no markdown fences, no commentary."
)
```