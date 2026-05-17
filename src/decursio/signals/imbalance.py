"""Order book imbalance from bid and ask size at the top of book."""

from __future__ import annotations


def top_of_book_imbalance(bid_size: int, ask_size: int) -> float:
    """
    Normalized imbalance in [-1, 1].

    Values near +1 indicate more size on the bid; near -1, more on the ask.
    When both sizes are zero, returns 0.0.
    """
    total = bid_size + ask_size
    if total <= 0:
        return 0.0
    return (bid_size - ask_size) / total
