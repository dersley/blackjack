import random

from . import card_counting
from . import deck_builder
from . import utils


class Dealer:
    def __init__(self, num_decks=1):
        self.num_decks = num_decks
        self.deck = self.build_deck()
        self.running_count = 0
        self.total_count = 0

        self.hand = []
        self.is_bust = False
        self.round_total = 0

    def build_deck(self):
        deck = [
            (rank, suit) for suit in deck_builder.SUITS for rank in deck_builder.RANKS
        ]
        self.deck = deck * self.num_decks
        return self.deck

    def shuffle_deck(self):
        # Shuffle the combined deck
        random.shuffle(self.deck)

        # Reset the running count
        self.running_count = 0

    def deal_card(self):
        # Deal top card
        card = self.deck.pop()

        # Add card value to running count
        self.running_count = card_counting.adjust_count(self.running_count, card)
        self.total_count = self.running_count / self.remaining_decks()

        return card

    def remaining_decks(self):
        remaining_decks = self.num_decks - int(len(self.deck) / 52)

        return remaining_decks

    def play_round(self):
        """
        Takes current hand and either hits or stays depending on house rules
        """

        # Get total from initially dealt cards
        total = utils.calculate_hand_total(self.hand)

        while total <= 17:
            # Deal self a card
            self.hand.append(self.deal_card())

            # Recalculate total
            total = utils.calculate_hand_total(self.hand)

            if total > 21:
                self.is_bust = True
                break

        # Store final total from round
        self.round_total = total
