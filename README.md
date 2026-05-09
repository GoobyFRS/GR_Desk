# GR_Core

An open-source IT Service Management (ITSM) application built with Flask.

## Overview

GR_Core provides a complete solution for managing IT support operations, including:

- **Ticket Management (ITSM)** - Create, track, and resolve support tickets
- **Customer Management (CRM)** - Maintain customer profiles and account information
- **Employee Management (HR)** - Manage employee records, roles, and access
- **Service Management** - Track provisioned services and infrastructure

## Features

- Public ticket submission portal
- Employee authentication with role-based access control
- Multi-queue ticket routing (support, escalation, billing)
- Customer self-signup
- VIP customer prioritization
- Work notes and ticket history
- CSV export for customers, employees, and services
- YAML-based data storage (no database required)
- Configurable via YAML files

## Project Structure

```
MyProject/
├── app.py                      # Application entry point
├── config/                     # Configuration files
│   ├── configuration.yml       # Main app configuration
│   ├── branding.yml            # Branding/theming
│   ├── public_navbar.yml       # Public navigation
│   ├── employee_navbar.yml     # Employee navigation
│   ├── employee_titles.yml     # Job titles list
│   ├── business_units.yml      # Business units list
│   └── service_types.yml       # Service types list
├── data/                       # YAML data storage
│   ├── employees.yaml
│   ├── customers.yaml
│   ├── tickets.yaml
│   └── services.yaml
└── servicedesk/
    ├── __init__.py             # App factory
    ├── config.py               # Configuration loaders
    ├── extensions.py           # Flask extensions
    ├── auth/                   # Authentication
    │   ├── decorators.py       # Route decorators
    │   └── utils.py            # Password hashing
    ├── blueprints/             # Route handlers
    │   ├── public.py           # Public routes
    │   ├── setup.py            # Initial setup wizard
    │   ├── itsm.py             # Ticket management
    │   ├── hr.py               # Employee management
    │   ├── crm.py              # Customer management
    │   ├── services.py         # Service management
    │   ├── reports.py          # Reports and analytics
    │   └── api_ingest.py       # Webhook ingestion API
    ├── webhooks/               # Outbound webhooks
    │   └── egress.py           # Discord, Slack, Teams
    ├── models/                 # Data models
    │   ├── employee.py
    │   ├── customer.py
    │   ├── ticket.py
    │   └── service.py
    ├── storage/                # Data persistence
    │   ├── yaml_store.py       # Generic YAML storage
    │   └── csv_export.py       # CSV export utilities
    ├── templates/              # Jinja2 templates
    └── static/                 # CSS and JavaScript
```

## Development Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd MyProject
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install flask flask-login pyyaml bcrypt
   ```

4. Create a `.env` file (optional):
   ```bash
   FLASK_APP_SECRET_KEY=your-secret-key-here
   ```

### Running the Application

**Development server:**
```bash
python app.py
```

Or using Flask CLI:
```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`

### First Run

On first run, you'll be redirected to the setup wizard (`/setup/wizard`) to create the initial admin account.

## URL Routes

### Public Routes (No Authentication)

| URL | Method | Description |
|-----|--------|-------------|
| `/` | GET | Home page with ticket submission form |
| `/submit-ticket` | POST | Submit a new support ticket |
| `/login` | GET, POST | Employee login page |
| `/logout` | GET | Log out current user |
| `/signup` | GET, POST | Customer self-registration |

### Setup Routes

| URL | Method | Description |
|-----|--------|-------------|
| `/setup/` | GET, POST | Setup wizard (first-run only) |
| `/setup/wizard` | GET, POST | Setup wizard (first-run only) |

### ITSM Routes (Technician/Admin Required)

| URL | Method | Description |
|-----|--------|-------------|
| `/itsm/` | GET | Redirect to dashboard |
| `/itsm/dashboard` | GET | Support queue dashboard |
| `/itsm/queues/<queue_name>` | GET | View tickets in specific queue |
| `/itsm/console/<ticket_number>` | GET, POST | View/edit single ticket |

### HR Routes (Admin Required)

| URL | Method | Description |
|-----|--------|-------------|
| `/hr/` | GET | Redirect to dashboard |
| `/hr/dashboard` | GET | Employee list |
| `/hr/export` | GET | Download employees CSV |
| `/hr/profile/<employee_id>` | GET | View employee profile |
| `/hr/profile/<employee_id>/edit` | POST | Update employee profile |
| `/hr/submit-new` | GET, POST | Create new employee |

### CRM Routes (Technician/Admin Required)

| URL | Method | Description |
|-----|--------|-------------|
| `/crm/` | GET | Redirect to dashboard |
| `/crm/dashboard` | GET | Customer list |
| `/crm/export` | GET | Download customers CSV |
| `/crm/profile/<uuid>` | GET | View customer profile |
| `/crm/profile/<uuid>/edit` | POST | Update customer profile |
| `/crm/submit-new` | GET, POST | Create new customer |

### Services Routes (Technician/Admin Required)

| URL | Method | Description |
|-----|--------|-------------|
| `/services/` | GET | Redirect to dashboard |
| `/services/dashboard` | GET | Services list |
| `/services/export` | GET | Download services CSV |
| `/services/profile/<service_id>` | GET | View service profile |
| `/services/profile/<service_id>/edit` | POST | Update service profile |
| `/services/submit-new` | GET, POST | Create new service |

### Reports Routes (Technician/Admin Required)

| URL | Method | Description |
|-----|--------|-------------|
| `/reports/` | GET | Redirect to dashboard |
| `/reports/dashboard` | GET | Reports dashboard with analytics |
| `/reports/export/tickets` | GET | Export all tickets to CSV |
| `/reports/export/tickets/open` | GET | Export open tickets to CSV |

### API Routes (Webhooks)

| URL | Method | Description |
|-----|--------|-------------|
| `/api/health` | GET | API health check |
| `/api/tailscale` | POST | Tailscale webhook ingestion |
| `/api/uptime-kuma` | POST | Uptime Kuma webhook ingestion |
| `/api/generic` | POST | Generic webhook for ticket creation |

## Access Roles

| Role | Access Level |
|------|--------------|
| `none` | No system access |
| `technician` | ITSM, CRM, Services |
| `admin` | All modules including HR |

## Configuration

### Main Configuration (`config/configuration.yml`)

```yaml
app:
  name: "Service Desk"
  debug: false
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 5000

data:
  path: "data"

tickets:
  queues:
    - "support"
    - "escalation"
    - "billing"
  statuses:
    - "new"
    - "in_progress"
    - "on_hold"
    - "resolved"
    - "cancelled"
```

### Branding (`config/branding.yml`)

```yaml
brand:
  name: "GR_Core"
  tagline: "IT Service Management"

colors:
  primary: "#2563eb"
  background: "#f8fafc"
```

## Production Deployment

### Prerequisites

- Python 3.10+
- A Linux server with systemd
- Nginx (recommended as reverse proxy)

### Installation

1. Create the application directory and user:
   ```bash
   sudo mkdir -p /var/www/grcore
   sudo mkdir -p /var/log/grcore
   sudo chown www-data:www-data /var/www/grcore /var/log/grcore
   ```

2. Clone the repository and set up virtual environment:
   ```bash
   cd /var/www/grcore
   sudo -u www-data git clone <repository-url> .
   sudo -u www-data python3 -m venv venv
   sudo -u www-data venv/bin/pip install -r requirements.txt
   ```

3. Create environment file with secrets:
   ```bash
   sudo -u www-data cp .env.example .env
   sudo -u www-data nano .env  # Set FLASK_APP_SECRET_KEY
   ```

4. Install and enable the systemd service:
   ```bash
   sudo cp grcore.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable grcore
   sudo systemctl start grcore
   ```

5. Check service status:
   ```bash
   sudo systemctl status grcore
   sudo journalctl -u grcore -f  # View logs
   ```

### Nginx Configuration (Recommended)

Create `/etc/nginx/sites-available/grcore`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://unix:/run/grcore/grcore.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/grcore/servicedesk/static;
        expires 30d;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/grcore /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Service Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start grcore` | Start the service |
| `sudo systemctl stop grcore` | Stop the service |
| `sudo systemctl restart grcore` | Restart the service |
| `sudo systemctl status grcore` | Check status |
| `sudo journalctl -u grcore -f` | View live logs |

## License

Open Source - See LICENSE file for details.
