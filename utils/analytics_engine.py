"""LeakFinder Analytics Engine for AI Poker Coach.

Identifies negative EV spots, calculates positional winrates,
and generates actionable leak recommendations.
"""

from typing import Optional
from collections import defaultdict


def parse_stake_to_bb(stake: str) -> float:
    """Parse stake string to big blind value.

    Args:
        stake: Stake string like "1/2", ".05/.10", "0.25/0.50"

    Returns:
        Big blind value as float. Returns 2.0 as default.
    """
    try:
        parts = stake.replace("$", "").split("/")
        if len(parts) == 2:
            return float(parts[1])
    except (ValueError, IndexError):
        pass
    return 2.0  # Default to $2 BB


def calculate_position_stats(hands: list[dict], sessions: list[dict]) -> dict:
    """Calculate win/loss statistics by position.

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries (for stake context).

    Returns:
        Dictionary with position stats including BB/100, total profit, hand count.
    """
    # Build session lookup for stake info
    session_stakes = {}
    for s in sessions:
        session_stakes[s.get("id")] = parse_stake_to_bb(s.get("stake", "1/2"))

    # Aggregate by position
    position_data = defaultdict(lambda: {"profit": 0, "hands": 0, "bb_profit": 0})

    for hand in hands:
        pos = hand.get("position", "Unknown")
        result = hand.get("result", 0)
        session_id = hand.get("session_id")
        bb = session_stakes.get(session_id, 2.0)

        position_data[pos]["profit"] += result
        position_data[pos]["hands"] += 1
        position_data[pos]["bb_profit"] += result / bb if bb > 0 else 0

    # Calculate BB/100
    stats = {}
    for pos, data in position_data.items():
        hands_count = data["hands"]
        bb_100 = (data["bb_profit"] / hands_count * 100) if hands_count > 0 else 0
        stats[pos] = {
            "profit": data["profit"],
            "hands": hands_count,
            "bb_profit": round(data["bb_profit"], 2),
            "bb_100": round(bb_100, 2),
        }

    return stats


def calculate_action_stats(hands: list[dict], sessions: list[dict]) -> dict:
    """Calculate win/loss statistics by preflop action.

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries.

    Returns:
        Dictionary with action stats including BB/100, total profit, hand count.
    """
    session_stakes = {}
    for s in sessions:
        session_stakes[s.get("id")] = parse_stake_to_bb(s.get("stake", "1/2"))

    action_data = defaultdict(lambda: {"profit": 0, "hands": 0, "bb_profit": 0})

    for hand in hands:
        action = hand.get("action", "unknown")
        result = hand.get("result", 0)
        session_id = hand.get("session_id")
        bb = session_stakes.get(session_id, 2.0)

        action_data[action]["profit"] += result
        action_data[action]["hands"] += 1
        action_data[action]["bb_profit"] += result / bb if bb > 0 else 0

    stats = {}
    for action, data in action_data.items():
        hands_count = data["hands"]
        bb_100 = (data["bb_profit"] / hands_count * 100) if hands_count > 0 else 0
        stats[action] = {
            "profit": data["profit"],
            "hands": hands_count,
            "bb_profit": round(data["bb_profit"], 2),
            "bb_100": round(bb_100, 2),
        }

    return stats


def calculate_position_action_stats(hands: list[dict], sessions: list[dict]) -> dict:
    """Calculate win/loss statistics by position AND action combination.

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries.

    Returns:
        Dictionary with combined position-action stats.
    """
    session_stakes = {}
    for s in sessions:
        session_stakes[s.get("id")] = parse_stake_to_bb(s.get("stake", "1/2"))

    combo_data = defaultdict(lambda: {"profit": 0, "hands": 0, "bb_profit": 0})

    for hand in hands:
        pos = hand.get("position", "Unknown")
        action = hand.get("action", "unknown")
        result = hand.get("result", 0)
        session_id = hand.get("session_id")
        bb = session_stakes.get(session_id, 2.0)

        key = f"{pos}_{action}"
        combo_data[key]["profit"] += result
        combo_data[key]["hands"] += 1
        combo_data[key]["bb_profit"] += result / bb if bb > 0 else 0
        combo_data[key]["position"] = pos
        combo_data[key]["action"] = action

    stats = {}
    for key, data in combo_data.items():
        hands_count = data["hands"]
        bb_100 = (data["bb_profit"] / hands_count * 100) if hands_count > 0 else 0
        stats[key] = {
            "position": data["position"],
            "action": data["action"],
            "profit": data["profit"],
            "hands": hands_count,
            "bb_profit": round(data["bb_profit"], 2),
            "bb_100": round(bb_100, 2),
        }

    return stats


def find_leaks(
    hands: list[dict],
    sessions: list[dict],
    min_hands: int = 5,
) -> list[dict]:
    """Identify negative EV spots (leaks) in your game.

    A leak is defined as a position/action combination where you're losing
    at a significant rate (negative BB/100).

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries.
        min_hands: Minimum hands required to identify a pattern (default 5).

    Returns:
        List of leak dictionaries sorted by severity (worst first).
    """
    combo_stats = calculate_position_action_stats(hands, sessions)
    position_stats = calculate_position_stats(hands, sessions)

    leaks = []

    # Check position-action combinations
    for key, stats in combo_stats.items():
        if stats["hands"] >= min_hands and stats["bb_100"] < -5:  # Losing > 5bb/100
            leaks.append({
                "type": "position_action",
                "position": stats["position"],
                "action": stats["action"],
                "bb_100": stats["bb_100"],
                "hands": stats["hands"],
                "total_loss": stats["profit"],
                "description": f"{stats['action'].title()} from {stats['position']}",
                "severity": abs(stats["bb_100"]),
            })

    # Check pure position leaks
    for pos, stats in position_stats.items():
        if stats["hands"] >= min_hands and stats["bb_100"] < -10:  # Losing > 10bb/100
            leaks.append({
                "type": "position",
                "position": pos,
                "action": None,
                "bb_100": stats["bb_100"],
                "hands": stats["hands"],
                "total_loss": stats["profit"],
                "description": f"Overall play from {pos}",
                "severity": abs(stats["bb_100"]),
            })

    # Sort by severity
    leaks.sort(key=lambda x: x["severity"], reverse=True)

    return leaks


def find_exploits(
    hands: list[dict],
    sessions: list[dict],
    min_hands: int = 5,
) -> list[dict]:
    """Identify positive EV spots (exploits/strengths) in your game.

    An exploit is a position/action combination where you're winning
    at a significant rate (positive BB/100).

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries.
        min_hands: Minimum hands required to identify a pattern.

    Returns:
        List of exploit dictionaries sorted by profitability (best first).
    """
    combo_stats = calculate_position_action_stats(hands, sessions)
    position_stats = calculate_position_stats(hands, sessions)

    exploits = []

    # Check position-action combinations
    for key, stats in combo_stats.items():
        if stats["hands"] >= min_hands and stats["bb_100"] > 10:  # Winning > 10bb/100
            exploits.append({
                "type": "position_action",
                "position": stats["position"],
                "action": stats["action"],
                "bb_100": stats["bb_100"],
                "hands": stats["hands"],
                "total_profit": stats["profit"],
                "description": f"{stats['action'].title()} from {stats['position']}",
                "strength": stats["bb_100"],
            })

    # Check pure position strengths
    for pos, stats in position_stats.items():
        if stats["hands"] >= min_hands and stats["bb_100"] > 15:  # Winning > 15bb/100
            exploits.append({
                "type": "position",
                "position": pos,
                "action": None,
                "bb_100": stats["bb_100"],
                "hands": stats["hands"],
                "total_profit": stats["profit"],
                "description": f"Overall play from {pos}",
                "strength": stats["bb_100"],
            })

    # Sort by strength
    exploits.sort(key=lambda x: x["strength"], reverse=True)

    return exploits


def generate_leak_recommendations(leaks: list[dict]) -> list[dict]:
    """Generate actionable recommendations for identified leaks.

    Args:
        leaks: List of leak dictionaries from find_leaks().

    Returns:
        List of recommendation dictionaries with specific advice.
    """
    recommendations = []

    # Position-specific advice
    position_advice = {
        "SB": {
            "call": "Tighten SB calling range. Consider 3-betting more instead of flatting.",
            "raise": "Review SB open-raise sizing. Consider smaller sizes or limping in some spots.",
        },
        "BB": {
            "call": "BB defense range may be too wide. Focus on hands with good playability.",
            "check": "Work on post-flop play from BB. Consider leading more on favorable boards.",
        },
        "UTG": {
            "raise": "UTG range may be too loose. Stick to premium hands only.",
            "call": "Avoid flatting UTG opens. 3-bet or fold in most spots.",
        },
        "BTN": {
            "call": "BTN calls showing losses? Consider raising more for value and steals.",
            "fold": "BTN folds losing money indicates you may be over-folding to 3-bets.",
        },
        "CO": {
            "call": "CO calling range should be tight. Prefer 3-betting over flatting.",
            "raise": "CO raises losing? May be opening too wide or sizing incorrectly.",
        },
    }

    # Action-specific advice
    action_advice = {
        "call": "Flatting is often a marginal play. Consider 3-betting stronger hands and folding weaker ones.",
        "raise": "Review open-raise sizing and hand selection. Are you adjusting to player tendencies?",
        "fold": "If folds are losing money, you may be over-folding. Trust your reads more.",
        "all-in": "Review all-in spots carefully. Are you getting the right odds? Consider pot control.",
    }

    for leak in leaks[:5]:  # Top 5 leaks
        pos = leak.get("position")
        action = leak.get("action")

        advice = ""

        # Try position-action specific advice
        if pos in position_advice and action in position_advice[pos]:
            advice = position_advice[pos][action]
        # Fall back to action advice
        elif action in action_advice:
            advice = action_advice[action]
        # Generic advice
        else:
            advice = f"Review your {leak['description']} strategy. Analyze specific hands for patterns."

        recommendations.append({
            "leak": leak["description"],
            "bb_100": leak["bb_100"],
            "hands": leak["hands"],
            "recommendation": advice,
            "priority": "HIGH" if leak["severity"] > 20 else "MEDIUM" if leak["severity"] > 10 else "LOW",
        })

    return recommendations


def get_edge_summary(
    hands: list[dict],
    sessions: list[dict],
    max_items: int = 3,
) -> dict:
    """Generate a summary of top exploits and leaks for dashboard display.

    Args:
        hands: List of hand dictionaries.
        sessions: List of session dictionaries.
        max_items: Maximum number of items per category (default 3).

    Returns:
        Dictionary with 'exploits', 'leaks', and 'recommendations' lists.
    """
    if not hands:
        return {
            "exploits": [],
            "leaks": [],
            "recommendations": [],
            "total_hands": 0,
            "overall_bb_100": 0,
        }

    exploits = find_exploits(hands, sessions)[:max_items]
    leaks = find_leaks(hands, sessions)[:max_items]
    recommendations = generate_leak_recommendations(leaks)[:max_items]

    # Calculate overall BB/100
    session_stakes = {}
    for s in sessions:
        session_stakes[s.get("id")] = parse_stake_to_bb(s.get("stake", "1/2"))

    total_bb_profit = 0
    for hand in hands:
        result = hand.get("result", 0)
        session_id = hand.get("session_id")
        bb = session_stakes.get(session_id, 2.0)
        total_bb_profit += result / bb if bb > 0 else 0

    overall_bb_100 = (total_bb_profit / len(hands) * 100) if hands else 0

    return {
        "exploits": exploits,
        "leaks": leaks,
        "recommendations": recommendations,
        "total_hands": len(hands),
        "overall_bb_100": round(overall_bb_100, 2),
    }


def analyze_opponent_tendencies(
    hands: list[dict],
    opponents: list[dict],
) -> list[dict]:
    """Analyze tendencies for tracked opponents.

    Args:
        hands: List of hand dictionaries.
        opponents: List of opponent dictionaries.

    Returns:
        List of opponent analysis dictionaries with exploitation notes.
    """
    analysis = []

    for opp in opponents:
        opp_id = opp.get("id")
        stats = opp.get("stats", {})
        hands_played = stats.get("hands_played", 0)

        if hands_played < 5:
            continue

        # Calculate percentages
        vpip = (stats.get("vpip_count", 0) / hands_played * 100) if hands_played else 0
        pfr = (stats.get("pfr_count", 0) / hands_played * 100) if hands_played else 0
        three_bet = (stats.get("three_bet_count", 0) / hands_played * 100) if hands_played else 0

        # Classify player type
        if vpip > 40 and pfr < 10:
            player_type = "Calling Station"
            exploit = "Value bet relentlessly. Avoid bluffing."
        elif vpip > 40 and pfr > 20:
            player_type = "LAG (Loose-Aggressive)"
            exploit = "Trap with strong hands. Call down lighter."
        elif vpip < 20 and pfr > 15:
            player_type = "TAG (Tight-Aggressive)"
            exploit = "Respect raises. Steal their blinds."
        elif vpip < 20 and pfr < 10:
            player_type = "Nit"
            exploit = "Steal relentlessly. Fold to their aggression."
        else:
            player_type = "Unknown"
            exploit = "Need more data to classify."

        # Calculate profit vs this opponent
        opp_profit = sum(
            h.get("result", 0)
            for h in hands
            if h.get("opponent_id") == opp_id
        )

        analysis.append({
            "name": opp.get("name"),
            "id": opp_id,
            "hands": hands_played,
            "vpip": round(vpip, 1),
            "pfr": round(pfr, 1),
            "three_bet": round(three_bet, 1),
            "player_type": player_type,
            "exploit": exploit,
            "profit_vs": opp_profit,
            "tags": opp.get("tags", []),
        })

    # Sort by hands played (most data = most reliable)
    analysis.sort(key=lambda x: x["hands"], reverse=True)

    return analysis
