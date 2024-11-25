import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytz
import json


def datetime_to_cron(dt):
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


season = 2025
today = datetime.now(ZoneInfo('America/New_York'))

api_key = 'a7bfde5bb651ac64e61f99c67631ef47'

url = f'https://www.basketball-reference.com/leagues/NBA_{season}_games-{today.strftime("%B").lower()}.html'
page = requests.get(url)
soup = BeautifulSoup(page.content, 'lxml')
table = soup.find('table')
while table.find_all('tr', class_ = 'thead') :
    table.find('tr', class_ = 'thead').decompose()
games = pd.read_html(str(table))[0].rename(columns = {'Start (ET)': 'Time'})
games['Home'] = [x['href'].split('/')[2] for x in table.find_all('a', href = True) if 'teams' in x['href']][1::2]
games['Away'] = [x['href'].split('/')[2] for x in table.find_all('a', href = True) if 'teams' in x['href']][0::2]
games['Date'] = pd.to_datetime(games['Date'])
games = games[pd.to_datetime(games['Date']) == pd.to_datetime(today.date())].reset_index(drop = True)
games['Time'] = (games['Date'].astype(str) + ' ' +  games['Time']).apply(lambda x: datetime.strptime(x.upper() + 'M', "%Y-%m-%d %I:%M%p"))
games['game_id'] = games['Date'].apply(lambda x: datetime.strftime(x, "%Y%m%d")) + '0' + games['Home']
games = games[['game_id', 'Date', 'Time', 'Home', 'Away']]

tmrw_utc = (today + timedelta(days = 1)).astimezone(pytz.utc)

events_response = requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/events',
                               params = {'apiKey': api_key,
                                         'commenceTimeTo': tmrw_utc.strftime('%Y-%m-%dT%H:%M:%SZ')})


events = pd.DataFrame(events_response.json()).rename(columns = {'id': 'event_id'})
events['commence_time'] = pd.to_datetime(events['commence_time'])


with open('utils/odds_tm_map.json', 'r') as file:
    odds_tm_map = json.load(file)


events['game_id'] = today.strftime("%Y%m%d") + '0' + events['home_team'].map(odds_tm_map)


games = pd.merge(games, events[['game_id', 'event_id']], on = 'game_id')

games['insert_timestamp_utc'] = datetime.now(timezone.utc)
games.to_csv('data/games.csv', index = None, mode = 'w')


execute_crons = [datetime_to_cron(t - timedelta(minutes = 30)) for t in games['Time'].unique()]

# .yml write path
yml_path = ".github/workflows/schedule_today_games.yml"  # Output workflow file

# Create the dynamic .yml file content
workflow_content = f"""name: Run Script Before NBA Games

on:
  schedule:
"""

# Add all calculated cron expressions to the workflow
for cron in execute_crons :
    workflow_content += f"    - cron: '{cron}'\n"

workflow_content += f"""
jobs:
  run_script:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

      - name: Set Up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: pip install -r requirements.txt

      - name: Run Before Game Script
        run: python run_before_game.py
"""

# Save the workflow content to a .yml file
with open(yml_path, "w") as f:
    f.write(workflow_content)

print(f"Workflow file {yml_path} created successfully!")