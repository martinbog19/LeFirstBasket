import pandas as pd
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import requests
import os
import json

from helpers.email import send_email


if os.getenv("GITHUB_ACTIONS") == "true" :
  api_key = os.getenv('ODDS_API_KEY')
else :
  with open('secrets/odds_api_key.txt') as f:
    api_key = f.read()

if os.getenv("GITHUB_ACTIONS") == "true" :
  start_time = int(os.getenv("START_TIME"))
else :
  start_time = 19

with open('utils/odds_tm_map.json', 'r') as f :
  odds_tm_map = json.load(f)

games = pd.read_csv('data/games.csv')

# Store subset of games in the next 30 minutes
now = datetime.now((ZoneInfo('US/Eastern')))
today_dt = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
print(now.strftime('%H:%M:%S'))
games_now = games[(games['Time'] >= now.strftime(f'%Y-%m-%d')  + f' {start_time}:00:00') & (games['Time'] < now.strftime(f'%Y-%m-%d')  + f' {start_time+3}:00:00')]

# Iterate through games
for _, game in games_now.iterrows() :

    eventId = game['event_id']
    print(f'Querying game {game["game_id"]}...')

    odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/events/{eventId}/odds',
                             params = {'apiKey': api_key,
                                       'regions': 'us',
                                       'markets': 'player_first_basket',
                                       'oddsFormat': 'decimal'})
    
    bm_dfs = [pd.DataFrame(columns = ['name', 'price', 'bookmaker', 'update_time'])]


    print(odds_response)


    for bookmaker in odds_response.json()['bookmakers'] :
        
        bm_df = pd.DataFrame(bookmaker['markets'][0]['outcomes'])
        bm_df['bookmaker'] = bookmaker['key']
        bm_df['update_time'] = bookmaker['markets'][0]['last_update']

        print(f'\tFound {len(bm_df)} lines from {bookmaker["key"]}')

        bm_dfs.append(
            bm_df
            .drop(columns = 'name')
            .rename(columns = {'description': 'name'})
        )

    game_df = pd.concat(bm_dfs).reset_index(drop = True)
    game_df['game_id'] = game['game_id']
    game_df['event_id'] = game['event_id']

    game_df['insert_timestamp_utc'] = datetime.now(timezone.utc)
    game_df.to_csv('data/odds_first_basket.csv', index = None, header = None, mode = 'a')

    # subject = f'[LeFirstBasket | {now.strftime("%d %b %Y")}] Successfully scraped {game["game_id"]}!'
    
    # send_email(game_df[['name', 'price', 'bookmaker', 'update_time']],
    #            receivers = ['martinbog19@gmail.com', 'lucas.leforestier@gmail.com'],
    #            subject = subject)