#!/usr/bin/env python3
"""
Initialize v1.0 data structures for gr_desk.
This script creates empty JSON files with proper schema for all data models.
Run this when upgrading from v0.9.x to v1.0.x
"""

import json
import os
from pathlib import Path

DATA_DIR = "./my_data"

# Create data directory if it doesn't exist
Path(DATA_DIR).mkdir(exist_ok=True)

# Initialize tickets.json
tickets_file = os.path.join(DATA_DIR, "tickets.json")
if not os.path.exists(tickets_file) or os.path.getsize(tickets_file) == 0:
    with open(tickets_file, "w") as f:
        json.dump([], f, indent=4)
    print(f"✓ Initialized {tickets_file}")
else:
    print(f"⊙ {tickets_file} already exists (skipping)")

# Initialize changes.json
changes_file = os.path.join(DATA_DIR, "changes.json")
if not os.path.exists(changes_file) or os.path.getsize(changes_file) == 0:
    with open(changes_file, "w") as f:
        json.dump([], f, indent=4)
    print(f"✓ Initialized {changes_file}")
else:
    print(f"⊙ {changes_file} already exists (skipping)")

# Initialize customers.json
customers_file = os.path.join(DATA_DIR, "customers.json")
if not os.path.exists(customers_file) or os.path.getsize(customers_file) == 0:
    with open(customers_file, "w") as f:
        json.dump([], f, indent=4)
    print(f"✓ Initialized {customers_file}")
else:
    print(f"⊙ {customers_file} already exists (skipping)")

# Initialize employees.json
employees_file = os.path.join(DATA_DIR, "employees.json")
if not os.path.exists(employees_file) or os.path.getsize(employees_file) == 0:
    with open(employees_file, "w") as f:
        json.dump([], f, indent=4)
    print(f"✓ Initialized {employees_file}")
else:
    print(f"⊙ {employees_file} already exists (skipping)")

# Knowledge base initialization removed (KB module deprecated)

print("\n✓ gr_desk v1.0 data structures initialized successfully!")
