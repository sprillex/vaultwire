#!/usr/bin/env bash
# Host setup script for VaultWire companion app

set -e

echo "Updating system and installing Python prerequisites..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev build-essential

echo "Initializing Python virtual environment..."
cd "$(dirname "$0")/.."
python3 -m venv .venv

echo "Activating virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Host setup complete."
