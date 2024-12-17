import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np
import os
import re
import json

from time import sleep
from .utils import getId, normalize_name

import warnings
warnings.simplefilter(action = 'ignore', category = FutureWarning)



def get_ratings(year) :

    url = f'https://hoopshype.com/nba2k/{year-1}-{year}/'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html')
    table = soup.find('table')
    ratings = pd.read_html(str(table))[0]
    ratings.columns = ['drop', 'name', 'rating']
    ratings = ratings.drop(columns = 'drop')
    ratings['name_norm'] = ratings['name'].apply(normalize_name)
    ratings = ratings[['name_norm', 'rating']]

    return ratings

def get_players(year) :

    url = f'https://www.basketball-reference.com/leagues/NBA_{year}_per_game.html'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'lxml')
    table = soup.find('table')
    while table.find_all('tr', class_ = 'thead') :
        table.find('tr', class_ = 'thead')
    try :
        table.find('tr', class_ = 'norank').decompose()
    except :
        pass

    players = pd.read_html(str(table))[0].rename(columns = {'Player': 'name'})
    players['name_norm'] = players['name'].apply(normalize_name)
    players['player_id'] = [getId(x) for x in table.find_all('a', href = True) if 'players' in x['href']]
    # players = players.copy()[players['GS'] > 0]
    # !!!Need to do something about players on multiple teams!!!!!!
    players = players.drop_duplicates().reset_index(drop = True)

    return players


def get_roster(game_id) :

    url = f'https://www.basketball-reference.com/boxscores/{game_id}.html'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'lxml')
    tables = [table for table in soup.find_all('table') if 'game' in table.get('id')]

    dfs = []
    for table in tables :
        df = pd.read_html(str(table))[0][:-1]
        df.columns = df.columns.droplevel(0)
        df = df.copy()[df['Starters'] != 'Reserves']
        df.insert(1, 'player_id', [x['href'].split('/')[-1].split('.')[0] for x in table.find_all('a', href = True)])
        df.insert(2, 'Team', table.get('id').split('-')[1])
        # Only keep players who have played               Checks if there is a digit in the string 
        df = df.copy()[df['MP'].apply(lambda x: ':' in x and max([char.isdigit() for char in x]))]
        df['MP'] = df['MP'].apply(lambda x: int(x.split(':')[0]) + int(x.split(':')[-1]) / 60.) # Time player to numeric
        if 'advanced' in table.get('id') :
            df['VORP'] = [float(str(x).split('VORP: ')[1].split('&')[0]) for x in table.find_all('td', class_ = ['right poptip', 'right poptip iz'])]
            df = df.drop(columns = ['Starters', 'MP', 'Team'])
        dfs.append(df.rename(columns = {'Starters': 'Player'}).fillna(0.))

    home_df = pd.merge(*dfs[2:], on = 'player_id')
    away_df = pd.merge(*dfs[:2], on = 'player_id')

    game = pd.concat([home_df, away_df]).reset_index(drop = True)
    game.insert(0, 'game_id', game_id)
    game['starter'] = game.groupby(['Team']).cumcount() < 5
    
    return game


def get_first_basket(gameId) :
    
    url = f'https://www.basketball-reference.com/boxscores/pbp/{gameId}.html'
    page = requests.get(url)
    if page.status_code == 429 :
        raise ValueError('Rate limited...')
    soup = BeautifulSoup(page.content, 'lxml')
    away, home = [x['href'].split('/')[2] for x in soup.find_all('a', href = True) if 'teams' in x['href']][1:3]
    table = soup.find('table')
    if len(table.find_all('tr')) > 1 :
        table.find('tr', class_ = 'thead').decompose()
        rows = table.find_all('tr')
        pbp = pd.read_html(str(table))[0]
        cols_ = pbp.columns.to_list()
        cols_[1] = away
        cols_[5] = home
        pbp.columns = cols_
        pbp['pts_scored'] = pbp['Score'].apply(lambda x: np.array(x.split('-')).astype(int).sum()
                            if re.search(r'\d+-\d+', x)
                            else np.nan)
        
        jumpball_list = [('Jump ball' in row.text) and ('12:00' in row.find('td').text) for row in rows[:10]]
        jumpball_exists = max(jumpball_list)
        jumpball_idx = np.argmax(jumpball_list)

        n_actions_before_pts = (pbp['pts_scored'] > 0).argmax() + 1

        # Keep rows until first points scored -- excluding jump ball
        pbp = pbp.head(n_actions_before_pts)[int(jumpball_exists):]


        pbp['player'] = [getId(row.find_all('a', href = True)[0]) if row.find('a', href = True) else ''
                        for row in rows[jumpball_exists+1:n_actions_before_pts+1]]

        # Check if miss or make or neither
        pbp = pbp.fillna('')
        pbp['home_miss'] = pbp[home].apply(lambda x: 'misses' in x).astype(int)
        pbp['away_miss'] = pbp[away].apply(lambda x: 'misses' in x).astype(int)
        pbp['home_make'] = pbp[home].apply(lambda x: 'makes' in x).astype(int)
        pbp['away_make'] = pbp[away].apply(lambda x: 'makes' in x).astype(int)
        pbp['shot'] = pbp[['home_miss', 'away_miss', 'home_make', 'away_make']].sum(axis = 1)
        pbp = pbp.copy()[pbp['shot'] == 1]

        # Starting lineups
        sleep(3)
        url = f'https://www.basketball-reference.com/boxscores/{gameId}.html'
        soup = BeautifulSoup(requests.get(url).content, 'lxml')
        starting_lineup_home = [getId(x) for x in soup.find('table', id = f'box-{home}-game-basic').find_all('a', href = True)[:5]]
        starting_lineup_away = [getId(x) for x in soup.find('table', id = f'box-{away}-game-basic').find_all('a', href = True)[:5]]


        # Store jump ball information
        if jumpball_exists and rows[jumpball_idx].find('a', href = True) :
            jb_away, jb_home, jb_poss = [getId(x) for x in rows[jumpball_idx].find_all('a', href = True)]
            if jb_poss in starting_lineup_home :
                jb_poss_tm = home
            elif jb_poss in starting_lineup_away :
                jb_poss_tm = away
            else :
                jb_poss_tm = None

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

    else :
        first_basket, first_basket_tm = None, None
        time_elapsed, num_shots, pts_scored, home_misses, away_misses = None, None, None, None, None
        jb_home, jb_away, jb_poss, jb_poss_tm = None, None, None, None
    
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
                ), (starting_lineup_home, starting_lineup_away)


def get_rotowire_lineups() :

    url = 'https://www.rotowire.com/basketball/nba-lineups.php'
    response = requests.get(url)
    html = response.text.replace('<!--', '').replace('-->', '')
    soup = BeautifulSoup(html, 'lxml')
    
    return soup

def get_lineups(soup, tm) :

    with open('utils/rotowire_tm_map.json', 'r') as f:
        tm_map = json.load(f)

    home_tags = soup.find_all('a', class_ = 'lineup__team is-home')
    away_tags = soup.find_all('a', class_ = 'lineup__team is-visit')

    home_lineup_tags = soup.find_all('ul', class_ = 'lineup__list is-home')
    away_lineup_tags = soup.find_all('ul', class_ = 'lineup__list is-visit')

    for home_tag, away_tag, home_lineup_tag, away_lineup_tag in zip(
        home_tags, away_tags, home_lineup_tags, away_lineup_tags
    ) :
        
        rw_home = home_tag.find(class_ = 'lineup__abbr').text
        rw_away = away_tag.find(class_ = 'lineup__abbr').text

        home, away = tm_map[rw_home], tm_map[rw_away]

        if home == tm or away == tm :

            starting_lineup_tags = home_lineup_tag.find_all('li')[1:6]
            players_home = [' '.join(x.find('a', href = True)['href'].split('/')[-1].split('-')[:-1]) for x in starting_lineup_tags]
            df_home = pd.DataFrame(players_home, columns = ['name'])
            df_home['name_norm'] = df_home['name'].apply(lambda x: normalize_name(x, True))
            df_home['Team'] = home

            starting_lineup_tags = away_lineup_tag.find_all('li')[1:6]
            players_away = [' '.join(x.find('a', href = True)['href'].split('/')[-1].split('-')[:-1]) for x in starting_lineup_tags]
            df_away = pd.DataFrame(players_away, columns = ['name'])
            df_away['name_norm'] = df_away['name'].apply(lambda x: normalize_name(x, True))
            df_away['Team'] = away
            break

        else :
            pass

    lineups = pd.concat([df_home, df_away]).reset_index(drop = True)

    return lineups