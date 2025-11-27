#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to that directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists in the parent directory
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Run the Flask App
python3 app.py
