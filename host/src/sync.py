import base64
import lzma
import json
import curses
from typing import Tuple, List, Dict, Any
from storage import save_local_data

def sync_mode(stdscr: curses.window, data_file: str) -> Tuple[bool, str]:
    """Special mode to ingest new database structure via compressed strings."""
    curses.echo() # Show characters as they are typed/streamed
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    stdscr.addstr(1, 2, "=== SYNC MODE ACTIVE ===", curses.A_BOLD)
    stdscr.addstr(3, 2, "1. Set focus to your Pi's Bluetooth keyboard.")
    stdscr.addstr(4, 2, "2. Trigger the 'Export Sync String' function on the Pi.")
    stdscr.addstr(5, 2, "   (The Pi will dump data here automatically).")
    stdscr.addstr(7, 2, "Paste or stream sync string below:")
    stdscr.addstr(8, 2, "> ")
    stdscr.refresh()

    # Capture the stream from the Pi's HID automation
    try:
        # Note: streaming large payloads via HID into getstr might drop chars on slow terms,
        # but this implements the documented design.
        raw_stream = stdscr.getstr(8, 4, width - 6).decode('utf-8').strip()
        if not raw_stream:
            return False, "Sync cancelled (empty payload)."

        # Strip HMAC signature prefix if it exists
        if ":" in raw_stream:
            # Assumes format "signature:base64payload"
            parts = raw_stream.split(":", 1)
            raw_stream = parts[1]

        # Decode the structure safely in memory
        compressed_data = base64.b64decode(raw_stream)
        decompressed_text = lzma.decompress(compressed_data).decode('utf-8')
        new_vault_data = json.loads(decompressed_text)

        # Ensure it's a list
        if not isinstance(new_vault_data, list):
             return False, "Sync Decode Error: Decoded data is not a valid list."

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
         return False, f"Sync Decode Error: Corrupted compressed data ({str(e)})."
    except json.JSONDecodeError as e:
         return False, f"Sync Decode Error: Invalid JSON structure ({str(e)})."
    except Exception as e:
        return False, f"Sync Decode Error: {str(e)}"
