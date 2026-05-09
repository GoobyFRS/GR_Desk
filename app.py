#!/usr/bin/env python3
"""GR_Desk - Helpdesk and IT Service Management Application.

A Flask-based ITSM platform supporting ticket management, changes,
customer relationship management (CRM), human resource management (HRM),
and reporting with role-based access control and webhook notifications.

Rest in Peace Alex, July 2nd 2005 - December 14th 2024
Rest in Peace Dave, August 16th 1967 - December 19th 2025
"""

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import local_handlers.local_authentication_handler as local_authentication_handler
import local_handlers.local_config_loader as local_config_loader
import local_handlers.local_email_handler as local_email_handler
import local_handlers.local_webhook_handler as local_webhook_handler
from local_handlers.local_storage_handler import (
    generate_ticket_number,
    load_employees,
    load_tickets,
    save_employees,
    save_tickets,
)
from blueprints.api_ingest import api_ingest_bp
from blueprints.changes_module import changes_module_bp
from blueprints.crm_module import crm_module_bp
from blueprints.hrm_module import hrm_module_bp
from blueprints.itsm_core import itsm_core_bp
from blueprints.itsm_queues import itsm_queues_bp
from blueprints.reports_module import reports_module_bp
from blueprints.services_module import services_module_bp
from decorators import technician_required

# Application Constants
BUILD_ID: str = "0.1.0"
SESSION_TIMEOUT_HOURS: int = 12
EMAIL_CHECK_INTERVAL_SECONDS: int = 600
MAX_EMAIL_CHECK_ITERATIONS: int = 10_000
MAX_CONTENT_LENGTH_BYTES: int = 16 * 1024 * 1024

# Valid ticket statuses
VALID_TICKET_STATUSES: list[str] = [
    "new", "in_progress", "on_hold", "closed", "cancelled"
]

# Load secrets from .env file
load_dotenv(dotenv_path=".env")
EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
TAILSCALE_NOTIFY_EMAIL: str | None = os.getenv("TAILSCALE_NOTIFY_EMAIL")

# Configuration non-secret data loaded from YAML
core_yaml_config = local_config_loader.load_core_config()
TICKETS_FILE: str = core_yaml_config["tickets_file"]
EMPLOYEE_FILE: str = core_yaml_config["employee_file"]
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]
EMAIL_ENABLED: bool = core_yaml_config["email"]["enabled"]
EMAIL_ACCOUNT: str = core_yaml_config["email"]["account"]
IMAP_SERVER: str = core_yaml_config["email"]["imap_server"]
SMTP_SERVER: str = core_yaml_config["email"]["smtp_server"]
SMTP_PORT: int = core_yaml_config["email"]["smtp_port"]

# Flask App core setup and configuration
TEMPLATES_DIR: str = os.path.join(os.path.dirname(__file__), "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.getenv("FLASKAPP_SECRET_KEY")
app.permanent_session_lifetime = timedelta(hours=SESSION_TIMEOUT_HOURS)

app.config.update(
    SESSION_COOKIE_NAME="gr_desk_session_cookie",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=not app.debug,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_REFRESH_EACH_REQUEST=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=SESSION_TIMEOUT_HOURS),
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH_BYTES,
)

api_ingest_bp.config = {'TAILSCALE_NOTIFY_EMAIL': TAILSCALE_NOTIFY_EMAIL}
app.register_blueprint(api_ingest_bp)
app.register_blueprint(reports_module_bp)
app.register_blueprint(changes_module_bp)
app.register_blueprint(itsm_core_bp)
app.register_blueprint(itsm_queues_bp)
app.register_blueprint(crm_module_bp)
app.register_blueprint(hrm_module_bp)
app.register_blueprint(services_module_bp)

# Security header constants
HSTS_MAX_AGE_SECONDS: int = 86400  # 1 day

CONTENT_SECURITY_POLICY: str = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.bunny.net; "
    "img-src 'self' data: https:; "
    "font-src 'self' data: https://fonts.bunny.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


@app.after_request
def set_security_headers(response: Response) -> Response:
    """Apply security headers to all HTTP responses.

    Sets headers for XSS protection, clickjacking prevention,
    content security policy, and HSTS.

    Args:
        response: The Flask response object to modify.

    Returns:
        The response with security headers applied.
    """
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    if not app.debug:
        response.headers["Strict-Transport-Security"] = (
            f"max-age={HSTS_MAX_AGE_SECONDS}; includeSubDomains; preload"
        )

    return response

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def background_email_monitor() -> None:
    """Background thread for monitoring email replies.

    Continuously fetches email replies on a configurable interval and
    appends them to corresponding ticket notes. Uses bounded iterations
    to prevent unbounded loops per Power of 10 rule.
    """
    for _ in range(MAX_EMAIL_CHECK_ITERATIONS):
        try:
            local_email_handler.fetch_email_replies()
        except Exception as e:
            logging.error(f"Email monitor error: {e}")
        time.sleep(EMAIL_CHECK_INTERVAL_SECONDS)

    logging.warning(
        f"Email monitor reached max iterations ({MAX_EMAIL_CHECK_ITERATIONS})"
    )


def _start_email_monitor() -> None:
    """Start the background email monitoring thread if enabled."""
    if EMAIL_ENABLED:
        logging.info("Starting background email monitoring thread...")
        threading.Thread(target=background_email_monitor, daemon=True).start()
    else:
        logging.info("EMAIL_ENABLED is set to false. Skipping...")


_start_email_monitor()

@app.route("/", methods=["GET", "POST"])
def home() -> str | Any:
    """Render home page and handle new ticket submissions.

    GET: Display the ticket submission form.
    POST: Process new ticket creation and send notifications.

    Returns:
        Rendered template for GET, or redirect for POST.
    """
    if request.method == "POST":
        return _handle_ticket_submission()
    return render_template("index.html")


def _handle_ticket_submission() -> Any:
    """Process a new ticket submission from the home page form.

    Returns:
        Redirect to home page with flash message.
    """
    try:
        new_ticket = _create_ticket_from_form()
        _save_new_ticket(new_ticket)
        _send_ticket_notifications(new_ticket)

        flash(
            f"Ticket {new_ticket['ticket_number']} has been submitted successfully!",
            "success",
        )
        return redirect(url_for("home"))

    except KeyError as e:
        logging.error(f"Missing required form field: {e}")
        flash("Please fill out all required fields.", "danger")
        return redirect(url_for("home"))
    except Exception as e:
        logging.critical(f"Failed to process ticket submission: {e}")
        flash(
            "An error occurred while submitting your ticket. Please try again later.",
            "danger",
        )
        return redirect(url_for("home"))


def _create_ticket_from_form() -> dict[str, Any]:
    """Build a ticket dictionary from form data.

    Returns:
        Dictionary containing all ticket fields.

    Raises:
        KeyError: If required form fields are missing.
    """
    ticket_number = generate_ticket_number()

    return {
        "uuid": str(uuid.uuid4()),
        "ticket_number": ticket_number,
        "ticket_status": "new",
        "requestor_name": request.form["requestor_name"],
        "requestor_username": request.form.get("requestor_username", ""),
        "requestor_email": request.form["requestor_email"],
        "ticket_type": request.form.get("request_type", "request"),
        "ticket_subject": request.form["ticket_subject"],
        "ticket_body": request.form["ticket_message"],
        "ticket_impact": request.form.get("ticket_impact", "low"),
        "ticket_urgency": request.form.get("ticket_urgency", "low"),
        "escalation_level": 0,
        "assigned_queue": "support",
        "assigned_technician": None,
        "ticket_worknotes": [],
        "ticket_created_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket_escalation_timestamp": None,
        "ticket_closed_timestamp": None,
        "ticket_acknowledged_timestamp": None,
        "requestor_vip_status": False,
        "ticket_overdue": False,
    }


def _save_new_ticket(ticket: dict[str, Any]) -> None:
    """Save a new ticket to storage.

    Args:
        ticket: The ticket dictionary to save.
    """
    tickets = load_tickets()
    tickets.append(ticket)
    save_tickets(tickets)
    logging.info(f"{ticket['ticket_number']} has been created.")


def _send_ticket_notifications(ticket: dict[str, Any]) -> None:
    """Send email and webhook notifications for a new ticket.

    Args:
        ticket: The ticket dictionary containing notification details.
    """
    ticket_number = ticket["ticket_number"]

    # Send confirmation email
    if EMAIL_ENABLED:
        try:
            email_body = render_template("new-ticket-email.html", ticket=ticket)
            local_email_handler.send_email(
                ticket["requestor_email"],
                f"{ticket_number} - {ticket['ticket_subject']}",
                email_body,
                html=True,
            )
            logging.info(f"Confirmation email for {ticket_number} sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send email for {ticket_number}: {e}")
    else:
        logging.debug(f"EMAIL_ENABLED is false. Skipping email for {ticket_number}.")

    # Send webhook notifications
    try:
        local_webhook_handler.notify_ticket_event(
            ticket_number,
            ticket["ticket_subject"],
            "Open",
        )
        logging.info(f"Webhook notifications for {ticket_number} sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send webhook notifications for {ticket_number}: {e}")

@app.route("/login", methods=["GET", "POST"])
def login() -> str | Any:
    """Handle technician login authentication.

    GET: Display the login form.
    POST: Authenticate user credentials and create session.

    Returns:
        Rendered login template or redirect to dashboard on success.
    """
    if request.method == "POST":
        return _handle_login()
    return render_template("login.html")


def _handle_login() -> str | Any:
    """Process login form submission.

    Returns:
        Redirect to dashboard on success, or login page with error.
    """
    username = request.form.get("tech_username_box", "").strip()
    password = request.form.get("tech_password_box", "")
    employees = load_employees()

    for employee in employees:
        if employee.get("employee_username") != username:
            continue

        # Check if account is locked
        if employee.get("account_locked", False):
            logging.warning(f"Login attempt for locked account: {username}")
            return render_template("login.html", error="Account is locked.")

        # Modern hashed password check
        stored_hash = employee.get("password_hash")
        if stored_hash and local_authentication_handler.verify_password(
            password, stored_hash
        ):
            # Update last login timestamp
            employee["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            employee["failed_login_attempts"] = 0
            save_employees(employees)
            return _create_session(username)

        # Increment failed login attempts
        employee["failed_login_attempts"] = employee.get("failed_login_attempts", 0) + 1
        if employee["failed_login_attempts"] >= 5:
            employee["account_locked"] = True
        save_employees(employees)
        break

    logging.warning(f"Failed login attempt for username: {username}")
    return render_template("login.html", error="Invalid credentials.")


def _create_session(username: str) -> Any:
    """Create an authenticated session for a user.

    Args:
        username: The username to store in session.

    Returns:
        Redirect to dashboard.
    """
    session.permanent = True
    session["technician"] = username
    logging.info(f"{username} logged in successfully.")
    return redirect(url_for("dashboard"))

OPEN_TICKET_STATUSES: list[str] = ["new", "in_progress", "on_hold", "Open"]


@app.route("/dashboard")
@technician_required
def dashboard() -> str:
    """Display the technician dashboard with open tickets.

    Shows all tickets that are new, in progress, or on hold.

    Returns:
        Rendered dashboard template.
    """
    tickets = load_tickets()
    open_tickets = [
        ticket for ticket in tickets
        if ticket.get("ticket_status") in OPEN_TICKET_STATUSES
    ]
    return render_template(
        "dashboard.html",
        tickets=open_tickets,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )


@app.route("/ticket/<ticket_number>")
@technician_required
def ticket_detail(ticket_number: str) -> str | tuple[str, int]:
    """Display detailed view of a single ticket.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        Rendered ticket commander template or 404 page.
    """
    tickets = load_tickets()
    ticket = next(
        (t for t in tickets if t["ticket_number"] == ticket_number), None
    )

    if ticket:
        return render_template(
            "ticket-commander.html",
            ticket=ticket,
            loggedInTech=session["technician"],
        )

    return render_template("404.html"), 404


@app.route("/ticket/<ticket_number>/update_status/<ticket_status>", methods=["POST"])
@technician_required
def update_ticket_status(
    ticket_number: str, ticket_status: str
) -> tuple[str, int] | Any:
    """Update the status of a ticket.

    Args:
        ticket_number: The unique ticket identifier.
        ticket_status: The new status to set.

    Returns:
        JSON response with success message or error page.
    """
    if not session.get("technician"):
        return render_template("403.html"), 403

    if ticket_status not in VALID_TICKET_STATUSES:
        return render_template("400.html"), 400

    logged_in_tech = session["technician"]
    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        ticket_subject = ticket.get("ticket_subject", "No Subject Provided")
        ticket["ticket_status"] = ticket_status

        if ticket_status == "closed":
            ticket["ticket_closed_timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif ticket_status == "in_progress":
            ticket["ticket_acknowledged_timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        save_tickets(tickets)
        logging.info(
            f"Ticket {ticket_number} status updated to {ticket_status} "
            f"by {logged_in_tech}."
        )

        _send_status_webhook(ticket_number, ticket_status, ticket_subject)

        return jsonify({"message": f"Ticket {ticket_number} updated to {ticket_status}."})

    return render_template("404.html"), 404


def _send_status_webhook(
    ticket_number: str, ticket_status: str, ticket_subject: str
) -> None:
    """Send webhook notification for ticket status update.

    Args:
        ticket_number: The unique ticket identifier.
        ticket_status: The new ticket status.
        ticket_subject: The ticket subject line.
    """
    try:
        local_webhook_handler.notify_ticket_event(
            ticket_number=ticket_number,
            ticket_status=ticket_status,
            ticket_subject=ticket_subject,
        )
        logging.info(
            f"Ticket {ticket_number} status update notifications sent successfully."
        )
    except Exception as e:
        logging.error(
            f"Failed to send ticket status update notifications for {ticket_number}: {e}"
        )


@app.route("/ticket/<ticket_number>/append_note", methods=["POST"])
@technician_required
def add_ticket_note(ticket_number: str) -> tuple[Any, int]:
    """Append a work note to a ticket.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        JSON response with success or error message and HTTP status code.
    """
    new_tkt_note = request.form.get("note_content")

    if not new_tkt_note:
        return jsonify({"message": "Note Contents cannot be empty!"}), 400

    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        ticket["ticket_worknotes"].append(new_tkt_note)
        save_tickets(tickets)
        logging.info(f"Note successfully appended to {ticket_number}.")
        return jsonify({"message": "Note added successfully."}), 200

    return jsonify({"message": "Ticket not found."}), 404


@app.route("/logout")
def logout() -> Any:
    """Log out the current user and clear session.

    Returns:
        Redirect to login page.
    """
    session.pop("technician", None)
    return redirect(url_for("login"))


# Error handlers
@app.errorhandler(400)
def bad_request(e: Exception) -> tuple[str, int]:
    """Handle 400 Bad Request errors.

    Args:
        e: The exception that triggered the error.

    Returns:
        Rendered 400 error page with status code.
    """
    return render_template("400.html"), 400


@app.errorhandler(403)
def forbidden(e: Exception) -> tuple[str, int]:
    """Handle 403 Forbidden errors.

    Args:
        e: The exception that triggered the error.

    Returns:
        Rendered 403 error page with status code.
    """
    return render_template("403.html"), 403


@app.errorhandler(404)
def page_not_found(e: Exception) -> tuple[str, int]:
    """Handle 404 Not Found errors.

    Args:
        e: The exception that triggered the error.

    Returns:
        Rendered 404 error page with status code.
    """
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e: Exception) -> tuple[str, int]:
    """Handle 500 Internal Server errors.

    Args:
        e: The exception that triggered the error.

    Returns:
        Rendered 500 error page with status code.
    """
    logging.critical(f"Internal Server Error: {e}")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
