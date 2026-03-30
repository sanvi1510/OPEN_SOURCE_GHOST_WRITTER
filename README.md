# Open-Source Ghostwriter 🤖📝

An autonomous AI agent that **detects and fixes outdated documentation** in GitHub repositories.

When a pull request is merged, Ghostwriter automatically:

1. **Analyzes** the code diff to identify documentation-breaking changes
2. **Rewrites** affected README sections using an LLM
3. **Validates** every code example in a secure Docker sandbox
4. **Self-corrects** if any example fails (up to a configurable retry limit)
5. **Pushes** the verified documentation update back to the repository

---

## Architecture

```
GitHub Webhook ─► FastAPI Server ─► LangGraph Workflow
                                        │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                      Analyzer       Writer         Tester
                     (LLM diff    (LLM rewrite)   (Docker sandbox)
                      analysis)       ▲              │
                                      └── retry ─────┘
```

---

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI entry point
│   └── webhook.py           # Webhook endpoint & HMAC validation
├── agent/
│   ├── state.py             # LangGraph workflow state
│   ├── nodes.py             # Analyzer, Writer, Tester nodes
│   └── workflow.py          # Graph definition & orchestration
├── tools/
│   ├── git_manager.py       # Clone, diff, commit, push
│   ├── docker_executor.py   # Secure sandbox execution
│   └── code_extractor.py    # Markdown → Python code blocks
├── prompts/
│   ├── analyzer_prompt.py   # Diff analysis prompt
│   └── writer_prompt.py     # Documentation rewrite prompt
├── sandbox/
│   └── Dockerfile           # Minimal Python sandbox image
├── tests/
│   ├── test_code_extractor.py
│   ├── test_git_manager.py
│   └── test_webhook.py
├── config.py                # Pydantic settings
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-org/ghostwriter.git
cd ghostwriter
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your secrets
```

| Variable               | Description                                     |
|------------------------|-------------------------------------------------|
| `GITHUB_WEBHOOK_SECRET`| Secret configured in the GitHub webhook settings |
| `GITHUB_TOKEN`         | Personal access token with `repo` scope          |
| `OPENAI_API_KEY`       | OpenAI API key                                   |
| `LLM_MODEL`            | Model to use (default: `gpt-4o`)                 |
| `CLONE_DIR`            | Directory for cloned repos (default: `/tmp/…`)   |
| `DOCKER_IMAGE`         | Sandbox image name (default: `ghostwriter-sandbox`) |
| `MAX_RETRIES`          | Max self-correction loops (default: `3`)         |

### 3. Build the Sandbox Image

```bash
docker build -t ghostwriter-sandbox sandbox/
```

### 4. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Set Up the GitHub Webhook

In your GitHub repository → **Settings** → **Webhooks** → **Add webhook**:

| Field          | Value                                      |
|----------------|--------------------------------------------|
| Payload URL    | `https://your-server.com/webhook`          |
| Content type   | `application/json`                         |
| Secret         | Same value as `GITHUB_WEBHOOK_SECRET`      |
| Events         | Select **Pull requests**                   |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## How It Works

1. **Webhook** – GitHub sends a `pull_request` event when a PR is merged.
2. **Validation** – The server verifies the HMAC-SHA256 signature.
3. **Clone** – The repository is cloned (or updated) locally.
4. **Diff** – The unified diff between the base and head commits is computed.
5. **Analyze** – An LLM identifies documentation-breaking changes.
6. **Write** – A second LLM call rewrites the affected README sections.
7. **Test** – Python code blocks are extracted and executed in a Docker sandbox.
8. **Retry** – If any code block fails, the error is fed back to the writer for self-correction.
9. **Push** – Once all examples pass (or the retry limit is reached), the updated README is committed and pushed.

---

## License

MIT
