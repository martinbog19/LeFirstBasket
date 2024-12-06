import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np
import os
import time


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

    # Four factors
    page_ = page.text.split('<div class="table_container" id="div_four_factors">')[1].split('</table>')[0] + '</table>'
    soup = BeautifulSoup(page_, 'lxml')
    table = soup.find('table')
    ff = pd.read_html(str(table))[0]
    ff.columns = ff.columns.droplevel(0)
    ff = ff.rename(columns = {'Unnamed: 0_level_1': 'Team'})
    ff.insert(0, 'game_id', game_id)
    
    return game, ff

years = np.arange(2024, 2024 + 1)
for year in years :

    print(year, '...')

    game_ids = pd.concat([pd.read_csv(os.path.join(f'data.nosync/schedules/{year}/', f)) for f in os.listdir(f'data.nosync/schedules/{year}/')])['game_id'].unique().tolist()
    teams = sorted([x.split('-')[1] for x in os.listdir(f'data.nosync/schedules/{year}/')])

    for tm in teams :
        os.makedirs(f'data.nosync/rosters/{year}/{tm}', exist_ok = True)
        game_ids_tm = [gid for gid in game_ids if tm in gid]
        ffs = []
        for game_id in game_ids_tm :
            time.sleep(2)
            roster, ff = get_roster(game_id)
            roster.to_csv(f'data.nosync/rosters/{year}/{tm}/roster-{year-1}-{year}-{game_id}.csv', index = None)
            ffs.append(ff)
        ffs_data = pd.concat(ffs).reset_index(drop = True)
        ffs_data.to_csv(f'data.nosync/rosters/{year}/{tm}/four-factors-{tm}-{year-1}-{year}.csv', index = None)

        time.sleep(10)

    time.sleep(60)