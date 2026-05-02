## Code Quality

Project must be based on Python3 and Flask. It should be meant to run behind Caddy -> Gunicorn.

- Use flask blueprints
- no sql databases
- Use Jinja for HTML templates.
- Follow HTML5 W3 best practices for modern  and accessible web.
- Single css file with all elements. Reuse as many as possible.
- Single JavaScript file for all scripts.
- Strict PEP8 compliant Python
- configuration via configuration.yml
- custom branding via custom.yml
- Secrets stored and referenced in a DOTENV file.
- Use decorators to perform access control.

## Core Features

- IT Ticket / Service Desk
- Support Ticket Metrics Reporting
- Knowledge Base

### Secondary Features

- Customer Management
- Employee Management
- Discord ChatOps
- Slack ChatOps

### IT Ticket Service Desk

Home/Landing/index.html page should be the primary ticket submission page. Getting the following information from the end-user.

1. Name (requestor_name)
2. In-Game Username (requestor_username)
3. Ticket Type (ticket_type)
4. Ticket Subject (ticket_ subject)
5. Ticket Description (ticket_body)

Tickets can be assigned a Urgency level 1 thru 5.

1. Critical
2. High
3. Medium
4. Low
5. Planning

Tickets can be assigned an Impact level 1 thru 4.

1. High
2. Medium
3. Low
4. Unknown

**Ticket Types:** 

1. Request - General Support.
2. Change - Requesting/Executing changes to configuration or access.
3. Incident - Something broke when it shouldn't have. 
4. Billing - Billing, Payments, Refunds.

**Ticket Numbers:** By default, all new tickets should have a ticket_number of TKT<YEAR>-<N+1> with four 0 padding. (TKT2026-0001 or TKT2026-0234)

**Ticket Status:** new, in_progress, on_hold, closed, cancelled

Use json key-value pairs to store and sort this data.

**Ticket JSON Key:Values**

- uuid
- ticket_number
- ticket_status (Default:new)
- requestor_name
- requestor_username
- ticket_type
- ticket_subject
- ticket_body
- ticket_impact (Default:low)
- ticket_urgency (Default:low)
- escalation_level (Default:0)
- assigned_team_queue (Default:support)
- assigned_support_person (Default:none)
- ticket_worknotes
- ticket_created_timestamp (year-month-day-24:00)
- ticket_escalation_timestamp (year-month-day-24:00)
- ticket_closed_timestamp (year-month-day-24:00)
- ticket_acknowledged_timestamp
- requestor_vip_status (Default:false)
- ticket_overdue (Default:false)

**Access Roles:** everyone, technician, manager

### Service Desk Change Module

- uuid
- change_number (CHG<YEAR>-0000)
- change_status (Default:new)
- change_requestor
- assigned_team_queue (Default:support)
- change_implementor
- change_subject
- change_description
- change_rollback_plan
- change_implement_plan
- change_test_plan
- change_start_timestamp (year-month-day 24:00)
- change_end_timestamp (year-month-day 24:00)
- change_to_appid (Default:null)

### Service Desk Reporting Module

- Total Open Count
- Total Closed
- Current Open Count
- Open Last 7 Days
- Closed Last 7 Days
- Open Last 30 Days
- Closed Last 30 Days
- Closed Count per Technician

### Service Desk Ingest API Endpoint Module

- uptime-kuma
- tailscale
- CubeCoders AMP
- newrelic

### Service Desk Egress API Endpoint Module

- newrelic

## Customer Management Platform

Not sure if JSON or YAML would be better for this.

**Fraud Risk Levels:** unknown, low, medium, high

**Account Statuses:** Active, inactive, banned, requested_closed

**Customer Key:Values**

- uuid
- customer_id (C<count>)
- customer_username
- customer_first_name
- customer_last_name
- customer_prefered_name
- customer_ingame_username
- customer_contact_email
- customer_account_created_date (year-month-day)
- customer_account_status (Default:active)
- customer_fraud_risk (Default:low)
- customer_vip_status (Default:no)
- customer_account_value
- customer_helpdesk_tickets
- is_content_creator (Default:no)

## Employee Management Platform

Not sure if JSON or YAML would be better for this.

- uuid
- employee_id (EM<count>)
- employee_first_name
- employee_last_name
- employee_preferred_name
- employee_age
- employee_dob (year-month-day)
- employee_state
- employee_ingame_username
- employee_chat_userid
- employee_hire_date (year-month-day)
- employee_termination_date (Default:null)
- rehire_status (Default:yes)
- employee_role (Default:technician)
- employee_compensation (Default:null)
- salary_exempt (Default:no)
- is_bonus_eligible (Default:no)
- bonus_rate (Default:0)
- assigned_business_unit (Default:support)
- access_role (Default:technician)
- employee_pip_count (Default:0)
- has_active_pip (Default:no)
- is_on_probation (Default:no)
- total_pto_available (Default:0)
- reports_to (Default:null)

### Service Desk Technical Operations

- Tickets should be assigned to the support queue by default
- Tickets should send a Slack/Discord webhook when they are created, escalated, or closed.
- ITSM Dashboard should have a method to close a ticket without opening the console view
- Ticket console view should be able to mark in-progress, mark closed, and leave work notes.
- Tickets should have the ability to be escalated.

### Predictable URL Structure

```/``` - index.html

```/login``` - Login Page

```/itsm/dashboard``` - Employee Specific Queue

```/itsm/queue/triage``` - Display un-assigned tickets.

```/itsm/queue/support``` - Display Support Team ticket queue.

```/itsm/queue/billing``` - Display Billing Team ticket queue.

```/itsm/console/<ticket_number>``` - Ticket Console view

```/reports``` - IT Service Management Reporting Module

```/changes``` - Change Management Module

```/changes/submit-new``` - Submit a new change

```/changes/console/<change_number>``` Change Console view

```/api/tailscale``` - Tailscale Notifications

```/api/uptimekuma``` - Uptime-Kuma Notifications

```/api/newrelic``` - New Relic alerts

```/api/amp``` - CubeCoders AMP Alerts and Events

```/crm/dashboard``` - Customer Dashboard

```/crm/submit-new``` - Saves new Customer to the file

```/crm/profile/<uuid>``` - View customer profile

```/crm/profile/<uuid>/edit``` - Save edits?

```/hrm/dashboard```

```/hrm/submit-new```

```/hrm/profile/<uuid>```

```/hrm/profile/<uuid>/edit```

```/kb``` - Knowledge Base Home

```/kb/minecraft```

```/kb/account```