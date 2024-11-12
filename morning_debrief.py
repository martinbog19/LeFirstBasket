import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
from time import sleep

from scrape import get_first_basket, getId


yst = datetime.today() - timedelta(days = 1)

url = f'https://www.basketball-reference.com/boxscores/?month={yst.month}&day={yst.day}&year={yst.year}'
page = requests.get(url)
soup = BeautifulSoup(page.content, 'lxml')

def predict_first_basket() :
    ######### starting_lineups #########
    return np.random.randint(0, 10)



game_ids = [getId(x) for x in soup.find_all('a', href = True) if 'boxscores/pbp' in x['href']]
dfs = []
for gameId in game_ids :
    sleep(10)
    df, starting_lineups = get_first_basket(gameId, starting_lineups = True)
    idx = predict_first_basket()
    df['first_basket_pred'] = (starting_lineups[0] + starting_lineups[1])[idx]
    dfs.append(df[['game_id', 'Home', 'Away', 'first_basket', 'first_basket_tm', 'first_basket_pred']])

first_basket_df = pd.concat(dfs).set_index('game_id')
first_basket_df['Date'] = yst.date()
first_basket_df['correct_pred'] = (first_basket_df['first_basket'] == first_basket_df['first_basket_pred'])
first_basket_df = first_basket_df[['Date', 'Home', 'Away', 'first_basket', 'first_basket_tm', 'first_basket_pred', 'correct_pred']]




acc = first_basket_df['correct_pred'].mean()

print(f'\nAccuracy: {round(100 * acc, 1)}%  [{first_basket_df["correct_pred"].sum()}/{first_basket_df.shape[0]}]\n\n')
print(first_basket_df, '\n\n\n')
