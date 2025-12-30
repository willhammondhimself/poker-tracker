"""Data loader module for poker session data."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
DUMMY_SESSIONS_FILE = DATA_DIR / "dummy_sessions.json"


def load_sessions() -> list[dict]:
    """
    Load poker sessions from JSON file.
    Tries real sessions first, falls back to dummy data.

    Returns:
        list[dict]: List of session dictionaries. Returns empty list if not found.
    """
    # Try real sessions first
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass

    # Fall back to dummy data
    try:
        with open(DUMMY_SESSIONS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_session(session: dict) -> bool:
    """
    Save a new session to the sessions JSON file.

    Args:
        session: Session data dictionary.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    try:
        # Load existing sessions (only from real file, not dummy)
        sessions = []
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'r') as f:
                sessions = json.load(f)

        # Generate ID
        max_id = max((s.get("id", 0) for s in sessions), default=0)
        session["id"] = max_id + 1

        # Append and save
        sessions.append(session)

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)

        return True
    except Exception:
        return False


def delete_session(session_id: int) -> bool:
    """
    Delete a session by ID.

    Args:
        session_id: The ID of the session to delete.

    Returns:
        bool: True if deleted successfully, False otherwise.
    """
    try:
        if not SESSIONS_FILE.exists():
            return False

        with open(SESSIONS_FILE, 'r') as f:
            sessions = json.load(f)

        sessions = [s for s in sessions if s.get("id") != session_id]

        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)

        return True
    except Exception:
        return False
