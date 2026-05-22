"""Flask blueprints for the Service Desk application."""

from servicedesk.blueprints.public import public_bp
from servicedesk.blueprints.setup import setup_bp
from servicedesk.blueprints.itsm import itsm_bp
from servicedesk.blueprints.hr import hr_bp
from servicedesk.blueprints.crm import crm_bp
from servicedesk.blueprints.services import services_bp

__all__ = [
    "public_bp",
    "setup_bp",
    "itsm_bp",
    "hr_bp",
    "crm_bp",
    "services_bp",
]
