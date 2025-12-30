"""Session logging form component."""

import streamlit as st
from datetime import date, datetime
from typing import Callable, Literal


# Common poker locations and stakes
DEFAULT_LOCATIONS = ["ClubWPT Gold", "Morongo Casino", "Commerce Casino", "Home Game", "Other"]
DEFAULT_STAKES = ["1/2", "1/3", "2/5", "5/10", "Other"]


def render_start_session_form(on_submit: Callable[[dict], int | None] | None = None) -> int | None:
    """
    Render form to start a live session.

    Args:
        on_submit: Callback that saves session and returns session_id.

    Returns:
        Session ID if started, None otherwise.
    """
    st.header("🎮 Start Live Session")

    with st.form("start_session_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            location = st.selectbox("Location", options=DEFAULT_LOCATIONS, index=0)

        with col2:
            stake = st.selectbox("Stake", options=DEFAULT_STAKES, index=0)

        buy_in = st.number_input("Buy-in ($)", min_value=0, max_value=100000, value=200, step=50)

        submitted = st.form_submit_button("🚀 Start Session", use_container_width=True, type="primary")

        if submitted:
            session_data = {
                "date": date.today().isoformat(),
                "location": location,
                "stake": stake,
                "buy_in": buy_in,
                "cash_out": None,  # Not ended yet
                "duration_hours": None,
                "status": "active",
                "start_time": datetime.now().isoformat(),
                "notes": "",
            }

            if on_submit:
                session_id = on_submit(session_data)
                if session_id:
                    st.success(f"✅ Session started! ID: {session_id}")
                    return session_id
                else:
                    st.error("❌ Failed to start session.")
            return None

    return None


def render_end_session_form(
    session: dict,
    on_submit: Callable[[int, dict], bool] | None = None
) -> bool:
    """
    Render form to end an active session.

    Args:
        session: The active session dict.
        on_submit: Callback(session_id, updates) to finalize session.

    Returns:
        True if session ended successfully.
    """
    st.header("🏁 End Session")

    # Show session info
    st.markdown(f"**Location:** {session.get('location')} | **Stake:** {session.get('stake')}")
    st.markdown(f"**Buy-in:** ${session.get('buy_in', 0):,}")

    # Calculate duration
    start_time = datetime.fromisoformat(session.get("start_time", datetime.now().isoformat()))
    duration_hours = (datetime.now() - start_time).total_seconds() / 3600

    st.markdown(f"**Duration:** {duration_hours:.1f} hours")

    with st.form("end_session_form"):
        cash_out = st.number_input(
            "Cash-out ($)",
            min_value=0,
            max_value=100000,
            value=session.get("buy_in", 200),
            step=50,
        )

        notes = st.text_area("Session Notes", placeholder="Key hands, reads, mental state...")

        profit = cash_out - session.get("buy_in", 0)
        hourly = profit / duration_hours if duration_hours > 0 else 0

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            color = "green" if profit >= 0 else "red"
            st.markdown(f"**Profit:** :{color}[${profit:+,}]")
        with col2:
            color = "green" if hourly >= 0 else "red"
            st.markdown(f"**Hourly:** :{color}[${hourly:+,.2f}/hr]")

        submitted = st.form_submit_button("🏁 End Session", use_container_width=True, type="primary")

        if submitted and on_submit:
            updates = {
                "cash_out": cash_out,
                "duration_hours": round(duration_hours, 2),
                "profit": profit,
                "hourly_rate": round(hourly, 2),
                "notes": notes.strip(),
                "status": "completed",
                "end_time": datetime.now().isoformat(),
            }
            success = on_submit(session.get("id"), updates)
            if success:
                st.success("✅ Session ended!")
                return True
            else:
                st.error("❌ Failed to end session.")

    return False


def render_session_form(on_submit: Callable[[dict], bool] | None = None) -> dict | None:
    """
    Render the session logging form (for logging completed sessions).

    Args:
        on_submit: Optional callback function that receives session data.
                   Should return True if save successful.

    Returns:
        Session data dict if submitted, None otherwise.
    """
    st.header("📝 Log Completed Session")

    # Initialize form state
    if "session_form_submitted" not in st.session_state:
        st.session_state.session_form_submitted = False

    with st.form("session_form", clear_on_submit=True):
        # Row 1: Date and Location
        col1, col2 = st.columns(2)

        with col1:
            session_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today(),
            )

        with col2:
            location = st.selectbox(
                "Location",
                options=DEFAULT_LOCATIONS,
                index=0,
            )

        # Row 2: Stake and Duration
        col3, col4 = st.columns(2)

        with col3:
            stake = st.selectbox(
                "Stake",
                options=DEFAULT_STAKES,
                index=0,
            )

        with col4:
            duration = st.number_input(
                "Duration (hours)",
                min_value=0.5,
                max_value=24.0,
                value=4.0,
                step=0.5,
            )

        # Row 3: Buy-in and Cash-out
        col5, col6 = st.columns(2)

        with col5:
            buy_in = st.number_input(
                "Buy-in ($)",
                min_value=0,
                max_value=100000,
                value=200,
                step=50,
            )

        with col6:
            cash_out = st.number_input(
                "Cash-out ($)",
                min_value=0,
                max_value=100000,
                value=200,
                step=50,
            )

        # Notes
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Key hands, reads, mental state...",
            max_chars=500,
        )

        # Calculate stats preview
        profit = cash_out - buy_in
        hourly_rate = profit / duration if duration > 0 else 0

        st.markdown("---")

        # Preview stats
        preview_col1, preview_col2, preview_col3 = st.columns(3)

        with preview_col1:
            profit_color = "green" if profit >= 0 else "red"
            st.markdown(f"**Profit:** :{profit_color}[${profit:+,}]")

        with preview_col2:
            hourly_color = "green" if hourly_rate >= 0 else "red"
            st.markdown(f"**Hourly:** :{hourly_color}[${hourly_rate:+,.2f}/hr]")

        with preview_col3:
            roi = (profit / buy_in * 100) if buy_in > 0 else 0
            roi_color = "green" if roi >= 0 else "red"
            st.markdown(f"**ROI:** :{roi_color}[{roi:+.1f}%]")

        # Submit button
        submitted = st.form_submit_button("💾 Save Session", use_container_width=True)

        if submitted:
            session_data = {
                "date": session_date.isoformat(),
                "location": location,
                "stake": stake,
                "duration_hours": duration,
                "buy_in": buy_in,
                "cash_out": cash_out,
                "profit": profit,
                "hourly_rate": round(hourly_rate, 2),
                "notes": notes.strip() if notes else "",
                "created_at": datetime.now().isoformat(),
            }

            if on_submit:
                success = on_submit(session_data)
                if success:
                    st.success("✅ Session logged successfully!")
                    return session_data
                else:
                    st.error("❌ Failed to save session. Please try again.")
                    return None
            else:
                st.success("✅ Session logged successfully!")
                return session_data

    return None
