"""
Automated Opponent Tagging Engine.

Auto-classifies opponents based on statistical thresholds
using behavioral patterns from poker theory.
"""

from typing import Optional


# Tag definitions with rules and descriptions
TAG_DEFINITIONS = {
    'whale': {
        'description': 'Loose-passive fish. Calls too much, rarely raises.',
        'color': '#27AE60',  # Green - profitable target
        'priority': 1,
    },
    'nit': {
        'description': 'Tight-aggressive. Only plays premium hands.',
        'color': '#3498DB',  # Blue - avoid without strong hands
        'priority': 2,
    },
    'lag': {
        'description': 'Loose-aggressive. Plays many hands aggressively.',
        'color': '#E74C3C',  # Red - dangerous opponent
        'priority': 3,
    },
    'tag': {
        'description': 'Tight-aggressive. Standard solid player.',
        'color': '#9B59B6',  # Purple - competent
        'priority': 4,
    },
    'maniac': {
        'description': 'Hyper-aggressive. Raises everything.',
        'color': '#E74C3C',  # Red - volatile
        'priority': 5,
    },
    'calling_station': {
        'description': 'Calls everything, never folds.',
        'color': '#27AE60',  # Green - value bet relentlessly
        'priority': 6,
    },
    'foldy': {
        'description': 'Folds to aggression too often.',
        'color': '#27AE60',  # Green - bluff target
        'priority': 7,
    },
    'passive': {
        'description': 'Rarely raises, prefers calling.',
        'color': '#F39C12',  # Orange - bet for value
        'priority': 8,
    },
    'aggro': {
        'description': 'Highly aggressive postflop.',
        'color': '#E74C3C',  # Red - be careful
        'priority': 9,
    },
    'limper': {
        'description': 'Frequently open-limps preflop.',
        'color': '#27AE60',  # Green - iso-raise
        'priority': 10,
    },
    'short_stack': {
        'description': 'Plays with reduced stack (ratholing?).',
        'color': '#95A5A6',  # Gray - adjust sizing
        'priority': 11,
    },
    'reg': {
        'description': 'Regular player. Plays solid fundamentals.',
        'color': '#9B59B6',  # Purple - table select away
        'priority': 12,
    },
    'unknown': {
        'description': 'Insufficient data to classify.',
        'color': '#95A5A6',  # Gray
        'priority': 99,
    },
}


def auto_tag(stats: dict, opponent: Optional[dict] = None) -> list[str]:
    """
    Automatically classify an opponent based on statistical thresholds.

    Uses poker theory-based rules to assign behavioral tags.

    Args:
        stats: Calculated stats dict with keys like:
            - vpip: float (0-100)
            - pfr: float (0-100)
            - af: float (aggression factor)
            - three_bet: float (0-100)
            - hands_played: int
        opponent: Optional full opponent dict for additional context

    Returns:
        List of applicable tag strings, sorted by priority

    Example:
        >>> stats = {'vpip': 45, 'pfr': 8, 'af': 0.5, 'hands_played': 100}
        >>> auto_tag(stats)
        ['whale', 'passive', 'limper']
    """
    tags = []
    hands = stats.get('hands_played', 0)

    # Need minimum sample size for reliable tagging
    if hands < 10:
        return ['unknown']

    # Extract stats with defaults
    vpip = stats.get('vpip', 0)
    pfr = stats.get('pfr', 0)
    af = stats.get('af', 0)
    three_bet = stats.get('three_bet', 0)

    # Calculate derived stats
    limp_rate = vpip - pfr if vpip > pfr else 0

    # =========================================
    # Primary Player Type Classification
    # =========================================

    # Whale: Loose-passive (calls too much, rarely raises)
    # VPIP > 40% AND PFR < 10% = passive fish
    if vpip > 40 and pfr < 10:
        tags.append('whale')

    # Nit: Tight-aggressive but VERY tight
    # VPIP < 20% AND plays aggressively when in
    elif vpip < 20 and af > 2:
        tags.append('nit')

    # LAG: Loose-aggressive (plays many hands, raises often)
    elif vpip > 30 and pfr > 20 and af > 2:
        tags.append('lag')

    # TAG: Tight-aggressive (solid winning style)
    elif 18 <= vpip <= 28 and 12 <= pfr <= 22 and af >= 1.5:
        tags.append('tag')

    # Maniac: Hyper-aggressive
    elif pfr > 30 and af > 4:
        tags.append('maniac')

    # Calling Station: Loose-passive extreme
    elif vpip > 50 and pfr < 8:
        tags.append('calling_station')

    # =========================================
    # Secondary Behavioral Tags
    # =========================================

    # Foldy: Folds to 3-bets too often (exploitable)
    # This would need fold_to_3bet stat which we may not have
    # Using low 3-bet frequency as proxy for foldiness
    if three_bet < 3 and pfr > 10:
        tags.append('foldy')

    # Passive: Low aggression factor
    if af < 1.0 and vpip > 20:
        tags.append('passive')

    # Aggro: High aggression factor
    if af > 3.0:
        tags.append('aggro')

    # Limper: High limp rate (VPIP - PFR spread)
    if limp_rate > 15:
        tags.append('limper')

    # Reg: Solid stats suggesting experienced player
    if 22 <= vpip <= 28 and 15 <= pfr <= 22 and 2 <= af <= 3:
        if 'tag' not in tags:
            tags.append('reg')

    # =========================================
    # Sample Size Considerations
    # =========================================

    # With small sample, add uncertainty marker
    if hands < 50:
        if 'unknown' not in tags and len(tags) == 0:
            tags.append('unknown')

    # Sort by priority
    tags = sorted(tags, key=lambda t: TAG_DEFINITIONS.get(t, {}).get('priority', 50))

    return tags if tags else ['unknown']


def get_tag_display(tag: str) -> dict:
    """
    Get display info for a tag.

    Args:
        tag: Tag string

    Returns:
        Dict with color, description, priority
    """
    return TAG_DEFINITIONS.get(tag, {
        'description': 'Unknown tag',
        'color': '#95A5A6',
        'priority': 50,
    })


def get_tag_html(tags: list[str]) -> str:
    """
    Generate HTML badges for a list of tags.

    Args:
        tags: List of tag strings

    Returns:
        HTML string with styled badges
    """
    if not tags:
        return ""

    badges = []
    for tag in tags[:3]:  # Limit to 3 tags
        info = get_tag_display(tag)
        badge = (
            f'<span style="background-color: {info["color"]}; '
            f'color: white; padding: 2px 8px; border-radius: 12px; '
            f'font-size: 11px; font-weight: 500; margin-right: 4px;">'
            f'{tag.upper()}</span>'
        )
        badges.append(badge)

    return ''.join(badges)


def get_exploitation_tips(tags: list[str]) -> list[str]:
    """
    Generate exploitation tips based on opponent tags.

    Args:
        tags: List of opponent tags

    Returns:
        List of actionable tips
    """
    tips = []

    if 'whale' in tags or 'calling_station' in tags:
        tips.append("💰 Value bet relentlessly - they call too much")
        tips.append("🚫 Don't bluff - they won't fold")
        tips.append("📈 Bet larger for value (1.2x pot+)")

    if 'nit' in tags:
        tips.append("⚠️ Respect their raises - they have it")
        tips.append("🎯 Steal their blinds aggressively")
        tips.append("🏃 Fold to their 3-bets without premiums")

    if 'lag' in tags:
        tips.append("🎣 Trap with strong hands")
        tips.append("📉 Tighten your 3-bet range")
        tips.append("⚡ Be willing to go to war with top pair+")

    if 'foldy' in tags:
        tips.append("🎯 3-bet them liberally")
        tips.append("💨 C-bet bluff frequently")
        tips.append("🔥 Apply maximum pressure postflop")

    if 'passive' in tags:
        tips.append("📊 Bet for thin value")
        tips.append("🎟️ Take free cards when weak")
        tips.append("⚠️ Respect their raises")

    if 'aggro' in tags:
        tips.append("🎣 Let them bluff into you")
        tips.append("📉 Widen your calling range")
        tips.append("🎯 Check-raise for value")

    if 'limper' in tags:
        tips.append("📈 Iso-raise to 4-5x")
        tips.append("🎯 Target them in position")
        tips.append("💰 They have a capped range")

    if 'maniac' in tags:
        tips.append("🧘 Stay patient - let them hang themselves")
        tips.append("📉 Tighten up but call more")
        tips.append("🎣 Trap with monsters")

    if 'reg' in tags or 'tag' in tags:
        tips.append("⚔️ This is a competent player")
        tips.append("🎯 Focus on softer targets")
        tips.append("📊 Play fundamentally sound")

    if 'unknown' in tags:
        tips.append("👀 Gather more data before exploiting")
        tips.append("📊 Play ABC poker until reads develop")

    return tips[:5]  # Limit to 5 tips


def analyze_opponent_profile(opponent: dict, stats: dict) -> dict:
    """
    Generate comprehensive opponent profile with tags and tips.

    Args:
        opponent: Opponent dict from data_loader
        stats: Calculated stats from calculate_opponent_stats

    Returns:
        Profile dict with tags, tips, and summary
    """
    tags = auto_tag(stats, opponent)
    tips = get_exploitation_tips(tags)

    # Generate summary
    primary_tag = tags[0] if tags else 'unknown'
    tag_info = get_tag_display(primary_tag)

    hands = stats.get('hands_played', 0)
    confidence = 'High' if hands > 200 else 'Medium' if hands > 50 else 'Low'

    return {
        'tags': tags,
        'tags_html': get_tag_html(tags),
        'tips': tips,
        'primary_type': primary_tag,
        'primary_description': tag_info['description'],
        'primary_color': tag_info['color'],
        'confidence': confidence,
        'hands_played': hands,
        'stats': stats,
        'summary': f"{primary_tag.upper()}: {tag_info['description']}" if primary_tag != 'unknown' else "Need more hands",
    }
