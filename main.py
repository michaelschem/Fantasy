import os
import pickle
import logging
import datetime
from models import Game, TradeSuggestion

logging.getLogger().setLevel(logging.INFO)

new = False

if new:
    game = Game()
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date = pickle.dump(game, open(f"pickles/game {dt}.pk", "wb"))
else:
    saved_games = os.listdir("pickles")
    saved_games.sort(key=lambda x: os.path.getmtime(f"pickles/{x}"))
    game = pickle.load(open(f"pickles/{saved_games[-1]}", "rb"))

trade_suggestion = TradeSuggestion(game)
best_trades = trade_suggestion.find_trade()
trade_suggestion.print_best_trades(best_trades)

# print(game.me.build_best_team())
