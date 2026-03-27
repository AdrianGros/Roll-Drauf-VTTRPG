import random
import re


def roll_dice(dice_string: str) -> dict[str, int | list[int] | str]:
    match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_string)
    if not match:
        return {'error': 'Invalid dice format. Use e.g., 1d20+5'}

    num = int(match.group(1))
    sides = int(match.group(2))
    mod = int(match.group(3)) if match.group(3) else 0

    rolls = [random.randint(1, sides) for _ in range(num)]
    total = sum(rolls) + mod
    return {'rolls': rolls, 'modifier': mod, 'total': total}
