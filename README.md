# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It uses a combination of natural language processing (NLP) and machine learning (ML) to analyze code changes and update documentation accordingly.

## Key Features
* Analyzes code changes and identifies areas that require documentation updates
* Uses NLP and ML to generate high-quality documentation
* Integrates with GitHub webhooks to automate the documentation update process
* Supports multiple LLM providers, including Groq, Google, and Anthropic

## Architecture / Workflow
The Open-Source Ghostwriter workflow consists of the following nodes:
1. **Analyzer**: analyzes a git diff and produces a structured JSON description of the code changes that could affect documentation.
2. **Retriever**: retrieves relevant source code chunks from the repository using Retrieval-Augmented Generation (RAG).
3. **Writer**: rewrites the README to reflect the code changes.
4. **Tester**: extracts Python blocks, runs them in a sandbox, and records pass/fail status.

## Installation
To install Open-Source Ghostwriter, run the following commands:
```bash
pip install -r requirements.txt
```
Note: Make sure to replace `requirements.txt` with the actual path to your requirements file.

## Configuration
Open-Source Ghostwriter uses environment variables to configure the application. The following variables are required:
* `GITHUB_WEBHOOK_SECRET`: secret used to validate GitHub webhook HMAC-SHA256 signatures
* `GITHUB_TOKEN`: personal access token (PAT) for GitHub API & git push
* `ANTHROPIC_API_KEY`: Anthropic API key (optional)
* `GOOGLE_API_KEY`: Google AI Studio API key (optional)
* `GROQ_API_KEY`: Groq API key (optional)

## Usage
To use Open-Source Ghostwriter, simply push code changes to your GitHub repository. The application will automatically analyze the changes and update the documentation accordingly.

## API Reference
The Open-Source Ghostwriter API is not publicly available. However, the application uses the following endpoints:
* `/webhook`: receives GitHub webhook deliveries and triggers the documentation update workflow

## Examples
To test Open-Source Ghostwriter, you can use the following example:
```python
import os

# Set environment variables
os.environ["GITHUB_WEBHOOK_SECRET"] = "your_secret_here"
os.environ["GITHUB_TOKEN"] = "your_token_here"

# Run the application
if __name__ == "__main__":
    import uvicorn
    from app.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000)
```
Note: Make sure to replace `your_secret_here` and `your_token_here` with your actual GitHub webhook secret and token.

## Testing
To test Open-Source Ghostwriter, you can use the following commands:
```bash
pytest
```
Note: Make sure to install the required dependencies using `pip install -r requirements.txt` before running the tests.

## License
Open-Source Ghostwriter is licensed under the [MIT License](https://opensource.org/licenses/MIT).