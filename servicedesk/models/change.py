"""Change data model for IT Change Management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import uuid4


@dataclass
class Change:
    """Change request database model.

    Represents an IT change request with planning, approval workflow,
    and links to employees and services.

    Attributes:
        uuid: Unique identifier.
        change_number: Human-readable change ID (CHG-YYYY-NNNN).
        change_status: Current status (Draft, Pending, Approved, etc.).
        requestor_uuid: UUID of the requesting employee.
        requestor_id: Employee ID of the requestor (for display).
        implementor_uuid: UUID of the implementing employee.
        implementor_id: Employee ID of the implementor (for display).
        impacted_service_uuid: UUID of the impacted service.
        impacted_service_id: Service ID of the impacted service (for display).
        implement_plan: Implementation plan text.
        test_accept_plan: Test/acceptance plan text.
        rollback_plan: Rollback plan text.
        change_risk: Risk level (None, Low, Medium, High).
        planned_start_timestamp: Planned start time (YYYY-MM-DD HH:MM).
        planned_end_timestamp: Planned end time (YYYY-MM-DD HH:MM).
        change_created_timestamp: Creation timestamp.
        change_updated_timestamp: Last update timestamp.
    """

    _counter: ClassVar[int] = 0

    uuid: str = field(default_factory=lambda: str(uuid4()))
    change_number: str = ""
    change_status: str = "Draft"
    requestor_uuid: str = ""
    requestor_id: str = ""
    implementor_uuid: str = ""
    implementor_id: str = ""
    impacted_service_uuid: str = ""
    impacted_service_id: str = ""
    implement_plan: str = ""
    test_accept_plan: str = ""
    rollback_plan: str = ""
    change_risk: str = "None"
    planned_start_timestamp: str = ""
    planned_end_timestamp: str = ""
    change_created_timestamp: str = ""
    change_updated_timestamp: str = ""

    def __post_init__(self) -> None:
        """Initialize change number and timestamps if not set."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if not self.change_created_timestamp:
            self.change_created_timestamp = now

        if not self.change_updated_timestamp:
            self.change_updated_timestamp = now

        if not self.change_number:
            self.change_number = self._generate_change_number()

    @property
    def has_complete_plans(self) -> bool:
        """Check if all three plan fields are filled.

        Returns:
            True if all plans are non-empty, False otherwise.
        """
        return bool(
            self.implement_plan.strip()
            and self.test_accept_plan.strip()
            and self.rollback_plan.strip()
        )

    @property
    def can_leave_draft(self) -> bool:
        """Check if change can transition out of Draft status.

        Returns:
            True if plans are complete, False otherwise.
        """
        return self.has_complete_plans

    @property
    def is_active(self) -> bool:
        """Check if change is in an active state.

        Returns:
            True if not completed, rolled back, or cancelled.
        """
        return self.change_status not in ("Completed", "Rollback", "Cancelled")

    @classmethod
    def _generate_change_number(cls) -> str:
        """Generate a new change number.

        Returns:
            Change number in format CHG-YYYY-NNNN.
        """
        cls._counter += 1
        year = datetime.now().year
        return f"CHG-{year}-{cls._counter:04d}"

    @classmethod
    def set_counter(cls, value: int) -> None:
        """Set the change counter (used when loading from storage).

        Args:
            value: Counter value to set.
        """
        assert value >= 0, "Counter must be non-negative"
        cls._counter = value

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.change_updated_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> dict[str, object]:
        """Convert change to dictionary.

        Returns:
            Dictionary representation of the change.
        """
        return {
            "uuid": self.uuid,
            "change_number": self.change_number,
            "change_status": self.change_status,
            "requestor_uuid": self.requestor_uuid,
            "requestor_id": self.requestor_id,
            "implementor_uuid": self.implementor_uuid,
            "implementor_id": self.implementor_id,
            "impacted_service_uuid": self.impacted_service_uuid,
            "impacted_service_id": self.impacted_service_id,
            "implement_plan": self.implement_plan,
            "test_accept_plan": self.test_accept_plan,
            "rollback_plan": self.rollback_plan,
            "change_risk": self.change_risk,
            "planned_start_timestamp": self.planned_start_timestamp,
            "planned_end_timestamp": self.planned_end_timestamp,
            "change_created_timestamp": self.change_created_timestamp,
            "change_updated_timestamp": self.change_updated_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Change:
        """Create change from dictionary.

        Args:
            data: Dictionary with change data.

        Returns:
            Change instance.
        """
        assert isinstance(data, dict), "Data must be a dictionary"

        return cls(
            uuid=str(data.get("uuid", uuid4())),
            change_number=str(data.get("change_number", "")),
            change_status=str(data.get("change_status", "Draft")),
            requestor_uuid=str(data.get("requestor_uuid", "")),
            requestor_id=str(data.get("requestor_id", "")),
            implementor_uuid=str(data.get("implementor_uuid", "")),
            implementor_id=str(data.get("implementor_id", "")),
            impacted_service_uuid=str(data.get("impacted_service_uuid", "")),
            impacted_service_id=str(data.get("impacted_service_id", "")),
            implement_plan=str(data.get("implement_plan", "")),
            test_accept_plan=str(data.get("test_accept_plan", "")),
            rollback_plan=str(data.get("rollback_plan", "")),
            change_risk=str(data.get("change_risk", "None")),
            planned_start_timestamp=str(data.get("planned_start_timestamp", "")),
            planned_end_timestamp=str(data.get("planned_end_timestamp", "")),
            change_created_timestamp=str(data.get("change_created_timestamp", "")),
            change_updated_timestamp=str(data.get("change_updated_timestamp", "")),
        )
