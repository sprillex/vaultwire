#!/usr/bin/env bash
# Prepares a DietPi SD card for offline headless setup.

echo "=== VaultWire SD Card Offline Preparation Tool ==="

# Check for root since we will mount partitions
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (e.g. sudo ./prepare_sd.sh)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Step 1: Ensure Docker dependencies are built
echo ""
echo "Step 1: Checking offline dependencies (Wheels and Debs)"
DIST_DIR="$REPO_ROOT/docker/dist"
if [ ! -d "$DIST_DIR/wheels" ] || [ ! -d "$DIST_DIR/debs" ] || [ -z "$(ls -A $DIST_DIR/wheels 2>/dev/null)" ]; then
    echo "Dependencies not found in $DIST_DIR."
    echo "Running Docker build process to generate ARM packages..."
    cd "$REPO_ROOT/docker"
    ./build_wheels.sh
    cd "$SCRIPT_DIR"
else
    echo "Offline dependencies found in $DIST_DIR."
fi

# Step 2: Identify SD Card
echo ""
echo "Step 2: Identify SD Card"
echo "Currently attached block devices:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -v loop

echo ""
read -p "Please insert your flashed DietPi SD card into the host computer and press [Enter]..."
echo "Scanning for new devices..."
sleep 3
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -v loop


echo ""
read -p "Enter the path to your KeePass database (.kdbx) file: " KDBX_PATH
if [ ! -f "$KDBX_PATH" ]; then
    echo "Error: File not found at $KDBX_PATH"
    kill -INT $$
fi

echo ""
read -p "Enter the base device name of your SD card (e.g., sdb or mmcblk0): " SD_DEV

if [ ! -b "/dev/$SD_DEV" ]; then
    echo "Error: /dev/$SD_DEV is not a valid block device."
    exit 1
fi

# Detect partitions. mmcblk0 uses p1, p2. sdb uses sdb1, sdb2.
if [[ "$SD_DEV" == mmcblk* ]]; then
    BOOT_PART="/dev/${SD_DEV}p1"
    ROOT_PART="/dev/${SD_DEV}p2"
else
    BOOT_PART="/dev/${SD_DEV}1"
    ROOT_PART="/dev/${SD_DEV}2"
fi

if [ ! -b "$BOOT_PART" ] || [ ! -b "$ROOT_PART" ]; then
    echo "Error: Could not find partitions $BOOT_PART and $ROOT_PART."
    exit 1
fi

# Step 3: Mount partitions

echo ""
read -p "Enter the MAC address of your Bluetooth Keyboard (e.g. 1A:2B:3C:4D:5E:6F) or leave blank to skip: " BT_MAC

echo ""
echo "Step 3: Mounting partitions..."
MNT_BOOT=$(mktemp -d)
MNT_ROOT=$(mktemp -d)

mount "$BOOT_PART" "$MNT_BOOT"
mount "$ROOT_PART" "$MNT_ROOT"

trap "umount $MNT_BOOT; umount $MNT_ROOT; rmdir $MNT_BOOT $MNT_ROOT; echo 'Cleanup done.'" EXIT

# Step 4: Transfer files
echo ""
echo "Step 4: Transferring VaultWire files to SD card rootfs (/opt/vaultwire)..."
VW_TARGET="$MNT_ROOT/opt/vaultwire"
mkdir -p "$VW_TARGET"
cp -r "$REPO_ROOT/pi" "$VW_TARGET/"


# Step 4b: Create Isolated Storage Container (vault.img)
echo ""
echo "Step 4b: Creating encrypted vault container (vault.img)..."
# Create a 64MB FAT32 image for mass storage exposure
dd if=/dev/zero of="$VW_TARGET/vault.img" bs=1M count=64 status=none
mkfs.vfat "$VW_TARGET/vault.img" > /dev/null

# Mount the image via loopback to copy the file
MNT_VAULT=$(mktemp -d)
mount -o loop "$VW_TARGET/vault.img" "$MNT_VAULT"
cp "$KDBX_PATH" "$MNT_VAULT/vault.kdbx"
umount "$MNT_VAULT"
rm -rf "$MNT_VAULT"
echo "KeePass database successfully injected into vault.img"

# Create offline directory for dependencies
OFFLINE_DIR="$VW_TARGET/offline_deps"
mkdir -p "$OFFLINE_DIR"
cp -r "$DIST_DIR/wheels" "$OFFLINE_DIR/"
cp -r "$DIST_DIR/debs" "$OFFLINE_DIR/"

# Step 5: Configure dietpi.txt

if [ -n "$BT_MAC" ]; then
    echo "$BT_MAC" > "$MNT_BOOT/bt_mac.txt"
fi

echo ""
echo "Step 5: Configuring dietpi.txt for headless offline boot..."
DIETPI_TXT="$MNT_BOOT/dietpi.txt"
if [ -f "$DIETPI_TXT" ]; then
    # Disable networking (WiFi & Ethernet)
    sed -i 's/AUTO_SETUP_NET_ETHERNET_ENABLED=1/AUTO_SETUP_NET_ETHERNET_ENABLED=0/g' "$DIETPI_TXT"
    sed -i 's/AUTO_SETUP_NET_WIFI_ENABLED=1/AUTO_SETUP_NET_WIFI_ENABLED=0/g' "$DIETPI_TXT"

    # We still want bluetooth since it's required for the development phase
    sed -i 's/AUTO_SETUP_BLUETOOTH_ENABLED=0/AUTO_SETUP_BLUETOOTH_ENABLED=1/g' "$DIETPI_TXT" || true

    # Enable custom automation script
    sed -i 's/AUTO_SETUP_AUTOMATED=0/AUTO_SETUP_AUTOMATED=1/g' "$DIETPI_TXT"
    sed -i 's/AUTO_SETUP_GLOBAL_PASSWORD=.*/AUTO_SETUP_GLOBAL_PASSWORD=dietpi/g' "$DIETPI_TXT"
    sed -i 's/AUTO_SETUP_CUSTOM_SCRIPT_EXEC=0/AUTO_SETUP_CUSTOM_SCRIPT_EXEC=1/g' "$DIETPI_TXT"
else
    echo "Warning: dietpi.txt not found on boot partition."
fi

# Step 6: Create the custom first-boot script
echo ""
echo "Step 6: Creating Custom Automation Script..."
cat << 'BOOTSCRIPT' > "$MNT_BOOT/Automation_Custom_Script.sh"
#!/usr/bin/env bash
# DietPi Custom First-Boot Automation Script for VaultWire

echo "Starting VaultWire Offline Setup..." > /var/log/vaultwire_setup.log

# 1. Install offline deb packages
cd /opt/vaultwire/offline_deps/debs
dpkg -i *.deb >> /var/log/vaultwire_setup.log 2>&1 || echo "Some deb installations may have failed (check dependencies)." >> /var/log/vaultwire_setup.log

# Fix any broken dependencies silently just in case (though it's offline)
apt-get install -f -y >> /var/log/vaultwire_setup.log 2>&1 || true

# 2. Setup Python environment for Pi
cd /opt/vaultwire/pi
python3 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links /opt/vaultwire/offline_deps/wheels -r requirements.txt >> /var/log/vaultwire_setup.log 2>&1

# 3. Disable Swap (VaultWire hard requirement)
systemctl disable dphys-swapfile || true
dphys-swapfile swapoff || true
dphys-swapfile uninstall || true
rm -f /var/swap || true

# 4. Setup systemd service for vault_daemon
cat << 'SERVICE' > /etc/systemd/system/vaultwire.service
[Unit]
Description=VaultWire Daemon
After=network.target

[Service]
ExecStart=/opt/vaultwire/pi/.venv/bin/python /opt/vaultwire/pi/src/vault_daemon.py
WorkingDirectory=/opt/vaultwire/pi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable vaultwire.service

# 5. Setup ConfigFS hid_gadget.sh to run on boot
cat << 'GADGETSERVICE' > /etc/systemd/system/vaultwire-gadget.service
[Unit]
Description=VaultWire USB HID Gadget Init
Before=vaultwire.service

[Service]
Type=oneshot
ExecStart=/bin/bash /opt/vaultwire/pi/src/hid_gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
GADGETSERVICE

systemctl daemon-reload
systemctl enable vaultwire-gadget.service

# 6. Hello World Notification
# Run the hid gadget initialization manually now so we can type
/bin/bash /opt/vaultwire/pi/src/hid_gadget.sh >> /var/log/vaultwire_setup.log 2>&1
# Wait a moment for the USB host to recognize the new gadget
sleep 5

# Type "Hello world" and hit Enter.
# Using standard bash echo to /dev/hidg0.
# The USB HID keyboard protocol requires 8 bytes per report.
# Byte 0: Modifiers
# Byte 1: Reserved
# Byte 2-7: Keycodes

# Helper function to send keystroke
send_key() {
    # Key down
    echo -ne "\x00\x00\x$1\x00\x00\x00\x00\x00" > /dev/hidg0
    # Key up
    echo -ne "\x00\x00\x00\x00\x00\x00\x00\x00" > /dev/hidg0
}

# Helper function to send shifted keystroke (Shift is modifier 0x02)
send_shift_key() {
    # Shift down + key
    echo -ne "\x02\x00\x$1\x00\x00\x00\x00\x00" > /dev/hidg0
    # Key up
    echo -ne "\x00\x00\x00\x00\x00\x00\x00\x00" > /dev/hidg0
}

if [ -c /dev/hidg0 ]; then
    send_shift_key "0b" # H
    send_key "08" # e
    send_key "0f" # l
    send_key "0f" # l
    send_key "12" # o
    send_key "2c" # space
    send_key "1a" # w
    send_key "12" # o
    send_key "15" # r
    send_key "0f" # l
    send_key "07" # d
    send_key "28" # Enter
fi


# 7. Bluetooth Auto-Pairing
if [ -f /boot/bt_mac.txt ]; then
    BT_MAC=$(cat /boot/bt_mac.txt)
    echo "Setting up auto-pairing for Bluetooth MAC: $BT_MAC" >> /var/log/vaultwire_setup.log

    # Create a pairing script
    cat << 'BTSCRIPT' > /opt/vaultwire/bt_pair.sh
#!/usr/bin/env bash
MAC="$1"
while true; do
    # Ensure bluetooth is unblocked and powered on
    rfkill unblock bluetooth
    bluetoothctl power on
    bluetoothctl agent KeyboardOnly
    bluetoothctl default-agent
    bluetoothctl scan on &
    SCAN_PID=$!
    sleep 5

    # Try to pair, trust, and connect
    bluetoothctl pair $MAC
    bluetoothctl trust $MAC
    bluetoothctl connect $MAC

    kill $SCAN_PID 2>/dev/null || true

    # Check if connected
    if bluetoothctl info $MAC | grep -q "Connected: yes"; then
        echo "Successfully paired to $MAC" >> /var/log/vaultwire_bt.log
        break
    fi
    sleep 10
done
BTSCRIPT
    chmod +x /opt/vaultwire/bt_pair.sh

    # Setup a systemd service to run the pairing loop in the background,
    # since we don't want to block the setup script.
    cat << BTSERVICE > /etc/systemd/system/vaultwire-bt-pair.service
[Unit]
Description=VaultWire Bluetooth Auto-Pairing
After=bluetooth.target

[Service]
ExecStart=/opt/vaultwire/bt_pair.sh "$BT_MAC"
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
BTSERVICE

    systemctl daemon-reload
    systemctl enable vaultwire-bt-pair.service
    systemctl start vaultwire-bt-pair.service
fi

echo "VaultWire Offline Setup Complete." >> /var/log/vaultwire_setup.log
BOOTSCRIPT

chmod +x "$MNT_BOOT/Automation_Custom_Script.sh"

echo ""
echo "=== Setup Complete! ==="
echo "The SD card has been configured for a fully offline, headless install."
echo "Unmounting partitions..."
# trap will handle unmounting upon exit
