# Open-Source Ghostwriter
==========================

## Description
Open-Source Ghostwriter is an autonomous AI agent that detects and fixes outdated documentation. It analyzes code changes, updates the README, and tests the code examples to ensure they are accurate and run without errors.

## Installation
To install the project, run the following command:
```bash
pip install -r requirements.txt
```
This will install all the required dependencies, including FastAPI, Uvicorn, GitPython, Docker, and LangChain.

## Usage Examples
To test the project, you can use the following example:

```python
def add(a, b):
    return a + b
print(add(2, 3))  # Output: 5
```
This code defines a simple `add` function and prints the result of adding 2 and 3.

To run the Ghostwriter workflow, you can use the following command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
This will start the FastAPI server and make the webhook endpoint available at `http://localhost:8000/webhook`.

## API Reference
The API has a single endpoint: `POST /webhook`. This endpoint accepts a JSON payload with the following structure:
```json
{
    "action": "closed",
    "pull_request": {
        "merged": true,
        "base": {"ref": "main"},
        "head": {"ref": "feature/new-feature"}
    },
    "repository": {
        "clone_url": "https://github.com/your-username/your-repo.git"
    }
}
```
This payload triggers the Ghostwriter workflow, which analyzes the code changes, updates the README, and tests the code examples.

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).