# VaultWire - Headless Offline Installation Guide

This guide details the process of installing VaultWire onto a Raspberry Pi Zero 2 W in a completely headless and offline manner. This is the most secure installation method, as the Pi is never connected to the internet.

## Prerequisites

1.  **Host PC**: A Linux-based computer (Ubuntu, Debian, Fedora, etc.) to run the preparation script.
2.  **SD Card**: A MicroSD card.
3.  **DietPi OS**: Download the [DietPi](https://dietpi.com/) image for the Raspberry Pi (typically the `ARMv8 64-bit` image for the Pi Zero 2 W).
4.  **Flashing Software**: Use `balenaEtcher`, `Raspberry Pi Imager`, or `dd` to flash the DietPi OS image onto your SD card.
5.  **Docker**: Ensure Docker is installed on your Host PC (along with `qemu-user-static` for multi-architecture builds if necessary).

## Step-by-Step Installation

### Step 1: Flash the SD Card

First, flash the standard DietPi OS image to your MicroSD card. Do **not** plug the SD card into the Raspberry Pi yet. Keep the SD card handy, as you will insert it into your host PC during the next step.

### Step 2: Prepare the SD Card

On your host PC, navigate to the VaultWire repository and run the `prepare_sd.sh` script as root.

```bash
cd vaultwire/host/scripts
sudo ./prepare_sd.sh
```

**What this script does:**
1.  **Docker Build**: It initiates a Docker container to cross-compile the required Python wheels (`.whl`) and download the necessary `apt` Debian packages (`.deb`) for the ARM64 architecture.
2.  **Identify SD Card**: It will ask you to insert your flashed SD card and help you identify its device name (e.g., `sdb` or `mmcblk0`).
3.  **Transfer Files**: It mounts the SD card partitions and transfers the VaultWire daemon source code (`pi/`), Python wheels, and Debian packages.
4.  **Configure `dietpi.txt`**: It modifies DietPi's boot configuration to aggressively disable networking (WiFi and Ethernet) while maintaining Bluetooth (for the development keyboard), and instructs DietPi to run our custom offline automation script.
5.  **Create Automation Script**: It generates an `Automation_Custom_Script.sh` on the boot partition. This script runs automatically on the Pi's very first boot to install the transferred packages, set up the Python virtual environment, disable swap (a critical security requirement), and install the systemd service.

### Step 3: Boot the Raspberry Pi

1.  Safely eject the SD card from your host PC.
2.  Insert the SD card into your Raspberry Pi Zero 2 W.
3.  Connect the Pi to your host PC using the USB data cable (this provides power and acts as the HID connection).
4.  Wait for the Pi to boot. DietPi will automatically expand the filesystem, restart, and then execute the custom automation script. This process can take a few minutes.
5.  Once complete, the VaultWire daemon (`vault_daemon.py`) will automatically start in the background, waiting for input via your connected Bluetooth keyboard.

## Troubleshooting

*   **Docker Build Fails**: Ensure you have multi-architecture support enabled on your host PC. The script attempts to run `docker run --rm --privileged multiarch/qemu-user-static --reset -p yes` to facilitate this.
*   **Daemon Fails to Start**: You can check the setup logs by inserting the SD card back into your host PC and reading `/var/log/vaultwire_setup.log` from the root partition.

## Security Note

This process ensures that the Pi operates with zero network footprint. By disabling swap memory and installing the software offline, VaultWire's architecture ensures no plaintext data is ever swapped to persistent storage and no external attacks can be performed over a network.
