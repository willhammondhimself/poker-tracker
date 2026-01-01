"""Winrate CI and sample size calculations."""

import math
from typing import Optional


def calculate_winrate_ci(
    total_bb_won: float,
    hands_played: int,
    variance: float = 68.0,
    confidence: float = 0.95,
) -> dict:
    """95% CI for winrate. Uses ~68 BB^2 variance for 6max NLHE."""
    # Minimum hand threshold
    if hands_played < 10:
        return {
            'winrate': 0.0,
            'ci_lower': 0.0,
            'ci_upper': 0.0,
            'margin_of_error': 0.0,
            'std_error': 0.0,
            'interpretation': "Insufficient data. Need at least 10 hands.",
            'sample_adequacy': "insufficient",
            'hands_played': hands_played,
            'confidence_level': confidence,
        }

    # Calculate observed winrate (BB/100)
    winrate = (total_bb_won / hands_played) * 100

    # Z-score for confidence level
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    # Standard error calculation
    # SE = sqrt(variance / hands) * 100 to convert to BB/100 scale
    std_error = math.sqrt(variance / hands_played) * 100

    # Confidence interval bounds
    margin_of_error = z * std_error
    ci_lower = winrate - margin_of_error
    ci_upper = winrate + margin_of_error

    # Generate interpretation
    interpretation = _generate_interpretation(
        winrate, ci_lower, ci_upper, hands_played
    )

    # Sample adequacy assessment
    sample_adequacy = _assess_sample_size(hands_played)

    return {
        'winrate': round(winrate, 2),
        'ci_lower': round(ci_lower, 2),
        'ci_upper': round(ci_upper, 2),
        'margin_of_error': round(margin_of_error, 2),
        'std_error': round(std_error, 2),
        'interpretation': interpretation,
        'sample_adequacy': sample_adequacy,
        'hands_played': hands_played,
        'confidence_level': confidence,
    }


def _generate_interpretation(
    winrate: float,
    ci_lower: float,
    ci_upper: float,
    hands: int,
) -> str:
    """Generate human-readable interpretation of CI results."""

    # Check if CI includes zero (breakeven)
    if ci_lower <= 0 <= ci_upper:
        if winrate > 2:
            return (
                f"Your observed winrate of {winrate:+.1f} BB/100 is positive, "
                f"but with {hands:,} hands, we cannot rule out variance. "
                f"Need more hands for statistical significance."
            )
        elif winrate < -2:
            return (
                f"Your observed winrate of {winrate:.1f} BB/100 is negative, "
                f"but variance could explain these results. "
                f"The confidence interval includes breakeven."
            )
        else:
            return (
                f"Results are close to breakeven ({winrate:+.1f} BB/100). "
                f"With {hands:,} hands, no clear edge is detectable yet."
            )

    elif ci_lower > 0:
        # Statistically significant winner
        if ci_lower > 5:
            return (
                f"Strong winning player! Your true winrate is likely "
                f"between {ci_lower:+.1f} and {ci_upper:+.1f} BB/100. "
                f"This is statistically significant over {hands:,} hands."
            )
        else:
            return (
                f"Statistically significant winner. True winrate likely "
                f"between {ci_lower:+.1f} and {ci_upper:+.1f} BB/100. "
                f"Based on {hands:,} hands."
            )

    else:
        # Statistically significant loser (ci_upper < 0)
        return (
            f"Results indicate a losing winrate. "
            f"True winrate likely between {ci_lower:.1f} and {ci_upper:.1f} BB/100. "
            f"Consider reviewing strategy or moving down in stakes."
        )


def _assess_sample_size(hands: int) -> str:
    """Assess sample size adequacy for statistical confidence."""
    if hands < 5000:
        return "insufficient"
    elif hands < 10000:
        return "marginal"
    elif hands < 50000:
        return "adequate"
    elif hands < 100000:
        return "good"
    else:
        return "excellent"


def get_sample_size_message(adequacy: str) -> str:
    """Get human-readable message for sample size adequacy."""
    messages = {
        "insufficient": "Need 5,000+ hands for meaningful confidence intervals.",
        "marginal": "Sample size is marginal. 10,000+ hands recommended.",
        "adequate": "Sample size is adequate for basic statistical confidence.",
        "good": "Good sample size. Results are becoming reliable.",
        "excellent": "Excellent sample size. High statistical confidence.",
    }
    return messages.get(adequacy, "Unknown sample size status.")


def hands_needed_for_confidence(
    target_margin: float = 5.0,
    variance: float = 68.0,
    confidence: float = 0.95,
) -> int:
    """How many hands for +/- target_margin BB/100."""
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    # Solve for n: target_margin = z * sqrt(variance / n) * 100
    # n = (z * 100)^2 * variance / target_margin^2
    hands_needed = ((z * 100) ** 2 * variance) / (target_margin ** 2)

    return int(math.ceil(hands_needed))


def calculate_hourly_rate_ci(
    total_profit: float,
    hours_played: float,
    session_profits: list[float],
    confidence: float = 0.95,
) -> Optional[dict]:
    """CI for $/hr based on session-level variance."""
    if hours_played < 1 or len(session_profits) < 3:
        return None

    # Calculate observed hourly rate
    hourly_rate = total_profit / hours_played

    # Calculate standard deviation of session profits
    mean_profit = sum(session_profits) / len(session_profits)
    variance = sum((p - mean_profit) ** 2 for p in session_profits) / len(session_profits)
    std_dev = math.sqrt(variance)

    # Standard error of mean session profit
    n_sessions = len(session_profits)
    std_error = std_dev / math.sqrt(n_sessions)

    # Z-score for confidence level
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    # Margin of error for session profit
    margin = z * std_error

    # Convert to hourly (approximate)
    avg_hours_per_session = hours_played / n_sessions
    hourly_margin = margin / avg_hours_per_session if avg_hours_per_session > 0 else 0

    return {
        'hourly_rate': round(hourly_rate, 2),
        'ci_lower': round(hourly_rate - hourly_margin, 2),
        'ci_upper': round(hourly_rate + hourly_margin, 2),
        'margin_of_error': round(hourly_margin, 2),
        'sessions': n_sessions,
        'hours': round(hours_played, 1),
    }
