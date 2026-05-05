#!/usr/bin/env python3
import json
import uuid
from datetime import datetime
import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
CUSTOMERS_FILE = core_config.get("customers_file", "./my_data/customers.json")

def load_customers():
    try:
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def save_customers(customers):
    with open(CUSTOMERS_FILE, "w") as f:
        json.dump(customers, f, indent=4)

def get_next_customer_id(): # Generate Customer ID numbers.
    customers = load_customers()
    return f"CLIENT{str(len(customers) + 1).zfill(4)}"

def create_customer(customer_username, customer_first_name, customer_last_name, customer_contact_email, **kwargs):
    customer = {
        "uuid": str(uuid.uuid4()),
        "customer_id": get_next_customer_id(),
        "customer_username": customer_username,
        "customer_first_name": customer_first_name,
        "customer_last_name": customer_last_name,
        "customer_prefered_name": kwargs.get("customer_prefered_name", customer_first_name),
        "customer_ingame_username": kwargs.get("customer_ingame_username", ""),
        "customer_contact_email": customer_contact_email,
        "customer_account_created_date": datetime.now().strftime("%Y-%m-%d"),
        "customer_account_status": kwargs.get("customer_account_status", "Active"),
        "customer_fraud_risk": kwargs.get("customer_fraud_risk", "low"),
        "customer_vip_status": kwargs.get("customer_vip_status", False),
        "customer_account_value": kwargs.get("customer_account_value", 0.0),
        "customer_helpdesk_tickets": [],
        "is_content_creator": kwargs.get("is_content_creator", False)
    }
    return customer

def find_customer_by_uuid(customer_uuid):
    customers = load_customers()
    return next((c for c in customers if c["uuid"] == customer_uuid), None)

def find_customer_by_username(username):
    customers = load_customers()
    return next((c for c in customers if c["customer_username"] == username), None)

def update_customer(customer_uuid, updates):
    customers = load_customers()
    for customer in customers:
        if customer["uuid"] == customer_uuid:
            customer.update(updates)
            save_customers(customers)
            return True
    return False
