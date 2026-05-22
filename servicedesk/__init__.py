"""Service Desk - Open Source ITSM Application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Flask

from servicedesk.config import load_branding, load_config
from servicedesk.extensions import login_manager

if TYPE_CHECKING:
    from flask import Flask as FlaskApp

__version__ = "0.1.0"


def create_app(config_path: Path | None = None) -> FlaskApp:
    """Create and configure the Flask application.

    Args:
        config_path: Optional path to configuration directory.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Determine config path
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config"

    # Load configuration
    config = load_config(config_path / "configuration.yml")
    branding = load_branding(config_path / "branding.yml")

    # Flask configuration
    app.config["SECRET_KEY"] = os.environ.get("FLASK_APP_SECRET_KEY", "dev-secret-change-me")
    app.config["APP_CONFIG"] = config
    app.config["BRANDING"] = branding
    app.config["CONFIG_PATH"] = config_path
    app.config["DATA_PATH"] = Path(config.get("data", {}).get("path", "data"))

    # Ensure data directory exists
    data_path = Path(app.config["DATA_PATH"])
    if not data_path.is_absolute():
        data_path = Path(__file__).parent.parent / data_path
    data_path.mkdir(parents=True, exist_ok=True)
    app.config["DATA_PATH"] = data_path

    # Initialize extensions
    login_manager.init_app(app)

    # Register context processors
    @app.context_processor
    def inject_branding() -> dict[str, object]:
        """Inject branding into all templates."""
        return {"branding": branding}

    # Register blueprints
    _register_blueprints(app)

    return app


def _register_blueprints(app: FlaskApp) -> None:
    """Register all application blueprints.

    Args:
        app: Flask application instance.
    """
    from servicedesk.blueprints.public import public_bp
    from servicedesk.blueprints.setup import setup_bp
    from servicedesk.blueprints.itsm import itsm_bp
    from servicedesk.blueprints.hr import hr_bp
    from servicedesk.blueprints.crm import crm_bp
    from servicedesk.blueprints.services import services_bp
    from servicedesk.blueprints.changes import changes_bp
    from servicedesk.blueprints.reports import reports_bp
    from servicedesk.blueprints.api_ingest import api_ingest_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(setup_bp, url_prefix="/setup")
    app.register_blueprint(itsm_bp, url_prefix="/itsm")
    app.register_blueprint(hr_bp, url_prefix="/hr")
    app.register_blueprint(crm_bp, url_prefix="/crm")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(changes_bp, url_prefix="/changes")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(api_ingest_bp, url_prefix="/api")
