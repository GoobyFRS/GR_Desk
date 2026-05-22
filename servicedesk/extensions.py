"""Flask extensions initialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask_login import LoginManager

if TYPE_CHECKING:
    from servicedesk.models.employee import Employee

login_manager: LoginManager = LoginManager()
login_manager.login_view = "public.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str) -> Employee | None:
    """Load user by ID for Flask-Login.

    Args:
        user_id: The employee UUID.

    Returns:
        Employee instance or None if not found.
    """
    from flask import current_app

    from servicedesk.storage.yaml_store import YamlStore
    from servicedesk.models.employee import Employee

    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(
        data_path / "employees.yaml",
        Employee,
    )
    return store.get_by_id(user_id)
