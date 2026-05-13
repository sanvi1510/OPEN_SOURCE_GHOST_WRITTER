# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It uses a combination of natural language processing (NLP) and machine learning (ML) to analyze code changes and update documentation accordingly.

## Key Features
* Analyzes git diffs to identify changes that could affect documentation
* Uses LLMs to produce structured JSON descriptions of code changes
* Updates README files to reflect code changes
* Tests updated README files using a Docker sandbox
* Supports multiple LLM providers, including Groq, Google, and Anthropic

## Architecture / Workflow
The workflow consists of the following nodes:
1. **Analyzer**: analyzes a git diff and produces a structured JSON description of code changes
2. **Retriever**: retrieves relevant source code chunks from the repository using RAG
3. **Writer**: rewrites the README to reflect code changes
4. **Tester**: extracts Python blocks, runs them in the sandbox, and records pass/fail status

The workflow is triggered by a merged pull request event and is designed to handle retries and errors.

## Installation
To install the project, run the following command:
```bash
pip install -r requirements.txt
```
## Configuration
The project uses a `.env` file to store configuration settings. The following settings are required:
* `GITHUB_WEBHOOK_SECRET`: secret used to validate GitHub webhook HMAC-SHA256 signatures
* `GITHUB_TOKEN`: personal access token (PAT) for GitHub API and git push
* `ANTHROPIC_API_KEY`: Anthropic API key (optional)
* `GOOGLE_API_KEY`: Google AI Studio API key (optional)
* `GROQ_API_KEY`: Groq API key (optional)

## Usage
To run the project, start the FastAPI app using the following command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
The app will listen for incoming GitHub webhook events and trigger the workflow accordingly.

## API Reference
The API consists of a single endpoint: `/webhook`. This endpoint accepts POST requests with a JSON payload containing the GitHub webhook event data.

## Screenshots
No screenshots are available for this project.

## Testing
To test the project, run the following command:
```bash
pytest
```
This will run the test suite and report any errors or failures.

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).