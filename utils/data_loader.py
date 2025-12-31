"""Data loader module for poker session data."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
DUMMY_SESSIONS_FILE = DATA_DIR / "dummy_sessions.json"
HANDS_FILE = DATA_DIR / "hands.json"
OPPONENTS_FILE = DATA_DIR / "opponents.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "bankroll": 350.00,
    "bankroll_target": 500.00,
}


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


# =============================================================================
# Opponent Profiling Functions
# =============================================================================

def load_opponents() -> list[dict]:
    """
    Load all opponents from JSON file.

    Returns:
        list[dict]: List of opponent dictionaries.
    """
    try:
        if not OPPONENTS_FILE.exists():
            return []

        with open(OPPONENTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_opponent(opponent_id: int) -> dict | None:
    """
    Get a single opponent by ID.

    Args:
        opponent_id: The ID of the opponent.

    Returns:
        dict | None: Opponent data if found, None otherwise.
    """
    opponents = load_opponents()
    for opp in opponents:
        if opp.get("id") == opponent_id:
            return opp
    return None


def get_opponent_by_name(name: str) -> dict | None:
    """
    Get an opponent by name (case-insensitive).

    Args:
        name: The opponent's name or identifier.

    Returns:
        dict | None: Opponent data if found, None otherwise.
    """
    opponents = load_opponents()
    name_lower = name.lower().strip()
    for opp in opponents:
        if opp.get("name", "").lower().strip() == name_lower:
            return opp
    return None


def save_opponent(opponent: dict) -> int | None:
    """
    Save a new opponent to the opponents JSON file.

    Args:
        opponent: Opponent data dictionary with at minimum 'name' field.
                  Schema: {
                      name: str,
                      tags: list[str],  # e.g., ["aggro", "fish", "limper"]
                      notes: str,
                      stats: {
                          hands_played: int,
                          vpip_count: int,      # Voluntarily Put $ In Pot
                          pfr_count: int,       # Pre-Flop Raise
                          three_bet_count: int,
                          cbet_count: int,      # Continuation bet
                          fold_to_cbet_count: int,
                      }
                  }

    Returns:
        int | None: Opponent ID if saved successfully, None otherwise.
    """
    try:
        from datetime import datetime

        opponents = load_opponents()

        # Generate ID
        max_id = max((o.get("id", 0) for o in opponents), default=0)
        opponent["id"] = max_id + 1

        # Initialize stats if not provided
        if "stats" not in opponent:
            opponent["stats"] = {
                "hands_played": 0,
                "vpip_count": 0,
                "pfr_count": 0,
                "three_bet_count": 0,
                "cbet_count": 0,
                "fold_to_cbet_count": 0,
            }

        # Initialize other fields
        if "tags" not in opponent:
            opponent["tags"] = []
        if "notes" not in opponent:
            opponent["notes"] = ""

        opponent["created_at"] = datetime.now().isoformat()
        opponent["updated_at"] = datetime.now().isoformat()

        opponents.append(opponent)

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(OPPONENTS_FILE, 'w') as f:
            json.dump(opponents, f, indent=2)

        return opponent["id"]
    except Exception:
        return None


def update_opponent(opponent_id: int, updates: dict) -> bool:
    """
    Update an opponent's data.

    Args:
        opponent_id: The ID of the opponent to update.
        updates: Dictionary of fields to update.

    Returns:
        bool: True if updated successfully, False otherwise.
    """
    try:
        from datetime import datetime

        if not OPPONENTS_FILE.exists():
            return False

        with open(OPPONENTS_FILE, 'r') as f:
            opponents = json.load(f)

        updated = False
        for opp in opponents:
            if opp.get("id") == opponent_id:
                opp.update(updates)
                opp["updated_at"] = datetime.now().isoformat()
                updated = True
                break

        if not updated:
            return False

        with open(OPPONENTS_FILE, 'w') as f:
            json.dump(opponents, f, indent=2)

        return True
    except Exception:
        return False


def update_opponent_stats(
    opponent_id: int,
    hand_action: str,
    is_vpip: bool = False,
    is_pfr: bool = False,
    is_3bet: bool = False,
    is_cbet: bool = False,
    folded_to_cbet: bool = False,
) -> bool:
    """
    Update an opponent's stats after a hand.

    This function increments the relevant counters based on the opponent's
    actions in a hand. Call this after logging a hand with opponent info.

    Args:
        opponent_id: The opponent's ID.
        hand_action: The opponent's preflop action (for reference).
        is_vpip: True if opponent voluntarily put money in pot.
        is_pfr: True if opponent raised preflop.
        is_3bet: True if opponent 3-bet.
        is_cbet: True if opponent made a continuation bet.
        folded_to_cbet: True if opponent folded to a c-bet.

    Returns:
        bool: True if updated successfully, False otherwise.
    """
    try:
        opponent = get_opponent(opponent_id)
        if not opponent:
            return False

        stats = opponent.get("stats", {
            "hands_played": 0,
            "vpip_count": 0,
            "pfr_count": 0,
            "three_bet_count": 0,
            "cbet_count": 0,
            "fold_to_cbet_count": 0,
        })

        # Increment counters
        stats["hands_played"] = stats.get("hands_played", 0) + 1
        if is_vpip:
            stats["vpip_count"] = stats.get("vpip_count", 0) + 1
        if is_pfr:
            stats["pfr_count"] = stats.get("pfr_count", 0) + 1
        if is_3bet:
            stats["three_bet_count"] = stats.get("three_bet_count", 0) + 1
        if is_cbet:
            stats["cbet_count"] = stats.get("cbet_count", 0) + 1
        if folded_to_cbet:
            stats["fold_to_cbet_count"] = stats.get("fold_to_cbet_count", 0) + 1

        return update_opponent(opponent_id, {"stats": stats})
    except Exception:
        return False


def calculate_opponent_stats(opponent: dict) -> dict:
    """
    Calculate derived stats (VPIP%, PFR%, etc.) for an opponent.

    Args:
        opponent: Opponent dictionary with stats.

    Returns:
        dict: Calculated percentages and ratios.
    """
    stats = opponent.get("stats", {})
    hands = stats.get("hands_played", 0)

    if hands == 0:
        return {
            "vpip": 0.0,
            "pfr": 0.0,
            "three_bet": 0.0,
            "af": 0.0,  # Aggression factor
            "hands_played": 0,
        }

    vpip = (stats.get("vpip_count", 0) / hands) * 100
    pfr = (stats.get("pfr_count", 0) / hands) * 100
    three_bet = (stats.get("three_bet_count", 0) / hands) * 100

    # Aggression factor: (raises + bets) / calls
    # Simplified: PFR / (VPIP - PFR) if VPIP > PFR
    vpip_count = stats.get("vpip_count", 0)
    pfr_count = stats.get("pfr_count", 0)
    calls = vpip_count - pfr_count
    af = pfr_count / calls if calls > 0 else pfr_count if pfr_count > 0 else 0

    return {
        "vpip": round(vpip, 1),
        "pfr": round(pfr, 1),
        "three_bet": round(three_bet, 1),
        "af": round(af, 2),
        "hands_played": hands,
    }


def get_or_create_opponent(name: str) -> dict:
    """
    Get an existing opponent by name, or create a new one.

    Args:
        name: The opponent's name or identifier.

    Returns:
        dict: The opponent data (existing or newly created).
    """
    existing = get_opponent_by_name(name)
    if existing:
        return existing

    # Create new opponent
    new_id = save_opponent({"name": name.strip()})
    if new_id:
        return get_opponent(new_id)

    # Fallback
    return {"id": None, "name": name, "stats": {}, "tags": [], "notes": ""}


def get_opponent_with_tags(opponent_id: int) -> dict | None:
    """
    Get opponent with auto-generated tags based on stats.

    Args:
        opponent_id: The opponent's ID.

    Returns:
        dict | None: Opponent with 'auto_tags' field, or None if not found.
    """
    from utils.tagging_engine import auto_tag, analyze_opponent_profile

    opponent = get_opponent(opponent_id)
    if not opponent:
        return None

    # Calculate stats and generate tags
    stats = calculate_opponent_stats(opponent)
    profile = analyze_opponent_profile(opponent, stats)

    # Add profile data to opponent
    opponent['auto_tags'] = profile['tags']
    opponent['tags_html'] = profile['tags_html']
    opponent['exploitation_tips'] = profile['tips']
    opponent['player_type'] = profile['primary_type']
    opponent['calculated_stats'] = stats

    return opponent


def get_all_opponents_with_tags() -> list[dict]:
    """
    Load all opponents with auto-generated tags.

    Returns:
        list[dict]: List of opponents with tags applied.
    """
    from utils.tagging_engine import auto_tag, get_tag_html

    opponents = load_opponents()
    for opp in opponents:
        stats = calculate_opponent_stats(opp)
        tags = auto_tag(stats, opp)
        opp['auto_tags'] = tags
        opp['tags_html'] = get_tag_html(tags)
        opp['calculated_stats'] = stats

    return opponents


# ============================================
# Settings Management
# ============================================

def load_settings() -> dict:
    """
    Load user settings from JSON file.

    Returns:
        dict: Settings dictionary with bankroll, bankroll_target, etc.
    """
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Merge with defaults for any missing keys
                return {**DEFAULT_SETTINGS, **settings}
        return DEFAULT_SETTINGS.copy()
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> bool:
    """
    Save user settings to JSON file.

    Args:
        settings: Settings dictionary to save.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    try:
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def get_bankroll() -> float:
    """Get current bankroll from settings."""
    settings = load_settings()
    return settings.get("bankroll", DEFAULT_SETTINGS["bankroll"])


def get_bankroll_target() -> float:
    """Get bankroll target from settings."""
    settings = load_settings()
    return settings.get("bankroll_target", DEFAULT_SETTINGS["bankroll_target"])


def update_bankroll(bankroll: float, target: float = None) -> bool:
    """
    Update bankroll (and optionally target) in settings.

    Args:
        bankroll: New bankroll amount.
        target: New target amount (optional).

    Returns:
        bool: True if saved successfully.
    """
    settings = load_settings()
    settings["bankroll"] = round(bankroll, 2)
    if target is not None:
        settings["bankroll_target"] = round(target, 2)
    return save_settings(settings)
