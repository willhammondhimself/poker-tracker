"""Data loader module for poker session data."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
DUMMY_SESSIONS_FILE = DATA_DIR / "dummy_sessions.json"
HANDS_FILE = DATA_DIR / "hands.json"


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


def save_session(session: dict) -> int | None:
    """
    Save a new session to the sessions JSON file.

    Args:
        session: Session data dictionary.

    Returns:
        int | None: Session ID if saved successfully, None otherwise.
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

        return session["id"]
    except Exception:
        return None


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


def get_session(session_id: int) -> dict | None:
    """
    Load a single session by ID.

    Args:
        session_id: The ID of the session to retrieve.

    Returns:
        dict | None: Session data if found, None otherwise.
    """
    sessions = load_sessions()
    for session in sessions:
        if session.get("id") == session_id:
            return session
    return None


def update_session(session_id: int, updates: dict) -> bool:
    """
    Update specific fields of a session.

    Args:
        session_id: The ID of the session to update.
        updates: Dictionary of fields to update.

    Returns:
        bool: True if updated successfully, False otherwise.
    """
    try:
        if not SESSIONS_FILE.exists():
            return False

        with open(SESSIONS_FILE, 'r') as f:
            sessions = json.load(f)

        updated = False
        for session in sessions:
            if session.get("id") == session_id:
                session.update(updates)
                updated = True
                break

        if not updated:
            return False

        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)

        return True
    except Exception:
        return False


def save_hand(hand: dict, session_id: int) -> bool:
    """
    Save a new hand to the hands JSON file.

    Args:
        hand: Hand data dictionary.
        session_id: The session ID this hand belongs to.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    try:
        from datetime import datetime

        # Load existing hands
        hands = []
        if HANDS_FILE.exists():
            with open(HANDS_FILE, 'r') as f:
                hands = json.load(f)

        # Generate ID
        max_id = max((h.get("id", 0) for h in hands), default=0)
        hand["id"] = max_id + 1

        # Add metadata
        hand["session_id"] = session_id
        hand["timestamp"] = datetime.now().isoformat()

        # Append and save
        hands.append(hand)

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(HANDS_FILE, 'w') as f:
            json.dump(hands, f, indent=2)

        return True
    except Exception:
        return False


def load_hands(session_id: int | None = None) -> list[dict]:
    """
    Load hands from JSON file, optionally filtered by session.

    Args:
        session_id: If provided, only return hands from this session.

    Returns:
        list[dict]: List of hand dictionaries. Returns empty list if not found.
    """
    try:
        if not HANDS_FILE.exists():
            return []

        with open(HANDS_FILE, 'r') as f:
            hands = json.load(f)

        if session_id is not None:
            hands = [h for h in hands if h.get("session_id") == session_id]

        return hands
    except (FileNotFoundError, json.JSONDecodeError):
        return []
