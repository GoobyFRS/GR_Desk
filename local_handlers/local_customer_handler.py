#!/usr/bin/env python3
"""Customer management and data persistence.

Handles all customer-related operations including creation, retrieval,
and updates. Customers are stored as JSON records with metadata for
account management, support tracking, and VIP status.
"""

import json
import uuid
from datetime import datetime
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
CUSTOMERS_FILE: str = core_config.get(
    "customers_file", "./my_data/customers.json"
)


def load_customers() -> list[dict[str, Any]]:
    """Load all customers from JSON storage.

    Returns:
        List of customer dictionaries. Empty list if file missing or invalid.
    """
    try:
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_customers(customers: list[dict[str, Any]]) -> None:
    """Persist customers to JSON storage.

    Args:
        customers: List of customer dictionaries to save.
    """
    with open(CUSTOMERS_FILE, "w") as f:
        json.dump(customers, f, indent=4)


def get_next_customer_id() -> str:
    """Generate next sequential customer ID.

    Returns:
        Customer ID in format 'CLIENT####' (e.g., 'CLIENT0001').
    """
    customers = load_customers()
    return f"CLIENT{str(len(customers) + 1).zfill(4)}"


def create_customer(
    customer_username: str,
    customer_first_name: str,
    customer_last_name: str,
    customer_contact_email: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new customer record.

    Args:
        customer_username: Unique login username.
        customer_first_name: Customer's first name.
        customer_last_name: Customer's last name.
        customer_contact_email: Email address for communications.
        **kwargs: Optional fields including customer_prefered_name,
            customer_ingame_username, customer_account_status,
            customer_fraud_risk, customer_vip_status, customer_account_value,
            is_content_creator.

    Returns:
        Dictionary representing the new customer record with UUID and
        auto-generated customer_id.
    """
    customer: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "customer_id": get_next_customer_id(),
        "customer_username": customer_username,
        "customer_first_name": customer_first_name,
        "customer_last_name": customer_last_name,
        "customer_prefered_name": kwargs.get(
            "customer_prefered_name", customer_first_name
        ),
        "customer_ingame_username": kwargs.get("customer_ingame_username", ""),
        "customer_contact_email": customer_contact_email,
        "customer_account_created_date": datetime.now().strftime("%Y-%m-%d"),
        "customer_account_status": kwargs.get(
            "customer_account_status", "Active"
        ),
        "customer_fraud_risk": kwargs.get("customer_fraud_risk", "low"),
        "customer_vip_status": kwargs.get("customer_vip_status", False),
        "customer_account_value": kwargs.get("customer_account_value", 0.0),
        "customer_helpdesk_tickets": [],
        "is_content_creator": kwargs.get("is_content_creator", False),
    }
    return customer


def find_customer_by_uuid(customer_uuid: str) -> dict[str, Any] | None:
    """Find a customer by their UUID.

    Args:
        customer_uuid: The UUID to search for.

    Returns:
        Customer dictionary if found, None otherwise.
    """
    customers = load_customers()
    return next(
        (c for c in customers if c["uuid"] == customer_uuid), None
    )


def find_customer_by_username(username: str) -> dict[str, Any] | None:
    """Find a customer by their username.

    Args:
        username: The customer username to search for.

    Returns:
        Customer dictionary if found, None otherwise.
    """
    customers = load_customers()
    return next(
        (c for c in customers if c["customer_username"] == username), None
    )


def update_customer(
    customer_uuid: str, updates: dict[str, Any]
) -> bool:
    """Update an existing customer record.

    Args:
        customer_uuid: The UUID of the customer to update.
        updates: Dictionary of fields to update.

    Returns:
        True if update was successful, False if customer not found.
    """
    customers = load_customers()
    for customer in customers:
        if customer["uuid"] == customer_uuid:
            customer.update(updates)
            save_customers(customers)
            return True
    return False
