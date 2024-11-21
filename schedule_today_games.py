import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def datetime_to_cron(dt):
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


season = 2025
today = datetime.now(ZoneInfo('America/New_York'))



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
games['insert_timestamp_utc'] = datetime.now(timezone.utc)
games.to_csv('data/games.csv', index = None, mode = 'a')


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
# with open(yml_path, "w") as f:
#     f.write(workflow_content)

print(f"Workflow file {yml_path} created successfully!")