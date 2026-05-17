from decursio.signals.imbalance import top_of_book_imbalance


def test_top_of_book_imbalance_symmetric() -> None:
    assert top_of_book_imbalance(100, 100) == 0.0


def test_top_of_book_imbalance_bid_heavy() -> None:
    assert top_of_book_imbalance(300, 100) == 0.5


def test_top_of_book_imbalance_zero_depth() -> None:
    assert top_of_book_imbalance(0, 0) == 0.0
