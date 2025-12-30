"""
Quant Poker Edge - Main Application Entry Point
A professional-grade poker analytics platform.
"""

import streamlit as st
import pandas as pd
from utils.data_loader import load_sessions, save_session
from components import render_session_form, render_card_selector


# Page Configuration
st.set_page_config(
    page_title="Quant Poker Edge",
    page_icon="♠️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True


def apply_theme() -> None:
    """Apply dark/light theme based on session state."""
    if st.session_state.dark_mode:
        st.markdown(
            """
            <style>
            .stApp { background-color: #0e1117; }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar() -> str:
    """Render sidebar navigation and settings. Returns selected page."""
    with st.sidebar:
        st.title("♠️ Quant Poker Edge")
        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            options=["Dashboard", "Log Session", "Hand Logger", "Analytics"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Settings
        with st.expander("⚙️ Settings"):
            dark_mode = st.toggle(
                "Dark Mode",
                value=st.session_state.dark_mode,
                key="dark_mode_toggle",
            )
            if dark_mode != st.session_state.dark_mode:
                st.session_state.dark_mode = dark_mode
                st.rerun()

        st.markdown("---")
        st.caption("v0.2.0 | Phase 1 MVP")

    return page


def render_dashboard() -> None:
    """Render the main dashboard page."""
    st.header("📊 Dashboard")

    sessions = load_sessions()

    if not sessions:
        st.info("📭 No Data Yet — Log your first session to get started!")
        return

    df = pd.DataFrame(sessions)

    # Calculate summary stats
    df["profit"] = df["cash_out"] - df["buy_in"]
    df["hourly_rate"] = df["profit"] / df["duration_hours"]

    total_profit = df["profit"].sum()
    total_hours = df["duration_hours"].sum()
    avg_hourly = total_profit / total_hours if total_hours > 0 else 0
    sessions_count = len(df)

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Profit", f"${total_profit:,.0f}")
    with col2:
        st.metric("Sessions", sessions_count)
    with col3:
        st.metric("Hours Played", f"{total_hours:.1f}")
    with col4:
        st.metric("Avg $/hr", f"${avg_hourly:.2f}")

    st.markdown("---")

    # Recent Sessions Table
    st.subheader("Recent Sessions")

    display_df = df[["date", "location", "stake", "buy_in", "cash_out", "profit", "duration_hours"]].copy()
    display_df.columns = ["Date", "Location", "Stake", "Buy-in", "Cash-out", "Profit", "Hours"]
    display_df = display_df.sort_values("Date", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


def render_log_session() -> None:
    """Render the session logging page."""
    render_session_form(on_submit=save_session)


def render_hand_logger() -> None:
    """Render the hand logger page with card selector demo."""
    st.header("🃏 Hand Logger")

    # Initialize used cards in session state
    if "used_cards" not in st.session_state:
        st.session_state.used_cards = set()

    st.markdown("**Select your hole cards** *(type shortcuts like `As Kh` or click to select)*")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        card1 = render_card_selector(
            "hole_card_1",
            st.session_state.used_cards,
            label="Card 1"
        )
        if card1:
            st.session_state.used_cards.add(card1)

    with col2:
        card2 = render_card_selector(
            "hole_card_2",
            st.session_state.used_cards,
            label="Card 2"
        )
        if card2:
            st.session_state.used_cards.add(card2)

    with col3:
        st.markdown("### 🎴 Hand Preview")
        if card1 and card2:
            # Large card display
            c1_color = "#E74C3C" if card1[1] in ["♥", "♦"] else "#2C3E50"
            c2_color = "#E74C3C" if card2[1] in ["♥", "♦"] else "#2C3E50"
            st.markdown(
                f'<div style="font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0;">'
                f'<span style="color: {c1_color};">{card1[0]}{card1[1]}</span> '
                f'<span style="color: {c2_color};">{card2[0]}{card2[1]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("Select both cards to see your hand")

        if st.button("🔄 Reset All Cards", use_container_width=True):
            st.session_state.used_cards = set()
            # Clear selector states
            for k in list(st.session_state.keys()):
                if k.startswith("card_selector_"):
                    del st.session_state[k]
            st.rerun()

    st.markdown("---")
    st.info("🚧 Full hand logging (position, board, actions) coming soon!")


def render_analytics() -> None:
    """Render the analytics page placeholder."""
    st.header("📈 Analytics")
    st.info("**Analytics** is coming soon in Phase 2 development.")

    st.markdown("""
    **Planned Features:**
    - Bankroll growth chart (Plotly)
    - Position winrate heatmap
    - Variance tracking & luck indicator
    - Win/loss streaks
    """)


def main() -> None:
    """Main application entry point."""
    init_session_state()
    apply_theme()

    page = render_sidebar()

    if page == "Dashboard":
        render_dashboard()
    elif page == "Log Session":
        render_log_session()
    elif page == "Hand Logger":
        render_hand_logger()
    elif page == "Analytics":
        render_analytics()


if __name__ == "__main__":
    main()
