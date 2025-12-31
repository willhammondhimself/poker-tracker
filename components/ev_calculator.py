"""
Luck Bucket - EV Calculator for All-In Spots.

Calculates expected value for common all-in scenarios
and tracks luck factor (actual results vs EV).
"""

import streamlit as st
from typing import Optional


# Pre-calculated equity values for common all-in matchups
# Format: (hand1, hand2): equity_for_hand1
EQUITY_TABLE = {
    # Premium vs Premium
    ("AA", "KK"): 0.82,
    ("AA", "QQ"): 0.82,
    ("AA", "JJ"): 0.82,
    ("AA", "TT"): 0.81,
    ("AA", "AKs"): 0.87,
    ("AA", "AKo"): 0.88,
    ("KK", "QQ"): 0.82,
    ("KK", "JJ"): 0.82,
    ("KK", "AKs"): 0.66,
    ("KK", "AKo"): 0.70,
    ("KK", "AQs"): 0.72,
    ("QQ", "JJ"): 0.82,
    ("QQ", "AKs"): 0.54,
    ("QQ", "AKo"): 0.57,
    ("JJ", "AKs"): 0.54,
    ("JJ", "AKo"): 0.57,
    ("JJ", "TT"): 0.82,

    # Pair vs Overcards
    ("TT", "AKs"): 0.54,
    ("TT", "AKo"): 0.57,
    ("TT", "AQs"): 0.55,
    ("99", "AKs"): 0.54,
    ("99", "AKo"): 0.56,
    ("88", "AKo"): 0.55,
    ("77", "AKo"): 0.54,
    ("66", "AKo"): 0.53,
    ("55", "AKo"): 0.53,
    ("44", "AKo"): 0.52,
    ("33", "AKo"): 0.51,
    ("22", "AKo"): 0.50,

    # Pair vs Undercards
    ("AA", "KQs"): 0.83,
    ("KK", "QJs"): 0.82,
    ("QQ", "JTs"): 0.82,
    ("JJ", "T9s"): 0.81,

    # Domination scenarios
    ("AKs", "AQs"): 0.71,
    ("AKo", "AQo"): 0.73,
    ("AKs", "AJs"): 0.72,
    ("AQs", "AJs"): 0.71,
    ("AKs", "KQs"): 0.72,
    ("KQs", "KJs"): 0.71,
    ("AKs", "QJs"): 0.63,

    # Suited connector vs big pair
    ("AA", "JTs"): 0.79,
    ("KK", "JTs"): 0.78,
    ("QQ", "JTs"): 0.79,

    # Coin flips
    ("AKs", "88"): 0.46,
    ("AKo", "77"): 0.43,
    ("AQs", "99"): 0.45,
    ("AJs", "88"): 0.44,
}


# Hand type classification
PAIRS = ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22"]
BROADWAY = ["AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "KQs", "KQo", "KJs", "KJo", "QJs", "QJo"]
SUITED_CONNECTORS = ["JTs", "T9s", "98s", "87s", "76s", "65s", "54s"]


def normalize_hand(hand: str) -> str:
    """
    Normalize hand notation (e.g., 'AhKd' -> 'AKo', 'AsKs' -> 'AKs').

    Args:
        hand: Hand string in various formats

    Returns:
        Normalized hand string like 'AKs' or 'AKo'
    """
    hand = hand.strip().upper()

    # Already in normalized format
    if hand in PAIRS or hand.endswith('s') or hand.endswith('o'):
        return hand

    # Parse card-suit format
    if len(hand) == 4:
        c1_rank = hand[0]
        c1_suit = hand[1].lower()
        c2_rank = hand[2]
        c2_suit = hand[3].lower()

        # Pair check
        if c1_rank == c2_rank:
            return c1_rank + c2_rank

        # Order by rank
        rank_order = "AKQJT98765432"
        if rank_order.index(c1_rank) > rank_order.index(c2_rank):
            c1_rank, c2_rank = c2_rank, c1_rank
            c1_suit, c2_suit = c2_suit, c1_suit

        suited = 's' if c1_suit == c2_suit else 'o'
        return c1_rank + c2_rank + suited

    return hand


def get_equity(hero_hand: str, villain_hand: str) -> Optional[float]:
    """
    Look up equity for a matchup.

    Args:
        hero_hand: Hero's hand in normalized format
        villain_hand: Villain's hand in normalized format

    Returns:
        Hero's equity as float (0-1), or None if not found
    """
    hero = normalize_hand(hero_hand)
    villain = normalize_hand(villain_hand)

    # Direct lookup
    if (hero, villain) in EQUITY_TABLE:
        return EQUITY_TABLE[(hero, villain)]

    # Reverse lookup
    if (villain, hero) in EQUITY_TABLE:
        return 1 - EQUITY_TABLE[(villain, hero)]

    # Estimate for common patterns
    # Overpair vs underpair
    if hero in PAIRS and villain in PAIRS:
        return 0.82 if PAIRS.index(hero) < PAIRS.index(villain) else 0.18

    return None


def calculate_ev(
    hero_hand: str,
    villain_hand: str,
    pot_size: float,
    hero_investment: float,
) -> dict:
    """
    Calculate EV for an all-in spot.

    Args:
        hero_hand: Hero's hand
        villain_hand: Villain's hand
        pot_size: Total pot size including all bets
        hero_investment: Hero's money in the pot

    Returns:
        Dict with equity, ev, pot_odds, etc.
    """
    equity = get_equity(hero_hand, villain_hand)

    if equity is None:
        return {
            "equity": None,
            "ev": None,
            "error": f"Equity not found for {hero_hand} vs {villain_hand}",
        }

    # EV = (Equity * Pot) - Investment
    ev = (equity * pot_size) - hero_investment

    # Pot odds = Investment / (Pot + Investment)
    pot_odds = hero_investment / pot_size if pot_size > 0 else 0

    # Breakeven equity
    breakeven = pot_odds

    return {
        "hero_hand": normalize_hand(hero_hand),
        "villain_hand": normalize_hand(villain_hand),
        "equity": equity,
        "equity_pct": f"{equity * 100:.1f}%",
        "ev": ev,
        "ev_formatted": f"${ev:+,.2f}",
        "pot_size": pot_size,
        "pot_odds": pot_odds,
        "pot_odds_pct": f"{pot_odds * 100:.1f}%",
        "breakeven_equity": breakeven,
        "is_profitable": equity > breakeven,
    }


def calculate_luck_factor(
    ev: float,
    actual_result: float,
) -> dict:
    """
    Calculate how lucky/unlucky a result was.

    Args:
        ev: Expected value of the spot
        actual_result: Actual profit/loss

    Returns:
        Dict with luck analysis
    """
    luck_delta = actual_result - ev

    # Classify luck level
    if luck_delta > 0:
        if luck_delta > ev * 0.5:
            luck_level = "Very Lucky"
            luck_emoji = "🍀🍀"
        else:
            luck_level = "Lucky"
            luck_emoji = "🍀"
    elif luck_delta < 0:
        if abs(luck_delta) > abs(ev) * 0.5:
            luck_level = "Very Unlucky"
            luck_emoji = "💀💀"
        else:
            luck_level = "Unlucky"
            luck_emoji = "💀"
    else:
        luck_level = "Expected"
        luck_emoji = "🎯"

    return {
        "ev": ev,
        "actual": actual_result,
        "luck_delta": luck_delta,
        "luck_delta_formatted": f"${luck_delta:+,.2f}",
        "luck_level": luck_level,
        "luck_emoji": luck_emoji,
    }


def render_ev_calculator() -> None:
    """Render the interactive EV calculator widget."""
    st.subheader("💰 Luck Bucket - EV Calculator")
    st.caption("Calculate expected value for all-in spots")

    col1, col2 = st.columns(2)

    with col1:
        hero_hand = st.selectbox(
            "Your Hand",
            options=PAIRS + BROADWAY + SUITED_CONNECTORS,
            index=0,
            help="Select your hole cards",
        )

    with col2:
        villain_hand = st.selectbox(
            "Villain's Hand",
            options=PAIRS + BROADWAY + SUITED_CONNECTORS,
            index=1,
            help="Select villain's range/hand",
        )

    pot_col, invest_col = st.columns(2)

    with pot_col:
        pot_size = st.number_input(
            "Total Pot ($)",
            min_value=1.0,
            value=100.0,
            step=10.0,
            help="Total pot size after all bets",
        )

    with invest_col:
        hero_investment = st.number_input(
            "Your Investment ($)",
            min_value=0.0,
            value=50.0,
            step=5.0,
            help="Money you put in",
        )

    # Calculate EV
    result = calculate_ev(hero_hand, villain_hand, pot_size, hero_investment)

    if result.get("equity") is not None:
        # Display results
        st.markdown("---")

        res_col1, res_col2, res_col3 = st.columns(3)

        with res_col1:
            equity_color = "#27AE60" if result["equity"] > 0.5 else "#E74C3C"
            st.markdown(
                f"""<div style="text-align: center; padding: 10px;
                background: linear-gradient(135deg, {equity_color}, {equity_color}dd);
                border-radius: 8px;">
                <div style="color: white; font-size: 1.5em; font-weight: bold;">
                {result["equity_pct"]}</div>
                <div style="color: #ffffffcc; font-size: 0.9em;">Your Equity</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with res_col2:
            ev_color = "#27AE60" if result["ev"] > 0 else "#E74C3C"
            st.markdown(
                f"""<div style="text-align: center; padding: 10px;
                background: linear-gradient(135deg, {ev_color}, {ev_color}dd);
                border-radius: 8px;">
                <div style="color: white; font-size: 1.5em; font-weight: bold;">
                {result["ev_formatted"]}</div>
                <div style="color: #ffffffcc; font-size: 0.9em;">Expected Value</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with res_col3:
            decision = "✅ +EV Call" if result["is_profitable"] else "❌ -EV Fold"
            decision_color = "#27AE60" if result["is_profitable"] else "#E74C3C"
            st.markdown(
                f"""<div style="text-align: center; padding: 10px;
                background: linear-gradient(135deg, {decision_color}, {decision_color}dd);
                border-radius: 8px;">
                <div style="color: white; font-size: 1.2em; font-weight: bold;">
                {decision}</div>
                <div style="color: #ffffffcc; font-size: 0.9em;">
                Need {result["breakeven_equity"]*100:.1f}% to call</div>
                </div>""",
                unsafe_allow_html=True,
            )

        # Luck factor (optional actual result)
        st.markdown("---")
        with st.expander("🎲 Calculate Luck Factor", expanded=False):
            actual_result = st.number_input(
                "Actual Result ($)",
                value=0.0,
                step=10.0,
                help="Enter your actual profit/loss from this hand",
            )

            if actual_result != 0:
                luck = calculate_luck_factor(result["ev"], actual_result)

                luck_color = "#27AE60" if luck["luck_delta"] > 0 else "#E74C3C"
                st.markdown(
                    f"""<div style="text-align: center; padding: 15px;
                    background: linear-gradient(135deg, {luck_color}, {luck_color}dd);
                    border-radius: 10px; margin-top: 10px;">
                    <div style="font-size: 2em;">{luck["luck_emoji"]}</div>
                    <div style="color: white; font-size: 1.3em; font-weight: bold;">
                    {luck["luck_level"]}</div>
                    <div style="color: #ffffffcc; font-size: 1em;">
                    {luck["luck_delta_formatted"]} vs EV</div>
                    <div style="color: #ffffff99; font-size: 0.8em; margin-top: 5px;">
                    Expected: ${luck["ev"]:+,.2f} | Actual: ${luck["actual"]:+,.2f}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.warning(result.get("error", "Unable to calculate equity for this matchup."))


def render_mini_ev_calculator() -> dict:
    """
    Render a compact EV calculator for sidebar use.

    Returns:
        Result dict or empty dict if not calculated
    """
    st.markdown("##### 💰 Quick EV Check")

    col1, col2 = st.columns(2)

    with col1:
        hero = st.selectbox(
            "Hero",
            options=PAIRS[:5] + BROADWAY[:3],
            index=0,
            key="mini_ev_hero",
            label_visibility="collapsed",
        )

    with col2:
        villain = st.selectbox(
            "Villain",
            options=PAIRS[:5] + BROADWAY[:3],
            index=1,
            key="mini_ev_villain",
            label_visibility="collapsed",
        )

    equity = get_equity(hero, villain)

    if equity:
        color = "#27AE60" if equity > 0.5 else "#E74C3C"
        st.markdown(
            f"""<div style="text-align: center; padding: 8px;
            background: {color}; border-radius: 6px;">
            <span style="color: white; font-weight: bold;">
            {hero} vs {villain}: {equity*100:.0f}%</span>
            </div>""",
            unsafe_allow_html=True,
        )
        return {"hero": hero, "villain": villain, "equity": equity}

    return {}
