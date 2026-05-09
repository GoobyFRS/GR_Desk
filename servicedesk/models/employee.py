"""Employee data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import uuid4

from flask_login import UserMixin


@dataclass
class Employee(UserMixin):
    """Employee model with Flask-Login integration.

    Attributes:
        uuid: Unique identifier.
        employee_id: Human-readable employee ID (EM-NNNN).
        employee_first_name: First name.
        employee_last_name: Last name.
        employee_preferred_name: Preferred/display name.
        employee_dob: Date of birth (YYYY-MM-DD).
        employee_email: Email address (used for login).
        employee_phone: Phone number.
        employee_timezone: Timezone preference.
        employee_ingame_username: In-game username.
        employee_chat_userid: Chat platform user ID.
        employee_hire_date: Hire date (YYYY-MM-DD).
        employee_termination_date: Termination date if applicable.
        employment_status: Current employment status.
        rehire_status: Whether eligible for rehire.
        employee_title: Job title.
        employee_access_role: Access role (none, technician, admin).
        employee_compensation_type: Compensation type (salary, hourly).
        employee_base_salary: Annual salary amount.
        employee_hourly_rate: Hourly rate.
        employee_salary_exempt: Exempt from overtime.
        is_bonus_eligible: Eligible for bonuses.
        employee_bonus_rate: Bonus percentage.
        assigned_business_unit: Business unit assignment.
        employee_assignment_queue: Default ticket queue.
        employee_total_pto_available: Available PTO hours.
        reports_to: Manager's employee ID.
        employee_mfa_enabled: MFA enabled flag.
        employee_last_login: Last login timestamp.
        employee_password_last_changed: Password change timestamp.
        employee_account_locked: Account lock status.
        failed_login_attempts: Failed login counter.
        password_hash: Hashed password (not stored in exports).
        has_freshrss_access: FreshRSS access flag.
        has_jellyfin_access: Jellyfin access flag.
        has_nextcloud_access: Nextcloud access flag.
        has_tailnet_access: Tailscale access flag.
        has_gitea_access: Gitea access flag.
        has_discord_access: Discord access flag.
        has_slack_access: Slack access flag.
    """

    _counter: ClassVar[int] = 0

    uuid: str = field(default_factory=lambda: str(uuid4()))
    employee_id: str = ""
    employee_first_name: str = ""
    employee_last_name: str = ""
    employee_preferred_name: str = ""
    employee_dob: str | None = None
    employee_email: str = ""
    employee_phone: str = ""
    employee_timezone: str = "UTC"
    employee_ingame_username: str = ""
    employee_chat_userid: str = ""
    employee_hire_date: str = ""
    employee_termination_date: str | None = None
    employment_status: str = "active"
    rehire_status: str = "yes"
    employee_title: str = "Support Technician"
    employee_access_role: str = "technician"
    employee_compensation_type: str = "hourly"
    employee_base_salary: float = 0.0
    employee_hourly_rate: float = 0.0
    employee_salary_exempt: bool = False
    is_bonus_eligible: bool = False
    employee_bonus_rate: float = 0.0
    assigned_business_unit: str = "support"
    employee_assignment_queue: str = "support"
    employee_total_pto_available: float = 0.0
    reports_to: str | None = None
    employee_mfa_enabled: bool = False
    employee_last_login: str | None = None
    employee_password_last_changed: str | None = None
    employee_account_locked: bool = True
    failed_login_attempts: int = 0
    password_hash: str = ""
    has_freshrss_access: bool = False
    has_jellyfin_access: bool = False
    has_nextcloud_access: bool = False
    has_tailnet_access: bool = False
    has_gitea_access: bool = False
    has_discord_access: bool = False
    has_slack_access: bool = False

    def __post_init__(self) -> None:
        """Initialize employee ID and hire date if not set."""
        if not self.employee_hire_date:
            self.employee_hire_date = datetime.now().strftime("%Y-%m-%d")

        if not self.employee_id:
            self.employee_id = self._generate_employee_id()

    def get_id(self) -> str:
        """Return the user ID for Flask-Login.

        Returns:
            The employee UUID.
        """
        return self.uuid

    @property
    def is_admin(self) -> bool:
        """Check if employee has admin role.

        Returns:
            True if admin, False otherwise.
        """
        return self.employee_access_role == "admin"

    @property
    def is_technician(self) -> bool:
        """Check if employee has technician role.

        Returns:
            True if technician or admin, False otherwise.
        """
        return self.employee_access_role in ("technician", "admin")

    @property
    def display_name(self) -> str:
        """Get display name for the employee.

        Returns:
            Preferred name if set, otherwise first name.
        """
        if self.employee_preferred_name:
            return self.employee_preferred_name
        return self.employee_first_name

    @property
    def full_name(self) -> str:
        """Get full name of the employee.

        Returns:
            First and last name combined.
        """
        return f"{self.employee_first_name} {self.employee_last_name}".strip()

    @classmethod
    def _generate_employee_id(cls) -> str:
        """Generate a new employee ID.

        Returns:
            Employee ID in format EM-NNNN.
        """
        cls._counter += 1
        return f"EM-{cls._counter:04d}"

    @classmethod
    def set_counter(cls, value: int) -> None:
        """Set the employee counter (used when loading from storage).

        Args:
            value: Counter value to set.
        """
        assert value >= 0, "Counter must be non-negative"
        cls._counter = value

    def record_login(self) -> None:
        """Record a successful login."""
        self.employee_last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.failed_login_attempts = 0

    def record_failed_login(self) -> None:
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.employee_account_locked = True

    def unlock_account(self) -> None:
        """Unlock the employee account."""
        self.employee_account_locked = False
        self.failed_login_attempts = 0

    def to_dict(self, include_password: bool = True) -> dict[str, object]:
        """Convert employee to dictionary.

        Args:
            include_password: Whether to include password hash.

        Returns:
            Dictionary representation of the employee.
        """
        data: dict[str, object] = {
            "uuid": self.uuid,
            "employee_id": self.employee_id,
            "employee_first_name": self.employee_first_name,
            "employee_last_name": self.employee_last_name,
            "employee_preferred_name": self.employee_preferred_name,
            "employee_dob": self.employee_dob,
            "employee_email": self.employee_email,
            "employee_phone": self.employee_phone,
            "employee_timezone": self.employee_timezone,
            "employee_ingame_username": self.employee_ingame_username,
            "employee_chat_userid": self.employee_chat_userid,
            "employee_hire_date": self.employee_hire_date,
            "employee_termination_date": self.employee_termination_date,
            "employment_status": self.employment_status,
            "rehire_status": self.rehire_status,
            "employee_title": self.employee_title,
            "employee_access_role": self.employee_access_role,
            "employee_compensation_type": self.employee_compensation_type,
            "employee_base_salary": self.employee_base_salary,
            "employee_hourly_rate": self.employee_hourly_rate,
            "employee_salary_exempt": self.employee_salary_exempt,
            "is_bonus_eligible": self.is_bonus_eligible,
            "employee_bonus_rate": self.employee_bonus_rate,
            "assigned_business_unit": self.assigned_business_unit,
            "employee_assignment_queue": self.employee_assignment_queue,
            "employee_total_pto_available": self.employee_total_pto_available,
            "reports_to": self.reports_to,
            "employee_mfa_enabled": self.employee_mfa_enabled,
            "employee_last_login": self.employee_last_login,
            "employee_password_last_changed": self.employee_password_last_changed,
            "employee_account_locked": self.employee_account_locked,
            "failed_login_attempts": self.failed_login_attempts,
            "has_freshrss_access": self.has_freshrss_access,
            "has_jellyfin_access": self.has_jellyfin_access,
            "has_nextcloud_access": self.has_nextcloud_access,
            "has_tailnet_access": self.has_tailnet_access,
            "has_gitea_access": self.has_gitea_access,
            "has_discord_access": self.has_discord_access,
            "has_slack_access": self.has_slack_access,
        }

        if include_password:
            data["password_hash"] = self.password_hash

        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Employee:
        """Create employee from dictionary.

        Args:
            data: Dictionary with employee data.

        Returns:
            Employee instance.
        """
        assert isinstance(data, dict), "Data must be a dictionary"

        return cls(
            uuid=str(data.get("uuid", uuid4())),
            employee_id=str(data.get("employee_id", "")),
            employee_first_name=str(data.get("employee_first_name", "")),
            employee_last_name=str(data.get("employee_last_name", "")),
            employee_preferred_name=str(data.get("employee_preferred_name", "")),
            employee_dob=data.get("employee_dob"),  # type: ignore[arg-type]
            employee_email=str(data.get("employee_email", "")),
            employee_phone=str(data.get("employee_phone", "")),
            employee_timezone=str(data.get("employee_timezone", "UTC")),
            employee_ingame_username=str(data.get("employee_ingame_username", "")),
            employee_chat_userid=str(data.get("employee_chat_userid", "")),
            employee_hire_date=str(data.get("employee_hire_date", "")),
            employee_termination_date=data.get("employee_termination_date"),  # type: ignore[arg-type]
            employment_status=str(data.get("employment_status", "active")),
            rehire_status=str(data.get("rehire_status", "yes")),
            employee_title=str(data.get("employee_title", "Support Technician")),
            employee_access_role=str(data.get("employee_access_role", "technician")),
            employee_compensation_type=str(data.get("employee_compensation_type", "hourly")),
            employee_base_salary=float(data.get("employee_base_salary", 0.0)),  # type: ignore[arg-type]
            employee_hourly_rate=float(data.get("employee_hourly_rate", 0.0)),  # type: ignore[arg-type]
            employee_salary_exempt=bool(data.get("employee_salary_exempt", False)),
            is_bonus_eligible=bool(data.get("is_bonus_eligible", False)),
            employee_bonus_rate=float(data.get("employee_bonus_rate", 0.0)),  # type: ignore[arg-type]
            assigned_business_unit=str(data.get("assigned_business_unit", "support")),
            employee_assignment_queue=str(data.get("employee_assignment_queue", "support")),
            employee_total_pto_available=float(data.get("employee_total_pto_available", 0.0)),  # type: ignore[arg-type]
            reports_to=data.get("reports_to"),  # type: ignore[arg-type]
            employee_mfa_enabled=bool(data.get("employee_mfa_enabled", False)),
            employee_last_login=data.get("employee_last_login"),  # type: ignore[arg-type]
            employee_password_last_changed=data.get("employee_password_last_changed"),  # type: ignore[arg-type]
            employee_account_locked=bool(data.get("employee_account_locked", True)),
            failed_login_attempts=int(data.get("failed_login_attempts", 0)),  # type: ignore[arg-type]
            password_hash=str(data.get("password_hash", "")),
            has_freshrss_access=bool(data.get("has_freshrss_access", False)),
            has_jellyfin_access=bool(data.get("has_jellyfin_access", False)),
            has_nextcloud_access=bool(data.get("has_nextcloud_access", False)),
            has_tailnet_access=bool(data.get("has_tailnet_access", False)),
            has_gitea_access=bool(data.get("has_gitea_access", False)),
            has_discord_access=bool(data.get("has_discord_access", False)),
            has_slack_access=bool(data.get("has_slack_access", False)),
        )
