"""Counter synchronization utilities for model ID generation.

This module provides helper functions to synchronize model counters
with existing data, ensuring unique ID generation after application restart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from servicedesk.models.customer import Customer
    from servicedesk.models.employee import Employee
    from servicedesk.models.service import Service
    from servicedesk.models.ticket import Ticket


def sync_ticket_counter(tickets: list[Ticket]) -> None:
    """Synchronize ticket counter from existing tickets.

    Parses ticket numbers (INC-YYYY-NNNN) to find the highest
    sequence number and updates the Ticket class counter.

    Args:
        tickets: List of existing tickets.
    """
    from servicedesk.models.ticket import Ticket

    if not tickets:
        return

    max_num: int = 0
    for ticket in tickets:
        num = _parse_ticket_number(ticket.ticket_number)
        if num > max_num:
            max_num = num

    Ticket.set_counter(max_num)


def sync_customer_counter(customers: list[Customer]) -> None:
    """Synchronize customer counter from existing customers.

    Parses customer IDs (CUST-NNNN) to find the highest
    sequence number and updates the Customer class counter.

    Args:
        customers: List of existing customers.
    """
    from servicedesk.models.customer import Customer

    if not customers:
        return

    max_num: int = 0
    for customer in customers:
        num = _parse_customer_id(customer.customer_id)
        if num > max_num:
            max_num = num

    Customer.set_counter(max_num)


def sync_employee_counter(employees: list[Employee]) -> None:
    """Synchronize employee counter from existing employees.

    Parses employee IDs (EMP-NNNN) to find the highest
    sequence number and updates the Employee class counter.

    Args:
        employees: List of existing employees.
    """
    from servicedesk.models.employee import Employee

    if not employees:
        return

    max_num: int = 0
    for employee in employees:
        num = _parse_employee_id(employee.employee_id)
        if num > max_num:
            max_num = num

    Employee.set_counter(max_num)


def sync_service_counter(services: list[Service]) -> None:
    """Synchronize service counter from existing services.

    Parses service IDs (SVC-NNNN) to find the highest
    sequence number and updates the Service class counter.

    Args:
        services: List of existing services.
    """
    from servicedesk.models.service import Service

    if not services:
        return

    max_num: int = 0
    for service in services:
        num = _parse_service_id(service.service_id)
        if num > max_num:
            max_num = num

    Service.set_counter(max_num)


def _parse_ticket_number(ticket_number: str) -> int:
    """Parse sequence number from ticket number.

    Args:
        ticket_number: Ticket number in format INC-YYYY-NNNN.

    Returns:
        Sequence number, or 0 if parsing fails.
    """
    parts = ticket_number.split("-")
    if len(parts) != 3:
        return 0
    try:
        return int(parts[2])
    except ValueError:
        return 0


def _parse_customer_id(customer_id: str) -> int:
    """Parse sequence number from customer ID.

    Args:
        customer_id: Customer ID in format CUST-NNNN.

    Returns:
        Sequence number, or 0 if parsing fails.
    """
    parts = customer_id.split("-")
    if len(parts) != 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def _parse_employee_id(employee_id: str) -> int:
    """Parse sequence number from employee ID.

    Args:
        employee_id: Employee ID in format EMP-NNNN.

    Returns:
        Sequence number, or 0 if parsing fails.
    """
    parts = employee_id.split("-")
    if len(parts) != 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def _parse_service_id(service_id: str) -> int:
    """Parse sequence number from service ID.

    Args:
        service_id: Service ID in format SVC-NNNN.

    Returns:
        Sequence number, or 0 if parsing fails.
    """
    parts = service_id.split("-")
    if len(parts) != 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0
