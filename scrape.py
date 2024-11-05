import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import os
import re
import calendar
from time import sleep

months = list(calendar.month_name)[1:]
season = 2024

# season = min([int(f.split('_')[-1].split('.')[0]) for f in os.listdir('data')])

def getId(tag) :
    return tag['href'].split('/')[-1].split('.html')[0]

def get_monthly_games(month_url) :

    url = f'https://www.basketball-reference.com/{month_url}'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'lxml')
    table = soup.find('table')
    games = pd.read_html(str(table))[0].rename(columns = {'Start (ET)': 'Time'})
    games['Date'] = pd.to_datetime(games['Date'])
    games['Home'] = [x['href'].split('/')[2] for x in table.find_all('a', href = True) if 'teams' in x['href']][1::2]
    games['Away'] = [x['href'].split('/')[2] for x in table.find_all('a', href = True) if 'teams' in x['href']][0::2]
    games['game_id'] = [getId(x) for x in table.find_all('a', href = True) if 'boxscores' in x['href']][1::2]

    return games[['game_id', 'Date', 'Time', 'Home', 'Away']]


def get_first_basket(gameId) :
    
    url = f'https://www.basketball-reference.com/boxscores/pbp/{gameId}.html'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'lxml')
    away, home = [x['href'].split('/')[2] for x in soup.find_all('a', href = True) if 'teams' in x['href']][1:3]
    table = soup.find('table')
    table.find('tr', class_ = 'thead').decompose()
    pbp = pd.read_html(str(table))[0]
    cols_ = pbp.columns.to_list()
    cols_[1] = away
    cols_[5] = home
    pbp.columns = cols_
    pbp['pts_scored'] = pbp['Score'].apply(lambda x: np.array(x.split('-')).astype(int).sum()
                        if re.search(r'\d+-\d+', x)
                        else np.nan)

    n_actions_before_pts = (pbp['pts_scored'] > 0).argmax() + 1

    # Keep rows until first points scored -- excluding jump ball
    pbp = pbp.head(n_actions_before_pts)[1:]

    # Store player involved
    rows = table.find_all('tr')
    pbp['player'] = [getId(row.find_all('a', href = True)[0]) if row.find('a', href = True) else ''
                 for row in rows[2:n_actions_before_pts+1]]
    
    # Check if miss or make or neither
    pbp = pbp.fillna('')
    pbp['home_miss'] = pbp[home].apply(lambda x: 'misses' in x).astype(int)
    pbp['away_miss'] = pbp[away].apply(lambda x: 'misses' in x).astype(int)
    pbp['home_make'] = pbp[home].apply(lambda x: 'makes' in x).astype(int)
    pbp['away_make'] = pbp[away].apply(lambda x: 'makes' in x).astype(int)
    pbp['shot'] = pbp[['home_miss', 'away_miss', 'home_make', 'away_make']].sum(axis = 1)
    pbp = pbp.copy()[pbp['shot'] == 1]


    # Store jump ball information
    if rows[1].find('a', href = True) :
        jb_away, jb_home, jb_poss = [getId(x) for x in rows[1].find_all('a', href = True)]
        url = f'https://www.basketball-reference.com/boxscores/{gameId}.html'
        soup = BeautifulSoup(requests.get(url).content, 'lxml')
        if jb_poss in [getId(x) for x in soup.find('table', id = f'box-{home}-game-basic').find_all('a', href = True)[:5]] :
            jb_poss_tm = home
        else :
            jb_poss_tm = away
    else :
        jb_away, jb_home, jb_poss, jb_poss_tm = None, None, None, None

    # First basket information
    min, sec = np.array(pbp['Time'].values[-1].split(':')).astype(float)
    time_elapsed = 60 * (12 - min - 1) + (60 - sec)
    pts_scored = pbp['pts_scored'].values[-1]
    num_shots = pbp.shape[0]
    home_misses = pbp['home_miss'].sum()
    away_misses = pbp['away_miss'].sum()
    first_basket_tm = home * pbp['home_make'].values[-1] + away * pbp['away_make'].values[-1]
    first_basket = pbp['player'].values[-1]

    return pd.DataFrame(
                [[gameId, home, away, first_basket, first_basket_tm, time_elapsed, num_shots, pts_scored, home_misses, away_misses,
                  jb_home, jb_away, jb_poss, jb_poss_tm]],
                columns = [
                    'game_id',
                    'Home',
                    'Away',
                    'first_basket',
                    'first_basket_tm',
                    'time_elapsed',
                    'num_shots',
                    'pts_scored',
                    'misses_home',
                    'misses_away',
                    'jumpball_home',
                    'jumpball_away',
                    'jumpball_possession',
                    'jumpball_possession_tm'
                ]
            )


url = f'https://www.basketball-reference.com/leagues/NBA_{season}_games.html'
page = requests.get(url)
soup = BeautifulSoup(page.content, 'lxml')
month_urls = [x['href'] for x in soup.find_all('a', href = True) if 'games' in x['href'] 
                and any(m.lower() in x['href'] for m in months)]

for m, month_url in enumerate(month_urls) :

    games_monthly = get_monthly_games(month_url)
    games_monthly['season'] = season

    first_basket_info = []
    for i, gameId in enumerate(games_monthly['game_id'])  :

        print(f'[{round(100*(i+1)/len(games_monthly))}%...] season :  {season-1}-{season}, month :  {month_url.split("-")[-1].split(".")[0]} ({gameId})')
        sleep(5)
        first_basket_info.append(get_first_basket(gameId))


    first_basket_df = pd.concat(first_basket_info)
    first_basket_df = games_monthly.merge(first_basket_df, on = ['game_id', 'Home', 'Away'], how = 'inner')
    if m == 0 :
        first_basket_df.to_csv(f'data/first_basket_{season}.csv', index = False)
    else :
        first_basket_df.to_csv(f'data/first_basket_{season}.csv', mode = 'a', header = False, index = False)
