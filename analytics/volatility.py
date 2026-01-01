"""
Market Regime Detector - GARCH Volatility Modeling.

Uses GARCH(1,1) to model conditional volatility of bankroll PnL,
classifying the current market regime as Low, Medium, or High volatility.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from typing import Optional
from arch import arch_model


class VolatilityModel:
    """
    GARCH(1,1) volatility model for poker session PnL.

    Fits a GARCH model to session returns and classifies the
    current volatility regime relative to historical mean.
    """

    def __init__(self, pnl_series: pd.Series):
        """
        Initialize the volatility model.

        Args:
            pnl_series: pandas Series of session PnL values (indexed by date).
        """
        self.pnl_series = pnl_series.dropna()
        self.model = None
        self.results = None
        self.conditional_volatility = None
        self.current_regime = None
        self.regime_thresholds = None

        if len(self.pnl_series) >= 10:
            self._fit_model()

    def _fit_model(self) -> None:
        """Fit the GARCH(1,1) model to the PnL series."""
        try:
            # Scale returns for numerical stability
            returns = self.pnl_series.values
            scale_factor = np.std(returns) if np.std(returns) > 0 else 1
            scaled_returns = returns / scale_factor * 100

            # Fit GARCH(1,1) model
            self.model = arch_model(
                scaled_returns,
                vol='Garch',
                p=1,
                q=1,
                mean='Constant',
                rescale=False,
            )

            self.results = self.model.fit(disp='off', show_warning=False)

            # Get conditional volatility and rescale
            cond_vol = self.results.conditional_volatility
            self.conditional_volatility = pd.Series(
                cond_vol * scale_factor / 100,
                index=self.pnl_series.index,
            )

            # Calculate regime thresholds (mean ± 1 std)
            vol_mean = self.conditional_volatility.mean()
            vol_std = self.conditional_volatility.std()

            self.regime_thresholds = {
                'low_upper': vol_mean - 0.5 * vol_std,
                'high_lower': vol_mean + 0.5 * vol_std,
                'mean': vol_mean,
                'std': vol_std,
            }

            # Classify current regime
            current_vol = self.conditional_volatility.iloc[-1]
            self.current_regime = self._classify_regime(current_vol)

        except Exception as e:
            # Fallback to simple rolling volatility
            self._fallback_volatility()

    def _fallback_volatility(self) -> None:
        """Use rolling standard deviation as fallback."""
        window = min(10, len(self.pnl_series))
        self.conditional_volatility = self.pnl_series.rolling(
            window=window,
            min_periods=3,
        ).std().fillna(method='bfill')

        vol_mean = self.conditional_volatility.mean()
        vol_std = self.conditional_volatility.std()

        self.regime_thresholds = {
            'low_upper': vol_mean - 0.5 * vol_std,
            'high_lower': vol_mean + 0.5 * vol_std,
            'mean': vol_mean,
            'std': vol_std,
        }

        current_vol = self.conditional_volatility.iloc[-1]
        self.current_regime = self._classify_regime(current_vol)

    def _classify_regime(self, volatility: float) -> str:
        """
        Classify volatility into regime.

        Args:
            volatility: Current volatility value.

        Returns:
            Regime classification: 'Low', 'Medium', or 'High'.
        """
        if self.regime_thresholds is None:
            return 'Unknown'

        if volatility < self.regime_thresholds['low_upper']:
            return 'Low'
        elif volatility > self.regime_thresholds['high_lower']:
            return 'High'
        else:
            return 'Medium'

    def get_summary(self) -> dict:
        """
        Get summary statistics.

        Returns:
            Dictionary with volatility metrics.
        """
        if self.conditional_volatility is None:
            return {
                'current_regime': 'Insufficient Data',
                'current_volatility': 0,
                'mean_volatility': 0,
                'volatility_percentile': 0,
            }

        current_vol = self.conditional_volatility.iloc[-1]
        percentile = (
            (self.conditional_volatility < current_vol).sum()
            / len(self.conditional_volatility) * 100
        )

        return {
            'current_regime': self.current_regime,
            'current_volatility': round(current_vol, 2),
            'mean_volatility': round(self.conditional_volatility.mean(), 2),
            'volatility_percentile': round(percentile, 1),
        }


def render_volatility_chart(
    pnl_series: pd.Series,
    title: str = "Conditional Volatility (GARCH)",
) -> Optional[VolatilityModel]:
    """
    Render the GARCH volatility chart with regime bands.

    Args:
        pnl_series: pandas Series of session PnL values.
        title: Chart title.

    Returns:
        VolatilityModel instance or None if insufficient data.
    """
    if len(pnl_series) < 10:
        st.warning("Need at least 10 sessions for volatility modeling.")
        return None

    # Fit model
    model = VolatilityModel(pnl_series)

    if model.conditional_volatility is None:
        st.error("Failed to fit volatility model.")
        return None

    # Create figure
    fig = go.Figure()

    # Add conditional volatility line
    fig.add_trace(go.Scatter(
        x=model.conditional_volatility.index,
        y=model.conditional_volatility.values,
        mode='lines',
        name='Conditional Volatility',
        line=dict(color='#3498DB', width=2),
        hovertemplate='Date: %{x}<br>Volatility: $%{y:.2f}<extra></extra>',
    ))

    # Add mean line
    mean_vol = model.regime_thresholds['mean']
    fig.add_hline(
        y=mean_vol,
        line_dash='dash',
        line_color='#95A5A6',
        annotation_text=f'Mean: ${mean_vol:.2f}',
    )

    # Add +2σ band (High volatility zone)
    high_threshold = mean_vol + 2 * model.regime_thresholds['std']
    fig.add_hline(
        y=high_threshold,
        line_dash='dot',
        line_color='#E74C3C',
        annotation_text='+2σ',
    )

    # Add -2σ band (Low volatility zone)
    low_threshold = max(0, mean_vol - 2 * model.regime_thresholds['std'])
    fig.add_hline(
        y=low_threshold,
        line_dash='dot',
        line_color='#27AE60',
        annotation_text='-2σ',
    )

    # Add regime shading
    fig.add_hrect(
        y0=model.regime_thresholds['high_lower'],
        y1=high_threshold,
        fillcolor='rgba(231, 76, 60, 0.1)',
        line_width=0,
        annotation_text='High Vol',
        annotation_position='top right',
    )

    fig.add_hrect(
        y0=low_threshold,
        y1=model.regime_thresholds['low_upper'],
        fillcolor='rgba(39, 174, 96, 0.1)',
        line_width=0,
        annotation_text='Low Vol',
        annotation_position='bottom right',
    )

    # Style
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#fff')),
        xaxis_title='Date',
        yaxis_title='Volatility ($)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    return model
