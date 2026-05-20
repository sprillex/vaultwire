# VaultWire - Phase 1 Setup Documentation

## Overview
This document outlines the strict environmental setup procedures for both the Linux Mint host machine and the Raspberry Pi Zero 2 W running DietPi. These instructions adhere to the core architectural constraints: utilizing Python Virtual Environments (`venv`), avoiding global `pip`, and maintaining strict system isolation.

## 1. Directory Structure
```
vaultwire/
├── host/
│   ├── requirements.txt
│   └── scripts/
│       └── setup_host.sh
├── pi/
│   ├── requirements.txt
│   ├── daemon/
│   └── scripts/
│       └── setup_pi.sh
├── docker/
│   ├── Dockerfile
│   └── build_wheels.sh
└── docs/
    └── PHASE_1_SETUP.md
```

## 2. Linux Mint Host Setup

The host companion app requires a Python virtual environment to manage dependencies.

### Prerequisites
Ensure the system has Python 3 and the `venv` module installed.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev build-essential
```

### Environment Initialization
Run the host setup script or execute the following manually:

```bash
cd host
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

To exit the environment: `deactivate`

## 3. DietPi Setup (Raspberry Pi Zero 2 W)

The Pi daemon requires specific hardware interaction libraries and the KeePass parser.

### Prerequisites
Install system-level dependencies required for building C-extensions (if needed) and virtual environments.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev build-essential libffi-dev libssl-dev
```

### Environment Initialization
Run the Pi setup script or execute the following manually:

```bash
cd pi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

*Note: For complex dependencies on ARM, utilize the Docker build process to generate pre-compiled wheels.*

## 4. Docker Cross-Compilation (ARM Wheels)

To avoid compiling heavy cryptographic libraries on the Pi Zero 2 W, we use a multi-architecture Docker build on a more powerful machine.

### Prerequisites
Ensure Docker is installed and configured for `buildx`.

```bash
# Enable multi-arch execution
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx create --use
```

### Building Wheels
Execute the build script in the `docker/` directory:

```bash
cd docker
./build_wheels.sh
```

This will output `.whl` files to a `dist/` folder, which can be transferred to the Pi via Sync Mode and installed inside the Pi's `.venv` using `pip install *.whl`.
