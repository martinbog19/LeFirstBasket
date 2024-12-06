import json
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from helpers.scrape import get_ratings, get_players
from fuzzywuzzy import process

from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler

def manual_rating(row, hardcoded_players) :

    if np.isnan(row['rating']) and row['player_id'] in hardcoded_players:
        with open('utils/manual_2k.json', 'r') as f:
            manual_dict = json.load(f)
        return manual_dict[row['player_id']]
    else :
        return row['rating']
    
#### GLOBAL VARIABLE ####
season = 2025
########

ratings = get_ratings(season)
players = get_players(season)


# Replace with name_map_2k
with open('utils/name_map_2k.json', 'r') as f:
    name_map = json.load(f)
ratings['name_norm'] = ratings['name_norm'].apply(lambda x: name_map[x] if x in name_map.keys() else x)

# Initial merge
players_ratings = pd.merge(players, ratings,
                  how = 'left',
                  on = 'name_norm')

# Check for duplicates
if players_ratings['player_id'].value_counts().max() > 1 :
    duplicated_ratings = players_ratings.copy()[players_ratings['player_id'].duplicated(keep = False)]
    duplicated_ids = duplicated_ratings['player_id'].unique().tolist()
    players_ratings['rating'].loc[duplicated_ratings.index] = np.nan
    print(f'!!!  playerId {", ".join(duplicated_ids)} duplicated, ratings set to NULL')

# Hard-coded ratings (the Sabonis)
with open('utils/manual_2k.json', 'r') as f:
    manual_dict = json.load(f)
hardcoded_players = list(manual_dict.keys())
players_ratings['rating'] = players_ratings.apply(manual_rating, axis = 1, args = hardcoded_players)

# Suggested additions to name_map_2k
null_ratings = players_ratings.copy()[players_ratings['rating'].isna()]
choices = ratings['name_norm'].tolist()
suggested_map = {name: process.extractOne(name, choices)[0] for name in null_ratings['name_norm']}
with open('utils/name_map_suggestions_2k.json', 'w') as f :
    json.dump(suggested_map, f)

# Impute still missing with kNN
with open('utils/knn_features.txt', 'r') as file:
    knn_features = [f.strip('\n') for f in file.readlines()]
train = players_ratings.copy()[players_ratings['rating'].notna()]
scaler = StandardScaler()
X_train = scaler.fit_transform(train[knn_features])
# Fit a kNN model with 10 neighbors to the data
knn = KNeighborsRegressor(n_neighbors = 10)
knn.fit(X_train, train['rating'])
X_null = scaler.transform(null_ratings[knn_features])
null_ratings['rating'] = knn.predict(X_null)

players_ratings['insert_timestamp_utc'] = datetime.now(timezone.utc)

players_ratings = (
    pd.concat([train, null_ratings])
    [['player_id', 'name', 'name_norm', 'Team', 'rating']]
    .sort_values('rating', ascending = False)
)

players_ratings['insert_timestamp_utc'] = datetime.now(timezone.utc)
                            
players_ratings.to_csv('data/player_metadata.csv', index = False)