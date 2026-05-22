"""Input validation utilities for the Service Desk application.

This module provides validation functions with proper assertions
following the Power of 10 rules for high assertion density.
"""

from __future__ import annotations

import re

# Maximum lengths for string inputs (prevent memory exhaustion)
MAX_NAME_LENGTH: int = 100
MAX_EMAIL_LENGTH: int = 254  # RFC 5321
MAX_SUBJECT_LENGTH: int = 200
MAX_BODY_LENGTH: int = 50000
MAX_FIELD_LENGTH: int = 500

# Email regex pattern (RFC 5322 simplified)
EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_required_string(
    value: str | None,
    field_name: str,
    max_length: int = MAX_FIELD_LENGTH,
) -> str:
    """Validate a required string field.

    Args:
        value: The string value to validate.
        field_name: Name of the field for error messages.
        max_length: Maximum allowed length.

    Returns:
        The stripped and validated string.

    Raises:
        ValueError: If validation fails.
    """
    # Preconditions
    assert field_name, "field_name cannot be empty"
    assert max_length > 0, "max_length must be positive"

    if value is None:
        raise ValueError(f"{field_name} is required")

    stripped = value.strip()

    if not stripped:
        raise ValueError(f"{field_name} is required")

    if len(stripped) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length}")

    # Postcondition
    assert len(stripped) <= max_length, "Result exceeds max length"

    return stripped


def validate_optional_string(
    value: str | None,
    field_name: str,
    max_length: int = MAX_FIELD_LENGTH,
) -> str:
    """Validate an optional string field.

    Args:
        value: The string value to validate.
        field_name: Name of the field for error messages.
        max_length: Maximum allowed length.

    Returns:
        The stripped string or empty string if None.

    Raises:
        ValueError: If validation fails.
    """
    # Preconditions
    assert field_name, "field_name cannot be empty"
    assert max_length > 0, "max_length must be positive"

    if value is None:
        return ""

    stripped = value.strip()

    if len(stripped) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length}")

    # Postcondition
    assert len(stripped) <= max_length, "Result exceeds max length"

    return stripped


def validate_email(value: str | None, required: bool = True) -> str:
    """Validate an email address.

    Args:
        value: The email address to validate.
        required: Whether the field is required.

    Returns:
        The validated and normalized email address.

    Raises:
        ValueError: If validation fails.
    """
    if value is None or not value.strip():
        if required:
            raise ValueError("Email is required")
        return ""

    email = value.strip().lower()

    # Length check (RFC 5321)
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email exceeds maximum length of {MAX_EMAIL_LENGTH}")

    # Format validation
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")

    # Basic structure check
    parts = email.split("@")
    assert len(parts) == 2, "Email must have exactly one @ symbol"

    local, domain = parts
    if len(local) > 64:  # RFC 5321 local part limit
        raise ValueError("Email local part too long")

    # Postcondition
    assert "@" in email, "Valid email must contain @"

    return email


def validate_password(
    password: str | None,
    min_length: int = 8,
    require_confirmation: bool = True,
    confirmation: str | None = None,
) -> str:
    """Validate a password.

    Args:
        password: The password to validate.
        min_length: Minimum required length.
        require_confirmation: Whether to check confirmation.
        confirmation: The confirmation password.

    Returns:
        The validated password.

    Raises:
        ValueError: If validation fails.
    """
    # Preconditions
    assert min_length >= 8, "Minimum password length should be at least 8"

    if not password:
        raise ValueError("Password is required")

    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters")

    if require_confirmation and password != confirmation:
        raise ValueError("Passwords do not match")

    return password


def validate_choice(
    value: str | None,
    choices: list[str],
    field_name: str,
    default: str | None = None,
) -> str:
    """Validate a value against a list of allowed choices.

    Args:
        value: The value to validate.
        choices: List of allowed values.
        field_name: Name of the field for error messages.
        default: Default value if input is None or empty.

    Returns:
        The validated choice.

    Raises:
        ValueError: If validation fails.
    """
    # Preconditions
    assert choices, "choices list cannot be empty"
    assert field_name, "field_name cannot be empty"

    if value is None or not value.strip():
        if default is not None:
            assert default in choices, "default must be in choices"
            return default
        raise ValueError(f"{field_name} is required")

    stripped = value.strip()

    if stripped not in choices:
        raise ValueError(f"Invalid {field_name}: {stripped}")

    return stripped


def validate_positive_float(
    value: str | float | None,
    field_name: str,
    allow_zero: bool = True,
) -> float:
    """Validate a positive float value.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        allow_zero: Whether to allow zero.

    Returns:
        The validated float.

    Raises:
        ValueError: If validation fails.
    """
    # Preconditions
    assert field_name, "field_name cannot be empty"

    if value is None or value == "":
        return 0.0

    try:
        result = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{field_name} must be a number") from e

    if result < 0:
        raise ValueError(f"{field_name} cannot be negative")

    if not allow_zero and result == 0:
        raise ValueError(f"{field_name} must be greater than zero")

    # Postcondition
    assert result >= 0, "Result must be non-negative"

    return result


def collect_validation_errors(validators: list[tuple[str, callable]]) -> list[str]:
    """Run multiple validators and collect all errors.

    Args:
        validators: List of (field_name, validator_callable) tuples.

    Returns:
        List of error messages (empty if all valid).
    """
    errors: list[str] = []

    for field_name, validator in validators:
        try:
            validator()
        except ValueError as e:
            errors.append(str(e))

    return errors
