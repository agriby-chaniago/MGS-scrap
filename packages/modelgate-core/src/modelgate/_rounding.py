"""Numeric semantics per specs/mgs/MGS-1.0.md §6.

Python's builtin round() uses round-half-to-even (banker's rounding),
which the spec explicitly forbids (§6.2) — two conformant implementations
that both "round to 4 decimal places" can still disagree at a boundary
value if one uses round-half-to-even and the other round-half-away-from-
zero. This module is the one place that rounding happens, so there is
exactly one behavior to get right.
"""

from decimal import Decimal, ROUND_HALF_UP

_QUANT = Decimal("0.0001")


def round4(value: float) -> float:
    """Round-half-away-from-zero to exactly 4 decimal places."""
    # Decimal(str(value)), not Decimal(value) directly — the latter
    # would quantize the float's exact binary representation (e.g.
    # 0.1 as a float is actually 0.1000000000000000055511151231257827),
    # which defeats the point of specifying decimal rounding at all.
    return float(Decimal(str(value)).quantize(_QUANT, rounding=ROUND_HALF_UP))
