# VaultWire - Phase 1 Setup Documentation

## Overview
This document outlines the strict environmental setup procedures for both the host machine and the Raspberry Pi Zero 2 W running DietPi. These instructions adhere to the core architectural constraints: utilizing Python Virtual Environments (`venv`), avoiding global `pip`, and maintaining strict system isolation.

## 1. Directory Structure
```
vaultwire/
├── host/
│   ├── requirements.txt
│   ├── src/
│   │   ├── main.py
│   │   ├── ui.py
│   │   ├── sync.py
│   │   └── storage.py
│   └── scripts/
│       └── setup_host.sh
├── pi/
│   ├── requirements.txt
│   ├── src/
│   │   ├── vault_daemon.py
│   │   └── hid_gadget.sh
│   └── scripts/
│       └── setup_pi.sh
├── docker/
│   ├── Dockerfile
│   └── build_wheels.sh
└── docs/
    └── PHASE_1_SETUP.md
```

## 2. Host Setup

The host companion app requires a Python virtual environment to manage dependencies (like cryptography).

### Environment Initialization
Run the host setup script which robustly creates a virtual environment and installs dependencies:

```bash
cd host/scripts
./setup_host.sh
```

To run the application:
```bash
cd host
source .venv/bin/activate
python3 src/main.py --data-file ~/my_vault_index.json
```

## 3. DietPi Setup (Raspberry Pi Zero 2 W)

The Pi daemon requires specific hardware interaction libraries and the KeePass parser.

### OS Hardening: Disabling Swap
Because VaultWire decrypts vaults directly into RAM, it is critical to disable the OS swap file to prevent unencrypted password fragments from persisting on the SD card. Execute the following on the Pi:

```bash
sudo systemctl disable dphys-swapfile
sudo dphys-swapfile swapoff
sudo dphys-swapfile uninstall
sudo rm /var/swap
```

### Environment Initialization
Run the Pi setup script to establish the virtual environment:

```bash
cd pi/scripts
./setup_pi.sh
```

*Note: For complex dependencies on ARM, utilize the Docker build process to generate pre-compiled wheels.*

## 4. Docker Cross-Compilation (ARM Wheels)

To avoid compiling heavy cryptographic libraries on the Pi Zero 2 W, we use a multi-architecture Docker build on a more powerful machine.

### Prerequisites
Ensure Docker is installed and configured for `buildx`.

### Building Wheels
Execute the build script in the `docker/` directory from your host machine (not inside the container):

```bash
cd docker
docker build -t vaultwire-arm-builder .
```

The Dockerfile explicitly uses Docker buildx to emulate ARM architecture, builds the wheels listed in `pi/requirements.txt`, and uses `/build_wheels.sh` as its entrypoint. By running the container (e.g. `docker run -v $(pwd)/dist:/out_cache vaultwire-arm-builder`), the `.whl` files are output to a local `docker/dist/` folder. These files can then be securely transferred to the Pi and installed inside the Pi's `.venv` using `pip install *.whl`.
