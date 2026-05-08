#!/usr/bin/env python3
"""Role-based access control decorators for Flask route protection.

Provides decorators for enforcing technician, manager, and admin-level
authorization checks on Flask routes. Decorators verify session user
exists and has the required access role before allowing route execution.
"""

from functools import wraps
from typing import Any, Callable, TypeVar

from flask import render_template, session

import local_handlers.local_employee_handler as local_employee_handler

F = TypeVar("F", bound=Callable[..., Any])


def technician_required(func: F) -> F:
    """Require active technician session to access route.

    Checks that a 'technician' key exists in Flask session.
    If not, returns 403 Forbidden response.

    Args:
        func: The Flask route handler to wrap.

    Returns:
        Wrapped function that enforces session requirement.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not session.get("technician"):
            return render_template("403.html"), 403
        return func(*args, **kwargs)

    return wrapper  # type: ignore


def manager_required(func: F) -> F:
    """Require manager or admin access role to access route.

    Checks that a technician session exists and has access_role
    of 'manager' or 'admin'. If not, returns 403 Forbidden response.

    Args:
        func: The Flask route handler to wrap.

    Returns:
        Wrapped function that enforces manager+ authorization.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not session.get("technician"):
            return render_template("403.html"), 403

        username = session["technician"]
        employee = local_employee_handler.find_employee_by_username(username)

        if (
            not employee
            or employee.get("access_role") not in ["manager", "admin"]
        ):
            return render_template("403.html"), 403

        return func(*args, **kwargs)

    return wrapper  # type: ignore


def admin_required(func: F) -> F:
    """Require admin access role to access route.

    Checks that a technician session exists and has access_role
    of 'admin'. If not, returns 403 Forbidden response.

    Args:
        func: The Flask route handler to wrap.

    Returns:
        Wrapped function that enforces admin-only authorization.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not session.get("technician"):
            return render_template("403.html"), 403

        username = session["technician"]
        employee = local_employee_handler.find_employee_by_username(username)

        if not employee or employee.get("access_role") != "admin":
            return render_template("403.html"), 403

        return func(*args, **kwargs)

    return wrapper  # type: ignore


def role_required(required_role: str) -> Callable[[F], F]:
    """Require a specific access role to access route.

    Returns a decorator that checks for a specific access_role value.
    If the technician session doesn't exist or has a different role,
    returns 403 Forbidden response.

    Args:
        required_role: The required access_role value (e.g., 'technician',
            'manager', 'admin').

    Returns:
        A decorator function for Flask route handlers.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not session.get("technician"):
                return render_template("403.html"), 403

            username = session["technician"]
            employee = (
                local_employee_handler.find_employee_by_username(username)
            )

            if (
                not employee
                or employee.get("access_role") != required_role
            ):
                return render_template("403.html"), 403

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
