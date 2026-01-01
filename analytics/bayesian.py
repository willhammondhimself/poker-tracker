"""
The Truth Seeker - Bayesian Winrate Estimation.

Uses Bootstrap resampling to estimate the posterior distribution
of true winrate and calculate probability of long-term profitability.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from typing import Optional
from scipy import stats


class WinrateEstimator:
    """
    Bootstrap-based winrate estimation.

    Performs bootstrap resampling to generate a posterior distribution
    of the true winrate (BB/100) and calculates confidence intervals.
    """

    def __init__(
        self,
        hand_results: list[float],
        n_bootstrap: int = 10000,
        confidence: float = 0.95,
    ):
        """
        Initialize the winrate estimator.

        Args:
            hand_results: List of hand-level PnL in BB.
            n_bootstrap: Number of bootstrap iterations.
            confidence: Confidence level for HDI (default 0.95).
        """
        self.hand_results = np.array(hand_results)
        self.n_bootstrap = n_bootstrap
        self.confidence = confidence

        self.point_estimate = None
        self.hdi_lower = None
        self.hdi_upper = None
        self.prob_profitable = None
        self.samples = None

        if len(self.hand_results) >= 100:
            self._run_bootstrap()

    def _run_bootstrap(self) -> None:
        """Run bootstrap resampling to estimate winrate distribution."""
        n_hands = len(self.hand_results)

        # Calculate observed winrate (BB/100)
        self.point_estimate = np.mean(self.hand_results) * 100

        # Bootstrap resampling
        bootstrap_winrates = []

        for _ in range(self.n_bootstrap):
            # Sample with replacement
            sample = np.random.choice(self.hand_results, size=n_hands, replace=True)
            # Calculate BB/100 for this sample
            winrate = np.mean(sample) * 100
            bootstrap_winrates.append(winrate)

        self.samples = np.array(bootstrap_winrates)

        # Calculate HDI (High Density Interval)
        alpha = 1 - self.confidence
        self.hdi_lower = np.percentile(self.samples, alpha / 2 * 100)
        self.hdi_upper = np.percentile(self.samples, (1 - alpha / 2) * 100)

        # Calculate probability of profitability
        self.prob_profitable = np.mean(self.samples > 0)

    def get_summary(self) -> dict:
        """
        Get summary statistics.

        Returns:
            Dictionary with estimation metrics.
        """
        if self.samples is None:
            return {
                'point_estimate': 0,
                'hdi_lower': 0,
                'hdi_upper': 0,
                'prob_profitable': 0,
                'sample_size': len(self.hand_results),
                'status': 'Insufficient data (need 100+ hands)',
            }

        return {
            'point_estimate': round(self.point_estimate, 2),
            'hdi_lower': round(self.hdi_lower, 2),
            'hdi_upper': round(self.hdi_upper, 2),
            'prob_profitable': round(self.prob_profitable * 100, 1),
            'sample_size': len(self.hand_results),
            'status': 'Complete',
        }

    def get_interpretation(self) -> str:
        """
        Get human-readable interpretation.

        Returns:
            Interpretation string.
        """
        if self.samples is None:
            return "Need at least 100 hands for reliable estimation."

        # Determine confidence level
        if self.hdi_lower > 0:
            confidence = "high"
            verdict = "You are likely a winning player."
        elif self.hdi_upper < 0:
            confidence = "high"
            verdict = "You are likely a losing player."
        else:
            confidence = "uncertain"
            verdict = "Your true winrate is uncertain - the CI crosses zero."

        # Sample size assessment
        n = len(self.hand_results)
        if n < 5000:
            size_note = "Sample size is small. Results will stabilize with more hands."
        elif n < 20000:
            size_note = "Moderate sample size. Results are becoming reliable."
        else:
            size_note = "Large sample size. High confidence in results."

        return f"{verdict} {size_note}"


def render_posterior_chart(
    hand_results: list[float],
    title: str = "Posterior Winrate Distribution (Bootstrap)",
) -> Optional[WinrateEstimator]:
    """
    Render the posterior distribution histogram.

    Args:
        hand_results: List of hand-level PnL in BB.
        title: Chart title.

    Returns:
        WinrateEstimator instance or None if insufficient data.
    """
    if len(hand_results) < 100:
        st.warning("Need at least 100 hands for Bayesian estimation.")
        return None

    # Fit model
    model = WinrateEstimator(hand_results)

    if model.samples is None:
        st.error("Failed to run bootstrap estimation.")
        return None

    # Create figure
    fig = go.Figure()

    # Add histogram
    fig.add_trace(go.Histogram(
        x=model.samples,
        nbinsx=50,
        name='Posterior Distribution',
        marker_color='rgba(52, 152, 219, 0.7)',
        hovertemplate='BB/100: %{x:.2f}<br>Count: %{y}<extra></extra>',
    ))

    # Add vertical lines for CI bounds
    fig.add_vline(
        x=model.hdi_lower,
        line_dash='dash',
        line_color='#E74C3C',
        annotation_text=f'2.5%: {model.hdi_lower:.2f}',
        annotation_position='top left',
    )

    fig.add_vline(
        x=model.hdi_upper,
        line_dash='dash',
        line_color='#E74C3C',
        annotation_text=f'97.5%: {model.hdi_upper:.2f}',
        annotation_position='top right',
    )

    # Add zero line
    fig.add_vline(
        x=0,
        line_dash='solid',
        line_color='#95A5A6',
        line_width=2,
        annotation_text='Breakeven',
        annotation_position='bottom',
    )

    # Add point estimate line
    fig.add_vline(
        x=model.point_estimate,
        line_dash='dot',
        line_color='#27AE60',
        annotation_text=f'Observed: {model.point_estimate:.2f}',
        annotation_position='top',
    )

    # Shade the 95% HDI region
    fig.add_vrect(
        x0=model.hdi_lower,
        x1=model.hdi_upper,
        fillcolor='rgba(231, 76, 60, 0.1)',
        line_width=0,
    )

    # Style
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#fff')),
        xaxis_title='Winrate (BB/100)',
        yaxis_title='Frequency',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
        bargap=0.1,
    )

    st.plotly_chart(fig, use_container_width=True)

    return model


def calculate_required_sample_size(
    target_precision: float = 1.0,
    variance: float = 68.0,
    confidence: float = 0.95,
) -> int:
    """
    Calculate required sample size for target precision.

    Args:
        target_precision: Desired margin of error in BB/100.
        variance: Assumed per-hand variance (default 68 BB²).
        confidence: Confidence level.

    Returns:
        Required number of hands.
    """
    z = stats.norm.ppf((1 + confidence) / 2)
    # SE = sqrt(variance / n) * 100
    # target_precision = z * SE
    # n = (z * sqrt(variance) * 100 / target_precision)²
    n = (z * np.sqrt(variance) * 100 / target_precision) ** 2
    return int(np.ceil(n))
