"""Smart Card Selector component for Quant Poker Analytics.

Provides a professional 2-click card entry interface with visual feedback
and dead card tracking.
"""

import streamlit as st
from typing import Optional


# Card constants
RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
SUITS = ["♠", "♥", "♦", "♣"]
SUIT_COLORS = {
    "♠": "#2C3E50",  # Dark blue-grey
    "♣": "#2C3E50",  # Dark blue-grey
    "♥": "#E74C3C",  # Red
    "♦": "#E74C3C",  # Red
}


def _apply_card_selector_styles() -> None:
    """Apply custom CSS styling for card selector."""
    st.markdown(
        """
        <style>
        /* Card selector container */
        .card-selector-container {
            background: #F8F9FA;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
        }

        /* Rank buttons */
        .stButton > button[data-rank] {
            width: 100%;
            height: 60px;
            font-size: 24px;
            font-weight: 600;
            border-radius: 6px;
            border: 2px solid #BDC3C7;
            background: white;
            color: #2C3E50;
            transition: all 0.2s;
        }

        .stButton > button[data-rank]:hover {
            border-color: #3498DB;
            background: #EBF5FB;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(52, 152, 219, 0.2);
        }

        .stButton > button[data-rank]:active {
            transform: translateY(0);
        }

        /* Suit buttons */
        .stButton > button[data-suit] {
            width: 100%;
            height: 80px;
            font-size: 48px;
            border-radius: 6px;
            border: 2px solid #BDC3C7;
            background: white;
            transition: all 0.2s;
        }

        .stButton > button[data-suit]:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }

        /* Disabled/used cards */
        .stButton > button[disabled] {
            opacity: 0.3;
            cursor: not-allowed;
            background: #ECF0F1 !important;
        }

        /* Selected state */
        .stButton > button[data-selected="true"] {
            border-color: #3498DB;
            background: #EBF5FB;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
        }

        /* Clear button */
        .stButton > button[data-clear] {
            background: #E74C3C;
            color: white;
            border: none;
            font-weight: 600;
        }

        .stButton > button[data-clear]:hover {
            background: #C0392B;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_card_selector(
    key: str, used_cards: Optional[set[tuple[str, str]]] = None
) -> Optional[tuple[str, str]]:
    """Render interactive card selector with 2-click entry system.

    User selects rank first, then suit. Cards already in use are greyed out
    and disabled.

    Args:
        key: Unique key for this selector instance
        used_cards: Set of (rank, suit) tuples representing unavailable cards

    Returns:
        Selected card as (rank, suit) tuple, or None if no selection made

    Example:
        >>> used = {("A", "♠"), ("K", "♥")}
        >>> card = render_card_selector("hole_card_1", used)
        >>> if card:
        ...     st.write(f"Selected: {card[0]}{card[1]}")
    """
    # Initialize used cards set
    if used_cards is None:
        used_cards = set()

    # Apply custom styles
    _apply_card_selector_styles()

    # Initialize session state for this selector
    state_key = f"card_selector_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "selected_rank": None,
            "selected_suit": None,
            "completed_card": None,
        }

    state = st.session_state[state_key]

    # Container for selector
    st.markdown('<div class="card-selector-container">', unsafe_allow_html=True)

    # Step 1: Rank Selection
    st.markdown("**Step 1: Select Rank**")
    rank_cols = st.columns(13)

    for idx, rank in enumerate(RANKS):
        with rank_cols[idx]:
            # Check if any card with this rank is available
            rank_available = any(
                (rank, suit) not in used_cards for suit in SUITS
            )

            if st.button(
                rank,
                key=f"{key}_rank_{rank}",
                disabled=not rank_available,
                use_container_width=True,
            ):
                state["selected_rank"] = rank
                state["selected_suit"] = None
                state["completed_card"] = None

    # Show selected rank
    if state["selected_rank"]:
        st.markdown(f"**Selected Rank:** `{state['selected_rank']}`")

        # Step 2: Suit Selection
        st.markdown("**Step 2: Select Suit**")
        suit_cols = st.columns(4)

        for idx, suit in enumerate(SUITS):
            with suit_cols[idx]:
                card = (state["selected_rank"], suit)
                is_used = card in used_cards

                # Style button with suit color
                button_html = f"""
                <style>
                button[data-suit-{key}-{suit}] {{
                    color: {SUIT_COLORS[suit]} !important;
                }}
                </style>
                """
                st.markdown(button_html, unsafe_allow_html=True)

                if st.button(
                    suit,
                    key=f"{key}_suit_{suit}",
                    disabled=is_used,
                    use_container_width=True,
                ):
                    state["selected_suit"] = suit
                    state["completed_card"] = card

    # Control buttons
    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Clear", key=f"{key}_clear", use_container_width=True):
            state["selected_rank"] = None
            state["selected_suit"] = None
            state["completed_card"] = None
            st.rerun()

    # Show completed selection
    if state["completed_card"]:
        rank, suit = state["completed_card"]
        color = SUIT_COLORS[suit]
        st.markdown(
            f'<div style="font-size: 36px; font-weight: bold; '
            f'color: {color}; text-align: center; margin: 20px 0;">'
            f'{rank}{suit}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    return state["completed_card"]


def get_card_display(card: tuple[str, str]) -> str:
    """Get HTML-formatted card display string.

    Args:
        card: Tuple of (rank, suit)

    Returns:
        HTML string with colored card representation

    Example:
        >>> html = get_card_display(("A", "♠"))
        >>> st.markdown(html, unsafe_allow_html=True)
    """
    rank, suit = card
    color = SUIT_COLORS[suit]
    return (
        f'<span style="color: {color}; font-weight: bold; '
        f'font-size: 1.2em;">{rank}{suit}</span>'
    )
