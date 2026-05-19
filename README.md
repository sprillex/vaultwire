Markdown

# VaultWire 🛡️⌨️

VaultWire is an air-gapped, hardware-hardened credential injector built on a Raspberry Pi Zero 2 W. It acts as a dedicated, physical security accessory that unlocks an encrypted KeePass (`.kdbx`) database and injects passwords into a host computer by mimicking a standard USB Human Interface Device (HID) keyboard. 

By utilizing an independent Bluetooth keyboard connected directly to the Pi and a stateless terminal companion app on the host computer, VaultWire keeps your raw cryptographic keys completely isolated from the target operating system. Communication is strictly one-way over a physical copper wire.

---

## 🏗️ System Architecture

             [ Bluetooth Keyboard ]
                       │
                (Wireless Input)
                       ▼
           ┌───────────────────────┐
           │  Raspberry Pi Zero 2  │ ◄─── Decrypts .kdbx in Volatile RAM
           │  (DietPi OS - R/O)    │
           └───────────┬───────────┘
                       │
         (USB HID Keyboard Emulation)
                       ▼

┌────────────────────────────────────────────────┐
│                  HOST PC                       │
│            (Linux Mint Desktop)                │
│                                                │
│  1. [User Launches App]                        │
│  2. [Companion CLI displays Local Vault Map]   │
│  3. [User Selects Entry] ──► Copies Index ID   │
│  4. [Pi sends Ctrl+C]    ◄── Reads Clipboard   │
│  5. [Pi Blasts Keystrokes into Target Field]   │
└────────────────────────────────────────────────┘


---

## 🔒 Core Security & Operational Principles

### 1. Hard Air-Gap (No Network Footprint)
The Raspberry Pi runs completely headless with Wi-Fi and Bluetooth networking stacks disabled. It has no IP address, no web server, and no SSH daemon active. It interacts with the host PC *exclusively* as a wired USB keyboard device (`/dev/hidg0`).

### 2. The Unidirectional "Echo Key" Protocol
Because a standard USB keyboard cannot receive data back from a computer, VaultWire solves the two-way communication bottleneck using a clever clipboard feedback hook:
* The Linux Mint companion app stores entry descriptions (Titles, Usernames, URLs) locally on the machine or a thumb drive—**never passwords**.
* Selecting an item in the companion app automatically stages a non-sensitive index tag (e.g., `ID:42`) onto the host PC's clipboard.
* When you prompt the Pi using its dedicated Bluetooth keyboard, it issues a standard `Ctrl + C` macro command down the wire, reads the index tag from the clipboard, fetches the corresponding password from its own isolated RAM, and types it.

### 3. Absolute RAM Footprint Volatiles
The KeePass database is decrypted entirely inside the Pi's volatile RAM. 
* **No Swap Space:** Linux swap daemons are disabled on the Pi to ensure unencrypted fragments never slide onto persistent storage.
* **Instant Lock:** The moment power is dropped (cable pulled or power switch flipped), the memory contents vanish instantly.
* **Read-Only OS:** The operating system runs out of a read-only filesystem profile, ensuring safe, zero-corruption power cuts as a standard locking mechanism.

---

## 🎛️ Hardware & Component Requirements

* **Microcontroller:** Raspberry Pi Zero 2 W.
* **Operating System:** DietPi OS (Minimal base image, hardened).
* **Input Peripherals:** Standard Bluetooth Keyboard (Paired exclusively to the Pi).
* **Interconnect Cable:** High-quality Micro-USB to USB-A (or USB-C) data cable plugged into the Pi's native `USB` OTG port.
* **Host Environment:** Linux Mint (Cinnamon Desktop running `xclip` toolchain dependencies).

---

## 🚀 Step-by-Step Operational Workflow

### Phase 1: Unlocking the Vault
1. Power on the Raspberry Pi Zero 2 W by plugging it into the host PC.
2. The Pi boots directly into a localized script and enters a blocking state, waiting for the master password input.
3. Type the master password on the Pi's **Bluetooth keyboard** to unlock the embedded `.kdbx` file directly into volatile memory.

### Phase 2: Interacting with the Host Menu
1. Open the **VaultWire Companion App** (`mint_vault_manager.py`) manually inside your Linux Mint terminal interface.
2. Use your PC's arrow keys to browse your local credential map.
3. Highlight your target account (e.g., *GitHub*) and press `[ENTER]`. The app pushes `ID:02` to your computer's clipboard.

### Phase 3: Password Injection Execution
1. Click your mouse cursor directly into the username/password input text box of the website or application you want to log into.
2. Press the execution shortcut on your **Pi's Bluetooth keyboard**.
3. The Pi sends a fast `Ctrl + C` macro to read the clipboard state, identifies `ID:02`, matches it to the decrypted entry payload, counts down for 3 seconds, and securely types your credentials.

---

## 🔄 Dynamic Synchronization (Sync Mode)

When you add, remove, or modify services inside your KeePass file, you can effortlessly synchronize the text-only layout mapping to your companion app without updating data files manually:

1. Press `[S]` inside the Linux Mint companion utility to launch the native listening hook.
2. Execute the **Export Sync Layout** macro via your Pi's Bluetooth keyboard.
3. The Pi compresses the updated structural data array (Titles, Usernames, IDs) using LZMA, wraps it in Base64, and simulates a fast-typing script to drop the stream directly into the terminal window. 
4. The companion utility instantly updates your local JSON layout map. **Passwords are dropped during transmission; they remain solely on the Pi.**

---

## 🛠️ Installation & Repository Structure

```text
├── host/
│   ├── mint_vault_manager.py   # Interactive Curses terminal app for Linux Mint
│   └── README.md                # Host environment setup and xclip configurations
└── pi/
    ├── boot/
    │   ├── config.txt           # Dwc2 USB controller configuration overlay
    │   └── cmdline.txt          # Kernel execution string customization
    └── src/
        ├── hid_gadget.sh        # Core ConfigFS initialization script
        └── vault_daemon.py      # Main Python daemon handling pykeepass and HID macros

Host Side Prerequisites
Bash

# Install xclip toolchain to manage system tray clipboards
sudo apt update && sudo apt install -y xclip

# Run the local layout visualizer
python3 host/mint_vault_manager.py

Pi Side Prerequisites
Bash

# Purge standard swap mechanisms to prevent memory tracking leaks
sudo apt-get remove -y dphys-swapfile

# Install local layout parsing libraries
pip3 install pykeepass
