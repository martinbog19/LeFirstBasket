import pandas as pd
import numpy as np
import os


data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def feature_engineering(lineups = None) :

    feature_stats = ['PTS', 'USG%', 'VORP', 'FGA']
    windows = [5, 25, 50]


    # Load label dtaa
    first_basket_dir = data_path
    first_basket = pd.concat([pd.read_csv(os.path.join(first_basket_dir, file)) for file in os.listdir(first_basket_dir) if file.startswith('first_basket')])
    first_basket = first_basket.sort_values('Date').reset_index(drop = True)

    # Load feature data
    roster_dir = os.path.join(data_path, 'rosters.nosync')
    dfs = []
    for file in os.listdir(roster_dir) :
        df = pd.read_csv(os.path.join(roster_dir, file))
        year = int(file.split('_')[-1][:4])
        df.insert(1, 'Year', year)
        dfs.append(df)
    stats = pd.concat(dfs).sort_values('game_id').reset_index(drop = True)

    # Add future game lineups
    stats = pd.concat([stats, lineups]).reset_index(drop = True)

    # Load rating data
    ratings = pd.read_csv(os.path.join(data_path, '2k-ratings-2001-2024.csv'))[['Year', 'player_id', 'rating']]
    ratings_25 = pd.read_csv(os.path.join(data_path, 'player_metadata.csv'))[['player_id', 'rating']]
    ratings_25['Year'] = 2025
    ratings = pd.concat([ratings, ratings_25]).reset_index(drop = True)


    features = []

    for f in feature_stats :

        stats[f'{f}_avg'] = stats.groupby('player_id')[f'{f}'].expanding().mean().reset_index(level = 0, drop = True)
        stats[f'{f}_avg'] = stats.groupby('player_id')[f'{f}_avg'].shift()
        features.append(f'{f}_avg')

        for w in windows :
            stats[f'{f}_{w}'] = stats.groupby('player_id')[f'{f}'].rolling(w, min_periods = 1).mean().reset_index(level = 0, drop = True)
            stats[f'{f}_{w}'] = stats.groupby('player_id')[f'{f}_{w}'].shift()
            features.append(f'{f}_{w}')


    # Merge
    stats = pd.merge(stats, first_basket[['game_id', 'first_basket']], on = 'game_id', how = 'left')
    stats['first_basket_scorer'] = stats.apply(lambda row :
        int(row['first_basket'] == row['player_id'])
        if not pd.isna(row['first_basket'])
        else np.nan,
        axis = 1
    )

    stats['first_basket_avg'] = stats.groupby('player_id')['first_basket_scorer'].expanding().mean().reset_index(level = 0, drop = True)
    stats['first_basket_avg'] = stats.groupby('player_id')['first_basket_avg'].shift()
    features.append('first_basket_avg')

    for w in windows :
        stats[f'first_basket_{w}'] = stats.groupby('player_id')['first_basket_scorer'].rolling(w, min_periods = 1).mean().reset_index(level = 0, drop = True)
        stats[f'first_basket_{w}'] = stats.groupby('player_id')[f'first_basket_{w}'].shift()
        features.append(f'first_basket_{w}')

    stats = stats.merge(
        ratings,
        on = ['player_id', 'Year'],
        how = 'left'
    )
    features.append('rating')

    starters = stats.copy()[stats['starter']]
    data = starters[['game_id', 'Player', 'player_id', 'first_basket_scorer'] + features].reset_index(drop = True)

    # Normalize per game
    eps = 1e-6
    data[features] = (
        (
            data[features] - data.groupby('game_id')[features].transform('mean')
        )
        / (data.groupby('game_id')[features].transform('std') + eps)
    )

    return data, features