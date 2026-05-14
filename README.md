# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent designed to detect and fix outdated documentation in open-source projects. It leverages the power of large language models (LLMs) to analyze code changes, identify potential documentation updates, and generate high-quality documentation.

## Key Features
* Analyzes git diffs to identify changes that may affect documentation
* Uses LLMs to generate structured JSON descriptions of code changes
* Rewrites README files to reflect code changes
* Tests generated documentation using a Docker sandbox
* Supports multiple LLM providers, including Groq, Google, and Anthropic

## Architecture / Workflow
The Ghostwriter workflow consists of the following nodes:
1. **Analyzer**: Analyzes a git diff and produces a structured JSON description of the code changes.
2. **Retriever**: Retrieves relevant source code chunks from the repository using Retrieval-Augmented Generation (RAG).
3. **Writer**: Rewrites the README file to reflect the code changes.
4. **Tester**: Tests the generated documentation using a Docker sandbox.

The workflow is orchestrated by the LangGraph framework, which provides a flexible and scalable way to define and execute complex workflows.

## Installation
To install the Ghostwriter, follow these steps:
1. Clone the repository: `git clone https://github.com/your-repo/ghostwriter.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your LLM API keys and other configuration settings

## Configuration
The Ghostwriter can be configured using environment variables or a `.env` file. The following settings are available:
* `GITHUB_WEBHOOK_SECRET`: Secret used to validate GitHub webhook HMAC-SHA256 signatures
* `GITHUB_TOKEN`: Personal access token for GitHub API and git push
* `ANTHROPIC_API_KEY`: Anthropic API key
* `GOOGLE_API_KEY`: Google AI Studio API key for Gemini models
* `GROQ_API_KEY`: Groq API key for fast LLM inference
* `ANALYZER_PROVIDER`: LLM provider for the Analyzer node (e.g. groq, google, anthropic)
* `ANALYZER_MODEL`: Fast, cheap model for analyzing diffs
* `WRITER_PROVIDER`: LLM provider for the Writer node
* `WRITER_MODEL`: Advanced reasoning model for writing documentation

## Usage
To use the Ghostwriter, follow these steps:
1. Set up a GitHub webhook to trigger the Ghostwriter workflow on merged pull requests
2. Configure the Ghostwriter using environment variables or a `.env` file
3. Run the Ghostwriter using `uvicorn main:app --host 0.0.0.0 --port 8000`

## API Reference
The Ghostwriter provides a simple API for triggering the workflow:
* `POST /webhook`: Trigger the Ghostwriter workflow on a merged pull request

## Examples
Here is an example of how to use the Ghostwriter:
```python
import requests

# Set up a GitHub webhook to trigger the Ghostwriter workflow
webhook_url = "https://your-ghostwriter-instance.com/webhook"
github_repo = "https://github.com/your-repo/your-project"

# Trigger the Ghostwriter workflow on a merged pull request
response = requests.post(webhook_url, json={
    "action": "closed",
    "pull_request": {
        "merged": True,
        "base": {
            "ref": "main"
        },
        "head": {
            "ref": "feature/new-feature"
        }
    },
    "repository": {
        "clone_url": github_repo
    }
})

# Check the response
if response.status_code == 200:
    print("Ghostwriter workflow triggered successfully!")
else:
    print("Error triggering Ghostwriter workflow:", response.text)
```

## Testing
To test the Ghostwriter, follow these steps:
1. Run the Ghostwriter using `uvicorn main:app --host 0.0.0.0 --port 8000`
2. Use a tool like `curl` or a REST client to trigger the Ghostwriter workflow on a merged pull request
3. Verify that the Ghostwriter workflow completes successfully and generates high-quality documentation

## License
The Ghostwriter is licensed under the [MIT License](https://opensource.org/licenses/MIT).