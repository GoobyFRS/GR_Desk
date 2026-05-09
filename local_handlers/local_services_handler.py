#!/usr/bin/env python3
"""Service database handler for managing provisioned services.

Provides CRUD operations for service records including game servers,
cloud instances, and other provisioned resources.
"""

__all__ = [
    "load_services",
    "save_services",
    "create_service",
    "find_service_by_id",
    "find_services_by_customer",
    "update_service_status",
    "generate_service_id",
]

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
SERVICES_FILE: str = core_config.get("services_file", "data/services.json")
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Constants
MAX_SERVICES_LOAD: int = 10_000
SERVICE_ID_PREFIX: str = "SVC"
VALID_SERVICE_STATUSES: list[str] = [
    "active", "suspended", "terminated", "pending", "maintenance"
]
VALID_PROVISIONING_STATUSES: list[str] = [
    "pending", "provisioning", "active", "failed", "deprovisioning"
]


def load_services() -> list[dict[str, Any]]:
    """Load services from JSON storage file.

    Returns:
        List of service dictionaries. Empty list if file doesn't exist
        or contains invalid data.
    """
    services_path = Path(SERVICES_FILE)

    if not services_path.exists():
        logging.debug("SERVICES HANDLER - Services file not found, returning empty list.")
        return []

    try:
        with open(services_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            logging.error("SERVICES HANDLER - Services file contains invalid data type.")
            return []

        return data[:MAX_SERVICES_LOAD]

    except json.JSONDecodeError as e:
        logging.error(f"SERVICES HANDLER - Failed to parse services file: {e}")
        return []
    except Exception as e:
        logging.error(f"SERVICES HANDLER - Failed to load services: {e}")
        return []


def save_services(services: list[dict[str, Any]]) -> bool:
    """Save services to JSON storage file.

    Args:
        services: List of service dictionaries to save.

    Returns:
        True if save was successful, False otherwise.
    """
    services_path = Path(SERVICES_FILE)

    try:
        services_path.parent.mkdir(parents=True, exist_ok=True)

        with open(services_path, "w", encoding="utf-8") as f:
            json.dump(services, f, indent=4)

        logging.info(f"SERVICES HANDLER - Saved {len(services)} services.")
        return True

    except Exception as e:
        logging.error(f"SERVICES HANDLER - Failed to save services: {e}")
        return False


def generate_service_id() -> str:
    """Generate a unique service ID.

    Returns:
        Service ID in format SVC-YYYY-NNNN.
    """
    services = load_services()
    current_year = datetime.now().year

    year_services = [
        s for s in services
        if s.get("service_id", "").startswith(f"{SERVICE_ID_PREFIX}-{current_year}-")
    ]

    next_number = len(year_services) + 1
    return f"{SERVICE_ID_PREFIX}-{current_year}-{next_number:04d}"


def create_service(
    service_name: str,
    service_type: str,
    customer_uuid: str | None = None,
    customer_id: str | None = None,
    service_sku: str | None = None,
    service_ip: str | None = None,
    service_subdomain: str | None = None,
    service_provision_source: str | None = None,
    service_rcon_port: int | None = None,
    service_rcon_pwd: str | None = None,
    node_id: str | None = None,
    cluster_id: str | None = None,
    region: str | None = None,
    allocated_ram_mb: int | None = None,
    allocated_disk_gb: int | None = None,
    allocated_cpu_cores: int | None = None,
    allocated_ports: list[int] | None = None,
    minecraft_version: str | None = None,
    server_type: str | None = None,
    modpack_name: str | None = None,
    player_limit: int | None = None,
) -> dict[str, Any]:
    """Create a new service record.

    Args:
        service_name: Display name for the service.
        service_type: Type of service (e.g., "minecraft", "vps", "web").
        customer_uuid: UUID of the owning customer.
        customer_id: Customer ID (CID) of the owner.
        service_sku: Product SKU for billing.
        service_ip: IP address assigned to service.
        service_subdomain: Subdomain for service access.
        service_provision_source: Source system that provisioned this service.
        service_rcon_port: RCON port for game servers.
        service_rcon_pwd: RCON password for game servers.
        node_id: Physical/virtual node hosting the service.
        cluster_id: Cluster the service belongs to.
        region: Geographic region of the service.
        allocated_ram_mb: RAM allocation in MB.
        allocated_disk_gb: Disk allocation in GB.
        allocated_cpu_cores: CPU core allocation.
        allocated_ports: List of allocated ports.
        minecraft_version: Minecraft version (for MC servers).
        server_type: Server software type (e.g., "paper", "forge").
        modpack_name: Modpack name if applicable.
        player_limit: Maximum concurrent players.

    Returns:
        Dictionary containing the new service record.
    """
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "uuid": str(uuid.uuid4()),
        "service_id": generate_service_id(),
        "service_sku": service_sku,
        "service_type": service_type,
        "service_name": service_name,
        "service_status": "pending",
        "provisioning_status": "pending",
        "service_ip": service_ip,
        "service_subdomain": service_subdomain,
        "service_created_timestamp": current_timestamp,
        "service_terminated_timestamp": None,
        "service_updated_timestamp": current_timestamp,
        "service_provision_source": service_provision_source,
        "customer_uuid": customer_uuid,
        "customer_id": customer_id,
        "service_rcon_port": service_rcon_port,
        "service_rcon_pwd": service_rcon_pwd,
        "node_id": node_id,
        "cluster_id": cluster_id,
        "region": region,
        "allocated_ram_mb": allocated_ram_mb,
        "allocated_disk_gb": allocated_disk_gb,
        "allocated_cpu_cores": allocated_cpu_cores,
        "allocated_ports": allocated_ports or [],
        "minecraft_version": minecraft_version,
        "server_type": server_type,
        "modpack_name": modpack_name,
        "player_limit": player_limit,
    }


def find_service_by_id(service_id: str) -> dict[str, Any] | None:
    """Find a service by its service ID.

    Args:
        service_id: The service ID to search for.

    Returns:
        Service dictionary if found, None otherwise.
    """
    services = load_services()

    for service in services:
        if service.get("service_id") == service_id:
            return service

    return None


def find_services_by_customer(customer_id: str) -> list[dict[str, Any]]:
    """Find all services belonging to a customer.

    Args:
        customer_id: The customer ID (CID) to search for.

    Returns:
        List of service dictionaries belonging to the customer.
    """
    services = load_services()
    return [s for s in services if s.get("customer_id") == customer_id]


def update_service_status(
    service_id: str,
    service_status: str | None = None,
    provisioning_status: str | None = None,
) -> bool:
    """Update the status of a service.

    Args:
        service_id: The service ID to update.
        service_status: New service status (if updating).
        provisioning_status: New provisioning status (if updating).

    Returns:
        True if service was found and updated, False otherwise.
    """
    if service_status and service_status not in VALID_SERVICE_STATUSES:
        logging.error(f"SERVICES HANDLER - Invalid service status: {service_status}")
        return False

    if provisioning_status and provisioning_status not in VALID_PROVISIONING_STATUSES:
        logging.error(
            f"SERVICES HANDLER - Invalid provisioning status: {provisioning_status}"
        )
        return False

    services = load_services()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for service in services:
        if service.get("service_id") != service_id:
            continue

        if service_status:
            service["service_status"] = service_status
            if service_status == "terminated":
                service["service_terminated_timestamp"] = current_timestamp

        if provisioning_status:
            service["provisioning_status"] = provisioning_status

        service["service_updated_timestamp"] = current_timestamp
        save_services(services)

        logging.info(f"SERVICES HANDLER - Service {service_id} status updated.")
        return True

    logging.warning(f"SERVICES HANDLER - Service {service_id} not found.")
    return False


def update_service(service_id: str, updates: dict[str, Any]) -> bool:
    """Update service fields.

    Args:
        service_id: The service ID to update.
        updates: Dictionary of fields to update.

    Returns:
        True if service was found and updated, False otherwise.
    """
    services = load_services()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fields that should not be updated directly
    protected_fields = {"uuid", "service_id", "service_created_timestamp"}

    for service in services:
        if service.get("service_id") != service_id:
            continue

        for key, value in updates.items():
            if key in protected_fields:
                logging.warning(
                    f"SERVICES HANDLER - Attempted to update protected field: {key}"
                )
                continue
            service[key] = value

        service["service_updated_timestamp"] = current_timestamp
        save_services(services)

        logging.info(f"SERVICES HANDLER - Service {service_id} updated.")
        return True

    logging.warning(f"SERVICES HANDLER - Service {service_id} not found for update.")
    return False
