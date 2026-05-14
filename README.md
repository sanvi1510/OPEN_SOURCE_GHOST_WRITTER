# Open-Source Ghostwriter
## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It uses a combination of natural language processing (NLP) and machine learning (ML) to analyze code changes and update documentation accordingly.

## Key Features
* Analyzes code changes using a large language model (LLM)
* Updates documentation based on the analysis
* Uses a retrieval-augmented generation (RAG) approach to improve the accuracy of the analysis
* Supports multiple LLM providers, including Groq, Google, and Anthropic
* Provides a webhook endpoint for receiving GitHub pull request events

## Architecture / Workflow
The Ghostwriter workflow consists of the following steps:
1. Clone the repository and compute the diff between the base and head commits.
2. Analyze the diff using an LLM and produce a structured JSON description of the changes.
3. Use the analysis to update the README file.
4. Test the updated README file using a sandbox environment.
5. If the tests pass, commit and push the updated README file.

## Installation
To install the Ghostwriter, follow these steps:
1. Clone the repository using `git clone https://github.com/user/repo.git`.
2. Install the required dependencies using `pip install -r requirements.txt`.
3. Create a `.env` file with the required environment variables, including `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, and `GROQ_API_KEY`.

## Configuration
The Ghostwriter can be configured using environment variables. The following variables are supported:
* `GITHUB_WEBHOOK_SECRET`: The secret used to validate GitHub webhook HMAC-SHA256 signatures.
* `GITHUB_TOKEN`: The personal access token (PAT) for the GitHub API and git push.
* `ANTHROPIC_API_KEY`: The Anthropic API key.
* `GOOGLE_API_KEY`: The Google AI Studio API key for Gemini models.
* `GROQ_API_KEY`: The Groq API key for fast LLM inference.
* `ANALYZER_PROVIDER`: The LLM provider for the analyzer node (e.g., Groq, Google, Anthropic).
* `ANALYZER_MODEL`: The model used for analyzing diffs.
* `WRITER_PROVIDER`: The LLM provider for the writer node.
* `WRITER_MODEL`: The model used for writing documentation.

## Usage
To use the Ghostwriter, send a GitHub pull request event to the webhook endpoint. The endpoint will analyze the diff and update the README file accordingly.

## API Reference
The Ghostwriter provides a single endpoint for receiving GitHub pull request events:
* `POST /webhook`: Receive a GitHub pull request event and trigger the Ghostwriter workflow.

## Examples
Here is an example of how to send a GitHub pull request event to the Ghostwriter webhook endpoint:
```python
import requests

def send_webhook_event():
    # Set up the GitHub webhook payload
    payload = {
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
            "clone_url": "https://github.com/user/repo.git"
        }
    }

    # Send the webhook payload to the Ghostwriter API
    response = requests.post("http://localhost:8000/webhook", json=payload)

    # Print the response
    print(response.json())

send_webhook_event()
```
Note: Make sure to replace `http://localhost:8000` with the actual URL of your Ghostwriter instance.

## Testing
To test the Ghostwriter, you can use the following example:
```python
import os
import unittest
from unittest.mock import patch
from ghostwriter.workflow import run_ghostwriter_workflow

class TestGhostwriterWorkflow(unittest.TestCase):
    @patch("ghostwriter.workflow.clone_repo")
    @patch("ghostwriter.workflow.get_diff")
    @patch("ghostwriter.workflow.read_file")
    def test_workflow(self, mock_read_file, mock_get_diff, mock_clone_repo):
        # Set up the mock responses
        mock_clone_repo.return_value = "/path/to/repo"
        mock_get_diff.return_value = "diff"
        mock_read_file.return_value = "README content"

        # Run the workflow
        result = run_ghostwriter_workflow("https://github.com/user/repo.git", "main", "base_sha", "head_sha")

        # Assert the result
        self.assertEqual(result["status"], "ok")

if __name__ == "__main__":
    unittest.main()
```
Note: Make sure to replace `ghostwriter.workflow` with the actual module name of your Ghostwriter instance.

## License
The Ghostwriter is licensed under the [MIT License](https://opensource.org/licenses/MIT).