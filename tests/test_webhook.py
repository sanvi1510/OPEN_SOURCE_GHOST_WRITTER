"""
Unit tests for the GitHub webhook endpoint.

Covers:
  • HMAC-SHA256 signature validation (valid & invalid)
  • Ignoring non-pull-request events
  • Ignoring unmerged pull requests
  • Triggering background workflow on merged PRs
  • Malformed payload handling
  • Delivery deduplication
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.webhook import _processed_deliveries
from config import settings


def _sign_payload(payload: bytes) -> str:
    """Generate a valid HMAC-SHA256 signature for *payload*."""
    return (
        "sha256="
        + hmac.new(
            key=settings.github_webhook_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )


# ── Sample payloads ─────────────────────────────────────────────────────────

_MERGED_PR_PAYLOAD: dict = {
    "action": "closed",
    "pull_request": {
        "merged": True,
        "base": {"ref": "main", "sha": "aaa111"},
        "head": {"ref": "feature", "sha": "bbb222"},
    },
    "repository": {
        "clone_url": "https://github.com/user/repo.git",
    },
}

_UNMERGED_PR_PAYLOAD: dict = {
    "action": "closed",
    "pull_request": {
        "merged": False,
        "base": {"ref": "main", "sha": "aaa111"},
        "head": {"ref": "feature", "sha": "bbb222"},
    },
    "repository": {
        "clone_url": "https://github.com/user/repo.git",
    },
}


def _headers(
    body: bytes,
    event: str = "pull_request",
    delivery: str | None = None,
) -> dict[str, str]:
    """Build request headers with a valid signature."""
    h: dict[str, str] = {
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": _sign_payload(body),
    }
    if delivery:
        h["X-GitHub-Delivery"] = delivery
    return h


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_delivery_cache() -> None:
    """Reset the deduplication cache between tests."""
    _processed_deliveries.clear()


@pytest.mark.asyncio
async def test_health_check() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_missing_signature_returns_401() -> None:
    body = json.dumps(_MERGED_PR_PAYLOAD).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers={"X-GitHub-Event": "pull_request"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_signature_returns_401() -> None:
    body = json.dumps(_MERGED_PR_PAYLOAD).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=invalidsig",
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_non_pr_event_ignored() -> None:
    body = json.dumps({"action": "created"}).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers=_headers(body, event="issues"),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_unmerged_pr_ignored() -> None:
    body = json.dumps(_UNMERGED_PR_PAYLOAD).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers=_headers(body),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_merged_pr_triggers_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """A merged PR should return 200 with status 'processing'."""
    monkeypatch.setattr(
        "app.webhook.run_ghostwriter_workflow",
        lambda **kw: None,
    )

    body = json.dumps(_MERGED_PR_PAYLOAD).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers=_headers(body),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["branch"] == "main"


@pytest.mark.asyncio
async def test_malformed_payload_returns_400() -> None:
    """Non-JSON body should return 400."""
    body = b"not json at all"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers=_headers(body),
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_delivery_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same X-GitHub-Delivery ID should not trigger the workflow twice."""
    monkeypatch.setattr(
        "app.webhook.run_ghostwriter_workflow",
        lambda **kw: None,
    )

    body = json.dumps(_MERGED_PR_PAYLOAD).encode()
    hdrs = _headers(body, delivery="delivery-123")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post("/webhook", content=body, headers=hdrs)
        resp2 = await client.post("/webhook", content=body, headers=hdrs)

    assert resp1.json()["status"] == "processing"
    assert resp2.json()["status"] == "ignored"
    assert resp2.json()["reason"] == "duplicate delivery"
