"""Data loader module for poker session data."""

import json
from pathlib import Path


def load_sessions() -> list[dict]:
    """
    Load poker sessions from JSON file.

    Returns:
        list[dict]: List of session dictionaries. Returns empty list if file not found.
    """
    sessions_file = Path(__file__).parent.parent / "data" / "dummy_sessions.json"

    try:
        with open(sessions_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
