import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from time import sleep
import pickle

from helpers.scrape import get_first_basket, get_roster
from helpers.preprocess import feature_engineering
from helpers.utils import getId
from helpers.email import send_email


yst = datetime.now(ZoneInfo('America/New_York')) - timedelta(days = 1)


url = f'https://www.basketball-reference.com/boxscores/?month={yst.month}&day={yst.day}&year={yst.year}'
page = requests.get(url)
soup = BeautifulSoup(page.content, 'lxml')

def predict_first_basket(starting_lineups) :
    players = (starting_lineups[0] + starting_lineups[1])
    ratings = pd.read_csv('data/player_metadata.csv')
    ratings = ratings.copy()[ratings['player_id'].isin(players)].sort_values('rating')
    first_basket_pred = ratings['player_id'].values[-1]
    return first_basket_pred

def random_first_basket(starting_lineups) :
    players = (starting_lineups[0] + starting_lineups[1])
    idx = np.random.randint(0, 10)
    return players[idx]


game_ids = [getId(x) for x in soup.find_all('a', href = True) if 'boxscores/pbp' in x['href']]

dfs = []
for i, gameId in enumerate(game_ids) :
    sleep(5)
    print(f'[{i+1}/{len(game_ids)}] {gameId}')
    df, starting_lineups = get_first_basket(gameId)
    df.insert(1, 'Date', yst.date())
    df.insert(2, 'Time', np.nan)
    df.insert(5, 'season', 2025)
    df.to_csv('data/first_basket_2025.csv', index = False, header = False, mode = 'a')
    df['first_basket_rand'] = random_first_basket(starting_lineups)
    df['first_basket_pred'] = predict_first_basket(starting_lineups)
    dfs.append(df[['game_id', 'Date', 'Home', 'Away', 'first_basket', 'first_basket_tm', 'first_basket_rand', 'first_basket_pred']])
    sleep(5)
    roster = get_roster(gameId)
    roster.to_csv('data/rosters.nosync/rosters_2025.csv', index = None, header = None, mode = 'a')

first_basket_df = pd.concat(dfs).set_index('game_id')
first_basket_df['correct_pred'] = (first_basket_df['first_basket'] == first_basket_df['first_basket_pred'])
first_basket_df['correct_rand'] = (first_basket_df['first_basket'] == first_basket_df['first_basket_rand'])
first_basket_df = first_basket_df[['Date', 'Home', 'Away', 'first_basket', 'first_basket_tm', 'first_basket_pred', 'correct_pred', 'first_basket_rand', 'correct_rand']]

# Map id's to player names
player_metadata = pd.read_csv('data/player_metadata.csv')
playerId_map = dict(zip(player_metadata['player_id'], player_metadata['name']))
for player_col in ['first_basket', 'first_basket_pred', 'first_basket_rand'] :
    first_basket_df[player_col] = first_basket_df[player_col].map(playerId_map)

acc_pred = first_basket_df['correct_pred'].mean()
acc_rand = first_basket_df['correct_rand'].mean()

print(f'\nAccuracy predicted : {round(100 * acc_pred, 1)}%  [{first_basket_df["correct_pred"].sum()}/{first_basket_df.shape[0]}]\n')
print(f'\nAccuracy random    : {round(100 * acc_rand, 1)}%  [{first_basket_df["correct_rand"].sum()}/{first_basket_df.shape[0]}]\n\n')
print(first_basket_df, '\n\n\n')

date = yst.strftime("%d %b %Y")
synopsis = f'[LeFirstBasket | {date}] Random model: {round(100 * acc_rand, 1)}% | Predicted model: {round(100 * acc_pred, 1)}%'

send_email(first_basket_df,
           receivers = ['martinbog19@gmail.com', 'lucas.leforestier@gmail.com'],
           subject = synopsis)





# Send ML preds
data, features = feature_engineering()

games = data.copy()[data['game_id'].isin(game_ids)].reset_index(drop = True)

X = games[features].to_numpy()

# Load the model from the .pkl file
with open('models/model_rf.pkl', "rb") as f:
    model = pickle.load(f)

y_pred = model.predict_proba(X)[:, -1]

games = games[['game_id', 'player_id', 'Player']]
games['Pred. prob (%)'] = games['Pred. prob (%)'] / games.groupby('game_id')['Pred. prob (%)'].transform('sum')
games['Pred. odds'] = games['Pred. prob (%)'].apply(lambda x: round(1/x, 1))
games['Pred. prob (%)'] = games['Pred. prob (%)'].apply(lambda x: round(x * 100, 1))
games = games.sort_values(['game_id', 'Pred. odds']).reset_index(drop = True)

send_email(games,
           receivers = ['martinbog19@gmail.com', 'lucas.leforestier@gmail.com'],
           subject = 'MACHINE LEARNING PREDICTIONS')