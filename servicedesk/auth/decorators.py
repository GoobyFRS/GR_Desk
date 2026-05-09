"""Authorization decorators for role-based access control."""

from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from flask import flash, redirect, url_for
from flask_login import current_user, login_required

P = ParamSpec("P")
R = TypeVar("R")


def role_required(
    *roles: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to require specific roles for a view.

    Args:
        *roles: Allowed role names (e.g., "admin", "technician").

    Returns:
        Decorated function that checks user role.

    Example:
        @role_required("admin", "technician")
        def protected_view():
            ...
    """

    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        @login_required
        def decorated_function(*args: P.args, **kwargs: P.kwargs) -> R:
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("public.login"))  # type: ignore[return-value]

            user_role = getattr(current_user, "employee_access_role", "none")

            if user_role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("public.index"))  # type: ignore[return-value]

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f: Callable[P, R]) -> Callable[P, R]:
    """Decorator to require admin role.

    Args:
        f: The view function to protect.

    Returns:
        Decorated function that checks for admin role.

    Example:
        @admin_required
        def admin_only_view():
            ...
    """

    @wraps(f)
    @login_required
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> R:
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("public.login"))  # type: ignore[return-value]

        if not getattr(current_user, "is_admin", False):
            flash("Admin access required.", "danger")
            return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]

        return f(*args, **kwargs)

    return decorated_function


def technician_required(f: Callable[P, R]) -> Callable[P, R]:
    """Decorator to require technician or admin role.

    Args:
        f: The view function to protect.

    Returns:
        Decorated function that checks for technician role.

    Example:
        @technician_required
        def tech_view():
            ...
    """

    @wraps(f)
    @login_required
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> R:
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("public.login"))  # type: ignore[return-value]

        if not getattr(current_user, "is_technician", False):
            flash("Technician access required.", "danger")
            return redirect(url_for("public.index"))  # type: ignore[return-value]

        return f(*args, **kwargs)

    return decorated_function


def setup_required(f: Callable[P, R]) -> Callable[P, R]:
    """Decorator to redirect to setup if no employees exist.

    Args:
        f: The view function to wrap.

    Returns:
        Decorated function that checks for initial setup.
    """

    @wraps(f)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> R:
        from flask import current_app

        from servicedesk.storage.yaml_store import YamlStore
        from servicedesk.models.employee import Employee

        data_path = current_app.config["DATA_PATH"]
        store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

        if store.is_empty():
            return redirect(url_for("setup.wizard"))  # type: ignore[return-value]

        return f(*args, **kwargs)

    return decorated_function
