"""Service data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import uuid4


@dataclass
class Service:
    """Service database model.

    Supports both generic services and game server specific fields.

    Attributes:
        uuid: Unique identifier.
        service_id: Human-readable service ID (SVC-NNNN).
        service_sku: Product SKU.
        service_type: Type of service.
        service_name: Display name.
        service_status: Current status (active, suspended, terminated, provisioning).
        provisioning_status: Provisioning state.
        service_ip: IP address.
        service_subdomain: Subdomain.
        service_created_timestamp: Creation timestamp.
        service_terminated_timestamp: Termination timestamp.
        service_updated_timestamp: Last update timestamp.
        service_provision_source: Source of provisioning.
        customer_uuid: Linked customer UUID.
        customer_id: Linked customer ID.
        service_rcon_port: RCON port (game servers).
        service_rcon_pwd: RCON password (game servers).
        node_id: Infrastructure node ID.
        cluster_id: Infrastructure cluster ID.
        region: Geographic region.
        allocated_ram_mb: Allocated RAM in MB.
        allocated_disk_gb: Allocated disk in GB.
        allocated_cpu_cores: Allocated CPU cores.
        allocated_ports: Allocated network ports.
        minecraft_version: Minecraft version (game servers).
        server_type: Server software type.
        modpack_name: Modpack name (game servers).
        player_limit: Maximum players (game servers).
    """

    _counter: ClassVar[int] = 0

    uuid: str = field(default_factory=lambda: str(uuid4()))
    service_id: str = ""
    service_sku: str = ""
    service_type: str = ""
    service_name: str = ""
    service_status: str = "provisioning"
    provisioning_status: str = "pending"
    service_ip: str = ""
    service_subdomain: str = ""
    service_created_timestamp: str = ""
    service_terminated_timestamp: str | None = None
    service_updated_timestamp: str = ""
    service_provision_source: str = ""
    customer_uuid: str = ""
    customer_id: str = ""
    service_rcon_port: int | None = None
    service_rcon_pwd: str = ""
    node_id: str = ""
    cluster_id: str = ""
    region: str = ""
    allocated_ram_mb: int = 0
    allocated_disk_gb: int = 0
    allocated_cpu_cores: float = 0.0
    allocated_ports: list[int] = field(default_factory=list)
    minecraft_version: str = ""
    server_type: str = ""
    modpack_name: str = ""
    player_limit: int = 0

    def __post_init__(self) -> None:
        """Initialize service ID and timestamps if not set."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if not self.service_created_timestamp:
            self.service_created_timestamp = now

        if not self.service_updated_timestamp:
            self.service_updated_timestamp = now

        if not self.service_id:
            self.service_id = self._generate_service_id()

    @property
    def is_active(self) -> bool:
        """Check if service is active.

        Returns:
            True if active, False otherwise.
        """
        return self.service_status == "active"

    @property
    def is_game_server(self) -> bool:
        """Check if service is a game server.

        Returns:
            True if game server fields are populated.
        """
        return bool(self.minecraft_version or self.modpack_name or self.player_limit)

    @classmethod
    def _generate_service_id(cls) -> str:
        """Generate a new service ID.

        Returns:
            Service ID in format SVC-NNNN.
        """
        cls._counter += 1
        return f"SVC-{cls._counter:04d}"

    @classmethod
    def set_counter(cls, value: int) -> None:
        """Set the service counter (used when loading from storage).

        Args:
            value: Counter value to set.
        """
        assert value >= 0, "Counter must be non-negative"
        cls._counter = value

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.service_updated_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def terminate(self) -> None:
        """Mark the service as terminated."""
        self.service_status = "terminated"
        self.service_terminated_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.update_timestamp()

    def to_dict(self) -> dict[str, object]:
        """Convert service to dictionary.

        Returns:
            Dictionary representation of the service.
        """
        return {
            "uuid": self.uuid,
            "service_id": self.service_id,
            "service_sku": self.service_sku,
            "service_type": self.service_type,
            "service_name": self.service_name,
            "service_status": self.service_status,
            "provisioning_status": self.provisioning_status,
            "service_ip": self.service_ip,
            "service_subdomain": self.service_subdomain,
            "service_created_timestamp": self.service_created_timestamp,
            "service_terminated_timestamp": self.service_terminated_timestamp,
            "service_updated_timestamp": self.service_updated_timestamp,
            "service_provision_source": self.service_provision_source,
            "customer_uuid": self.customer_uuid,
            "customer_id": self.customer_id,
            "service_rcon_port": self.service_rcon_port,
            "service_rcon_pwd": self.service_rcon_pwd,
            "node_id": self.node_id,
            "cluster_id": self.cluster_id,
            "region": self.region,
            "allocated_ram_mb": self.allocated_ram_mb,
            "allocated_disk_gb": self.allocated_disk_gb,
            "allocated_cpu_cores": self.allocated_cpu_cores,
            "allocated_ports": self.allocated_ports,
            "minecraft_version": self.minecraft_version,
            "server_type": self.server_type,
            "modpack_name": self.modpack_name,
            "player_limit": self.player_limit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Service:
        """Create service from dictionary.

        Args:
            data: Dictionary with service data.

        Returns:
            Service instance.
        """
        assert isinstance(data, dict), "Data must be a dictionary"

        return cls(
            uuid=str(data.get("uuid", uuid4())),
            service_id=str(data.get("service_id", "")),
            service_sku=str(data.get("service_sku", "")),
            service_type=str(data.get("service_type", "")),
            service_name=str(data.get("service_name", "")),
            service_status=str(data.get("service_status", "provisioning")),
            provisioning_status=str(data.get("provisioning_status", "pending")),
            service_ip=str(data.get("service_ip", "")),
            service_subdomain=str(data.get("service_subdomain", "")),
            service_created_timestamp=str(data.get("service_created_timestamp", "")),
            service_terminated_timestamp=data.get("service_terminated_timestamp"),  # type: ignore[arg-type]
            service_updated_timestamp=str(data.get("service_updated_timestamp", "")),
            service_provision_source=str(data.get("service_provision_source", "")),
            customer_uuid=str(data.get("customer_uuid", "")),
            customer_id=str(data.get("customer_id", "")),
            service_rcon_port=data.get("service_rcon_port"),  # type: ignore[arg-type]
            service_rcon_pwd=str(data.get("service_rcon_pwd", "")),
            node_id=str(data.get("node_id", "")),
            cluster_id=str(data.get("cluster_id", "")),
            region=str(data.get("region", "")),
            allocated_ram_mb=int(data.get("allocated_ram_mb", 0)),  # type: ignore[arg-type]
            allocated_disk_gb=int(data.get("allocated_disk_gb", 0)),  # type: ignore[arg-type]
            allocated_cpu_cores=float(data.get("allocated_cpu_cores", 0.0)),  # type: ignore[arg-type]
            allocated_ports=list(data.get("allocated_ports", [])),  # type: ignore[arg-type]
            minecraft_version=str(data.get("minecraft_version", "")),
            server_type=str(data.get("server_type", "")),
            modpack_name=str(data.get("modpack_name", "")),
            player_limit=int(data.get("player_limit", 0)),  # type: ignore[arg-type]
        )
