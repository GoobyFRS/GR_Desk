#!/usr/bin/env python3
import json
import threading
import time
import logging
import os
import uuid
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, Response, render_template, request, redirect, url_for, session, jsonify, flash

import local_handlers.local_config_loader as local_config_loader
import local_handlers.local_email_handler as local_email_handler
import local_handlers.local_webhook_handler as local_webhook_handler
import local_handlers.local_authentication_handler as local_authentication_handler

from blueprints.api_ingest import api_ingest_bp
from blueprints.reports_module import reports_module_bp
from blueprints.changes_module import changes_module_bp
from blueprints.itsm_core import itsm_core_bp
from blueprints.itsm_queues import itsm_queues_bp
from blueprints.crm_module import crm_module_bp
from blueprints.hrm_module import hrm_module_bp
from decorators import technician_required, manager_required, admin_required

BUILDID=str("0.1.0")

"""
Rest in Peace Alex, July 2nd 2005 - December 14th 2024
Rest in Peace Dave, August 16th 1967 - December 19th 2025
"""
# Secrets loaded from .env file.
load_dotenv(dotenv_path=".env")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # App Password from Gmail or relevant email provider.
# CF_TURNSTILE_SITE_KEY = os.getenv("CF_TURNSTILE_SITE_KEY") # REQUIRED for CAPTCHA functionality.
# CF_TURNSTILE_SECRET_KEY = os.getenv("CF_TURNSTILE_SECRET_KEY") # REQUIRED for CAPTCHA functionality.
TAILSCALE_NOTIFY_EMAIL = os.getenv("TAILSCALE_NOTIFY_EMAIL")

# Configuration non-secret data loaded from YAML.
core_yaml_config = local_config_loader.load_core_config()
TICKETS_FILE = core_yaml_config["tickets_file"]
EMPLOYEE_FILE = core_yaml_config["employee_file"]
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]
EMAIL_ENABLED = core_yaml_config["email"]["enabled"]
EMAIL_ACCOUNT = core_yaml_config["email"]["account"]
IMAP_SERVER = core_yaml_config["email"]["imap_server"]
SMTP_SERVER = core_yaml_config["email"]["smtp_server"]
SMTP_PORT = core_yaml_config["email"]["smtp_port"]

# Flask App core setup and configuration.
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.getenv("FLASKAPP_SECRET_KEY")
app.permanent_session_lifetime = timedelta(hours=12)

app.config.update(
    SESSION_COOKIE_NAME="gr_desk_session_cookie",
    SESSION_COOKIE_HTTPONLY=True, # XSS Cookie Theft Prevention
    SESSION_COOKIE_SECURE=not app.debug, 
    SESSION_COOKIE_SAMESITE="Lax", # Strict, Lax, None
    SESSION_REFRESH_EACH_REQUEST=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,)

api_ingest_bp.config = {'TAILSCALE_NOTIFY_EMAIL': TAILSCALE_NOTIFY_EMAIL}
app.register_blueprint(api_ingest_bp)
app.register_blueprint(reports_module_bp)
app.register_blueprint(changes_module_bp)
app.register_blueprint(itsm_core_bp)
app.register_blueprint(itsm_queues_bp)
app.register_blueprint(crm_module_bp)
app.register_blueprint(hrm_module_bp)

# Security Headers for all responses.
@app.after_request
def set_security_headers(response):
    # Prevent clickjacking attacks
    response.headers['X-Frame-Options'] = 'DENY'
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enable browser XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Content Security Policy - start restrictive and adjust as needed
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        # "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.bunny.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.bunny.net; "
        "connect-src 'self'; "
        # "frame-src https://challenges.cloudflare.com; "
        "frame-ancestors 'none'"
    )
    # HTTP Strict Transport Security (forces HTTPS) set to 1 Day.
    if not app.debug:
        response.headers['Strict-Transport-Security'] = ('max-age=86400; includeSubDomains; preload')
    
    # Permissions Policy (formerly Feature-Policy)
    response.headers['Permissions-Policy'] = ('geolocation=(), microphone=(), camera=()')
    
    return response

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
""" Above is the default logging configuration.
Debug - Detailed information
Info - Successes
Warning - Unexpected events
Error - Function failures
Critical - Serious application failures
"""
# INITIAL ERROR CODES
# if not CF_TURNSTILE_SITE_KEY or not CF_TURNSTILE_SECRET_KEY:
#     logging.critical("CF_TURNSTILE_SITE_KEY and CF_TURNSTILE_SECRET_KEY must be configured in the .env file. It is required for CAPTCHA functionality.")
#     exit(1) 

#email_thread_enabler_check = os.getenv("EMAIL_ENABLED")
#if email_thread_enabler_check is None:
#    logging.info("EMAIL_ENABLED is not defined. Defaulting to False.")
#    EMAIL_ENABLED = False
#else:
#    EMAIL_ENABLED = email_thread_enabler_check.lower() == "true"
#    logging.info(f"EMAIL_ENABLED is set to {EMAIL_ENABLED}.")

# Read/Loads the ticket file into memory. This is the original load_tickets function that works on Windows and Unix.
def load_tickets():
    try:
        with open(TICKETS_FILE, "r") as tkt_file:
            return json.load(tkt_file)
    except FileNotFoundError:
        logging.critical("Ticket JSON Database file could not be located.")
        exit(1)
    except json.JSONDecodeError:
        logging.error("Ticket JSON Database file is empty or contains invalid JSON. Treating as empty list.")
        return []

# Writes to the ticket file database. Eventually needs file locking for Linux.
def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as tkt_file_write_op:
        json.dump(tickets, tkt_file_write_op, indent=4)
        logging.debug("The Ticket JSON Database file was modified.")

# Read/Loads the employee file into memory.
def load_employees():
    try:
        with open(EMPLOYEE_FILE, "r") as tech_file_read_op:
            return json.load(tech_file_read_op)
    except FileNotFoundError:
        logging.debug("Employee JSON Database file could not be located.")
        return []
    except json.JSONDecodeError:
        logging.error("Employee JSON Database file is empty or contains invalid JSON. Treating as empty list.")
        return []
    
# Helper script for secure password hasing auto-migration.
def save_employees(employees):
    with open(EMPLOYEE_FILE, "w") as emp_file_write_op:
        json.dump(employees, emp_file_write_op, indent=4)
    logging.debug("The Employee JSON Database file was modified.")

# Generate a new ticket number in format TKTyyyy-nnnn
def get_next_ticket_number():
    tickets = load_tickets()
    current_year = datetime.now().year
    # Find max ticket number for current year
    current_year_tickets = [t for t in tickets if t["ticket_number"].startswith(f"TKT{current_year}")]
    next_count = len(current_year_tickets) + 1
    ticket_count = str(next_count).zfill(4)
    return f"TKT-{current_year}-{ticket_count}"

def generate_ticket_number():
    return get_next_ticket_number()

def generate_change_request_number():
    tickets = load_tickets()
    current_year = datetime.now().year
    ticket_count = str(len(tickets) + 1).zfill(4)
    return f"CHG-{current_year}-{ticket_count}"

# Background email inbox monitoring process.
def background_email_monitor():
    while True:
        local_email_handler.fetch_email_replies()
        time.sleep(600)  # Wait for emails every 10 minutes.
#threading.Thread(target=background_email_monitor, daemon=True).start()

if EMAIL_ENABLED is True:
    logging.info("Starting background email monitoring thread...")
    threading.Thread(target=background_email_monitor, daemon=True).start()
else:
    logging.info("EMAIL_ENABLED is set to false. Skipping...")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        try:
            # Cloudflare Turnstile CAPTCHA validation
            # turnstile_token = request.form.get("cf-turnstile-response")
            # if not turnstile_token:
            #     flash("CAPTCHA verification failed. Please try again.", "danger")
            #     return redirect(url_for("home"))
            #
            # turnstile_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
            # turnstile_data = {
            #     "secret": CF_TURNSTILE_SECRET_KEY,
            #     "response": turnstile_token,
            #     "remoteip": request.remote_addr
            # }
            #
            # try:
            #     turnstile_response = requests.post(turnstile_url, data=turnstile_data)
            #     result = turnstile_response.json()
            #     if not result.get("success"):
            #         logging.warning(f"Turnstile verification failed: {result}")
            #         flash("CAPTCHA verification failed. Please try again.", "danger")
            #         return redirect(url_for("home"))
            # except Exception as e:
            #     logging.error(f"Turnstile verification error: {str(e)}")
            #     flash("Error verifying CAPTCHA. Please try again later.", "danger")
            #     return redirect(url_for("home"))

            # Process ticket submission
            ticket_number = generate_ticket_number()

            new_ticket = {
                "uuid": str(uuid.uuid4()),
                "ticket_number": ticket_number,
                "ticket_status": "new",
                "requestor_name": request.form["requestor_name"],
                "requestor_username": request.form.get("requestor_username", ""),
                "requestor_email": request.form["requestor_email"],
                "ticket_type": request.form.get("request_type", "Request"),
                "ticket_subject": request.form["ticket_subject"],
                "ticket_body": request.form["ticket_message"],
                "ticket_impact": int(request.form.get("ticket_impact", 3)),
                "ticket_urgency": int(request.form.get("ticket_urgency", 4)),
                "escalation_level": 0,
                "assigned_team_queue": "support",
                "assigned_support_person": None,
                "ticket_worknotes": [],
                "ticket_created_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ticket_escalation_timestamp": None,
                "ticket_closed_timestamp": None,
                "ticket_acknowledged_timestamp": None,
                "requestor_vip_status": False,
                "ticket_overdue": False
            }

            tickets = load_tickets()
            tickets.append(new_ticket)
            save_tickets(tickets)
            logging.info(f"{ticket_number} has been created.")

            # Send confirmation email to the requestor
            if EMAIL_ENABLED:
                try:
                    email_body = render_template("new-ticket-email.html", ticket=new_ticket)
                    local_email_handler.send_email(
                        new_ticket["requestor_email"],
                        f"{ticket_number} - {new_ticket['ticket_subject']}",
                        email_body,
                        html=True
                    )
                    logging.info(f"Confirmation email for {ticket_number} sent successfully.")
                except Exception as e:
                    logging.error(f"Failed to send email for {ticket_number}: {str(e)}")
            else:
                logging.debug(f"EMAIL_ENABLED is false. Skipping email for {ticket_number}.")

            # Send webhook notifications
            try:
                local_webhook_handler.notify_ticket_event(
                    ticket_number,
                    new_ticket["ticket_subject"],
                    "Open"
                )
                logging.info(f"Webhook notifications for {ticket_number} sent successfully.")
            except Exception as e:
                logging.error(f"Failed to send webhook notifications for {ticket_number}: {str(e)}")

            # Prompt the user's web interface of a successful ticket submission
            flash(f"Ticket {ticket_number} has been submitted successfully!", "success")
            return redirect(url_for("home"))

        except KeyError as e:
            logging.error(f"Missing required form field: {str(e)}")
            flash("Please fill out all required fields.", "danger")
            return redirect(url_for("home"))
        except Exception as e:
            logging.critical(f"Failed to process ticket submission: {str(e)}")
            flash("An error occurred while submitting your ticket. Please try again later.", "danger")
            return redirect(url_for("home"))

    # Refresh and reload the Home/Index
    return render_template("index.html")  # , sitekey=CF_TURNSTILE_SITE_KEY

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("tech_username_box", "").strip()
        password = request.form.get("tech_password_box", "")
        employees = load_employees()
        for employee in employees:
            if employee.get("tech_username") != username:
                continue

            # LEGACY PASSWORD AUTO-MIGRATION
            if "tech_authcode" in employee:
                if password == employee["tech_authcode"]:
                    employee["password_hash"] = local_authentication_handler.hash_password(password)
                    del employee["tech_authcode"]

                    save_employees(employees)

                    session.permanent = True
                    session["technician"] = username
                    logging.info(f"{username} logged in using legacy password and was auto-migrated.")
                    return redirect(url_for("dashboard"))
                # Username matched, legacy password wrong -> stop checking
                break
            # MODERN HASHED PASSWORD CHECK
            stored_hash = employee.get("password_hash")
            if stored_hash and local_authentication_handler.verify_password(password, stored_hash):
                session.permanent = True
                session["technician"] = username
                logging.info(f"{username} logged in successfully.")
                return redirect(url_for("dashboard"))
            # Username matched but password incorrect
            break

        # If we reach here -> authentication failed
        logging.warning(f"Failed login attempt for username: {username}")
        return render_template("login.html", error="Invalid credentials.")

    return render_template("login.html")  # , sitekey=CF_TURNSTILE_SITE_KEY

# Route for rendering the core technician dashboard. Displays all Open and In-Progress tickets.
@app.route("/dashboard")
@technician_required
def dashboard():
    tickets = load_tickets()
    # Filter to show only open tickets (new, in_progress, on_hold)
    open_tickets = [ticket for ticket in tickets if ticket.get("ticket_status") in ["new", "in_progress", "on_hold", "Open"]]
    return render_template("dashboard.html", tickets=open_tickets, loggedInTech=session["technician"], BUILDID=BUILDID)

# Route for viewing a ticket in the Ticket Commander view.
@app.route("/ticket/<ticket_number>")
@technician_required
def ticket_detail(ticket_number):
    tickets = load_tickets()
    ticket = next((t for t in tickets if t["ticket_number"] == ticket_number), None)
    
    if ticket:
        return render_template("ticket-commander.html", ticket=ticket, loggedInTech=session["technician"])

    return render_template("404.html"), 404

# Route for updating a ticket. Called from Dashboard and Ticket Commander.
@app.route("/ticket/<ticket_number>/update_status/<ticket_status>", methods=["POST"])
@technician_required
def update_ticket_status(ticket_number, ticket_status):
    if not session.get("technician"):
        return render_template("403.html"), 403

    valid_statuses = ["new", "in_progress", "on_hold", "closed", "cancelled"]
    if ticket_status not in valid_statuses:
        return render_template("400.html"), 400

    loggedInTech = session["technician"]
    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] == ticket_number:
            # Extract subject for webhook notifications
            ticket_subject = ticket.get("ticket_subject", "No Subject Provided")
            # Update ticket in memory
            ticket["ticket_status"] = ticket_status

            if ticket_status == "closed":
                ticket["ticket_closed_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if ticket_status == "in_progress":
                ticket["ticket_acknowledged_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            save_tickets(tickets)
            logging.info(f"Ticket {ticket_number} status updated to {ticket_status} by {loggedInTech}.")
            # Send webhook notifications for status update.
            try:
                local_webhook_handler.notify_ticket_event(ticket_number=ticket_number, ticket_status=ticket_status, ticket_subject=ticket_subject)
                logging.info(f"Ticket {ticket_number} status update notifications sent successfully.")
            except Exception as e:
                logging.error(f"Failed to send ticket status update notifications for {ticket_number}: {str(e)}")

            return jsonify({"message": f"Ticket {ticket_number} updated to {ticket_status}."})

    return render_template("404.html"), 404

# Route for appending a new note to a ticket.
@app.route("/ticket/<ticket_number>/append_note", methods=["POST"])
@technician_required
def add_ticket_note(ticket_number):
    new_tkt_note = request.form.get("note_content")

    if not new_tkt_note:
        return jsonify({"message": "Note Contents cannot be empty!"}), 400

    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] == ticket_number:
            ticket["ticket_worknotes"].append(new_tkt_note)
            save_tickets(tickets)
            logging.info(f"Note successfully appended to {ticket_number}.")
            return jsonify({"message": "Note added successfully."}), 200

    return jsonify({"message": "Ticket not found."}), 404

# ABOVE THIS LINE SHOULD ONLY BE TECHNICIAN/TICKETING PAGES ONLY!

# Thanks to Claude Sonnet 4.5, API Ingest has moved to ./blueprints/reports_module.py

# BELOW THIS LINE IS RESERVED FOR LOGOUT AND API INGEST ROUTES ONLY!
# Removes the session cookie from the user browser, sending the Technician/user back to the login page.

# Thanks to Claude Sonnet 4.5, API Ingest has moved to ./blueprints/api_ingest.py

@app.route("/logout")
def logout():
    session.pop("technician", None)
    return redirect(url_for("login"))

# BELOW THIS LINE IS RESERVED FOR FLASK ERROR ROUTES. PUT ALL CORE APP FUNCTIONS ABOVE THIS LINE!
# Handle 400 errors.
@app.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400

# Handle 403 errors.
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

# Handle 404 errors.
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Handles 500 errors.
@app.errorhandler(500)
def internal_server_error(e):
    logging.critical(f"Internal Server Error: {str(e)}")
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(debug=True) #debug=True
