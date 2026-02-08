#!/bin/bash
cd "$(dirname "$0")/.."

# Check/Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
fi

# Upgrade pip if needed (silently)
./.venv/bin/pip install --upgrade pip > /dev/null 2>&1

# SOTA: Always install deps via venv before starting
# This ensures new requirements are picked up even if angel.py update logic fails
../.venv/bin/pip install -r requirements.txt

# Launch Angel directly with venv python
# Angel will then spawn Trinity using sys.executable (which is this venv python)
./.venv/bin/python angel.py
