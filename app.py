"""Main streamlit app."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data_loader import (
    load_sessions,
    save_session,
    get_session,
    update_session,
    delete_session,
    save_hand,
    load_hands,
    load_opponents,
    get_or_create_opponent,
    get_opponent,
    get_opponent_with_tags,
    update_opponent_stats,
    calculate_opponent_stats,
    load_settings,
    update_bankroll,
)
from utils.analytics_engine import get_edge_summary, analyze_opponent_tendencies
from utils.ai_coach import (
    analyze_hand,
    render_api_key_input,
    render_analysis_result,
    get_api_key,
)
from utils.ignition_parser import parse_ignition_file, get_import_summary
from utils.range_analyzer import analyze_ranges, get_range_grid_data, get_position_summary, RANKS
from utils.poker_math import calculate_winrate_ci, get_sample_size_message
from utils.monte_carlo import (
    simulate_bankroll,
    calculate_kelly_criterion,
    estimate_time_to_target,
    get_sample_trajectories,
    get_percentile_trajectories,
)
from utils.tilt_detector import (
    detect_tilt,
    get_tilt_color,
    get_tilt_emoji,
)
from components import (
    render_session_form,
    render_start_session_form,
    render_end_session_form,
    render_card_selector,
    render_board_cards,
    render_analytics_page,
    parse_multi_cards,
    render_hand_visualizer,
    render_hand_replayer,
)


# Page Configuration
st.set_page_config(
    page_title="Quant Poker Edge",
    page_icon="♠️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Init session state."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None
    if "bankroll" not in st.session_state or "bankroll_target" not in st.session_state:
        # Load from persistent settings file
        settings = load_settings()
        st.session_state.bankroll = settings.get("bankroll", 350.00)
        st.session_state.bankroll_target = settings.get("bankroll_target", 500.00)


def apply_theme():
    """Apply theme."""
    if st.session_state.dark_mode:
        st.markdown(
            """
            <style>
            .stApp { background-color: #0e1117; }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar():
    """Sidebar nav. Returns selected page."""
    with st.sidebar:
        st.title("♠️ Quant Poker Edge")

        # Live session indicator
        if st.session_state.active_session_id:
            session = get_session(st.session_state.active_session_id)
            if session and session.get("status") == "active":
                st.markdown(
                    f'<div style="background: linear-gradient(135deg, #27AE60, #2ECC71); '
                    f'padding: 10px; border-radius: 8px; margin: 10px 0;">'
                    f'<span style="color: white; font-weight: bold;">🟢 LIVE SESSION</span><br>'
                    f'<span style="color: #E8F8F5; font-size: 0.9em;">'
                    f'{session.get("location")} - ${session.get("stake")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                # Session was completed or deleted, clear the state
                st.session_state.active_session_id = None

        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            options=["Dashboard", "Log Session", "Hand Logger", "Data Import", "My Ranges", "Analytics", "Simulator", "Quant Lab"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Bankroll Status Progress Bar
        bankroll = st.session_state.bankroll
        target = st.session_state.bankroll_target
        progress = min(bankroll / target, 1.0) if target > 0 else 0

        st.markdown("**💰 Bankroll Status**")
        st.progress(progress)
        progress_color = "#27AE60" if progress >= 0.8 else "#F39C12" if progress >= 0.5 else "#E74C3C"
        st.markdown(
            f'<div style="text-align: center; margin-top: -10px;">'
            f'<span style="color: {progress_color}; font-weight: bold;">${bankroll:,.2f}</span>'
            f' / ${target:,.2f} to Next Stake</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Quick EV Calculator
        from components.ev_calculator import render_mini_ev_calculator
        with st.expander("💰 Quick EV Check"):
            render_mini_ev_calculator()

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
            st.markdown("**Bankroll Settings**")
            new_bankroll = st.number_input(
                "Current Bankroll ($)",
                value=float(st.session_state.bankroll),
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key="bankroll_input",
            )
            new_target = st.number_input(
                "Target for Next Stake ($)",
                value=float(st.session_state.bankroll_target),
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="target_input",
            )
            if new_bankroll != st.session_state.bankroll or new_target != st.session_state.bankroll_target:
                st.session_state.bankroll = new_bankroll
                st.session_state.bankroll_target = new_target
                # Save to persistent file and refresh to sync both displays
                update_bankroll(new_bankroll, new_target)
                st.rerun()

        st.markdown("---")

        # AI Coach Settings
        render_api_key_input()

        st.caption("v0.6.0 | Phase 4: Polish")

    return page


def render_dashboard():
    """Main dashboard."""
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

    # Load hands once for both PDF and My Edge Card
    hands = load_hands()

    # PDF Report Download
    from utils.report_generator import generate_tearsheet
    from datetime import datetime as dt

    with st.expander("📄 Generate Performance Report"):
        st.markdown("Export a professional PDF tearsheet with your stats and session history.")
        if st.button("Generate PDF", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                pdf_bytes = generate_tearsheet(sessions, hands)
                st.download_button(
                    label="Download PDF Tearsheet",
                    data=pdf_bytes,
                    file_name=f"poker_tearsheet_{dt.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    st.markdown("---")

    # My Edge Card
    if hands:
        edge_summary = get_edge_summary(hands, sessions)

        st.subheader("🎯 My Edge")

        edge_col1, edge_col2 = st.columns(2)

        with edge_col1:
            st.markdown("**💪 Top Exploits** *(Your Strengths)*")
            if edge_summary["exploits"]:
                for exploit in edge_summary["exploits"][:3]:
                    st.markdown(
                        f'<div style="background: linear-gradient(135deg, #27AE60, #2ECC71); '
                        f'padding: 10px; border-radius: 8px; margin: 5px 0;">'
                        f'<span style="color: white; font-weight: bold;">'
                        f'+{exploit["bb_100"]:.1f} BB/100</span> '
                        f'<span style="color: #E8F8F5;">{exploit["description"]}</span>'
                        f'<br><span style="color: #A9DFBF; font-size: 0.8em;">'
                        f'${exploit["total_profit"]:+,.0f} over {exploit["hands"]} hands</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Log more hands to identify your strengths")

        with edge_col2:
            st.markdown("**🩸 Top Leaks** *(Areas to Improve)*")
            if edge_summary["leaks"]:
                for leak in edge_summary["leaks"][:3]:
                    st.markdown(
                        f'<div style="background: linear-gradient(135deg, #E74C3C, #C0392B); '
                        f'padding: 10px; border-radius: 8px; margin: 5px 0;">'
                        f'<span style="color: white; font-weight: bold;">'
                        f'{leak["bb_100"]:.1f} BB/100</span> '
                        f'<span style="color: #FADBD8;">{leak["description"]}</span>'
                        f'<br><span style="color: #F5B7B1; font-size: 0.8em;">'
                        f'${leak["total_loss"]:+,.0f} over {leak["hands"]} hands</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Log more hands to identify leaks")

        # Recommendations
        if edge_summary["recommendations"]:
            with st.expander("📋 Recommendations"):
                for rec in edge_summary["recommendations"]:
                    priority_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
                    st.markdown(f"{priority_color} **{rec['leak']}** ({rec['bb_100']:.1f} BB/100)")
                    st.markdown(f"> {rec['recommendation']}")
                    st.markdown("---")

        # Overall BB/100
        overall_bb = edge_summary["overall_bb_100"]
        bb_color = "#27AE60" if overall_bb >= 0 else "#E74C3C"
        st.markdown(
            f'<div style="text-align: center; margin-top: 15px;">'
            f'<span style="font-size: 1.2em; color: #888;">Overall: </span>'
            f'<span style="font-size: 1.5em; font-weight: bold; color: {bb_color};">'
            f'{overall_bb:+.1f} BB/100</span>'
            f'<span style="color: #888;"> ({edge_summary["total_hands"]} hands logged)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Confidence Interval Display
        total_hands = edge_summary["total_hands"]
        if total_hands >= 10:
            # Calculate total BB won from overall_bb and hands
            total_bb_won = overall_bb * total_hands / 100
            ci_result = calculate_winrate_ci(total_bb_won, total_hands)

            # Color based on CI crossing zero
            if ci_result["ci_lower"] > 0:
                ci_color = "#27AE60"  # Green - significant winner
                ci_bg = "linear-gradient(135deg, rgba(39, 174, 96, 0.15), rgba(46, 204, 113, 0.1))"
            elif ci_result["ci_upper"] < 0:
                ci_color = "#E74C3C"  # Red - significant loser
                ci_bg = "linear-gradient(135deg, rgba(231, 76, 60, 0.15), rgba(192, 57, 43, 0.1))"
            else:
                ci_color = "#F39C12"  # Yellow - inconclusive
                ci_bg = "linear-gradient(135deg, rgba(243, 156, 18, 0.15), rgba(230, 126, 34, 0.1))"

            st.markdown(
                f'<div style="background: {ci_bg}; border-radius: 10px; padding: 12px; '
                f'margin-top: 15px; border: 1px solid {ci_color}40;">'
                f'<div style="text-align: center;">'
                f'<span style="color: #888; font-size: 0.9em;">95% Confidence Interval:</span><br>'
                f'<span style="color: {ci_color}; font-weight: bold; font-size: 1.3em;">'
                f'{ci_result["ci_lower"]:+.1f} to {ci_result["ci_upper"]:+.1f} BB/100</span>'
                f'</div>'
                f'<div style="color: #aaa; font-size: 0.8em; margin-top: 8px; text-align: center;">'
                f'{get_sample_size_message(ci_result["sample_adequacy"])}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Tilt Detection for recent session
        if sessions and hands:
            # Get most recent session with hands
            recent_session = max(sessions, key=lambda s: s.get('date', ''))
            recent_session_id = recent_session.get('id')
            recent_hands = [h for h in hands if h.get('session_id') == recent_session_id]

            if len(recent_hands) >= 20:
                tilt_analysis = detect_tilt(recent_hands)
                tilt_color = get_tilt_color(tilt_analysis.tilt_score)
                tilt_emoji = get_tilt_emoji(tilt_analysis.tilt_level)

                st.markdown("---")
                st.markdown("##### 🧠 Emotional Control (Last Session)")

                tilt_col1, tilt_col2 = st.columns([1, 2])

                with tilt_col1:
                    st.markdown(
                        f'<div style="background: linear-gradient(135deg, {tilt_color}, {tilt_color}dd); '
                        f'padding: 20px; border-radius: 10px; text-align: center;">'
                        f'<div style="font-size: 2em;">{tilt_emoji}</div>'
                        f'<div style="color: white; font-size: 1.8em; font-weight: bold;">'
                        f'{tilt_analysis.tilt_score:.1f}/10</div>'
                        f'<div style="color: #ffffffcc; font-size: 0.9em;">Tilt Score</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with tilt_col2:
                    # Show warning and indicators
                    if tilt_analysis.tilt_level == 'severe':
                        st.error(tilt_analysis.warning_message)
                    elif tilt_analysis.tilt_level == 'moderate':
                        st.warning(tilt_analysis.warning_message)
                    elif tilt_analysis.tilt_level == 'mild':
                        st.info(tilt_analysis.warning_message)
                    else:
                        st.success(tilt_analysis.warning_message)

                    # Show key indicators
                    indicators = []
                    if tilt_analysis.downswing_detected:
                        indicators.append("📉 Downswing detected")
                    if tilt_analysis.vpip_increase > 5:
                        indicators.append(f"📈 VPIP +{tilt_analysis.vpip_increase:.0f}% after losses")
                    if tilt_analysis.aggression_spike:
                        indicators.append("⚡ Aggression spike")
                    if tilt_analysis.loss_chasing:
                        indicators.append("🎰 Loss chasing behavior")

                    if indicators:
                        st.markdown("**Indicators:** " + " | ".join(indicators))

                # Recommendations in expander
                if tilt_analysis.tilt_level != 'none' and tilt_analysis.recommendations:
                    with st.expander("💡 Recommendations"):
                        for rec in tilt_analysis.recommendations:
                            st.markdown(f"- {rec}")

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

    # Session Management
    st.markdown("---")
    with st.expander("⚙️ Manage Sessions"):
        # Filter to completed sessions only
        completed_sessions = [s for s in sessions if s.get("status") != "active"]

        if not completed_sessions:
            st.info("No completed sessions to manage.")
        else:
            # Session selector
            session_options = {
                f"{s.get('date')} - {s.get('location')} ({s.get('stake')}) - ${s.get('profit', 0):+,}": s.get("id")
                for s in sorted(completed_sessions, key=lambda x: x.get("date", ""), reverse=True)
            }

            selected_label = st.selectbox(
                "Select Session",
                options=list(session_options.keys()),
            )

            if selected_label:
                selected_id = session_options[selected_label]
                selected_session = get_session(selected_id)

                if selected_session:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Session Details:**")
                        st.write(f"📅 Date: {selected_session.get('date')}")
                        st.write(f"📍 Location: {selected_session.get('location')}")
                        st.write(f"💰 Stake: {selected_session.get('stake')}")
                        st.write(f"💵 Buy-in: ${selected_session.get('buy_in', 0):,}")
                        st.write(f"💸 Cash-out: ${selected_session.get('cash_out', 0):,}")
                        profit = selected_session.get("profit", 0)
                        color = "green" if profit >= 0 else "red"
                        st.markdown(f"📊 Profit: :{color}[${profit:+,}]")

                    with col2:
                        st.markdown("**Actions:**")

                        # Edit session
                        with st.form(f"edit_session_{selected_id}"):
                            new_notes = st.text_area(
                                "Edit Notes",
                                value=selected_session.get("notes", ""),
                            )
                            new_buy_in = st.number_input(
                                "Buy-in ($)",
                                value=selected_session.get("buy_in", 0),
                                min_value=0,
                            )
                            new_cash_out = st.number_input(
                                "Cash-out ($)",
                                value=selected_session.get("cash_out", 0),
                                min_value=0,
                            )

                            if st.form_submit_button("💾 Save Changes"):
                                new_profit = new_cash_out - new_buy_in
                                hours = selected_session.get("duration_hours", 1)
                                new_hourly = new_profit / hours if hours > 0 else 0

                                updates = {
                                    "notes": new_notes,
                                    "buy_in": new_buy_in,
                                    "cash_out": new_cash_out,
                                    "profit": new_profit,
                                    "hourly_rate": round(new_hourly, 2),
                                }
                                if update_session(selected_id, updates):
                                    st.success("✅ Session updated!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update session.")

                        # Delete session
                        st.markdown("---")
                        if st.button("🗑️ Delete Session", type="secondary", use_container_width=True):
                            st.session_state[f"confirm_delete_{selected_id}"] = True

                        if st.session_state.get(f"confirm_delete_{selected_id}"):
                            st.warning("⚠️ Are you sure? This cannot be undone.")
                            del_col1, del_col2 = st.columns(2)
                            with del_col1:
                                if st.button("✅ Yes, Delete", use_container_width=True):
                                    if delete_session(selected_id):
                                        st.success("Session deleted.")
                                        del st.session_state[f"confirm_delete_{selected_id}"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete.")
                            with del_col2:
                                if st.button("❌ Cancel", use_container_width=True):
                                    del st.session_state[f"confirm_delete_{selected_id}"]
                                    st.rerun()


def render_log_session():
    """Session logging page."""
    # Check if there's an active session
    active_session = None
    if st.session_state.active_session_id:
        active_session = get_session(st.session_state.active_session_id)
        if active_session and active_session.get("status") != "active":
            active_session = None
            st.session_state.active_session_id = None

    if active_session:
        # Show end session form
        def end_callback(session_id: int, updates: dict) -> bool:
            success = update_session(session_id, updates)
            if success:
                st.session_state.active_session_id = None
            return success

        ended = render_end_session_form(active_session, on_submit=end_callback)
        if ended:
            st.rerun()
    else:
        # Show tabs for starting new or logging completed
        tab1, tab2 = st.tabs(["🎮 Start Live Session", "📝 Log Completed Session"])

        with tab1:
            def start_callback(session_data: dict) -> int | None:
                session_id = save_session(session_data)
                if session_id:
                    st.session_state.active_session_id = session_id
                return session_id

            session_id = render_start_session_form(on_submit=start_callback)
            if session_id:
                st.rerun()

        with tab2:
            render_session_form(on_submit=lambda s: save_session(s) is not None)


def render_hand_logger():
    """Hand logger page."""
    st.header("🃏 Hand Logger")

    # Quick entry at TOP for mobile-first design
    st.markdown("**⌨️ Quick Entry** *(type: `As Kh` or `AsKh`)*")
    quick_both = st.text_input(
        "Enter hole cards",
        key="quick_both_cards",
        placeholder="As Kh, As,Kh, or AsKh...",
        label_visibility="collapsed",
    )

    # Parse quick entry for both cards
    if quick_both:
        parsed_cards = parse_multi_cards(quick_both)
        if len(parsed_cards) >= 2:
            # Set both cards in session state
            st.session_state["card_selector_hole_card_1"] = {
                "selected_rank": parsed_cards[0][0],
                "selected_suit": parsed_cards[0][1],
                "completed_card": parsed_cards[0],
            }
            st.session_state["card_selector_hole_card_2"] = {
                "selected_rank": parsed_cards[1][0],
                "selected_suit": parsed_cards[1][1],
                "completed_card": parsed_cards[1],
            }

    st.markdown("---")

    # Check for active session
    active_session = None
    if st.session_state.active_session_id:
        active_session = get_session(st.session_state.active_session_id)
        if active_session and active_session.get("status") != "active":
            active_session = None

    if not active_session:
        st.warning("⚠️ **No active session.** Start a session first to log hands.")
        if st.button("➡️ Go to Log Session", use_container_width=True):
            st.session_state["nav_override"] = "Log Session"
            st.rerun()
        st.markdown("---")

    else:
        # Show active session info (compact)
        st.success(
            f"📍 {active_session.get('location')} - ${active_session.get('stake')}"
        )

    st.markdown("**Or select cards individually:**")

    # Get current card selections (dynamic, not accumulated)
    card1_state = st.session_state.get("card_selector_hole_card_1", {})
    card2_state = st.session_state.get("card_selector_hole_card_2", {})
    card1 = card1_state.get("completed_card")
    card2 = card2_state.get("completed_card")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Only mark card2 as used (not card1 itself)
        used_for_card1 = {card2} if card2 else set()
        card1 = render_card_selector(
            "hole_card_1",
            used_for_card1,
            label="Card 1"
        )

    with col2:
        # Only mark card1 as used (not card2 itself)
        used_for_card2 = {card1} if card1 else set()
        card2 = render_card_selector(
            "hole_card_2",
            used_for_card2,
            label="Card 2"
        )

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

            # Hand logging form (only if active session)
            if active_session:
                st.markdown("---")

                # Board cards (optional) - use hole cards as used
                hole_cards_used = set()
                if card1:
                    hole_cards_used.add(card1)
                if card2:
                    hole_cards_used.add(card2)

                with st.expander("🃏 Add Board Cards (Optional)", expanded=False):
                    board = render_board_cards(
                        "board",
                        hole_cards_used,
                    )

                with st.form("log_hand_form", clear_on_submit=True):
                    pos_col, action_col, result_col = st.columns(3)

                    with pos_col:
                        position = st.selectbox(
                            "Position",
                            ["BTN", "CO", "HJ", "LJ", "UTG", "SB", "BB"],
                        )

                    with action_col:
                        preflop_action = st.selectbox(
                            "Preflop Action",
                            ["raise", "call", "fold", "check", "all-in"],
                        )

                    with result_col:
                        result = st.number_input("Result ($)", value=0, step=10)

                    # Opponent tracking
                    opp_col1, opp_col2 = st.columns(2)
                    with opp_col1:
                        # Get existing opponents for autocomplete
                        existing_opponents = load_opponents()
                        opponent_names = ["(None)"] + [o.get("name", "") for o in existing_opponents]
                        opponent_select = st.selectbox(
                            "Villain",
                            opponent_names,
                            help="Select existing or type new name below",
                        )
                    with opp_col2:
                        new_opponent = st.text_input(
                            "New Villain Name",
                            placeholder="e.g., Seat 3, TAG_Mike, Fish_lady",
                            help="Add a new opponent if not in list",
                        )

                    # Opponent action tracking
                    with st.expander("Villain Actions (for HUD stats)"):
                        opp_action_cols = st.columns(4)
                        with opp_action_cols[0]:
                            villain_vpip = st.checkbox("VPIP", help="Villain put money in pot voluntarily")
                        with opp_action_cols[1]:
                            villain_pfr = st.checkbox("PFR", help="Villain raised preflop")
                        with opp_action_cols[2]:
                            villain_3bet = st.checkbox("3-Bet", help="Villain 3-bet")
                        with opp_action_cols[3]:
                            villain_cbet = st.checkbox("C-Bet", help="Villain continuation bet")

                    # Street-by-street actions (optional)
                    with st.expander("Street Actions (Optional)"):
                        street_cols = st.columns(3)
                        with street_cols[0]:
                            flop_action = st.selectbox(
                                "Flop",
                                ["—", "bet", "check", "call", "raise", "fold"],
                                key="flop_action",
                            )
                        with street_cols[1]:
                            turn_action = st.selectbox(
                                "Turn",
                                ["—", "bet", "check", "call", "raise", "fold"],
                                key="turn_action",
                            )
                        with street_cols[2]:
                            river_action = st.selectbox(
                                "River",
                                ["—", "bet", "check", "call", "raise", "fold"],
                                key="river_action",
                            )

                    notes = st.text_input("Notes", placeholder="Villain tendencies, key decision...")

                    if st.form_submit_button("💾 Log Hand", use_container_width=True):
                        # Build street actions dict
                        street_actions = {}
                        if flop_action != "—":
                            street_actions["flop"] = flop_action
                        if turn_action != "—":
                            street_actions["turn"] = turn_action
                        if river_action != "—":
                            street_actions["river"] = river_action

                        # Handle opponent
                        opponent_id = None
                        opponent_name = None
                        if new_opponent.strip():
                            # Create or get new opponent
                            opp = get_or_create_opponent(new_opponent.strip())
                            opponent_id = opp.get("id")
                            opponent_name = opp.get("name")
                        elif opponent_select != "(None)":
                            # Use selected opponent
                            opp = get_or_create_opponent(opponent_select)
                            opponent_id = opp.get("id")
                            opponent_name = opp.get("name")

                        hand_data = {
                            "hole_cards": [card1, card2],
                            "board": board if any(board.values()) else None,
                            "position": position,
                            "action": preflop_action,
                            "street_actions": street_actions if street_actions else None,
                            "result": result,
                            "notes": notes,
                            "opponent_id": opponent_id,
                            "opponent_name": opponent_name,
                        }

                        if save_hand(hand_data, active_session.get("id")):
                            # Update opponent stats if we have an opponent
                            if opponent_id:
                                update_opponent_stats(
                                    opponent_id,
                                    hand_action=preflop_action,
                                    is_vpip=villain_vpip,
                                    is_pfr=villain_pfr,
                                    is_3bet=villain_3bet,
                                    is_cbet=villain_cbet,
                                )
                            st.success("✅ Hand logged!")

                            # Store last logged hand for AI Coach
                            st.session_state["last_logged_hand"] = hand_data
                            st.session_state["last_logged_session"] = active_session

                            # Ask Coach + GTO Wizard buttons (Location A: after logging)
                            coach_col, gto_col = st.columns(2)
                            with coach_col:
                                if get_api_key():
                                    if st.button("🤖 Ask Coach", key="ask_coach_new", use_container_width=True):
                                        st.session_state["analyze_hand"] = hand_data
                                        st.session_state["analyze_session"] = active_session
                                        st.session_state["analyze_opponent_id"] = opponent_id
                                else:
                                    st.info("💡 Add API key for AI Coach")
                            with gto_col:
                                # Build GTO Wizard search URL
                                cards_str = f"{card1[0]}{card1[1]}{card2[0]}{card2[1]}" if card1 and card2 else ""
                                gto_query = f"{position} {cards_str} {preflop_action}"
                                gto_url = f"https://gtowizard.com/solutions?q={gto_query.replace(' ', '%20')}"
                                st.link_button("🔗 GTO Wizard", gto_url, use_container_width=True)

                            # Reset cards
                            for k in list(st.session_state.keys()):
                                if k.startswith("card_selector_") or k.startswith("board_") or k == "quick_both_cards":
                                    del st.session_state[k]
                            st.rerun()
                        else:
                            st.error("❌ Failed to log hand.")
        else:
            st.info("Select both cards to see your hand")

        if st.button("🔄 Reset All Cards", use_container_width=True):
            # Clear all card selector states
            for k in list(st.session_state.keys()):
                if k.startswith("card_selector_") or k.startswith("board_") or k == "quick_both_cards":
                    del st.session_state[k]
            st.rerun()

    # Show AI Coach Analysis if requested
    if st.session_state.get("analyze_hand"):
        st.markdown("---")
        hand_to_analyze = st.session_state.get("analyze_hand")
        session_for_analysis = st.session_state.get("analyze_session", active_session or {})
        opponent_id = st.session_state.get("analyze_opponent_id")

        # Get opponent data with auto-tags if available
        opponent_data = None
        if opponent_id:
            opponent_data = get_opponent_with_tags(opponent_id)
            # Show opponent tags if available
            if opponent_data and opponent_data.get('tags_html'):
                st.markdown(
                    f"**Opponent Profile:** {opponent_data.get('name', 'Unknown')} "
                    f"{opponent_data.get('tags_html', '')}",
                    unsafe_allow_html=True,
                )
                # Show exploitation tips
                tips = opponent_data.get('exploitation_tips', [])
                if tips:
                    with st.expander("🎯 Exploitation Tips"):
                        for tip in tips:
                            st.markdown(f"- {tip}")

        with st.spinner("🤖 Analyzing hand..."):
            result = analyze_hand(hand_to_analyze, session_for_analysis, opponent_data)
            render_analysis_result(result)

        # Show the hand being analyzed with visual cards
        st.markdown("##### Hand Analyzed:")
        render_hand_visualizer(
            hole_cards=hand_to_analyze.get("hole_cards", []),
            board=hand_to_analyze.get("board"),
            position=hand_to_analyze.get("position"),
            opponent=hand_to_analyze.get("opponent_name"),
            action=hand_to_analyze.get("action"),
            result=hand_to_analyze.get("result"),
        )

        if st.button("✖️ Close Analysis", use_container_width=True):
            del st.session_state["analyze_hand"]
            if "analyze_session" in st.session_state:
                del st.session_state["analyze_session"]
            if "analyze_opponent_id" in st.session_state:
                del st.session_state["analyze_opponent_id"]
            st.rerun()

    # Show logged hands for this session
    if active_session:
        hands = load_hands(active_session.get("id"))
        if hands:
            st.markdown("---")
            st.subheader(f"📋 Hands This Session ({len(hands)})")

            has_api_key = bool(get_api_key())

            # Check if replaying a hand
            if "replay_hand" in st.session_state and st.session_state["replay_hand"]:
                st.markdown("##### 🎬 Hand Replayer")
                render_hand_replayer(st.session_state["replay_hand"])
                if st.button("✖️ Close Replayer", use_container_width=True):
                    del st.session_state["replay_hand"]
                    st.rerun()
                st.markdown("---")

            for idx, hand in enumerate(reversed(hands[-5:])):  # Show last 5
                cards = hand.get("hole_cards", [])
                card_str = f"{cards[0][0]}{cards[0][1]} {cards[1][0]}{cards[1][1]}" if len(cards) == 2 else "?"
                result = hand.get("result", 0)
                color = "green" if result >= 0 else "red"
                villain = hand.get("opponent_name", "")
                villain_str = f" vs **{villain}**" if villain else ""

                # Create columns for hand info and action buttons
                hand_col, replay_col, coach_col = st.columns([5, 1, 1])

                with hand_col:
                    st.markdown(
                        f"**{card_str}** | {hand.get('position')} | {hand.get('action')} | "
                        f":{color}[${result:+}]{villain_str}"
                    )

                with replay_col:
                    if st.button("🎬", key=f"replay_hand_{idx}", help="Replay Hand"):
                        st.session_state["replay_hand"] = hand
                        st.rerun()

                with coach_col:
                    if has_api_key:
                        if st.button("🤖", key=f"coach_hand_{idx}", help="Ask AI Coach"):
                            st.session_state["analyze_hand"] = hand
                            st.session_state["analyze_session"] = active_session
                            st.session_state["analyze_opponent_id"] = hand.get("opponent_id")
                            st.rerun()


def render_data_import():
    """Ignition import page."""
    st.header("📥 Data Import")
    st.markdown("Import hand histories from **Ignition Casino** (Zone Poker)")

    st.markdown("""
    ### How to Export from Ignition:
    1. Go to **Poker Lobby** → **Account** → **Hand History**
    2. Select your date range and download the `.txt` file
    3. Upload it below
    """)

    st.markdown("---")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Ignition Hand History (.txt)",
        type=['txt'],
        help="Upload your Ignition/Bovada hand history text file",
    )

    if uploaded_file is not None:
        # Read file content
        file_content = uploaded_file.read().decode('utf-8')

        with st.spinner("Parsing hand history..."):
            # Parse the file
            parsed_hands = parse_ignition_file(file_content)

        if not parsed_hands:
            st.error("❌ No hands could be parsed from this file. Make sure it's a valid Ignition hand history.")
            return

        # Show summary
        summary = get_import_summary(parsed_hands)

        st.success(f"✅ Found **{summary['total_hands']}** hands to import!")

        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            profit_color = "green" if summary['total_profit'] >= 0 else "red"
            st.metric("Total Profit", f"${summary['total_profit']:+.2f}")
        with col2:
            st.metric("Winning Hands", summary['winning_hands'])
        with col3:
            st.metric("Losing Hands", summary['losing_hands'])
        with col4:
            st.metric("Win Rate", f"{summary['win_rate']}%")

        st.markdown(f"**Stakes:** {', '.join(summary['stakes'])}")
        if summary['date_range']:
            st.markdown(f"**Date Range:** {summary['date_range']}")

        st.markdown("---")

        # Preview some hands
        with st.expander("Preview Hands", expanded=False):
            for i, hand in enumerate(parsed_hands[:5]):
                cards = hand.get('hole_cards', [])
                if len(cards) == 2:
                    card_str = f"{cards[0][0]}{cards[0][1]} {cards[1][0]}{cards[1][1]}"
                else:
                    card_str = "?"
                result = hand.get('result', 0)
                color = "green" if result >= 0 else "red"
                st.markdown(
                    f"**{card_str}** | {hand.get('position')} | {hand.get('action')} | "
                    f":{color}[${result:+.2f}]"
                )
            if len(parsed_hands) > 5:
                st.caption(f"...and {len(parsed_hands) - 5} more hands")

        st.markdown("---")

        # Import options
        st.markdown("### Import Options")

        # Create or select session for imported hands
        create_session = st.checkbox(
            "Create new session for imported hands",
            value=True,
            help="Group imported hands under a new session entry",
        )

        if create_session:
            session_col1, session_col2 = st.columns(2)
            with session_col1:
                import_location = st.text_input(
                    "Location",
                    value="Ignition Zone Poker",
                )
            with session_col2:
                import_stake = st.selectbox(
                    "Stake",
                    options=summary['stakes'] if summary['stakes'] else ['0.05/0.10'],
                )

        # Import button
        if st.button("📥 Import Hands", type="primary", use_container_width=True):
            with st.spinner("Importing hands..."):
                session_id = None

                if create_session:
                    # Create a new session for these hands
                    from datetime import datetime

                    # Get date from first hand or use today
                    first_date = parsed_hands[0].get('date', datetime.now().isoformat())
                    if isinstance(first_date, str):
                        session_date = first_date[:10]
                    else:
                        session_date = first_date.strftime('%Y-%m-%d')

                    # Calculate session stats
                    total_profit = sum(h.get('result', 0) for h in parsed_hands)
                    duration = max(1, len(parsed_hands) / 60)  # Estimate ~60 hands/hour

                    session_data = {
                        'date': session_date,
                        'location': import_location,
                        'stake': import_stake,
                        'buy_in': 0,  # Unknown for imports
                        'cash_out': 0,
                        'profit': round(total_profit, 2),
                        'duration_hours': round(duration, 1),
                        'hourly_rate': round(total_profit / duration, 2) if duration > 0 else 0,
                        'notes': f'Imported {len(parsed_hands)} hands from Ignition',
                        'status': 'completed',
                        'source': 'ignition_import',
                    }

                    session_id = save_session(session_data)

                # Save all hands
                success_count = 0
                for hand in parsed_hands:
                    if save_hand(hand, session_id):
                        success_count += 1

            if success_count > 0:
                st.success(f"✅ Successfully imported **{success_count}** hands!")
                st.balloons()

                # Show next steps
                st.markdown("### Next Steps")
                st.markdown("""
                - Go to **Dashboard** to see your updated stats
                - Check **Analytics** for your LeakFinder analysis
                - Use **AI Coach** to review specific hands
                """)
            else:
                st.error("❌ Failed to import hands. Please try again.")

    # Show existing import history
    st.markdown("---")
    st.subheader("📊 Import History")

    sessions = load_sessions()
    imported_sessions = [s for s in sessions if s.get('source') == 'ignition_import']

    if imported_sessions:
        for session in sorted(imported_sessions, key=lambda x: x.get('date', ''), reverse=True)[:5]:
            st.markdown(
                f"**{session.get('date')}** - {session.get('location')} | "
                f"${session.get('profit', 0):+.2f} | {session.get('notes', '')}"
            )
    else:
        st.info("No imported sessions yet. Upload a hand history file above to get started.")


def render_my_ranges():
    """Range chart page."""
    import plotly.graph_objects as go

    st.header("📊 My Ranges")
    st.markdown("Visualize your actual playing ranges by position")

    # Load all hands
    hands = load_hands()

    if not hands:
        st.warning("No hands logged yet. Import hand histories or log hands manually to see your ranges.")
        return

    # Position filter
    positions = ['All Positions', 'BTN', 'CO', 'MP', 'EP', 'SB', 'BB']

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        selected_position = st.selectbox(
            "Position",
            options=positions,
            index=0,
        )
    with col2:
        view_mode = st.selectbox(
            "View Mode",
            options=['Frequency', 'Profit', 'Win Rate'],
            index=0,
        )
    with col3:
        color_scheme = st.selectbox(
            "Color Scheme",
            options=['Green/Red', 'Blue', 'Heat'],
            index=0,
        )

    # Get position filter
    pos_filter = None if selected_position == 'All Positions' else selected_position

    # Analyze ranges
    range_data = analyze_ranges(hands, pos_filter)
    grid_data = get_range_grid_data(
        range_data['matrix'],
        mode=view_mode.lower().replace(' ', '')
    )

    # Show summary stats
    st.markdown("---")
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("Total Hands", range_data['total_hands'])
    with stat_cols[1]:
        st.metric("VPIP Hands", range_data['vpip_hands'])
    with stat_cols[2]:
        st.metric("VPIP %", f"{range_data['vpip_pct']}%")
    with stat_cols[3]:
        total_profit = sum(cell['profit'] for row in grid_data for cell in row)
        profit_color = "green" if total_profit >= 0 else "red"
        st.metric("Total Profit", f"${total_profit:+.2f}")

    st.markdown("---")

    # Build the heatmap
    # Create labels and values matrices
    z_values = []
    hover_text = []
    annotations = []

    for row_idx, row in enumerate(grid_data):
        z_row = []
        hover_row = []
        for col_idx, cell in enumerate(row):
            # Value for color intensity
            if view_mode == 'Frequency':
                z_row.append(cell['count'])
            elif view_mode == 'Profit':
                z_row.append(cell['avg_profit'])
            else:  # Win Rate
                z_row.append(cell['winrate'] - 50)  # Center around 50%

            # Hover text
            hover_row.append(
                f"<b>{cell['hand']}</b><br>"
                f"Count: {cell['count']}<br>"
                f"Profit: ${cell['profit']:+.2f}<br>"
                f"Avg: ${cell['avg_profit']:+.2f}<br>"
                f"Win Rate: {cell['winrate']}%"
            )

            # Annotation (hand name)
            annotations.append(dict(
                x=col_idx,
                y=row_idx,
                text=cell['hand'],
                font=dict(
                    size=10,
                    color='white' if cell['count'] > 0 else 'gray'
                ),
                showarrow=False,
            ))

        z_values.append(z_row)
        hover_text.append(hover_row)

    # Color scale based on selection
    if color_scheme == 'Green/Red':
        if view_mode == 'Frequency':
            colorscale = [[0, '#1a1a2e'], [0.5, '#2d5a27'], [1, '#27ae60']]
        else:
            colorscale = [[0, '#c0392b'], [0.5, '#2c3e50'], [1, '#27ae60']]
    elif color_scheme == 'Blue':
        colorscale = [[0, '#1a1a2e'], [0.5, '#2980b9'], [1, '#3498db']]
    else:  # Heat
        colorscale = [[0, '#2c3e50'], [0.33, '#e74c3c'], [0.66, '#f39c12'], [1, '#f1c40f']]

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=RANKS,
        y=RANKS,
        hovertext=hover_text,
        hoverinfo='text',
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(
            title=view_mode,
            titleside='right',
        ),
    ))

    # Add annotations
    fig.update_layout(
        annotations=annotations,
        xaxis=dict(
            title='',
            tickvals=list(range(13)),
            ticktext=RANKS,
            side='top',
        ),
        yaxis=dict(
            title='',
            tickvals=list(range(13)),
            ticktext=RANKS,
            autorange='reversed',
        ),
        height=600,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    st.plotly_chart(fig, use_container_width=True)

    # Position breakdown
    st.markdown("---")
    st.subheader("📍 Position Breakdown")

    position_stats = get_position_summary(hands)

    if position_stats:
        # Sort by standard position order
        pos_order = ['EP', 'MP', 'CO', 'BTN', 'SB', 'BB']
        sorted_positions = sorted(
            position_stats.items(),
            key=lambda x: pos_order.index(x[0]) if x[0] in pos_order else 99
        )

        pos_cols = st.columns(min(6, len(sorted_positions)))
        for i, (pos, stats) in enumerate(sorted_positions[:6]):
            with pos_cols[i % 6]:
                profit_color = "🟢" if stats['profit'] >= 0 else "🔴"
                st.markdown(f"**{pos}**")
                st.markdown(f"Hands: {stats['hands']}")
                st.markdown(f"VPIP: {stats['vpip_pct']}%")
                st.markdown(f"PFR: {stats['pfr_pct']}%")
                st.markdown(f"{profit_color} ${stats['profit']:+.2f}")

    # Top hands analysis
    st.markdown("---")
    st.subheader("🏆 Top Performing Hands")

    # Flatten grid and sort by profit
    all_hands = []
    for row in grid_data:
        for cell in row:
            if cell['count'] > 0:
                all_hands.append(cell)

    # Sort by profit
    top_profitable = sorted(all_hands, key=lambda x: x['profit'], reverse=True)[:10]
    most_played = sorted(all_hands, key=lambda x: x['count'], reverse=True)[:10]

    top_col1, top_col2 = st.columns(2)

    with top_col1:
        st.markdown("**💰 Most Profitable**")
        for hand in top_profitable[:5]:
            color = "green" if hand['profit'] >= 0 else "red"
            st.markdown(
                f"**{hand['hand']}** - :{color}[${hand['profit']:+.2f}] "
                f"({hand['count']} hands, {hand['winrate']}% win)"
            )

    with top_col2:
        st.markdown("**📈 Most Played**")
        for hand in most_played[:5]:
            color = "green" if hand['profit'] >= 0 else "red"
            st.markdown(
                f"**{hand['hand']}** - {hand['count']} hands "
                f"(:{color}[${hand['profit']:+.2f}], {hand['winrate']}% win)"
            )

    # Worst hands
    st.markdown("---")
    st.subheader("⚠️ Leak Detection")

    worst_hands = sorted(all_hands, key=lambda x: x['profit'])[:5]
    if worst_hands and worst_hands[0]['profit'] < 0:
        st.markdown("**Hands losing the most money:**")
        for hand in worst_hands:
            if hand['profit'] < 0:
                st.markdown(
                    f"**{hand['hand']}** - :red[${hand['profit']:.2f}] "
                    f"({hand['count']} hands, {hand['winrate']}% win)"
                )
    else:
        st.success("No significant leaks detected! All hands are profitable or break-even.")


def render_analytics():
    """Analytics page."""
    sessions = load_sessions()
    hands = load_hands()
    render_analytics_page(sessions, hands)


def render_simulator():
    """Monte Carlo sim page."""
    st.title("🎲 Monte Carlo Simulator")
    st.markdown("*Risk of Ruin analysis using Monte Carlo simulation*")

    # Get current stats from sessions for defaults
    sessions = load_sessions()
    edge = get_edge_summary(sessions)

    # Default values from actual data or reasonable estimates
    default_winrate = edge.get('bb_per_100', 5.0) if edge.get('total_hands', 0) > 100 else 5.0
    default_bankroll = st.session_state.bankroll
    default_target = st.session_state.bankroll_target

    st.markdown("---")

    # Input Section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Simulation Parameters")

        current_br = st.number_input(
            "Current Bankroll ($)",
            min_value=1.0,
            value=float(default_bankroll),
            step=10.0,
            format="%.2f",
            help="Your current poker bankroll",
        )

        target_br = st.number_input(
            "Target Bankroll ($)",
            min_value=current_br + 1,
            value=float(max(default_target, current_br + 100)),
            step=50.0,
            format="%.2f",
            help="Goal bankroll (for probability calculation)",
        )

        winrate = st.number_input(
            "Win Rate (BB/100)",
            min_value=-20.0,
            max_value=50.0,
            value=float(default_winrate),
            step=0.5,
            format="%.1f",
            help="Your estimated win rate in big blinds per 100 hands",
        )

    with col2:
        st.subheader("⚙️ Advanced Settings")

        std_dev = st.number_input(
            "Standard Deviation (BB/100)",
            min_value=20.0,
            max_value=200.0,
            value=80.0,
            step=5.0,
            help="Typical range: 60-100 for NLHE. Higher = more variance.",
        )

        hands_to_sim = st.select_slider(
            "Hands to Simulate",
            options=[10000, 25000, 50000, 100000, 200000, 500000],
            value=50000,
            help="More hands = longer time horizon",
        )

        n_sims = st.select_slider(
            "Number of Simulations",
            options=[100, 500, 1000, 2500, 5000],
            value=1000,
            help="More sims = more accurate but slower",
        )

        big_blind = st.selectbox(
            "Big Blind Size ($)",
            options=[0.02, 0.05, 0.10, 0.25, 0.50, 1.00, 2.00, 5.00],
            index=2,  # Default to $0.10
            format_func=lambda x: f"${x:.2f}",
            help="The big blind at your stake",
        )

    # Run Simulation Button
    st.markdown("---")

    if st.button("🚀 Run Simulation", type="primary", use_container_width=True):
        with st.spinner("Running Monte Carlo simulation..."):
            try:
                result = simulate_bankroll(
                    current_br=current_br,
                    winrate_bb100=winrate,
                    std_dev_bb100=std_dev,
                    hands=hands_to_sim,
                    n_sims=n_sims,
                    target_br=target_br,
                    big_blind=big_blind,
                )

                # Store in session state for display
                st.session_state.sim_result = result
                st.session_state.sim_params = {
                    'current_br': current_br,
                    'target_br': target_br,
                    'winrate': winrate,
                    'std_dev': std_dev,
                    'hands': hands_to_sim,
                    'big_blind': big_blind,
                }

            except Exception as e:
                st.error(f"Simulation error: {str(e)}")

    # Display Results
    if hasattr(st.session_state, 'sim_result') and st.session_state.sim_result is not None:
        result = st.session_state.sim_result
        params = st.session_state.sim_params

        st.markdown("---")
        st.subheader("📈 Simulation Results")

        # Key Metrics Row
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            ror_color = "#E74C3C" if result.risk_of_ruin > 0.05 else "#27AE60"
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, {ror_color}, {ror_color}dd);
                padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{result.risk_of_ruin:.1%}</h2>
                <p style="color: #ffffffcc; margin: 5px 0 0 0;">Risk of Ruin</p>
                </div>""",
                unsafe_allow_html=True,
            )

        with m2:
            prob_color = "#27AE60" if result.prob_reach_target > 0.5 else "#F39C12"
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, {prob_color}, {prob_color}dd);
                padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{result.prob_reach_target:.1%}</h2>
                <p style="color: #ffffffcc; margin: 5px 0 0 0;">P(Reach Target)</p>
                </div>""",
                unsafe_allow_html=True,
            )

        with m3:
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, #3498DB, #2980B9);
                padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">${result.expected_final_br:,.0f}</h2>
                <p style="color: #ffffffcc; margin: 5px 0 0 0;">Expected Value</p>
                </div>""",
                unsafe_allow_html=True,
            )

        with m4:
            st.markdown(
                f"""<div style="background: linear-gradient(135deg, #9B59B6, #8E44AD);
                padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">${result.max_drawdown_median:,.0f}</h2>
                <p style="color: #ffffffcc; margin: 5px 0 0 0;">Median Max DD</p>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Fan Chart
        st.subheader("🎯 Bankroll Trajectories")

        # Get percentile data for confidence bands
        percentiles = get_percentile_trajectories(result)
        x_axis = np.linspace(0, params['hands'], result.trajectories.shape[1])

        # Create Plotly figure
        fig = go.Figure()

        # Add confidence bands (filled areas)
        # 5th-95th percentile band (lightest)
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_axis, x_axis[::-1]]),
            y=np.concatenate([percentiles['p95'], percentiles['p5'][::-1]]),
            fill='toself',
            fillcolor='rgba(52, 152, 219, 0.15)',
            line=dict(color='rgba(0,0,0,0)'),
            name='5th-95th Percentile',
            showlegend=True,
        ))

        # 25th-75th percentile band (darker)
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_axis, x_axis[::-1]]),
            y=np.concatenate([percentiles['p75'], percentiles['p25'][::-1]]),
            fill='toself',
            fillcolor='rgba(52, 152, 219, 0.3)',
            line=dict(color='rgba(0,0,0,0)'),
            name='25th-75th Percentile',
            showlegend=True,
        ))

        # Sample trajectories (thin lines)
        sample_trajectories = get_sample_trajectories(result, n_samples=50)
        for i, traj in enumerate(sample_trajectories):
            fig.add_trace(go.Scatter(
                x=x_axis,
                y=traj,
                mode='lines',
                line=dict(color='rgba(52, 152, 219, 0.2)', width=0.5),
                showlegend=False,
                hoverinfo='skip',
            ))

        # Median line (bold)
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=percentiles['p50'],
            mode='lines',
            line=dict(color='#2980B9', width=3),
            name='Median',
        ))

        # Starting bankroll line
        fig.add_hline(
            y=params['current_br'],
            line_dash="dash",
            line_color="#F39C12",
            annotation_text=f"Start: ${params['current_br']:,.0f}",
        )

        # Target line
        fig.add_hline(
            y=params['target_br'],
            line_dash="dash",
            line_color="#27AE60",
            annotation_text=f"Target: ${params['target_br']:,.0f}",
        )

        # Bust line
        fig.add_hline(
            y=0,
            line_dash="solid",
            line_color="#E74C3C",
            annotation_text="Bust",
        )

        fig.update_layout(
            title=f"Bankroll Evolution Over {params['hands']:,} Hands ({result.simulations_run:,} Simulations)",
            xaxis_title="Hands Played",
            yaxis_title="Bankroll ($)",
            template="plotly_dark",
            height=500,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
            ),
            hovermode='x unified',
        )

        st.plotly_chart(fig, use_container_width=True)

        # Distribution of Final Bankrolls
        st.subheader("📊 Final Bankroll Distribution")

        final_brs = result.trajectories[:, -1]

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=final_brs,
            nbinsx=50,
            marker_color='#3498DB',
            opacity=0.7,
            name='Final Bankroll',
        ))

        # Add vertical lines for key metrics
        fig_hist.add_vline(x=params['current_br'], line_dash="dash", line_color="#F39C12",
                          annotation_text="Start")
        fig_hist.add_vline(x=params['target_br'], line_dash="dash", line_color="#27AE60",
                          annotation_text="Target")
        fig_hist.add_vline(x=result.median_final_br, line_dash="solid", line_color="#9B59B6",
                          annotation_text="Median")

        fig_hist.update_layout(
            title="Distribution of Final Bankroll Values",
            xaxis_title="Final Bankroll ($)",
            yaxis_title="Frequency",
            template="plotly_dark",
            height=350,
            showlegend=False,
        )

        st.plotly_chart(fig_hist, use_container_width=True)

        # Detailed Statistics
        st.subheader("📋 Detailed Statistics")

        stat_col1, stat_col2, stat_col3 = st.columns(3)

        with stat_col1:
            st.markdown("**Percentile Outcomes**")
            st.markdown(f"- 5th percentile: ${result.percentile_5:,.2f}")
            st.markdown(f"- 25th percentile: ${result.percentile_25:,.2f}")
            st.markdown(f"- Median (50th): ${result.median_final_br:,.2f}")
            st.markdown(f"- 75th percentile: ${result.percentile_75:,.2f}")
            st.markdown(f"- 95th percentile: ${result.percentile_95:,.2f}")

        with stat_col2:
            st.markdown("**Risk Metrics**")
            st.markdown(f"- Risk of Ruin: {result.risk_of_ruin:.2%}")
            st.markdown(f"- P(Reach ${params['target_br']:,.0f}): {result.prob_reach_target:.2%}")
            st.markdown(f"- Median Max Drawdown: ${result.max_drawdown_median:,.2f}")
            st.markdown(f"- Expected Final BR: ${result.expected_final_br:,.2f}")

        with stat_col3:
            # Kelly criterion
            kelly = calculate_kelly_criterion(params['winrate'], params['std_dev'])
            time_est = estimate_time_to_target(
                params['current_br'],
                params['target_br'],
                params['winrate'],
                big_blind=params['big_blind'],
            )

            st.markdown("**Recommendations**")
            st.markdown(f"- Conservative buyins: {kelly['conservative_buyins']}")
            st.markdown(f"- Moderate buyins: {kelly['moderate_buyins']}")
            st.markdown(f"- Est. hours to target: {time_est['hours_needed']}")
            st.markdown(f"- Est. sessions: {time_est['sessions_needed']}")

        # Interpretation
        st.markdown("---")
        st.subheader("🎓 Interpretation")

        if result.risk_of_ruin < 0.01:
            st.success(
                f"**Excellent bankroll management!** With only {result.risk_of_ruin:.1%} risk of ruin, "
                f"your bankroll is well-protected. You have a {result.prob_reach_target:.0%} chance "
                f"of reaching your ${params['target_br']:,.0f} target."
            )
        elif result.risk_of_ruin < 0.05:
            st.info(
                f"**Solid bankroll position.** A {result.risk_of_ruin:.1%} risk of ruin is acceptable "
                f"for most players. Consider your {result.max_drawdown_median:,.0f} median max drawdown "
                f"when planning session stop-losses."
            )
        elif result.risk_of_ruin < 0.15:
            st.warning(
                f"**Elevated risk detected.** With {result.risk_of_ruin:.1%} risk of ruin, you may want "
                f"to consider moving down in stakes or adding to your bankroll. Your current setup "
                f"has significant downside risk."
            )
        else:
            st.error(
                f"**High risk of ruin ({result.risk_of_ruin:.1%})!** This bankroll is undersized for "
                f"your stakes and/or variance. Strongly recommend: (1) Move down in stakes, "
                f"(2) Add funds, or (3) Improve your win rate before continuing."
            )

    else:
        # No simulation run yet - show educational content
        st.markdown("---")
        st.info("👆 Configure parameters above and click **Run Simulation** to analyze your bankroll risk.")

        with st.expander("📚 What is Risk of Ruin?"):
            st.markdown("""
            **Risk of Ruin (RoR)** is the probability that you'll lose your entire bankroll before
            reaching your goal. It depends on:

            - **Bankroll size**: More buyins = lower RoR
            - **Win rate**: Higher winrate = lower RoR
            - **Variance**: Lower variance = lower RoR

            **General guidelines:**
            - < 1% RoR: Very conservative (50+ buyins)
            - 1-5% RoR: Reasonable risk (30-50 buyins)
            - 5-10% RoR: Aggressive (20-30 buyins)
            - > 10% RoR: High risk, consider moving down
            """)

        with st.expander("📊 Understanding the Fan Chart"):
            st.markdown("""
            The simulation creates thousands of possible futures for your bankroll:

            - **Median line** (dark): The "typical" outcome
            - **25th-75th band** (darker): 50% of outcomes fall here
            - **5th-95th band** (lighter): 90% of outcomes fall here
            - **Individual paths**: Show actual simulation trajectories

            A wider fan = more uncertainty. Paths that hit zero = bust scenarios.
            """)


def render_quant_lab():
    """Quant lab - GARCH, clustering, bayesian stuff."""
    import pandas as pd
    from analytics.volatility import VolatilityModel, render_volatility_chart
    from analytics.clustering import VillainCluster, render_cluster_chart
    from analytics.bayesian import WinrateEstimator, render_posterior_chart

    st.title("🔬 Quant Research Lab")
    st.markdown("*Advanced statistical analysis for edge quantification*")

    # Load data
    sessions = load_sessions()
    hands = load_hands()
    opponents = load_opponents()

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📈 Risk Modeling",
        "👥 Population Analysis",
        "🎯 Bayesian Validation",
    ])

    # =========================================================================
    # Tab 1: Risk Modeling (GARCH Volatility)
    # =========================================================================
    with tab1:
        st.subheader("Market Regime Detection (GARCH)")
        st.markdown("""
        Uses **GARCH(1,1)** to model conditional volatility of your session PnL.
        Identifies whether you're in a Low, Medium, or High volatility regime.
        """)

        # Prepare session PnL data
        completed_sessions = [s for s in sessions if s.get('profit') is not None]

        if len(completed_sessions) >= 10:
            # Create PnL series
            pnl_data = []
            for s in completed_sessions:
                date = s.get('date', '2024-01-01')
                profit = s.get('profit', 0)
                pnl_data.append({'date': date, 'pnl': profit})

            pnl_df = pd.DataFrame(pnl_data)
            pnl_df['date'] = pd.to_datetime(pnl_df['date'])
            pnl_df = pnl_df.sort_values('date')
            pnl_series = pd.Series(pnl_df['pnl'].values, index=pnl_df['date'])

            # Render chart and get model
            model = render_volatility_chart(pnl_series)

            if model:
                summary = model.get_summary()

                # Display metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    regime = summary['current_regime']
                    regime_colors = {'Low': '#27AE60', 'Medium': '#F39C12', 'High': '#E74C3C'}
                    st.markdown(
                        f"""<div style="text-align: center; padding: 20px;
                        background: {regime_colors.get(regime, '#95A5A6')};
                        border-radius: 10px;">
                        <div style="color: white; font-size: 2em; font-weight: bold;">
                        {regime}</div>
                        <div style="color: #ffffffcc;">Current Regime</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.metric(
                        "Current Volatility",
                        f"${summary['current_volatility']:.2f}",
                    )

                with col3:
                    st.metric(
                        "Vol Percentile",
                        f"{summary['volatility_percentile']:.0f}%",
                    )

                # Interpretation
                st.markdown("---")
                if regime == 'High':
                    st.warning("""
                    **High Volatility Regime**: Your recent sessions show elevated variance.
                    Consider tighter bankroll management and avoiding marginal spots.
                    """)
                elif regime == 'Low':
                    st.success("""
                    **Low Volatility Regime**: Your results are stable.
                    Good conditions for shot-taking at higher stakes if rolled.
                    """)
                else:
                    st.info("""
                    **Medium Volatility Regime**: Normal variance expected.
                    Continue standard bankroll management protocols.
                    """)
        else:
            st.info(f"Need at least 10 sessions for volatility modeling. Currently have {len(completed_sessions)}.")

            # Offer to generate synthetic data
            if st.button("Generate Demo Data", key="gen_vol_data"):
                from utils.synthetic_data import save_synthetic_data
                result = save_synthetic_data(n_sessions=50, n_opponents=25, n_hands=500)
                st.success(f"Generated {result['sessions']} sessions, {result['opponents']} opponents, {result['hands']} hands")
                st.rerun()

    # =========================================================================
    # Tab 2: Population Analysis (K-Means Clustering)
    # =========================================================================
    with tab2:
        st.subheader("Villain Taxonomy (Unsupervised Learning)")
        st.markdown("""
        Uses **PCA** for dimensionality reduction and **K-Means** clustering
        to automatically classify opponents into behavioral archetypes.
        """)

        # Prepare opponent stats
        if opponents and len(opponents) >= 4:
            # Build stats DataFrame
            stats_data = []
            for opp in opponents:
                stats = opp.get('stats', {})
                calc_stats = opp.get('calculated_stats', {})
                hands_played = stats.get('hands_played', 0)

                if hands_played >= 50:
                    # Calculate percentages if not pre-calculated
                    if calc_stats:
                        vpip = calc_stats.get('vpip', 0)
                        pfr = calc_stats.get('pfr', 0)
                        af = calc_stats.get('af', 0)
                        wtsd = calc_stats.get('wtsd', 25)
                    else:
                        vpip = (stats.get('vpip_count', 0) / hands_played * 100) if hands_played > 0 else 0
                        pfr = (stats.get('pfr_count', 0) / hands_played * 100) if hands_played > 0 else 0
                        af = pfr / (vpip - pfr) if vpip > pfr else 0
                        wtsd = 25  # Default

                    stats_data.append({
                        'name': opp.get('name', 'Unknown'),
                        'vpip': vpip,
                        'pfr': pfr,
                        'af': af,
                        'wtsd': wtsd,
                        'hands_played': hands_played,
                    })

            if len(stats_data) >= 4:
                player_stats_df = pd.DataFrame(stats_data)

                # Render cluster chart
                model = render_cluster_chart(player_stats_df)

                if model and model.cluster_stats is not None:
                    st.markdown("---")
                    st.markdown("### Cluster Centroids")

                    # Display cluster stats
                    display_df = model.cluster_stats[['archetype', 'count', 'vpip', 'pfr', 'af']].copy()
                    display_df.columns = ['Archetype', 'Players', 'Avg VPIP', 'Avg PFR', 'Avg AF']
                    display_df['Avg VPIP'] = display_df['Avg VPIP'].round(1)
                    display_df['Avg PFR'] = display_df['Avg PFR'].round(1)
                    display_df['Avg AF'] = display_df['Avg AF'].round(2)

                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Archetype legend
                    with st.expander("📖 Archetype Guide"):
                        from analytics.clustering import ARCHETYPES
                        for name, info in ARCHETYPES.items():
                            st.markdown(f"**{name}**: {info['description']}")
                            st.markdown(f"*Exploit*: {info['exploit']}")
                            st.markdown("---")
            else:
                st.info(f"Need at least 4 opponents with 50+ hands. Found {len(stats_data)} qualifying.")
        else:
            st.info(f"Need at least 4 opponents for clustering. Currently have {len(opponents)}.")

            if st.button("Generate Demo Opponents", key="gen_opp_data"):
                from utils.synthetic_data import save_synthetic_data
                result = save_synthetic_data(n_sessions=50, n_opponents=25, n_hands=500)
                st.success(f"Generated {result['opponents']} opponents with diverse profiles")
                st.rerun()

    # =========================================================================
    # Tab 3: Bayesian Validation (Bootstrap Winrate)
    # =========================================================================
    with tab3:
        st.subheader("True Winrate Estimation (Bootstrap)")
        st.markdown("""
        Uses **Bootstrap resampling** (10,000 iterations) to estimate the
        posterior distribution of your true winrate and calculate confidence intervals.
        """)

        # Get hand results in BB
        if hands and len(hands) >= 100:
            hand_results = [h.get('result', 0) for h in hands if h.get('result') is not None]

            if len(hand_results) >= 100:
                # Render posterior chart
                model = render_posterior_chart(hand_results)

                if model:
                    summary = model.get_summary()

                    # Display metrics
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        prob = summary['prob_profitable']
                        prob_color = '#27AE60' if prob >= 70 else '#E74C3C' if prob < 50 else '#F39C12'
                        st.markdown(
                            f"""<div style="text-align: center; padding: 20px;
                            background: {prob_color};
                            border-radius: 10px;">
                            <div style="color: white; font-size: 2em; font-weight: bold;">
                            {prob:.1f}%</div>
                            <div style="color: #ffffffcc;">P(Profitable)</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

                    with col2:
                        st.metric(
                            "95% CI Lower",
                            f"{summary['hdi_lower']:.2f} BB/100",
                        )

                    with col3:
                        st.metric(
                            "95% CI Upper",
                            f"{summary['hdi_upper']:.2f} BB/100",
                        )

                    # Interpretation
                    st.markdown("---")
                    interpretation = model.get_interpretation()
                    st.info(interpretation)

                    # Sample size guidance
                    with st.expander("📊 Sample Size Analysis"):
                        from analytics.bayesian import calculate_required_sample_size

                        current_n = summary['sample_size']
                        n_for_1bb = calculate_required_sample_size(target_precision=1.0)
                        n_for_2bb = calculate_required_sample_size(target_precision=2.0)

                        st.markdown(f"""
                        **Current Sample**: {current_n:,} hands

                        **Required for ±1 BB/100 precision**: {n_for_1bb:,} hands
                        **Required for ±2 BB/100 precision**: {n_for_2bb:,} hands

                        The more hands you play, the narrower your confidence interval becomes.
                        Professional players typically need 100k+ hands for reliable winrate estimates.
                        """)
            else:
                st.info(f"Need at least 100 hands with results. Found {len(hand_results)}.")
        else:
            st.info(f"Need at least 100 hands for Bayesian estimation. Currently have {len(hands)}.")

            if st.button("Generate Demo Hands", key="gen_hand_data"):
                from utils.synthetic_data import save_synthetic_data
                result = save_synthetic_data(n_sessions=50, n_opponents=25, n_hands=500)
                st.success(f"Generated {result['hands']} hands with realistic results")
                st.rerun()


def main():
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
    elif page == "Data Import":
        render_data_import()
    elif page == "My Ranges":
        render_my_ranges()
    elif page == "Simulator":
        render_simulator()
    elif page == "Quant Lab":
        render_quant_lab()


if __name__ == "__main__":
    main()
