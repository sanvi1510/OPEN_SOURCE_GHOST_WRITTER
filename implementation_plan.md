# Open-Source Ghostwriter — Implementation Plan

An autonomous AI agent that detects and fixes outdated documentation in open-source GitHub repositories.

## Proposed Changes

### Project Layout

```
c:\Users\Lenovo\Desktop\PBL\
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry-point
│   └── webhook.py         # Webhook endpoint + signature validation
├── agent/
│   ├── __init__.py
│   ├── state.py           # TypedDict workflow state
│   ├── nodes.py           # Analyzer / Writer / Tester nodes
│   └── workflow.py        # LangGraph graph definition
├── tools/
│   ├── __init__.py
│   ├── git_manager.py     # Clone, diff, commit, push
│   ├── docker_executor.py # Run code in Docker sandbox
│   └── code_extractor.py  # Extract fenced code blocks from Markdown
├── prompts/
│   ├── __init__.py
│   ├── analyzer_prompt.py # System + user prompts for the Analyzer
│   └── writer_prompt.py   # System + user prompts for the Writer
├── tests/
│   ├── __init__.py
│   ├── test_code_extractor.py
│   ├── test_git_manager.py
│   └── test_webhook.py
├── sandbox/
│   └── Dockerfile         # Python slim image for sandboxed execution
├── config.py              # Pydantic Settings (env-driven)
├── requirements.txt
├── .env.example
└── README.md
```

---

### 1. Scaffolding & Config

#### [NEW] [config.py](file:///c:/Users/Lenovo/Desktop/PBL/config.py)
- Pydantic `BaseSettings` reading from `.env`
- Keys: `GITHUB_WEBHOOK_SECRET`, `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`), `LLM_MODEL`, `GITHUB_TOKEN`, `CLONE_DIR`, `DOCKER_IMAGE`, `MAX_RETRIES`

#### [NEW] [requirements.txt](file:///c:/Users/Lenovo/Desktop/PBL/requirements.txt)
- `fastapi`, `uvicorn[standard]`, `langchain-openai`, `langgraph`, `langchain-core`, `gitpython`, `docker`, `python-dotenv`, `pydantic-settings`, `httpx`, `pytest`

#### [NEW] [.env.example](file:///c:/Users/Lenovo/Desktop/PBL/.env.example)
- Template with all required env vars

#### [NEW] [sandbox/Dockerfile](file:///c:/Users/Lenovo/Desktop/PBL/sandbox/Dockerfile)
- `python:3.11-slim`, no network, limited memory; receives code via `CMD`

---

### 2. Webhook Server

#### [NEW] [app/main.py](file:///c:/Users/Lenovo/Desktop/PBL/app/main.py)
- Create FastAPI app, include webhook router, add health-check `/`

#### [NEW] [app/webhook.py](file:///c:/Users/Lenovo/Desktop/PBL/app/webhook.py)
- `POST /webhook` endpoint
- Validate `X-Hub-Signature-256` using HMAC-SHA256
- Parse JSON payload → detect `pull_request` action `closed` with `merged=true`
- Extract repo clone URL, base/head SHAs, branch
- Call agent workflow asynchronously via `BackgroundTasks`

---

### 3. Repository Manager

#### [NEW] [tools/git_manager.py](file:///c:/Users/Lenovo/Desktop/PBL/tools/git_manager.py)
- `clone_repo(url, dest)` — shallow clone
- `get_diff(repo_path, base_sha, head_sha)` — returns unified diff string
- `read_file(repo_path, filepath)` — read a file from the repo
- `write_file(repo_path, filepath, content)` — write updated content
- `commit_and_push(repo_path, message, branch)` — stage, commit, push with token auth

---

### 4. Docker Sandbox

#### [NEW] [tools/docker_executor.py](file:///c:/Users/Lenovo/Desktop/PBL/tools/docker_executor.py)
- `execute_code(code: str) -> dict` returning `{stdout, stderr, exit_code}`
- Uses `docker` Python SDK
- Container config: no network, 256 MB memory, 30 s timeout, auto-remove

---

### 5. Code Block Extraction

#### [NEW] [tools/code_extractor.py](file:///c:/Users/Lenovo/Desktop/PBL/tools/code_extractor.py)
- Regex-based extraction of fenced ` ```python ` blocks from Markdown
- Returns `list[str]` of code snippets

---

### 6. Prompt Templates

#### [NEW] [prompts/analyzer_prompt.py](file:///c:/Users/Lenovo/Desktop/PBL/prompts/analyzer_prompt.py)
- System prompt instructs the LLM to produce structured JSON analysis from a diff (changed functions, old/new signatures, impact)

#### [NEW] [prompts/writer_prompt.py](file:///c:/Users/Lenovo/Desktop/PBL/prompts/writer_prompt.py)
- System prompt instructs the LLM to rewrite documentation sections, preserving Markdown formatting, using only real APIs

---

### 7. LangGraph Agent Workflow

#### [NEW] [agent/state.py](file:///c:/Users/Lenovo/Desktop/PBL/agent/state.py)
- `AgentState(TypedDict)` with fields: `repo_path`, `diff`, `analysis`, `readme_content`, `updated_readme`, `code_blocks`, `test_results`, `errors`, `retry_count`

#### [NEW] [agent/nodes.py](file:///c:/Users/Lenovo/Desktop/PBL/agent/nodes.py)
- `analyze_diff(state)` — calls LLM with analyzer prompt + diff → returns analysis
- `write_docs(state)` — calls LLM with writer prompt + analysis + README → returns updated README
- `test_docs(state)` — extracts code blocks → runs each in Docker → collects results

#### [NEW] [agent/workflow.py](file:///c:/Users/Lenovo/Desktop/PBL/agent/workflow.py)
- LangGraph `StateGraph` with nodes: `analyzer → writer → tester`
- Conditional edge from `tester`: if all tests pass → `END`; else → `writer` (self-correction loop)
- Max retries guard to prevent infinite loops

---

### 8. Tests

#### [NEW] [tests/test_code_extractor.py](file:///c:/Users/Lenovo/Desktop/PBL/tests/test_code_extractor.py)
- Tests for extracting Python blocks, ignoring non-Python blocks, handling edge cases

#### [NEW] [tests/test_git_manager.py](file:///c:/Users/Lenovo/Desktop/PBL/tests/test_git_manager.py)
- Tests for diff parsing helpers (mocked git)

#### [NEW] [tests/test_webhook.py](file:///c:/Users/Lenovo/Desktop/PBL/tests/test_webhook.py)
- `TestClient` tests: valid/invalid signature, non-merge PR, health-check

---

### 9. README

#### [NEW] [README.md](file:///c:/Users/Lenovo/Desktop/PBL/README.md)
- Project overview, architecture diagram (Mermaid), setup steps, env vars, running locally, testing

---

## Verification Plan

### Automated Tests
```bash
# From project root
cd c:\Users\Lenovo\Desktop\PBL
pip install -r requirements.txt
pytest tests/ -v
```
Tests cover:
- Code extractor correctness
- Webhook signature validation & payload routing
- Git manager helper logic (mocked)

### Manual Verification
1. **Server starts**: Run `uvicorn app.main:app --reload` and verify `GET /` returns `200 OK`.
2. **Webhook handling**: Use `curl` or Postman to send a sample merged-PR payload to `POST /webhook` and check server logs.
3. **Docker sandbox** (requires Docker running): Call `execute_code("print('hello')")` in a Python REPL and confirm `{'stdout': 'hello\n', 'stderr': '', 'exit_code': 0}`.

> [!IMPORTANT]
> Running the full end-to-end pipeline requires valid API keys (OpenAI or Anthropic) and a real GitHub repo with a webhook configured. The automated tests are designed to work **without** external dependencies by mocking LLM and GitHub calls.
