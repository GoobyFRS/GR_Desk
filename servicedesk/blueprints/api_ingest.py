"""API Ingest blueprint for receiving webhooks from external platforms."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from servicedesk.models.ticket import Ticket
from servicedesk.storage.counter_sync import sync_ticket_counter
from servicedesk.storage.yaml_store import YamlStore

logger: logging.Logger = logging.getLogger(__name__)

api_ingest_bp: Blueprint = Blueprint("api_ingest", __name__)


def _create_ticket_from_webhook(
    source: str,
    subject: str,
    body: str,
    requestor_name: str = "System",
    requestor_email: str = "",
    ticket_type: str = "Alert",
    impact: str = "medium",
    urgency: str = "medium",
    metadata: dict[str, Any] | None = None,
) -> Ticket:
    """Create a ticket from webhook data.

    Args:
        source: Source platform identifier.
        subject: Ticket subject.
        body: Ticket body/description.
        requestor_name: Name of requestor.
        requestor_email: Email of requestor.
        ticket_type: Type of ticket.
        impact: Impact level.
        urgency: Urgency level.
        metadata: Additional metadata to store.

    Returns:
        Created ticket instance.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    sync_ticket_counter(store.get_all())

    ticket = Ticket(
        requestor_name=requestor_name,
        requestor_username=requestor_email or f"{source}@webhook.internal",
        ticket_type=ticket_type,
        ticket_subject=subject,
        ticket_body=body,
        ticket_impact=impact,
        ticket_urgency=urgency,
        ticket_source=source,
    )

    # Add metadata as a work note if provided
    if metadata:
        metadata_str = "\n".join(f"{k}: {v}" for k, v in metadata.items())
        ticket.add_worknote("System", f"Webhook metadata:\n{metadata_str}")

    store.save(ticket)

    # Trigger outbound webhooks
    from servicedesk.webhooks.egress import send_ticket_created_webhook
    send_ticket_created_webhook(ticket)

    logger.info(f"Created ticket {ticket.ticket_number} from {source} webhook")
    return ticket


@api_ingest_bp.route("/health", methods=["GET"])
def health_check() -> Response:
    """Health check endpoint for API.

    Returns:
        JSON response with status.
    """
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# =============================================================================
# Tailscale Webhooks
# https://tailscale.com/kb/1213/webhooks
# =============================================================================

@api_ingest_bp.route("/tailscale", methods=["POST"])
def tailscale_webhook() -> tuple[Response, int]:
    """Handle incoming Tailscale webhooks.

    Tailscale sends webhooks for various events like:
    - nodeCreated, nodeDeleted, nodeApproved
    - userCreated, userDeleted, userApproved
    - policyUpdate

    Returns:
        JSON response with status.
    """
    config = current_app.config["APP_CONFIG"]
    webhook_config = config.get("webhooks", {}).get("ingest", {}).get("tailscale", {})

    if not webhook_config.get("enabled", False):
        logger.warning("Tailscale webhook received but not enabled")
        return jsonify({"error": "Webhook not enabled"}), 403

    # Verify webhook signature if secret is configured
    webhook_secret = webhook_config.get("secret", "")
    if webhook_secret:
        signature = request.headers.get("Tailscale-Webhook-Signature", "")
        if not _verify_tailscale_signature(request.data, signature, webhook_secret):
            logger.warning("Tailscale webhook signature verification failed")
            return jsonify({"error": "Invalid signature"}), 401

    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception as e:
        logger.error(f"Failed to parse Tailscale webhook: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract event details
    events = payload.get("events", [])
    if not events:
        return jsonify({"status": "no events"}), 200

    tickets_created = []

    for event in events:
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", "")
        data = event.get("data", {})

        # Determine severity based on event type
        impact, urgency = _get_tailscale_severity(event_type)

        # Build ticket content
        subject = f"[Tailscale] {_format_event_type(event_type)}"
        body = _build_tailscale_body(event_type, data, timestamp)

        metadata = {
            "event_type": event_type,
            "timestamp": timestamp,
            "tailnet": payload.get("tailnet", ""),
        }

        ticket = _create_ticket_from_webhook(
            source="tailscale",
            subject=subject,
            body=body,
            requestor_name="Tailscale",
            ticket_type="Alert",
            impact=impact,
            urgency=urgency,
            metadata=metadata,
        )
        tickets_created.append(ticket.ticket_number)

    return jsonify({
        "status": "success",
        "tickets_created": tickets_created,
    }), 201


def _verify_tailscale_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Tailscale webhook signature.

    Args:
        payload: Raw request body.
        signature: Signature from header.
        secret: Webhook secret.

    Returns:
        True if signature is valid.
    """
    if not signature or not secret:
        return False

    # Tailscale uses HMAC-SHA256
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def _get_tailscale_severity(event_type: str) -> tuple[str, str]:
    """Determine impact and urgency based on Tailscale event type.

    Args:
        event_type: The Tailscale event type.

    Returns:
        Tuple of (impact, urgency).
    """
    high_severity_events = {
        "nodeDeleted", "userDeleted", "policyUpdate",
        "nodeKeyExpiringInOneDay", "nodeKeyExpired",
    }
    medium_severity_events = {
        "nodeCreated", "userCreated", "nodeApproved", "userApproved",
    }

    if event_type in high_severity_events:
        return ("high", "high")
    elif event_type in medium_severity_events:
        return ("medium", "medium")
    return ("low", "low")


def _format_event_type(event_type: str) -> str:
    """Format event type for display.

    Args:
        event_type: Raw event type string.

    Returns:
        Human-readable event type.
    """
    # Convert camelCase to Title Case with spaces
    result = ""
    for char in event_type:
        if char.isupper() and result:
            result += " "
        result += char
    return result.title()


def _build_tailscale_body(event_type: str, data: dict[str, Any], timestamp: str) -> str:
    """Build ticket body from Tailscale event data.

    Args:
        event_type: The event type.
        data: Event data payload.
        timestamp: Event timestamp.

    Returns:
        Formatted ticket body.
    """
    lines = [
        f"Tailscale Event: {_format_event_type(event_type)}",
        f"Timestamp: {timestamp}",
        "",
        "Event Details:",
    ]

    if "node" in data:
        node = data["node"]
        lines.append(f"  Node: {node.get('name', 'Unknown')}")
        lines.append(f"  Node ID: {node.get('id', 'Unknown')}")
        lines.append(f"  Addresses: {', '.join(node.get('addresses', []))}")

    if "user" in data:
        user = data["user"]
        lines.append(f"  User: {user.get('displayName', 'Unknown')}")
        lines.append(f"  Email: {user.get('loginName', 'Unknown')}")

    if "policy" in data:
        lines.append("  Policy update detected")

    if "actor" in data:
        actor = data["actor"]
        lines.append(f"  Actor: {actor.get('displayName', actor.get('loginName', 'Unknown'))}")

    return "\n".join(lines)


# =============================================================================
# Uptime Kuma Webhooks
# https://github.com/louislam/uptime-kuma/wiki/Webhook
# =============================================================================

@api_ingest_bp.route("/uptime-kuma", methods=["POST"])
def uptime_kuma_webhook() -> tuple[Response, int]:
    """Handle incoming Uptime Kuma webhooks.

    Uptime Kuma sends webhooks when monitors change state (up/down).

    Returns:
        JSON response with status.
    """
    config = current_app.config["APP_CONFIG"]
    webhook_config = config.get("webhooks", {}).get("ingest", {}).get("uptime_kuma", {})

    if not webhook_config.get("enabled", False):
        logger.warning("Uptime Kuma webhook received but not enabled")
        return jsonify({"error": "Webhook not enabled"}), 403

    # Verify secret token if configured
    expected_token = webhook_config.get("token", "")
    if expected_token:
        auth_header = request.headers.get("Authorization", "")
        provided_token = auth_header.replace("Bearer ", "") if auth_header else ""
        if not hmac.compare_digest(provided_token, expected_token):
            logger.warning("Uptime Kuma webhook token verification failed")
            return jsonify({"error": "Invalid token"}), 401

    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception as e:
        logger.error(f"Failed to parse Uptime Kuma webhook: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract monitor and heartbeat data
    monitor = payload.get("monitor", {})
    heartbeat = payload.get("heartbeat", {})
    msg = payload.get("msg", "")

    monitor_name = monitor.get("name", "Unknown Monitor")
    monitor_url = monitor.get("url", "")
    status = heartbeat.get("status", 0)  # 0 = down, 1 = up, 2 = pending
    status_text = {0: "DOWN", 1: "UP", 2: "PENDING"}.get(status, "UNKNOWN")

    # Only create tickets for DOWN events by default
    create_for_up = webhook_config.get("create_ticket_on_up", False)
    if status == 1 and not create_for_up:
        logger.info(f"Uptime Kuma: {monitor_name} is UP, not creating ticket")
        return jsonify({"status": "acknowledged", "action": "none"}), 200

    # Determine severity
    if status == 0:  # DOWN
        impact = "high"
        urgency = "high"
        ticket_type = "Incident"
    else:
        impact = "low"
        urgency = "low"
        ticket_type = "Alert"

    subject = f"[Uptime Kuma] {monitor_name} is {status_text}"
    body = _build_uptime_kuma_body(monitor, heartbeat, msg)

    metadata = {
        "monitor_id": monitor.get("id", ""),
        "monitor_name": monitor_name,
        "monitor_url": monitor_url,
        "status": status_text,
        "response_time": heartbeat.get("ping", ""),
    }

    ticket = _create_ticket_from_webhook(
        source="uptime-kuma",
        subject=subject,
        body=body,
        requestor_name="Uptime Kuma",
        ticket_type=ticket_type,
        impact=impact,
        urgency=urgency,
        metadata=metadata,
    )

    return jsonify({
        "status": "success",
        "ticket_number": ticket.ticket_number,
    }), 201


def _build_uptime_kuma_body(
    monitor: dict[str, Any],
    heartbeat: dict[str, Any],
    msg: str
) -> str:
    """Build ticket body from Uptime Kuma data.

    Args:
        monitor: Monitor configuration data.
        heartbeat: Heartbeat/status data.
        msg: Status message.

    Returns:
        Formatted ticket body.
    """
    status = heartbeat.get("status", 0)
    status_text = {0: "DOWN", 1: "UP", 2: "PENDING"}.get(status, "UNKNOWN")

    lines = [
        f"Monitor: {monitor.get('name', 'Unknown')}",
        f"Status: {status_text}",
        f"URL: {monitor.get('url', 'N/A')}",
        f"Type: {monitor.get('type', 'Unknown')}",
        "",
        f"Message: {msg}",
        "",
        "Details:",
        f"  Response Time: {heartbeat.get('ping', 'N/A')} ms",
        f"  Time: {heartbeat.get('time', 'N/A')}",
    ]

    if heartbeat.get("msg"):
        lines.append(f"  Error: {heartbeat.get('msg')}")

    return "\n".join(lines)


# =============================================================================
# Generic Webhook Endpoint
# =============================================================================

@api_ingest_bp.route("/generic", methods=["POST"])
def generic_webhook() -> tuple[Response, int]:
    """Handle generic webhook payloads.

    Accepts a simple JSON payload to create tickets programmatically.

    Expected payload:
    {
        "subject": "Ticket subject",
        "body": "Ticket description",
        "source": "system-name",
        "requestor_name": "System Name",
        "requestor_email": "alerts@example.com",
        "ticket_type": "Alert",
        "impact": "medium",
        "urgency": "medium"
    }

    Returns:
        JSON response with created ticket number.
    """
    config = current_app.config["APP_CONFIG"]
    webhook_config = config.get("webhooks", {}).get("ingest", {}).get("generic", {})

    if not webhook_config.get("enabled", False):
        logger.warning("Generic webhook received but not enabled")
        return jsonify({"error": "Webhook not enabled"}), 403

    # Verify API key if configured
    api_key = webhook_config.get("api_key", "")
    if api_key:
        provided_key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided_key, api_key):
            logger.warning("Generic webhook API key verification failed")
            return jsonify({"error": "Invalid API key"}), 401

    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception as e:
        logger.error(f"Failed to parse generic webhook: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Validate required fields
    subject = payload.get("subject", "").strip()
    body = payload.get("body", "").strip()

    if not subject:
        return jsonify({"error": "Missing required field: subject"}), 400
    if not body:
        return jsonify({"error": "Missing required field: body"}), 400

    ticket = _create_ticket_from_webhook(
        source=payload.get("source", "generic"),
        subject=subject,
        body=body,
        requestor_name=payload.get("requestor_name", "API"),
        requestor_email=payload.get("requestor_email", ""),
        ticket_type=payload.get("ticket_type", "Alert"),
        impact=payload.get("impact", "medium"),
        urgency=payload.get("urgency", "medium"),
        metadata=payload.get("metadata"),
    )

    return jsonify({
        "status": "success",
        "ticket_number": ticket.ticket_number,
        "ticket_id": ticket.uuid,
    }), 201
