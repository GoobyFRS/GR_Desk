#!/usr/bin/env python3
"""Customer management and data persistence.

Handles all customer-related operations including creation, retrieval,
and updates. Customers are stored as JSON records with metadata for
account management, support tracking, and VIP status.
"""

__all__ = [
    "load_customers",
    "save_customers",
    "create_customer",
    "find_customer_by_uuid",
    "find_customer_by_id",
    "update_customer",
    "generate_customer_id",
]

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
CUSTOMERS_FILE: str = core_config.get(
    "customers_file", "./my_data/customers.json"
)

# Constants
CUSTOMER_ID_PREFIX: str = "CID"
VALID_ACCOUNT_STATUSES: list[str] = ["active", "inactive", "suspended", "closed"]
VALID_FRAUD_RISKS: list[str] = ["low", "medium", "high", "critical"]


def load_customers() -> list[dict[str, Any]]:
    """Load all customers from JSON storage.

    Returns:
        List of customer dictionaries. Empty list if file missing or invalid.
    """
    customers_path = Path(CUSTOMERS_FILE)

    if not customers_path.exists():
        return []

    try:
        with open(customers_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_customers(customers: list[dict[str, Any]]) -> None:
    """Persist customers to JSON storage.

    Args:
        customers: List of customer dictionaries to save.
    """
    customers_path = Path(CUSTOMERS_FILE)
    customers_path.parent.mkdir(parents=True, exist_ok=True)

    with open(customers_path, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=4)


def generate_customer_id() -> str:
    """Generate next sequential customer ID.

    Returns:
        Customer ID in format 'CID-YYYY-NNNN' (e.g., 'CID-2025-0001').
    """
    customers = load_customers()
    current_year = datetime.now().year

    year_customers = [
        c for c in customers
        if c.get("customer_id", "").startswith(f"{CUSTOMER_ID_PREFIX}-{current_year}-")
    ]

    next_number = len(year_customers) + 1
    return f"{CUSTOMER_ID_PREFIX}-{current_year}-{next_number:04d}"


def create_customer(
    customer_first_name: str,
    customer_last_name: str,
    customer_contact_email: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new customer record.

    Args:
        customer_first_name: Customer's first name.
        customer_last_name: Customer's last name.
        customer_contact_email: Email address for communications.
        **kwargs: Optional fields for customer record.

    Returns:
        Dictionary representing the new customer record with UUID and
        auto-generated customer_id.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")

    return {
        # Identity
        "uuid": str(uuid.uuid4()),
        "customer_id": generate_customer_id(),
        "customer_first_name": customer_first_name,
        "customer_last_name": customer_last_name,
        "customer_preferred_name": kwargs.get(
            "customer_preferred_name", customer_first_name
        ),
        # Online Identities
        "customer_ingame_username": kwargs.get("customer_ingame_username"),
        "customer_discord_user_id": kwargs.get("customer_discord_user_id"),
        # Contact
        "customer_contact_email": customer_contact_email,
        "preferred_contact_method": kwargs.get("preferred_contact_method", "email"),
        # Account Status
        "customer_account_created_date": kwargs.get(
            "customer_account_created_date", current_date
        ),
        "customer_account_status": kwargs.get("customer_account_status", "active"),
        "customer_fraud_risk": kwargs.get("customer_fraud_risk", "low"),
        "customer_vip_status": kwargs.get("customer_vip_status", "no"),
        "customer_status_reason": kwargs.get("customer_status_reason"),
        # Financial
        "customer_account_value": kwargs.get("customer_account_value", 0.0),
        "customer_total_lifetime_value": kwargs.get(
            "customer_total_lifetime_value", 0.0
        ),
        "vat_taxid": kwargs.get("vat_taxid"),
        "customer_last_order_date": kwargs.get("customer_last_order_date"),
        "customer_last_payment_date": kwargs.get("customer_last_payment_date"),
        # Content Creator
        "is_content_creator": kwargs.get("is_content_creator", "no"),
        # Authentication (if customer portal exists)
        "customer_mfa_enabled": kwargs.get("customer_mfa_enabled", False),
        "customer_last_login": kwargs.get("customer_last_login"),
        "password_last_changed": kwargs.get("password_last_changed"),
        "customer_account_locked": kwargs.get("customer_account_locked", False),
        # Notifications
        "marketing_opt_in": kwargs.get("marketing_opt_in", False),
        "maintenance_notifications_enabled": kwargs.get(
            "maintenance_notifications_enabled", True
        ),
        # Service Access
        "has_freshrss_access": kwargs.get("has_freshrss_access", False),
        "has_jellyfin_access": kwargs.get("has_jellyfin_access", False),
        "has_nextcloud_access": kwargs.get("has_nextcloud_access", False),
    }


def find_customer_by_uuid(customer_uuid: str) -> dict[str, Any] | None:
    """Find a customer by their UUID.

    Args:
        customer_uuid: The UUID to search for.

    Returns:
        Customer dictionary if found, None otherwise.
    """
    customers = load_customers()

    for customer in customers:
        if customer.get("uuid") == customer_uuid:
            return customer

    return None


def find_customer_by_id(customer_id: str) -> dict[str, Any] | None:
    """Find a customer by their customer ID.

    Args:
        customer_id: The customer ID (CID-YYYY-NNNN) to search for.

    Returns:
        Customer dictionary if found, None otherwise.
    """
    customers = load_customers()

    for customer in customers:
        if customer.get("customer_id") == customer_id:
            return customer

    return None


def find_customer_by_email(email: str) -> dict[str, Any] | None:
    """Find a customer by their email address.

    Args:
        email: The email address to search for.

    Returns:
        Customer dictionary if found, None otherwise.
    """
    customers = load_customers()

    for customer in customers:
        if customer.get("customer_contact_email") == email:
            return customer

    return None


def update_customer(customer_uuid: str, updates: dict[str, Any]) -> bool:
    """Update an existing customer record.

    Args:
        customer_uuid: The UUID of the customer to update.
        updates: Dictionary of fields to update.

    Returns:
        True if update was successful, False if customer not found.
    """
    customers = load_customers()

    # Protected fields that should not be updated directly
    protected_fields = {"uuid", "customer_id", "customer_account_created_date"}

    for customer in customers:
        if customer.get("uuid") != customer_uuid:
            continue

        for key, value in updates.items():
            if key in protected_fields:
                continue
            customer[key] = value

        save_customers(customers)
        return True

    return False


def get_vip_customers() -> list[dict[str, Any]]:
    """Get all customers with VIP status.

    Returns:
        List of customer dictionaries with VIP status set to 'yes'.
    """
    customers = load_customers()
    return [
        c for c in customers
        if c.get("customer_vip_status") == "yes"
    ]


def get_active_customers() -> list[dict[str, Any]]:
    """Get all active customers.

    Returns:
        List of customer dictionaries with active account status.
    """
    customers = load_customers()
    return [
        c for c in customers
        if c.get("customer_account_status") == "active"
    ]
