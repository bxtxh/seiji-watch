"""
Airtable Webhook Handler - Process issue review workflow status changes.
Handles secure webhook notifications from Airtable when issues are reviewed.
"""

import hashlib
import hmac
import json
import logging
import os

# Import the enhanced services
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator

# TODO: Replace with proper HTTP client calls to respective services
# These are placeholder implementations to avoid cross-service imports
class AirtableIssueManager:
    """Placeholder for Airtable issue management. Should be replaced with HTTP API calls."""
    
    async def process_webhook_data(self, data: Any) -> dict[str, Any]:
        """Placeholder method for processing webhook data."""
        logger.warning("AirtableIssueManager.process_webhook_data called - implement HTTP API call")
        return {"status": "placeholder", "message": "HTTP API call not yet implemented"}

class DiscordNotificationBot:
    """Placeholder for Discord notifications. Should be replaced with HTTP API calls."""
    
    async def send_notification(self, message: str, data: Any = None) -> bool:
        """Placeholder method for sending notifications."""
        logger.warning("DiscordNotificationBot.send_notification called - implement HTTP API call")
        return True


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/airtable", tags=["Airtable Webhooks"])

# Security scheme
security = HTTPBearer()


@dataclass
class WebhookConfig:
    """Configuration for Airtable webhook handling."""

    webhook_secret: str
    max_payload_size: int = 1024 * 1024  # 1MB
    rate_limit_per_minute: int = 60
    signature_header: str = "X-Airtable-Webhook-Signature"
    timestamp_tolerance: int = 300  # 5 minutes


# Webhook configuration
webhook_config = WebhookConfig(
    webhook_secret=os.getenv("AIRTABLE_WEBHOOK_SECRET", ""),
)


# Request Models
class AirtableWebhookPayload(BaseModel):
    """Airtable webhook payload structure."""

    base: dict[str, str]
    webhook: dict[str, str]
    timestamp: str
    action_metadata: dict[str, Any] | None = Field(None, alias="actionMetadata")
    changed_tables_by_id: dict[str, Any] | None = Field(None, alias="changedTablesById")
    created_records_by_id: dict[str, Any] | None = Field(
        None, alias="createdRecordsById"
    )
    destroyed_record_ids: list[str] | None = Field(None, alias="destroyedRecordIds")
    changed_records_by_id: dict[str, Any] | None = Field(
        None, alias="changedRecordsById"
    )

    @validator("timestamp")
    def validate_timestamp(self, v):
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Invalid timestamp format")


class WebhookProcessingResult(BaseModel):
    """Result of webhook processing."""

    success: bool
    processed_changes: int
    notifications_sent: int
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: int


# Dependencies
async def get_airtable_manager() -> AirtableIssueManager:
    """Get Airtable issue manager instance."""
    return AirtableIssueManager()


async def get_discord_bot() -> DiscordNotificationBot:
    """Get Discord notification bot instance."""
    return DiscordNotificationBot()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Airtable webhook signature using HMAC-SHA256."""
    if not secret:
        logger.warning("No webhook secret configured - signature verification disabled")
        return True

    try:
        # Airtable sends signature as: sha256=<hex_digest>
        if not signature.startswith("sha256="):
            logger.error("Invalid signature format")
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix

        # Calculate HMAC
        calculated_signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        # Secure comparison
        return hmac.compare_digest(calculated_signature, expected_signature)

    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


def extract_issue_changes(payload: AirtableWebhookPayload) -> list[dict[str, Any]]:
    """Extract issue-related changes from webhook payload."""
    changes = []

    # Process changed records
    if payload.changedRecordsById:
        for record_id, record_data in payload.changedRecordsById.items():
            # Check if this is an Issues table change
            current = record_data.get("current", {})
            previous = record_data.get("previous", {})

            # Look for status changes
            current_status = current.get("fields", {}).get("Status")
            previous_status = previous.get("fields", {}).get("Status")

            if current_status and current_status != previous_status:
                changes.append(
                    {
                        "record_id": record_id,
                        "change_type": "status_change",
                        "old_status": previous_status,
                        "new_status": current_status,
                        "fields": current.get("fields", {}),
                        "timestamp": payload.timestamp,
                    }
                )

    # Process created records
    if payload.createdRecordsById:
        for record_id, record_data in payload.createdRecordsById.items():
            fields = record_data.get("fields", {})
            if fields.get("Status"):
                changes.append(
                    {
                        "record_id": record_id,
                        "change_type": "record_created",
                        "new_status": fields.get("Status"),
                        "fields": fields,
                        "timestamp": payload.timestamp,
                    }
                )

    # Process destroyed records
    if payload.destroyedRecordIds:
        for record_id in payload.destroyedRecordIds:
            changes.append(
                {
                    "record_id": record_id,
                    "change_type": "record_deleted",
                    "timestamp": payload.timestamp,
                }
            )

    return changes


async def process_status_change(
    change: dict[str, Any],
    airtable_manager: AirtableIssueManager,
    discord_bot: DiscordNotificationBot,
) -> dict[str, Any]:
    """Process a single status change event."""
    result = {
        "record_id": change["record_id"],
        "success": False,
        "actions_taken": [],
        "errors": [],
    }

    try:
        record_id = change["record_id"]
        new_status = change["new_status"]
        old_status = change.get("old_status")

        logger.info(
            f"Processing status change for {record_id}: {old_status} -> {new_status}"
        )

        # Get the full issue record for context
        issue_record = await airtable_manager.get_issue_record(record_id)
        if not issue_record:
            result["errors"].append(f"Issue record {record_id} not found")
            return result

        # Log the status transition
        audit_log = {
            "record_id": record_id,
            "issue_id": issue_record.issue_id,
            "status_change": f"{old_status} -> {new_status}",
            "timestamp": change["timestamp"],
            "fields": change.get("fields", {}),
        }
        logger.info(f"Issue status audit: {json.dumps(audit_log)}")
        result["actions_taken"].append("audit_logged")

        # Handle specific status transitions
        if new_status == "approved":
            # Issue was approved - might trigger cache refresh, notifications, etc.
            result["actions_taken"].append("approval_processed")

            # Send notification for high-impact approvals
            if issue_record.quality_score > 0.8:
                await discord_bot.send_custom_notification(
                    title="🎯 高品質イシューが承認されました",
                    message=f"品質スコア {issue_record.quality_score:.2f} のイシューが承認されました:\n\n"
                    f"**Level 1:** {issue_record.label_lv1}\n"
                    f"**Level 2:** {issue_record.label_lv2}\n"
                    f"**関連法案:** {issue_record.source_bill_id}",
                    color=0x00FF00,
                )
                result["actions_taken"].append("notification_sent")

        elif new_status == "rejected":
            # Issue was rejected
            result["actions_taken"].append("rejection_processed")

            # Log rejection reason if available
            reviewer_notes = change.get("fields", {}).get("Reviewer_Notes")
            if reviewer_notes:
                logger.info(f"Issue {record_id} rejected with notes: {reviewer_notes}")

        elif new_status == "failed_validation":
            # Issue failed validation
            result["actions_taken"].append("validation_failure_processed")

            # Could trigger reprocessing or manual review alerts

        # Update any cached data if needed
        # (This would integrate with caching system when implemented)
        result["actions_taken"].append("cache_invalidated")

        result["success"] = True

    except Exception as e:
        error_msg = f"Failed to process status change for {change['record_id']}: {e}"
        logger.error(error_msg)
        result["errors"].append(error_msg)

    return result


# Rate limiting state (in production, use Redis or similar)
_rate_limit_state = {}


def check_rate_limit(client_ip: str) -> bool:
    """Simple in-memory rate limiting."""
    now = datetime.now()
    minute_key = now.strftime("%Y-%m-%d-%H-%M")
    key = f"{client_ip}:{minute_key}"

    current_count = _rate_limit_state.get(key, 0)
    if current_count >= webhook_config.rate_limit_per_minute:
        return False

    _rate_limit_state[key] = current_count + 1

    # Clean old entries (keep only current minute)
    keys_to_remove = [k for k in _rate_limit_state.keys() if not k.endswith(minute_key)]
    for old_key in keys_to_remove:
        _rate_limit_state.pop(old_key, None)

    return True


# Webhook Endpoints
@router.post("/issues/status-changes")
async def handle_issue_status_changes(
    request: Request,
    background_tasks: BackgroundTasks,
    airtable_manager: AirtableIssueManager = Depends(get_airtable_manager),
    discord_bot: DiscordNotificationBot = Depends(get_discord_bot),
):
    """Handle Airtable webhook for issue status changes."""
    start_time = datetime.now()

    try:
        # Rate limiting
        client_ip = request.client.host
        if not check_rate_limit(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Get raw payload for signature verification
        raw_payload = await request.body()

        # Check payload size
        if len(raw_payload) > webhook_config.max_payload_size:
            raise HTTPException(status_code=413, detail="Payload too large")

        # Verify signature
        signature = request.headers.get(webhook_config.signature_header)
        if not signature:
            logger.warning("Webhook request missing signature header")
            raise HTTPException(status_code=401, detail="Missing signature")

        if not verify_webhook_signature(
            raw_payload, signature, webhook_config.webhook_secret
        ):
            logger.error("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse payload
        try:
            payload_dict = json.loads(raw_payload.decode("utf-8"))
            payload = AirtableWebhookPayload(**payload_dict)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload format")

        # Validate timestamp (prevent replay attacks)
        try:
            webhook_time = datetime.fromisoformat(
                payload.timestamp.replace("Z", "+00:00")
            )
            time_diff = abs(
                (datetime.now().astimezone() - webhook_time).total_seconds()
            )

            if time_diff > webhook_config.timestamp_tolerance:
                logger.warning(f"Webhook timestamp too old: {time_diff} seconds")
                raise HTTPException(status_code=400, detail="Request timestamp too old")

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp")

        # Log webhook receipt
        logger.info(
            f"Received Airtable webhook from {client_ip}: {payload.webhook.get('id', 'unknown')}"
        )

        # Extract issue changes
        changes = extract_issue_changes(payload)

        if not changes:
            return WebhookProcessingResult(
                success=True,
                processed_changes=0,
                notifications_sent=0,
                processing_time_ms=int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
            )

        # Process changes in background
        background_tasks.add_task(
            process_changes_background, changes, airtable_manager, discord_bot
        )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return WebhookProcessingResult(
            success=True,
            processed_changes=len(changes),
            notifications_sent=0,  # Will be updated in background
            processing_time_ms=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_changes_background(
    changes: list[dict[str, Any]],
    airtable_manager: AirtableIssueManager,
    discord_bot: DiscordNotificationBot,
):
    """Process webhook changes in background."""
    try:
        results = []
        notifications_sent = 0

        for change in changes:
            if change["change_type"] in ["status_change", "record_created"]:
                result = await process_status_change(
                    change, airtable_manager, discord_bot
                )
                results.append(result)

                if "notification_sent" in result.get("actions_taken", []):
                    notifications_sent += 1

        # Log summary
        successful_changes = sum(1 for r in results if r["success"])
        total_changes = len(results)

        logger.info(
            f"Background processing complete: {successful_changes}/{total_changes} successful, "
            f"{notifications_sent} notifications sent"
        )

    except Exception as e:
        logger.error(f"Background processing error: {e}")


@router.post("/issues/test-webhook")
async def test_webhook_handler():
    """Test endpoint for webhook functionality."""
    return {
        "message": "Webhook handler is working",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "secret_configured": bool(webhook_config.webhook_secret),
            "max_payload_size": webhook_config.max_payload_size,
            "rate_limit": webhook_config.rate_limit_per_minute,
        },
    }


@router.get("/issues/webhook-status")
async def get_webhook_status():
    """Get webhook handler status and configuration."""
    return {
        "status": "active",
        "configuration": {
            "webhook_secret_configured": bool(webhook_config.webhook_secret),
            "max_payload_size_mb": webhook_config.max_payload_size // (1024 * 1024),
            "rate_limit_per_minute": webhook_config.rate_limit_per_minute,
            "timestamp_tolerance_seconds": webhook_config.timestamp_tolerance,
        },
        "rate_limiting": {
            "current_state_size": len(_rate_limit_state),
            "implementation": "in_memory",
        },
        "security": {
            "signature_verification": "hmac_sha256",
            "replay_protection": "timestamp_validation",
        },
    }


# Health check for the webhook handler
@router.get("/health")
async def webhook_health_check():
    """Health check for webhook handler."""
    try:
        # Test dependencies
        airtable_manager = AirtableIssueManager()
        airtable_healthy = await airtable_manager.health_check()

        discord_bot = DiscordNotificationBot()
        discord_healthy = await discord_bot.health_check()

        overall_healthy = airtable_healthy and discord_healthy

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": {
                "airtable_manager": "healthy" if airtable_healthy else "unhealthy",
                "discord_bot": "healthy" if discord_healthy else "unhealthy",
                "webhook_config": (
                    "healthy" if webhook_config.webhook_secret else "warning"
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Webhook health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
