"""
Monte Carlo Bankroll Simulator - Risk of Ruin Analysis.

Simulates future bankroll trajectories using historical winrate
and variance to calculate probability of going broke.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """Results from Monte Carlo bankroll simulation."""
    trajectories: np.ndarray          # Shape: (n_sims, n_hands+1)
    risk_of_ruin: float               # Probability of hitting 0
    expected_final_br: float          # Mean final bankroll
    median_final_br: float            # Median final bankroll
    percentile_5: float               # 5th percentile (bad case)
    percentile_25: float              # 25th percentile
    percentile_75: float              # 75th percentile
    percentile_95: float              # 95th percentile (good case)
    prob_reach_target: float          # Probability of reaching target
    max_drawdown_median: float        # Median maximum drawdown
    hands_simulated: int
    simulations_run: int

    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            'risk_of_ruin': self.risk_of_ruin,
            'expected_final_br': self.expected_final_br,
            'median_final_br': self.median_final_br,
            'percentile_5': self.percentile_5,
            'percentile_25': self.percentile_25,
            'percentile_75': self.percentile_75,
            'percentile_95': self.percentile_95,
            'prob_reach_target': self.prob_reach_target,
            'max_drawdown_median': self.max_drawdown_median,
            'hands_simulated': self.hands_simulated,
            'simulations_run': self.simulations_run,
        }


def simulate_bankroll(
    current_br: float,
    winrate_bb100: float,
    std_dev_bb100: float = 80.0,
    hands: int = 50000,
    n_sims: int = 1000,
    target_br: Optional[float] = None,
    big_blind: float = 0.10,
) -> SimulationResult:
    """
    Run Monte Carlo simulation of bankroll evolution.

    Uses random walk model where each hand's result is drawn from
    a normal distribution with mean = winrate and std = standard deviation.

    Args:
        current_br: Starting bankroll in dollars
        winrate_bb100: Win rate in BB/100 hands (e.g., 5.0 = 5 BB/100)
        std_dev_bb100: Standard deviation in BB/100 (default 80 for NLHE)
        hands: Number of hands to simulate
        n_sims: Number of simulation paths to run
        target_br: Target bankroll to calculate probability of reaching
        big_blind: Big blind size in dollars (for BB to $ conversion)

    Returns:
        SimulationResult with trajectories and statistics

    Mathematical Model:
        - Each 100-hand block: result ~ N(winrate, std_dev)
        - Bankroll[t+100] = Bankroll[t] + result * BB_size
        - Risk of Ruin = P(min(Bankroll) <= 0)
    """
    # Validate inputs
    if current_br <= 0:
        raise ValueError("Starting bankroll must be positive")
    if hands < 100:
        raise ValueError("Must simulate at least 100 hands")
    if n_sims < 10:
        raise ValueError("Must run at least 10 simulations")

    # Convert to per-hand metrics
    # Winrate: BB/100 → BB/hand → $/hand
    mean_per_hand = (winrate_bb100 / 100) * big_blind

    # Std dev: BB/100 → BB/hand → $/hand
    # Note: Variance scales linearly with hands, so std dev scales with sqrt
    # std_dev_bb100 is the std dev of sum over 100 hands
    # Per-hand std dev = std_dev_bb100 / sqrt(100) = std_dev_bb100 / 10
    std_per_hand = (std_dev_bb100 / 10) * big_blind

    # Initialize trajectory array
    # Shape: (n_sims, hands + 1) - includes starting bankroll
    trajectories = np.zeros((n_sims, hands + 1))
    trajectories[:, 0] = current_br

    # Generate all random outcomes at once (vectorized for speed)
    # Each value represents one hand's P&L
    outcomes = np.random.normal(mean_per_hand, std_per_hand, size=(n_sims, hands))

    # Calculate cumulative bankroll
    cumulative_outcomes = np.cumsum(outcomes, axis=1)
    trajectories[:, 1:] = current_br + cumulative_outcomes

    # Calculate statistics
    final_bankrolls = trajectories[:, -1]
    min_bankrolls = np.min(trajectories, axis=1)

    # Risk of Ruin: fraction of sims where bankroll hit 0 or below
    risk_of_ruin = np.mean(min_bankrolls <= 0)

    # Final bankroll statistics
    expected_final = np.mean(final_bankrolls)
    median_final = np.median(final_bankrolls)
    p5 = np.percentile(final_bankrolls, 5)
    p25 = np.percentile(final_bankrolls, 25)
    p75 = np.percentile(final_bankrolls, 75)
    p95 = np.percentile(final_bankrolls, 95)

    # Probability of reaching target
    if target_br and target_br > current_br:
        max_bankrolls = np.max(trajectories, axis=1)
        prob_target = np.mean(max_bankrolls >= target_br)
    else:
        prob_target = 1.0 if target_br and target_br <= current_br else 0.0

    # Maximum drawdown calculation
    # Drawdown at each point = peak so far - current value
    running_max = np.maximum.accumulate(trajectories, axis=1)
    drawdowns = running_max - trajectories
    max_drawdowns = np.max(drawdowns, axis=1)
    median_max_drawdown = np.median(max_drawdowns)

    return SimulationResult(
        trajectories=trajectories,
        risk_of_ruin=risk_of_ruin,
        expected_final_br=expected_final,
        median_final_br=median_final,
        percentile_5=p5,
        percentile_25=p25,
        percentile_75=p75,
        percentile_95=p95,
        prob_reach_target=prob_target,
        max_drawdown_median=median_max_drawdown,
        hands_simulated=hands,
        simulations_run=n_sims,
    )


def calculate_kelly_criterion(
    winrate_bb100: float,
    std_dev_bb100: float = 80.0,
) -> dict:
    """
    Calculate Kelly Criterion for optimal bankroll sizing.

    Kelly formula for continuous outcomes:
    f* = μ / σ² (fraction of bankroll to risk per unit of variance)

    For poker, this translates to minimum buyins needed.

    Args:
        winrate_bb100: Win rate in BB/100
        std_dev_bb100: Standard deviation in BB/100

    Returns:
        Dictionary with Kelly calculations
    """
    if std_dev_bb100 <= 0:
        return {'error': 'Standard deviation must be positive'}

    # Convert to per-hand
    mu = winrate_bb100 / 100  # BB per hand
    sigma = std_dev_bb100 / 10  # BB per hand std dev

    # Variance per hand
    variance = sigma ** 2

    # Kelly fraction (what fraction of edge to capture)
    # Full Kelly: f* = μ / σ²
    full_kelly = mu / variance if variance > 0 else 0

    # For poker, we want buyins needed
    # Rule of thumb: 20-30 buyins for full Kelly, more conservative = more buyins
    # Bankroll needed = 1 / (kelly_fraction * risk_tolerance)

    # Calculate recommended buyins at different risk levels
    # Conservative: 1% RoR target, Moderate: 5% RoR, Aggressive: 10% RoR

    # Using simplified formula: Buyins ≈ variance / (2 * winrate) for low RoR
    if mu > 0:
        conservative_buyins = max(50, int(variance / (0.02 * mu)))
        moderate_buyins = max(30, int(variance / (0.05 * mu)))
        aggressive_buyins = max(20, int(variance / (0.10 * mu)))
    else:
        # Losing or breakeven player
        conservative_buyins = 100
        moderate_buyins = 100
        aggressive_buyins = 100

    return {
        'full_kelly_fraction': round(full_kelly, 6),
        'conservative_buyins': conservative_buyins,
        'moderate_buyins': moderate_buyins,
        'aggressive_buyins': aggressive_buyins,
        'winrate_bb100': winrate_bb100,
        'std_dev_bb100': std_dev_bb100,
    }


def estimate_time_to_target(
    current_br: float,
    target_br: float,
    winrate_bb100: float,
    hands_per_hour: float = 60,
    big_blind: float = 0.10,
) -> dict:
    """
    Estimate hours needed to reach bankroll target.

    Args:
        current_br: Current bankroll in dollars
        target_br: Target bankroll in dollars
        winrate_bb100: Win rate in BB/100
        hands_per_hour: Average hands played per hour
        big_blind: Big blind size in dollars

    Returns:
        Dictionary with time estimates
    """
    if target_br <= current_br:
        return {
            'hours_needed': 0,
            'hands_needed': 0,
            'sessions_needed': 0,
            'message': 'Target already reached!',
        }

    if winrate_bb100 <= 0:
        return {
            'hours_needed': float('inf'),
            'hands_needed': float('inf'),
            'sessions_needed': float('inf'),
            'message': 'Cannot reach target with non-positive winrate',
        }

    # Dollars needed
    dollars_needed = target_br - current_br

    # Dollars won per hand (expected value)
    dollars_per_hand = (winrate_bb100 / 100) * big_blind

    # Hands needed (expected value)
    hands_needed = dollars_needed / dollars_per_hand

    # Hours needed
    hours_needed = hands_needed / hands_per_hour

    # Sessions (assuming 2 hour sessions)
    sessions_needed = hours_needed / 2

    return {
        'hours_needed': round(hours_needed, 1),
        'hands_needed': int(hands_needed),
        'sessions_needed': int(np.ceil(sessions_needed)),
        'dollars_per_hour': round(dollars_per_hand * hands_per_hour, 2),
        'message': f'~{int(hours_needed)} hours at current winrate',
    }


def get_sample_trajectories(
    result: SimulationResult,
    n_samples: int = 100,
) -> np.ndarray:
    """
    Get a subset of trajectories for plotting.

    Selects evenly spaced trajectories to show distribution.

    Args:
        result: SimulationResult from simulate_bankroll
        n_samples: Number of trajectories to return

    Returns:
        Array of shape (n_samples, hands+1)
    """
    n_sims = result.trajectories.shape[0]
    if n_samples >= n_sims:
        return result.trajectories

    # Sort by final bankroll to get representative sample
    final_brs = result.trajectories[:, -1]
    sorted_indices = np.argsort(final_brs)

    # Select evenly spaced indices from sorted array
    selected = np.linspace(0, n_sims - 1, n_samples, dtype=int)
    trajectory_indices = sorted_indices[selected]

    return result.trajectories[trajectory_indices]


def get_percentile_trajectories(result: SimulationResult) -> dict:
    """
    Calculate percentile trajectories for confidence band plotting.

    Args:
        result: SimulationResult from simulate_bankroll

    Returns:
        Dictionary with percentile trajectories
    """
    trajectories = result.trajectories

    return {
        'p5': np.percentile(trajectories, 5, axis=0),
        'p25': np.percentile(trajectories, 25, axis=0),
        'p50': np.percentile(trajectories, 50, axis=0),  # Median
        'p75': np.percentile(trajectories, 75, axis=0),
        'p95': np.percentile(trajectories, 95, axis=0),
        'mean': np.mean(trajectories, axis=0),
    }
