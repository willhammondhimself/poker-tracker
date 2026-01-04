"""Ignition Casino Hand History Parser for Quant Poker Analytics.

Parses Ignition/Bovada Zone Poker hand history files and extracts
structured hand data for analysis.

Supports:
- Zone Poker (anonymous tables)
- Cash games (No Limit Hold'em)
- 6-max and 9-max tables
"""

import re
from datetime import datetime
from typing import Optional


# Card conversion for Ignition format
RANK_MAP = {
    'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', 'T': 'T',
    '10': 'T', '9': '9', '8': '8', '7': '7', '6': '6',
    '5': '5', '4': '4', '3': '3', '2': '2'
}

SUIT_MAP = {
    'h': '♥', 's': '♠', 'd': '♦', 'c': '♣',
    'H': '♥', 'S': '♠', 'D': '♦', 'C': '♣'
}

# Position mapping based on seat count and button position
POSITION_MAP_6MAX = {
    0: 'BTN', 1: 'SB', 2: 'BB', 3: 'UTG', 4: 'HJ', 5: 'CO'
}

POSITION_MAP_9MAX = {
    0: 'BTN', 1: 'SB', 2: 'BB', 3: 'UTG', 4: 'UTG+1',
    5: 'MP', 6: 'MP+1', 7: 'HJ', 8: 'CO'
}


def parse_card(card_str: str) -> Optional[tuple[str, str]]:
    """Parse a card string like 'Ah' or '10s' into (rank, suit) tuple.

    Args:
        card_str: Card string in Ignition format (e.g., 'Ah', 'Ks', '10d')

    Returns:
        Tuple of (rank, suit_symbol) or None if invalid
    """
    card_str = card_str.strip()
    if len(card_str) < 2:
        return None

    # Handle 10 as special case
    if card_str.startswith('10'):
        rank = 'T'
        suit = card_str[2:3]
    else:
        rank = card_str[0].upper()
        suit = card_str[1:2]

    if rank not in RANK_MAP:
        return None
    if suit.lower() not in SUIT_MAP:
        return None

    return (RANK_MAP[rank], SUIT_MAP[suit.lower()])


def parse_cards(cards_str: str) -> list[tuple[str, str]]:
    """Parse multiple cards from a string like '[Ah Ks]' or 'Ah Ks'.

    Args:
        cards_str: String containing card representations

    Returns:
        List of (rank, suit) tuples
    """
    # Remove brackets
    cards_str = cards_str.replace('[', '').replace(']', '').strip()

    # Split on whitespace
    card_strs = cards_str.split()

    cards = []
    for cs in card_strs:
        card = parse_card(cs)
        if card:
            cards.append(card)

    return cards


def parse_stake(stake_str: str) -> str:
    """Parse stake string like '$0.02/$0.05' into '0.02/0.05'.

    Args:
        stake_str: Stake string from hand history

    Returns:
        Formatted stake string
    """
    # Remove $ symbols and clean up
    stake_str = stake_str.replace('$', '').strip()
    return stake_str


def parse_money(money_str: str) -> float:
    """Parse money string like '$5.25' or '5.25' into float.

    Args:
        money_str: Money string

    Returns:
        Float value
    """
    money_str = money_str.replace('$', '').replace(',', '').strip()
    try:
        return float(money_str)
    except ValueError:
        return 0.0


def determine_position(seat_num: int, button_seat: int, num_seats: int) -> str:
    """Determine position name based on seat relative to button.

    Args:
        seat_num: Player's seat number (1-indexed)
        button_seat: Button's seat number (1-indexed)
        num_seats: Total seats at table (6 or 9)

    Returns:
        Position string (BTN, SB, BB, UTG, etc.)
    """
    # Calculate relative position from button
    relative_pos = (seat_num - button_seat) % num_seats

    if num_seats <= 6:
        return POSITION_MAP_6MAX.get(relative_pos, 'Unknown')
    else:
        return POSITION_MAP_9MAX.get(relative_pos, 'Unknown')


def extract_preflop_action(hand_text: str, hero_name: str) -> str:
    """Extract hero's preflop action from hand text.

    Args:
        hand_text: Full hand text
        hero_name: Hero's identifier (e.g., '[ME]')

    Returns:
        Action string: 'raise', 'call', 'fold', 'check', 'all-in'
    """
    # Find preflop section (before FLOP or end if no flop)
    flop_match = re.search(r'\*\*\* FLOP \*\*\*', hand_text)
    if flop_match:
        preflop_section = hand_text[:flop_match.start()]
    else:
        preflop_section = hand_text

    # Look for hero's actions in preflop
    hero_pattern = re.escape(hero_name) + r'\s*:\s*(\w+)'
    actions = re.findall(hero_pattern, preflop_section, re.IGNORECASE)

    # Determine primary action (ignore posting blinds)
    for action in actions:
        action_lower = action.lower()
        if 'raise' in action_lower or 'bet' in action_lower:
            return 'raise'
        elif 'call' in action_lower:
            return 'call'
        elif 'fold' in action_lower:
            return 'fold'
        elif 'check' in action_lower:
            return 'check'
        elif 'all' in action_lower:
            return 'all-in'

    return 'unknown'


def extract_street_actions(hand_text: str, hero_name: str) -> dict:
    """Extract hero's actions on each street.

    Args:
        hand_text: Full hand text
        hero_name: Hero's identifier

    Returns:
        Dict with 'flop', 'turn', 'river' keys
    """
    actions = {}

    # Define street patterns
    streets = [
        ('flop', r'\*\*\* FLOP \*\*\*.*?(?=\*\*\* TURN|\*\*\* SUMMARY|$)'),
        ('turn', r'\*\*\* TURN \*\*\*.*?(?=\*\*\* RIVER|\*\*\* SUMMARY|$)'),
        ('river', r'\*\*\* RIVER \*\*\*.*?(?=\*\*\* SUMMARY|$)'),
    ]

    for street_name, pattern in streets:
        match = re.search(pattern, hand_text, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(0)
            hero_pattern = re.escape(hero_name) + r'\s*:\s*(\w+)'
            hero_actions = re.findall(hero_pattern, section, re.IGNORECASE)

            for action in hero_actions:
                action_lower = action.lower()
                if 'raise' in action_lower:
                    actions[street_name] = 'raise'
                    break
                elif 'bet' in action_lower:
                    actions[street_name] = 'bet'
                    break
                elif 'call' in action_lower:
                    actions[street_name] = 'call'
                    break
                elif 'fold' in action_lower:
                    actions[street_name] = 'fold'
                    break
                elif 'check' in action_lower:
                    actions[street_name] = 'check'
                    break

    return actions


def parse_single_hand(hand_text: str) -> Optional[dict]:
    """Parse a single hand from Ignition hand history text.

    Args:
        hand_text: Text of a single hand

    Returns:
        Dictionary with hand data or None if parsing fails
    """
    try:
        # Extract hand ID
        hand_id_match = re.search(r'Hand #(\d+)', hand_text)
        if not hand_id_match:
            return None
        hand_id = hand_id_match.group(1)

        # Extract date/time - Ignition uses YYYY-MM-DD format
        date_match = re.search(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
            hand_text
        )
        if date_match:
            date_str = date_match.group(1)
            try:
                hand_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                hand_date = datetime.now()
        else:
            hand_date = datetime.now()

        # Extract stakes
        stake_match = re.search(r'\$[\d.]+/\$[\d.]+', hand_text)
        stake = parse_stake(stake_match.group(0)) if stake_match else '0.05/0.10'

        # Extract table info (6-max or 9-max)
        table_match = re.search(r'(\d+)-max', hand_text, re.IGNORECASE)
        num_seats = int(table_match.group(1)) if table_match else 6

        # Find button seat
        button_match = re.search(r'Seat #(\d+) is the button', hand_text)
        button_seat = int(button_match.group(1)) if button_match else 1

        # Find hero (marked as [ME] in Ignition)
        hero_cards_match = re.search(
            r'Card dealt to a\]spot \[([^\]]+)\]|'
            r'\[ME\]\s*:\s*Card dealt to a spot \[([^\]]+)\]|'
            r'Dealt to \[ME\] \[([^\]]+)\]|'
            r'Card dealt to a spot \[([^\]]+)\]',
            hand_text,
            re.IGNORECASE
        )

        if not hero_cards_match:
            # Try alternate pattern
            hero_cards_match = re.search(
                r'\[ME\].*?(\[[A-Za-z0-9]{2}\s+[A-Za-z0-9]{2}\])',
                hand_text
            )

        if not hero_cards_match:
            return None

        # Get the first non-None group
        cards_str = next(
            (g for g in hero_cards_match.groups() if g),
            None
        )
        if not cards_str:
            return None

        hole_cards = parse_cards(cards_str)
        if len(hole_cards) != 2:
            return None

        # Find hero's seat
        hero_seat_match = re.search(
            r'Seat (\d+):\s*\[ME\]',
            hand_text,
            re.IGNORECASE
        )
        hero_seat = int(hero_seat_match.group(1)) if hero_seat_match else 1

        # Determine position
        position = determine_position(hero_seat, button_seat, num_seats)

        # Extract board cards
        board = {'flop': [], 'turn': [], 'river': []}

        flop_match = re.search(r'\*\*\* FLOP \*\*\* \[([^\]]+)\]', hand_text)
        if flop_match:
            board['flop'] = parse_cards(flop_match.group(1))

        turn_match = re.search(r'\*\*\* TURN \*\*\* \[[^\]]+\] \[([^\]]+)\]', hand_text)
        if turn_match:
            board['turn'] = parse_cards(turn_match.group(1))

        river_match = re.search(r'\*\*\* RIVER \*\*\* \[[^\]]+\] \[([^\]]+)\]', hand_text)
        if river_match:
            board['river'] = parse_cards(river_match.group(1))

        # Extract result (profit/loss)
        # Step 1: Calculate total invested by hero
        invested = 0.0

        # Match blinds and posts
        blind_matches = re.findall(
            r'\[ME\]\s*:\s*(?:Small Blind|Big blind|Posts chip)\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in blind_matches:
            invested += parse_money(m)

        # Match calls
        call_matches = re.findall(
            r'\[ME\]\s*:\s*Calls?\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in call_matches:
            invested += parse_money(m)

        # Match bets
        bet_matches = re.findall(
            r'\[ME\]\s*:\s*Bets?\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in bet_matches:
            invested += parse_money(m)

        # Match all-ins
        allin_matches = re.findall(
            r'\[ME\]\s*:\s*All-in\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in allin_matches:
            invested += parse_money(m)

        # Match raises - "Raises $X to $Y" means total bet is Y on that street
        # We need the "to" amount, not the raise amount
        raise_matches = re.findall(
            r'\[ME\]\s*:\s*Raises\s*\$?[\d.]+\s+to\s+\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in raise_matches:
            invested += parse_money(m)

        # Step 2: Subtract returned uncalled bets
        return_matches = re.findall(
            r'\[ME\]\s*:\s*Return uncalled portion of bet\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        for m in return_matches:
            invested -= parse_money(m)

        # Step 3: Determine win or loss
        # "Hand result $X" = total pot won (not profit!)
        # Profit = pot won - amount invested
        win_match = re.search(
            r'\[ME\]\s*:\s*Hand result\s*\$?([\d.]+)',
            hand_text,
            re.IGNORECASE
        )
        if win_match:
            pot_won = parse_money(win_match.group(1))
            result = pot_won - invested  # Profit = won - invested
        else:
            # No "Hand result" = hero lost (folded or lost at showdown)
            result = -invested if invested > 0 else 0.0

        # Extract preflop action
        preflop_action = extract_preflop_action(hand_text, '[ME]')

        # Extract street actions
        street_actions = extract_street_actions(hand_text, '[ME]')

        return {
            'hand_id': f'IGN-{hand_id}',
            'source': 'ignition',
            'date': hand_date.isoformat(),
            'stake': stake,
            'hole_cards': hole_cards,
            'board': board if any(board.values()) else None,
            'position': position,
            'action': preflop_action,
            'street_actions': street_actions if street_actions else None,
            'result': round(result, 2),
            'notes': f'Zone Poker - {num_seats}max',
            'opponent_id': None,
            'opponent_name': None,
        }

    except Exception as e:
        # Return None for unparseable hands
        return None


def parse_ignition_file(file_content: str) -> list[dict]:
    """Parse an Ignition hand history file and extract all hands.

    Args:
        file_content: Full text content of the hand history file

    Returns:
        List of parsed hand dictionaries
    """
    hands = []

    # Split file into individual hands
    # Ignition hands are separated by blank lines and start with "Ignition Hand #"
    hand_pattern = r'(?:Ignition|Bovada)\s+Hand\s+#\d+.*?(?=(?:Ignition|Bovada)\s+Hand\s+#|\Z)'
    hand_texts = re.findall(hand_pattern, file_content, re.DOTALL | re.IGNORECASE)

    for hand_text in hand_texts:
        parsed = parse_single_hand(hand_text)
        if parsed:
            hands.append(parsed)

    return hands


def get_import_summary(hands: list[dict]) -> dict:
    """Generate a summary of imported hands.

    Args:
        hands: List of parsed hand dictionaries

    Returns:
        Summary dictionary with stats
    """
    if not hands:
        return {
            'total_hands': 0,
            'total_profit': 0,
            'winning_hands': 0,
            'losing_hands': 0,
            'breakeven_hands': 0,
            'stakes': [],
            'date_range': None,
        }

    total_profit = sum(h.get('result', 0) for h in hands)
    winning = sum(1 for h in hands if h.get('result', 0) > 0)
    losing = sum(1 for h in hands if h.get('result', 0) < 0)
    breakeven = len(hands) - winning - losing

    stakes = list(set(h.get('stake', 'Unknown') for h in hands))

    dates = [h.get('date') for h in hands if h.get('date')]
    if dates:
        dates.sort()
        date_range = f"{dates[0][:10]} to {dates[-1][:10]}"
    else:
        date_range = None

    return {
        'total_hands': len(hands),
        'total_profit': round(total_profit, 2),
        'winning_hands': winning,
        'losing_hands': losing,
        'breakeven_hands': breakeven,
        'win_rate': round(winning / len(hands) * 100, 1) if hands else 0,
        'stakes': stakes,
        'date_range': date_range,
    }
