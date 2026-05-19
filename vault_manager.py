#!/usr/bin/env python3
import os
import sys
import json
import base64
import lzma
import subprocess
import curses

# Set this path to a thumb drive or local folder
DATA_FILE = os.path.expanduser("~/mint_vault_data.json")

def load_local_data():
    """Loads the vault skeleton from a local file or thumb drive."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_local_data(data):
    """Saves the local structural skeleton (No passwords)."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False

def sync_mode(stdscr):
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
        raw_stream = stdscr.getstr(8, 4, width - 6).decode('utf-8').strip()
        if not raw_stream:
            return False, "Sync cancelled (empty payload)."
            
        # Decode the structure safely in memory
        compressed_data = base64.b64decode(raw_stream)
        decompressed_text = lzma.decompress(compressed_data).decode('utf-8')
        new_vault_data = json.loads(decompressed_text)
        
        # Strip passwords out if they were accidentally included during export
        for item in new_vault_data:
            item.pop('password', None)
            
        if save_local_data(new_vault_data):
            return True, f"Successfully synced {len(new_vault_data)} items!"
        else:
            return False, "Failed to write sync file to storage media."
            
    except Exception as e:
        return False, f"Sync Decode Error: {str(e)}"

def draw_main_menu(stdscr):
    """Main application loop handling help instructions and navigation."""
    curses.curs_set(0)
    curses.noecho()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN) # Active cursor bar
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Header text
    
    current_row = 0
    status_message = ""
    
    while True:
        vault_data = load_local_data()
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # 1. Hardware Operational Instructions Bracket
        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(1, 2, "🛡️ HARDWARE KEEPASS MANAGER COMPANION")
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        stdscr.addstr(3, 2, "👉 HOW TO USE:")
        stdscr.addstr(4, 4, "• Browse to find the service ID you want to log into.")
        stdscr.addstr(5, 4, "• Manually type the ID into the Pi's Bluetooth keyboard to trigger injection.")
        stdscr.addstr(6, 4, "• Press [S] to enter Sync Mode and import current service metadata from the Pi.")
        stdscr.addstr(7, 4, "• Press [Q] to quit safely.")
        stdscr.addstr(8, 2, "-" * (width - 4))
        
        # 2. Render Status / Confirmation Bars
        if status_message:
            stdscr.addstr(9, 2, f"ℹ️ {status_message}", curses.A_REVERSE)
            stdscr.addstr(10, 2, "-" * (width - 4))
        
        # 3. Dynamic Menu Data Generation
        data_start_y = 11 if status_message else 10
        
        if not vault_data:
            stdscr.addstr(data_start_y, 4, "[!] No local service index found. Press [S] to sync with your Pi.", curses.A_BLINK)
        else:
            for idx, item in enumerate(vault_data):
                display_line = f" [{item['id']}] {item['title'].ljust(22)} | User: {item['username']}"
                if len(display_line) > width - 4:
                    display_line = display_line[:width - 7] + "..."
                
                y_pos = data_start_y + idx
                if y_pos >= height - 2: # Stop printing if terminal size runs short
                    break
                    
                if idx == current_row:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y_pos, 2, display_line.ljust(width - 4))
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y_pos, 2, display_line)
                    
        stdscr.refresh()
        
        # 4. Input Processing Node
        key = stdscr.getch()
        status_message = "" # Reset status strip on every fresh keystroke
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(vault_data) - 1:
            current_row += 1
        elif key in [ord('s'), ord('S')]:
            # Temporarily exit main UI loop to handle standard string absorption
            success, msg = sync_mode(stdscr)
            status_message = msg
            current_row = 0
            curses.noecho()
            curses.curs_set(0)
        elif key in [10, 13, curses.KEY_ENTER] and vault_data:
            # Display target ID clearly for manual entry
            selected = vault_data[current_row]
            status_message = f"Selected ID is '{selected['id']}'. Type this on the Pi keyboard to inject!"
        elif key in [ord('q'), ord('Q'), 27]:
            break

def main():
    curses.wrapper(draw_main_menu)
    print("\n[+] Companion app suspended cleanly. Storage state un-altered.")

if __name__ == "__main__":
    main()
