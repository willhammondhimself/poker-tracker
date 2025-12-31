"""
Hand Visualizer Component - Casino-Quality Card Rendering.

Renders poker hands with professional card appearance for
AI Coach output, hand review, and analytics displays.
"""

import streamlit as st
from typing import Optional

# Reuse color scheme from card_selector
SUIT_COLORS = {
    "♠": "#2C3E50",  # Dark blue-grey (spades)
    "♣": "#2C3E50",  # Dark blue-grey (clubs)
    "♥": "#E74C3C",  # Red (hearts)
    "♦": "#E74C3C",  # Red (diamonds)
}


def _get_visualizer_styles() -> str:
    """Return CSS styles for hand visualization."""
    return """
    <style>
    .hand-viz-container {
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .hand-viz-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .position-badge {
        background: linear-gradient(135deg, #3498DB 0%, #2980B9 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .result-badge {
        padding: 6px 14px;
        border-radius: 16px;
        font-weight: bold;
        font-size: 14px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
    }

    .result-badge.winning {
        background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%);
        color: white;
    }

    .result-badge.losing {
        background: linear-gradient(135deg, #E74C3C 0%, #C0392B 100%);
        color: white;
    }

    .result-badge.neutral {
        background: linear-gradient(135deg, #95A5A6 0%, #7F8C8D 100%);
        color: white;
    }

    .cards-section {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 12px 0;
    }

    .cards-label {
        color: #888;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        min-width: 60px;
    }

    .cards-row {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
    }

    /* Playing card styling */
    .poker-card {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: linear-gradient(145deg, #ffffff 0%, #f0f0f0 100%);
        border-radius: 6px;
        box-shadow:
            0 2px 4px rgba(0, 0, 0, 0.15),
            0 4px 8px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.9);
        font-family: 'Georgia', 'Times New Roman', serif;
        position: relative;
    }

    .poker-card.hero {
        width: 52px;
        height: 72px;
        border: 2px solid #3498DB;
    }

    .poker-card.board {
        width: 42px;
        height: 58px;
        border: 1px solid #ddd;
    }

    .poker-card.winning {
        box-shadow:
            0 0 12px rgba(39, 174, 96, 0.4),
            0 2px 4px rgba(0, 0, 0, 0.15);
        border-color: #27AE60;
    }

    .poker-card.losing {
        opacity: 0.85;
    }

    .card-rank {
        font-size: 18px;
        font-weight: bold;
        line-height: 1;
    }

    .card-rank.board {
        font-size: 14px;
    }

    .card-suit {
        font-size: 20px;
        line-height: 1;
        margin-top: -2px;
    }

    .card-suit.board {
        font-size: 16px;
    }

    .street-divider {
        color: #666;
        font-size: 16px;
        margin: 0 4px;
    }

    .street-label {
        font-size: 9px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 4px;
    }

    .action-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 12px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        color: #aaa;
        font-size: 13px;
    }

    .action-tag {
        background: rgba(255, 255, 255, 0.1);
        padding: 4px 10px;
        border-radius: 4px;
        color: #ddd;
        font-size: 12px;
    }

    .opponent-tag {
        color: #F39C12;
        font-weight: 500;
    }
    </style>
    """


def _render_single_card(
    card: tuple[str, str],
    card_type: str = "hero",
    result_state: str = "neutral",
) -> str:
    """
    Generate HTML for a single playing card.

    Args:
        card: Tuple of (rank, suit) e.g., ("A", "♠")
        card_type: "hero" for hole cards, "board" for community cards
        result_state: "winning", "losing", or "neutral"

    Returns:
        HTML string for the card element
    """
    rank, suit = card
    color = SUIT_COLORS.get(suit, "#2C3E50")

    size_class = "board" if card_type == "board" else ""
    result_class = result_state if result_state != "neutral" else ""

    return f'''
    <div class="poker-card {card_type} {result_class}">
        <span class="card-rank {size_class}" style="color: {color};">{rank}</span>
        <span class="card-suit {size_class}" style="color: {color};">{suit}</span>
    </div>
    '''


def _get_result_badge(result: float) -> str:
    """Generate result badge HTML."""
    if result > 0:
        return f'''
        <div class="result-badge winning">
            <span>+${result:,.0f}</span>
        </div>
        '''
    elif result < 0:
        return f'''
        <div class="result-badge losing">
            <span>-${abs(result):,.0f}</span>
        </div>
        '''
    else:
        return '''
        <div class="result-badge neutral">
            <span>$0</span>
        </div>
        '''


def render_hand_visualizer(
    hole_cards: list[tuple[str, str]],
    board: Optional[dict] = None,
    position: Optional[str] = None,
    opponent: Optional[str] = None,
    action: Optional[str] = None,
    result: Optional[float] = None,
    compact: bool = False,
) -> None:
    """
    Render a complete hand visualization with casino-quality cards.

    Args:
        hole_cards: Hero's two hole cards as list of (rank, suit) tuples
        board: Optional board cards {"flop": [...], "turn": [...], "river": [...]}
        position: Hero's position (BTN, CO, etc.)
        opponent: Villain identifier/name
        action: Preflop action taken
        result: Dollar result (+/-)
        compact: If True, use smaller layout for lists
    """
    if not hole_cards or len(hole_cards) < 2:
        return

    # Determine result state for card styling
    result_state = "neutral"
    if result is not None:
        result_state = "winning" if result > 0 else "losing" if result < 0 else "neutral"

    # Build HTML
    st.markdown(_get_visualizer_styles(), unsafe_allow_html=True)

    html_parts = ['<div class="hand-viz-container">']

    # Header row with position and result
    html_parts.append('<div class="hand-viz-header">')

    if position:
        html_parts.append(f'<span class="position-badge">{position}</span>')
    else:
        html_parts.append('<span></span>')

    if result is not None:
        html_parts.append(_get_result_badge(result))
    else:
        html_parts.append('<span></span>')

    html_parts.append('</div>')

    # Hero cards section
    html_parts.append('<div class="cards-section">')
    html_parts.append('<span class="cards-label">Hand</span>')
    html_parts.append('<div class="cards-row">')

    for card in hole_cards[:2]:
        html_parts.append(_render_single_card(card, "hero", result_state))

    html_parts.append('</div>')
    html_parts.append('</div>')

    # Board cards section (if present)
    if board and not compact:
        html_parts.append('<div class="cards-section">')
        html_parts.append('<span class="cards-label">Board</span>')
        html_parts.append('<div class="cards-row">')

        # Flop
        flop = board.get("flop", [])
        if flop:
            for card in flop:
                html_parts.append(_render_single_card(card, "board"))

        # Turn
        turn = board.get("turn", [])
        if turn:
            html_parts.append('<span class="street-divider">|</span>')
            for card in turn:
                html_parts.append(_render_single_card(card, "board"))

        # River
        river = board.get("river", [])
        if river:
            html_parts.append('<span class="street-divider">|</span>')
            for card in river:
                html_parts.append(_render_single_card(card, "board"))

        html_parts.append('</div>')
        html_parts.append('</div>')

    # Action row
    if (action or opponent) and not compact:
        html_parts.append('<div class="action-row">')

        if action:
            # Capitalize first letter
            action_display = action.capitalize() if action else ""
            html_parts.append(f'<span class="action-tag">{action_display}</span>')

        if opponent:
            html_parts.append(f'<span class="opponent-tag">vs {opponent}</span>')

        html_parts.append('</div>')

    html_parts.append('</div>')

    # Render the complete HTML
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_hand_compact(
    hole_cards: list[tuple[str, str]],
    position: Optional[str] = None,
    result: Optional[float] = None,
) -> None:
    """
    Render a compact hand visualization for lists.

    Args:
        hole_cards: Hero's two hole cards
        position: Hero's position
        result: Dollar result
    """
    render_hand_visualizer(
        hole_cards=hole_cards,
        position=position,
        result=result,
        compact=True,
    )


def render_cards_inline(cards: list[tuple[str, str]]) -> str:
    """
    Return inline HTML for cards (for use in markdown strings).

    Args:
        cards: List of (rank, suit) tuples

    Returns:
        HTML string with styled cards
    """
    if not cards:
        return ""

    html_parts = []
    for card in cards:
        rank, suit = card
        color = SUIT_COLORS.get(suit, "#2C3E50")
        html_parts.append(
            f'<span style="color: {color}; font-weight: bold; font-size: 1.1em;">'
            f'{rank}{suit}</span>'
        )

    return " ".join(html_parts)
