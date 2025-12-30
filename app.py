"""
Quant Poker Edge - Main Application Entry Point
A professional-grade poker analytics platform.
"""

import streamlit as st
import pandas as pd
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
    update_opponent_stats,
    calculate_opponent_stats,
)
from utils.analytics_engine import get_edge_summary, analyze_opponent_tendencies
from components import (
    render_session_form,
    render_start_session_form,
    render_end_session_form,
    render_card_selector,
    render_board_cards,
    render_analytics_page,
    parse_multi_cards,
)


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
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None


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
        st.caption("v0.4.0 | Phase 2: The Quant Layer")

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

    # My Edge Card
    hands = load_hands()
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


def render_log_session() -> None:
    """Render the session logging page with start/end/log modes."""
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


def render_hand_logger() -> None:
    """Render the hand logger page with card selector and session linking."""
    st.header("🃏 Hand Logger")

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
        # Show active session info
        st.success(
            f"📍 **Active Session:** {active_session.get('location')} - "
            f"${active_session.get('stake')} | Buy-in: ${active_session.get('buy_in', 0):,}"
        )

    # Quick entry for both cards at once
    st.markdown("**Quick Entry** *(type both cards: `As Kh` or `As, Kh` or `AsKh`)*")
    quick_both = st.text_input(
        "⌨️ Enter both hole cards",
        key="quick_both_cards",
        placeholder="As Kh, As,Kh, or AsKh...",
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

    # Show logged hands for this session
    if active_session:
        hands = load_hands(active_session.get("id"))
        if hands:
            st.markdown("---")
            st.subheader(f"📋 Hands This Session ({len(hands)})")
            for hand in reversed(hands[-5:]):  # Show last 5
                cards = hand.get("hole_cards", [])
                card_str = f"{cards[0][0]}{cards[0][1]} {cards[1][0]}{cards[1][1]}" if len(cards) == 2 else "?"
                result = hand.get("result", 0)
                color = "green" if result >= 0 else "red"
                villain = hand.get("opponent_name", "")
                villain_str = f" vs **{villain}**" if villain else ""
                st.markdown(
                    f"**{card_str}** | {hand.get('position')} | {hand.get('action')} | "
                    f":{color}[${result:+}]{villain_str}"
                )


def render_analytics() -> None:
    """Render the analytics page with charts and metrics."""
    sessions = load_sessions()
    hands = load_hands()
    render_analytics_page(sessions, hands)


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
