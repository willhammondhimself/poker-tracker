"""
Quant Poker Edge - Main Application Entry Point
A professional-grade poker analytics platform.
"""

import streamlit as st
import pandas as pd
from utils.data_loader import load_sessions


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
        st.caption("v0.1.0 | Phase 1 MVP")

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


def render_placeholder(page_name: str) -> None:
    """Render a placeholder page for features under development."""
    st.header(f"🚧 {page_name}")
    st.info(f"**{page_name}** is coming soon in Phase 1 development.")

    if page_name == "Log Session":
        st.markdown("""
        **Planned Features:**
        - Quick session entry form
        - Auto-calculate profit & hourly rate
        - Location and stake tracking
        """)
    elif page_name == "Hand Logger":
        st.markdown("""
        **Planned Features:**
        - Smart card selector (2-click entry)
        - Position and action tracking
        - Auto-grey dead cards
        """)
    elif page_name == "Analytics":
        st.markdown("""
        **Planned Features:**
        - Bankroll growth chart
        - Position winrate heatmap
        - Variance tracking
        """)


def main() -> None:
    """Main application entry point."""
    init_session_state()
    apply_theme()

    page = render_sidebar()

    if page == "Dashboard":
        render_dashboard()
    else:
        render_placeholder(page)


if __name__ == "__main__":
    main()
