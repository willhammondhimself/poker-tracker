"""
Interactive Hand Replayer Component.

Visually animates hand history with street-by-street reveal
for demo and analysis purposes.
"""

import streamlit as st
from typing import Optional

# Reuse styling from hand_visualizer
SUIT_COLORS = {
    "♠": "#2C3E50",
    "♣": "#2C3E50",
    "♥": "#E74C3C",
    "♦": "#E74C3C",
}


def _get_replayer_styles() -> str:
    """CSS styles for the hand replayer."""
    return """
    <style>
    .replayer-container {
        background: linear-gradient(145deg, #1a472a 0%, #0d2818 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        border: 2px solid #2d5a3d;
    }

    .replayer-table {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        min-height: 180px;
    }

    .player-area {
        text-align: center;
        min-width: 120px;
    }

    .player-label {
        color: #aaa;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .player-name {
        color: white;
        font-weight: bold;
        margin-bottom: 10px;
    }

    .board-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0 20px;
    }

    .board-cards {
        display: flex;
        gap: 8px;
        justify-content: center;
        flex-wrap: wrap;
    }

    .street-label {
        color: #88a892;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .pot-display {
        background: rgba(0, 0, 0, 0.3);
        color: #F1C40F;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        margin-top: 15px;
    }

    .replayer-card {
        width: 50px;
        height: 70px;
        background: linear-gradient(145deg, #ffffff, #f0f0f0);
        border-radius: 6px;
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        font-family: 'Georgia', serif;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .replayer-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
    }

    .replayer-card.hero {
        width: 60px;
        height: 84px;
        border: 2px solid #3498DB;
    }

    .replayer-card.hidden {
        background: linear-gradient(145deg, #2C3E50, #1a252f);
        border: 2px solid #34495E;
    }

    .replayer-card.hidden .card-rank,
    .replayer-card.hidden .card-suit {
        color: transparent;
    }

    .replayer-card.hidden::before {
        content: "?";
        color: #5D6D7E;
        font-size: 24px;
        font-weight: bold;
    }

    .card-rank {
        font-size: 16px;
        font-weight: bold;
        line-height: 1;
    }

    .card-suit {
        font-size: 18px;
        line-height: 1;
    }

    .action-bar {
        background: rgba(0, 0, 0, 0.2);
        padding: 12px;
        border-radius: 8px;
        margin-top: 16px;
        text-align: center;
    }

    .action-text {
        color: #F39C12;
        font-size: 14px;
        font-weight: 500;
    }

    .result-banner {
        text-align: center;
        padding: 12px;
        border-radius: 8px;
        margin-top: 16px;
        font-weight: bold;
        font-size: 18px;
    }

    .result-banner.win {
        background: linear-gradient(135deg, #27AE60, #2ECC71);
        color: white;
    }

    .result-banner.lose {
        background: linear-gradient(135deg, #E74C3C, #C0392B);
        color: white;
    }
    </style>
    """


def _render_card_html(card: tuple, card_class: str = "", hidden: bool = False) -> str:
    """Render a single card as HTML."""
    if hidden:
        return '<div class="replayer-card hidden"></div>'

    rank, suit = card
    color = SUIT_COLORS.get(suit, "#2C3E50")

    return f'''
    <div class="replayer-card {card_class}">
        <span class="card-rank" style="color: {color};">{rank}</span>
        <span class="card-suit" style="color: {color};">{suit}</span>
    </div>
    '''


def render_hand_replayer(
    hand: dict,
    session_key: str = "replayer_state",
) -> None:
    """
    Render an interactive hand replayer with street-by-street reveal.

    Args:
        hand: Hand dictionary with hole_cards, board, action, result, etc.
        session_key: Key for storing replay state in session_state
    """
    # Initialize state
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'street': 0,  # 0=preflop, 1=flop, 2=turn, 3=river, 4=showdown
            'hand_id': hand.get('id'),
        }

    # Reset if different hand
    if st.session_state[session_key].get('hand_id') != hand.get('id'):
        st.session_state[session_key] = {
            'street': 0,
            'hand_id': hand.get('id'),
        }

    state = st.session_state[session_key]
    current_street = state['street']

    # Extract hand data
    hole_cards = hand.get('hole_cards', [])
    board = hand.get('board', {})
    flop = board.get('flop', [])
    turn = board.get('turn', [])
    river = board.get('river', [])
    position = hand.get('position', 'Unknown')
    opponent = hand.get('opponent_name', 'Villain')
    action = hand.get('action', '')
    result = hand.get('result', 0)
    pot_size = abs(result) * 2 if result != 0 else 0  # Estimate

    # Street names
    street_names = ['Preflop', 'Flop', 'Turn', 'River', 'Showdown']

    # Inject styles
    st.markdown(_get_replayer_styles(), unsafe_allow_html=True)

    # Build the replayer HTML
    html_parts = ['<div class="replayer-container">']

    # Table area
    html_parts.append('<div class="replayer-table">')

    # Hero area (left)
    html_parts.append('<div class="player-area">')
    html_parts.append(f'<div class="player-label">Hero ({position})</div>')
    html_parts.append('<div style="display: flex; gap: 6px; justify-content: center;">')
    for card in hole_cards[:2]:
        html_parts.append(_render_card_html(card, "hero"))
    html_parts.append('</div>')
    html_parts.append('</div>')

    # Board area (center)
    html_parts.append('<div class="board-area">')
    html_parts.append(f'<div class="street-label">{street_names[min(current_street, 4)]}</div>')
    html_parts.append('<div class="board-cards">')

    # Render board cards based on current street
    if current_street >= 1 and flop:
        for card in flop:
            html_parts.append(_render_card_html(card))
    elif current_street == 0 and flop:
        # Show hidden flop placeholders
        for _ in range(3):
            html_parts.append(_render_card_html(('', ''), hidden=True))

    if current_street >= 2 and turn:
        for card in turn:
            html_parts.append(_render_card_html(card))
    elif current_street >= 1 and turn:
        html_parts.append(_render_card_html(('', ''), hidden=True))

    if current_street >= 3 and river:
        for card in river:
            html_parts.append(_render_card_html(card))
    elif current_street >= 2 and river:
        html_parts.append(_render_card_html(('', ''), hidden=True))

    html_parts.append('</div>')

    # Pot display
    if pot_size > 0:
        html_parts.append(f'<div class="pot-display">Pot: ${pot_size:,.2f}</div>')

    html_parts.append('</div>')

    # Opponent area (right)
    html_parts.append('<div class="player-area">')
    html_parts.append(f'<div class="player-label">Opponent</div>')
    html_parts.append(f'<div class="player-name">{opponent or "Unknown"}</div>')
    html_parts.append('<div style="display: flex; gap: 6px; justify-content: center;">')
    # Opponent cards are hidden
    html_parts.append(_render_card_html(('', ''), hidden=True))
    html_parts.append(_render_card_html(('', ''), hidden=True))
    html_parts.append('</div>')
    html_parts.append('</div>')

    html_parts.append('</div>')  # End table

    # Action bar
    if action:
        html_parts.append('<div class="action-bar">')
        html_parts.append(f'<span class="action-text">Hero action: {action.upper()}</span>')
        html_parts.append('</div>')

    # Result banner (at showdown)
    if current_street >= 4:
        result_class = "win" if result >= 0 else "lose"
        result_text = f"+${result:,.2f}" if result >= 0 else f"-${abs(result):,.2f}"
        html_parts.append(f'<div class="result-banner {result_class}">Result: {result_text}</div>')

    html_parts.append('</div>')

    # Render the HTML
    st.markdown(''.join(html_parts), unsafe_allow_html=True)

    # Street navigation controls
    st.markdown("")  # Spacer

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("⏮️ Reset", use_container_width=True, key=f"{session_key}_reset"):
            st.session_state[session_key]['street'] = 0
            st.rerun()

    with col2:
        if st.button("⬅️ Previous", use_container_width=True, key=f"{session_key}_prev",
                     disabled=current_street == 0):
            st.session_state[session_key]['street'] = max(0, current_street - 1)
            st.rerun()

    with col3:
        max_street = 4 if (flop or turn or river) else 0
        if st.button("➡️ Next Street", use_container_width=True, key=f"{session_key}_next",
                     disabled=current_street >= max_street):
            st.session_state[session_key]['street'] = min(max_street, current_street + 1)
            st.rerun()

    with col4:
        if st.button("⏭️ Showdown", use_container_width=True, key=f"{session_key}_end"):
            st.session_state[session_key]['street'] = 4
            st.rerun()

    # Street progress indicator
    progress = current_street / 4
    st.progress(progress)
    st.caption(f"Street: {street_names[min(current_street, 4)]}")


def render_replay_button(hand: dict, button_key: str) -> bool:
    """
    Render a 'Replay Hand' button that opens the replayer.

    Args:
        hand: Hand dictionary
        button_key: Unique key for the button

    Returns:
        True if button was clicked
    """
    return st.button("🎬 Replay Hand", key=button_key, use_container_width=True)


def render_compact_replay(hand: dict) -> None:
    """
    Render a compact, non-interactive hand display.

    For use in lists or summaries where full replayer is too heavy.

    Args:
        hand: Hand dictionary
    """
    hole_cards = hand.get('hole_cards', [])
    board = hand.get('board', {})
    result = hand.get('result', 0)

    # Build compact display
    cards_str = ""
    if len(hole_cards) >= 2:
        c1 = f"{hole_cards[0][0]}{hole_cards[0][1]}"
        c2 = f"{hole_cards[1][0]}{hole_cards[1][1]}"
        cards_str = f"**{c1} {c2}**"

    board_str = ""
    flop = board.get('flop', [])
    turn = board.get('turn', [])
    river = board.get('river', [])

    if flop:
        board_str = "[" + " ".join(f"{c[0]}{c[1]}" for c in flop)
        if turn:
            board_str += " | " + f"{turn[0][0]}{turn[0][1]}"
        if river:
            board_str += " | " + f"{river[0][0]}{river[0][1]}"
        board_str += "]"

    result_color = "green" if result >= 0 else "red"
    result_str = f":{result_color}[${result:+,.2f}]"

    st.markdown(f"{cards_str} {board_str} → {result_str}")
