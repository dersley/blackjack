
from . import basic_strategy
from . import deck_builder
from . import utils


class Player:
    def __init__(self, bank, game, dynamic_betting=True, card_counter=True):
        self.bank = bank
        self.game = game

        # Default bet of 2% of starting bank balance
        self.default_bet = self.bank / 50
        
        # Set whether the player is counting cards
        self.card_counter = card_counter

        # If dynamic betting, the bet will be recalculated each round
        self.dynamic_betting = dynamic_betting

        self.hand = []

    def draw_card(self):
        card = self.game.dealer.deal_card()
        self.hand.append(card)

    def place_bet(self):
        """
        Place a bet for an individual hand (including splits).
        If dynamic betting, the default bet will be a proportion of the current bank balance.

        If player bank is less than game minimum, bet is set to zero
        """

        # If player can't make minimum bet, return 0
        if self.bank < self.game.minimum_bet:
            return 0

        # Check the game's total count if the player is a card counter, and change bet accordingly
        if self.card_counter:
            bet = self.place_card_counter_bet()
        
        # Set a bet based on the player's remaining bank if they are betting dynamically
        elif self.dynamic_betting:
            bet = self.bank / 50

        # Otherwise just play the default bet every round
        else:
            bet = self.default_bet

        # Return bet as an even divisor of minimum bet
        return utils.round_to_minimum_bet(bet, self.game.minimum_bet)

    def place_card_counter_bet(self, betting_spread=10):

        # Get the game's total count
        total_count = self.game.dealer.total_count
        
        # Calculate the minimum and maximum bet
        min_bet = self.game.minimum_bet
        ground_bet = self.bank / 50
        max_bet = ground_bet * betting_spread
        
        # Adjust bet based on total count
        if total_count <= 0:
            # Stay in the game with a minimum bet
            bet = min_bet
        else:
            # Increase bet linearly with total_count, but do not exceed max_bet
            bet = min(ground_bet * total_count, max_bet)

        # Return the calculated bet
        return bet

    def is_twin(self, hand):
        """
        Returns True if the player's hand is a twin (same rank)
        """

        if len(hand) != 2:
            return False
        
        first_card, second_card = hand

        first_rank = first_card[0]
        second_rank = second_card[0]

        return first_rank == second_rank
    
    def is_soft(self, hand):
        """
        Return True if the player's hand contains one Ace (two possible totals)

        Only returns true in 2 card hands
        """

        if len(hand) != 2:
            return False
        
        # Return false if both cards are aces
        if all(rank == 'Ace' for rank, _ in hand):
            return False

        soft = any(rank == 'Ace' for rank, _ in hand)

        return soft
    
    def find_soft_index(self, hand):

        for index, (rank, _) in enumerate(hand):
            if rank != 'Ace':
                return index

    def hit(self, hand):
        """
        Append a new card to the hand
        """

        hand.append(self.game.dealer.deal_card())

        return hand

    def double_down(self, hand, current_bet):
        """
        Double the current bet and receive one more card, ending the round.
        """

        new_bet = current_bet * 2

        hand.append(self.game.dealer.deal_card())

        return hand, new_bet
    
    def play_round(self):
        """
        Play out the full round from an initial starting bet
        """

        # Round totals and bets are in lists to account for split hands. Payouts are handled by the Game with resolve_round()
        self.round_total = []
        self.round_bet = []

        # Place initial round bet
        self.initial_bet = self.place_bet()

        # Get game split limit
        split_limit = self.game.split_limit

        # Play hands
        self.play_hand(self.hand, split_limit=split_limit)


    def play_hand(self, hand, split_count=0, split_limit=3):
        """
        Takes current hand and plays Basic Strategy

        When a twin is encountered (while splitting is allowed) the function call itself to play the split hands.
        On a Hit, the function calls itself to continue the play.
        """

        # Set the current bet
        current_bet = self.initial_bet
        
        # Check dealer's visible card
        dealer_upcard = deck_builder.CARD_VALUES[self.game.dealer.hand[0][0]]

        # Calculate hand total
        hand_total = utils.calculate_hand_total(hand)

        # Check if hand is a twin and split if allowable
        if split_count < split_limit and self.is_twin(hand):
            # Get hand rank
            twin_rank = deck_builder.CARD_VALUES[hand[0][0]]

            # Implement twin strategy
            if basic_strategy.PAIR_SPLITTING[(str(twin_rank), str(dealer_upcard))]:
                split_count += 1

                # Draw first new hand and place bet
                first_hand = [hand[0], self.game.dealer.deal_card()]
                self.initial_bet = self.place_bet()
                self.play_hand(first_hand, split_count)

                # Draw second hand and place bet
                second_hand = [hand[1], self.game.dealer.deal_card()]
                self.initial_bet = self.place_bet()
                self.play_hand(second_hand, split_count)

                return
            
        # Return if on blackjack with a bonus to winnings
        if hand_total == 21:
            self.round_total.append(hand_total)
            self.round_bet.append(current_bet * 1.5)
            return
        
        # Return on any hand over 20
        elif hand_total >= 20:
            self.round_total.append(hand_total)
            self.round_bet.append(current_bet)
            return

        # Check if hand is a soft or hard total
        if self.is_soft(hand):
            self.soft_total_strategy(hand, dealer_upcard, current_bet, split_count)

        # Play out hard total strategy
        else:
            self.hard_total_strategy(hand, dealer_upcard, current_bet, split_count)


    def soft_total_strategy(self, hand, dealer_upcard, current_bet, split_count):

        # Calculate hand total
        hand_total = utils.calculate_hand_total(hand)
        
        # Get the non Ace total
        soft_index = self.find_soft_index(hand)
        soft_total = deck_builder.CARD_VALUES[hand[soft_index][0]]
        strategy = basic_strategy.SOFT_TOTALS[str(soft_total), str(dealer_upcard)]

        # If 'S' stay and end round
        if strategy == 'S':
            self.round_total.append(hand_total)
            self.round_bet.append(current_bet)
            return
        
        # Double down on 'D', draw one card and end round
        if strategy == 'D' or strategy == 'DS':
            hand, new_bet = self.double_down(hand, current_bet=current_bet)

            # Calculate hand total after double down
            new_hand_total = utils.calculate_hand_total(hand)
            self.round_total.append(new_hand_total)
            self.round_bet.append(new_bet)
            return

        elif strategy == 'H':
            hand = self.hit(hand)

            new_hand_total = utils.calculate_hand_total(hand)
            
            if new_hand_total > 21:
                self.round_total.append(new_hand_total)
                self.round_bet.append(current_bet)
                return

            # Continue hand if not bust
            self.play_hand(hand, split_count)


    def hard_total_strategy(self, hand, dealer_upcard, current_bet, split_count):
        
        # Calculate hand total
        hand_total = utils.calculate_hand_total(hand)

        # Same strategy applies for any hard total lower than 8
        if hand_total < 8:
            hard_total = 8
        else:
            hard_total = hand_total

        # Always stay on a hard hand greater than 17
        if hand_total > 17:
            self.round_total.append(hand_total)
            self.round_bet.append(current_bet)
            return

        strategy = basic_strategy.HARD_TOTALS[str(hard_total), str(dealer_upcard)]

        # If 'S' stay and end round
        if strategy == 'S':
            self.round_total.append(hand_total)
            self.round_bet.append(current_bet)
            return
        
        # Double down on 'D'
        if strategy == 'D':
            hand, new_bet = self.double_down(hand, current_bet)

            # Calculate hand total after double down
            new_hand_total = utils.calculate_hand_total(hand)
            self.round_total.append(new_hand_total)
            self.round_bet.append(new_bet)
            return

        # Hit on 'H'
        elif strategy == 'H':
            hand = self.hit(hand)

            new_hand_total = utils.calculate_hand_total(hand)

            if new_hand_total > 21:
                self.round_total.append(new_hand_total)
                self.round_bet.append(current_bet)
                return

            # Continue hand if not bust
            self.play_hand(hand, split_count)





