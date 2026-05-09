# Self-Hosted ITSM Service Desk

- Use Python3, HTML5, CSS3, and vanilla JavaScript
- Use Flask with Gunicorn
- Expect Caddy Reverse Proxy
- Expect to run on a low resource machine
- Platform Branding should come from a branding.yml file
- Application configuration should happen in configuration.yml
- Should track tickets, customers, employees, and services
- Public_NavBar should be configurable from a YAML file
- Employee_NavBar should be configurable from a YAML file
- Store data in YAML, JSON, and CSV before databases.
- Use Flask Blueprints

Home Page/index.html should contain....

- Basic navigation bar
    - Link to Login
    - Link to Sign-Up
- Ticket submission

### Basic ITSM Ticket management (ITSM)

Somehow I'd like to be able to link Services, Customers, and Tickets to see linked impact.

**Queues:** support,escalation,billing

/itsm/queues/<queue_name> should render all tickets assigned to X queue and are not ticket_status resolved.

**Status:** new,in_progress,on_hold,resolved,cancelled

New tickets should be assigned to the support queue with assigned_technician as None or Null

/itsm/ should direct towards /itsm/dashoard
/itsm/dashboard should render all tickets assigned to support queue and are not ticket_status resolved

/itsm/console/<ticket_number> should render the ticket content. Logged In User should be able to change the status, and add ticket_worknotes.

    uuid
    ticket_number
    ticket_status (Default:new)
    requestor_name
    requestor_username
    ticket_type
    ticket_subject
    ticket_body
    ticket_impact (Default:low)
    ticket_urgency (Default:low)
    escalation_level (Default:0)
    assigned_queue (Default:support)
    assigned_technician (Default:none)
    ticket_worknotes
    ticket_resolution_notes
    ticket_created_timestamp (year-month-day-24:00)
    ticket_escalation_timestamp (year-month-day-24:00)
    ticket_closed_timestamp (year-month-day-24:00)
    ticket_acknowledged_timestamp
    requestor_vip_status (Default:false)
    ticket_overdue (Default:false)

### Employee & Access Management (HR)

/hr/ should auto-direct towards /hr/dashboard
/hr/dashboard should display....

- Basic Nav Bar
- Create New Customer button
- Export as CSV button
- EMID, First Name, Last name, Title, Access Role

/hr/profile/<employee_id> should display all options.
/hr/submit-new should allow the input of all options

**Employee Access Roles:** none,technician,admin (links to decorators)

**Employee Titles:** should render from a YAML

    uuid
    employee_id (EM)
    employee_first_name
    employee_last_name
    employee_preferred_name
    employee_dob (year-month-day)
    employee_email
    employee_phone
    employee_timezone
    employee_ingame_username
    employee_chat_userid
    employee_hire_date (year-month-day)
    employee_termination_date (Default:null)
    employment_status
    rehire_status (Default:yes)
    employee_title (Default:technician)
    employee_access_role
    employee_compensation_type
    employee_base_salary
    employee_hourly_rate
    employee_salary_exempt (Default:no)
    is_bonus_eligible (Default:no)
    employee_bonus_rate (Default:0)
    assigned_business_unit (Default:support)
    employee_access_role (Default:technician)
    employee_assignment_queue (Default:support)
    employee_total_pto_available (Default:0)
    reports_to (Default:null)
    employee_mfa_enabled
    employee_last_login
    employee_password_last_changed
    employee_account_locked (Default: true)
    failed_login_attempts
    has_freshrss_access
    has_jellyfin_access
    has_nextcloud_access
    has_tailnet_access
    has_gitea_access
    has_discord_access
    has_slack_access

### Customer Tracker (CRM)

/crm/ should auto-direct towards /crm/dashboard
/crm/dashboard should display....
- Basic Nav Bar
- Create New Customer button
- Export as CSV button
- CID, First Name, Last name, Account Value, Account Status

/crm/profile/<uuid> should display all options.
/crm/submit-new should allow the input of all options

    uuid
    customer_id (CID)
    customer_first_name
    customer_last_name
    customer_preferred_name
    customer_ingame_username
    customer_discord_user_id
    customer_contact_email
    customer_account_created_date (year-month-day)
    customer_account_status (Default:active)
    customer_fraud_risk (Default:low)
    customer_vip_status (Default:no)
    customer_account_value
    is_content_creator (Default:no)
    vat_taxid (Default:null)
    customer_mfa_enabled
    customer_last_login
    password_last_changed
    customer_account_locked
    customer_last_login
    customer_last_order_date
    customer_last_payment_date
    customer_total_lifetime_value
    customer_status_reason
    preferred_contact_method
    marketing_opt_in
    maintenance_notifications_enabled

### Service Database

/services/ should auto-direct towards /services/dashboard
/services/dashboard should display....

- Create New Service button
- Export as CSV button

Service ID, Service Name, Customer ID, Service Subdomain

/services/submit-new should allow the input of all options.
Should be able to link to an existing customer based on Customer ID

/services/profile/<service_id> 

    uuid
    service_id
    service_sku
    service_type
    service_name
    service_status
    provisioning_status
    service_ip
    service_subdomain
    service_created_timestamp
    service_terminated_timestamp
    service_updated_timestamp
    service_provision_source
    customer_uuid
    customer_id
    service_rcon_port
    service_rcon_pwd
    node_id
    cluster_id
    region
    allocated_ram_mb
    allocated_disk_gb
    allocated_cpu_cores
    allocated_ports
    minecraft_version
    server_type
    modpack_name
    player_limit
