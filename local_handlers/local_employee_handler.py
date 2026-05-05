#!/usr/bin/env python3
import json
import uuid
from datetime import datetime
import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
EMPLOYEES_FILE = core_config.get("employee_file", "./my_data/employees.json")

def load_employees():
    try:
        with open(EMPLOYEES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def save_employees(employees):
    with open(EMPLOYEES_FILE, "w") as f:
        json.dump(employees, f, indent=4)

def get_next_employee_id(): # Used to Generate Employee IDs
    employees = load_employees()
    return f"EMP{str(len(employees) + 1).zfill(4)}"

def create_employee(employee_first_name, employee_last_name, employee_contact_email, **kwargs):
    employee = {
        "uuid": str(uuid.uuid4()),
        "employee_id": get_next_employee_id(),
        "employee_first_name": employee_first_name,
        "employee_last_name": employee_last_name,
        "employee_preferred_name": kwargs.get("employee_preferred_name", employee_first_name),
        "employee_age": kwargs.get("employee_age"),
        "employee_dob": kwargs.get("employee_dob"),
        "employee_state": kwargs.get("employee_state"),
        "employee_ingame_username": kwargs.get("employee_ingame_username", ""),
        "employee_chat_userid": kwargs.get("employee_chat_userid"),
        "employee_hire_date": kwargs.get("employee_hire_date", datetime.now().strftime("%Y-%m-%d")),
        "employee_termination_date": kwargs.get("employee_termination_date"),
        "rehire_status": kwargs.get("rehire_status", "yes"),
        "employee_role": kwargs.get("employee_role", "technician"),
        "employee_compensation": kwargs.get("employee_compensation"),
        "salary_exempt": kwargs.get("salary_exempt", False),
        "is_bonus_eligible": kwargs.get("is_bonus_eligible", False),
        "bonus_rate": kwargs.get("bonus_rate", 0),
        "assigned_business_unit": kwargs.get("assigned_business_unit", "support"),
        "access_role": kwargs.get("access_role", "technician"),
        "employee_pip_count": kwargs.get("employee_pip_count", 0),
        "has_active_pip": kwargs.get("has_active_pip", False),
        "is_on_probation": kwargs.get("is_on_probation", False),
        "total_pto_available": kwargs.get("total_pto_available", 0),
        "reports_to": kwargs.get("reports_to"),
        "tech_username": kwargs.get("tech_username"),
        "password_hash": kwargs.get("password_hash"),
        "employee_contact_email": employee_contact_email
    }
    return employee

def find_employee_by_uuid(employee_uuid):
    employees = load_employees()
    return next((e for e in employees if e["uuid"] == employee_uuid), None)

def find_employee_by_username(username):
    employees = load_employees()
    return next((e for e in employees if e.get("tech_username") == username), None)

def update_employee(employee_uuid, updates):
    employees = load_employees()
    for employee in employees:
        if employee["uuid"] == employee_uuid:
            employee.update(updates)
            save_employees(employees)
            return True
    return False

def get_all_managers():
    employees = load_employees()
    return [e for e in employees if e.get("access_role") in ["manager", "admin"]]
