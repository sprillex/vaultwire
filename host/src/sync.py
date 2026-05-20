import base64
import lzma
import json
import curses
import hmac
import hashlib
from typing import Tuple
from storage import save_local_data


def sync_mode(stdscr: curses.window, data_file: str) -> Tuple[bool, str]:
    """Special mode to ingest new database structure via compressed strings."""
    curses.echo()  # Show characters as they are typed/streamed
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # First, prompt for the sync secret to verify HMAC
    stdscr.addstr(1, 2, "=== SYNC MODE ACTIVE ===", curses.A_BOLD)
    stdscr.addstr(
        3,
        2,
        "Enter Sync Secret (leave blank to skip verification): ")
    stdscr.refresh()
    curses.noecho()
    # Read up to 200 characters to avoid restrictive width bug
    sync_secret = stdscr.getstr(3, 56, 200).decode('utf-8').strip()
    curses.echo()

    stdscr.clear()
    stdscr.addstr(1, 2, "=== SYNC MODE ACTIVE ===", curses.A_BOLD)
    stdscr.addstr(
        3,
        2,
        "1. Set focus to your Pi's Bluetooth keyboard (Development Phase).")
    stdscr.addstr(
        4,
        2,
        "2. Trigger the 'Export Sync String' function on the Pi.")
    stdscr.addstr(5, 2, "   (The Pi will dump data here automatically).")
    stdscr.addstr(7, 2, "Paste or stream sync string below:")
    stdscr.addstr(8, 2, "> ")
    stdscr.refresh()

    # Capture the stream from the Pi's HID automation reliably
    try:
        stdscr.timeout(500)  # Wait up to 500ms for the next character
        stdscr.move(8, 4)
        raw_chars = []
        while True:
            c = stdscr.getch()
            if c in (curses.ERR, ord('\n'), curses.KEY_ENTER, 10, 13):
                # If we timeout (ERR) and have chars, assume stream ended
                # Or if we hit enter, the stream ended
                if len(raw_chars) > 0:
                    break
                # If nothing was typed and we hit enter/timeout, keep waiting
                # if the user hasn't started streaming yet
                if c != curses.ERR:
                    break  # User pressed enter with no text
            else:
                # Disable timeout once streaming starts to grab everything fast
                stdscr.timeout(50)
                try:
                    raw_chars.append(chr(c))
                except ValueError:
                    pass  # Ignore non-ascii/weird keycodes

        stdscr.timeout(-1)  # Reset to blocking mode
        raw_stream = "".join(raw_chars).strip()

        if not raw_stream:
            return False, "Sync cancelled (empty payload)."

        # Strip HMAC signature prefix if it exists
        signature_present = False
        received_signature = ""
        payload_body = raw_stream

        if ":" in raw_stream:
            # Assumes format "signature:base64payload"
            parts = raw_stream.split(":", 1)
            if len(parts) == 2:
                received_signature = parts[0]
                payload_body = parts[1]
                signature_present = True
            else:
                return False, "Sync Decode Error: Malformed signature prefix."

        if sync_secret:
            if not signature_present:
                return False, ("Sync Decode Error: Payload is missing HMAC "
                               "signature, but a secret was provided.")

            expected_mac = hmac.new(
                sync_secret.encode('utf-8'),
                payload_body.encode('utf-8'),
                hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_mac, received_signature):
                return False, ("Sync Decode Error: HMAC signature "
                               "verification failed.")
        elif signature_present:
            return False, ("Sync Decode Error: Payload has HMAC signature, "
                           "but no secret was provided to verify it.")

        # Decode the structure safely in memory
        compressed_data = base64.b64decode(payload_body)
        decompressed_text = lzma.decompress(compressed_data).decode('utf-8')

        try:
            new_vault_data = json.loads(decompressed_text)
        except json.JSONDecodeError as e:
            return False, (f"Sync Decode Error: Invalid JSON "
                           f"structure ({str(e)}).")

        # Ensure it's a list
        if not isinstance(new_vault_data, list):
            return False, ("Sync Decode Error: Decoded data is "
                           "not a valid list.")

        # Strip passwords out if they were accidentally included during export
        for item in new_vault_data:
            item.pop('password', None)

        if save_local_data(data_file, new_vault_data):
            return True, f"Successfully synced {len(new_vault_data)} items!"
        else:
            return False, "Failed to write sync file to storage media."

    except base64.binascii.Error as e:
        return False, f"Sync Decode Error: Invalid base64 stream ({str(e)})."
    except lzma.LZMAError as e:
        return False, (f"Sync Decode Error: Corrupted "
                       f"compressed data ({str(e)}).")
    except json.JSONDecodeError as e:
        return False, f"Sync Decode Error: Invalid JSON structure ({str(e)})."
    except Exception as e:
        return False, f"Sync Decode Error: {str(e)}"
