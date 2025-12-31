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
    get_opponent,
    update_opponent_stats,
    calculate_opponent_stats,
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
    if "bankroll" not in st.session_state:
        st.session_state.bankroll = 350  # Current bankroll
    if "bankroll_target" not in st.session_state:
        st.session_state.bankroll_target = 500  # Target for next stake


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
            options=["Dashboard", "Log Session", "Hand Logger", "Data Import", "My Ranges", "Analytics"],
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
            f'<span style="color: {progress_color}; font-weight: bold;">${bankroll:,.0f}</span>'
            f' / ${target:,.0f} to Next Stake</div>',
            unsafe_allow_html=True,
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
            st.markdown("**Bankroll Settings**")
            new_bankroll = st.number_input(
                "Current Bankroll ($)",
                value=st.session_state.bankroll,
                min_value=0,
                step=50,
                key="bankroll_input",
            )
            new_target = st.number_input(
                "Target for Next Stake ($)",
                value=st.session_state.bankroll_target,
                min_value=100,
                step=100,
                key="target_input",
            )
            if new_bankroll != st.session_state.bankroll or new_target != st.session_state.bankroll_target:
                st.session_state.bankroll = new_bankroll
                st.session_state.bankroll_target = new_target

        st.markdown("---")

        # AI Coach Settings
        render_api_key_input()

        st.caption("v0.6.0 | Phase 4: Polish")

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

        # Get opponent data if available
        opponent_data = None
        if opponent_id:
            opponent_data = get_opponent(opponent_id)

        with st.spinner("🤖 Analyzing hand..."):
            result = analyze_hand(hand_to_analyze, session_for_analysis, opponent_data)
            render_analysis_result(result)

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

            for idx, hand in enumerate(reversed(hands[-5:])):  # Show last 5
                cards = hand.get("hole_cards", [])
                card_str = f"{cards[0][0]}{cards[0][1]} {cards[1][0]}{cards[1][1]}" if len(cards) == 2 else "?"
                result = hand.get("result", 0)
                color = "green" if result >= 0 else "red"
                villain = hand.get("opponent_name", "")
                villain_str = f" vs **{villain}**" if villain else ""

                # Create columns for hand info and coach button
                hand_col, coach_col = st.columns([5, 1])

                with hand_col:
                    st.markdown(
                        f"**{card_str}** | {hand.get('position')} | {hand.get('action')} | "
                        f":{color}[${result:+}]{villain_str}"
                    )

                with coach_col:
                    if has_api_key:
                        if st.button("🤖", key=f"coach_hand_{idx}", help="Ask AI Coach"):
                            st.session_state["analyze_hand"] = hand
                            st.session_state["analyze_session"] = active_session
                            st.session_state["analyze_opponent_id"] = hand.get("opponent_id")
                            st.rerun()


def render_data_import() -> None:
    """Render the data import page for Ignition hand histories."""
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


def render_my_ranges() -> None:
    """Render the range chart visualization page."""
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
    elif page == "Data Import":
        render_data_import()
    elif page == "My Ranges":
        render_my_ranges()


if __name__ == "__main__":
    main()
