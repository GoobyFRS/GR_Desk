#!/usr/bin/env python3
"""Employee management and data persistence.

Handles all employee/technician operations including creation, retrieval,
and updates. Employees are stored as JSON records with role-based access
control, compensation tracking, and performance management fields.
"""

import json
import uuid
from datetime import datetime
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
EMPLOYEES_FILE: str = core_config.get(
    "employee_file", "./my_data/employees.json"
)


def load_employees() -> list[dict[str, Any]]:
    """Load all employees from JSON storage.

    Returns:
        List of employee dictionaries. Empty list if file missing or invalid.
    """
    try:
        with open(EMPLOYEES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_employees(employees: list[dict[str, Any]]) -> None:
    """Persist employees to JSON storage.

    Args:
        employees: List of employee dictionaries to save.
    """
    with open(EMPLOYEES_FILE, "w") as f:
        json.dump(employees, f, indent=4)


def get_next_employee_id() -> str:
    """Generate next sequential employee ID.

    Returns:
        Employee ID in format 'EMP####' (e.g., 'EMP0001').
    """
    employees = load_employees()
    return f"EMP{str(len(employees) + 1).zfill(4)}"


def create_employee(
    employee_first_name: str,
    employee_last_name: str,
    employee_contact_email: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new employee record.

    Args:
        employee_first_name: Employee's first name.
        employee_last_name: Employee's last name.
        employee_contact_email: Email address for communications.
        **kwargs: Optional fields including employee_preferred_name,
            employee_age, employee_dob, employee_state, employee_role,
            access_role, tech_username, password_hash, total_pto_available,
            and compensation/benefits fields.

    Returns:
        Dictionary representing the new employee record with UUID and
        auto-generated employee_id.
    """
    employee: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "employee_id": get_next_employee_id(),
        "employee_first_name": employee_first_name,
        "employee_last_name": employee_last_name,
        "employee_preferred_name": kwargs.get(
            "employee_preferred_name", employee_first_name
        ),
        "employee_age": kwargs.get("employee_age"),
        "employee_dob": kwargs.get("employee_dob"),
        "employee_state": kwargs.get("employee_state"),
        "employee_ingame_username": kwargs.get("employee_ingame_username", ""),
        "employee_chat_userid": kwargs.get("employee_chat_userid"),
        "employee_hire_date": kwargs.get(
            "employee_hire_date", datetime.now().strftime("%Y-%m-%d")
        ),
        "employee_termination_date": kwargs.get("employee_termination_date"),
        "rehire_status": kwargs.get("rehire_status", "yes"),
        "employee_role": kwargs.get("employee_role", "technician"),
        "employee_compensation": kwargs.get("employee_compensation"),
        "salary_exempt": kwargs.get("salary_exempt", False),
        "is_bonus_eligible": kwargs.get("is_bonus_eligible", False),
        "bonus_rate": kwargs.get("bonus_rate", 0),
        "assigned_business_unit": kwargs.get(
            "assigned_business_unit", "support"
        ),
        "access_role": kwargs.get("access_role", "technician"),
        "employee_pip_count": kwargs.get("employee_pip_count", 0),
        "has_active_pip": kwargs.get("has_active_pip", False),
        "is_on_probation": kwargs.get("is_on_probation", False),
        "total_pto_available": kwargs.get("total_pto_available", 0),
        "reports_to": kwargs.get("reports_to"),
        "tech_username": kwargs.get("tech_username"),
        "password_hash": kwargs.get("password_hash"),
        "employee_contact_email": employee_contact_email,
    }
    return employee


def find_employee_by_uuid(employee_uuid: str) -> dict[str, Any] | None:
    """Find an employee by their UUID.

    Args:
        employee_uuid: The UUID to search for.

    Returns:
        Employee dictionary if found, None otherwise.
    """
    employees = load_employees()
    return next(
        (e for e in employees if e.get("uuid") == employee_uuid), None
    )


def find_employee_by_username(username: str) -> dict[str, Any] | None:
    """Find an employee by their tech username.

    Args:
        username: The tech username to search for.

    Returns:
        Employee dictionary if found, None otherwise.
    """
    employees = load_employees()
    return next(
        (e for e in employees if e.get("tech_username") == username), None
    )


def update_employee(
    employee_uuid: str, updates: dict[str, Any]
) -> bool:
    """Update an existing employee record.

    Args:
        employee_uuid: The UUID of the employee to update.
        updates: Dictionary of fields to update.

    Returns:
        True if update was successful, False if employee not found.
    """
    employees = load_employees()
    for employee in employees:
        if employee.get("uuid") == employee_uuid:
            employee.update(updates)
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
        e
        for e in employees
        if e.get("access_role") in ["manager", "admin"]
    ]
