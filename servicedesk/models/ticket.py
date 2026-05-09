"""Ticket data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import uuid4


@dataclass
class Ticket:
    """ITSM Ticket model.

    Attributes:
        uuid: Unique identifier.
        ticket_number: Human-readable ticket number (INC-YYYY-NNNN).
        ticket_status: Current status (new, in_progress, on_hold, resolved, cancelled).
        requestor_name: Name of the person who submitted the ticket.
        requestor_username: Username/email of the requestor.
        ticket_type: Type/category of the ticket.
        ticket_subject: Brief description of the issue.
        ticket_body: Detailed description of the issue.
        ticket_impact: Business impact level (low, medium, high, critical).
        ticket_urgency: Urgency level (low, medium, high, critical).
        escalation_level: Current escalation level.
        assigned_queue: Queue the ticket is assigned to.
        assigned_technician: Employee ID of assigned technician.
        ticket_worknotes: Internal work notes.
        ticket_resolution_notes: Resolution summary.
        ticket_created_timestamp: When the ticket was created.
        ticket_escalation_timestamp: When the ticket was escalated.
        ticket_closed_timestamp: When the ticket was resolved/closed.
        ticket_acknowledged_timestamp: When the ticket was first acknowledged.
        requestor_vip_status: Whether the requestor is a VIP.
        ticket_overdue: Whether the ticket is past SLA.
        ticket_source: Source of the ticket (web, tailscale, uptime-kuma, etc.).
    """

    _counter: ClassVar[int] = 0

    uuid: str = field(default_factory=lambda: str(uuid4()))
    ticket_number: str = ""
    ticket_status: str = "new"
    requestor_name: str = ""
    requestor_username: str = ""
    ticket_type: str = ""
    ticket_subject: str = ""
    ticket_body: str = ""
    ticket_impact: str = "low"
    ticket_urgency: str = "low"
    escalation_level: int = 0
    assigned_queue: str = "support"
    assigned_technician: str | None = None
    ticket_worknotes: list[dict[str, str]] = field(default_factory=list)
    ticket_resolution_notes: str = ""
    ticket_created_timestamp: str = ""
    ticket_escalation_timestamp: str | None = None
    ticket_closed_timestamp: str | None = None
    ticket_acknowledged_timestamp: str | None = None
    requestor_vip_status: bool = False
    ticket_overdue: bool = False
    ticket_source: str = "web"

    def __post_init__(self) -> None:
        """Initialize ticket number and timestamp if not set."""
        if not self.ticket_created_timestamp:
            self.ticket_created_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()

    @classmethod
    def _generate_ticket_number(cls) -> str:
        """Generate a new ticket number.

        Returns:
            Ticket number in format INC-YYYY-NNNN.
        """
        cls._counter += 1
        year = datetime.now().year
        return f"INC-{year}-{cls._counter:04d}"

    @classmethod
    def set_counter(cls, value: int) -> None:
        """Set the ticket counter (used when loading from storage).

        Args:
            value: Counter value to set.
        """
        assert value >= 0, "Counter must be non-negative"
        cls._counter = value

    def add_worknote(self, author: str, content: str) -> None:
        """Add a work note to the ticket.

        Args:
            author: Name of the author.
            content: Work note content.
        """
        assert author, "Author cannot be empty"
        assert content, "Content cannot be empty"

        note = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "author": author,
            "content": content,
        }
        self.ticket_worknotes.append(note)

    def resolve(self, resolution_notes: str) -> None:
        """Mark the ticket as resolved.

        Args:
            resolution_notes: Summary of the resolution.
        """
        assert resolution_notes, "Resolution notes cannot be empty"

        self.ticket_status = "resolved"
        self.ticket_resolution_notes = resolution_notes
        self.ticket_closed_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def escalate(self) -> None:
        """Escalate the ticket."""
        self.escalation_level += 1
        self.assigned_queue = "escalation"
        self.ticket_escalation_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> dict[str, object]:
        """Convert ticket to dictionary.

        Returns:
            Dictionary representation of the ticket.
        """
        return {
            "uuid": self.uuid,
            "ticket_number": self.ticket_number,
            "ticket_status": self.ticket_status,
            "requestor_name": self.requestor_name,
            "requestor_username": self.requestor_username,
            "ticket_type": self.ticket_type,
            "ticket_subject": self.ticket_subject,
            "ticket_body": self.ticket_body,
            "ticket_impact": self.ticket_impact,
            "ticket_urgency": self.ticket_urgency,
            "escalation_level": self.escalation_level,
            "assigned_queue": self.assigned_queue,
            "assigned_technician": self.assigned_technician,
            "ticket_worknotes": self.ticket_worknotes,
            "ticket_resolution_notes": self.ticket_resolution_notes,
            "ticket_created_timestamp": self.ticket_created_timestamp,
            "ticket_escalation_timestamp": self.ticket_escalation_timestamp,
            "ticket_closed_timestamp": self.ticket_closed_timestamp,
            "ticket_acknowledged_timestamp": self.ticket_acknowledged_timestamp,
            "requestor_vip_status": self.requestor_vip_status,
            "ticket_overdue": self.ticket_overdue,
            "ticket_source": self.ticket_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Ticket:
        """Create ticket from dictionary.

        Args:
            data: Dictionary with ticket data.

        Returns:
            Ticket instance.
        """
        assert isinstance(data, dict), "Data must be a dictionary"

        return cls(
            uuid=str(data.get("uuid", uuid4())),
            ticket_number=str(data.get("ticket_number", "")),
            ticket_status=str(data.get("ticket_status", "new")),
            requestor_name=str(data.get("requestor_name", "")),
            requestor_username=str(data.get("requestor_username", "")),
            ticket_type=str(data.get("ticket_type", "")),
            ticket_subject=str(data.get("ticket_subject", "")),
            ticket_body=str(data.get("ticket_body", "")),
            ticket_impact=str(data.get("ticket_impact", "low")),
            ticket_urgency=str(data.get("ticket_urgency", "low")),
            escalation_level=int(data.get("escalation_level", 0)),  # type: ignore[arg-type]
            assigned_queue=str(data.get("assigned_queue", "support")),
            assigned_technician=data.get("assigned_technician"),  # type: ignore[arg-type]
            ticket_worknotes=list(data.get("ticket_worknotes", [])),  # type: ignore[arg-type]
            ticket_resolution_notes=str(data.get("ticket_resolution_notes", "")),
            ticket_created_timestamp=str(data.get("ticket_created_timestamp", "")),
            ticket_escalation_timestamp=data.get("ticket_escalation_timestamp"),  # type: ignore[arg-type]
            ticket_closed_timestamp=data.get("ticket_closed_timestamp"),  # type: ignore[arg-type]
            ticket_acknowledged_timestamp=data.get("ticket_acknowledged_timestamp"),  # type: ignore[arg-type]
            requestor_vip_status=bool(data.get("requestor_vip_status", False)),
            ticket_overdue=bool(data.get("ticket_overdue", False)),
            ticket_source=str(data.get("ticket_source", "web")),
        )
