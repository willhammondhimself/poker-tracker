"""
Range Analyzer - Calculate and visualize playing ranges from hand history.
"""

from typing import Optional
from collections import defaultdict

# Standard 13x13 hand matrix layout
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

# All possible starting hands in matrix format
# Pairs on diagonal, suited above, offsuit below
def get_hand_matrix_position(card1: tuple, card2: tuple) -> tuple[int, int, str]:
    """
    Convert two hole cards to matrix position.

    Returns:
        (row, col, hand_type) where hand_type is 'pair', 'suited', or 'offsuit'
    """
    rank1, suit1 = card1
    rank2, suit2 = card2

    # Normalize ranks (T for 10)
    r1 = rank1 if rank1 != '10' else 'T'
    r2 = rank2 if rank2 != '10' else 'T'

    # Get rank indices
    try:
        idx1 = RANKS.index(r1)
        idx2 = RANKS.index(r2)
    except ValueError:
        return (-1, -1, 'unknown')

    is_suited = suit1 == suit2

    if idx1 == idx2:
        # Pair - on diagonal
        return (idx1, idx2, 'pair')
    elif is_suited:
        # Suited - higher rank determines row (above diagonal)
        row = min(idx1, idx2)
        col = max(idx1, idx2)
        return (row, col, 'suited')
    else:
        # Offsuit - higher rank determines column (below diagonal)
        row = max(idx1, idx2)
        col = min(idx1, idx2)
        return (row, col, 'offsuit')


def get_hand_name(row: int, col: int) -> str:
    """Get the hand name for a matrix position."""
    if row == col:
        return f"{RANKS[row]}{RANKS[col]}"
    elif row < col:
        return f"{RANKS[row]}{RANKS[col]}s"
    else:
        return f"{RANKS[col]}{RANKS[row]}o"


def analyze_ranges(hands: list[dict], position_filter: Optional[str] = None) -> dict:
    """
    Analyze hands to build range data.

    Args:
        hands: List of hand dictionaries with hole_cards, position, result, action
        position_filter: Optional position to filter by (e.g., 'BTN', 'CO')

    Returns:
        Dictionary with range statistics:
        {
            'matrix': 13x13 matrix of hand stats,
            'total_hands': int,
            'vpip_hands': int,
            'positions': {position: count},
            'summary': str
        }
    """
    # Initialize 13x13 matrix
    matrix = [[{
        'count': 0,
        'profit': 0.0,
        'vpip': 0,
        'pfr': 0,
        'won': 0,
        'actions': defaultdict(int)
    } for _ in range(13)] for _ in range(13)]

    total_hands = 0
    vpip_hands = 0
    positions = defaultdict(int)

    for hand in hands:
        hole_cards = hand.get('hole_cards', [])
        position = hand.get('position', 'Unknown')
        result = hand.get('result', 0)
        action = hand.get('action', 'Unknown')

        # Apply position filter
        if position_filter and position != position_filter:
            continue

        # Need valid hole cards
        if len(hole_cards) != 2:
            continue

        total_hands += 1
        positions[position] += 1

        # Determine VPIP (voluntary put money in pot)
        is_vpip = action.lower() not in ['fold', 'check', 'unknown']
        if is_vpip:
            vpip_hands += 1

        # Get matrix position
        row, col, hand_type = get_hand_matrix_position(hole_cards[0], hole_cards[1])

        if row < 0 or col < 0:
            continue

        # Update matrix cell
        cell = matrix[row][col]
        cell['count'] += 1
        cell['profit'] += result
        if is_vpip:
            cell['vpip'] += 1
        if action.lower() in ['raise', '3bet', '4bet', 'all-in']:
            cell['pfr'] += 1
        if result > 0:
            cell['won'] += 1
        cell['actions'][action] += 1

    return {
        'matrix': matrix,
        'total_hands': total_hands,
        'vpip_hands': vpip_hands,
        'positions': dict(positions),
        'vpip_pct': round(vpip_hands / total_hands * 100, 1) if total_hands > 0 else 0,
    }


def get_range_grid_data(matrix: list, mode: str = 'frequency') -> list[list[dict]]:
    """
    Convert matrix to grid display data.

    Args:
        matrix: 13x13 matrix from analyze_ranges
        mode: 'frequency' (count), 'profit', or 'winrate'

    Returns:
        13x13 grid with display data for each cell
    """
    grid = []
    max_count = max(cell['count'] for row in matrix for cell in row) or 1

    for row_idx, row in enumerate(matrix):
        grid_row = []
        for col_idx, cell in enumerate(row):
            hand_name = get_hand_name(row_idx, col_idx)
            count = cell['count']
            profit = cell['profit']
            vpip = cell['vpip']
            won = cell['won']

            # Calculate display value and color intensity
            if mode == 'frequency':
                intensity = count / max_count if max_count > 0 else 0
                value = count
            elif mode == 'profit':
                # Normalize profit to -1 to 1 range
                if count > 0:
                    avg_profit = profit / count
                    intensity = max(-1, min(1, avg_profit / 50))  # $50 scale
                else:
                    intensity = 0
                value = round(profit, 2)
            elif mode == 'winrate':
                if count > 0:
                    winrate = won / count
                    intensity = winrate * 2 - 1  # 0-1 -> -1 to 1
                else:
                    intensity = 0
                value = round(won / count * 100, 1) if count > 0 else 0
            else:
                intensity = 0
                value = 0

            grid_row.append({
                'hand': hand_name,
                'count': count,
                'profit': round(profit, 2),
                'vpip': vpip,
                'won': won,
                'winrate': round(won / count * 100, 1) if count > 0 else 0,
                'avg_profit': round(profit / count, 2) if count > 0 else 0,
                'intensity': intensity,
                'value': value,
            })
        grid.append(grid_row)

    return grid


def get_position_summary(hands: list[dict]) -> dict:
    """
    Get summary stats by position.

    Returns:
        {
            'BTN': {'hands': 50, 'vpip': 45, 'profit': 125.00, ...},
            ...
        }
    """
    positions = defaultdict(lambda: {
        'hands': 0,
        'vpip': 0,
        'pfr': 0,
        'profit': 0.0,
        'won': 0,
    })

    for hand in hands:
        position = hand.get('position', 'Unknown')
        action = hand.get('action', 'Unknown')
        result = hand.get('result', 0)

        positions[position]['hands'] += 1
        positions[position]['profit'] += result

        if result > 0:
            positions[position]['won'] += 1

        if action.lower() not in ['fold', 'check', 'unknown']:
            positions[position]['vpip'] += 1

        if action.lower() in ['raise', '3bet', '4bet', 'all-in']:
            positions[position]['pfr'] += 1

    # Calculate percentages
    result = {}
    for pos, stats in positions.items():
        hands = stats['hands']
        result[pos] = {
            'hands': hands,
            'vpip': stats['vpip'],
            'vpip_pct': round(stats['vpip'] / hands * 100, 1) if hands > 0 else 0,
            'pfr': stats['pfr'],
            'pfr_pct': round(stats['pfr'] / hands * 100, 1) if hands > 0 else 0,
            'profit': round(stats['profit'], 2),
            'won': stats['won'],
            'winrate': round(stats['won'] / hands * 100, 1) if hands > 0 else 0,
        }

    return result
