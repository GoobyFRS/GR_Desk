#!/usr/bin/env python3
"""Employee management and data persistence.

Handles all employee/technician operations including creation, retrieval,
and updates. Employees are stored as JSON records with role-based access
control, compensation tracking, and service access permissions.
"""

__all__ = [
    "load_employees",
    "save_employees",
    "create_employee",
    "find_employee_by_uuid",
    "find_employee_by_username",
    "update_employee",
    "get_all_managers",
    "generate_employee_id",
]

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
EMPLOYEES_FILE: str = core_config.get(
    "employee_file", "./my_data/employees.json"
)

# Constants
EMPLOYEE_ID_PREFIX: str = "EM"
VALID_ACCESS_ROLES: list[str] = ["technician", "manager", "admin"]
VALID_EMPLOYMENT_STATUSES: list[str] = ["active", "inactive", "terminated", "on_leave"]


def load_employees() -> list[dict[str, Any]]:
    """Load all employees from JSON storage.

    Returns:
        List of employee dictionaries. Empty list if file missing or invalid.
    """
    employees_path = Path(EMPLOYEES_FILE)

    if not employees_path.exists():
        return []

    try:
        with open(employees_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_employees(employees: list[dict[str, Any]]) -> None:
    """Persist employees to JSON storage.

    Args:
        employees: List of employee dictionaries to save.
    """
    employees_path = Path(EMPLOYEES_FILE)
    employees_path.parent.mkdir(parents=True, exist_ok=True)

    with open(employees_path, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=4)


def generate_employee_id() -> str:
    """Generate next sequential employee ID.

    Returns:
        Employee ID in format 'EM-YYYY-NNNN' (e.g., 'EM-2025-0001').
    """
    employees = load_employees()
    current_year = datetime.now().year

    year_employees = [
        e for e in employees
        if e.get("employee_id", "").startswith(f"{EMPLOYEE_ID_PREFIX}-{current_year}-")
    ]

    next_number = len(year_employees) + 1
    return f"{EMPLOYEE_ID_PREFIX}-{current_year}-{next_number:04d}"


def create_employee(
    employee_first_name: str,
    employee_last_name: str,
    employee_email: str,
    employee_username: str,
    password_hash: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new employee record.

    Args:
        employee_first_name: Employee's first name.
        employee_last_name: Employee's last name.
        employee_email: Email address for communications.
        employee_username: Username for login authentication.
        password_hash: Bcrypt-hashed password.
        **kwargs: Optional fields for employee record.

    Returns:
        Dictionary representing the new employee record with UUID and
        auto-generated employee_id.
    """
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_date = datetime.now().strftime("%Y-%m-%d")

    return {
        # Identity
        "uuid": str(uuid.uuid4()),
        "employee_id": generate_employee_id(),
        "employee_first_name": employee_first_name,
        "employee_last_name": employee_last_name,
        "employee_preferred_name": kwargs.get(
            "employee_preferred_name", employee_first_name
        ),
        "employee_dob": kwargs.get("employee_dob"),
        # Contact
        "employee_email": employee_email,
        "employee_phone": kwargs.get("employee_phone"),
        "employee_timezone": kwargs.get("employee_timezone", "UTC"),
        # Online Identities
        "employee_ingame_username": kwargs.get("employee_ingame_username"),
        "employee_chat_userid": kwargs.get("employee_chat_userid"),
        # Employment
        "employee_hire_date": kwargs.get("employee_hire_date", current_date),
        "employee_termination_date": kwargs.get("employee_termination_date"),
        "employment_status": kwargs.get("employment_status", "active"),
        "rehire_status": kwargs.get("rehire_status", "yes"),
        "employee_role": kwargs.get("employee_role", "technician"),
        # Compensation
        "compensation_type": kwargs.get("compensation_type", "hourly"),
        "base_salary": kwargs.get("base_salary"),
        "hourly_rate": kwargs.get("hourly_rate"),
        "salary_exempt": kwargs.get("salary_exempt", "no"),
        "is_bonus_eligible": kwargs.get("is_bonus_eligible", "no"),
        "bonus_rate": kwargs.get("bonus_rate", 0),
        # Organization
        "assigned_business_unit": kwargs.get("assigned_business_unit", "support"),
        "access_role": kwargs.get("access_role", "technician"),
        "total_pto_available": kwargs.get("total_pto_available", 0),
        "reports_to": kwargs.get("reports_to"),
        # Authentication
        "employee_username": employee_username,
        "password_hash": password_hash,
        "mfa_enabled": kwargs.get("mfa_enabled", False),
        "last_login": None,
        "password_last_changed": current_timestamp,
        "account_locked": kwargs.get("account_locked", True),
        "failed_login_attempts": 0,
        # Service Access
        "has_freshrss_access": kwargs.get("has_freshrss_access", False),
        "has_jellyfin_access": kwargs.get("has_jellyfin_access", False),
        "has_nextcloud_access": kwargs.get("has_nextcloud_access", False),
        "has_tailnet_access": kwargs.get("has_tailnet_access", False),
        "has_gitea_access": kwargs.get("has_gitea_access", False),
        "has_discord_access": kwargs.get("has_discord_access", False),
        "has_slack_access": kwargs.get("has_slack_access", False),
    }


def find_employee_by_uuid(employee_uuid: str) -> dict[str, Any] | None:
    """Find an employee by their UUID.

    Args:
        employee_uuid: The UUID to search for.

    Returns:
        Employee dictionary if found, None otherwise.
    """
    employees = load_employees()

    for employee in employees:
        if employee.get("uuid") == employee_uuid:
            return employee

    return None


def find_employee_by_username(username: str) -> dict[str, Any] | None:
    """Find an employee by their username.

    Args:
        username: The employee username to search for.

    Returns:
        Employee dictionary if found, None otherwise.
    """
    employees = load_employees()

    for employee in employees:
        if employee.get("employee_username") == username:
            return employee

    return None


def find_employee_by_id(employee_id: str) -> dict[str, Any] | None:
    """Find an employee by their employee ID.

    Args:
        employee_id: The employee ID (EM-YYYY-NNNN) to search for.

    Returns:
        Employee dictionary if found, None otherwise.
    """
    employees = load_employees()

    for employee in employees:
        if employee.get("employee_id") == employee_id:
            return employee

    return None


def update_employee(employee_uuid: str, updates: dict[str, Any]) -> bool:
    """Update an existing employee record.

    Args:
        employee_uuid: The UUID of the employee to update.
        updates: Dictionary of fields to update.

    Returns:
        True if update was successful, False if employee not found.
    """
    employees = load_employees()

    # Protected fields that should not be updated directly
    protected_fields = {"uuid", "employee_id"}

    for employee in employees:
        if employee.get("uuid") != employee_uuid:
            continue

        for key, value in updates.items():
            if key in protected_fields:
                continue
            employee[key] = value

        save_employees(employees)
        return True

    return False


def get_all_managers() -> list[dict[str, Any]]:
    """Get all employees with manager or admin access role.

    Returns:
        List of employee dictionaries with access_role of 'manager' or 'admin'.
    """
    employees = load_employees()
    return [
        e for e in employees
        if e.get("access_role") in ["manager", "admin"]
    ]


def record_login_attempt(username: str, success: bool) -> None:
    """Record a login attempt for an employee.

    Args:
        username: The username that attempted to log in.
        success: Whether the login was successful.
    """
    employees = load_employees()

    for employee in employees:
        if employee.get("employee_username") != username:
            continue

        if success:
            employee["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            employee["failed_login_attempts"] = 0
        else:
            employee["failed_login_attempts"] = employee.get(
                "failed_login_attempts", 0
            ) + 1
            # Lock account after 5 failed attempts
            if employee["failed_login_attempts"] >= 5:
                employee["account_locked"] = True

        save_employees(employees)
        return
