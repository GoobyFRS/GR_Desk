"""Data models for the Service Desk application."""

from servicedesk.models.ticket import Ticket
from servicedesk.models.employee import Employee
from servicedesk.models.customer import Customer
from servicedesk.models.service import Service

__all__ = ["Ticket", "Employee", "Customer", "Service"]
