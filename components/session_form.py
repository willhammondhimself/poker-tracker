"""Session logging form component."""

import streamlit as st
from datetime import date, datetime
from typing import Callable


# Common poker locations and stakes
DEFAULT_LOCATIONS = ["ClubWPT Gold", "Morongo Casino", "Commerce Casino", "Home Game", "Other"]
DEFAULT_STAKES = ["1/2", "1/3", "2/5", "5/10", "Other"]


def render_session_form(on_submit: Callable[[dict], bool] | None = None) -> dict | None:
    """
    Render the session logging form.

    Args:
        on_submit: Optional callback function that receives session data.
                   Should return True if save successful.

    Returns:
        Session data dict if submitted, None otherwise.
    """
    st.header("📝 Log Session")

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
