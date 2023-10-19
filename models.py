import logging
import os
from collections import defaultdict

from heapq import heappush, heappop
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time


class Player:
    def __init__(self, name, position, proj_pts, start_pct, buy_week, rank=None):
        logging.info(f"Initializing Player {name}")
        self.name = name
        self.position = position
        self.proj_pts = None if proj_pts == "-" else float(proj_pts)
        self.start_pct = start_pct
        self.buy_week = buy_week
        self.rank = rank
        self.type = name.split("-")[-1].strip()

    def __repr__(self) -> str:
        return self.name

    @property
    def is_bench(self):
        return self.position == "BN"

    @property
    def contributing_points(self):
        if self.is_bench:
            return 0
        return self.proj_pts

    @classmethod
    def from_tr(cls, tr):
        if tr.text == "":
            return None
        tas = [i.text for i in tr.find_elements(By.CLASS_NAME, "Ta-end")]
        return cls(
            name=tr.find_element(By.CLASS_NAME, "ysf-player-name").text,
            position=tr.find_element(By.CLASS_NAME, "pos-label").text,
            proj_pts=tas[2],
            start_pct=tas[3],
            buy_week=tas[0],
        )


class Team:
    def __init__(
        self, rank, name, wins, losses, ties, pf, pa, streak, waiver, moves, url
    ) -> None:
        logging.info(f"Initializing Team {name}")
        self.rank = rank
        self.name = name
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.pf = pf
        self.pa = pa
        self.streak = streak
        self.waiver = waiver
        self.moves = moves

        self.url = url
        self.is_me = name == "michael's Okay Team"
        self.players = []

    def __repr__(self) -> str:
        return self.name

    @property
    def score(self):
        return sum(
            [
                float(player.proj_pts)
                for player in self.players
                if not player.is_bench and player.proj_pts is not None
            ]
        )

    @staticmethod
    def from_tr(tr):
        args = []
        try:
            for td in tr.find_elements(By.TAG_NAME, "td"):
                args.append(td.text)
            url = (
                tr.find_elements(By.TAG_NAME, "td")[1]
                .find_element(By.TAG_NAME, "a")
                .get_property("href")
            )
            return args[:2] + args[2].split("-") + args[3:] + [url]
        except (NoSuchElementException, StaleElementReferenceException):
            return None

    def get_players(self, driver):
        driver.get(self.url)
        table = driver.find_element(By.ID, "statTable0")
        self.players = []
        for tr in table.find_elements(By.TAG_NAME, "tr")[2:]:
            player = Player.from_tr(tr)
            if player is not None:
                self.players.append(player)
        return self.players

    def build_best_team(self, players=None):
        if players is None:
            players = self.players
        best_team = defaultdict(list)

        # Group players by position
        players_by_position = defaultdict(list)
        for player in players:
            if player is not None and player.proj_pts is not None:
                players_by_position[player.type].append(player)

        # Sort players within each position group by projected points
        for position, players in players_by_position.items():
            players.sort(key=lambda x: x.proj_pts, reverse=True)

        # Select best players for each position
        best_team["QB"] = players_by_position["QB"][:1]
        best_team["WR"] = players_by_position["WR"][:2]
        best_team["RB"] = players_by_position["RB"][:2]
        best_team["TE"] = players_by_position["TE"][:1]

        # Flex position can be WR/RB/TE
        remaining_players = (
            players_by_position["WR"][2:]
            + players_by_position["RB"][2:]
            + players_by_position["TE"][1:]
        )
        remaining_players.sort(key=lambda x: x.proj_pts, reverse=True)
        best_team["FLEX"] = remaining_players[:1]

        score = sum(
            [player.proj_pts for sublist in best_team.items() for player in sublist[1]]
        )

        return best_team, score


class Game:
    def __init__(self) -> None:
        logging.info("Initializing Game")
        chrome_options = Options()
        chrome_options.add_argument("--headless")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://login.yahoo.com/")

        email_elem = driver.find_element(value="username", by=By.NAME)
        email_elem.send_keys("michaelschem@yahoo.com")
        email_elem.send_keys(Keys.RETURN)

        # Pause to wait for next page to load
        time.sleep(2)

        # Find password field, input password, and submit
        password_elem = driver.find_element(value="password", by=By.NAME)
        password_elem.send_keys(os.getenv("pw"))
        password_elem.send_keys(Keys.RETURN)

        # Pause to wait for login to complete
        time.sleep(2)

        driver.get("https://football.fantasysports.yahoo.com/f1/845768")

        table = driver.find_element(By.ID, "standingstable")

        self.teams = []
        for tr in table.find_elements(By.TAG_NAME, "tr")[1:]:
            args = Team.from_tr(tr)
            team = Team(*args)
            self.teams.append(team)

        for team in self.teams:
            team.get_players(driver)

    @property
    def me(self):
        return next(team for team in self.teams if team.is_me)


class TradeSuggestion:
    def __init__(self, game):
        self.game = game
        self.my_team = next(team for team in self.game.teams if team.is_me)

    @staticmethod
    def calculate_team_score(team):
        score = 0
        for player in team.players:
            if player is None or player.proj_pts is None or player.position == "BN":
                continue
            score += float(player.proj_pts)
        return score

    def find_trade(self):
        trades = []

        _, my_initial_score = self.my_team.build_best_team()

        for team in self.game.teams:
            if team.is_me:
                continue

            _, other_initial_score = team.build_best_team()

            for my_player in self.my_team.players:
                if my_player is None or my_player.proj_pts is None:
                    continue

                for other_player in team.players:
                    if other_player is None or other_player.proj_pts is None:
                        continue

                    # Simulate the trade for both teams
                    my_new_players = [
                        p for p in self.my_team.players if p != my_player
                    ] + [other_player]
                    other_new_players = [
                        p for p in team.players if p != other_player
                    ] + [my_player]

                    _, my_new_score = self.my_team.build_best_team(my_new_players)
                    _, other_new_score = team.build_best_team(other_new_players)

                    my_improvement = my_new_score - my_initial_score
                    other_improvement = other_new_score - other_initial_score

                    if my_improvement > 0 or other_improvement > 0:
                        combined_improvement = my_improvement + other_improvement
                        trades.append(
                            (
                                my_player,
                                other_player,
                                team,
                                my_improvement,
                                other_improvement,
                                combined_improvement,
                            )
                        )

        trades.sort(key=lambda x: x[-1], reverse=True)
        return trades[:10]

    def print_best_trades(self, best_trades):
        for best_trade in best_trades:
            (
                my_player,
                other_player,
                other_team,
                my_improvement,
                other_improvement,
                combined_improvement,
            ) = best_trade
            print(
                f"{my_player.name}({my_player.proj_pts}) ->"
                f" {other_team.name} - {other_player.name}({other_player.proj_pts})"
                f" ({my_improvement}) - {other_improvement} - {combined_improvement}"
            )
