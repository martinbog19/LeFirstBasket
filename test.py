import os
import json


if os.getenv("GITHUB_ACTIONS") == "true" :
  api_key = os.environ.get('ODDS_API_KEY')
  print('GH')
else :
  with open('secrets/odds_api_key.txt') as f:
    api_key = f.read()

with open('utils/odds_tm_map.json', 'r') as f :
  odds_tm_map = json.load(f)
