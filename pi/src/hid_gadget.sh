#!/usr/bin/env bash
# Initialize VaultWire USB Gadget using ConfigFS
# This script must be run as root during boot.

set -e

# Error handler
trap 'echo "Error during USB gadget initialization. Exiting."; exit 1' ERR

GADGET_DIR="/sys/kernel/config/usb_gadget/vaultwire"

# Check for required modules
modprobe libcomposite
modprobe dwc2

# Clear out any existing gadget setup
if [ -d "$GADGET_DIR" ]; then
    echo "Gadget already exists. Tearing down..."
    cd "$GADGET_DIR" || exit 1
    # Remove binding
    if [ -e "UDC" ]; then
        echo "" > UDC
    fi
    # Remove functions from config
    for config_func in configs/c.1/*; do
        if [ -e "$config_func" ] && [ ! "$config_func" = "configs/c.1/strings" ] && [ ! "$config_func" = "configs/c.1/MaxPower" ] && [ ! "$config_func" = "configs/c.1/bmAttributes" ]; then
            rm -f "$config_func"
        fi
    done

    # Remove strings, configs, functions
    rm -rf configs/c.1/strings/0x409 2>/dev/null || true
    rmdir configs/c.1 2>/dev/null || true
    rmdir functions/hid.usb0 2>/dev/null || true
    rmdir functions/mass_storage.usb0 2>/dev/null || true
    rm -rf strings/0x409 2>/dev/null || true
    cd /
    rmdir "$GADGET_DIR" 2>/dev/null || true
fi

# Determine Mode
# Read GPIO 17 (Switch) to determine mode. A value of 1 (bridged/closed) means Mass Storage mode.
# Default is 0 (open), meaning HID Vault mode.
MODE="HID"

if [ -d "/sys/class/gpio/gpio17" ]; then
    VAL=$(cat /sys/class/gpio/gpio17/value)
    if [ "$VAL" -eq "1" ]; then
        MODE="MASS_STORAGE"
    fi
fi

echo "Initializing USB Gadget in $MODE mode..."

# Create gadget
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# Set identity (VaultWire)
echo 0x1d6b > idVendor  # Linux Foundation
echo 0x0104 > idProduct # Multifunction Composite Gadget
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0200 > bcdUSB    # USB 2.0

mkdir -p strings/0x409
echo "fedcba9876543210" > strings/0x409/serialnumber
echo "VaultWire" > strings/0x409/manufacturer
echo "VaultWire Security Device" > strings/0x409/product

# Create configuration
mkdir -p configs/c.1/strings/0x409
echo "Config 1: ECM network" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

if [ "$MODE" = "HID" ]; then
    # Create HID function (Keyboard)
    mkdir -p functions/hid.usb0
    echo 1 > functions/hid.usb0/protocol
    echo 1 > functions/hid.usb0/subclass
    echo 8 > functions/hid.usb0/report_length
    # Standard HID keyboard report descriptor
    echo -ne \\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0 > functions/hid.usb0/report_desc

    # Link function to config
    ln -s functions/hid.usb0 configs/c.1/

    # Enable UDC
    ls /sys/class/udc > UDC

    # Wait for device node creation
    sleep 1

    # Grant access to the unprivileged vault_daemon user
    if id "vault_daemon" >/dev/null 2>&1; then
        chown vault_daemon:vault_daemon /dev/hidg0
        chmod 660 /dev/hidg0
    fi

    # Ensure vault.img is internally mounted for Vault Mode as Read-Only
    mkdir -p /mnt/vault
    if [ -f "/opt/vaultwire/vault.img" ]; then
        # Check if already mounted
        if ! mountpoint -q /mnt/vault; then
             mount -o ro,noexec,nosuid,nodev,loop /opt/vaultwire/vault.img /mnt/vault
        fi
    fi

elif [ "$MODE" = "MASS_STORAGE" ]; then
    # Create Mass Storage function
    mkdir -p functions/mass_storage.usb0

    # Make sure we only expose the vault image, not the whole OS
    if [ ! -f "/opt/vaultwire/vault.img" ]; then
        echo "Error: /opt/vaultwire/vault.img not found! Cannot expose storage."
        exit 1
    fi

    # Expose the image as a removable USB drive
    echo "/opt/vaultwire/vault.img" > functions/mass_storage.usb0/lun.0/file
    echo 1 > functions/mass_storage.usb0/lun.0/removable

    # Link function to config
    ln -s functions/mass_storage.usb0 configs/c.1/

    # Enable UDC
    ls /sys/class/udc > UDC
fi

echo "USB Gadget Initialization Complete."
