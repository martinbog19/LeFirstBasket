import pandas as pd
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import requests
import os
import json



if os.getenv("GITHUB_ACTIONS") == "true" :
  api_key = os.getenv('ODDS_API_KEY')
else :
  with open('secrets/odds_api_key.txt') as f:
    api_key = f.read()

with open('utils/odds_tm_map.json', 'r') as f :
  odds_tm_map = json.load(f)


print(os.getenv("GITHUB_ACTIONS"), api_key)

games = pd.read_csv('data/games.csv')

# Store subset of games in the next 30 minutes
now = datetime.now(ZoneInfo('America/New_York'))
games_now = games[(games['Time'] > now.strftime('%Y-%m-%d %H:%M:%S')) & (games['Time'] <= (now + timedelta(minutes = 30)).strftime('%Y-%m-%d %H:%M:%S'))]
print(games_now.shape)

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

        print(f'Found {len(bm_df)} lines from {bookmaker["key"]}')

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