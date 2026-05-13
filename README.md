# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent designed to detect and fix outdated documentation in software projects. It utilizes a combination of natural language processing (NLP) and machine learning (ML) to analyze code changes and update corresponding documentation.

## Key Features
* Analyzes git diffs to identify changes that may affect documentation
* Utilizes LLMs (Large Language Models) to generate high-quality documentation updates
* Supports multiple LLM providers, including Groq, Google, and Anthropic
* Includes a retry mechanism to handle LLM call failures and ensure reliable documentation updates
* Supports a variety of programming languages and documentation formats

## Architecture / Workflow
The Open-Source Ghostwriter workflow consists of the following nodes:
1. **Analyzer Node**: Analyzes a git diff and produces a structured JSON description of the code changes that could affect documentation.
2. **Retriever Node**: Retrieves relevant source code chunks from the repository using RAG (Retrieval-Augmented Generation).
3. **Writer Node**: Rewrites the README to reflect the code changes.
4. **Tester Node**: Extracts Python blocks, runs them in a sandbox, and records pass/fail status.

## Installation
To install Open-Source Ghostwriter, follow these steps:
1. Clone the repository: `git clone https://github.com/your-repo/ghostwriter.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables: `cp .env.example .env` and update the `.env` file with your LLM API keys and other settings

## Configuration
Configure Open-Source Ghostwriter by updating the `.env` file with your LLM API keys, GitHub webhook secret, and other settings.

## Usage
To use Open-Source Ghostwriter, follow these steps:
1. Set up a GitHub webhook to trigger the workflow on merged pull requests.
2. Configure the workflow to use your preferred LLM provider and model.
3. Test the workflow by merging a pull request with code changes that affect documentation.

## API Reference
The Open-Source Ghostwriter API is not publicly exposed. However, the `run_ghostwriter_workflow` function can be called programmatically to trigger the workflow.

## Examples
```python
def test_ghostwriter_workflow():
    clone_url = "https://github.com/your-repo/your-project.git"
    branch = "main"
    base_sha = "abc123"
    head_sha = "def456"

    result = run_ghostwriter_workflow(clone_url, branch, base_sha, head_sha)
    print(result)

test_ghostwriter_workflow()
```

## Testing
To test Open-Source Ghostwriter, run the following command: `pytest`

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).