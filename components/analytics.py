"""Analytics components for Quant Poker Edge.

Provides comprehensive poker analytics including bankroll tracking,
position analysis, streaks, and variance metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
import numpy as np


def calculate_streaks(sessions: list[dict]) -> dict:
    """Calculate win/loss streak statistics.

    Args:
        sessions: List of session dictionaries with 'profit' field.

    Returns:
        Dictionary with current_streak, best_win_streak, worst_loss_streak.
    """
    if not sessions:
        return {"current": 0, "best_win": 0, "worst_loss": 0, "type": "none"}

    # Sort by date
    sorted_sessions = sorted(sessions, key=lambda x: x.get("date", ""))

    current_streak = 0
    best_win_streak = 0
    worst_loss_streak = 0
    temp_streak = 0

    for session in sorted_sessions:
        profit = session.get("profit", 0)
        if profit is None:
            continue

        if profit >= 0:
            if temp_streak >= 0:
                temp_streak += 1
            else:
                temp_streak = 1
            best_win_streak = max(best_win_streak, temp_streak)
        else:
            if temp_streak <= 0:
                temp_streak -= 1
            else:
                temp_streak = -1
            worst_loss_streak = min(worst_loss_streak, temp_streak)

    current_streak = temp_streak
    streak_type = "win" if current_streak > 0 else ("loss" if current_streak < 0 else "none")

    return {
        "current": abs(current_streak),
        "best_win": best_win_streak,
        "worst_loss": abs(worst_loss_streak),
        "type": streak_type,
    }


def calculate_variance_stats(sessions: list[dict]) -> dict:
    """Calculate variance and statistical metrics.

    Args:
        sessions: List of session dictionaries with 'profit' field.

    Returns:
        Dictionary with std_dev, variance, confidence intervals.
    """
    profits = [s.get("profit", 0) for s in sessions if s.get("profit") is not None]

    if len(profits) < 2:
        return {
            "std_dev": 0,
            "variance": 0,
            "mean": profits[0] if profits else 0,
            "ci_lower": 0,
            "ci_upper": 0,
            "sample_size": len(profits),
        }

    profits_array = np.array(profits)
    mean = np.mean(profits_array)
    std_dev = np.std(profits_array, ddof=1)  # Sample std dev
    variance = np.var(profits_array, ddof=1)

    # 95% confidence interval
    n = len(profits_array)
    se = std_dev / np.sqrt(n)
    ci_lower = mean - 1.96 * se
    ci_upper = mean + 1.96 * se

    return {
        "std_dev": round(std_dev, 2),
        "variance": round(variance, 2),
        "mean": round(mean, 2),
        "ci_lower": round(ci_lower, 2),
        "ci_upper": round(ci_upper, 2),
        "sample_size": n,
    }


def render_bankroll_chart(sessions: list[dict]) -> None:
    """Render interactive bankroll growth chart.

    Args:
        sessions: List of session dictionaries.
    """
    if not sessions:
        st.info("No session data available for chart.")
        return

    # Filter sessions with valid profit data
    valid_sessions = [s for s in sessions if s.get("profit") is not None]
    if not valid_sessions:
        st.info("No completed sessions to chart.")
        return

    # Create DataFrame and sort by date
    df = pd.DataFrame(valid_sessions)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Calculate cumulative profit
    df["cumulative_profit"] = df["profit"].cumsum()

    # Create Plotly chart
    fig = go.Figure()

    # Add cumulative profit line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["cumulative_profit"],
        mode="lines+markers",
        name="Bankroll",
        line=dict(color="#3498DB", width=3),
        marker=dict(size=8),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "Bankroll: $%{y:,.0f}<br>"
            "<extra></extra>"
        ),
    ))

    # Add trend line
    if len(df) >= 2:
        z = np.polyfit(range(len(df)), df["cumulative_profit"], 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=p(range(len(df))),
            mode="lines",
            name="Trend",
            line=dict(color="#E74C3C", width=2, dash="dash"),
            hoverinfo="skip",
        ))

    # Add zero line
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

    # Style the chart
    fig.update_layout(
        title="Bankroll Growth",
        xaxis_title="Date",
        yaxis_title="Cumulative Profit ($)",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=20, r=20, t=50, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_position_winrate(hands: list[dict]) -> None:
    """Render position winrate analysis table.

    Args:
        hands: List of hand dictionaries with 'position' and 'result' fields.
    """
    if not hands:
        st.info("No hand data available for position analysis.")
        return

    # Group by position
    positions = ["BTN", "CO", "HJ", "LJ", "UTG", "SB", "BB"]
    position_stats = []

    for pos in positions:
        pos_hands = [h for h in hands if h.get("position") == pos]
        if pos_hands:
            total = len(pos_hands)
            wins = sum(1 for h in pos_hands if h.get("result", 0) > 0)
            losses = sum(1 for h in pos_hands if h.get("result", 0) < 0)
            total_profit = sum(h.get("result", 0) for h in pos_hands)
            win_rate = (wins / total * 100) if total > 0 else 0

            position_stats.append({
                "Position": pos,
                "Hands": total,
                "Wins": wins,
                "Losses": losses,
                "Win %": f"{win_rate:.1f}%",
                "Profit": f"${total_profit:+,.0f}",
            })

    if not position_stats:
        st.info("No position data available.")
        return

    df = pd.DataFrame(position_stats)

    # Color-code the profit column
    def color_profit(val):
        if "+" in str(val):
            return "color: #2ECC71"
        elif "-" in str(val):
            return "color: #E74C3C"
        return ""

    styled_df = df.style.applymap(color_profit, subset=["Profit"])

    st.subheader("Position Analysis")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_streak_metrics(sessions: list[dict]) -> None:
    """Render win/loss streak metrics.

    Args:
        sessions: List of session dictionaries.
    """
    streaks = calculate_streaks(sessions)

    st.subheader("Win/Loss Streaks")

    col1, col2, col3 = st.columns(3)

    with col1:
        streak_icon = "🔥" if streaks["type"] == "win" else ("❄️" if streaks["type"] == "loss" else "➖")
        streak_color = "green" if streaks["type"] == "win" else ("red" if streaks["type"] == "loss" else "gray")
        st.metric(
            "Current Streak",
            f"{streak_icon} {streaks['current']}",
            delta=f"{streaks['type'].upper()}" if streaks["type"] != "none" else None,
            delta_color="normal" if streaks["type"] == "win" else "inverse",
        )

    with col2:
        st.metric("Best Win Streak", f"🏆 {streaks['best_win']}")

    with col3:
        st.metric("Worst Loss Streak", f"📉 {streaks['worst_loss']}")


def render_variance_metrics(sessions: list[dict]) -> None:
    """Render variance and statistical metrics.

    Args:
        sessions: List of session dictionaries.
    """
    stats = calculate_variance_stats(sessions)

    st.subheader("Variance Analysis")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Avg Session", f"${stats['mean']:+,.0f}")

    with col2:
        st.metric("Std Deviation", f"${stats['std_dev']:,.0f}")

    with col3:
        st.metric("95% CI Lower", f"${stats['ci_lower']:,.0f}")

    with col4:
        st.metric("95% CI Upper", f"${stats['ci_upper']:,.0f}")

    # Variance explanation
    if stats["sample_size"] >= 5:
        if stats["std_dev"] > abs(stats["mean"]) * 2:
            st.warning("High variance detected. Results are highly variable.")
        elif stats["std_dev"] < abs(stats["mean"]) * 0.5:
            st.success("Low variance. Results are relatively consistent.")
        else:
            st.info("Moderate variance. Standard for poker.")


def render_summary_stats(sessions: list[dict], hands: list[dict]) -> None:
    """Render summary statistics row.

    Args:
        sessions: List of session dictionaries.
        hands: List of hand dictionaries.
    """
    # Filter completed sessions
    completed = [s for s in sessions if s.get("profit") is not None]

    total_profit = sum(s.get("profit", 0) for s in completed)
    total_hours = sum(s.get("duration_hours", 0) for s in completed)
    hourly_rate = total_profit / total_hours if total_hours > 0 else 0
    win_count = sum(1 for s in completed if s.get("profit", 0) > 0)
    win_rate = (win_count / len(completed) * 100) if completed else 0

    st.subheader("Summary Statistics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        profit_color = "normal" if total_profit >= 0 else "inverse"
        st.metric("Total Profit", f"${total_profit:+,.0f}", delta_color=profit_color)

    with col2:
        st.metric("Sessions", len(completed))

    with col3:
        st.metric("Hands Logged", len(hands))

    with col4:
        st.metric("Hours Played", f"{total_hours:.1f}")

    with col5:
        st.metric("Win Rate", f"{win_rate:.1f}%")


def render_analytics_page(sessions: list[dict], hands: list[dict]) -> None:
    """Render the complete analytics page.

    Args:
        sessions: List of session dictionaries.
        hands: List of hand dictionaries.
    """
    st.header("📈 Analytics")

    if not sessions:
        st.info("📭 No data yet. Log some sessions to see analytics!")
        return

    # Summary stats at top
    render_summary_stats(sessions, hands)

    st.markdown("---")

    # Main chart
    render_bankroll_chart(sessions)

    st.markdown("---")

    # Two-column layout for streaks and variance
    col1, col2 = st.columns(2)

    with col1:
        render_streak_metrics(sessions)

    with col2:
        render_variance_metrics(sessions)

    st.markdown("---")

    # Position analysis
    render_position_winrate(hands)

    # Quant Radar - Playstyle comparison
    if hands:
        st.markdown("---")
        from .radar_chart import render_radar_chart
        render_radar_chart(hands, title="🎯 Quant Radar: Your Playstyle vs GTO")
