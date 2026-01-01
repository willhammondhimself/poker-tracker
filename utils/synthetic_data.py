"""
Synthetic Data Generator for Quant Research Platform.

Generates realistic poker data for testing and demonstration:
- Sessions with diverse PnL patterns
- Opponents with distinct statistical profiles
- Hands with realistic result distributions
"""

import json
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"


# Player archetype templates
ARCHETYPES = {
    'Nit': {
        'vpip_range': (10, 18),
        'pfr_range': (8, 14),
        'af_range': (1.5, 3.0),
        'wtsd_range': (20, 28),
        'names': ['TightMike', 'RockSolid', 'NittyNate', 'PatientPaul', 'WaitingWalt'],
    },
    'TAG': {
        'vpip_range': (20, 28),
        'pfr_range': (16, 22),
        'af_range': (2.5, 4.0),
        'wtsd_range': (24, 32),
        'names': ['SolidSam', 'RegularRick', 'BalancedBen', 'OptimalOmar', 'GTOGreg'],
    },
    'LAG': {
        'vpip_range': (30, 40),
        'pfr_range': (25, 35),
        'af_range': (3.5, 5.5),
        'wtsd_range': (28, 38),
        'names': ['LooselarryL', 'AggroAndy', 'PressurePete', 'BetBetBet', 'ActionAl'],
    },
    'Calling Station': {
        'vpip_range': (40, 55),
        'pfr_range': (5, 12),
        'af_range': (0.5, 1.5),
        'wtsd_range': (35, 50),
        'names': ['CallMeCarl', 'SeeTheFlop', 'CuriousChris', 'ShowdownStan', 'NeverFoldNick'],
    },
    'Maniac': {
        'vpip_range': (50, 70),
        'pfr_range': (35, 50),
        'af_range': (4.0, 7.0),
        'wtsd_range': (30, 45),
        'names': ['CrazyMike', 'AllInAlex', 'ManiacMax', 'WildWill', 'ChaosCarl'],
    },
}


def generate_synthetic_sessions(
    n: int = 50,
    start_date: Optional[datetime] = None,
    winrate_bb_hr: float = 5.0,
    variance: float = 80.0,
) -> list[dict]:
    """
    Generate synthetic poker sessions with realistic variance.

    Args:
        n: Number of sessions to generate.
        start_date: Starting date for sessions.
        winrate_bb_hr: Expected winrate in BB/hour.
        variance: Standard deviation of hourly results.

    Returns:
        List of session dictionaries.
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=n * 2)

    sessions = []
    current_date = start_date

    stakes_options = ['0.05/0.10', '0.10/0.25', '0.25/0.50']
    locations = ['Online - Ignition', 'Online - ACR', 'Home Game', 'Casino']

    for i in range(n):
        # Randomize session length (1-6 hours)
        hours = round(random.uniform(1.0, 6.0), 1)

        # Generate PnL with variance
        # BB/hr * hours + noise
        bb_won = np.random.normal(winrate_bb_hr * hours, variance * np.sqrt(hours))

        # Convert BB to $ based on stakes
        stakes = random.choice(stakes_options)
        bb_size = float(stakes.split('/')[1])
        profit = round(bb_won * bb_size, 2)

        # Generate buy-in and cash-out
        buy_in = random.choice([100, 200, 300, 500])
        cash_out = round(buy_in + profit, 2)

        # Advance date
        current_date += timedelta(days=random.randint(1, 4))

        session = {
            'id': i + 1,
            'date': current_date.strftime('%Y-%m-%d'),
            'stakes': stakes,
            'location': random.choice(locations),
            'duration_hours': hours,
            'buy_in': buy_in,
            'cash_out': cash_out,
            'profit': profit,
            'hands_played': int(hours * 75),  # ~75 hands/hr
            'notes': '',
        }

        sessions.append(session)

    return sessions


def generate_synthetic_opponents(n: int = 25) -> list[dict]:
    """
    Generate synthetic opponents with distinct stat profiles.

    Creates villains across all archetypes:
    - 5 Nits
    - 5 TAGs
    - 5 LAGs
    - 5 Calling Stations
    - 5 Maniacs

    Args:
        n: Total number of opponents (distributed across types).

    Returns:
        List of opponent dictionaries.
    """
    opponents = []
    opponent_id = 1

    # Distribute across archetypes
    per_type = max(1, n // 5)

    for archetype, template in ARCHETYPES.items():
        names = template['names'][:per_type]

        for name in names:
            # Generate stats within archetype ranges
            vpip = random.uniform(*template['vpip_range'])
            pfr = random.uniform(*template['pfr_range'])
            af = random.uniform(*template['af_range'])
            wtsd = random.uniform(*template['wtsd_range'])

            # Generate hands played (50-500 for diversity)
            hands_played = random.randint(50, 500)

            # Calculate raw counts from percentages
            vpip_count = int(vpip / 100 * hands_played)
            pfr_count = int(pfr / 100 * hands_played)
            three_bet_count = int(random.uniform(2, 8) / 100 * hands_played)

            opponent = {
                'id': opponent_id,
                'name': name,
                'tags': [archetype.lower().replace(' ', '_')],
                'notes': f'Auto-generated {archetype} profile',
                'stats': {
                    'hands_played': hands_played,
                    'vpip_count': vpip_count,
                    'pfr_count': pfr_count,
                    'three_bet_count': three_bet_count,
                    'cbet_count': int(random.uniform(0.4, 0.7) * pfr_count),
                    'fold_to_cbet_count': int(random.uniform(0.3, 0.6) * vpip_count),
                },
                'calculated_stats': {
                    'vpip': round(vpip, 1),
                    'pfr': round(pfr, 1),
                    'af': round(af, 2),
                    'wtsd': round(wtsd, 1),
                },
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }

            opponents.append(opponent)
            opponent_id += 1

    return opponents


def generate_synthetic_hands(
    n: int = 500,
    session_id: int = 1,
    winrate_bb100: float = 5.0,
) -> list[dict]:
    """
    Generate synthetic hand results with realistic distribution.

    Uses a mixture model:
    - 70% small pots (-3 to +3 BB)
    - 20% medium pots (-15 to +15 BB)
    - 10% big pots (-100 to +100 BB)

    Args:
        n: Number of hands to generate.
        session_id: Session ID to associate with.
        winrate_bb100: Target winrate in BB/100.

    Returns:
        List of hand dictionaries.
    """
    hands = []
    positions = ['BTN', 'CO', 'MP', 'UTG', 'SB', 'BB']
    actions = ['fold', 'call', 'raise', '3-bet', 'all-in']

    # Adjust mean to achieve target winrate
    # Small pots: mean = winrate_bb100 / 100
    small_mean = winrate_bb100 / 100 * 0.7
    medium_mean = winrate_bb100 / 100 * 0.2
    big_mean = winrate_bb100 / 100 * 0.1

    for i in range(n):
        # Determine pot size category
        r = random.random()

        if r < 0.70:
            # Small pot
            result = np.random.normal(small_mean, 1.5)
            result = np.clip(result, -5, 5)
        elif r < 0.90:
            # Medium pot
            result = np.random.normal(medium_mean, 8)
            result = np.clip(result, -25, 25)
        else:
            # Big pot
            result = np.random.normal(big_mean, 40)
            result = np.clip(result, -150, 150)

        hand = {
            'id': i + 1,
            'session_id': session_id,
            'timestamp': (datetime.now() - timedelta(minutes=n - i)).isoformat(),
            'position': random.choice(positions),
            'hole_cards': _random_hole_cards(),
            'action': random.choice(actions),
            'result': round(result, 2),
            'board': _random_board() if random.random() > 0.3 else {},
            'notes': '',
        }

        hands.append(hand)

    return hands


def _random_hole_cards() -> list[dict]:
    """Generate random hole cards."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    suits = ['h', 'd', 'c', 's']

    cards = []
    used = set()

    for _ in range(2):
        while True:
            rank = random.choice(ranks)
            suit = random.choice(suits)
            card = f"{rank}{suit}"
            if card not in used:
                used.add(card)
                cards.append({'rank': rank, 'suit': suit})
                break

    return cards


def _random_board() -> dict:
    """Generate random board cards."""
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    suits = ['h', 'd', 'c', 's']

    used = set()
    board = {}

    # Flop
    flop = []
    for _ in range(3):
        while True:
            rank = random.choice(ranks)
            suit = random.choice(suits)
            card = f"{rank}{suit}"
            if card not in used:
                used.add(card)
                flop.append({'rank': rank, 'suit': suit})
                break
    board['flop'] = flop

    # Turn (70% of the time)
    if random.random() > 0.3:
        while True:
            rank = random.choice(ranks)
            suit = random.choice(suits)
            card = f"{rank}{suit}"
            if card not in used:
                used.add(card)
                board['turn'] = {'rank': rank, 'suit': suit}
                break

        # River (60% of turn hands)
        if random.random() > 0.4:
            while True:
                rank = random.choice(ranks)
                suit = random.choice(suits)
                card = f"{rank}{suit}"
                if card not in used:
                    used.add(card)
                    board['river'] = {'rank': rank, 'suit': suit}
                    break

    return board


def save_synthetic_data(
    n_sessions: int = 50,
    n_opponents: int = 25,
    n_hands: int = 500,
) -> dict:
    """
    Generate and save all synthetic data.

    Args:
        n_sessions: Number of sessions.
        n_opponents: Number of opponents.
        n_hands: Number of hands.

    Returns:
        Summary of generated data.
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Generate data
    sessions = generate_synthetic_sessions(n_sessions)
    opponents = generate_synthetic_opponents(n_opponents)
    hands = generate_synthetic_hands(n_hands)

    # Save to files
    with open(DATA_DIR / 'sessions.json', 'w') as f:
        json.dump(sessions, f, indent=2)

    with open(DATA_DIR / 'opponents.json', 'w') as f:
        json.dump(opponents, f, indent=2)

    with open(DATA_DIR / 'hands.json', 'w') as f:
        json.dump(hands, f, indent=2)

    return {
        'sessions': len(sessions),
        'opponents': len(opponents),
        'hands': len(hands),
        'path': str(DATA_DIR),
    }


if __name__ == '__main__':
    # Run standalone to generate test data
    result = save_synthetic_data()
    print(f"Generated synthetic data:")
    print(f"  - {result['sessions']} sessions")
    print(f"  - {result['opponents']} opponents")
    print(f"  - {result['hands']} hands")
    print(f"  - Saved to: {result['path']}")
