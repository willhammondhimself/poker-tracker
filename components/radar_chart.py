"""Radar chart comparing your stats to GTO baseline."""

import plotly.graph_objects as go
import streamlit as st
from typing import Optional


# GTO Baseline stats for 6-max NLHE cash games
GTO_BASELINE = {
    'VPIP': 24.0,      # Voluntarily Put $ In Pot
    'PFR': 19.0,       # Pre-Flop Raise
    '3Bet': 9.0,       # 3-Bet frequency
    'Agg': 3.0,        # Aggression Factor
    'WTSD': 27.0,      # Went To Showdown %
}

# Stat descriptions for tooltips
STAT_DESCRIPTIONS = {
    'VPIP': 'Voluntarily Put $ In Pot - How often you play hands',
    'PFR': 'Pre-Flop Raise - How often you raise preflop',
    '3Bet': '3-Bet Frequency - How often you re-raise',
    'Agg': 'Aggression Factor - Bets+Raises / Calls',
    'WTSD': 'Went To Showdown - How often you see showdown',
}

# Optimal ranges for each stat (for color coding)
OPTIMAL_RANGES = {
    'VPIP': (20, 28),
    'PFR': (15, 22),
    '3Bet': (6, 12),
    'Agg': (2.0, 4.0),
    'WTSD': (24, 32),
}


def calculate_hero_stats(hands: list[dict]) -> dict:
    """VPIP/PFR/3Bet/Agg/WTSD from hands."""
    if not hands:
        return {k: 0.0 for k in GTO_BASELINE.keys()}

    total_hands = len(hands)
    vpip_count = 0
    pfr_count = 0
    three_bet_count = 0
    bets_raises = 0
    calls = 0
    showdowns = 0

    for hand in hands:
        action = hand.get('action', '').lower()

        # VPIP: Any voluntary action (not fold or check preflop)
        if action not in ['fold', 'check', '']:
            vpip_count += 1

        # PFR: Raised preflop
        if action in ['raise', 'open', '3-bet', '4-bet', 'all-in']:
            pfr_count += 1

        # 3-Bet: Specifically 3-bet
        if action == '3-bet':
            three_bet_count += 1

        # Aggression: Count bets/raises vs calls
        if action in ['raise', 'bet', '3-bet', '4-bet', 'open']:
            bets_raises += 1
        elif action == 'call':
            calls += 1

        # WTSD: Check if went to showdown (has river card and result)
        board = hand.get('board') or {}
        if board.get('river') and hand.get('result', 0) != 0:
            showdowns += 1

    # Calculate percentages
    vpip = (vpip_count / total_hands * 100) if total_hands > 0 else 0
    pfr = (pfr_count / total_hands * 100) if total_hands > 0 else 0
    three_bet = (three_bet_count / total_hands * 100) if total_hands > 0 else 0
    agg = (bets_raises / calls) if calls > 0 else bets_raises if bets_raises > 0 else 0
    wtsd = (showdowns / vpip_count * 100) if vpip_count > 0 else 0

    return {
        'VPIP': round(vpip, 1),
        'PFR': round(pfr, 1),
        '3Bet': round(three_bet, 1),
        'Agg': round(agg, 2),
        'WTSD': round(wtsd, 1),
    }


def normalize_stats(stats: dict, baseline: dict = GTO_BASELINE) -> dict:
    """
    Normalize stats to 0-100 scale for radar chart.

    Uses baseline as the "center" (50) with deviations scaled appropriately.

    Args:
        stats: Hero's stats
        baseline: Reference stats (default GTO)

    Returns:
        Normalized stats dict (0-100 scale)
    """
    normalized = {}

    # Scaling factors (how much deviation from baseline = 1 unit)
    scale_factors = {
        'VPIP': 2.0,    # ±2% per unit
        'PFR': 2.0,
        '3Bet': 1.5,
        'Agg': 0.5,
        'WTSD': 2.0,
    }

    for stat, value in stats.items():
        base = baseline.get(stat, 50)
        scale = scale_factors.get(stat, 1.0)

        # Calculate deviation from baseline and normalize
        deviation = (value - base) / scale
        normalized_value = 50 + (deviation * 10)  # 50 = baseline, ±10 per unit

        # Clamp to 0-100
        normalized[stat] = max(0, min(100, normalized_value))

    return normalized


def get_stat_assessment(stat: str, value: float) -> tuple[str, str]:
    """
    Get assessment of a stat value.

    Returns:
        Tuple of (assessment_text, color)
    """
    low, high = OPTIMAL_RANGES.get(stat, (0, 100))

    if low <= value <= high:
        return "Optimal", "#27AE60"
    elif value < low:
        diff = low - value
        if diff > 5:
            return "Too Tight", "#E74C3C"
        return "Slightly Tight", "#F39C12"
    else:
        diff = value - high
        if diff > 5:
            return "Too Loose", "#E74C3C"
        return "Slightly Loose", "#F39C12"


def render_radar_chart(
    hands: list[dict],
    title: str = "Quant Radar: Your Playstyle vs GTO",
    show_stats_table: bool = True,
) -> None:
    """
    Render the Quant Radar visualization.

    Args:
        hands: List of hand dictionaries
        title: Chart title
        show_stats_table: Whether to show detailed stats below chart
    """
    # Calculate Hero stats
    hero_stats = calculate_hero_stats(hands)

    # Categories for radar
    categories = list(GTO_BASELINE.keys())

    # Create figure
    fig = go.Figure()

    # Add GTO Baseline trace (filled area)
    fig.add_trace(go.Scatterpolar(
        r=list(GTO_BASELINE.values()),
        theta=categories,
        fill='toself',
        fillcolor='rgba(52, 152, 219, 0.2)',
        line=dict(color='#3498DB', width=2),
        name='GTO Baseline',
    ))

    # Add Hero stats trace (filled area)
    hero_values = [hero_stats.get(cat, 0) for cat in categories]
    fig.add_trace(go.Scatterpolar(
        r=hero_values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(46, 204, 113, 0.3)',
        line=dict(color='#2ECC71', width=3),
        name='Your Stats',
    ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(hero_values), max(GTO_BASELINE.values())) * 1.2],
                tickfont=dict(size=10, color='#888'),
                gridcolor='rgba(255, 255, 255, 0.1)',
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color='#fff'),
                gridcolor='rgba(255, 255, 255, 0.1)',
            ),
            bgcolor='rgba(0, 0, 0, 0)',
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color='#fff'),
        ),
        title=dict(
            text=title,
            font=dict(size=16, color='#fff'),
            x=0.5,
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        height=400,
        margin=dict(t=60, b=60, l=60, r=60),
    )

    # Render chart
    st.plotly_chart(fig, use_container_width=True)

    # Show stats comparison table
    if show_stats_table:
        st.markdown("##### Stat Breakdown")

        # Create comparison table
        cols = st.columns(len(categories))

        for i, stat in enumerate(categories):
            hero_val = hero_stats.get(stat, 0)
            gto_val = GTO_BASELINE.get(stat, 0)
            diff = hero_val - gto_val

            assessment, color = get_stat_assessment(stat, hero_val)

            with cols[i]:
                # Format based on stat type
                if stat == 'Agg':
                    hero_str = f"{hero_val:.1f}"
                    gto_str = f"{gto_val:.1f}"
                    diff_str = f"{diff:+.1f}"
                else:
                    hero_str = f"{hero_val:.0f}%"
                    gto_str = f"{gto_val:.0f}%"
                    diff_str = f"{diff:+.0f}%"

                st.markdown(
                    f"""
                    <div style="text-align: center; padding: 8px;
                    background: rgba(255,255,255,0.05); border-radius: 8px;">
                    <div style="font-size: 0.8em; color: #888;">{stat}</div>
                    <div style="font-size: 1.4em; font-weight: bold; color: {color};">{hero_str}</div>
                    <div style="font-size: 0.7em; color: #666;">GTO: {gto_str}</div>
                    <div style="font-size: 0.75em; color: {color};">{diff_str}</div>
                    <div style="font-size: 0.65em; color: {color};">{assessment}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Show sample size warning if needed
        if len(hands) < 100:
            st.caption(f"⚠️ Based on {len(hands)} hands. Need 100+ for reliable stats.")
        else:
            st.caption(f"📊 Based on {len(hands)} hands.")


def render_mini_radar(hands: list[dict], height: int = 200) -> None:
    """
    Render a compact radar chart without stats table.

    For use in dashboards or sidebars.
    """
    hero_stats = calculate_hero_stats(hands)
    categories = list(GTO_BASELINE.keys())

    fig = go.Figure()

    # GTO Baseline
    fig.add_trace(go.Scatterpolar(
        r=list(GTO_BASELINE.values()),
        theta=categories,
        fill='toself',
        fillcolor='rgba(52, 152, 219, 0.15)',
        line=dict(color='#3498DB', width=1),
        name='GTO',
    ))

    # Hero stats
    hero_values = [hero_stats.get(cat, 0) for cat in categories]
    fig.add_trace(go.Scatterpolar(
        r=hero_values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(46, 204, 113, 0.25)',
        line=dict(color='#2ECC71', width=2),
        name='You',
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False),
            angularaxis=dict(tickfont=dict(size=9, color='#aaa')),
            bgcolor='rgba(0, 0, 0, 0)',
        ),
        showlegend=False,
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        height=height,
        margin=dict(t=20, b=20, l=40, r=40),
    )

    st.plotly_chart(fig, use_container_width=True)
