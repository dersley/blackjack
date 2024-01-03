import numpy as np
from .deck_builder import CARD_VALUES

def calculate_hand_total(hand: list[tuple]):
    total = 0
    aces = 0
    for rank, suit in hand:
        if rank == 'Ace':
            total += 11
            aces += 1
        else:
            total += CARD_VALUES[rank]
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def compare_hands(dealer_hand_total, player_hand_total):
    
    if player_hand_total > 21:
        return 'Lose'
    elif dealer_hand_total > 21:
        return 'Win'
    elif player_hand_total > dealer_hand_total:
        return 'Win'
    elif dealer_hand_total > player_hand_total:
        return 'Lose'
    else:
        return 'Draw'
    

def calculate_percentiles(data: np.ndarray, confidence=95):
    """
    Calculate the confidence interval percentiles for a slice of simdata
    """

    lower = np.percentile(data, (50 - confidence / 2))
    mid = np.percentile(data, 50)
    upper = np.percentile(data, (50 + confidence / 2))

    return lower, mid, upper

def round_to_minimum_bet(bet, minimum_bet):

    remainder = bet % minimum_bet
    if remainder < minimum_bet / 2:
        return bet - remainder
    else:
        return bet - remainder + (minimum_bet)

