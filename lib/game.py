import matplotlib.pyplot as plt
import numpy as np

from . import utils
from .dealer import Dealer
from .player import Player


class Game:
    def __init__(
        self,
        num_players: int,
        player_bank: int = 10_000,
        num_decks: int = 1,
        split_limit: int = 3,
        minimum_bet: int = 10,
        shuffle_trigger: float = 0.25,
    ):
        self.dealer = Dealer(num_decks)
        self.num_decks = num_decks
        self.num_players = num_players
        self.player_bank = player_bank

        self.minimum_bet = minimum_bet
        self.split_limit = split_limit
        self.shuffle_trigger = shuffle_trigger

        # Create players
        self.players = self.create_players()

        # Shuffle cards
        self.dealer.shuffle_deck()

    def create_players(self):
        self.players = []
        for i in range(self.num_players):
            # First player is a card counter
            if i == 0:
                self.players.append(
                    Player(bank=self.player_bank, game=self, card_counter=True)
                )

            # Second player just bets minimum every game
            elif i == 1:
                self.players.append(
                    Player(
                        bank=self.player_bank,
                        game=self,
                        card_counter=False,
                        dynamic_betting=False,
                    )
                )

            else:
                # Other players play basic strategy with proportional betting
                self.players.append(
                    Player(bank=self.player_bank, game=self, card_counter=False)
                )

        return self.players

    def check_deck(self):
        # Check if deck needs refresh
        remaining_cards = len(self.dealer.deck)
        shuffle_limit = self.shuffle_trigger * (52 * self.num_decks)

        if remaining_cards <= shuffle_limit:
            self.dealer.build_deck()
            self.dealer.shuffle_deck()

    def clear_table(self):
        for player in self.players:
            player.hand = []
            player.round_total = []
            player.round_bet = []

        self.dealer.hand = []
        self.dealer.round_total = []

    def restart_game(self):
        """
        Restart the game, replenishing each of the player bank balances
        """

        for player in range(self.num_players):
            self.players[player].bank = self.player_bank

    def deal_round(self):
        """
        Check to see if deck needs a shuffle.

        Deal each player and the dealer two cards each.
        """

        # Check deck level, rebuild and shuffle if it is below limit
        self.check_deck()

        # Players
        for player in self.players:
            player.hand.append(self.dealer.deal_card())
            player.hand.append(self.dealer.deal_card())

        # Dealer
        self.dealer.hand.append(self.dealer.deal_card())
        self.dealer.hand.append(self.dealer.deal_card())

    def play_round(self):
        """
        Each player plays their hand, followed by the dealer
        """

        for player in self.players:
            player.play_round()

        self.dealer.play_round()

    def resolve_round(self):
        """
        Pay out all players based on their final totals
        """

        for player in self.players:
            for i, hand in enumerate(player.round_total):
                outcome = utils.compare_hands(hand, self.dealer.round_total)

                if outcome == "Win":
                    # Pay the bet value to the player bank
                    player.bank += player.round_bet[i]
                if outcome == "Lose":
                    # Remove the bet value from the player bank
                    player.bank -= player.round_bet[i]
                    # If player has overbet, set bank to zero
                    if player.bank < 0:
                        player.bank = 0
                if outcome == "Draw":
                    # Do nothing on a draw
                    pass

        self.clear_table()

    def simulate_game(self, rounds=200, sims=5000):
        """
        Simulate a game of a given number of rounds.

        Return:
        a 3D array of shape (sims, rounds, players)
        a 2D array of card counts (running and total) of shape (sims, rounds, 2)
        """

        simdata = np.zeros((sims, rounds, self.num_players))
        count_data = np.zeros((sims, rounds, 2))
        for i, sim in enumerate(simdata):
            # Restart the bank balances after each sim
            self.restart_game()

            for round in range(rounds):
                # Record counts at start of round
                count_data[i, round, 0] = self.dealer.running_count
                count_data[i, round, 1] = self.dealer.total_count

                # Track player earnings at start of round
                for player in range(self.num_players):
                    # Write the player's bank to the simdata
                    simdata[i, round, player] = self.players[player].bank

                # Play round
                self.deal_round()
                self.play_round()

                # Pay out hands
                self.resolve_round()

        return simdata, count_data

    def plot_simdata(
        self,
        player_index=0,
        simdata=None,
        plot_sims=True,
        confidence=95,
        log_scale=False,
        figsize=(16, 4),
    ):
        # Simulate default simdata if none is passed
        if simdata is None:
            simdata = self.simulate_game()

        # Get rounds and players from the shape of the simdata
        num_rounds = simdata.shape[1]

        # Slice simdata to just the desired player array of shape (sims, rounds)
        player_data = simdata[:, :, player_index]

        # Calculate percentiles for each player in array of shape (rounds, 3)
        percentiles = np.zeros((num_rounds, 3))
        for round in range(num_rounds):
            round_simdata = player_data[:, round]
            percentiles[round, :] = utils.calculate_percentiles(
                round_simdata, confidence=confidence
            )

        fig, ax = plt.subplots(figsize=figsize)

        x = np.arange(num_rounds)

        # Plot subset of sims
        if plot_sims:
            for i in range(simdata.shape[0] // 4):
                ax.plot(x, player_data[i], alpha=0.2, lw=1)

        # Plot the percentile values
        ax.plot(x, percentiles[:, 0], color="red", lw=1)
        ax.plot(x, percentiles[:, 1], color="red", lw=2)
        ax.plot(x, percentiles[:, 2], color="red", lw=1)

        ax.fill_between(
            x, y1=percentiles[:, 0], y2=percentiles[:, 2], color="red", alpha=0.25
        )

        if log_scale:
            ax.set_yscale("log")

        else:
            ax.set_ylim(0, 20_000)

        ax.set_xlim(0)
        ax.set_xlabel("Rounds")
        ax.set_ylabel("Bank Balance ($)")

        # Get player info for the plot title
        dynamic_better = self.players[player_index].dynamic_betting
        card_counter = self.players[player_index].card_counter
        default_bet = self.players[player_index].default_bet

        if dynamic_better:
            bet_percentage = (default_bet / self.player_bank) * 100

        # Set title based on type of player
        if card_counter:
            title = f"Player Balance: Card Counting, {bet_percentage :.0f}% Bet"
        elif dynamic_better:
            title = f"Player Balance: Basic Strategy, {bet_percentage :.0f}% Bet"
        else:
            title = f"Player Balance: Basic Strategy, ${default_bet :.0f} Bet"

        ax.set_title(title)

        plt.show()
