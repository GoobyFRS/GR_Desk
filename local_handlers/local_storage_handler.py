#!/usr/bin/env python3
"""Centralized data persistence for tickets and employees.

This module handles all file I/O operations for tickets and employees,
eliminating circular dependencies. All modules should import from here
for ticket/employee access rather than loading files independently.
"""

__all__ = [
    "load_tickets",
    "save_tickets",
    "load_employees",
    "save_employees",
    "generate_ticket_number",
    "generate_change_request_number",
]

import json
import logging
import sys
from datetime import datetime
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
TICKETS_FILE: str = core_config.get("tickets_file", "./my_data/tickets.json")
EMPLOYEE_FILE: str = core_config.get(
    "employee_file", "./my_data/employees.json"
)

LOG_LEVEL: str = core_config.get("logging", {}).get("level", "INFO")
LOG_FILE: str = core_config.get("logging", {}).get("file", "app.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_tickets() -> list[dict[str, Any]]:
    """Load all tickets from JSON storage.

    Reads the tickets database file and returns all tickets.

    Returns:
        List of ticket dictionaries.

    Raises:
        SystemExit: If the tickets file does not exist (critical error).
    """
    try:
        with open(TICKETS_FILE, "r") as tkt_file:
            return json.load(tkt_file)
    except FileNotFoundError:
        logging.critical(
            f"Ticket JSON Database file could not be located at {TICKETS_FILE}."
        )
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(
            "Ticket JSON Database file is empty or contains invalid JSON. "
            "Treating as empty list."
        )
        return []


def save_tickets(tickets: list[dict[str, Any]]) -> None:
    """Persist tickets to JSON storage.

    Args:
        tickets: List of ticket dictionaries to save.
    """
    with open(TICKETS_FILE, "w") as tkt_file_write_op:
        json.dump(tickets, tkt_file_write_op, indent=4)
    logging.debug("The Ticket JSON Database file was modified.")


def load_employees() -> list[dict[str, Any]]:
    """Load all employees from JSON storage.

    Reads the employees database file and returns all employee records.

    Returns:
        List of employee dictionaries. Empty list if file not found or invalid.
    """
    try:
        with open(EMPLOYEE_FILE, "r") as tech_file_read_op:
            return json.load(tech_file_read_op)
    except FileNotFoundError:
        logging.debug(
            f"Employee JSON Database file could not be located at {EMPLOYEE_FILE}."
        )
        return []
    except json.JSONDecodeError:
        logging.error(
            "Employee JSON Database file is empty or contains invalid JSON. "
            "Treating as empty list."
        )
        return []


def save_employees(employees: list[dict[str, Any]]) -> None:
    """Persist employees to JSON storage.

    Args:
        employees: List of employee dictionaries to save.
    """
    with open(EMPLOYEE_FILE, "w") as emp_file_write_op:
        json.dump(employees, emp_file_write_op, indent=4)
    logging.debug("The Employee JSON Database file was modified.")


def generate_ticket_number() -> str:
    """Generate a new unique ticket number.

    Generates ticket numbers in format TKT-YYYY-NNNN where YYYY is
    the current year and NNNN is a zero-padded sequence number.

    Returns:
        New ticket number string (e.g., 'TKT-2025-0042').
    """
    tickets = load_tickets()
    current_year = datetime.now().year
    # Find all ticket numbers for current year
    current_year_tickets = [
        t
        for t in tickets
        if t.get("ticket_number", "").startswith(f"TKT-{current_year}-")
    ]
    next_count = len(current_year_tickets) + 1
    ticket_count = str(next_count).zfill(4)
    return f"TKT-{current_year}-{ticket_count}"


def generate_change_request_number() -> str:
    """Generate a new unique change request number.

    Generates change request numbers in format CHG-YYYY-NNNN where YYYY is
    the current year and NNNN is a zero-padded sequence number.

    Returns:
        New change request number string (e.g., 'CHG-2025-0005').
    """
    tickets = load_tickets()
    current_year = datetime.now().year
    ticket_count = str(len(tickets) + 1).zfill(4)
    return f"CHG-{current_year}-{ticket_count}"
