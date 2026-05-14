# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It uses a LangGraph workflow to analyze code changes, rewrite the README, and test the updated documentation.

## Key Features
* Analyzes code changes using a Large Language Model (LLM)
* Rewrites the README to reflect the code changes
* Tests the updated documentation using a Docker sandbox
* Supports multiple LLM providers (Groq, Google, Anthropic)
* Configurable using environment variables

## Architecture / Workflow
The workflow consists of the following nodes:
1. **Analyzer**: analyzes a git diff and produces a structured JSON description of the code changes.
2. **Retriever**: retrieves relevant source code chunks from the repository using Retrieval-Augmented Generation (RAG).
3. **Writer**: rewrites the README to reflect the code changes.
4. **Tester**: tests the updated documentation using a Docker sandbox.

The workflow is triggered by a GitHub webhook endpoint, which validates the HMAC signature, de-duplicates deliveries, and kicks off the workflow as a background task.

## Installation
To install the project, run the following command:
```bash
pip install -r requirements.txt
```
## Configuration
The project uses environment variables for configuration. Create a `.env` file with the following variables:
* `GITHUB_WEBHOOK_SECRET`: secret used to validate GitHub webhook HMAC-SHA256 signatures
* `GITHUB_TOKEN`: personal access token for GitHub API & git push
* `ANTHROPIC_API_KEY`: Anthropic API key (optional)
* `GOOGLE_API_KEY`: Google AI Studio API key (optional)
* `GROQ_API_KEY`: Groq API key (optional)
* `ANALYZER_PROVIDER`: LLM provider for the Analyzer node (e.g. groq, google, anthropic)
* `ANALYZER_MODEL`: model for the Analyzer node (e.g. llama-3.1-8b-instant)
* `WRITER_PROVIDER`: LLM provider for the Writer node (e.g. groq, google, anthropic)
* `WRITER_MODEL`: model for the Writer node (e.g. llama-3.3-70b-versatile)
* `CLONE_DIR`: local directory used for cloning repositories
* `DOCKER_IMAGE`: Docker image name for the code-execution sandbox
* `MAX_RETRIES`: maximum number of writer ↔ tester retry cycles
* `MAX_DIFF_CHARS`: maximum diff size (in characters) forwarded to the LLM
* `LLM_REQUEST_TIMEOUT`: timeout in seconds for a single LLM API request

## Usage
To run the project, start the FastAPI app:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
The app will listen for incoming GitHub webhook deliveries on port 8000.

## API Reference
The project exposes a single endpoint:
* `POST /webhook`: receives and processes a GitHub webhook delivery

## Examples
To test the project, create a GitHub repository and add a webhook with the following settings:
* Payload URL: `http://localhost:8000/webhook`
* Content type: `application/json`
* Events: `pull_request`

Merge a pull request to trigger the workflow. The project will analyze the code changes, rewrite the README, and test the updated documentation.

## Testing
To run the tests, use the following command:
```bash
pytest
```
## License
MIT License

Note: This is a placeholder for the license. Please replace with the actual license used by the project.