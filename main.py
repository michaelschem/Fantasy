import os
import pickle
import logging
import datetime
from models import Game, TradeSuggestion

logging.getLogger().setLevel(logging.INFO)


# game = Game()
# dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# date = pickle.dump(game, open(f"pickles/game {dt}.pk", "wb"))

saved_games = os.listdir("pickles")
saved_games.sort(key=lambda x: os.path.getmtime(f"pickles/{x}"))

game = pickle.load(open(f"pickles/{saved_games[-1]}", "rb"))


trade_suggestion = TradeSuggestion(game)
best_trade = trade_suggestion.find_trade()

if best_trade:
    my_player, other_player, other_team = best_trade
    print(f"Suggested Trade: Your {my_player.name} for {other_team.name}'s {other_player.name}")