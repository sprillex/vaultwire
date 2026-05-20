#!/usr/bin/env python3
import os
import argparse
import curses
from ui import draw_main_menu


def main():
    parser = argparse.ArgumentParser(
        description="VaultWire Host Companion Application")
    parser.add_argument(
        "--data-file",
        type=str,
        default="~/mint_vault_data.json",
        help="Path to the JSON file storing the local vault index."
    )
    args = parser.parse_args()

    data_file = os.path.expanduser(args.data_file)

    # Wrapper safely initializes and tears down the curses environment
    curses.wrapper(lambda stdscr: draw_main_menu(stdscr, data_file))
    print("\n[+] Companion app suspended cleanly. Storage state un-altered.")


if __name__ == "__main__":
    main()
