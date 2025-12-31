"""AI Coach Module for Quant Poker Analytics.

Integrates with Perplexity API to provide GTO-based hand analysis
and coaching recommendations.
"""

import requests
import streamlit as st
from typing import Optional


PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def get_api_key() -> Optional[str]:
    """Get Perplexity API key from Streamlit secrets or session state.

    Returns:
        API key string or None if not configured.
    """
    # Try secrets file first
    try:
        return st.secrets.get("perplexity", {}).get("api_key")
    except Exception:
        pass

    # Fall back to session state (user-entered)
    return st.session_state.get("perplexity_api_key")


def format_cards(cards: list[tuple[str, str]]) -> str:
    """Format card tuples to readable string.

    Args:
        cards: List of (rank, suit) tuples.

    Returns:
        Formatted string like "A♠ K♥".
    """
    if not cards:
        return "Unknown"
    return " ".join(f"{rank}{suit}" for rank, suit in cards)


def format_board(board: dict) -> str:
    """Format board cards dictionary to readable string.

    Args:
        board: Dictionary with 'flop', 'turn', 'river' keys.

    Returns:
        Formatted board string.
    """
    if not board:
        return "No board"

    parts = []
    flop = board.get("flop", [])
    turn = board.get("turn", [])
    river = board.get("river", [])

    if flop:
        parts.append(f"Flop: {format_cards(flop)}")
    if turn:
        parts.append(f"Turn: {format_cards(turn)}")
    if river:
        parts.append(f"River: {format_cards(river)}")

    return " | ".join(parts) if parts else "Preflop only"


def build_prompt(
    hand_data: dict,
    session: dict,
    opponent: Optional[dict] = None,
) -> str:
    """Build the GTO analysis prompt for Perplexity.

    Args:
        hand_data: Hand dictionary with cards, position, action, result.
        session: Session dictionary with stake info.
        opponent: Optional opponent dictionary with stats.

    Returns:
        Formatted prompt string for the AI.
    """
    stake = session.get("stake", "1/2")
    hole_cards = format_cards(hand_data.get("hole_cards", []))
    position = hand_data.get("position", "Unknown")
    action = hand_data.get("action", "Unknown")
    result = hand_data.get("result", 0)
    board = format_board(hand_data.get("board", {}))
    notes = hand_data.get("notes", "")

    # Build opponent info if available
    villain_info = ""
    if opponent:
        stats = opponent.get("stats", {})
        hands_played = stats.get("hands_played", 0)
        if hands_played >= 5:
            vpip = (stats.get("vpip_count", 0) / hands_played * 100) if hands_played else 0
            pfr = (stats.get("pfr_count", 0) / hands_played * 100) if hands_played else 0
            villain_info = f"""
Villain Stats ({opponent.get('name', 'Unknown')}):
- VPIP: {vpip:.1f}%
- PFR: {pfr:.1f}%
- Sample: {hands_played} hands
- Tags: {', '.join(opponent.get('tags', [])) or 'None'}
"""

    prompt = f"""You are an expert GTO Poker Coach specializing in live cash games. Analyze this hand and provide actionable feedback.

**Hand Details:**
- Stakes: ${stake}
- Hero's Hand: {hole_cards}
- Position: {position}
- Preflop Action: {action}
- Board: {board}
- Result: ${result:+.2f}
{f'- Notes: {notes}' if notes else ''}
{villain_info}

**Your Analysis Should Include:**

1. **Rating (1-10):** How well did Hero play this hand from a GTO perspective?

2. **Analysis:** Break down the key decision points. What did Hero do well? What could be improved?

3. **GTO Deviation:** If Hero deviated from GTO, explain what the solver would recommend and why.

4. **Alternative Lines:** Suggest 2-3 alternative lines Hero could have taken, with reasoning.

5. **Exploitative Adjustments:** If villain stats are provided, how should Hero adjust against this player type?

Be specific, concise, and actionable. Focus on the most important strategic concepts for this hand."""

    return prompt


def analyze_hand(
    hand_data: dict,
    session: dict,
    opponent: Optional[dict] = None,
) -> dict:
    """Send hand to Perplexity API for GTO analysis.

    Args:
        hand_data: Hand dictionary with cards, position, action, result.
        session: Session dictionary with stake info.
        opponent: Optional opponent dictionary with stats.

    Returns:
        Dictionary with:
            - success: bool
            - rating: int (1-10) or None
            - analysis: str
            - error: str or None
    """
    api_key = get_api_key()

    if not api_key:
        return {
            "success": False,
            "rating": None,
            "analysis": "",
            "error": "No API key configured. Add your Perplexity API key in Settings.",
        }

    prompt = build_prompt(hand_data, session, opponent)

    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional poker coach with expertise in GTO (Game Theory Optimal) strategy for live cash games. Provide clear, actionable analysis.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.2,
                "max_tokens": 1000,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        analysis_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not analysis_text:
            return {
                "success": False,
                "rating": None,
                "analysis": "",
                "error": "Empty response from API.",
            }

        # Try to extract rating from the analysis
        rating = extract_rating(analysis_text)

        return {
            "success": True,
            "rating": rating,
            "analysis": analysis_text,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "rating": None,
            "analysis": "",
            "error": "Request timed out. Please try again.",
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return {
                "success": False,
                "rating": None,
                "analysis": "",
                "error": "Invalid API key. Please check your Perplexity API key.",
            }
        return {
            "success": False,
            "rating": None,
            "analysis": "",
            "error": f"API error: {e.response.status_code}",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "rating": None,
            "analysis": "",
            "error": f"Connection error: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "rating": None,
            "analysis": "",
            "error": f"Unexpected error: {str(e)}",
        }


def extract_rating(analysis_text: str) -> Optional[int]:
    """Extract numeric rating from analysis text.

    Args:
        analysis_text: Full analysis response.

    Returns:
        Rating as int (1-10) or None if not found.
    """
    import re

    # Look for patterns like "Rating: 7/10", "7/10", "(7/10)", "Rating (1-10): 7"
    patterns = [
        r"[Rr]ating[:\s]*(\d+)\s*/\s*10",
        r"[Rr]ating[:\s]*(\d+)",
        r"\((\d+)/10\)",
        r"(\d+)/10",
    ]

    for pattern in patterns:
        match = re.search(pattern, analysis_text)
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 10:
                return rating

    return None


def render_api_key_input() -> None:
    """Render API key input in sidebar for users without secrets file."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### AI Coach Settings")

        current_key = st.session_state.get("perplexity_api_key", "")
        has_secrets_key = False

        try:
            has_secrets_key = bool(st.secrets.get("perplexity", {}).get("api_key"))
        except Exception:
            pass

        if has_secrets_key:
            st.success("API key configured via secrets.toml")
        else:
            api_key = st.text_input(
                "Perplexity API Key",
                value=current_key,
                type="password",
                help="Get your API key from https://www.perplexity.ai/settings/api",
            )
            if api_key:
                st.session_state["perplexity_api_key"] = api_key
                st.success("API key saved for this session")


def render_analysis_result(result: dict) -> None:
    """Render the AI coach analysis result.

    Args:
        result: Dictionary from analyze_hand().
    """
    if not result.get("success"):
        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
        return

    st.markdown("### AI Coach Analysis")

    # Rating display
    rating = result.get("rating")
    if rating:
        stars = "" * rating + "" * (10 - rating)
        st.markdown(f"**Rating:** {stars} ({rating}/10)")

    # Analysis content
    st.markdown("---")
    st.markdown(result.get("analysis", "No analysis available."))
