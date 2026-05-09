"""Customer data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import uuid4


@dataclass
class Customer:
    """Customer/CRM model.

    Attributes:
        uuid: Unique identifier.
        customer_id: Human-readable customer ID (CID-NNNN).
        customer_first_name: First name.
        customer_last_name: Last name.
        customer_preferred_name: Preferred/display name.
        customer_ingame_username: In-game username.
        customer_discord_user_id: Discord user ID.
        customer_contact_email: Contact email address.
        customer_account_created_date: Account creation date.
        customer_account_status: Account status (active, suspended, closed).
        customer_fraud_risk: Fraud risk level (low, medium, high).
        customer_vip_status: VIP customer flag.
        customer_account_value: Account tier/value.
        is_content_creator: Content creator flag.
        vat_taxid: VAT/Tax ID for invoicing.
        customer_mfa_enabled: MFA enabled flag.
        customer_last_login: Last login timestamp.
        password_last_changed: Password change timestamp.
        customer_account_locked: Account lock status.
        customer_last_order_date: Last order date.
        customer_last_payment_date: Last payment date.
        customer_total_lifetime_value: Total lifetime spend.
        customer_status_reason: Reason for current status.
        preferred_contact_method: Preferred contact method.
        marketing_opt_in: Marketing communications opt-in.
        maintenance_notifications_enabled: Maintenance notification opt-in.
        has_freshrss_access: FreshRSS access flag.
        freshrss_username: FreshRSS username.
        has_jellyfin_access: Jellyfin access flag.
        jellyfin_username: Jellyfin username.
        has_nextcloud_access: Nextcloud access flag.
        nextcloud_username: Nextcloud username.
        password_hash: Hashed password for customer portal.
    """

    _counter: ClassVar[int] = 0

    uuid: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    customer_first_name: str = ""
    customer_last_name: str = ""
    customer_preferred_name: str = ""
    customer_ingame_username: str = ""
    customer_discord_user_id: str = ""
    customer_contact_email: str = ""
    customer_account_created_date: str = ""
    customer_account_status: str = "active"
    customer_fraud_risk: str = "low"
    customer_vip_status: bool = False
    customer_account_value: str = ""
    is_content_creator: bool = False
    vat_taxid: str | None = None
    customer_mfa_enabled: bool = False
    customer_last_login: str | None = None
    password_last_changed: str | None = None
    customer_account_locked: bool = False
    customer_last_order_date: str | None = None
    customer_last_payment_date: str | None = None
    customer_total_lifetime_value: float = 0.0
    customer_status_reason: str = ""
    preferred_contact_method: str = "email"
    marketing_opt_in: bool = False
    maintenance_notifications_enabled: bool = True
    has_freshrss_access: bool = False
    freshrss_username: str = ""
    has_jellyfin_access: bool = False
    jellyfin_username: str = ""
    has_nextcloud_access: bool = False
    nextcloud_username: str = ""
    password_hash: str = ""

    def __post_init__(self) -> None:
        """Initialize customer ID and creation date if not set."""
        if not self.customer_account_created_date:
            self.customer_account_created_date = datetime.now().strftime("%Y-%m-%d")

        if not self.customer_id:
            self.customer_id = self._generate_customer_id()

    @property
    def display_name(self) -> str:
        """Get display name for the customer.

        Returns:
            Preferred name if set, otherwise first name.
        """
        if self.customer_preferred_name:
            return self.customer_preferred_name
        return self.customer_first_name

    @property
    def full_name(self) -> str:
        """Get full name of the customer.

        Returns:
            First and last name combined.
        """
        return f"{self.customer_first_name} {self.customer_last_name}".strip()

    @property
    def is_vip(self) -> bool:
        """Check if customer is VIP.

        Returns:
            True if VIP, False otherwise.
        """
        return self.customer_vip_status

    @property
    def is_active(self) -> bool:
        """Check if customer account is active.

        Returns:
            True if active, False otherwise.
        """
        return self.customer_account_status == "active"

    @classmethod
    def _generate_customer_id(cls) -> str:
        """Generate a new customer ID.

        Returns:
            Customer ID in format CID-NNNN.
        """
        cls._counter += 1
        return f"CID-{cls._counter:04d}"

    @classmethod
    def set_counter(cls, value: int) -> None:
        """Set the customer counter (used when loading from storage).

        Args:
            value: Counter value to set.
        """
        assert value >= 0, "Counter must be non-negative"
        cls._counter = value

    def to_dict(self, include_password: bool = True) -> dict[str, object]:
        """Convert customer to dictionary.

        Args:
            include_password: Whether to include password hash.

        Returns:
            Dictionary representation of the customer.
        """
        data: dict[str, object] = {
            "uuid": self.uuid,
            "customer_id": self.customer_id,
            "customer_first_name": self.customer_first_name,
            "customer_last_name": self.customer_last_name,
            "customer_preferred_name": self.customer_preferred_name,
            "customer_ingame_username": self.customer_ingame_username,
            "customer_discord_user_id": self.customer_discord_user_id,
            "customer_contact_email": self.customer_contact_email,
            "customer_account_created_date": self.customer_account_created_date,
            "customer_account_status": self.customer_account_status,
            "customer_fraud_risk": self.customer_fraud_risk,
            "customer_vip_status": self.customer_vip_status,
            "customer_account_value": self.customer_account_value,
            "is_content_creator": self.is_content_creator,
            "vat_taxid": self.vat_taxid,
            "customer_mfa_enabled": self.customer_mfa_enabled,
            "customer_last_login": self.customer_last_login,
            "password_last_changed": self.password_last_changed,
            "customer_account_locked": self.customer_account_locked,
            "customer_last_order_date": self.customer_last_order_date,
            "customer_last_payment_date": self.customer_last_payment_date,
            "customer_total_lifetime_value": self.customer_total_lifetime_value,
            "customer_status_reason": self.customer_status_reason,
            "preferred_contact_method": self.preferred_contact_method,
            "marketing_opt_in": self.marketing_opt_in,
            "maintenance_notifications_enabled": self.maintenance_notifications_enabled,
            "has_freshrss_access": self.has_freshrss_access,
            "freshrss_username": self.freshrss_username,
            "has_jellyfin_access": self.has_jellyfin_access,
            "jellyfin_username": self.jellyfin_username,
            "has_nextcloud_access": self.has_nextcloud_access,
            "nextcloud_username": self.nextcloud_username,
        }

        if include_password:
            data["password_hash"] = self.password_hash

        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Customer:
        """Create customer from dictionary.

        Args:
            data: Dictionary with customer data.

        Returns:
            Customer instance.
        """
        assert isinstance(data, dict), "Data must be a dictionary"

        return cls(
            uuid=str(data.get("uuid", uuid4())),
            customer_id=str(data.get("customer_id", "")),
            customer_first_name=str(data.get("customer_first_name", "")),
            customer_last_name=str(data.get("customer_last_name", "")),
            customer_preferred_name=str(data.get("customer_preferred_name", "")),
            customer_ingame_username=str(data.get("customer_ingame_username", "")),
            customer_discord_user_id=str(data.get("customer_discord_user_id", "")),
            customer_contact_email=str(data.get("customer_contact_email", "")),
            customer_account_created_date=str(data.get("customer_account_created_date", "")),
            customer_account_status=str(data.get("customer_account_status", "active")),
            customer_fraud_risk=str(data.get("customer_fraud_risk", "low")),
            customer_vip_status=bool(data.get("customer_vip_status", False)),
            customer_account_value=str(data.get("customer_account_value", "")),
            is_content_creator=bool(data.get("is_content_creator", False)),
            vat_taxid=data.get("vat_taxid"),  # type: ignore[arg-type]
            customer_mfa_enabled=bool(data.get("customer_mfa_enabled", False)),
            customer_last_login=data.get("customer_last_login"),  # type: ignore[arg-type]
            password_last_changed=data.get("password_last_changed"),  # type: ignore[arg-type]
            customer_account_locked=bool(data.get("customer_account_locked", False)),
            customer_last_order_date=data.get("customer_last_order_date"),  # type: ignore[arg-type]
            customer_last_payment_date=data.get("customer_last_payment_date"),  # type: ignore[arg-type]
            customer_total_lifetime_value=float(data.get("customer_total_lifetime_value", 0.0)),  # type: ignore[arg-type]
            customer_status_reason=str(data.get("customer_status_reason", "")),
            preferred_contact_method=str(data.get("preferred_contact_method", "email")),
            marketing_opt_in=bool(data.get("marketing_opt_in", False)),
            maintenance_notifications_enabled=bool(data.get("maintenance_notifications_enabled", True)),
            has_freshrss_access=bool(data.get("has_freshrss_access", False)),
            freshrss_username=str(data.get("freshrss_username", "")),
            has_jellyfin_access=bool(data.get("has_jellyfin_access", False)),
            jellyfin_username=str(data.get("jellyfin_username", "")),
            has_nextcloud_access=bool(data.get("has_nextcloud_access", False)),
            nextcloud_username=str(data.get("nextcloud_username", "")),
            password_hash=str(data.get("password_hash", "")),
        )
