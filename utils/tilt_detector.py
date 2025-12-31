"""
Tilt Detection Engine - Behavioral Finance Analysis.

Quantifies emotional control by detecting sub-optimal play patterns
after losses. Uses behavioral finance principles to identify tilt.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TiltAnalysis:
    """Results from tilt detection analysis."""
    tilt_score: float                # 0-10 scale
    tilt_level: str                  # 'none', 'mild', 'moderate', 'severe'
    downswing_detected: bool         # >10bb loss in 50 hands
    vpip_increase: float             # % increase after losses
    aggression_spike: bool           # Unusual aggression increase
    loss_chasing: bool               # Playing marginal hands after losses
    session_tilt_events: int         # Number of tilt episodes
    warning_message: str             # Human-readable warning
    recommendations: list[str]       # Tips to address tilt
    confidence: str                  # 'high', 'medium', 'low'

    def to_dict(self) -> dict:
        return {
            'tilt_score': self.tilt_score,
            'tilt_level': self.tilt_level,
            'downswing_detected': self.downswing_detected,
            'vpip_increase': self.vpip_increase,
            'aggression_spike': self.aggression_spike,
            'loss_chasing': self.loss_chasing,
            'session_tilt_events': self.session_tilt_events,
            'warning_message': self.warning_message,
            'recommendations': self.recommendations,
            'confidence': self.confidence,
        }


def detect_tilt(
    session_hands: list[dict],
    window_size: int = 50,
    downswing_threshold_bb: float = 10.0,
    vpip_increase_threshold: float = 10.0,
    big_blind: float = 0.10,
) -> TiltAnalysis:
    """
    Analyze a session's hands for tilt indicators.

    Tilt Detection Algorithm:
    1. Identify downswings (>10bb loss in rolling window)
    2. Check if VPIP increased >10% after downswing
    3. Look for aggression spikes post-loss
    4. Detect "revenge hands" (playing weak hands after losses)
    5. Calculate composite tilt score (0-10)

    Args:
        session_hands: List of hand dicts from session, chronologically ordered
        window_size: Rolling window for downswing detection (default 50 hands)
        downswing_threshold_bb: BB loss to trigger downswing (default 10)
        vpip_increase_threshold: VPIP increase % to flag tilt (default 10%)
        big_blind: Big blind size for BB calculation

    Returns:
        TiltAnalysis with score and recommendations
    """
    # Need minimum hands for analysis
    if len(session_hands) < 20:
        return TiltAnalysis(
            tilt_score=0.0,
            tilt_level='none',
            downswing_detected=False,
            vpip_increase=0.0,
            aggression_spike=False,
            loss_chasing=False,
            session_tilt_events=0,
            warning_message="Insufficient hands for tilt analysis",
            recommendations=["Play more hands to enable tilt detection"],
            confidence='low',
        )

    # Convert hands to analysis format
    hand_results = []
    for hand in session_hands:
        result_dollars = hand.get('result', 0)
        result_bb = result_dollars / big_blind if big_blind > 0 else 0

        # Determine if hand was VPIP (voluntarily put in pot)
        action = hand.get('action', '').lower()
        is_vpip = action not in ['fold', 'check', '']

        # Check for aggressive action
        is_aggressive = action in ['raise', '3-bet', '4-bet', 'all-in']

        # Check hand strength (simple heuristic based on hole cards)
        hole_cards = hand.get('hole_cards', [])
        hand_strength = _estimate_hand_strength(hole_cards)

        hand_results.append({
            'result_bb': result_bb,
            'is_vpip': is_vpip,
            'is_aggressive': is_aggressive,
            'hand_strength': hand_strength,
            'action': action,
        })

    # =========================================
    # Downswing Detection
    # =========================================
    downswings = []
    for i in range(len(hand_results) - window_size + 1):
        window = hand_results[i:i + window_size]
        window_result = sum(h['result_bb'] for h in window)

        if window_result <= -downswing_threshold_bb:
            downswings.append({
                'start_idx': i,
                'end_idx': i + window_size,
                'loss_bb': window_result,
            })

    downswing_detected = len(downswings) > 0

    # =========================================
    # VPIP Change Analysis
    # =========================================
    vpip_before_losses = 0.0
    vpip_after_losses = 0.0
    vpip_increase = 0.0

    if downswings:
        # Calculate VPIP before and after first major downswing
        first_downswing = downswings[0]
        ds_start = first_downswing['start_idx']
        ds_end = first_downswing['end_idx']

        # Before downswing (up to 50 hands before)
        before_start = max(0, ds_start - window_size)
        before_hands = hand_results[before_start:ds_start]
        if before_hands:
            vpip_before_losses = (
                sum(1 for h in before_hands if h['is_vpip']) / len(before_hands) * 100
            )

        # After downswing (next 30 hands)
        after_end = min(len(hand_results), ds_end + 30)
        after_hands = hand_results[ds_end:after_end]
        if after_hands:
            vpip_after_losses = (
                sum(1 for h in after_hands if h['is_vpip']) / len(after_hands) * 100
            )

        vpip_increase = vpip_after_losses - vpip_before_losses

    # =========================================
    # Aggression Spike Detection
    # =========================================
    aggression_spike = False
    if downswings:
        first_downswing = downswings[0]
        ds_end = first_downswing['end_idx']

        # Check aggression in 20 hands after downswing
        after_end = min(len(hand_results), ds_end + 20)
        after_hands = hand_results[ds_end:after_end]

        # Compare to session average
        session_aggression = (
            sum(1 for h in hand_results if h['is_aggressive']) / len(hand_results)
            if hand_results else 0
        )
        post_loss_aggression = (
            sum(1 for h in after_hands if h['is_aggressive']) / len(after_hands)
            if after_hands else 0
        )

        # Spike = 50% increase in aggression
        if session_aggression > 0 and post_loss_aggression > session_aggression * 1.5:
            aggression_spike = True

    # =========================================
    # Loss Chasing Detection
    # =========================================
    loss_chasing = False
    loss_chase_count = 0

    # Look for pattern: loss followed by VPIP with weak hand
    for i in range(1, len(hand_results)):
        prev_hand = hand_results[i - 1]
        curr_hand = hand_results[i]

        # If previous hand was a loss
        if prev_hand['result_bb'] < -2:  # Significant loss (>2bb)
            # And current hand is VPIP with weak cards
            if curr_hand['is_vpip'] and curr_hand['hand_strength'] < 0.3:
                loss_chase_count += 1

    # More than 20% of post-loss hands are chasing
    loss_hands = sum(1 for i, h in enumerate(hand_results[1:])
                     if hand_results[i]['result_bb'] < -2)
    if loss_hands > 0 and loss_chase_count / max(loss_hands, 1) > 0.2:
        loss_chasing = True

    # =========================================
    # Calculate Composite Tilt Score
    # =========================================
    tilt_score = 0.0

    # Downswing component (0-3 points)
    if downswing_detected:
        tilt_score += min(3.0, len(downswings) * 1.5)

    # VPIP increase component (0-3 points)
    if vpip_increase > 0:
        tilt_score += min(3.0, vpip_increase / 10 * 1.5)

    # Aggression spike (0-2 points)
    if aggression_spike:
        tilt_score += 2.0

    # Loss chasing (0-2 points)
    if loss_chasing:
        tilt_score += 2.0

    # Cap at 10
    tilt_score = min(10.0, round(tilt_score, 1))

    # =========================================
    # Determine Tilt Level and Recommendations
    # =========================================
    if tilt_score <= 2:
        tilt_level = 'none'
        warning_message = "No significant tilt detected. Playing solid!"
        recommendations = [
            "Continue with your current approach",
            "Stay focused on making +EV decisions",
        ]
    elif tilt_score <= 4:
        tilt_level = 'mild'
        warning_message = "Mild tilt indicators. Stay aware of your emotions."
        recommendations = [
            "Take a 5-minute break if you feel frustrated",
            "Review your session goals",
            "Focus on process over results",
        ]
    elif tilt_score <= 7:
        tilt_level = 'moderate'
        warning_message = "⚠️ Moderate tilt detected! Consider taking a break."
        recommendations = [
            "Take a 15-30 minute break immediately",
            "Do breathing exercises or take a walk",
            "Set a stop-loss for the remaining session",
            "Consider ending the session if losses continue",
        ]
    else:
        tilt_level = 'severe'
        warning_message = "🚨 SEVERE TILT DETECTED! Stop playing now!"
        recommendations = [
            "END THE SESSION IMMEDIATELY",
            "Walk away from the computer",
            "Review this session with fresh eyes tomorrow",
            "Consider if you're properly rolled for this stake",
            "Practice bankroll management",
        ]

    # Confidence based on sample size
    if len(session_hands) > 100:
        confidence = 'high'
    elif len(session_hands) > 50:
        confidence = 'medium'
    else:
        confidence = 'low'

    return TiltAnalysis(
        tilt_score=tilt_score,
        tilt_level=tilt_level,
        downswing_detected=downswing_detected,
        vpip_increase=round(vpip_increase, 1),
        aggression_spike=aggression_spike,
        loss_chasing=loss_chasing,
        session_tilt_events=len(downswings),
        warning_message=warning_message,
        recommendations=recommendations,
        confidence=confidence,
    )


def _estimate_hand_strength(hole_cards: list) -> float:
    """
    Estimate preflop hand strength on 0-1 scale.

    Simple heuristic based on card ranks and suitedness.

    Args:
        hole_cards: List of (rank, suit) tuples

    Returns:
        Float from 0.0 (weakest) to 1.0 (strongest)
    """
    if len(hole_cards) != 2:
        return 0.5  # Unknown

    rank_values = {
        'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
        '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2,
    }

    r1, s1 = hole_cards[0]
    r2, s2 = hole_cards[1]

    v1 = rank_values.get(r1, 5)
    v2 = rank_values.get(r2, 5)

    # Base strength from high card
    high = max(v1, v2)
    low = min(v1, v2)

    strength = (high + low) / 28  # Normalize to ~0-1

    # Pairs are stronger
    if v1 == v2:
        strength += 0.25

    # Suited bonus
    if s1 == s2:
        strength += 0.05

    # Connectedness bonus
    gap = abs(v1 - v2)
    if gap <= 2:
        strength += 0.03

    # Premium hands boost
    if v1 >= 12 and v2 >= 12:  # Both broadway
        strength += 0.1

    return min(1.0, max(0.0, strength))


def get_session_tilt_summary(sessions: list[dict], hands: list[dict]) -> list[dict]:
    """
    Calculate tilt scores for multiple sessions.

    Args:
        sessions: List of session dicts
        hands: List of all hands

    Returns:
        List of dicts with session_id and tilt analysis
    """
    summaries = []

    for session in sessions:
        session_id = session.get('id')
        session_hands = [h for h in hands if h.get('session_id') == session_id]

        if len(session_hands) >= 20:
            analysis = detect_tilt(session_hands)
            summaries.append({
                'session_id': session_id,
                'date': session.get('date'),
                'location': session.get('location'),
                'tilt_score': analysis.tilt_score,
                'tilt_level': analysis.tilt_level,
                'warning': analysis.warning_message,
                'hands_analyzed': len(session_hands),
            })

    return sorted(summaries, key=lambda x: x.get('tilt_score', 0), reverse=True)


def get_tilt_color(score: float) -> str:
    """Get color for tilt score visualization."""
    if score <= 2:
        return '#27AE60'  # Green
    elif score <= 4:
        return '#F1C40F'  # Yellow
    elif score <= 7:
        return '#E67E22'  # Orange
    else:
        return '#E74C3C'  # Red


def get_tilt_emoji(level: str) -> str:
    """Get emoji for tilt level."""
    return {
        'none': '😎',
        'mild': '😐',
        'moderate': '😤',
        'severe': '🤬',
    }.get(level, '❓')
