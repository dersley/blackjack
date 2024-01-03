from .deck_builder import HIGH_CARDS, LOW_CARDS

def adjust_count(running_count: int, card: tuple):
    """
    Adjusts a running count of the cards in play
    """

    rank = card[0]
    if rank in LOW_CARDS:
        running_count += 1
    elif rank in HIGH_CARDS:
        running_count -= 1

    return running_count