# VaultWire 🛡️⌨️

VaultWire is an air-gapped, hardware-hardened credential injector built on a Raspberry Pi Zero 2 W. It acts as a dedicated, physical security accessory that unlocks an encrypted KeePass (`.kdbx`) database and injects passwords into a host computer by mimicking a standard USB Human Interface Device (HID) keyboard. 

By utilizing an independent Bluetooth keyboard (during this development phase) connected directly to the Pi and a stateless terminal companion app on the host computer, VaultWire keeps your raw cryptographic keys completely isolated from the target operating system. Communication is strictly one-way over a physical copper wire.

---

## 🏗️ System Architecture

             [ Bluetooth Keyboard ]
          (Development Phase Only)
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
│            (Linux / macOS / Win)               │
│                                                │
│  1. [User Launches App]                        │
│  2. [Companion CLI displays Local Vault Map]   │
│  3. [User Selects Entry] ──► Reads ID Tag      │
│  4. [User Types ID into Pi Keyboard]           │
│  5. [Pi Blasts Keystrokes into Target Field]   │
└────────────────────────────────────────────────┘


---

## 🔒 Core Security & Operational Principles

### 1. Hard Air-Gap (No Network Footprint)
The Raspberry Pi runs completely headless with Wi-Fi and Bluetooth networking stacks disabled. *Note: In the current development phase, a dedicated BT keyboard is used, which is slated to be replaced by a physical keypad to achieve a true air-gap.* It has no IP address, no web server, and no SSH daemon active. It interacts with the host PC *exclusively* as a wired USB keyboard device (`/dev/hidg0`).

### 2. The Unidirectional "Echo Key" Protocol
Because a standard USB keyboard cannot receive data back from a computer, VaultWire relies entirely on manual physical initiation:
* The companion app stores entry descriptions (Titles, Usernames, URLs) locally on the machine or a thumb drive—**never passwords**.
* Selecting an item in the companion app shows an index tag (e.g., `ID:42`).
* When you type `42` into the Pi using its dedicated keyboard, it fetches the corresponding password from its own isolated RAM, and types it directly into your active window.

### 3. Absolute RAM Footprint Volatiles
The KeePass database is decrypted entirely inside the Pi's volatile RAM (`mlock` enforced).
* **No Swap Space:** Linux swap daemons are disabled on the Pi to ensure unencrypted fragments never slide onto persistent storage.
* **Instant Lock:** The moment power is dropped, memory contents vanish instantly.
* **Honeypot Trigger:** Entering the panic PIN or sequential scanning wipes the RAM immediately.

---

## 🎛️ Hardware & Component Requirements

* **Microcontroller:** Raspberry Pi Zero 2 W.
* **Operating System:** DietPi OS (Minimal base image, hardened).
* **Input Peripherals:** Standard Bluetooth Keyboard (Paired exclusively to the Pi) - Development Phase Only.
* **Interconnect Cable:** High-quality Micro-USB to USB-A (or USB-C) data cable.

---

## 🚀 Step-by-Step Operational Workflow

### Phase 1: Unlocking the Vault
1. Power on the Raspberry Pi Zero 2 W by plugging it into the host PC.
2. The Pi boots directly into `vault_daemon.py` and enters a blocking state, waiting for the master password input.
3. Type the master password on the Pi's keyboard to unlock the embedded `.kdbx` file into RAM.

### Phase 2: Interacting with the Host Menu
1. Open the **VaultWire Companion App** manually in your terminal interface. You can optionally specify the path to your layout index:
   ```bash
   python3 host/src/main.py --data-file ~/my_vault_index.json
   ```
2. Use your PC's arrow keys to browse your local credential map.
3. Highlight your target account and note the numeric ID.

### Phase 3: Password Injection Execution
1. Click your mouse cursor directly into the username/password input text box of the website.
2. Type the target ID into your **Pi's keyboard** and press Enter.
3. The Pi simulates human typing to inject your credentials securely.

---

## 🔄 Dynamic Synchronization (Sync Mode)

When you add, remove, or modify services inside your KeePass file, you can effortlessly synchronize the text-only layout mapping to your companion app without updating data files manually:

1. Press `[S]` inside the companion utility on your host PC to enter Sync Mode. The app will prompt you for an optional sync verification secret.
2. After entering the secret, leave your host PC cursor focused in the companion app terminal.
3. Type `s` and press Enter via your **Pi's keyboard** to execute the **Export Sync Layout** macro (typing `s` and pressing enter tells the Pi daemon to start the export stream).
4. The Pi compresses the updated structural data array (Titles, Usernames, IDs) using LZMA, signs it with an HMAC, wraps it in Base64, and simulates a fast-typing script to drop the stream directly into the terminal window.
4. The companion utility instantly updates your local JSON layout map. **Passwords are strictly dropped during transmission.**

---

## 🛠️ Installation & Repository Structure

For a fully secure, air-gapped installation of the Pi daemon without requiring an internet connection on the device, please refer to the [Headless Offline Installation Guide](docs/HEADLESS_INSTALL.md).

```text
├── host/
│   ├── src/
│   │   ├── main.py              # Application entrypoint
│   │   ├── ui.py                # Curses interface
│   │   ├── storage.py           # Local JSON index management
│   │   └── sync.py              # LZMA/Base64 ingestion logic
│   ├── requirements.txt         # Host dependencies
│   └── scripts/
│       └── setup_host.sh        # Environment initialization
└── pi/
    ├── requirements.txt         # Daemon dependencies (pykeepass, evdev)
    ├── scripts/
    │   └── setup_pi.sh          # Pi environment initialization
    └── src/
        ├── hid_gadget.sh        # Core ConfigFS init script (runs as root)
        └── vault_daemon.py      # Main Python daemon (KeePass parsing & injection)

Host Side Prerequisites (Linux/macOS/Windows)
Bash

# Initialize the virtual environment and install requirements
./host/scripts/setup_host.sh

# Run the local layout visualizer (defaults to ~/mint_vault_data.json)
python3 host/src/main.py --data-file ~/my_vault_index.json

Pi Side Prerequisites (DietPi OS)
Bash

# Run the setup script to establish the daemon environment
./pi/scripts/setup_pi.sh
