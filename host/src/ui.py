import curses
from storage import load_local_data
from sync import sync_mode

def draw_main_menu(stdscr: curses.window, data_file: str) -> None:
    """Main application loop handling help instructions and navigation."""
    curses.curs_set(0)
    curses.noecho()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN) # Active cursor bar
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Header text
    
    current_row = 0
    status_message = ""
    
    while True:
        vault_data = load_local_data(data_file)
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
            # Handle status message wrapping if it's too long
            display_msg = f"ℹ️ {status_message}"
            if len(display_msg) > width - 4:
                 display_msg = display_msg[:width - 7] + "..."
            stdscr.addstr(9, 2, display_msg, curses.A_REVERSE)
            stdscr.addstr(10, 2, "-" * (width - 4))
        
        # 3. Dynamic Menu Data Generation
        data_start_y = 11 if status_message else 10
        
        if not vault_data:
            stdscr.addstr(data_start_y, 4, "[!] No local service index found. Press [S] to sync with your Pi.", curses.A_BLINK)
        else:
            for idx, item in enumerate(vault_data):
                title = item.get('title', 'Unknown')
                username = item.get('username', 'Unknown')
                item_id = item.get('id', '?')

                display_line = f" [{item_id}] {title.ljust(22)} | User: {username}"
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
            success, msg = sync_mode(stdscr, data_file)
            status_message = msg
            current_row = 0
            curses.noecho()
            curses.curs_set(0)
        elif key in [10, 13, curses.KEY_ENTER] and vault_data:
            # Display target ID clearly for manual entry
            if current_row < len(vault_data):
                 selected = vault_data[current_row]
                 selected_id = selected.get('id', '?')
                 status_message = f"Selected ID is '{selected_id}'. Type this on the Pi keyboard to inject!"
        elif key in [ord('q'), ord('Q'), 27]:
            break
