#!/usr/bin/env python3
from flask import session, render_template
from functools import wraps
import local_handlers.local_employee_handler as local_employee_handler

def technician_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("technician"):
            return render_template("403.html"), 403
        return func(*args, **kwargs)
    return wrapper

def manager_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("technician"):
            return render_template("403.html"), 403

        username = session["technician"]
        employee = local_employee_handler.find_employee_by_username(username)

        if not employee or employee.get("access_role") not in ["manager", "admin"]:
            return render_template("403.html"), 403

        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("technician"):
            return render_template("403.html"), 403

        username = session["technician"]
        employee = local_employee_handler.find_employee_by_username(username)

        if not employee or employee.get("access_role") != "admin":
            return render_template("403.html"), 403

        return func(*args, **kwargs)
    return wrapper

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("technician"):
                return render_template("403.html"), 403

            username = session["technician"]
            employee = local_employee_handler.find_employee_by_username(username)

            if not employee or employee.get("access_role") != required_role:
                return render_template("403.html"), 403

            return func(*args, **kwargs)
        return wrapper
    return decorator
