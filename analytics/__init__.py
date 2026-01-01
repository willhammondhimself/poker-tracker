"""
Quant Research Platform - Advanced Analytics Modules.

Provides financial engineering and machine learning capabilities:
- GARCH volatility modeling for market regime detection
- K-Means clustering for villain taxonomy
- Bootstrap resampling for Bayesian winrate estimation
"""

from .volatility import VolatilityModel, render_volatility_chart
from .clustering import VillainCluster, render_cluster_chart
from .bayesian import WinrateEstimator, render_posterior_chart

__all__ = [
    "VolatilityModel",
    "render_volatility_chart",
    "VillainCluster",
    "render_cluster_chart",
    "WinrateEstimator",
    "render_posterior_chart",
]
