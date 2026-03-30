"""
GitHub webhook endpoint for Open-Source Ghostwriter.

Responsibilities
────────────────
1. Validate the HMAC-SHA256 signature that GitHub attaches to every delivery.
2. Parse the incoming JSON payload into a typed ``WebhookPayload`` model.
3. Detect **merged** pull-request events.
4. De-duplicate deliveries using the ``X-GitHub-Delivery`` header.
5. Kick off the LangGraph documentation-update workflow as a background task.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from config import settings
from models import WebhookPayload
from agent.workflow import run_ghostwriter_workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

# Simple in-memory set of processed delivery IDs to prevent duplicate runs.
# In production, replace with Redis or a database table.
_processed_deliveries: set[str] = set()
_MAX_DELIVERY_CACHE = 1_000


# ── Helpers ─────────────────────────────────────────────────────────────────

def verify_signature(payload_body: bytes, signature_header: str | None) -> None:
    """Validate the GitHub webhook HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of the ``X-Hub-Signature-256`` header.

    Raises:
        HTTPException: If the signature is missing or does not match.
    """
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header.")

    expected_signature = (
        "sha256="
        + hmac.new(
            key=settings.github_webhook_secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature.")


def _is_duplicate_delivery(delivery_id: str | None) -> bool:
    """Return ``True`` if this delivery has already been processed.

    GitHub retries webhook deliveries on timeouts, so we track IDs to
    avoid running the workflow twice for the same event.
    """
    if not delivery_id:
        return False  # missing header → process anyway

    if delivery_id in _processed_deliveries:
        return True

    # Evict oldest entries when the cache grows too large.
    if len(_processed_deliveries) >= _MAX_DELIVERY_CACHE:
        _processed_deliveries.clear()

    _processed_deliveries.add(delivery_id)
    return False


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, str]:
    """Receive and process a GitHub webhook delivery.

    Only **merged pull-request** events trigger the documentation workflow;
    all other events are acknowledged but ignored.
    """
    body: bytes = await request.body()

    # 1. Validate the HMAC signature
    verify_signature(body, x_hub_signature_256)

    # 2. De-duplicate deliveries
    if _is_duplicate_delivery(x_github_delivery):
        logger.info("Duplicate delivery %s – skipping.", x_github_delivery)
        return {"status": "ignored", "reason": "duplicate delivery"}

    # 3. Only handle pull-request events
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": "not a pull_request event"}

    # 4. Parse payload into a typed model (safe against missing keys)
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.warning("Malformed payload: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed payload.") from exc

    if not payload.is_merged_pr:
        return {"status": "ignored", "reason": "PR not merged"}

    # 5. Trigger workflow
    logger.info(
        "Merged PR detected – repo=%s  branch=%s",
        payload.clone_url,
        payload.branch,
    )

    background_tasks.add_task(
        run_ghostwriter_workflow,
        clone_url=payload.clone_url,
        branch=payload.branch,
        base_sha=payload.base_sha,
        head_sha=payload.head_sha,
    )

    return {"status": "processing", "branch": payload.branch}
