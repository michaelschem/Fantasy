import logging
import os

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
        self.proj_pts = None if proj_pts == '-' else float(proj_pts)
        self.start_pct = start_pct
        self.buy_week = buy_week
        self.rank = rank

    def __repr__(self) -> str:
        return self.name

    @classmethod
    def from_tr(cls, tr):
        if tr.text == '':
            return None
        tas = [i.text for i in tr.find_elements(By.CLASS_NAME, "Ta-end")]
        return cls(
            name=tr.find_element(By.CLASS_NAME, "ysf-player-name").text,
            position=tr.find_element(By.CLASS_NAME, "pos-label").text,
            proj_pts=tas[2],
            start_pct=tas[3],
            buy_week=tas[0]
        )

class Team:
    def __init__(self, rank, name, wins, losses, ties, pf, pa, streak, waiver, moves, url) -> None:
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

    @staticmethod
    def from_tr(tr):
        args = []
        try:
            for td in tr.find_elements(By.TAG_NAME, "td"):
                args.append(td.text)
            url = tr.find_elements(By.TAG_NAME, "td")[1].find_element(By.TAG_NAME, "a").get_property('href')
            return args[:2] + args[2].split('-') + args[3:] + [url]
        except (NoSuchElementException, StaleElementReferenceException):

            return None

    def get_players(self, driver):
        driver.get(self.url)
        table = driver.find_element(By.ID, "statTable0")
        self.players = []
        for tr in table.find_elements(By.TAG_NAME, "tr")[2:]:
            player = Player.from_tr(tr)
            self.players.append(player)
        return self.players


class Game:
    def __init__(self) -> None:
        logging.info("Initializing Game")
        chrome_options = Options()
        chrome_options.add_argument("--headless")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://login.yahoo.com/')

        email_elem = driver.find_element(value='username', by=By.NAME)
        email_elem.send_keys('michaelschem@yahoo.com')
        email_elem.send_keys(Keys.RETURN)

        # Pause to wait for next page to load
        time.sleep(2)

        # Find password field, input password, and submit
        password_elem = driver.find_element(value='password', by=By.NAME)
        password_elem.send_keys(os.getenv('pw'))
        password_elem.send_keys(Keys.RETURN)

        # Pause to wait for login to complete
        time.sleep(2)

        driver.get('https://football.fantasysports.yahoo.com/f1/845768')

        table = driver.find_element(By.ID, "standingstable")

        self.teams = []
        for tr in table.find_elements(By.TAG_NAME, "tr")[1:]:
            args = Team.from_tr(tr)
            team = Team(*args)
            self.teams.append(team)

        for team in self.teams:
            team.get_players(driver)


class TradeSuggestion:
    def __init__(self, game):
        self.game = game
        self.my_team = next(team for team in self.game.teams if team.is_me)

    def find_trade(self):
        best_trade = None
        best_diff = 0

        for team in self.game.teams:
            if team.is_me:
                continue

            for my_player in self.my_team.players:
                if my_player.proj_pts is None:
                    continue

                for other_player in team.players:
                    if other_player.proj_pts is None or my_player.position != other_player.position:
                        continue

                    my_pts = float(my_player.proj_pts)
                    other_pts = float(other_player.proj_pts)

                    diff = other_pts - my_pts
                    if diff > best_diff:
                        best_diff = diff
                        best_trade = (my_player, other_player, team)

        return best_trade
