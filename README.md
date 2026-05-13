# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It uses a combination of natural language processing (NLP) and machine learning (ML) to analyze code changes and update documentation accordingly.

## Key Features
* Analyzes git diffs to identify changes that affect documentation
* Uses LLMs to generate structured JSON descriptions of code changes
* Updates README files to reflect code changes
* Uses a Docker sandbox to execute Python code blocks and test documentation
* Supports multiple LLM providers, including Groq, Google, and Anthropic

## Architecture / Workflow
The workflow consists of the following nodes:
1. **Analyzer**: analyzes a git diff and produces a structured JSON description of the code changes
2. **Retriever**: retrieves relevant source code chunks from the repository using RAG
3. **Writer**: rewrites the README to reflect the code changes
4. **Tester**: extracts Python blocks, runs them in the sandbox, and records pass/fail status

The workflow is triggered by a GitHub webhook endpoint, which validates the HMAC-SHA256 signature and parses the incoming JSON payload.

## Installation
To install the project, run the following command:
```bash
pip install -r requirements.txt
```
You will also need to build the Docker image for the sandbox:
```bash
docker build -t ghostwriter-sandbox sandbox/
```
## Configuration
The project uses a `.env` file to store configuration settings. You can create a `.env` file with the following settings:
```makefile
GITHUB_WEBHOOK_SECRET=your_secret_here
GITHUB_TOKEN=your_token_here
ANTHROPIC_API_KEY=your_api_key_here
GOOGLE_API_KEY=your_api_key_here
GROQ_API_KEY=your_api_key_here
CLONE_DIR=/tmp/ghostwriter_repos
DOCKER_IMAGE=ghostwriter-sandbox
MAX_RETRIES=3
MAX_DIFF_CHARS=50000
LLM_REQUEST_TIMEOUT=120
```
Replace the `your_secret_here` placeholders with your actual secrets and API keys.

## Usage
To run the project, start the FastAPI app:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
You can then trigger the workflow by sending a GitHub webhook payload to the `/webhook` endpoint.

## API Reference
The project exposes a single endpoint: `/webhook`. This endpoint accepts a GitHub webhook payload and triggers the workflow.

## Examples
Here is an example of a GitHub webhook payload:
```json
{
  "action": "closed",
  "pull_request": {
    "merged": true,
    "base": {
      "ref": "main",
      "sha": "base_sha"
    },
    "head": {
      "ref": "feature/branch",
      "sha": "head_sha"
    }
  },
  "repository": {
    "clone_url": "https://github.com/your/repo.git"
  }
}
```
You can send this payload to the `/webhook` endpoint using a tool like `curl`:
```bash
curl -X POST \
  http://localhost:8000/webhook \
  -H 'Content-Type: application/json' \
  -H 'X-Hub-Signature-256: your_signature_here' \
  -d '{"action": "closed", "pull_request": {"merged": true, "base": {"ref": "main", "sha": "base_sha"}, "head": {"ref": "feature/branch", "sha": "head_sha"}}, "repository": {"clone_url": "https://github.com/your/repo.git"}}'
```
Replace the `your_signature_here` placeholder with your actual HMAC-SHA256 signature.

## Testing
To test the project, you can use the `pytest` framework. The project includes a set of test cases that cover the workflow and individual nodes.

## License
This project is licensed under the MIT License.