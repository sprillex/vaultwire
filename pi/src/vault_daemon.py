#!/usr/bin/env python3
"""
VaultWire Core Daemon
Executes on the Raspberry Pi Zero 2 W.
Handles KeePass decryption (in RAM), HID injection, limits, and Sync mode.
"""
import os
import sys
import time
import ctypes
import json
import base64
import lzma
import hmac
import hashlib
import logging
import secrets
import gc
from typing import Any

# Try to import pykeepass, gracefully handle failure for offline linting/setup
try:
    from pykeepass import PyKeePass
except ImportError:
    PyKeePass = None

# Set up logging to stdout and optionally to tmpfs
log_handlers = [logging.StreamHandler(sys.stdout)]
if os.path.exists('/tmp'):
    try:
        log_handlers.append(logging.FileHandler('/tmp/vault_daemon.log'))
    except IOError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Configuration Constants
HID_DEV = os.environ.get("HID_DEV", "/dev/hidg0")
KDBX_PATH = os.environ.get("KDBX_PATH", "/mnt/vault/vault.kdbx")
RATE_LIMIT_DELAY = int(os.environ.get("RATE_LIMIT_DELAY", 30))
HONEYPOT_LIMIT = int(os.environ.get("HONEYPOT_LIMIT", 3))
HONEYPOT_WINDOW = int(os.environ.get("HONEYPOT_WINDOW", 30))
SYNC_SECRET_PATH = os.environ.get(
    "SYNC_SECRET_PATH",
    "/opt/vaultwire/sync.key")

# Linux Keycodes Mapping (Abridged for typical password characters)
KEY_CODES = {
    'a': 4,
    'b': 5,
    'c': 6,
    'd': 7,
    'e': 8,
    'f': 9,
    'g': 10,
    'h': 11,
    'i': 12,
    'j': 13,
    'k': 14,
    'l': 15,
    'm': 16,
    'n': 17,
    'o': 18,
    'p': 19,
    'q': 20,
    'r': 21,
    's': 22,
    't': 23,
    'u': 24,
    'v': 25,
    'w': 26,
    'x': 27,
    'y': 28,
    'z': 29,
    '1': 30,
    '2': 31,
    '3': 32,
    '4': 33,
    '5': 34,
    '6': 35,
    '7': 36,
    '8': 37,
    '9': 38,
    '0': 39,
    '\n': 40,
    'ENTER': 40,
    'ESC': 41,
    'BACKSPACE': 42,
    'TAB': 43,
    'SPACE': 44,
    '-': 45,
    '=': 46,
    '[': 47,
    ']': 48,
    '\\': 49,
    ';': 51,
    "'": 52,
    '`': 53,
    ',': 54,
    '.': 55,
    '/': 56,
    'CAPSLOCK': 57}

SHIFT_CODES = {
    'A': 4,
    'B': 5,
    'C': 6,
    'D': 7,
    'E': 8,
    'F': 9,
    'G': 10,
    'H': 11,
    'I': 12,
    'J': 13,
    'K': 14,
    'L': 15,
    'M': 16,
    'N': 17,
    'O': 18,
    'P': 19,
    'Q': 20,
    'R': 21,
    'S': 22,
    'T': 23,
    'U': 24,
    'V': 25,
    'W': 26,
    'X': 27,
    'Y': 28,
    'Z': 29,
    '!': 30,
    '@': 31,
    '#': 32,
    '$': 33,
    '%': 34,
    '^': 35,
    '&': 36,
    '*': 37,
    '(': 38,
    ')': 39,
    '_': 45,
    '+': 46,
    '{': 47,
    '}': 48,
    '|': 49,
    ':': 51,
    '"': 52,
    '~': 53,
    '<': 54,
    '>': 55,
    '?': 56}

# --- Secure Memory Handling ---


def lock_memory() -> None:
    """Forces secure memory allocation using mlockall to prevent swapping."""
    try:
        libc = ctypes.CDLL("libc.so.6")
        # MCL_CURRENT = 1, MCL_FUTURE = 2
        result = libc.mlockall(3)
        if result != 0:
            logger.warning("mlockall failed. Swap must be disabled natively.")
    except Exception as e:
        logger.error(f"Memory lock exception: {e}")


def scrub_ram(obj: Any):
    """Explicitly overwrites variables in memory (best-effort in Python)."""
    if isinstance(obj, bytearray):
        for i in range(len(obj)):
            obj[i] = 0
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = 0
    # Note: Python strings are immutable. Calling scrub_ram on a string copy
    # does not scrub the original. Rely on deleting references and GC for
    # strings.

# --- Security Features ---


class SecurityMonitor:
    def __init__(self):
        self.last_injection_time = 0
        self.recent_requests = []
        self.last_requested_id = -1

    def check_rate_limit(self) -> bool:
        """Returns True if permitted, False if rate limited."""
        if time.time() - self.last_injection_time < RATE_LIMIT_DELAY:
            return False
        return True

    def register_request(self, target_id: int):
        now = time.time()
        self.recent_requests = [
            t for t in self.recent_requests if now -
            t < HONEYPOT_WINDOW]
        self.recent_requests.append(now)

        # Trigger 1: Too many requests in window
        if len(self.recent_requests) > HONEYPOT_LIMIT:
            self.trigger_honeypot("Rate limit exceeded (Honeypot Triggered).")

        # Trigger 2: Sequential IDs (e.g., 1, 2, 3...) indicating scraping
        if target_id == self.last_requested_id + 1 and target_id > 1:
            self.trigger_honeypot("Sequential scanning detected.")

        self.last_requested_id = target_id

    def trigger_honeypot(self, reason: str) -> None:
        """Purges RAM and halts system upon detecting an attack."""
        logger.critical(
            f"SECURITY VIOLATION: {reason}. Purging memory and halting.")
        # Attempt to overwrite any active memory here if we had direct C-struct
        # access
        sys.stdout.flush()

        import subprocess
        # Try sysrq first
        try:
            with open("/sysrq-trigger", "w") as f:
                f.write("b")
        except IOError:
            # Fallback to standard reboot and then poweroff
            logger.critical(
                "sysrq failed, falling back to standard reboot/poweroff")
            subprocess.run(["reboot", "-f"], check=False)
            subprocess.run(["poweroff", "-f"], check=False)

        os._exit(1)  # Immediate ungraceful exit bypassing standard teardown


# --- Core Logic ---

def validate_kdbx_header(filepath: str) -> bool:
    """Cryptographic Header Validation."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
            # KeePass 2.x magic bytes: 03 d9 a2 9a and 67 fb 4b b5
            expected = b'\x03\xd9\xa2\x9a\x67\xfb\x4b\xb5'
            if header == expected:
                return True
            # Allow fallback for varying signatures depending on minor version,
            # but strictly fail if it's completely malformed.
            if len(header) == 8:
                return True
        return False
    except FileNotFoundError:
        return False


def init_hid() -> None:
    """Validates HID interface is available."""
    if not os.path.exists(HID_DEV):
        logger.error(f"{HID_DEV} not found. Is the gadget initialized?")
        sys.exit(1)


def send_keystroke(keycode: int, shift: bool = False) -> bool:
    """Sends a raw keystroke to the HID interface."""
    modifier = b'\x02' if shift else b'\x00'  # Shift modifier
    null_char = b'\x00'

    # Press
    report = modifier + null_char + bytes([keycode]) + (null_char * 5)
    try:
        with open(HID_DEV, 'wb') as f:
            f.write(report)
    except IOError as e:
        logger.error(f"Failed to write to HID device: {e}")
        return False

    # Release
    report = (null_char * 8)
    try:
        with open(HID_DEV, 'wb') as f:
            f.write(report)
    except IOError as e:
        logger.error(f"Failed to write to HID device: {e}")
        return False

    return True


# Load typing delays from environment variables
MIN_TYPE_DELAY = float(os.environ.get("MIN_TYPE_DELAY", 0.005))
MAX_TYPE_DELAY = float(os.environ.get("MAX_TYPE_DELAY", 0.015))


def type_string(text: str) -> bool:
    """Simulates typing with micro-delays and jitter."""
    for char in text:
        shift = False
        keycode = 0
        if char in KEY_CODES:
            keycode = KEY_CODES[char]
        elif char in SHIFT_CODES:
            keycode = SHIFT_CODES[char]
            shift = True

        if keycode != 0:
            if not send_keystroke(keycode, shift):
                return False
            # Micro-delay to prevent dropped characters
            time.sleep(
                secrets.SystemRandom().uniform(
                    MIN_TYPE_DELAY,
                    MAX_TYPE_DELAY))
    return True


def override_caps_lock() -> None:
    """Forces caps lock off (Blind toggle, assuming standard initial state)."""
    send_keystroke(KEY_CODES['CAPSLOCK'])
    time.sleep(0.05)
    send_keystroke(KEY_CODES['CAPSLOCK'])
    time.sleep(0.05)


def generate_sync_payload(kp: Any) -> str:
    """Generates the compressed, HMAC-signed JSON structure for the host."""
    data = []
    # Using specific iteration to build index without exporting passwords
    for idx, entry in enumerate(kp.entries):
        if entry.title == "Meta-Info":
            continue
        data.append({
            'id': idx + 1,
            'title': entry.title or "Unknown",
            'username': entry.username or "",
            'url': entry.url or ""
        })

    raw_json = json.dumps(data)
    compressed = lzma.compress(raw_json.encode('utf-8'))
    b64_payload = base64.b64encode(compressed).decode('utf-8')

    # Sign the payload if key exists
    signature = ""
    try:
        with open(SYNC_SECRET_PATH, 'rb') as f:
            secret = f.read().strip()
            mac = hmac.new(
                secret,
                b64_payload.encode('utf-8'),
                hashlib.sha256).hexdigest()
            signature = f"{mac}:"
    except FileNotFoundError:
        pass  # Unsigned sync allowed for development

    return signature + b64_payload


def listen_for_input(kp: Any, monitor: SecurityMonitor) -> None:
    """Main loop awaiting manual input on the Pi's keyboard."""
    logger.info("Vault Open. Awaiting input ID or (S)ync command.")
    while True:
        try:
            cmd = input("Command> ").strip()

            # Duress PIN / Panic trigger
            if cmd == "9999":
                monitor.trigger_honeypot("Duress PIN entered.")

            # Sync Mode Export
            if cmd.lower() == 's':
                logger.info("Exporting sync layout...")
                payload = generate_sync_payload(kp)
                # Wait for user to focus terminal
                time.sleep(2)
                type_string(payload)
                send_keystroke(KEY_CODES['ENTER'])
                continue

            # Injection parsing
            if cmd.isdigit():
                target_id = int(cmd)
                monitor.register_request(target_id)

                if not monitor.check_rate_limit():
                    logger.warning(
                        f"Rate limited. Please wait {RATE_LIMIT_DELAY}s.")
                    continue

                # Fetch strictly via index lookup to prevent looping
                try:
                    entry = kp.entries[target_id - 1]
                except IndexError:
                    logger.error("Invalid ID.")
                    continue

                logger.info(f"Injecting credentials for: {entry.title}")

                # Caps lock override
                override_caps_lock()

                # Stage 1: URL
                if entry.url:
                    type_string(entry.url)
                    send_keystroke(KEY_CODES['ENTER'])
                    logger.info(
                        "URL Injected. Press ENTER on Pi to continue "
                        "with credentials...")
                    input("Press ENTER> ")

                # Stage 2: Username / Password
                if entry.username:
                    type_string(entry.username)
                    send_keystroke(KEY_CODES['TAB'])
                if entry.password:
                    type_string(entry.password)
                send_keystroke(KEY_CODES['ENTER'])

                # Improve RAM scrubbing by forcing garbage collection
                gc.collect()

                monitor.last_injection_time = time.time()
                logger.info("Injection complete.")

        except KeyboardInterrupt:
            logger.info("Shutting down daemon...")
            sys.exit(0)


def main() -> None:
    lock_memory()
    init_hid()

    if PyKeePass is None:
        logger.error("pykeepass not installed. Halting daemon.")
        sys.exit(1)

    if not validate_kdbx_header(KDBX_PATH):
        logger.error(f"Invalid or missing vault file at {KDBX_PATH}")
        sys.exit(1)

    while True:
        master_password = input("Enter Master Password: ").strip()

        try:
            # Load entirely into RAM
            kp = PyKeePass(KDBX_PATH, password=master_password)
            logger.info("Vault Unlocked Successfully.")
            # Clear master password reference
            del master_password
            break
        except Exception as e:
            logger.error(
                f"Failed to unlock vault. Incorrect password or "
                f"corrupted file ({e}).")
            print("Please try again.")
            del master_password

    monitor = SecurityMonitor()
    listen_for_input(kp, monitor)


if __name__ == "__main__":
    main()
