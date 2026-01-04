"""
Fund Tearsheet - PDF Performance Report Generator.

Generates professional PDF reports with session history,
key metrics, and playstyle analysis for portfolio presentation.
"""

from fpdf import FPDF
from datetime import datetime
from typing import Optional
import io


class PokerTearsheet(FPDF):
    """Custom PDF class for poker performance reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add header to each page."""
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "AI Poker Coach - Performance Tearsheet", align="C", ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", ln=True)
        self.ln(5)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        """Add a section title."""
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(44, 62, 80)  # Dark blue
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f"  {title}", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def metric_row(self, label: str, value: str, highlight: bool = False):
        """Add a metric row."""
        self.set_font("Helvetica", "", 11)
        if highlight:
            self.set_fill_color(236, 240, 241)
            self.cell(80, 8, label, fill=True)
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 8, value, fill=True, ln=True)
        else:
            self.cell(80, 8, label)
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 8, value, ln=True)


def calculate_report_metrics(sessions: list[dict], hands: list[dict]) -> dict:
    """
    Calculate all metrics needed for the report.

    Args:
        sessions: List of session dictionaries
        hands: List of hand dictionaries

    Returns:
        Dictionary with calculated metrics
    """
    completed = [s for s in sessions if s.get("profit") is not None]

    if not completed:
        return {
            "total_profit": 0,
            "total_sessions": 0,
            "total_hours": 0,
            "hourly_rate": 0,
            "win_rate": 0,
            "avg_session": 0,
            "best_session": 0,
            "worst_session": 0,
            "total_hands": len(hands),
            "winning_sessions": 0,
            "losing_sessions": 0,
        }

    profits = [s.get("profit", 0) for s in completed]
    hours = [s.get("duration_hours", 0) for s in completed]

    total_profit = sum(profits)
    total_hours = sum(hours)
    winning = sum(1 for p in profits if p > 0)
    losing = sum(1 for p in profits if p < 0)

    return {
        "total_profit": total_profit,
        "total_sessions": len(completed),
        "total_hours": total_hours,
        "hourly_rate": total_profit / total_hours if total_hours > 0 else 0,
        "win_rate": (winning / len(completed) * 100) if completed else 0,
        "avg_session": total_profit / len(completed) if completed else 0,
        "best_session": max(profits) if profits else 0,
        "worst_session": min(profits) if profits else 0,
        "total_hands": len(hands),
        "winning_sessions": winning,
        "losing_sessions": losing,
    }


def calculate_playstyle_stats(hands: list[dict]) -> dict:
    """
    Calculate playstyle stats for the report.

    Args:
        hands: List of hand dictionaries

    Returns:
        Dictionary with VPIP, PFR, 3Bet, Agg, WTSD
    """
    if not hands:
        return {"VPIP": 0, "PFR": 0, "3Bet": 0, "Agg": 0, "WTSD": 0}

    total = len(hands)
    vpip_count = 0
    pfr_count = 0
    three_bet_count = 0
    bets_raises = 0
    calls = 0
    showdowns = 0

    for hand in hands:
        action = hand.get("action", "").lower()

        if action not in ["fold", "check", ""]:
            vpip_count += 1

        if action in ["raise", "open", "3-bet", "4-bet", "all-in"]:
            pfr_count += 1

        if action == "3-bet":
            three_bet_count += 1

        if action in ["raise", "bet", "3-bet", "4-bet", "open"]:
            bets_raises += 1
        elif action == "call":
            calls += 1

        board = hand.get("board") or {}
        if board.get("river") and hand.get("result", 0) != 0:
            showdowns += 1

    vpip = (vpip_count / total * 100) if total > 0 else 0
    pfr = (pfr_count / total * 100) if total > 0 else 0
    three_bet = (three_bet_count / total * 100) if total > 0 else 0
    agg = (bets_raises / calls) if calls > 0 else bets_raises if bets_raises > 0 else 0
    wtsd = (showdowns / vpip_count * 100) if vpip_count > 0 else 0

    return {
        "VPIP": round(vpip, 1),
        "PFR": round(pfr, 1),
        "3Bet": round(three_bet, 1),
        "Agg": round(agg, 2),
        "WTSD": round(wtsd, 1),
    }


# GTO Baseline for comparison
GTO_BASELINE = {
    "VPIP": 24.0,
    "PFR": 19.0,
    "3Bet": 9.0,
    "Agg": 3.0,
    "WTSD": 27.0,
}


def generate_tearsheet(
    sessions: list[dict],
    hands: list[dict],
    player_name: str = "Hero",
) -> bytes:
    """
    Generate a PDF performance tearsheet.

    Args:
        sessions: List of session dictionaries
        hands: List of hand dictionaries
        player_name: Name to display on report

    Returns:
        PDF content as bytes
    """
    pdf = PokerTearsheet()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Calculate metrics
    metrics = calculate_report_metrics(sessions, hands)
    stats = calculate_playstyle_stats(hands)

    # Executive Summary
    pdf.section_title("Executive Summary")
    pdf.set_font("Helvetica", "", 11)

    profit_str = f"${metrics['total_profit']:+,.0f}"
    if metrics["total_profit"] >= 0:
        summary = f"{player_name} has generated {profit_str} in profit across {metrics['total_sessions']} sessions."
    else:
        summary = f"{player_name} is down {profit_str} across {metrics['total_sessions']} sessions."

    pdf.multi_cell(0, 6, summary)
    pdf.ln(5)

    # Key Performance Metrics
    pdf.section_title("Key Performance Metrics")

    pdf.metric_row("Total Profit/Loss", f"${metrics['total_profit']:+,.0f}", highlight=True)
    pdf.metric_row("Total Sessions", str(metrics["total_sessions"]))
    pdf.metric_row("Total Hours Played", f"{metrics['total_hours']:.1f}")
    pdf.metric_row("Hourly Win Rate", f"${metrics['hourly_rate']:+,.2f}/hr", highlight=True)
    pdf.metric_row("Session Win Rate", f"{metrics['win_rate']:.1f}%")
    pdf.metric_row("Average Session P/L", f"${metrics['avg_session']:+,.0f}")
    pdf.metric_row("Best Session", f"${metrics['best_session']:+,.0f}")
    pdf.metric_row("Worst Session", f"${metrics['worst_session']:+,.0f}")
    pdf.metric_row("Winning Sessions", str(metrics["winning_sessions"]))
    pdf.metric_row("Losing Sessions", str(metrics["losing_sessions"]))
    pdf.metric_row("Total Hands Logged", str(metrics["total_hands"]))
    pdf.ln(5)

    # Playstyle Analysis
    pdf.section_title("Playstyle Analysis (vs GTO Baseline)")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 8, "Stat", border=1)
    pdf.cell(40, 8, "Your Value", border=1, align="C")
    pdf.cell(40, 8, "GTO Baseline", border=1, align="C")
    pdf.cell(50, 8, "Deviation", border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    stat_labels = {
        "VPIP": "VPIP (Voluntarily Put $)",
        "PFR": "PFR (Pre-Flop Raise)",
        "3Bet": "3-Bet Frequency",
        "Agg": "Aggression Factor",
        "WTSD": "Went To Showdown %",
    }

    for stat, label in stat_labels.items():
        hero_val = stats.get(stat, 0)
        gto_val = GTO_BASELINE.get(stat, 0)
        diff = hero_val - gto_val

        # Format values
        if stat == "Agg":
            hero_str = f"{hero_val:.2f}"
            gto_str = f"{gto_val:.2f}"
            diff_str = f"{diff:+.2f}"
        else:
            hero_str = f"{hero_val:.1f}%"
            gto_str = f"{gto_val:.1f}%"
            diff_str = f"{diff:+.1f}%"

        pdf.cell(50, 7, label, border=1)
        pdf.cell(40, 7, hero_str, border=1, align="C")
        pdf.cell(40, 7, gto_str, border=1, align="C")
        pdf.cell(50, 7, diff_str, border=1, align="C")
        pdf.ln()

    pdf.ln(5)

    # Session History
    if sessions:
        pdf.section_title("Recent Session History")

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 7, "Date", border=1)
        pdf.cell(25, 7, "Stakes", border=1, align="C")
        pdf.cell(20, 7, "Hours", border=1, align="C")
        pdf.cell(25, 7, "Buy-In", border=1, align="C")
        pdf.cell(25, 7, "Cash-Out", border=1, align="C")
        pdf.cell(25, 7, "Profit", border=1, align="C")
        pdf.cell(30, 7, "$/hr", border=1, align="C")
        pdf.ln()

        # Sort sessions by date (most recent first)
        sorted_sessions = sorted(
            [s for s in sessions if s.get("profit") is not None],
            key=lambda x: x.get("date", ""),
            reverse=True,
        )[:15]  # Last 15 sessions

        pdf.set_font("Helvetica", "", 9)
        for session in sorted_sessions:
            date = session.get("date", "N/A")[:10]
            stakes = session.get("stakes", "N/A")
            hours = session.get("duration_hours", 0)
            buy_in = session.get("buy_in", 0)
            cash_out = session.get("cash_out", 0)
            profit = session.get("profit", 0)
            hourly = profit / hours if hours > 0 else 0

            pdf.cell(30, 6, date, border=1)
            pdf.cell(25, 6, str(stakes), border=1, align="C")
            pdf.cell(20, 6, f"{hours:.1f}", border=1, align="C")
            pdf.cell(25, 6, f"${buy_in:,.0f}", border=1, align="C")
            pdf.cell(25, 6, f"${cash_out:,.0f}", border=1, align="C")
            pdf.cell(25, 6, f"${profit:+,.0f}", border=1, align="C")
            pdf.cell(30, 6, f"${hourly:+,.0f}", border=1, align="C")
            pdf.ln()

    # Disclaimer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(
        0,
        4,
        "This report is generated by AI Poker Coach for analytical purposes only. "
        "Past performance does not guarantee future results. Sample sizes under 1000 hands "
        "may not be statistically significant.",
    )

    # Output PDF to bytes
    return pdf.output()


def render_download_button(sessions: list[dict], hands: list[dict]) -> None:
    """
    Render a Streamlit download button for the PDF report.

    Args:
        sessions: List of session dictionaries
        hands: List of hand dictionaries
    """
    import streamlit as st

    if st.button("Generate Performance Report", type="primary"):
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_tearsheet(sessions, hands)

            st.download_button(
                label="Download PDF Tearsheet",
                data=pdf_bytes,
                file_name=f"poker_tearsheet_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
