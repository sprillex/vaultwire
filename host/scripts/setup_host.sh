#!/usr/bin/env bash
# Host setup script for VaultWire companion app

set -e

# Error handler
trap 'echo "Error encountered during setup. Exiting."; exit 1' ERR

echo "Updating system and installing Python prerequisites..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev build-essential

echo "Initializing Python virtual environment..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Activating virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found in host directory."
fi

echo "Host setup complete."
