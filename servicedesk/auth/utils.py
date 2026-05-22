"""Password hashing and authentication utilities."""

from __future__ import annotations

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    """Hash a password using werkzeug's secure method.

    Args:
        password: Plain text password.

    Returns:
        Hashed password string.

    Raises:
        ValueError: If password is empty or too short.
    """
    assert password, "Password cannot be empty"

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    return generate_password_hash(password, method="scrypt")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: Plain text password to verify.
        password_hash: Stored password hash.

    Returns:
        True if password matches, False otherwise.
    """
    if not password or not password_hash:
        return False

    return check_password_hash(password_hash, password)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format.

    Returns:
        Current timestamp string.
    """
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def validate_email(email: str) -> bool:
    """Basic email validation.

    Args:
        email: Email address to validate.

    Returns:
        True if email appears valid, False otherwise.
    """
    if not email:
        return False

    # Basic validation: contains @ and has parts before and after
    parts = email.split("@")
    if len(parts) != 2:
        return False

    local, domain = parts
    if not local or not domain:
        return False

    if "." not in domain:
        return False

    return True
