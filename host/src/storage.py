import os
import json
from typing import List, Dict, Any


def load_local_data(data_file: str) -> List[Dict[str, Any]]:
    """Loads the vault skeleton from a local file or thumb drive."""
    if not os.path.exists(data_file):
        return []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error loading local data: {e}")
        return []


def save_local_data(data_file: str, data: List[Dict[str, Any]]) -> bool:
    """Saves the local structural skeleton (No passwords)."""
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except OSError as e:
        print(f"Error saving local data: {e}")
        return False
