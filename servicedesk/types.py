"""Type definitions for the Service Desk application.

This module contains TypedDict definitions for structured configuration
and data types used throughout the application.
"""

from __future__ import annotations

from typing import TypedDict


# =============================================================================
# Application Configuration Types
# =============================================================================


class AppConfigDict(TypedDict, total=False):
    """Application configuration settings."""

    name: str
    debug: bool
    log_level: str


class ServerConfigDict(TypedDict, total=False):
    """Server configuration settings."""

    host: str
    port: int
    workers: int


class DataConfigDict(TypedDict, total=False):
    """Data storage configuration settings."""

    path: str
    tickets_file: str
    employees_file: str
    customers_file: str
    services_file: str


class TicketConfigDict(TypedDict, total=False):
    """Ticket configuration settings."""

    queues: list[str]
    statuses: list[str]
    impacts: list[str]
    urgencies: list[str]
    types: list[str]
    default_queue: str
    default_status: str
    default_impact: str
    default_urgency: str


class EmployeeConfigDict(TypedDict, total=False):
    """Employee configuration settings."""

    access_roles: list[str]
    assignment_queues: list[str]
    default_role: str
    default_queue: str


class CustomerConfigDict(TypedDict, total=False):
    """Customer configuration settings."""

    statuses: list[str]
    fraud_risk_levels: list[str]
    default_status: str
    default_fraud_risk: str


class ServiceConfigDict(TypedDict, total=False):
    """Service configuration settings."""

    statuses: list[str]
    default_status: str


class SessionConfigDict(TypedDict, total=False):
    """Session configuration settings."""

    lifetime_hours: int


class WebhookPlatformConfigDict(TypedDict, total=False):
    """Webhook platform configuration."""

    enabled: bool
    webhook_url: str
    secret: str
    token: str
    api_key: str
    username: str
    avatar_url: str
    create_ticket_on_up: bool


class WebhookIngestConfigDict(TypedDict, total=False):
    """Inbound webhook configuration."""

    tailscale: WebhookPlatformConfigDict
    uptime_kuma: WebhookPlatformConfigDict
    generic: WebhookPlatformConfigDict


class WebhookEgressConfigDict(TypedDict, total=False):
    """Outbound webhook configuration."""

    discord: WebhookPlatformConfigDict
    slack: WebhookPlatformConfigDict
    teams365: WebhookPlatformConfigDict


class WebhooksConfigDict(TypedDict, total=False):
    """Webhooks configuration section."""

    ingest: WebhookIngestConfigDict
    egress: WebhookEgressConfigDict


class ConfigDict(TypedDict, total=False):
    """Main application configuration dictionary."""

    app: AppConfigDict
    server: ServerConfigDict
    data: DataConfigDict
    tickets: TicketConfigDict
    employees: EmployeeConfigDict
    customers: CustomerConfigDict
    services: ServiceConfigDict
    session: SessionConfigDict
    webhooks: WebhooksConfigDict


# =============================================================================
# Branding Configuration Types
# =============================================================================


class BrandInfoDict(TypedDict, total=False):
    """Brand information settings."""

    name: str
    tagline: str
    logo_url: str


class BrandColorsDict(TypedDict, total=False):
    """Brand color settings."""

    primary: str
    secondary: str
    background: str
    text: str


class BrandingDict(TypedDict, total=False):
    """Branding configuration dictionary."""

    brand: BrandInfoDict
    colors: BrandColorsDict


# =============================================================================
# Navbar Configuration Types
# =============================================================================


class NavLinkDict(TypedDict, total=False):
    """Navigation link definition."""

    label: str
    url: str
    submenu: list[NavLinkDict]


class NavbarSectionDict(TypedDict, total=False):
    """Navbar section configuration."""

    links: list[NavLinkDict]
    admin_links: list[NavLinkDict]


class NavbarDict(TypedDict, total=False):
    """Navbar configuration dictionary."""

    navbar: NavbarSectionDict
